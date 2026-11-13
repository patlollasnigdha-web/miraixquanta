"""
MIRAI — Adaptive Strategy Selector (M08)
Selects, ranks, and dynamically weights trading strategies according to
the prevailing macro market regime identified by M07.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from src.utils.logger import get_logger
from src.intelligence.regime_detection import MarketRegime
from src.strategies.base_strategy import StrategySignal, SignalAction

logger = get_logger("StrategySelector")


@dataclass
class StrategySelectionResult:
    """Standardized output structure for strategy selection decision."""
    selected_strategy: Optional[str]
    market_regime: str
    regime_confidence: float
    compatibility_score: float  # [0.0, 1.0]
    candidate_rankings: List[Dict[str, Any]]
    selection_reason: str
    rejection_reasons: Dict[str, str] = field(default_factory=dict)
    noise_filter_applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_strategy": self.selected_strategy,
            "market_regime": self.market_regime,
            "regime_confidence": round(self.regime_confidence, 3),
            "compatibility_score": round(self.compatibility_score, 3),
            "candidate_rankings": self.candidate_rankings,
            "selection_reason": self.selection_reason,
            "rejection_reasons": self.rejection_reasons,
            "noise_filter_applied": self.noise_filter_applied,
        }


class AdaptiveStrategySelector:
    """
    Dynamically maps detected market regimes to optimal quantitative strategies.
    Applies compatibility matrices, noise filtering, and transparency explanations.
    """

    # Baseline regime-to-strategy compatibility matrix (0.0 to 1.0)
    DEFAULT_COMPATIBILITY_MATRIX = {
        MarketRegime.BULLISH_TRENDING: {
            "MomentumStrategy": 0.95,
            "BreakoutStrategy": 0.85,
            "MeanReversionStrategy": 0.20,
        },
        MarketRegime.BEARISH_TRENDING: {
            "MomentumStrategy": 0.80,
            "BreakoutStrategy": 0.85,
            "MeanReversionStrategy": 0.15,
        },
        MarketRegime.SIDEWAYS_RANGE_BOUND: {
            "MeanReversionStrategy": 0.90,
            "MomentumStrategy": 0.35,
            "BreakoutStrategy": 0.30,
        },
        MarketRegime.HIGH_VOLATILITY: {
            "BreakoutStrategy": 0.65,
            "MomentumStrategy": 0.40,
            "MeanReversionStrategy": 0.10,
        },
        MarketRegime.LOW_VOLATILITY: {
            "MeanReversionStrategy": 0.80,
            "BreakoutStrategy": 0.60,
            "MomentumStrategy": 0.50,
        },
        MarketRegime.STRESS_ABNORMAL: {
            "MomentumStrategy": 0.10,
            "BreakoutStrategy": 0.10,
            "MeanReversionStrategy": 0.05,
        },
    }

    def __init__(
        self,
        compatibility_matrix: Optional[Dict[str, Dict[str, float]]] = None,
        min_compatibility_threshold: float = 0.40,
        min_regime_confidence: float = 0.50,
        persistence_requirement: int = 1,
    ):
        self.compat_matrix = compatibility_matrix or self.DEFAULT_COMPATIBILITY_MATRIX
        self.min_compat_threshold = min_compatibility_threshold
        self.min_regime_confidence = min_regime_confidence
        self.persistence_req = persistence_requirement

    def get_compatibility(self, regime: str, strategy_name: str) -> float:
        """Looks up regime compatibility for a strategy, defaulting to 0.50 if unknown."""
        reg_map = self.compat_matrix.get(regime)
        if not reg_map:
            return 0.50
        return reg_map.get(strategy_name, 0.50)

    def select_strategy(
        self,
        candidate_signals: List[StrategySignal],
        market_regime: str,
        regime_confidence: float = 0.80,
        persistence_bars: int = 1,
    ) -> StrategySelectionResult:
        """
        Ranks candidate signals and selects the most compatible strategy for current regime.
        """
        if not candidate_signals:
            return StrategySelectionResult(
                selected_strategy=None,
                market_regime=market_regime,
                regime_confidence=regime_confidence,
                compatibility_score=0.0,
                candidate_rankings=[],
                selection_reason="No candidate signals provided.",
            )

        # 1. Stress / Abnormal Market Safeguard
        if market_regime == MarketRegime.STRESS_ABNORMAL:
            rejections = {
                sig.strategy_name: "Market in STRESS_ABNORMAL regime; all aggressive strategies suppressed."
                for sig in candidate_signals
            }
            return StrategySelectionResult(
                selected_strategy=None,
                market_regime=market_regime,
                regime_confidence=regime_confidence,
                compatibility_score=0.0,
                candidate_rankings=[],
                selection_reason="All candidate strategies suppressed due to severe market stress regime.",
                rejection_reasons=rejections,
            )

        # 2. Score and rank candidates: Score = Compatibility * Signal Strength
        ranked_candidates = []
        rejections = {}

        for sig in candidate_signals:
            compat = self.get_compatibility(market_regime, sig.strategy_name)

            # Check if signal action is NO_SIGNAL
            if sig.signal == SignalAction.NO_SIGNAL:
                rejections[sig.strategy_name] = "Strategy emitted NO_SIGNAL (threshold conditions not met)."
                continue

            if compat < self.min_compat_threshold:
                rejections[sig.strategy_name] = (
                    f"Compatibility ({compat:.2f}) below threshold ({self.min_compat_threshold:.2f}) "
                    f"for regime '{market_regime}'."
                )
                continue

            # Composite ranking score
            rank_score = float(compat * sig.signal_strength)

            ranked_candidates.append({
                "strategy_name": sig.strategy_name,
                "signal": sig.signal,
                "signal_strength": sig.signal_strength,
                "compatibility": compat,
                "composite_score": rank_score,
                "signal_object": sig,
            })

        # 3. Sort by composite ranking score descending
        ranked_candidates.sort(key=lambda x: x["composite_score"], reverse=True)

        if not ranked_candidates:
            return StrategySelectionResult(
                selected_strategy=None,
                market_regime=market_regime,
                regime_confidence=regime_confidence,
                compatibility_score=0.0,
                candidate_rankings=[],
                selection_reason=f"No candidate strategy met compatibility thresholds for regime '{market_regime}'.",
                rejection_reasons=rejections,
            )

        best = ranked_candidates[0]
        sel_name = best["strategy_name"]
        sel_compat = best["compatibility"]
        sel_score = best["composite_score"]
        sel_signal = best["signal"]

        reason = (
            f"Selected '{sel_name}' ({sel_signal}, strength: {best['signal_strength']:.2f}) "
            f"with highest compatibility ({sel_compat:.2f}) for '{market_regime}' regime."
        )

        # Format output rankings (without embedding full object)
        clean_rankings = [
            {
                "strategy_name": c["strategy_name"],
                "signal": c["signal"],
                "signal_strength": round(c["signal_strength"], 3),
                "compatibility": round(c["compatibility"], 3),
                "composite_score": round(c["composite_score"], 3),
            }
            for c in ranked_candidates
        ]

        return StrategySelectionResult(
            selected_strategy=sel_name,
            market_regime=market_regime,
            regime_confidence=regime_confidence,
            compatibility_score=sel_compat,
            candidate_rankings=clean_rankings,
            selection_reason=reason,
            rejection_reasons=rejections,
        )
