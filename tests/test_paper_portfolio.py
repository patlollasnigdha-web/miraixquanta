"""
Tests for MIRAI Paper Portfolio Management (M14)
Validates virtual position holdings, weighted entry prices, cost basis, and valuations.
"""

import pytest
import pandas as pd
from src.paper_trading.paper_portfolio import PaperPortfolio


def test_portfolio_add_and_weighted_average():
    portfolio = PaperPortfolio()
    now = pd.Timestamp.now()

    # Initial position: 10 units @ 100
    pos = portfolio.add_or_update_position(
        symbol="TCS",
        units=10,
        entry_price=100.0,
        entry_time=now,
        stop_loss=90.0,
        take_profit=120.0,
    )
    assert pos.symbol == "TCS"
    assert pos.units == 10
    assert pos.average_entry_price == 100.0
    assert pos.cost_basis == 1000.0
    assert pos.stop_loss == 90.0
    assert pos.take_profit == 120.0

    # Add 10 more units @ 200 -> Average price should be (1000 + 2000) / 20 = 150
    pos2 = portfolio.add_or_update_position(
        symbol="TCS",
        units=10,
        entry_price=200.0,
        entry_time=now,
    )
    assert pos2.units == 20
    assert pos2.average_entry_price == 150.0
    assert pos2.cost_basis == 3000.0
    # Stop loss and take profit retained
    assert pos2.stop_loss == 90.0
    assert pos2.take_profit == 120.0


def test_partial_and_full_liquidation():
    portfolio = PaperPortfolio()
    now = pd.Timestamp.now()

    portfolio.add_or_update_position("INFY", units=30, entry_price=100.0, entry_time=now)
    assert portfolio.get_position("INFY").units == 30

    # Partially sell 10 units
    sold_units, cost_basis = portfolio.reduce_or_close_position("INFY", units_to_sell=10)
    assert sold_units == 10
    assert cost_basis == 1000.0
    pos = portfolio.get_position("INFY")
    assert pos is not None
    assert pos.units == 20
    assert pos.cost_basis == 2000.0

    # Liquidate remaining (request 50, but only 20 held)
    sold_remaining, cost_basis_rem = portfolio.reduce_or_close_position("INFY", units_to_sell=50)
    assert sold_remaining == 20
    assert cost_basis_rem == 2000.0
    assert portfolio.get_position("INFY") is None


def test_mark_prices_and_unrealized_pnl():
    portfolio = PaperPortfolio()
    now = pd.Timestamp.now()

    portfolio.add_or_update_position("TCS", units=10, entry_price=100.0, entry_time=now)
    portfolio.add_or_update_position("INFY", units=20, entry_price=50.0, entry_time=now)

    assert portfolio.total_cost_basis == 1000.0 + 1000.0  # 2000.0
    assert portfolio.total_market_value == 2000.0
    assert portfolio.total_unrealized_pnl == 0.0

    # Re-mark prices: TCS -> 120 (+200), INFY -> 45 (-100)
    portfolio.mark_prices({"TCS": 120.0, "INFY": 45.0})

    assert portfolio.get_position("TCS").current_price == 120.0
    assert portfolio.get_position("TCS").unrealized_pnl == 200.0
    assert portfolio.get_position("INFY").current_price == 45.0
    assert portfolio.get_position("INFY").unrealized_pnl == -100.0

    assert portfolio.total_market_value == (10 * 120.0) + (20 * 45.0)  # 1200 + 900 = 2100.0
    assert portfolio.total_unrealized_pnl == 100.0


def test_clear_portfolio():
    portfolio = PaperPortfolio()
    portfolio.add_or_update_position("TCS", units=10, entry_price=100.0, entry_time=pd.Timestamp.now())
    assert len(portfolio.get_all_positions()) == 1

    portfolio.clear()
    assert len(portfolio.get_all_positions()) == 0
    assert portfolio.total_market_value == 0.0
