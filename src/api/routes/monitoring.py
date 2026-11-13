"""
MIRAI — Monitoring & Observability Endpoints (M15 / M18)
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends

from src.api.dependencies import (
    get_health_monitor,
    get_metrics_collector,
    get_alert_manager,
    get_system_monitor,
)
from src.monitoring.health_monitor import HealthMonitor
from src.monitoring.metrics_collector import MetricsCollector
from src.monitoring.alert_manager import AlertManager
from src.monitoring.system_monitor import SystemMonitor

router = APIRouter(prefix="/monitoring", tags=["Monitoring & Observability"])


@router.get("/health")
def get_monitoring_health(
    monitor: HealthMonitor = Depends(get_health_monitor),
) -> Dict[str, Any]:
    """Returns diagnostic health report across all subsystems."""
    report = monitor.check_all()
    return report.to_dict()


@router.get("/metrics")
def get_monitoring_metrics(
    metrics: MetricsCollector = Depends(get_metrics_collector),
    alert_mgr: AlertManager = Depends(get_alert_manager),
) -> Dict[str, Any]:
    """Returns timing distributions, error rates, and operational counters."""
    summary = metrics.get_metric_summary()
    # Evaluate thresholds
    alert_mgr.evaluate_metrics(summary)
    return summary


@router.get("/alerts")
def get_monitoring_alerts(
    limit: int = 50,
    include_acknowledged: bool = True,
    alert_mgr: AlertManager = Depends(get_alert_manager),
) -> Dict[str, Any]:
    """Returns active and recent operational alerts."""
    alerts = alert_mgr.get_all_alerts(limit=limit, include_acknowledged=include_acknowledged)
    return {
        "alerts": [a.to_dict() for a in alerts],
        "count": len(alerts),
    }


@router.get("/system")
def get_monitoring_system(
    system_monitor: SystemMonitor = Depends(get_system_monitor),
) -> Dict[str, Any]:
    """Returns host system resource usage (CPU, RAM, Disk)."""
    return system_monitor.get_system_summary()
