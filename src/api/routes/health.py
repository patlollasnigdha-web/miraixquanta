"""
MIRAI — Health Endpoints (M15)
"""

from fastapi import APIRouter, Depends
from src.api.dependencies import get_health_monitor
from src.monitoring.health_monitor import HealthMonitor
from src.api.api_schemas import HealthResponse

router = APIRouter(prefix="", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health(monitor: HealthMonitor = Depends(get_health_monitor)):
    """Returns application health across backend, database, models, and Ollama."""
    report = monitor.check_all()
    return HealthResponse(
        overall_status=report.overall_status.value,
        version=report.version,
        timestamp=report.timestamp,
        components={k: v.to_dict() for k, v in report.components.items()},
    )
