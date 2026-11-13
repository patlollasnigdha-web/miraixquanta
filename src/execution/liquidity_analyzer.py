"""
MIRAI — Liquidity Analyzer & Market Impact Assessment (M12)
Evaluates participation rate, liquidity adequacy, and market impact risk.
Recommends order slicing strategies (TWAP / VWAP) when order sizes threaten market impact.
Clearly distinguishes daily OHLCV volume-based liquidity from Level-2 order-book depth.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from src.utils.logger import get_logger

logger = get_logger("LiquidityAnalyzer")


class LiquidityRegime(str, Enum):
    """Assessment of market depth relative to order magnitude."""
    HIGH_LIQUIDITY = "HIGH_LIQUIDITY"       # Order is negligible (<0.1% volume)
    MODERATE_LIQUIDITY = "MODERATE_LIQUIDITY" # Order is standard (0.1% - 1.0% volume)
    LOW_LIQUIDITY = "LOW_LIQUIDITY"         # Order is significant (1.0% - 5.0% volume)
    CRITICAL_ILLIQUID = "CRITICAL_ILLIQUID" # Order is excessive (>5.0% volume)
    UNSPECIFIED = "UNSPECIFIED"             # No volume information available


@dataclass
class LiquidityAssessment:
    """Standardized liquidity and impact evaluation for an order."""
    symbol: str
    order_quantity: int
    daily_volume: Optional[float]
    participation_rate: float            # Q / V (fraction)
    liquidity_regime: LiquidityRegime
    estimated_impact_bps: float
    is_excessive: bool
    recommended_execution_style: str    # 'MARKET', 'TWAP', 'VWAP', 'REJECT'
    recommended_slices: int
    data_source_type: str               # 'DAILY_VOLUME_OHLCV' vs 'LOB_DEPTH_M1'
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "order_quantity": self.order_quantity,
            "daily_volume": self.daily_volume,
            "participation_rate_pct": round(self.participation_rate * 100, 3),
            "liquidity_regime": self.liquidity_regime.value,
            "estimated_impact_bps": round(self.estimated_impact_bps, 2),
            "is_excessive": self.is_excessive,
            "recommended_execution_style": self.recommended_execution_style,
            "recommended_slices": self.recommended_slices,
            "data_source_type": self.data_source_type,
            "warnings": self.warnings,
        }


class LiquidityAnalyzer:
    """
    Analyzes instrument liquidity and assesses whether an order requires slicing.
    """

    def __init__(
        self,
        max_safe_participation_rate: float = 0.01,  # 1% of ADV / bar volume
        excessive_participation_rate: float = 0.05, # 5% of ADV / bar volume
        twap_slice_threshold_rate: float = 0.005,   # 0.5% triggers TWAP recommendation
    ):
        self.max_safe_part_rate = max_safe_participation_rate
        self.excessive_part_rate = excessive_participation_rate
        self.twap_slice_threshold_rate = twap_slice_threshold_rate

    def assess_order_liquidity(
        self,
        symbol: str,
        quantity: int,
        daily_volume: Optional[float] = None,
        is_lob_data: bool = False,
    ) -> LiquidityAssessment:
        """
        Assesses execution risk and recommends an execution strategy based on volume.
        """
        warnings: List[str] = []
        data_source = "LOB_DEPTH_M1" if is_lob_data else "DAILY_VOLUME_OHLCV"

        if daily_volume is None or daily_volume <= 0:
            warnings.append(
                "No volume/liquidity data available. Assuming conservative moderate liquidity."
            )
            return LiquidityAssessment(
                symbol=symbol,
                order_quantity=quantity,
                daily_volume=None,
                participation_rate=0.0,
                liquidity_regime=LiquidityRegime.UNSPECIFIED,
                estimated_impact_bps=5.0,  # Conservative fallback assumption
                is_excessive=False,
                recommended_execution_style="MARKET",
                recommended_slices=1,
                data_source_type=data_source,
                warnings=warnings,
            )

        participation_rate = float(quantity / daily_volume)

        # Classify regime
        if participation_rate <= 0.001:
            regime = LiquidityRegime.HIGH_LIQUIDITY
            style = "MARKET"
            slices = 1
            is_excessive = False
            impact_bps = 1.0
        elif participation_rate <= self.twap_slice_threshold_rate:
            regime = LiquidityRegime.MODERATE_LIQUIDITY
            style = "MARKET"
            slices = 1
            is_excessive = False
            impact_bps = 2.5
        elif participation_rate <= self.max_safe_part_rate:
            regime = LiquidityRegime.LOW_LIQUIDITY
            style = "TWAP"
            slices = 3
            is_excessive = False
            impact_bps = 5.0
            warnings.append(
                f"Order represents {participation_rate:.2%} of volume. Slicing into 3 TWAP intervals recommended."
            )
        elif participation_rate <= self.excessive_part_rate:
            regime = LiquidityRegime.LOW_LIQUIDITY
            style = "VWAP"
            slices = 5
            is_excessive = False
            impact_bps = 12.0
            warnings.append(
                f"Elevated participation rate ({participation_rate:.2%}). Slicing into 5 VWAP intervals recommended."
            )
        else:
            regime = LiquidityRegime.CRITICAL_ILLIQUID
            style = "VWAP"
            slices = 10
            is_excessive = True
            impact_bps = 25.0
            warnings.append(
                f"CRITICAL: Excessive order size ({participation_rate:.1%} of volume). Severe market impact expected."
            )

        return LiquidityAssessment(
            symbol=symbol,
            order_quantity=quantity,
            daily_volume=daily_volume,
            participation_rate=participation_rate,
            liquidity_regime=regime,
            estimated_impact_bps=impact_bps,
            is_excessive=is_excessive,
            recommended_execution_style=style,
            recommended_slices=slices,
            data_source_type=data_source,
            warnings=warnings,
        )
