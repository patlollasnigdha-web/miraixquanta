"""
Tests for MIRAI Paper Order Manager & Idempotency Engine (M14)
Validates duplicate rejection, pre-trade cash reservation, cancellation, and execution integration.
"""

import pytest
import pandas as pd
from src.paper_trading.paper_account import PaperAccount
from src.paper_trading.paper_order_manager import PaperOrderManager
from src.execution.execution_schemas import OrderRequest, OrderSide, OrderStatus, OrderType


def test_order_placement_and_idempotency_guard():
    acc = PaperAccount(initial_capital=500_000.0)
    mgr = PaperOrderManager(account=acc)

    now = pd.Timestamp("2026-01-01 10:00:00")
    bar = pd.Series({"open": 100.0, "high": 105.0, "low": 99.0, "close": 102.0, "volume": 10000})

    req1 = OrderRequest(
        symbol="TCS",
        side=OrderSide.BUY,
        quantity=50,
        order_type=OrderType.MARKET,
        created_at=now,
        strategy_id="TEST_STRAT",
    )

    # First placement succeeds
    order1 = mgr.place_order(req1, current_bar=bar)
    assert order1.status == OrderStatus.FILLED
    assert order1.filled_quantity == 50

    # Duplicate placement with identical intent should be rejected by idempotency key
    req2 = OrderRequest(
        symbol="TCS",
        side=OrderSide.BUY,
        quantity=50,
        order_type=OrderType.MARKET,
        created_at=now,
        strategy_id="TEST_STRAT",
    )
    order2 = mgr.place_order(req2, current_bar=bar)
    assert order2.status == OrderStatus.REJECTED
    assert "Duplicate order intent" in str(order2.rejection_reason)


def test_pre_trade_cash_reservation_for_limit_order():
    acc = PaperAccount(initial_capital=20_000.0)
    mgr = PaperOrderManager(account=acc)

    now = pd.Timestamp("2026-01-01 10:00:00")
    # Current bar price is 105, limit is 90 -> will not fill immediately
    bar = pd.Series({"open": 105.0, "high": 110.0, "low": 104.0, "close": 105.0, "volume": 10000})

    req = OrderRequest(
        symbol="INFY",
        side=OrderSide.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        limit_price=90.0,
        time_in_force="GTC",
        created_at=now,
    )

    order = mgr.place_order(req, current_bar=bar)
    assert order.status == OrderStatus.SUBMITTED
    # 100 * 90 * 1.002 = 9,018 reserved
    assert acc.reserved_cash > 9000.0
    assert acc.available_cash < 11_000.0

    # Cancel order -> reserved cash should be released back to available
    success = mgr.cancel_order(order.order_id, reason="User cancelled")
    assert success is True
    assert order.status == OrderStatus.CANCELLED
    assert acc.reserved_cash == 0.0
    assert acc.available_cash == 20_000.0


def test_order_rejection_insufficient_cash():
    acc = PaperAccount(initial_capital=5_000.0)
    mgr = PaperOrderManager(account=acc)

    now = pd.Timestamp.now()
    bar = pd.Series({"open": 200.0, "high": 205.0, "low": 195.0, "close": 200.0, "volume": 1000})

    # Needs ~20,000 INR, but account only has 5,000 INR
    req = OrderRequest(
        symbol="SBIN",
        side=OrderSide.BUY,
        quantity=100,
        order_type=OrderType.MARKET,
        created_at=now,
    )
    order = mgr.place_order(req, current_bar=bar)
    assert order.status == OrderStatus.REJECTED
    assert "Insufficient available cash" in str(order.rejection_reason)


def test_order_retrieval_methods():
    acc = PaperAccount(initial_capital=100_000.0)
    mgr = PaperOrderManager(account=acc)
    bar = pd.Series({"open": 100.0, "high": 105.0, "low": 95.0, "close": 100.0, "volume": 1000})

    req = OrderRequest(symbol="TCS", side=OrderSide.BUY, quantity=10, order_type=OrderType.MARKET)
    order = mgr.place_order(req, current_bar=bar)

    assert mgr.get_order(order.order_id) is not None
    assert len(mgr.get_all_orders()) == 1
    assert len(mgr.get_open_orders()) == 0  # Market order filled immediately
