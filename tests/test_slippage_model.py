"""
Unit Tests for Slippage Models (M12).
Tests Fixed Bps, Volatility-Adjusted, Volume-Sensitive (Almgren-Chriss),
and Composite slippage models. Verifies non-zero penalty and directional impact.
"""

import pytest

from src.execution.execution_schemas import OrderSide
from src.execution.slippage_model import (
    FixedBpsSlippageModel,
    VolatilityAdjustedSlippageModel,
    VolumeSensitiveSlippageModel,
    CompositeSlippageModel,
)


def test_fixed_bps_slippage_direction():
    """Tests that BUY orders increase execution price and SELL orders decrease price."""
    model = FixedBpsSlippageModel(default_bps=2.0)
    ref_price = 1000.0

    # BUY: 2 bps penalty = +0.02% -> 1000.20
    buy_res = model.calculate_slippage(ref_price, side=OrderSide.BUY, quantity=100)
    assert buy_res.execution_price > ref_price
    assert buy_res.execution_price == pytest.approx(1000.20)
    assert buy_res.slippage_bps == 2.0
    assert buy_res.total_slippage_cost == pytest.approx(0.20 * 100)

    # SELL: 2 bps penalty = -0.02% -> 999.80
    sell_res = model.calculate_slippage(ref_price, side=OrderSide.SELL, quantity=100)
    assert sell_res.execution_price < ref_price
    assert sell_res.execution_price == pytest.approx(999.80)


def test_volatility_adjusted_slippage():
    """Tests that elevated volatility scales up execution slippage."""
    model = VolatilityAdjustedSlippageModel(base_bps=2.0, baseline_annual_vol=0.15)
    ref_price = 500.0

    # Normal vol (15%) -> approx base 2.0 bps
    res_normal = model.calculate_slippage(ref_price, side="BUY", quantity=50, volatility=0.15)
    assert res_normal.slippage_bps == pytest.approx(2.0)

    # High vol (30% = 2x baseline) -> 4.0 bps
    res_high_vol = model.calculate_slippage(ref_price, side="BUY", quantity=50, volatility=0.30)
    assert res_high_vol.slippage_bps == pytest.approx(4.0)
    assert res_high_vol.execution_price > res_normal.execution_price

    # Missing vol -> conservative fallback
    res_missing = model.calculate_slippage(ref_price, side="BUY", quantity=50, volatility=None)
    assert res_missing.origin == "CONSERVATIVE_FALLBACK"
    assert res_missing.slippage_bps >= 2.0


def test_volume_sensitive_slippage():
    """Tests that larger order relative to daily volume incurs higher market impact."""
    model = VolumeSensitiveSlippageModel(base_bps=2.0, impact_coefficient=0.10)
    ref_price = 100.0
    daily_vol = 100_000.0

    # Small order (100 shares = 0.1% participation)
    res_small = model.calculate_slippage(ref_price, side="BUY", quantity=100, daily_volume=daily_vol)

    # Large order (10,000 shares = 10% participation)
    res_large = model.calculate_slippage(ref_price, side="BUY", quantity=10_000, daily_volume=daily_vol)

    assert res_large.slippage_bps > res_small.slippage_bps
    assert res_large.total_slippage_cost > res_small.total_slippage_cost

    # Missing volume fallback
    res_no_vol = model.calculate_slippage(ref_price, side="BUY", quantity=500, daily_volume=None)
    assert res_no_vol.origin == "CONSERVATIVE_FALLBACK"


def test_never_zero_slippage():
    """Verifies that slippage is never silently assumed to be zero."""
    composite = CompositeSlippageModel(base_bps=2.0)
    res = composite.calculate_slippage(100.0, side="BUY", quantity=10, daily_volume=None, volatility=None)
    assert res.slippage_bps > 0.0
    assert res.slippage_amount > 0.0
