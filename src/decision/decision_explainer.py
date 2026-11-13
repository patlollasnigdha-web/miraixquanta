"""
MIRAI — Investment Decision Explainer (M09)
Translates quantitative factor scores, rule outcomes, and veto triggers
into structured, human-interpretable investment narratives.
"""

from typing import Any, Dict, List, Optional
from src.decision.decision_schemas import DecisionExplanation, DecisionVerdict, DisplayLabel


class DecisionExplainer:
    """
    Generates structured decision explanations and actionable trigger conditions.
    """

    @staticmethod
    def generate_explanation(
        symbol: str,
        verdict: str,
        display_label: str,
        composite_score: float,
        confidence: float,
        positive_factors: List[str],
        negative_factors: List[str],
        conflicts: List[str],
        missing: List[str],
        strategy_signal: Optional[Any],
        market_regime: Optional[Any],
        risk_status: str,
    ) -> DecisionExplanation:
        """
        Builds a comprehensive DecisionExplanation object.
        """
        # 1. Verdict Rationale
        if verdict == DecisionVerdict.YES:
            rationale = (
                f"Evidence supports {display_label.upper()} action for {symbol}. "
                f"Composite conviction score is {composite_score:.1f}/100 with {confidence*100:.1f}% confidence. "
                f"Multi-pillar alignment confirms favorable risk-reward conditions."
            )
        elif verdict == DecisionVerdict.NO:
            rationale = (
                f"Evidence opposes active investment in {symbol} ({display_label}). "
                f"Composite score is {composite_score:.1f}/100. Adverse technical, model, or macro factors dominate."
            )
        elif verdict == DecisionVerdict.WAIT:
            if conflicts:
                rationale = (
                    f"Action deferred to WAIT for {symbol}. Conflicting evidence detected: "
                    f"{'; '.join(conflicts[:2])}. Holding recommended until alignment is established."
                )
            else:
                rationale = (
                    f"Action deferred to WAIT for {symbol}. Composite conviction ({composite_score:.1f}/100) "
                    f"is in neutral/inconclusive territory (threshold: >=68.0 for YES)."
                )
        else:  # INSUFFICIENT_DATA
            rationale = (
                f"Cannot generate investment decision for {symbol}: essential evidence is missing or incompatible. "
                f"Missing items: {'; '.join(missing[:3])}."
            )

        # 2. Strategy Context
        strat_context = "No candidate strategy evaluated."
        if strategy_signal:
            strat_context = (
                f"Strategy: '{strategy_signal.strategy_name}' (Signal: {strategy_signal.signal}, "
                f"Conviction: {strategy_signal.signal_strength*100:.1f}%, Horizon: {strategy_signal.prediction_horizon})."
            )

        # 3. Market Regime Context
        regime_context = "Macro regime context unavailable."
        if market_regime:
            regime_context = (
                f"Broader Market Regime: {market_regime.detected_regime} "
                f"(Confidence: {market_regime.regime_confidence*100:.1f}%, Persistence: {market_regime.persistence_bars} bars)."
            )

        # 4. Risk Notes
        risk_notes = f"Risk Status: {risk_status}. Note: Formal portfolio limits will be enforced by M11 Dynamic Risk Management."
        if risk_status == "RISK_BLOCKED":
            risk_notes = "ACTION BLOCKED: Active risk constraints violated."

        # 5. Actionable Triggers ("What would change this decision?")
        triggers = []
        if verdict in (DecisionVerdict.WAIT, DecisionVerdict.NO):
            if composite_score < 68.0:
                triggers.append(f"Composite score expanding above 68.0 (currently {composite_score:.1f})")
            if strategy_signal and strategy_signal.signal != "BUY":
                triggers.append("Candidate strategy emitting confirmed BUY signal with volume")
            if market_regime and market_regime.detected_regime in ("HIGH_VOLATILITY", "BEARISH_TRENDING", "STRESS_ABNORMAL"):
                triggers.append("Macro market regime stabilizing to BULLISH_TRENDING or LOW_VOLATILITY")
            if conflicts:
                triggers.append("Resolution of contradictory signals between predictive model and technical strategy")
        elif verdict == DecisionVerdict.YES:
            triggers.append("Breakdown below suggested stop-loss level")
            triggers.append("Macro regime transition into HIGH_VOLATILITY or STRESS_ABNORMAL")
            triggers.append("Predictive model flipping to Downward class")

        return DecisionExplanation(
            verdict_rationale=rationale,
            positive_factors=positive_factors,
            negative_factors=negative_factors,
            conflicting_signals=conflicts,
            missing_evidence=missing,
            strategy_context=strat_context,
            regime_context=regime_context,
            risk_notes=risk_notes,
            decision_triggers=triggers,
        )
