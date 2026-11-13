"""
Unit Tests for Execution Schemas and Order Lifecycle State Machine (M12).
Tests valid and invalid order transitions, request validation, and serialization.
"""

import pytest
import pandas as pd

from src.execution.execution_schemas import (
    OrderSide,
    OrderType,
    OrderStatus,
    OrderRequest,
    Order,
    ExecutionResult,
    InvalidOrderStateError,
    validate_status_transition,
)


def test_order_request_validation():
    """Tests validation of OrderRequest parameters."""
    # Valid MARKET order
    req = OrderRequest(symbol="TCS", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
    assert req.symbol == "TCS"
    assert req.side == OrderSide.BUY
    assert req.order_type == OrderType.MARKET
    assert req.quantity == 100

    # Non-positive quantity raises ValueError
    with pytest.raises(ValueError, match="Requested quantity must be positive"):
        OrderRequest(symbol="TCS", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0)

    # LIMIT order without limit_price raises ValueError
    with pytest.raises(ValueError, match="Limit orders must specify a positive limit_price"):
        OrderRequest(symbol="TCS", side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=50, limit_price=None)

    # String parsing
    req_str = OrderRequest(symbol="INFY", side="sell", order_type="limit", quantity=25, limit_price=1500.0)
    assert req_str.side == OrderSide.SELL
    assert req_str.order_type == OrderType.LIMIT


def test_order_valid_lifecycle_transitions():
    """Tests authorized lifecycle transitions from CREATED through to FILLED."""
    req = OrderRequest(symbol="RELIANCE", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
    order = Order(request=req)
    assert order.status == OrderStatus.CREATED
    assert order.remaining_quantity == 100
    assert order.filled_quantity == 0

    # CREATED -> VALIDATED
    order.transition_to(OrderStatus.VALIDATED, "Passed risk pre-checks")
    assert order.status == OrderStatus.VALIDATED

    # VALIDATED -> SUBMITTED
    order.transition_to(OrderStatus.SUBMITTED, "Sent to execution simulator")
    assert order.status == OrderStatus.SUBMITTED

    # SUBMITTED -> PARTIALLY_FILLED
    order.transition_to(OrderStatus.PARTIALLY_FILLED, "Partial fill of 50 units")
    assert order.status == OrderStatus.PARTIALLY_FILLED

    # PARTIALLY_FILLED -> FILLED
    order.transition_to(OrderStatus.FILLED, "Final fill of 50 units")
    assert order.status == OrderStatus.FILLED
    assert order.is_complete


def test_order_invalid_lifecycle_transitions():
    """Tests that unauthorized state transitions raise InvalidOrderStateError."""
    req = OrderRequest(symbol="HDFCBANK", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=50)
    order = Order(request=req)

    # Cannot skip directly from CREATED to FILLED
    with pytest.raises(InvalidOrderStateError, match="Illegal order lifecycle transition"):
        order.transition_to(OrderStatus.FILLED)

    # Advance to terminal state
    order.transition_to(OrderStatus.VALIDATED)
    order.transition_to(OrderStatus.SUBMITTED)
    order.transition_to(OrderStatus.FILLED)

    # Cannot transition out of terminal state FILLED
    with pytest.raises(InvalidOrderStateError, match="Illegal order lifecycle transition"):
        order.transition_to(OrderStatus.SUBMITTED)


def test_order_to_dict_serialization():
    """Tests Order serialization to dictionary."""
    req = OrderRequest(symbol="TCS", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
    order = Order(request=req)
    d = order.to_dict()
    assert d["symbol"] == "TCS"
    assert d["side"] == "BUY"
    assert d["requested_quantity"] == 100
    assert d["status"] == "CREATED"
    assert "cost_breakdown" in d
