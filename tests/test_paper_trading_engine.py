"""
Tests for MIRAI Integrated Paper Trading Engine (M14)
Validates engine lifecycle, bar stepping, replay orchestration, intrabar stops, and reporting.
"""

import pytest
import pandas as pd
from pathlib import Path

from src.paper_trading.paper_trading_engine import PaperTradingEngine
from src.paper_trading.paper_trading_schemas import SessionConfig, SessionStatus
from src.paper_trading.market_data_adapter import MarketDataAdapter
from src.paper_trading.paper_account import PaperAccount
from src.paper_trading.paper_portfolio import PaperPortfolio
from src.execution.execution_schemas import OrderRequest, OrderSide, OrderType


@pytest.fixture
def replay_df():
    dates = pd.date_range("2026-01-01", periods=10, freq="1D")
    return pd.DataFrame({
        "open": [100.0, 102.0, 101.0, 105.0, 104.0, 106.0, 108.0, 107.0, 110.0, 112.0],
        "high": [103.0, 104.0, 103.0, 107.0, 106.0, 109.0, 110.0, 109.0, 113.0, 115.0],
        "low": [99.0, 100.0, 99.0, 103.0, 102.0, 105.0, 106.0, 105.0, 108.0, 110.0],
        "close": [102.0, 101.0, 105.0, 104.0, 106.0, 108.0, 107.0, 110.0, 112.0, 114.0],
        "volume": [1000] * 10,
    }, index=dates)


def test_engine_initialization_and_stepping(replay_df, tmp_path):
    db_file = str(tmp_path / "paper_engine_test.db")
    adapter = MarketDataAdapter()
    adapter.load_replay_data(symbol="TCS", custom_df=replay_df)

    cfg = SessionConfig(session_name="StepTest", initial_capital=200_000.0, symbols=["TCS"])
    engine = PaperTradingEngine(
        session_config=cfg,
        market_adapter=adapter,
        db_path=db_file,
    )

    assert engine.session.status == SessionStatus.CREATED

    # Start and step 1 bar
    engine.start()
    assert engine.session.status == SessionStatus.RUNNING

    bar1 = engine.step_bar()
    assert bar1 is not None
    assert engine.session.bars_processed == 1
    assert len(engine.performance_tracker.snapshots) == 1

    # Replay 3 more bars
    bars_processed = engine.run_replay(num_bars=3)
    assert bars_processed == 3
    assert engine.session.bars_processed == 4


def test_intrabar_stop_loss_execution(tmp_path):
    db_file = str(tmp_path / "paper_stop_loss.db")
    dates = pd.date_range("2026-01-01", periods=3, freq="1D")
    df = pd.DataFrame({
        "open": [100.0, 102.0, 90.0],
        "high": [105.0, 104.0, 92.0],
        "low": [98.0, 100.0, 80.0],  # Bar 3 low plunges to 80.0
        "close": [102.0, 101.0, 85.0],
        "volume": [1000, 1000, 1000],
    }, index=dates)

    adapter = MarketDataAdapter()
    adapter.load_replay_data(symbol="TCS", custom_df=df)

    engine = PaperTradingEngine(
        market_adapter=adapter,
        db_path=db_file,
    )
    engine.start()

    # Step bar 1
    engine.step_bar()

    # Manually add an open position with a stop loss of 95.0
    engine.portfolio.add_or_update_position(
        symbol="TCS",
        units=50,
        entry_price=100.0,
        entry_time=dates[0],
        stop_loss=95.0,
    )
    # Deduct cash for this manual position and record active trade
    engine.account.process_buy_fill("TCS", units=50, execution_price=100.0, total_transaction_cost=25.0)
    engine.trade_manager.open_trade("TCS", quantity=50, entry_price=100.0, entry_time=dates[0], entry_costs=25.0, entry_slippage=0.0)

    # Step bar 2 (low = 100.0 > 95.0, no exit)
    engine.step_bar()
    assert engine.portfolio.get_position("TCS") is not None

    # Step bar 3 (low = 80.0 <= 95.0 -> stop loss hit!)
    engine.step_bar()
    # Position should now be liquidated
    assert engine.portfolio.get_position("TCS") is None
    closed_trades = engine.trade_manager.get_closed_trades()
    assert len(closed_trades) == 1
    assert closed_trades[0].exit_reason == "STOP_LOSS_HIT"


def test_emergency_stop_and_reporting(replay_df, tmp_path):
    db_file = str(tmp_path / "emergency_test.db")
    adapter = MarketDataAdapter()
    adapter.load_replay_data(symbol="INFY", custom_df=replay_df)

    engine = PaperTradingEngine(market_adapter=adapter, db_path=db_file)
    engine.start()
    engine.step_bar()

    # Trigger emergency stop
    engine.emergency_stop(reason="Abnormal market volatility detected")
    assert engine.account.circuit_breaker_state == "HALTED"
    assert len(engine.circuit_breaker_events) == 1
    assert engine.circuit_breaker_events[0]["event_type"] == "EMERGENCY_HALT"

    # Step bar should now be rejected due to HALTED state
    next_bar = engine.step_bar()
    assert next_bar is None

    # Generate Report
    report = engine.generate_report()
    assert report.session_name == engine.session.config.session_name
    assert len(report.circuit_breaker_events) == 1
    assert "EMERGENCY STOP" in report.to_summary_markdown() or "EMERGENCY_HALT" in report.to_summary_markdown()
