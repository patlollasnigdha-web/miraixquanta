"""
MIRAI — Slippage Modelling Engine (M12)
Provides realistic, conservative, and mathematically rigorous execution slippage models.
Supports Fixed Bps, Volatility-Adjusted, Volume-Sensitive (Almgren-Chriss),
and Composite models. Never silently assumes zero slippage.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.execution.execution_schemas import OrderSide

logger = get_logger("SlippageModel")


@dataclass
class SlippageResult:
    """Standardized output structure for execution slippage."""
    execution_price: float
    reference_price: float
    slippage_amount: float     # In currency units (INR) per share
    slippage_bps: float        # Basis points (1 bp = 0.01%)
    total_slippage_cost: float # Total impact in INR (slippage_amount * quantity)
    method: str                # 'FIXED_BPS', 'VOLATILITY_ADJUSTED', 'VOLUME_SENSITIVE', 'COMPOSITE'
    origin: str                # 'SIMULATED_MODEL', 'HISTORICAL_ESTIMATE', 'CONSERVATIVE_FALLBACK'
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_price": round(self.execution_price, 4),
            "reference_price": round(self.reference_price, 4),
            "slippage_amount": round(self.slippage_amount, 4),
            "slippage_bps": round(self.slippage_bps, 2),
            "total_slippage_cost": round(self.total_slippage_cost, 2),
            "method": self.method,
            "origin": self.origin,
            "notes": self.notes,
        }


class BaseSlippageModel(ABC):
    """Abstract base class for all execution slippage models."""

    @abstractmethod
    def calculate_slippage(
        self,
        reference_price: float,
        side: Union[OrderSide, str],
        quantity: int,
        daily_volume: Optional[float] = None,
        volatility: Optional[float] = None,
    ) -> SlippageResult:
        """Computes execution price and slippage for an order."""
        pass


class FixedBpsSlippageModel(BaseSlippageModel):
    """
    Fixed basis-point slippage model.
    Applies a constant basis-point penalty (default 2.0 bps = 0.02%).
    """

    def __init__(self, default_bps: Optional[float] = None):
        cfg = get_config()
        self.default_bps = (
            default_bps
            if default_bps is not None
            else cfg.get("execution.default_slippage_bps", 2.0)
        )
        if self.default_bps <= 0.0:
            logger.warning("Fixed slippage initialized with non-positive bps (%f). Floor of 0.5 bps enforced.", self.default_bps)
            self.default_bps = 0.5

    def calculate_slippage(
        self,
        reference_price: float,
        side: Union[OrderSide, str],
        quantity: int,
        daily_volume: Optional[float] = None,
        volatility: Optional[float] = None,
    ) -> SlippageResult:
        side_str = side.value if isinstance(side, OrderSide) else str(side).upper()
        slip_frac = self.default_bps / 10_000.0
        slip_amount = reference_price * slip_frac

        if side_str == "BUY":
            exec_price = reference_price + slip_amount
        else:
            exec_price = max(0.01, reference_price - slip_amount)

        total_cost = slip_amount * quantity
        return SlippageResult(
            execution_price=exec_price,
            reference_price=reference_price,
            slippage_amount=slip_amount,
            slippage_bps=self.default_bps,
            total_slippage_cost=total_cost,
            method="FIXED_BPS",
            origin="SIMULATED_MODEL",
            notes=f"Fixed {self.default_bps:.1f} bps penalty",
        )


class VolatilityAdjustedSlippageModel(BaseSlippageModel):
    """
    Slippage scaled dynamically by market volatility.
    In volatile market conditions, market makers widen spreads resulting in higher slippage.
    """

    def __init__(
        self,
        base_bps: float = 2.0,
        baseline_annual_vol: float = 0.15,
        vol_exponent: float = 1.0,
    ):
        self.base_bps = base_bps
        self.baseline_vol = baseline_annual_vol
        self.vol_exponent = vol_exponent

    def calculate_slippage(
        self,
        reference_price: float,
        side: Union[OrderSide, str],
        quantity: int,
        daily_volume: Optional[float] = None,
        volatility: Optional[float] = None,
    ) -> SlippageResult:
        side_str = side.value if isinstance(side, OrderSide) else str(side).upper()

        if volatility is None or volatility <= 0.0:
            # Conservative fallback assumption when volatility data is missing
            effective_bps = self.base_bps * 1.5
            origin = "CONSERVATIVE_FALLBACK"
            note = "Volatility missing; applied 1.5x conservative multiplier"
        else:
            vol_ratio = max(0.1, volatility / self.baseline_vol)
            effective_bps = self.base_bps * (vol_ratio ** self.vol_exponent)
            # Enforce minimum floor of 1.0 bp
            effective_bps = max(1.0, effective_bps)
            origin = "SIMULATED_MODEL"
            note = f"Volatility ratio: {vol_ratio:.2f}x (vol={volatility:.1%})"

        slip_amount = reference_price * (effective_bps / 10_000.0)
        exec_price = (
            reference_price + slip_amount
            if side_str == "BUY"
            else max(0.01, reference_price - slip_amount)
        )

        return SlippageResult(
            execution_price=exec_price,
            reference_price=reference_price,
            slippage_amount=slip_amount,
            slippage_bps=effective_bps,
            total_slippage_cost=slip_amount * quantity,
            method="VOLATILITY_ADJUSTED",
            origin=origin,
            notes=note,
        )


class VolumeSensitiveSlippageModel(BaseSlippageModel):
    """
    Square-root market impact law (Almgren-Chriss framework).
    Market impact scales with square-root of order size relative to market volume:
    Impact_bps = base_bps + impact_coeff * sqrt(quantity / daily_volume) * 10000
    """

    def __init__(
        self,
        base_bps: float = 2.0,
        impact_coefficient: float = 0.10,
        power_exponent: float = 0.5,
    ):
        self.base_bps = base_bps
        self.impact_coefficient = impact_coefficient
        self.power_exponent = power_exponent

    def calculate_slippage(
        self,
        reference_price: float,
        side: Union[OrderSide, str],
        quantity: int,
        daily_volume: Optional[float] = None,
        volatility: Optional[float] = None,
    ) -> SlippageResult:
        side_str = side.value if isinstance(side, OrderSide) else str(side).upper()

        if daily_volume is None or daily_volume <= 0:
            # Conservative fallback when market volume is unrecorded
            effective_bps = self.base_bps * 2.0
            origin = "CONSERVATIVE_FALLBACK"
            note = "Market volume missing; applied 2.0x conservative fallback"
        else:
            participation_rate = quantity / max(daily_volume, 1.0)
            impact_bps = self.impact_coefficient * (participation_rate ** self.power_exponent) * 10_000.0
            effective_bps = self.base_bps + impact_bps
            origin = "SIMULATED_MODEL"
            note = f"Participation rate: {participation_rate:.3%} (impact={impact_bps:.1f} bps)"

        slip_amount = reference_price * (effective_bps / 10_000.0)
        exec_price = (
            reference_price + slip_amount
            if side_str == "BUY"
            else max(0.01, reference_price - slip_amount)
        )

        return SlippageResult(
            execution_price=exec_price,
            reference_price=reference_price,
            slippage_amount=slip_amount,
            slippage_bps=effective_bps,
            total_slippage_cost=slip_amount * quantity,
            method="VOLUME_SENSITIVE",
            origin=origin,
            notes=note,
        )


class CompositeSlippageModel(BaseSlippageModel):
    """
    Master composite slippage model combining base spread, volatility scaling,
    and square-root market impact. Provides the most realistic simulation.
    """

    def __init__(
        self,
        base_bps: float = 2.0,
        baseline_annual_vol: float = 0.15,
        impact_coefficient: float = 0.10,
    ):
        self.base_bps = base_bps
        self.baseline_vol = baseline_annual_vol
        self.impact_coefficient = impact_coefficient

    def calculate_slippage(
        self,
        reference_price: float,
        side: Union[OrderSide, str],
        quantity: int,
        daily_volume: Optional[float] = None,
        volatility: Optional[float] = None,
    ) -> SlippageResult:
        side_str = side.value if isinstance(side, OrderSide) else str(side).upper()

        # 1. Volatility multiplier
        vol_factor = 1.0
        if volatility is not None and volatility > 0:
            vol_factor = max(0.5, volatility / self.baseline_vol)

        # 2. Volume impact
        impact_bps = 0.0
        origin = "SIMULATED_MODEL"
        if daily_volume is not None and daily_volume > 0:
            part_rate = quantity / daily_volume
            impact_bps = self.impact_coefficient * np.sqrt(part_rate) * 10_000.0
        else:
            # Conservative fallback assumption
            impact_bps = 2.0
            origin = "CONSERVATIVE_FALLBACK"

        effective_bps = (self.base_bps * vol_factor) + impact_bps
        effective_bps = max(1.0, effective_bps)  # Floor of 1 bp

        slip_amount = reference_price * (effective_bps / 10_000.0)
        exec_price = (
            reference_price + slip_amount
            if side_str == "BUY"
            else max(0.01, reference_price - slip_amount)
        )

        return SlippageResult(
            execution_price=exec_price,
            reference_price=reference_price,
            slippage_amount=slip_amount,
            slippage_bps=effective_bps,
            total_slippage_cost=slip_amount * quantity,
            method="COMPOSITE",
            origin=origin,
            notes=f"Vol factor: {vol_factor:.2f}x, impact: {impact_bps:.1f} bps",
        )
