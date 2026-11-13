"""
MIRAI — Monitoring & Observability Schemas (M18)
Data structures for system health, component checks, metrics, and alerts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
import pandas as pd


class HealthStatus(str, Enum):
    """Component and system health states."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


class AlertSeverity(str, Enum):
    """Alert priority and impact classification."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class ComponentHealth:
    """Health status and metadata for a single subsystem."""
    name: str
    status: HealthStatus
    message: str = "Operating normally"
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    last_checked: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "details": self.details,
            "last_checked": self.last_checked.isoformat(),
        }


@dataclass
class SystemHealthReport:
    """Holistic multi-component health report."""
    overall_status: HealthStatus
    version: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    components: Dict[str, ComponentHealth] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "components": {k: v.to_dict() for k, v in self.components.items()},
        }


@dataclass
class Alert:
    """System alert event triggered by health or metrics thresholds."""
    title: str
    description: str
    severity: AlertSeverity
    source: str
    alert_id: str = field(default_factory=lambda: f"ALT_{uuid.uuid4().hex[:8].upper()}")
    timestamp: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
        }


@dataclass
class SystemResourceUsage:
    """Host machine resource utilization."""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "timestamp": self.timestamp.isoformat(),
        }
