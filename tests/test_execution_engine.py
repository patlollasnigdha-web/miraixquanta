"""
Unit and Integration Tests for Intelligent Execution Engine (M12).
Tests Market, Limit, TWAP, VWAP execution styles, risk-blocked rejections,
liquidity-aware slicing, and execution quality reports.
"""

import pytest
import pandas as pd

from src.execution.execution_schemas import (
    OrderSide,
    OrderType,
    OrderStatus,
    OrderRequest,
    Order,
)
from src.execution.execution_engine import IntelligentExecutionEngine
from src.decision.decision_schemas import (
    InvestmentDecision,
    DecisionVerdict,
    DisplayLabel,
    RiskStatus,
    DecisionExplanation,
)
from src.risk_management.risk_engine import RiskManagementEngine, CircuitBreakerState


@pytest.fixture
def sample_market_bar():
    """Generates a sample daily OHLCV bar for TCS."""
    return pd.Series(
        {"open": 3500.0, "high": 3550.0, "low": 3480.0, "close": 3520.0, "volume": 500_000.0},
        name=pd.Timestamp("2026-03-30"),
    )


def test_market_order_execution(sample_market_bar):
    """Tests basic market order execution with slippage and costs."""
    engine = IntelligentExecutionEngine()
    req = OrderRequest(symbol="TCS", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=100)
    order = engine.submit_order(request=req, current_bar=sample_market_bar)

    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == 100
    assert order.remaining_quantity == 0
    assert order.average_price > 3500.0  # Slippage added to open price
    assert order.total_transaction_cost > 0.0
    assert len(order.slices) == 1

    report = engine.get_order_report(order)
    assert report.is_fully_filled
    assert report.slippage_bps > 0.0


def test_limit_order_execution_fill(sample_market_bar):
    """Tests that limit order fills when limit price is within bar range."""
    engine = IntelligentExecutionEngine()
    # Buy limit at 3490 (bar low is 3480, so touches limit price)
    req = OrderRequest(
        symbol="TCS",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=50,
        limit_price=3490.0,
    )
    order = engine.submit_order(request=req, current_bar=sample_market_bar)

    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == 50
    assert order.average_price <= 3490.0  # Enforces limit price cap


def test_limit_order_unfilled_expires(sample_market_bar):
    """Tests that limit order expires when limit price is not touched."""
    engine = IntelligentExecutionEngine()
    # Buy limit at 3450 (bar low is 3480 -> not touched)
    req = OrderRequest(
        symbol="TCS",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=50,
        limit_price=3450.0,
    )
    order = engine.submit_order(request=req, current_bar=sample_market_bar)

    assert order.status == OrderStatus.EXPIRED
    assert order.filled_quantity == 0
    assert order.remaining_quantity == 50


def test_twap_execution_slicing(sample_market_bar):
    """Tests TWAP order execution into chronological slices."""
    engine = IntelligentExecutionEngine()
    req = OrderRequest(
        symbol="TCS",
        side=OrderSide.BUY,
        order_type=OrderType.TWAP,
        quantity=100,
        execution_params={"num_slices": 4},
    )
    order = engine.submit_order(request=req, current_bar=sample_market_bar)

    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == 100
    assert len(order.slices) == 4
    assert sum(s.quantity for s in order.slices) == 100
    assert order.average_price > 0.0


def test_vwap_execution_volume_profile(sample_market_bar):
    """Tests VWAP order execution weighted by volume profile."""
    engine = IntelligentExecutionEngine()
    profile = [0.40, 0.20, 0.10, 0.30]
    req = OrderRequest(
        symbol="TCS",
        side=OrderSide.BUY,
        order_type=OrderType.VWAP,
        quantity=200,
    )
    order = engine.submit_order(request=req, current_bar=sample_market_bar, volume_profile=profile)

    assert order.status == OrderStatus.FILLED
    assert order.filled_quantity == 200
    assert len(order.slices) == len(profile)
    assert sum(s.quantity for s in order.slices) == 200


def test_execution_engine_rejects_risk_blocked_decision(sample_market_bar):
    """Verifies that an order with RISK_BLOCKED is immediately rejected."""
    engine = IntelligentExecutionEngine()
    decision = InvestmentDecision(
        symbol="TCS",
        pipeline_id="pipeline_b_nifty",
        timestamp=pd.Timestamp("2026-03-30"),
        verdict=DecisionVerdict.NO,
        display_label=DisplayLabel.NO_ACTION,
        action_type="OBSERVE",
        composite_score=20.0,
        confidence=0.8,
        investment_horizon="1d",
        entry_reference_price=3500.0,
        suggested_stop_loss=None,
        suggested_take_profit=None,
        factor_contributions={},
        factor_scores={},
        risk_status=RiskStatus.RISK_BLOCKED,  # BLOCKED!
        explanation=DecisionExplanation(verdict_rationale="Risk limit breached"),
    )

    order = engine.execute_decision(decision=decision, current_bar=sample_market_bar)
    assert order.status == OrderStatus.REJECTED
    assert "RISK_BLOCKED" in order.rejection_reason
    assert order.filled_quantity == 0


def test_execution_engine_rejects_on_halted_circuit_breaker(sample_market_bar):
    """Verifies that HALTED circuit breaker blocks execution."""
    engine = IntelligentExecutionEngine()
    risk_engine = RiskManagementEngine(initial_capital=1_000_000.0)
    risk_engine.circuit_breaker_state = CircuitBreakerState.HALTED

    decision = InvestmentDecision(
        symbol="TCS",
        pipeline_id="pipeline_b_nifty",
        timestamp=pd.Timestamp("2026-03-30"),
        verdict=DecisionVerdict.YES,
        display_label=DisplayLabel.BUY,
        action_type="ENTRY_LONG",
        composite_score=80.0,
        confidence=0.8,
        investment_horizon="1d",
        entry_reference_price=3500.0,
        suggested_stop_loss=3430.0,
        suggested_take_profit=3640.0,
        factor_contributions={},
        factor_scores={},
        risk_status=RiskStatus.RISK_APPROVED,
        explanation=DecisionExplanation(verdict_rationale="Strong signal"),
    )

    order = engine.execute_decision(decision=decision, current_bar=sample_market_bar, risk_engine=risk_engine)
    assert order.status == OrderStatus.REJECTED
    assert "Circuit Breaker HALTED" in order.rejection_reason
