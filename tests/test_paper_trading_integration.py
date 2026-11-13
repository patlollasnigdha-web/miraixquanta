"""
Tests for MIRAI End-to-End Paper Trading Integration (M14)
Validates full pipeline workflow: MarketDataAdapter -> MomentumStrategy ->
InvestmentDecisionEngine -> DynamicRiskEngine -> IntelligentExecutionEngine ->
PaperAccount -> PaperPortfolio -> SQLite Persistence -> PaperTradingReport.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from src.strategies.momentum_strategy import MomentumStrategy
from src.decision.decision_engine import InvestmentDecisionEngine
from src.risk_management.risk_engine import RiskManagementEngine
from src.execution.execution_engine import IntelligentExecutionEngine
from src.paper_trading.paper_trading_engine import PaperTradingEngine
from src.paper_trading.paper_trading_schemas import SessionConfig, SessionStatus
from src.paper_trading.market_data_adapter import MarketDataAdapter
from src.paper_trading.paper_state_manager import PaperStateManager


@pytest.fixture
def trending_ohlcv():
    """Generates 120 bars of synthetic upward trending OHLCV data."""
    np.random.seed(42)
    n = 120
    dates = pd.date_range("2025-01-01", periods=n, freq="1D")

    # Generate upward trending prices with low noise
    trend = np.linspace(100.0, 180.0, n)
    noise = np.random.normal(0, 0.5, n)
    close_prices = trend + noise

    high_prices = close_prices + np.random.uniform(0.5, 2.0, n)
    low_prices = close_prices - np.random.uniform(0.5, 2.0, n)
    open_prices = close_prices - np.random.uniform(-0.5, 0.5, n)
    volumes = np.random.randint(10000, 50000, n)

    df = pd.DataFrame({
        "open": open_prices,
        "high": high_prices,
        "low": low_prices,
        "close": close_prices,
        "volume": volumes,
    }, index=dates)
    return df


def test_full_paper_trading_pipeline_integration(trending_ohlcv, tmp_path):
    db_path = str(tmp_path / "integration_paper.db")

    # 1. Market Data Adapter
    adapter = MarketDataAdapter(pipeline_id="pipeline_b_nifty")
    adapter.load_replay_data(symbol="TCS", custom_df=trending_ohlcv)

    # 2. Engines from upstream batches
    strategy = MomentumStrategy(fast_window=10, slow_window=30, rsi_window=14)
    decision_engine = InvestmentDecisionEngine()
    risk_engine = RiskManagementEngine()
    execution_engine = IntelligentExecutionEngine()

    # 3. Paper Trading Engine
    cfg = SessionConfig(
        session_id="SESS_INTEGRATION_01",
        session_name="FullEndToEndPaperTest",
        initial_capital=500_000.0,
        symbols=["TCS"],
    )
    engine = PaperTradingEngine(
        session_config=cfg,
        market_adapter=adapter,
        strategy=strategy,
        decision_engine=decision_engine,
        risk_engine=risk_engine,
        execution_engine=execution_engine,
        db_path=db_path,
        auto_persist=True,
    )

    # 4. Run entire replay
    bars_processed = engine.run_replay()
    assert bars_processed == len(trending_ohlcv)
    assert engine.session.status == SessionStatus.STOPPED

    # 5. Check performance tracking
    eq_curve = engine.performance_tracker.get_equity_curve()
    assert len(eq_curve) == len(trending_ohlcv)
    assert eq_curve.iloc[0] > 0

    # 6. Check accounting invariants
    assert engine.account.total_cash >= 0.0
    assert engine.account.total_equity > 0.0
    assert engine.account.available_cash + engine.account.reserved_cash == engine.account.total_cash

    # 7. Check reports
    report = engine.generate_report()
    assert report.session_id == "SESS_INTEGRATION_01"
    assert report.status == "STOPPED"
    assert report.initial_capital == 500_000.0
    md = report.to_summary_markdown()
    assert "# MIRAI Paper Trading Report" in md
    assert "Capital & Financial Performance" in md

    # 8. Check persistence in SQLite
    state_mgr = PaperStateManager(db_path=db_path)
    restored = state_mgr.restore_session_state("SESS_INTEGRATION_01")
    assert restored is not None
    r_sess, r_acc, r_port, r_orders, r_trades = restored
    assert r_sess.session_id == "SESS_INTEGRATION_01"
    assert r_acc.initial_capital == 500_000.0
    assert len(r_orders) == len(engine.order_manager.get_all_orders())
