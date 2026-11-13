"""
MIRAI — Unit Tests for Investment Decision Engine (M09)
"""

import numpy as np
import pandas as pd
import pytest

from src.intelligence.regime_detection import MarketRegime, RegimeDetectionResult
from src.intelligence.stock_strength import StockStrengthResult
from src.intelligence.sentiment_analysis import SentimentResult
from src.intelligence.fundamental_analysis import FundamentalAssessment
from src.strategies.base_strategy import StrategySignal, SignalAction
from src.decision.decision_schemas import (
    DecisionInput,
    DecisionVerdict,
    DisplayLabel,
    RiskStatus,
    InvestmentDecision,
)
from src.decision.decision_engine import InvestmentDecisionEngine


def _mock_bullish_input(symbol: str = "RELIANCE") -> DecisionInput:
    """Creates fully aligned bullish decision input."""
    now = pd.Timestamp.now()
    return DecisionInput(
        symbol=symbol,
        pipeline_id="pipeline_b_nifty",
        timestamp=now,
        investment_horizon="1d",
        current_price=2500.0,
        model_prediction={"predicted_class": 1, "probabilities": [0.75, 0.15, 0.10], "status": "approved"},
        stock_strength=StockStrengthResult(
            symbol=symbol, evaluation_timestamp=now, evaluation_timeframe="1d",
            overall_score=82.0, classification="Very Strong", factor_scores={"momentum": 85.0},
            factor_contributions={"momentum": 17.0}, factor_weights={"momentum": 0.20},
            trend_status="Strengthening", data_coverage=1.0, confidence=0.90,
        ),
        sentiment=SentimentResult(
            symbol=symbol, evaluation_timestamp=now, sentiment_score=72.0,
            sentiment_label="POSITIVE", confidence=0.85, p_positive=0.72, p_negative=0.10, p_neutral=0.18, news_count=3,
        ),
        fundamentals=FundamentalAssessment(
            symbol=symbol, evaluation_date=now, publication_date=now - pd.Timedelta(days=30),
            staleness_days=30, fundamental_score=78.0, classification="HEALTHY", data_coverage=0.90,
        ),
        market_regime=RegimeDetectionResult(
            instrument="NIFTY 50", evaluation_timestamp=now, timeframe="1d",
            detected_regime=MarketRegime.BULLISH_TRENDING, regime_confidence=0.85,
            regime_probabilities={"BULLISH_TRENDING": 0.85}, quantitative_evidence={}, persistence_bars=5,
        ),
        strategy_signal=StrategySignal(
            symbol=symbol, pipeline_id="pipeline_b_nifty", strategy_name="MomentumStrategy",
            strategy_version="1.0", signal=SignalAction.BUY, signal_strength=0.85,
            prediction_horizon="1d", timestamp=now, entry_reference_price=2500.0,
            suggested_stop_loss=2450.0, suggested_take_profit=2620.0,
        ),
    )


def test_decision_verdict_yes():
    """Verify strong multi-pillar bullish alignment yields YES verdict and Buy display label."""
    engine = InvestmentDecisionEngine()
    inp = _mock_bullish_input("RELIANCE")

    decision = engine.make_decision(inp)
    assert isinstance(decision, InvestmentDecision)
    assert decision.symbol == "RELIANCE"
    assert decision.verdict == DecisionVerdict.YES
    assert decision.display_label in (DisplayLabel.BUY, DisplayLabel.STRONG_BUY)
    assert decision.action_type == "ENTRY_LONG"
    assert decision.composite_score >= 68.0
    assert decision.confidence > 0.80
    assert decision.entry_reference_price == 2500.0
    assert decision.suggested_stop_loss == 2450.0
    assert len(decision.explanation.positive_factors) >= 3
    assert len(decision.explanation.conflicting_signals) == 0


def test_decision_verdict_no():
    """Verify adverse/bearish multi-pillar signals yield NO verdict."""
    engine = InvestmentDecisionEngine()
    now = pd.Timestamp.now()

    inp = DecisionInput(
        symbol="BEAR_CO",
        pipeline_id="pipeline_b_nifty",
        timestamp=now,
        current_price=500.0,
        model_prediction={"predicted_class": 3, "probabilities": [0.10, 0.15, 0.75]},
        stock_strength=StockStrengthResult(
            symbol="BEAR_CO", evaluation_timestamp=now, evaluation_timeframe="1d",
            overall_score=22.0, classification="Very Weak", factor_scores={}, factor_contributions={},
            factor_weights={}, trend_status="Weakening", data_coverage=0.80, confidence=0.70,
        ),
        market_regime=RegimeDetectionResult(
            instrument="NIFTY 50", evaluation_timestamp=now, timeframe="1d",
            detected_regime=MarketRegime.BEARISH_TRENDING, regime_confidence=0.80,
            regime_probabilities={}, quantitative_evidence={}, persistence_bars=4,
        ),
        strategy_signal=StrategySignal(
            symbol="BEAR_CO", pipeline_id="pipeline_b_nifty", strategy_name="MomentumStrategy",
            strategy_version="1.0", signal=SignalAction.SELL, signal_strength=0.80,
            prediction_horizon="1d", timestamp=now, entry_reference_price=500.0,
        ),
    )

    decision = engine.make_decision(inp)
    assert decision.verdict == DecisionVerdict.NO
    assert decision.composite_score < 40.0
    assert decision.action_type in ("EXIT", "OBSERVE")
    assert len(decision.explanation.negative_factors) >= 2


def test_decision_verdict_wait_on_conflicting_signals():
    """Verify conflicting evidence (e.g. Model Downward vs Strategy BUY) forces WAIT."""
    engine = InvestmentDecisionEngine()
    inp = _mock_bullish_input("TCS")

    # Inject sharp conflict: predictive model predicts DOWNWARD class 3
    inp.model_prediction = {"predicted_class": 3, "probabilities": [0.10, 0.15, 0.75]}

    decision = engine.make_decision(inp)
    assert decision.verdict == DecisionVerdict.WAIT
    assert decision.display_label == DisplayLabel.HOLD
    assert len(decision.explanation.conflicting_signals) > 0
    assert any("CONFLICT" in c for c in decision.explanation.conflicting_signals)


def test_decision_insufficient_data():
    """Verify missing essential inputs returns INSUFFICIENT_DATA."""
    engine = InvestmentDecisionEngine()
    now = pd.Timestamp.now()

    # Input with NO strategy signal and NO stock strength
    empty_inp = DecisionInput(
        symbol="EMPTY",
        pipeline_id="pipeline_b_nifty",
        timestamp=now,
    )

    decision = engine.make_decision(empty_inp)
    assert decision.verdict == DecisionVerdict.INSUFFICIENT_DATA
    assert decision.confidence == 0.0
    assert len(decision.explanation.missing_evidence) > 0


def test_risk_constraint_blocking():
    """Verify violated risk constraints force RISK_BLOCKED status and block YES."""
    engine = InvestmentDecisionEngine()
    inp = _mock_bullish_input("INFY")

    # Attach risk constraint violation
    inp.risk_constraints = {
        "violation": True,
        "violation_reason": "Portfolio max drawdown threshold (15%) exceeded",
    }

    decision = engine.make_decision(inp)
    assert decision.risk_status == RiskStatus.RISK_BLOCKED
    assert decision.verdict in (DecisionVerdict.NO, DecisionVerdict.WAIT)
    assert any("RISK VETO" in c for c in decision.explanation.conflicting_signals)


def test_missing_factors_re_normalization():
    """Verify missing sentiment and fundamentals dynamically re-normalizes without penalizing to 0."""
    engine = InvestmentDecisionEngine()
    inp = _mock_bullish_input("TITAN")

    # Omit sentiment and fundamentals entirely
    inp.sentiment = None
    inp.fundamentals = None

    decision = engine.make_decision(inp)
    assert decision.verdict == DecisionVerdict.YES
    # Missing factors are NOT in factor contributions
    assert "sentiment_fundamentals" not in decision.factor_contributions
    assert decision.composite_score >= 68.0
    # Confidence is slightly discounted due to lower factor coverage
    assert decision.confidence < 0.90


def test_deterministic_decisions():
    """Verify identical inputs yield identical deterministic composite scores and verdicts."""
    engine = InvestmentDecisionEngine()
    inp1 = _mock_bullish_input("BAJFINANCE")
    inp2 = _mock_bullish_input("BAJFINANCE")

    d1 = engine.make_decision(inp1)
    d2 = engine.make_decision(inp2)

    assert d1.verdict == d2.verdict
    assert d1.composite_score == d2.composite_score
    assert d1.confidence == d2.confidence
    assert d1.display_label == d2.display_label
