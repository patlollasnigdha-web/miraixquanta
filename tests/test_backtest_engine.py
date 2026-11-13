"""
Unit and Integration Tests for Historical Backtest Engine (M13).
Tests bar-by-bar chronological execution, intrabar stop-loss triggers,
portfolio cash updates, end-of-data liquidation, and BacktestReport generation.
"""

import pytest
import numpy as np
import pandas as pd

from src.strategies.base_strategy import BaseStrategy, SignalAction, StrategySignal
from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.backtest_report import BacktestReport
from src.backtesting.portfolio_simulator import PortfolioSimulator


class MockTrendStrategy(BaseStrategy):
    """Mock deterministic strategy: generates BUY on bar 5, SELL on bar 15."""
    strategy_name = "MockTrendStrategy"
    strategy_version = "1.0"

    def generate_signal(self, data: pd.DataFrame, symbol: str) -> StrategySignal:
        idx = len(data) - 1
        curr_price = float(data["close"].iloc[-1])
        ts = data.index[-1]

        if idx == 5:
            return StrategySignal(
                symbol=symbol,
                pipeline_id="pipeline_b_nifty",
                strategy_name=self.strategy_name,
                strategy_version=self.strategy_version,
                signal=SignalAction.BUY,
                signal_strength=0.85,
                prediction_horizon="1d",
                timestamp=ts,
                entry_reference_price=curr_price,
                suggested_stop_loss=curr_price * 0.95,  # 5% stop
                suggested_take_profit=curr_price * 1.10, # 10% target
            )
        elif idx == 15:
            return StrategySignal(
                symbol=symbol,
                pipeline_id="pipeline_b_nifty",
                strategy_name=self.strategy_name,
                strategy_version=self.strategy_version,
                signal=SignalAction.SELL,
                signal_strength=0.80,
                prediction_horizon="1d",
                timestamp=ts,
                entry_reference_price=curr_price,
            )

        return StrategySignal(
            symbol=symbol,
            pipeline_id="pipeline_b_nifty",
            strategy_name=self.strategy_name,
            strategy_version=self.strategy_version,
            signal=SignalAction.HOLD,
            signal_strength=0.5,
            prediction_horizon="1d",
            timestamp=ts,
        )


@pytest.fixture
def sample_ohlcv_data():
    """Generates 30 synthetic daily OHLCV bars."""
    dates = pd.date_range("2026-01-01", periods=30, freq="B")
    # Upward trending prices: 100 -> 130
    close_prices = np.linspace(100.0, 130.0, 30)
    open_prices = close_prices - 0.5
    high_prices = close_prices + 1.5
    low_prices = close_prices - 1.5
    volume = np.full(30, 100_000.0)

    df = pd.DataFrame(
        {"open": open_prices, "high": high_prices, "low": low_prices, "close": close_prices, "volume": volume},
        index=dates,
    )
    return df


def test_backtest_engine_execution_flow(sample_ohlcv_data):
    """Tests end-to-end backtest run with MockTrendStrategy."""
    engine = BacktestEngine(initial_capital=100_000.0)
    strategy = MockTrendStrategy()

    report = engine.run_backtest(
        data=sample_ohlcv_data,
        strategy=strategy,
        symbol="TCS",
        use_decision_engine=False,  # Test direct execution flow
        use_risk_engine=False,
    )

    assert isinstance(report, BacktestReport)
    assert report.symbol == "TCS"
    assert report.total_bars == 30
    assert report.initial_capital == 100_000.0
    assert len(report.trades) >= 1

    report_dict = report.to_dict()
    assert "metrics" in report_dict
    assert "trades" in report_dict
    assert "execution_summary" in report_dict


def test_intrabar_stop_loss_trigger():
    """Tests that intrabar stop-loss triggers when bar low dips below stop."""
    simulator = PortfolioSimulator(initial_capital=100_000.0)
    # Simulate a position: 100 units @ 1000 INR with stop at 950 INR
    simulator.positions["TCS"] = {
        "units": 100,
        "average_price": 1000.0,
        "stop_loss": 950.0,
        "take_profit": 1100.0,
        "entry_bar": 0,
    }

    # Bar with dip below stop (low = 940)
    bar = pd.Series({"open": 980.0, "high": 990.0, "low": 940.0, "close": 960.0})
    exit_res = simulator.check_intrabar_exits(bar, symbol="TCS", bar_index=1)

    assert exit_res is not None
    exit_reason, exit_price = exit_res
    assert exit_reason == "STOP_LOSS"
    assert exit_price == 950.0


def test_intrabar_gap_down_stop():
    """Tests that a gap-down open below stop loss exits at the open price."""
    simulator = PortfolioSimulator(initial_capital=100_000.0)
    simulator.positions["TCS"] = {
        "units": 100,
        "average_price": 1000.0,
        "stop_loss": 950.0,
        "take_profit": 1100.0,
    }

    # Bar opens at 930 (gap down below 950 stop)
    bar = pd.Series({"open": 930.0, "high": 940.0, "low": 910.0, "close": 920.0})
    exit_res = simulator.check_intrabar_exits(bar, symbol="TCS", bar_index=1)

    assert exit_res is not None
    exit_reason, exit_price = exit_res
    assert exit_reason == "STOP_LOSS"
    assert exit_price == 930.0  # Conservative: fills at open (930), not stop price (950)


def test_benchmark_rejection_for_pipeline_a(sample_ohlcv_data):
    """Verifies that BenchmarkComparator strictly rejects Pipeline A."""
    engine = BacktestEngine()
    strategy = MockTrendStrategy()
    benchmark_series = sample_ohlcv_data["close"]

    with pytest.raises(ValueError, match="Cannot compare FI-2010 microstructure tick arrays directly"):
        engine.benchmark_comparator.compare(
            strategy_equity=sample_ohlcv_data["close"],
            benchmark_prices_or_equity=benchmark_series,
            pipeline_id="pipeline_a_fi2010",
        )
