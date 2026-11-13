"""
MIRAI — Investment Decisions Endpoints (M15)
"""

from fastapi import APIRouter, Depends
import pandas as pd

from src.api.dependencies import (
    get_data_access_service,
    get_decision_engine,
    get_risk_engine,
)
from src.data_engineering.data_access import DataAccessService
from src.decision.decision_engine import InvestmentDecisionEngine
from src.decision.decision_schemas import DecisionInput
from src.risk_management.risk_engine import RiskManagementEngine
from src.strategies.momentum_strategy import MomentumStrategy
from src.api.api_schemas import DecisionEvaluateRequest, DecisionResponse

router = APIRouter(prefix="/decisions", tags=["Decisions"])


@router.post("/evaluate", response_model=DecisionResponse)
def evaluate_decision(
    req: DecisionEvaluateRequest,
    data_service: DataAccessService = Depends(get_data_access_service),
    decision_engine: InvestmentDecisionEngine = Depends(get_decision_engine),
    risk_engine: RiskManagementEngine = Depends(get_risk_engine),
):
    """
    Authoritative Investment Decision endpoint.
    Aggregates multi-pillar evidence (M03, M05, M06, M07, M08) and validates through M11 risk engine.
    """
    sym = req.symbol.strip().upper()
    df = data_service.get_multistock_daily(symbols=[sym])
    if df.empty:
        df = data_service.get_nifty_daily_index()

    close_p = float(df["close"].iloc[-1]) if not df.empty and "close" in df.columns else 100.0
    bar_ts = df.index[-1] if not df.empty else pd.Timestamp.now()

    # Generate strategy signal if history permits
    strat = MomentumStrategy()
    signal = strat.generate_signal(df, symbol=sym) if len(df) >= 55 else None

    inp = DecisionInput(
        symbol=sym,
        timestamp=bar_ts,
        current_price=close_p,
        strategy_signal=signal,
        pipeline_id=req.pipeline_id,
        investment_horizon=req.investment_horizon,
    )

    decision = decision_engine.make_decision_with_risk(
        inp=inp,
        risk_engine=risk_engine,
        current_capital=1_000_000.0,
    )

    return DecisionResponse(
        symbol=sym,
        verdict=decision.verdict,
        display_label=decision.display_label,
        composite_score=decision.composite_score,
        confidence=decision.confidence,
        action_type=decision.action_type,
        risk_status=decision.risk_status,
        entry_reference_price=decision.entry_reference_price,
        suggested_stop_loss=decision.suggested_stop_loss,
        suggested_take_profit=decision.suggested_take_profit,
        explanation=decision.explanation.narrative if decision.explanation else "",
        positive_factors=decision.explanation.positive_factors if decision.explanation else [],
        negative_factors=decision.explanation.negative_factors if decision.explanation else [],
        conflicting_signals=decision.explanation.conflicting_signals if decision.explanation else [],
        warnings=[],
        timestamp=str(decision.timestamp),
    )
