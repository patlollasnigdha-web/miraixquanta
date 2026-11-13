"""
Unit Tests for Backtesting Performance Metrics (M13).
Tests CAGR, Sharpe, Sortino, Calmar, Max Drawdown, Win Rate, Profit Factor,
and robust handling of zero-volatility or empty data edge cases.
"""

import pytest
import numpy as np
import pandas as pd

from src.backtesting.trade_simulator import Trade
from src.backtesting.performance_metrics import (
    calculate_performance_metrics,
    compute_drawdown_curve,
)


@pytest.fixture
def sample_trades():
    """Generates a mixture of winning and losing closed trades."""
    trades = []
    # Trade 1: Win 5,000 INR
    t1 = Trade("T1", "TCS", "LONG", 100, pd.Timestamp("2026-01-01"), 3000.0, 50.0, 10.0)
    t1.close(pd.Timestamp("2026-01-05"), 3050.0, 50.0, 10.0, "TAKE_PROFIT", bars_held=4)
    trades.append(t1)

    # Trade 2: Loss 2,000 INR
    t2 = Trade("T2", "INFY", "LONG", 100, pd.Timestamp("2026-01-06"), 1500.0, 25.0, 5.0)
    t2.close(pd.Timestamp("2026-01-08"), 1480.0, 25.0, 5.0, "STOP_LOSS", bars_held=2)
    trades.append(t2)

    # Trade 3: Win 10,000 INR
    t3 = Trade("T3", "RELIANCE", "LONG", 200, pd.Timestamp("2026-01-10"), 2500.0, 80.0, 15.0)
    t3.close(pd.Timestamp("2026-01-20"), 2550.0, 80.0, 15.0, "SIGNAL_EXIT", bars_held=10)
    trades.append(t3)

    return trades


def test_drawdown_curve():
    """Tests drawdown series calculation."""
    # Equity curve: 1000 -> 1200 (peak) -> 900 (25% dd) -> 1100
    equity = pd.Series([1000.0, 1200.0, 1050.0, 900.0, 1100.0])
    dd_series, max_dd, curr_dd = compute_drawdown_curve(equity)

    assert max_dd == pytest.approx(-0.25, abs=1e-4)
    assert curr_dd == pytest.approx((1100.0 - 1200.0) / 1200.0, abs=1e-4)
    assert dd_series.iloc[1] == 0.0


def test_performance_metrics_normal(sample_trades):
    """Tests standard calculation of performance metrics."""
    # 252 daily bars growing from 1,000,000 to 1,150,000 (+15% return)
    np.random.seed(42)
    daily_rets = np.random.normal(0.0006, 0.01, 252)
    equity = pd.Series(1_000_000.0 * (1.0 + daily_rets).cumprod())

    metrics = calculate_performance_metrics(
        equity_curve=equity,
        trades=sample_trades,
        risk_free_rate=0.065,
    )

    assert metrics["total_trades"] == 3
    assert metrics["winning_trades"] == 2
    assert metrics["losing_trades"] == 1
    assert metrics["win_rate_pct"] == pytest.approx(66.67, abs=0.1)
    assert metrics["profit_factor"] > 1.0
    assert metrics["average_holding_bars"] > 0.0
    assert metrics["total_transaction_costs"] > 0.0
    assert isinstance(metrics["sharpe_ratio"], float)
    assert isinstance(metrics["sortino_ratio"], float)
    assert isinstance(metrics["calmar_ratio"], float)


def test_performance_metrics_edge_cases():
    """Tests edge cases: 0 trades, empty equity, flat equity (zero vol)."""
    # 1. Flat equity (zero volatility)
    flat_equity = pd.Series([100_000.0] * 50)
    metrics_flat = calculate_performance_metrics(flat_equity, trades=[])
    assert metrics_flat["annualized_volatility_pct"] == 0.0
    assert metrics_flat["sharpe_ratio"] == 0.0
    assert metrics_flat["total_trades"] == 0
    assert metrics_flat["profit_factor"] == 0.0

    # 2. Insufficient points (<2 observations)
    tiny_equity = pd.Series([100_000.0])
    metrics_tiny = calculate_performance_metrics(tiny_equity, trades=[])
    assert metrics_tiny["total_return_pct"] == 0.0
    assert "Insufficient data" in metrics_tiny["notes"]
