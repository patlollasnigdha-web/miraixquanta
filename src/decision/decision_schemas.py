"""
MIRAI — Investment Decision Engine Data Schemas (M09)
Defines structured inputs, primary verdicts, secondary display labels,
and investment decision containers.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import pandas as pd


class DecisionVerdict:
    """Primary decision states."""
    YES = "YES"                            # Evidence supports action under specified conditions
    NO = "NO"                              # Evidence opposes action
    WAIT = "WAIT"                          # In transition, missing confirmation, or inconclusive
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"# Missing, stale, or unreliable essential inputs

    ALL_VERDICTS = [YES, NO, WAIT, INSUFFICIENT_DATA]


class DisplayLabel:
    """Secondary display labels for presentation layers."""
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"
    STRONG_SELL = "Strong Sell"
    NO_ACTION = "No Action"


class RiskStatus:
    """Risk management authorization states."""
    RISK_PENDING = "RISK_PENDING"    # Awaiting M11 risk engine validation (default)
    RISK_APPROVED = "RISK_APPROVED"  # Validated against risk constraints
    RISK_BLOCKED = "RISK_BLOCKED"    # Violated risk constraints (drawdown, vol, leverage)


@dataclass
class DecisionInput:
    """
    Unified input bundle provided to the Investment Decision Engine.
    Aggregates evidence across Batches 1 to 4.
    """
    symbol: str
    pipeline_id: str  # 'pipeline_a_fi2010' or 'pipeline_b_nifty'
    timestamp: pd.Timestamp
    investment_horizon: Union[int, str] = "1d"  # e.g. '1d', '5d', 100 ticks
    current_price: Optional[float] = None

    # M03 & M04: Predictive AI & Registry
    model_prediction: Optional[Dict[str, Any]] = None  # {'predicted_class', 'probabilities', 'model_id', 'status'}

    # M05: Stock Strength Intelligence
    stock_strength: Optional[Any] = None  # StockStrengthResult

    # M06: Sentiment & Fundamentals
    sentiment: Optional[Any] = None       # SentimentResult
    fundamentals: Optional[Any] = None    # FundamentalAssessment

    # M07: Market Regime
    market_regime: Optional[Any] = None   # RegimeDetectionResult

    # M08: Strategy Signal
    strategy_signal: Optional[Any] = None # StrategySignal

    # Risk & Preferences (M11 forward interface)
    risk_constraints: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None

    def validate_consistency(self) -> List[str]:
        """Validates that nested inputs share consistent symbols and pipelines."""
        errors = []
        sym_upper = self.symbol.upper()

        if self.stock_strength and hasattr(self.stock_strength, "symbol"):
            if self.stock_strength.symbol.upper() != sym_upper:
                errors.append(f"Symbol mismatch: input is {self.symbol}, stock_strength is {self.stock_strength.symbol}")

        if self.sentiment and hasattr(self.sentiment, "symbol"):
            if self.sentiment.symbol.upper() != sym_upper:
                errors.append(f"Symbol mismatch: input is {self.symbol}, sentiment is {self.sentiment.symbol}")

        if self.fundamentals and hasattr(self.fundamentals, "symbol"):
            if self.fundamentals.symbol.upper() != sym_upper:
                errors.append(f"Symbol mismatch: input is {self.symbol}, fundamentals is {self.fundamentals.symbol}")

        if self.strategy_signal and hasattr(self.strategy_signal, "pipeline_id"):
            if self.strategy_signal.pipeline_id != self.pipeline_id:
                errors.append(f"Pipeline mismatch: input is {self.pipeline_id}, strategy is {self.strategy_signal.pipeline_id}")

        return errors


@dataclass
class DecisionExplanation:
    """Human-readable and structured evidence explanation for an investment verdict."""
    verdict_rationale: str
    positive_factors: List[str] = field(default_factory=list)
    negative_factors: List[str] = field(default_factory=list)
    conflicting_signals: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    strategy_context: str = ""
    regime_context: str = ""
    risk_notes: str = ""
    decision_triggers: List[str] = field(default_factory=list)  # Conditions that would change the decision

    @property
    def narrative(self) -> str:
        """Alias for verdict_rationale for conversational and API consumers."""
        return self.verdict_rationale

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict_rationale": self.verdict_rationale,
            "narrative": self.verdict_rationale,
            "positive_factors": self.positive_factors,
            "negative_factors": self.negative_factors,
            "conflicting_signals": self.conflicting_signals,
            "missing_evidence": self.missing_evidence,
            "strategy_context": self.strategy_context,
            "regime_context": self.regime_context,
            "risk_notes": self.risk_notes,
            "decision_triggers": self.decision_triggers,
        }


@dataclass
class InvestmentDecision:
    """Master decision object emitted by M09."""
    symbol: str
    pipeline_id: str
    timestamp: pd.Timestamp
    verdict: str  # YES, NO, WAIT, INSUFFICIENT_DATA
    display_label: str  # Strong Buy, Buy, Hold, Sell, Strong Sell, No Action
    action_type: str  # ENTRY_LONG, ENTRY_SHORT, EXIT, HOLD, OBSERVE
    composite_score: float  # [0.0, 100.0]
    confidence: float  # [0.0, 1.0]
    investment_horizon: Union[int, str]
    entry_reference_price: Optional[float]
    suggested_stop_loss: Optional[float]
    suggested_take_profit: Optional[float]
    factor_contributions: Dict[str, float]
    factor_scores: Dict[str, float]
    risk_status: str  # RISK_PENDING, RISK_APPROVED, RISK_BLOCKED
    explanation: DecisionExplanation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "pipeline_id": self.pipeline_id,
            "timestamp": self.timestamp.isoformat() if hasattr(self.timestamp, "isoformat") else str(self.timestamp),
            "verdict": self.verdict,
            "display_label": self.display_label,
            "action_type": self.action_type,
            "composite_score": round(self.composite_score, 2),
            "confidence": round(self.confidence, 3),
            "investment_horizon": str(self.investment_horizon),
            "entry_reference_price": round(self.entry_reference_price, 4) if self.entry_reference_price is not None else None,
            "suggested_stop_loss": round(self.suggested_stop_loss, 4) if self.suggested_stop_loss is not None else None,
            "suggested_take_profit": round(self.suggested_take_profit, 4) if self.suggested_take_profit is not None else None,
            "factor_contributions": {k: round(v, 2) for k, v in self.factor_contributions.items()},
            "factor_scores": {k: round(v, 2) for k, v in self.factor_scores.items()},
            "risk_status": self.risk_status,
            "explanation": self.explanation.to_dict(),
        }
