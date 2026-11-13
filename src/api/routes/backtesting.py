"""
MIRAI — Backtesting Endpoints (M15)
"""

import uuid
from fastapi import APIRouter, Depends
import pandas as pd

from src.api.dependencies import get_data_access_service
from src.data_engineering.data_access import DataAccessService
from src.backtesting.backtest_engine import BacktestEngine
from src.strategies.momentum_strategy import MomentumStrategy
from src.api.api_schemas import BacktestRunRequest, BacktestRunResponse

router = APIRouter(prefix="/backtesting", tags=["Backtesting"])


@router.post("/run", response_model=BacktestRunResponse)
def run_backtest(
    req: BacktestRunRequest,
    data_service: DataAccessService = Depends(get_data_access_service),
):
    """Executes institutional backtesting simulation across historical data."""
    sym = req.symbols[0].strip().upper() if req.symbols else "TCS"
    df = data_service.get_multistock_daily(symbols=[sym])
    if df.empty or len(df) < 55:
        df = data_service.get_nifty_daily_index()

    strategy = MomentumStrategy()
    engine = BacktestEngine(initial_capital=req.initial_capital)
    report = engine.run(strategy=strategy, data=df, symbol=sym)

    backtest_id = f"BT_{uuid.uuid4().hex[:8].upper()}"
    metrics = report.metrics if hasattr(report, "metrics") else {
        "total_return_pct": report.total_return * 100.0 if hasattr(report, "total_return") else 0.0,
        "max_drawdown_pct": report.max_drawdown * 100.0 if hasattr(report, "max_drawdown") else 0.0,
        "win_rate_pct": report.win_rate if hasattr(report, "win_rate") else 0.0,
        "sharpe_ratio": report.sharpe_ratio if hasattr(report, "sharpe_ratio") else 0.0,
        "total_trades": len(report.trades) if hasattr(report, "trades") else 0,
    }

    return BacktestRunResponse(
        backtest_id=backtest_id,
        status="COMPLETED",
        metrics=metrics,
    )
