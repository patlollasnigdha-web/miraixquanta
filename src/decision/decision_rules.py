"""
MIRAI — Investment Decision Rules & Multi-Pillar Synthesizer (M09)
Evaluates multi-pillar evidence, calculates composite conviction scores,
enforces veto guards, and resolves conflicting signals.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.intelligence.regime_detection import MarketRegime
from src.strategies.base_strategy import SignalAction
from src.decision.decision_schemas import (
    DecisionInput,
    DecisionVerdict,
    DisplayLabel,
    RiskStatus,
)

logger = get_logger("DecisionRules")


class DecisionRuleEvaluator:
    """
    Evaluates investment decision rules across predictive AI, stock strength,
    candidate strategies, market regimes, and fundamental intelligence.
    """

    DEFAULT_WEIGHTS = {
        "predictive_model": 0.25,
        "stock_strength": 0.25,
        "strategy_signal": 0.20,
        "regime_alignment": 0.15,
        "sentiment_fundamentals": 0.15,
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        yes_threshold: float = 68.0,
        wait_upper_threshold: float = 67.9,
        wait_lower_threshold: float = 40.0,
        no_threshold: float = 39.9,
        min_confidence: float = 0.45,
    ):
        cfg = get_config()
        self.weights = weights or cfg.get("decision_engine.weights", self.DEFAULT_WEIGHTS)
        total_w = sum(self.weights.values())
        if total_w > 0:
            self.weights = {k: v / total_w for k, v in self.weights.items()}

        self.yes_threshold = cfg.get("decision_engine.thresholds.yes_threshold", yes_threshold)
        self.wait_upper_threshold = cfg.get("decision_engine.thresholds.wait_upper_threshold", wait_upper_threshold)
        self.wait_lower_threshold = cfg.get("decision_engine.thresholds.wait_lower_threshold", wait_lower_threshold)
        self.no_threshold = cfg.get("decision_engine.thresholds.no_threshold", no_threshold)
        self.min_confidence = cfg.get("decision_engine.thresholds.min_confidence", min_confidence)

    # -------------------------------------------------------------
    # 1. PILLAR SCORING METHODS (Each normalized to 0 - 100)
    # -------------------------------------------------------------
    def _score_predictive_model(self, inp: DecisionInput) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        """Scores predictive AI model probabilities and validation approval."""
        if not inp.model_prediction:
            return None, None, None

        pred = inp.model_prediction
        pred_class = pred.get("predicted_class")  # 1: Upward, 2: Stationary, 3: Downward
        probs = pred.get("probabilities", [])
        status = pred.get("status", "experimental")

        # Class 1 (Upward) is bullish, Class 3 (Downward) is bearish, Class 2 (Stationary) is neutral
        if pred_class == 1:
            p = probs[0] if len(probs) >= 1 else 0.65
            score = 50.0 + (p * 50.0)  # e.g. 0.70 -> 85.0
            pos_fact = f"Model predicts Upward movement with {p*100:.1f}% probability (Status: {status})"
            return float(np.clip(score, 50.0, 100.0)), pos_fact, None
        elif pred_class == 3:
            p = probs[2] if len(probs) >= 3 else 0.65
            score = 50.0 - (p * 50.0)  # e.g. 0.70 -> 15.0
            neg_fact = f"Model predicts Downward movement with {p*100:.1f}% probability"
            return float(np.clip(score, 0.0, 50.0)), None, neg_fact
        else:
            return 50.0, "Model predicts Stationary price regime", None

    def _score_stock_strength(self, inp: DecisionInput) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        """Scores dynamic stock strength (0 to 100) and trend status."""
        if not inp.stock_strength:
            return None, None, None

        ss = inp.stock_strength
        score = float(ss.overall_score)
        trend = ss.trend_status

        pos = None
        neg = None
        if score >= 65.0:
            pos = f"High Stock Strength ({score:.1f}/100, {ss.classification}) — Trend: {trend}"
        elif score <= 40.0:
            neg = f"Weak Stock Strength ({score:.1f}/100, {ss.classification}) — Trend: {trend}"

        # Trend bonus
        if trend == "Strengthening":
            score = min(100.0, score + 4.0)
        elif trend == "Weakening":
            score = max(0.0, score - 4.0)

        return score, pos, neg

    def _score_strategy_signal(self, inp: DecisionInput) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        """Scores candidate strategy directive and conviction."""
        if not inp.strategy_signal:
            return None, None, None

        sig = inp.strategy_signal
        action = sig.signal
        strength = sig.signal_strength

        if action == SignalAction.BUY:
            score = 50.0 + (strength * 45.0)  # e.g. 0.80 strength -> 86.0
            pos = f"Strategy '{sig.strategy_name}' emitted BUY signal (Conviction: {strength*100:.1f}%)"
            return float(np.clip(score, 50.0, 95.0)), pos, None
        elif action == SignalAction.SELL:
            score = 50.0 - (strength * 45.0)
            neg = f"Strategy '{sig.strategy_name}' emitted SELL signal (Conviction: {strength*100:.1f}%)"
            return float(np.clip(score, 5.0, 50.0)), None, neg
        elif action == SignalAction.HOLD:
            return 50.0, f"Strategy '{sig.strategy_name}' emitted HOLD directive", None
        else:
            return 45.0, None, f"Strategy '{sig.strategy_name}' emitted NO_SIGNAL"

    def _score_regime_alignment(self, inp: DecisionInput) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        """Scores compatibility of market regime with equity action."""
        if not inp.market_regime:
            return None, None, None

        mr = inp.market_regime
        reg = mr.detected_regime

        if reg == MarketRegime.BULLISH_TRENDING:
            return 85.0, "Macro regime is BULLISH_TRENDING (Supportive for equity longs)", None
        elif reg == MarketRegime.LOW_VOLATILITY:
            return 70.0, "Macro regime is LOW_VOLATILITY (Orderly market environment)", None
        elif reg == MarketRegime.SIDEWAYS_RANGE_BOUND:
            return 50.0, "Macro regime is SIDEWAYS_RANGE_BOUND", None
        elif reg == MarketRegime.HIGH_VOLATILITY:
            return 35.0, None, "Macro regime is HIGH_VOLATILITY (Elevated risk environment)"
        elif reg == MarketRegime.BEARISH_TRENDING:
            return 25.0, None, "Macro regime is BEARISH_TRENDING (Adverse trend for equity longs)"
        elif reg == MarketRegime.STRESS_ABNORMAL:
            return 10.0, None, "Macro regime is STRESS_ABNORMAL (Severe market dislocation)"
        return 50.0, None, None

    def _score_sentiment_fundamentals(self, inp: DecisionInput) -> Tuple[Optional[float], Optional[str], Optional[str]]:
        """Synthesizes sentiment and fundamental health scores."""
        scores = []
        pos_list = []
        neg_list = []

        if inp.sentiment and inp.sentiment.status == "VALID":
            s_score = inp.sentiment.sentiment_score
            scores.append(s_score)
            if s_score >= 60.0:
                pos_list.append(f"Bullish news sentiment ({s_score:.1f}/100)")
            elif s_score <= 40.0:
                neg_list.append(f"Bearish news sentiment ({s_score:.1f}/100)")

        if inp.fundamentals and inp.fundamentals.status == "VALID" and inp.fundamentals.fundamental_score is not None:
            f_score = inp.fundamentals.fundamental_score
            scores.append(f_score)
            if f_score >= 65.0:
                pos_list.append(f"Healthy company fundamentals ({f_score:.1f}/100, {inp.fundamentals.classification})")
            elif f_score <= 40.0:
                neg_list.append(f"Weak company fundamentals ({f_score:.1f}/100, {inp.fundamentals.classification})")

        if not scores:
            return None, None, None

        score = float(np.mean(scores))
        pos = "; ".join(pos_list) if pos_list else None
        neg = "; ".join(neg_list) if neg_list else None
        return score, pos, neg

    # -------------------------------------------------------------
    # 2. MASTER EVALUATION & VETO GUARDS
    # -------------------------------------------------------------
    def evaluate(
        self, inp: DecisionInput
    ) -> Tuple[str, str, str, float, float, Dict[str, float], Dict[str, float], List[str], List[str], List[str], List[str], str]:
        """
        Executes multi-pillar evidence synthesis and rule checks.
        Returns:
        (verdict, display_label, action_type, composite_score, confidence,
         factor_scores, factor_contributions, positive_factors, negative_factors,
         conflicting_signals, missing_evidence, risk_status)
        """
        # 1. Validation check
        cons_errors = inp.validate_consistency()
        if cons_errors:
            logger.error("Input consistency errors: %s", cons_errors)
            return (
                DecisionVerdict.INSUFFICIENT_DATA,
                DisplayLabel.NO_ACTION,
                "OBSERVE",
                50.0,
                0.0,
                {},
                {},
                [],
                cons_errors,
                [],
                cons_errors,
                RiskStatus.RISK_PENDING,
            )

        pos_factors = []
        neg_factors = []
        conflicts = []
        missing = []

        # 2. Score individual pillars
        raw_scores: Dict[str, Optional[float]] = {}

        # Predictive Model
        s_model, p_mod, n_mod = self._score_predictive_model(inp)
        raw_scores["predictive_model"] = s_model
        if p_mod: pos_factors.append(p_mod)
        if n_mod: neg_factors.append(n_mod)
        if s_model is None: missing.append("Predictive model output unavailable")

        # Stock Strength
        s_ss, p_ss, n_ss = self._score_stock_strength(inp)
        raw_scores["stock_strength"] = s_ss
        if p_ss: pos_factors.append(p_ss)
        if n_ss: neg_factors.append(n_ss)
        if s_ss is None: missing.append("Stock strength score unavailable")

        # Strategy Signal
        s_strat, p_strat, n_strat = self._score_strategy_signal(inp)
        raw_scores["strategy_signal"] = s_strat
        if p_strat: pos_factors.append(p_strat)
        if n_strat: neg_factors.append(n_strat)
        if s_strat is None: missing.append("Candidate strategy signal unavailable")

        # Regime Alignment
        s_reg, p_reg, n_reg = self._score_regime_alignment(inp)
        raw_scores["regime_alignment"] = s_reg
        if p_reg: pos_factors.append(p_reg)
        if n_reg: neg_factors.append(n_reg)
        if s_reg is None: missing.append("Market regime classification unavailable")

        # Sentiment & Fundamentals
        s_sf, p_sf, n_sf = self._score_sentiment_fundamentals(inp)
        raw_scores["sentiment_fundamentals"] = s_sf
        if p_sf: pos_factors.append(p_sf)
        if n_sf: neg_factors.append(n_sf)
        if s_sf is None: missing.append("Sentiment & fundamental data unavailable (INSUFFICIENT_DATA)")

        # 3. Dynamic Re-normalization of Available Factors
        available_scores = {k: v for k, v in raw_scores.items() if v is not None}

        # Check for essential inputs (minimum 2 pillars required, including either strategy or stock strength)
        if len(available_scores) < 2 or ("strategy_signal" not in available_scores and "stock_strength" not in available_scores):
            return (
                DecisionVerdict.INSUFFICIENT_DATA,
                DisplayLabel.NO_ACTION,
                "OBSERVE",
                50.0,
                0.0,
                available_scores,
                {},
                pos_factors,
                neg_factors,
                conflicts,
                missing,
                RiskStatus.RISK_PENDING,
            )

        sum_w = sum(self.weights[k] for k in available_scores.keys())
        norm_weights = {k: self.weights[k] / sum_w for k in available_scores.keys()}
        contributions = {k: available_scores[k] * norm_weights[k] for k in available_scores.keys()}
        composite_score = float(sum(contributions.values()))

        # Confidence calculation based on coverage
        coverage = len(available_scores) / len(self.weights)
        confidence = float(np.clip(coverage * 0.95, 0.20, 1.0))

        # 4. Check for Conflict & Veto Guards
        action_type = "OBSERVE"
        regime_str = inp.market_regime.detected_regime if inp.market_regime else None

        # Veto 1: Severe Market Stress
        if regime_str == MarketRegime.STRESS_ABNORMAL:
            conflicts.append("VETO GUARD: Macro regime is STRESS_ABNORMAL. All long entries blocked.")
            return (
                DecisionVerdict.NO,
                DisplayLabel.NO_ACTION,
                "OBSERVE",
                composite_score,
                confidence,
                available_scores,
                contributions,
                pos_factors,
                neg_factors,
                conflicts,
                missing,
                RiskStatus.RISK_PENDING,
            )

        # Veto 2: Contradiction between Model and Strategy
        if inp.model_prediction and inp.strategy_signal:
            pred_class = inp.model_prediction.get("predicted_class")
            strat_act = inp.strategy_signal.signal
            if pred_class == 3 and strat_act == SignalAction.BUY:
                conflicts.append("CONFLICT: Model predicts Downward price movement while Strategy signals BUY.")
            elif pred_class == 1 and strat_act == SignalAction.SELL:
                conflicts.append("CONFLICT: Model predicts Upward price movement while Strategy signals SELL.")

        # Veto 3: Very Weak Stock Strength blocks Long Buy entries
        if inp.stock_strength and inp.stock_strength.overall_score < 30.0:
            if composite_score >= self.yes_threshold or (inp.strategy_signal and inp.strategy_signal.signal == SignalAction.BUY):
                conflicts.append("VETO GUARD: Stock Strength is 'Very Weak' (<30/100). Long BUY action blocked.")

        # Veto 4: Risk Constraint Violation (M11 Interface)
        risk_status = RiskStatus.RISK_PENDING
        if inp.risk_constraints:
            if inp.risk_constraints.get("violation", False):
                risk_status = RiskStatus.RISK_BLOCKED
                conflicts.append(f"RISK VETO: Violated risk limit ({inp.risk_constraints.get('violation_reason')})")

        # 5. Resolve Verdict from Composite Score & Guards
        if risk_status == RiskStatus.RISK_BLOCKED:
            verdict = DecisionVerdict.NO
            display_label = DisplayLabel.NO_ACTION
            action_type = "OBSERVE"
        elif conflicts:
            # When active directional conflicts exist, force WAIT state for safety
            verdict = DecisionVerdict.WAIT
            display_label = DisplayLabel.HOLD
            action_type = "HOLD"
        elif composite_score >= self.yes_threshold and confidence >= self.min_confidence:
            verdict = DecisionVerdict.YES
            display_label = DisplayLabel.STRONG_BUY if composite_score >= 82.0 else DisplayLabel.BUY
            action_type = "ENTRY_LONG"
        elif composite_score <= self.no_threshold:
            verdict = DecisionVerdict.NO
            display_label = DisplayLabel.STRONG_SELL if composite_score <= 25.0 else DisplayLabel.SELL
            action_type = "EXIT"
        else:
            verdict = DecisionVerdict.WAIT
            display_label = DisplayLabel.HOLD
            action_type = "HOLD"

        return (
            verdict,
            display_label,
            action_type,
            composite_score,
            confidence,
            available_scores,
            contributions,
            pos_factors,
            neg_factors,
            conflicts,
            missing,
            risk_status,
        )
