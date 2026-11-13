"""
MIRAI — Risk Management Endpoints (M15)
"""

from fastapi import APIRouter, Depends
from src.api.dependencies import get_risk_engine
from src.risk_management.risk_engine import RiskManagementEngine
from src.api.api_schemas import RiskStatusResponse

router = APIRouter(prefix="/risk", tags=["Risk Management"])


@router.get("/status", response_model=RiskStatusResponse)
def get_risk_status(
    risk_engine: RiskManagementEngine = Depends(get_risk_engine),
):
    """Returns current M11 dynamic risk engine metrics, limits, and circuit breaker status."""
    return RiskStatusResponse(
        circuit_breaker_state=risk_engine.circuit_breaker_state.value,
        max_drawdown_limit_pct=risk_engine.max_drawdown_pct,
        max_position_size_pct=risk_engine.max_position_size_pct,
        cash_reserve_required_pct=5.0,
        status_message="M11 Dynamic Risk Management Active. Safety constraints enforced.",
    )
