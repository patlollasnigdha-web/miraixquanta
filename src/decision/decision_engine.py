"""
MIRAI — Investment Decision Engine (M09)
Converts multi-source market intelligence, predictive models, strategy signals,
and regime contexts into transparent, evidence-based investment decisions.
"""

from typing import Any, Dict, List, Optional, Union
import pandas as pd

from src.utils.logger import get_logger
from src.decision.decision_schemas import (
    DecisionInput,
    DecisionVerdict,
    DisplayLabel,
    RiskStatus,
    InvestmentDecision,
)
from src.decision.decision_rules import DecisionRuleEvaluator
from src.decision.decision_explainer import DecisionExplainer

logger = get_logger("DecisionEngine")


class InvestmentDecisionEngine:
    """
    Central investment decision engine for MIRAI.
    Coordinates evidence evaluation, conflict resolution, risk constraint checks,
    and decision narrative generation across Pipeline A and Pipeline B.
    """

    def __init__(
        self,
        evaluator: Optional[DecisionRuleEvaluator] = None,
        explainer: Optional[DecisionExplainer] = None,
    ):
        self.evaluator = evaluator or DecisionRuleEvaluator()
        self.explainer = explainer or DecisionExplainer()

    def make_decision(self, inp: DecisionInput) -> InvestmentDecision:
        """
        Executes complete investment decision lifecycle on a DecisionInput bundle.
        """
        # 1. Evaluate rules and multi-pillar evidence
        (
            verdict,
            display_label,
            action_type,
            composite_score,
            confidence,
            factor_scores,
            factor_contributions,
            pos_factors,
            neg_factors,
            conflicts,
            missing,
            risk_status,
        ) = self.evaluator.evaluate(inp)

        # 2. Extract suggested price levels from strategy signal
        ref_price = inp.current_price
        stop_loss = None
        take_profit = None

        if inp.strategy_signal:
            if hasattr(inp.strategy_signal, "entry_reference_price") and inp.strategy_signal.entry_reference_price:
                ref_price = inp.strategy_signal.entry_reference_price
            if hasattr(inp.strategy_signal, "suggested_stop_loss"):
                stop_loss = inp.strategy_signal.suggested_stop_loss
            if hasattr(inp.strategy_signal, "suggested_take_profit"):
                take_profit = inp.strategy_signal.suggested_take_profit

        # 3. Generate structured explanation
        explanation = self.explainer.generate_explanation(
            symbol=inp.symbol,
            verdict=verdict,
            display_label=display_label,
            composite_score=composite_score,
            confidence=confidence,
            positive_factors=pos_factors,
            negative_factors=neg_factors,
            conflicts=conflicts,
            missing=missing,
            strategy_signal=inp.strategy_signal,
            market_regime=inp.market_regime,
            risk_status=risk_status,
        )

        decision = InvestmentDecision(
            symbol=inp.symbol,
            pipeline_id=inp.pipeline_id,
            timestamp=inp.timestamp,
            verdict=verdict,
            display_label=display_label,
            action_type=action_type,
            composite_score=composite_score,
            confidence=confidence,
            investment_horizon=inp.investment_horizon,
            entry_reference_price=ref_price,
            suggested_stop_loss=stop_loss,
            suggested_take_profit=take_profit,
            factor_contributions=factor_contributions,
            factor_scores=factor_scores,
            risk_status=risk_status,
            explanation=explanation,
        )

        score_display = f"{composite_score:.1f}" if composite_score is not None else "N/A"
        logger.info(
            "Decision for %s (%s): %s [%s] (Score: %s, Conf: %.2f)",
            inp.symbol, inp.pipeline_id, verdict, display_label, score_display, confidence
        )
        return decision

    def make_decision_with_risk(
        self,
        inp: DecisionInput,
        risk_engine: Any,
        current_capital: Optional[float] = None,
        atr: Optional[float] = None,
        win_rate: Optional[float] = None,
        win_loss_ratio: Optional[float] = None,
        sizing_method: str = "risk_budgeting",
    ) -> InvestmentDecision:
        """
        Executes decision generation and immediately evaluates it through M11 RiskManagementEngine.
        Transitions risk_status from RISK_PENDING to RISK_APPROVED or RISK_BLOCKED,
        blocking YES decisions if risk constraints are breached.
        """
        decision = self.make_decision(inp)
        ref_price = inp.current_price or decision.entry_reference_price or 100.0
        decision, _ = risk_engine.apply_risk_to_decision(
            decision=decision,
            current_price=ref_price,
            current_capital=current_capital,
            atr=atr,
            win_rate=win_rate,
            win_loss_ratio=win_loss_ratio,
            sizing_method=sizing_method,
        )
        return decision

