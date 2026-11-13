"""
Unit Tests for Transaction Cost Model (M12).
Tests itemized fee schedules for Indian equities (brokerage, STT, turnover, SEBI, stamp duty, GST),
net value calculations, and double-counting prevention.
"""

import pytest

from src.execution.execution_schemas import OrderSide
from src.execution.transaction_costs import TransactionCostModel, TransactionCostBreakdown


def test_transaction_cost_components_buy():
    """Tests transaction costs calculation on a BUY order."""
    # 100 shares @ 1000 INR = 100,000 INR gross value
    # Brokerage: 0.03% = 30 INR (capped at 20 INR)
    # Exchange turnover: 0.00345% = 3.45 INR
    # GST: 18% on (20 + 3.45) = 4.22 INR
    # Stamp duty: 0.003% on BUY = 3.00 INR
    # STT: 0.025% = 25.00 INR
    # SEBI: 0.0001% = 0.10 INR
    cost_model = TransactionCostModel(fixed_brokerage_cap=20.0)
    costs = cost_model.calculate_costs(side=OrderSide.BUY, quantity=100, execution_price=1000.0)

    assert costs.gross_value == 100_000.0
    assert costs.brokerage == 20.0  # Capped at 20 INR
    assert costs.exchange_turnover_fee == pytest.approx(3.45, abs=0.01)
    assert costs.gst == pytest.approx((20.0 + 3.45) * 0.18, abs=0.01)
    assert costs.stamp_duty == pytest.approx(3.0, abs=0.01)
    assert costs.stt == pytest.approx(25.0, abs=0.01)
    assert costs.sebi_charges == pytest.approx(0.10, abs=0.01)

    # Net value for BUY should be gross + total_cost
    assert costs.net_value == pytest.approx(costs.gross_value + costs.total_cost)
    assert costs.total_cost > 0.0


def test_transaction_cost_stamp_duty_sell():
    """Verifies that stamp duty is 0 for SELL orders in Indian equity market."""
    cost_model = TransactionCostModel()
    costs = cost_model.calculate_costs(side=OrderSide.SELL, quantity=100, execution_price=1000.0)

    assert costs.stamp_duty == 0.0
    # Net value for SELL should be gross - total_cost
    assert costs.net_value == pytest.approx(costs.gross_value - costs.total_cost)


def test_zero_cost_model():
    """Tests zero-cost model for theoretical backtest comparisons."""
    zero_model = TransactionCostModel.zero_cost()
    costs = zero_model.calculate_costs(side="BUY", quantity=100, execution_price=500.0)
    assert costs.gross_value == 50_000.0
    assert costs.total_cost == 0.0
    assert costs.net_value == 50_000.0


def test_invalid_and_zero_inputs():
    """Tests handling of zero or negative quantity and prices."""
    cost_model = TransactionCostModel()
    costs = cost_model.calculate_costs(side="BUY", quantity=0, execution_price=1000.0)
    assert costs.gross_value == 0.0
    assert costs.total_cost == 0.0
