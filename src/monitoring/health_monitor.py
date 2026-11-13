"""
MIRAI — Health Monitor (M18)
Performs synchronous and periodic health probes across the backend, database,
ML models, and local Ollama runtime.
"""

from datetime import datetime
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, Optional
import urllib.request
import json

from src.utils.logger import get_logger
from src.utils.config import get_config
from src.monitoring.monitoring_schemas import (
    ComponentHealth,
    HealthStatus,
    SystemHealthReport,
)

logger = get_logger("HealthMonitor")


class HealthMonitor:
    """
    Evaluates availability, response time, and integrity across all MIRAI subsystems.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        ollama_host: Optional[str] = None,
        models_dir: Optional[str] = None,
    ):
        cfg = get_config()
        self.db_path = db_path or os.getenv("MIRAI_DB_PATH", cfg.get("paper_trading.db_path", "data/paper_trading.db"))
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", cfg.get("assistant.ollama_host", "http://localhost:11434"))
        self.models_dir = models_dir or cfg.get("paths.model_save_dir", "models")
        self.app_version = cfg.get("api.version", "1.0.0")

    def check_database(self) -> ComponentHealth:
        """Probes SQLite database accessibility and schema table integrity."""
        t0 = time.perf_counter()
        db_p = Path(self.db_path)
        if not db_p.exists():
            return ComponentHealth(
                name="database",
                status=HealthStatus.DEGRADED,
                message=f"Database file not yet created at {self.db_path}. Will initialize on first session.",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                details={"db_path": str(db_p), "exists": False},
            )

        try:
            with sqlite3.connect(str(db_p), timeout=2.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [r[0] for r in cursor.fetchall()]
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="SQLite database connected and responsive",
                latency_ms=elapsed_ms,
                details={"db_path": str(db_p), "tables_count": len(tables), "tables": tables},
            )
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.error("Database health check failed: %s", e)
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database probe failed: {str(e)}",
                latency_ms=elapsed_ms,
                details={"db_path": str(db_p), "error": str(e)},
            )

    def check_ollama(self) -> ComponentHealth:
        """Probes local Ollama LLM endpoint."""
        t0 = time.perf_counter()
        url = f"{self.ollama_host.rstrip('/')}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MIRAI-Monitor/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body)
                models = [m.get("name") for m in data.get("models", [])]

            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.HEALTHY,
                message=f"Ollama reachable with {len(models)} model(s) available",
                latency_ms=elapsed_ms,
                details={"host": self.ollama_host, "available_models": models},
            )
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.info("Ollama probe: service not available (%s)", e)
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.DEGRADED,
                message=f"Ollama local service unavailable: {str(e)}",
                latency_ms=elapsed_ms,
                details={"host": self.ollama_host, "error": str(e)},
            )

    def check_models(self) -> ComponentHealth:
        """Verifies machine learning model registry artifacts."""
        t0 = time.perf_counter()
        m_dir = Path(self.models_dir)
        if not m_dir.exists():
            return ComponentHealth(
                name="models",
                status=HealthStatus.DEGRADED,
                message=f"Model directory '{self.models_dir}' not found.",
                latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                details={"directory": str(m_dir), "artifacts": []},
            )

        artifacts = list(m_dir.glob("*.joblib")) + list(m_dir.glob("*.pt"))
        names = [f.name for f in artifacts]
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        return ComponentHealth(
            name="models",
            status=HealthStatus.HEALTHY if names else HealthStatus.DEGRADED,
            message=f"Model directory contains {len(names)} artifact(s)" if names else "No model artifacts found",
            latency_ms=elapsed_ms,
            details={"directory": str(m_dir), "artifacts": names},
        )

    def check_all(self) -> SystemHealthReport:
        """Executes full diagnostic suite across all components."""
        db_health = self.check_database()
        ollama_health = self.check_ollama()
        models_health = self.check_models()

        components = {
            "backend": ComponentHealth(
                name="backend",
                status=HealthStatus.HEALTHY,
                message="FastAPI core running normally",
                latency_ms=0.1,
            ),
            "database": db_health,
            "ollama": ollama_health,
            "models": models_health,
        }

        # Overall status: UNHEALTHY if any component UNHEALTHY; DEGRADED if any DEGRADED; else HEALTHY
        statuses = [c.status for c in components.values()]
        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            # Note: Ollama being unavailable degrades assistant but does not make MIRAI UNHEALTHY
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return SystemHealthReport(
            overall_status=overall,
            version=self.app_version,
            timestamp=datetime.utcnow(),
            components=components,
        )


# Global shared instance
default_health = HealthMonitor()
