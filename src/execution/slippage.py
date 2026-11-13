"""
MIRAI — Slippage Compatibility Re-Export Module (M12)
"""

from src.execution.slippage_model import (
    SlippageResult,
    BaseSlippageModel,
    FixedBpsSlippageModel,
    VolatilityAdjustedSlippageModel,
    VolumeSensitiveSlippageModel,
    CompositeSlippageModel,
)

__all__ = [
    "SlippageResult",
    "BaseSlippageModel",
    "FixedBpsSlippageModel",
    "VolatilityAdjustedSlippageModel",
    "VolumeSensitiveSlippageModel",
    "CompositeSlippageModel",
]
