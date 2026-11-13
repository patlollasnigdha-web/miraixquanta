"""
Tests for MIRAI Paper Performance Tracker (M14)
Validates equity curve generation, drawdown calculation, win rate, and metrics computation.
"""

import pytest
import pandas as pd
from src.paper_trading.paper_performance import PaperPerformanceTracker
from src.backtesting.trade_simulator import Trade


def test_performance_tracker_snapshots_and_curves():
    tracker = PaperPerformanceTracker(initial_capital=100_000.0)
    dates = pd.date_range("2026-01-01", periods=5, freq="1D")

    # Day 1: 100k
    tracker.record_snapshot(dates[0], equity=100_000.0, cash=100_000.0)
    # Day 2: 110k (peak)
    tracker.record_snapshot(dates[1], equity=110_000.0, cash=90_000.0)
    # Day 3: 104.5k (5% drawdown from peak 110k)
    tracker.record_snapshot(dates[2], equity=104_500.0, cash=85_000.0)
    # Day 4: 115k (new peak)
    tracker.record_snapshot(dates[3], equity=115_000.0, cash=85_000.0)
    # Day 5: 115k
    tracker.record_snapshot(dates[4], equity=115_000.0, cash=115_000.0)

    eq_curve = tracker.get_equity_curve()
    assert len(eq_curve) == 5
    assert eq_curve.iloc[0] == 100_000.0
    assert eq_curve.iloc[-1] == 115_000.0

    dd_curve = tracker.get_drawdown_curve()
    assert len(dd_curve) == 5
    # Day 3 drawdown: (104,500 - 110,000) / 110,000 = -0.05 (-5.0%)
    assert pytest.approx(dd_curve.iloc[2], rel=1e-3) == -0.05


def test_performance_metrics_calculation_with_trades():
    tracker = PaperPerformanceTracker(initial_capital=100_000.0)
    dates = pd.date_range("2026-01-01", periods=3, freq="1D")

    tracker.record_snapshot(dates[0], equity=100_000.0, cash=100_000.0)
    tracker.record_snapshot(dates[1], equity=105_000.0, cash=105_000.0)
    tracker.record_snapshot(dates[2], equity=110_000.0, cash=110_000.0)

    # 2 Winning trades, 1 Losing trade
    t1 = Trade(
        trade_id="T1", symbol="TCS", direction="LONG", quantity=10,
        entry_time=dates[0], entry_price=100.0, entry_costs=5.0, entry_slippage=0.0,
        exit_time=dates[1], exit_price=120.0, exit_costs=5.0, exit_slippage=0.0,
        gross_pnl=200.0, net_pnl=190.0, exit_reason="TARGET", bars_held=1, is_closed=True
    )
    t2 = Trade(
        trade_id="T2", symbol="INFY", direction="LONG", quantity=10,
        entry_time=dates[0], entry_price=100.0, entry_costs=5.0, entry_slippage=0.0,
        exit_time=dates[1], exit_price=110.0, exit_costs=5.0, exit_slippage=0.0,
        gross_pnl=100.0, net_pnl=90.0, exit_reason="TARGET", bars_held=1, is_closed=True
    )
    t3 = Trade(
        trade_id="T3", symbol="SBIN", direction="LONG", quantity=10,
        entry_time=dates[1], entry_price=100.0, entry_costs=5.0, entry_slippage=0.0,
        exit_time=dates[2], exit_price=95.0, exit_costs=5.0, exit_slippage=0.0,
        gross_pnl=-50.0, net_pnl=-60.0, exit_reason="STOP", bars_held=1, is_closed=True
    )

    metrics = tracker.calculate_metrics(trades=[t1, t2, t3])

    assert metrics["total_trades"] == 3
    assert metrics["winning_trades"] == 2
    assert metrics["losing_trades"] == 1
    assert pytest.approx(metrics["win_rate_pct"], rel=1e-2) == 66.67
    assert metrics["total_return_pct"] > 0.0
    assert metrics["initial_capital"] == 100_000.0
    assert metrics["current_equity"] == 110_000.0
