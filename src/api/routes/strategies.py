"""
MIRAI — Strategies Endpoints (M15)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
import pandas as pd

from src.api.dependencies import get_data_access_service
from src.data_engineering.data_access import DataAccessService
from src.strategies.momentum_strategy import MomentumStrategy
from src.strategies.mean_reversion_strategy import MeanReversionStrategy
from src.strategies.breakout_strategy import BreakoutStrategy
from src.api.api_schemas import StrategyInfo, StrategyEvaluateRequest, StrategySignalResponse

router = APIRouter(prefix="/strategies", tags=["Strategies"])

REGISTERED_STRATEGIES = [
    StrategyInfo(
        name="Adaptive Momentum Strategy",
        strategy_id="MOMENTUM_STRATEGY",
        description="Captures trend expansions using EMA crossover, RSI confirmation, and ATR targets.",
        supported_pipelines=["pipeline_b_nifty"],
    ),
    StrategyInfo(
        name="Mean Reversion Strategy",
        strategy_id="MEAN_REVERSION_STRATEGY",
        description="Exploits statistical price mean-reversion with Bollinger Bands and regime suppression.",
        supported_pipelines=["pipeline_b_nifty"],
    ),
    StrategyInfo(
        name="Breakout Strategy",
        strategy_id="BREAKOUT_STRATEGY",
        description="Detects high-volume Donchian channel breakouts with volatility expansion filters.",
        supported_pipelines=["pipeline_b_nifty"],
    ),
]


@router.get("", response_model=List[StrategyInfo])
def list_strategies():
    """Lists all registered candidate trading strategies in MIRAI."""
    return REGISTERED_STRATEGIES


@router.post("/evaluate", response_model=StrategySignalResponse)
def evaluate_strategy(
    req: StrategyEvaluateRequest,
    data_service: DataAccessService = Depends(get_data_access_service),
):
    """Evaluates strategy rules on symbol market data and returns trading signals."""
    sym = req.symbol.strip().upper()
    df = data_service.get_multistock_daily(symbols=[sym])
    if df.empty:
        df = data_service.get_nifty_daily_index()

    if len(df) < 55:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient history ({len(df)} bars) to evaluate strategy. Minimum 55 bars required.",
        )

    # Strategy selection
    if req.strategy_id == "MEAN_REVERSION_STRATEGY":
        strategy = MeanReversionStrategy()
    elif req.strategy_id == "BREAKOUT_STRATEGY":
        strategy = BreakoutStrategy()
    else:
        strategy = MomentumStrategy()

    sig = strategy.generate_signal(df, symbol=sym)

    return StrategySignalResponse(
        symbol=sym,
        strategy_name=sig.strategy_name,
        signal=sig.signal,
        signal_strength=sig.signal_strength,
        suggested_stop_loss=sig.suggested_stop_loss,
        suggested_take_profit=sig.suggested_take_profit,
        timestamp=str(sig.timestamp),
    )
