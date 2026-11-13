"""
Re-exports from src.intelligence.regime_detection for backward compatibility.
"""

from src.intelligence.regime_detection import (
    MarketRegime,
    BaseRegimeDetector,
    RuleBasedRegimeDetector,
    GMMRegimeDetector,
    RegimeDetectionResult,
    extract_regime_features,
    compute_regime_transition_matrix,
)

__all__ = [
    "MarketRegime",
    "BaseRegimeDetector",
    "RuleBasedRegimeDetector",
    "GMMRegimeDetector",
    "RegimeDetectionResult",
    "extract_regime_features",
    "compute_regime_transition_matrix",
]
