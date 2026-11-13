"""
Tests for MIRAI Paper State Manager & SQLite Persistence (M14)
Validates transactional persistence, schema migrations, state recovery, and database resets.
"""

import pytest
import pandas as pd
from pathlib import Path

from src.paper_trading.paper_state_manager import PaperStateManager, SCHEMA_VERSION
from src.paper_trading.trading_session import TradingSession
from src.paper_trading.paper_trading_schemas import SessionConfig, SessionStatus
from src.paper_trading.paper_account import PaperAccount
from src.paper_trading.paper_portfolio import PaperPortfolio
from src.execution.execution_schemas import Order, OrderRequest, OrderSide, OrderStatus, OrderType
from src.backtesting.trade_simulator import Trade


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_paper.db"
    return str(db_file)


def test_schema_initialization(temp_db):
    mgr = PaperStateManager(db_path=temp_db)
    assert Path(temp_db).exists()

    with mgr._get_connection() as conn:
        meta = conn.execute("SELECT version FROM schema_meta").fetchone()
        assert meta["version"] == SCHEMA_VERSION


def test_save_and_restore_session_state(temp_db):
    mgr = PaperStateManager(db_path=temp_db)

    # 1. Setup session components
    cfg = SessionConfig(session_id="SESS_TEST_1", session_name="RecoveryTest", initial_capital=1_000_000.0, symbols=["TCS"])
    session = TradingSession(cfg)
    session.start()

    account = PaperAccount(account_id="ACC_1", initial_capital=1_000_000.0)
    account.available_cash = 950_000.0
    account.invested_capital = 50_000.0
    account.realized_pnl = 2_500.0

    portfolio = PaperPortfolio()
    now = pd.Timestamp("2026-01-01 10:00:00")
    portfolio.add_or_update_position(symbol="TCS", units=50, entry_price=1000.0, entry_time=now, stop_loss=950.0)

    # Orders
    req = OrderRequest(symbol="TCS", side=OrderSide.BUY, quantity=50, order_type=OrderType.MARKET, created_at=now)
    order = Order(request=req)
    order.status = OrderStatus.FILLED
    order.filled_quantity = 50
    order.average_price = 1000.0
    order.total_transaction_cost = 50.0

    # Trades
    trade = Trade(
        trade_id="TRD_001",
        symbol="TCS",
        direction="LONG",
        quantity=50,
        entry_time=now,
        entry_price=1000.0,
        entry_costs=10.0,
        entry_slippage=0.0,
        exit_time=now + pd.Timedelta(hours=2),
        exit_price=1050.0,
        gross_pnl=2500.0,
        net_pnl=2450.0,
        exit_reason="PROFIT_TARGET",
        bars_held=12,
        is_closed=True,
    )

    # 2. Save State
    mgr.save_session_state(
        session=session,
        account=account,
        portfolio=portfolio,
        orders=[order],
        trades=[trade],
    )

    # 3. Restore State
    restored = mgr.restore_session_state("SESS_TEST_1")
    assert restored is not None
    r_sess, r_acc, r_port, r_orders, r_trades = restored

    assert r_sess.session_id == "SESS_TEST_1"
    assert r_sess.status == SessionStatus.RUNNING

    assert r_acc.available_cash == 950_000.0
    assert r_acc.invested_capital == 50_000.0
    assert r_acc.realized_pnl == 2_500.0

    assert len(r_port.get_all_positions()) == 1
    pos = r_port.get_position("TCS")
    assert pos.units == 50
    assert pos.average_entry_price == 1000.0
    assert pos.stop_loss == 950.0

    assert len(r_orders) == 1
    assert r_orders[0].order_id == order.order_id
    assert r_orders[0].status == OrderStatus.FILLED

    assert len(r_trades) == 1
    assert r_trades[0].trade_id == "TRD_001"
    assert r_trades[0].net_pnl == 2450.0
    assert r_trades[0].is_closed is True


def test_reset_database_safeguard(temp_db):
    mgr = PaperStateManager(db_path=temp_db)
    cfg = SessionConfig(session_id="SESS_RESET")
    session = TradingSession(cfg)
    account = PaperAccount()
    portfolio = PaperPortfolio()

    mgr.save_session_state(session, account, portfolio, [], [])
    assert mgr.restore_session_state("SESS_RESET") is not None

    # Reset without confirm should do nothing
    res_false = mgr.reset_database(confirm=False)
    assert res_false is False
    assert mgr.restore_session_state("SESS_RESET") is not None

    # Reset with confirm should clear
    res_true = mgr.reset_database(confirm=True)
    assert res_true is True
    assert mgr.restore_session_state("SESS_RESET") is None
