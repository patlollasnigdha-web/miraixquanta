"""
MIRAI — Dynamic Risk Management Module (M11)
Exports risk metrics, dynamic position sizing, circuit breakers,
trailing stop ratcheting, exposure limits, and risk management engine.
"""

from src.risk_management.risk_metrics import (
    RiskMetrics,
    compute_drawdown_series,
    compute_historical_var,
    compute_historical_cvar,
    compute_parametric_var,
    compute_parametric_cvar,
    compute_sharpe_ratio,
    compute_sortino_ratio,
    compute_calmar_ratio,
    compute_risk_summary,
)
from src.risk_management.position_sizing import (
    PositionSizer,
    PositionSizeResult,
)
from src.risk_management.risk_controls import (
    CircuitBreakerState,
    CircuitBreakerMonitor,
    TrailingStopManager,
    TrailingStopState,
    update_trailing_stop,
    ExposureLimitValidator,
)
from src.risk_management.risk_engine import (
    RiskManagementEngine,
    RiskEvaluationResult,
)

__all__ = [
    "RiskMetrics",
    "compute_drawdown_series",
    "compute_historical_var",
    "compute_historical_cvar",
    "compute_parametric_var",
    "compute_parametric_cvar",
    "compute_sharpe_ratio",
    "compute_sortino_ratio",
    "compute_calmar_ratio",
    "compute_risk_summary",
    "PositionSizer",
    "PositionSizeResult",
    "CircuitBreakerState",
    "CircuitBreakerMonitor",
    "TrailingStopManager",
    "TrailingStopState",
    "update_trailing_stop",
    "ExposureLimitValidator",
    "RiskManagementEngine",
    "RiskEvaluationResult",
]
