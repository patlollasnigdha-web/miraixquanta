"""
End-to-End Integration Tests for Execution and Backtesting Engines (M12 & M13).
Validates full pipeline: Market Data -> Strategy -> Decision Engine -> Risk Engine ->
Execution Engine -> Backtest Report.
"""

import pytest
import numpy as np
import pandas as pd

from src.strategies.momentum_strategy import MomentumStrategy
from src.decision.decision_engine import InvestmentDecisionEngine
from src.risk_management.risk_engine import RiskManagementEngine, CircuitBreakerState
from src.execution.execution_engine import IntelligentExecutionEngine
from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.backtest_report import BacktestReport


@pytest.fixture
def trending_ohlcv_data():
    """Generates 100 daily bars of trending market data for TCS."""
    dates = pd.date_range("2026-01-01", periods=100, freq="B")
    # Base price path with rising momentum: 3000 -> 3800
    np.random.seed(42)
    drift = np.linspace(0, 800, 100)
    noise = np.random.normal(0, 15, 100)
    close = 3000.0 + drift + noise
    open_p = close - 5.0
    high_p = close + 25.0
    low_p = close - 20.0
    volume = np.random.uniform(200_000, 500_000, 100)

    return pd.DataFrame(
        {"open": open_p, "high": high_p, "low": low_p, "close": close, "volume": volume},
        index=dates,
    )


def test_full_pipeline_backtest_integration(trending_ohlcv_data):
    """
    Tests end-to-end integration of MomentumStrategy -> DecisionEngine ->
    RiskEngine -> ExecutionEngine -> BacktestEngine.
    """
    strategy = MomentumStrategy()
    dec_engine = InvestmentDecisionEngine()
    risk_engine = RiskManagementEngine(initial_capital=1_000_000.0)
    exec_engine = IntelligentExecutionEngine()

    bt_engine = BacktestEngine(
        initial_capital=1_000_000.0,
        execution_engine=exec_engine,
        risk_engine=risk_engine,
        decision_engine=dec_engine,
    )

    report = bt_engine.run_backtest(
        data=trending_ohlcv_data,
        strategy=strategy,
        symbol="TCS",
        pipeline_id="pipeline_b_nifty",
        use_decision_engine=True,
        use_risk_engine=True,
    )

    assert isinstance(report, BacktestReport)
    assert report.total_bars == 100
    assert report.initial_capital == 1_000_000.0
    assert len(report.equity_curve) == 100
    assert len(report.drawdown_curve) == 100
    assert report.performance_metrics is not None
    assert "sharpe_ratio" in report.performance_metrics
    assert "max_drawdown_pct" in report.performance_metrics
    assert report.execution_summary["total_orders"] >= 0


def test_risk_blocking_prevents_backtest_trade_execution(trending_ohlcv_data):
    """
    Tests that if RiskEngine enters HALTED state, BacktestEngine respects the block
    and executes zero new buy orders.
    """
    strategy = MomentumStrategy()
    risk_engine = RiskManagementEngine(initial_capital=1_000_000.0)
    risk_engine.circuit_breaker_state = CircuitBreakerState.HALTED  # HALTED!

    bt_engine = BacktestEngine(
        initial_capital=1_000_000.0,
        risk_engine=risk_engine,
    )

    report = bt_engine.run_backtest(
        data=trending_ohlcv_data,
        strategy=strategy,
        symbol="TCS",
        use_decision_engine=True,
        use_risk_engine=True,
    )

    # All buy trades should be blocked by circuit breaker
    assert report.performance_metrics["total_trades"] == 0
    assert report.execution_summary["filled_orders"] == 0
    assert report.final_equity == 1_000_000.0  # Cash completely preserved!
