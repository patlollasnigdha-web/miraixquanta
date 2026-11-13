"""
Tests for MIRAI Paper Account Management (M14)
Validates virtual cash accounting, buying power, reservations, fills, and constraints.
"""

import pytest
import pandas as pd
from src.paper_trading.paper_account import PaperAccount
from src.paper_trading.paper_trading_schemas import PaperAccountState


def test_account_initialization():
    acc = PaperAccount(account_id="TEST_ACC", initial_capital=500_000.0, cash_reserve_pct=0.10)
    assert acc.account_id == "TEST_ACC"
    assert acc.initial_capital == 500_000.0
    assert acc.available_cash == 500_000.0
    assert acc.reserved_cash == 0.0
    assert acc.invested_capital == 0.0
    assert acc.total_cash == 500_000.0
    assert acc.total_equity == 500_000.0
    # Reserve is 10% of 500,000 = 50,000; buying power = 450,000
    assert acc.buying_power == 450_000.0


def test_cash_reservation_and_release():
    acc = PaperAccount(initial_capital=100_000.0)
    # Reserve 20,000
    success = acc.reserve_cash(20_000.0)
    assert success is True
    assert acc.available_cash == 80_000.0
    assert acc.reserved_cash == 20_000.0
    assert acc.total_cash == 100_000.0

    # Attempt to reserve more than available (90,000 > 80,000)
    fail = acc.reserve_cash(90_000.0)
    assert fail is False
    assert acc.available_cash == 80_000.0

    # Release 15,000
    acc.release_reserved_cash(15_000.0)
    assert acc.available_cash == 95_000.0
    assert acc.reserved_cash == 5_000.0


def test_buy_fill_processing():
    acc = PaperAccount(initial_capital=100_000.0)
    # Buy 100 units @ 500 = 50,000, fee = 100 -> cash spent = 50,100
    acc.process_buy_fill(
        symbol="TCS",
        units=100,
        execution_price=500.0,
        total_transaction_cost=100.0,
    )
    assert acc.available_cash == 49_900.0
    assert acc.invested_capital == 50_000.0
    assert acc.total_cash == 49_900.0


def test_buy_fill_insufficient_cash():
    acc = PaperAccount(initial_capital=10_000.0, allow_margin=False)
    # Attempt to buy 100 units @ 200 = 20,000
    with pytest.raises(ValueError, match="Insufficient cash"):
        acc.process_buy_fill(
            symbol="INFY",
            units=100,
            execution_price=200.0,
            total_transaction_cost=50.0,
        )


def test_sell_fill_processing_and_pnl():
    acc = PaperAccount(initial_capital=100_000.0)
    # 1. Buy 50 units @ 1000 = 50,000 (fee 50)
    acc.process_buy_fill(symbol="RELIANCE", units=50, execution_price=1000.0, total_transaction_cost=50.0)
    assert acc.available_cash == 49_950.0
    assert acc.invested_capital == 50_000.0

    # 2. Sell 50 units @ 1100 = 55,000 (fee 55)
    # Net proceeds = 54,945; cost basis = 50,000 -> PnL = +4,945
    pnl = acc.process_sell_fill(
        symbol="RELIANCE",
        units=50,
        execution_price=1100.0,
        total_transaction_cost=55.0,
        cost_basis=50_000.0,
    )
    assert pnl == 4945.0
    assert acc.realized_pnl == 4945.0
    assert acc.invested_capital == 0.0
    assert acc.available_cash == 49_950.0 + 54_945.0


def test_mark_to_market_valuation():
    acc = PaperAccount(initial_capital=100_000.0)
    acc.process_buy_fill("TCS", units=10, execution_price=1000.0, total_transaction_cost=10.0)
    # available cash: 89,990; invested: 10,000
    # Portfolio market value rises to 12,000
    acc.update_market_valuation(portfolio_market_value=12_000.0)
    assert acc.portfolio_market_value == 12_000.0
    assert acc.total_equity == 89_990.0 + 12_000.0
    assert acc.unrealized_pnl == 2_000.0  # 12,000 - 10,000


def test_account_state_and_reset():
    acc = PaperAccount(initial_capital=100_000.0)
    acc.process_buy_fill("TCS", units=10, execution_price=100.0, total_transaction_cost=5.0)

    state = acc.get_state()
    assert isinstance(state, PaperAccountState)
    assert state.available_cash == 98_995.0

    # Non-confirmed reset should fail
    assert acc.reset(confirm=False) is False
    assert acc.available_cash == 98_995.0

    # Confirmed reset should succeed
    assert acc.reset(confirm=True) is True
    assert acc.available_cash == 100_000.0
    assert acc.invested_capital == 0.0
    assert acc.realized_pnl == 0.0
