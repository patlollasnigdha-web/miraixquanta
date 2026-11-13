"""
MIRAI — Investment Decisions Endpoints (M15)
"""

from fastapi import APIRouter, Depends
import numpy as np
import pandas as pd

from src.api.dependencies import (
    get_data_access_service,
    get_decision_engine,
    get_risk_engine,
    get_stock_strength_analyzer,
    get_regime_detector,
    get_sentiment_analyzer,
    get_fundamental_analyzer,
)
from src.data_engineering.data_access import DataAccessService
from src.decision.decision_engine import InvestmentDecisionEngine
from src.decision.decision_schemas import DecisionInput, DecisionVerdict, DisplayLabel, RiskStatus
from src.risk_management.risk_engine import RiskManagementEngine
from src.intelligence.stock_strength import StockStrengthAnalyzer
from src.intelligence.regime_detection import RegimeDetector
from src.intelligence.sentiment_analysis import NewsSentimentAnalyzer
from src.intelligence.fundamental_analysis import FundamentalAnalyzer
from src.strategies.momentum_strategy import MomentumStrategy
from src.models.model_registry import ModelRegistry
from src.api.api_schemas import DecisionEvaluateRequest, DecisionResponse
from src.utils.logger import get_logger

logger = get_logger("DecisionsRoute")

router = APIRouter(prefix="/decisions", tags=["Decisions"])


@router.post("/evaluate", response_model=DecisionResponse)
def evaluate_decision(
    req: DecisionEvaluateRequest,
    data_service: DataAccessService = Depends(get_data_access_service),
    decision_engine: InvestmentDecisionEngine = Depends(get_decision_engine),
    risk_engine: RiskManagementEngine = Depends(get_risk_engine),
    stock_strength: StockStrengthAnalyzer = Depends(get_stock_strength_analyzer),
    regime_detector: RegimeDetector = Depends(get_regime_detector),
    sentiment_analyzer: NewsSentimentAnalyzer = Depends(get_sentiment_analyzer),
    fundamental_analyzer: FundamentalAnalyzer = Depends(get_fundamental_analyzer),
):
    """
    Authoritative Investment Decision endpoint.
    Aggregates multi-pillar evidence (M03, M05, M06, M07, M08) and validates through M11 risk engine.
    """
    sym = req.symbol.strip().upper()
    df = data_service.get_multistock_daily(symbols=[sym])

    # If symbol has no market data, return safe INSUFFICIENT_DATA without fabricating NIFTY index data
    if df.empty or len(df) < 5:
        inp = DecisionInput(
            symbol=sym,
            timestamp=pd.Timestamp.now(),
            current_price=None,
            pipeline_id=req.pipeline_id,
            investment_horizon=req.investment_horizon,
        )
        decision = decision_engine.make_decision_with_risk(
            inp=inp,
            risk_engine=risk_engine,
            current_capital=1_000_000.0,
        )
        return DecisionResponse(
            symbol=sym,
            verdict=DecisionVerdict.INSUFFICIENT_DATA,
            display_label=DisplayLabel.NO_ACTION,
            composite_score=None,
            confidence=0.0,
            action_type="OBSERVE",
            risk_status=decision.risk_status,
            entry_reference_price=None,
            suggested_stop_loss=None,
            suggested_take_profit=None,
            explanation=f"Unable to evaluate investment decision for '{sym}': No historical price or volume data exists in the NIFTY multi-stock dataset. Symbol may be invalid or unlisted.",
            positive_factors=[],
            negative_factors=[f"Unrecognized or unlisted stock symbol: {sym}"],
            conflicting_signals=[],
            warnings=["No market data available for symbol."],
            timestamp=str(pd.Timestamp.now()),
        )

    close_p = float(df["close"].iloc[-1])
    bar_ts = df["timestamp"].iloc[-1] if "timestamp" in df.columns else (
        df.index[-1] if hasattr(df.index[-1], "isoformat") else pd.Timestamp.now()
    )
    bench = data_service.get_nifty_daily_index()

    # 1. Stock Strength Intelligence (M05)
    ss_res = None
    try:
        ss_res = stock_strength.evaluate_stock_strength(df_stock=df, symbol=sym, df_benchmark=bench)
    except Exception as e:
        logger.warning("Stock strength calculation failed for %s: %s", sym, e)

    # 2. Market Regime Detection (M07)
    reg_res = None
    try:
        reg_res = regime_detector.detect_regime(bench if not bench.empty else df)
    except Exception as e:
        logger.warning("Market regime detection failed: %s", e)

    # 3. Sentiment & Fundamentals (M06)
    sent_res = None
    try:
        sent_res = sentiment_analyzer.analyze_symbol_sentiment(sym)
    except Exception as e:
        logger.warning("Sentiment analysis failed for %s: %s", sym, e)

    fund_res = None
    try:
        fund_res = fundamental_analyzer.get_fundamental_score(sym)
    except Exception as e:
        logger.warning("Fundamental analysis failed for %s: %s", sym, e)

    # 4. Strategy Signal (M08)
    signal = None
    try:
        strat = MomentumStrategy()
        if len(df) >= 55:
            signal = strat.generate_signal(df, symbol=sym)
    except Exception as e:
        logger.warning("Strategy evaluation failed for %s: %s", sym, e)

    # 5. Predictive Model (M03 / M04)
    model_pred = None
    try:
        reg = ModelRegistry()
        models = reg.list_models(pipeline_id=req.pipeline_id)
        valid_models = [m for m in models if m.get("status") in ("approved", "validated")]
        if valid_models and req.pipeline_id == "pipeline_a_fi2010":
            target_meta = valid_models[0]
            reg_schema = target_meta.get("feature_schema", [])
            if len(df.columns) >= len(reg_schema):
                artifact = reg.load_model_artifact(target_meta["model_id"])
                X_inp = df[reg_schema].iloc[-1:].to_numpy().astype(np.float32)
                preds = artifact.predict(X_inp)
                probas = artifact.predict_proba(X_inp) if hasattr(artifact, "predict_proba") else None
                model_pred = {
                    "predicted_class": int(preds[0]),
                    "probabilities": probas[0].tolist() if probas is not None else [0.33, 0.34, 0.33],
                    "model_id": target_meta["model_id"],
                    "model_name": target_meta.get("model_name"),
                    "version": target_meta.get("version"),
                    "horizon": target_meta.get("prediction_horizon"),
                    "status": target_meta.get("status"),
                }
    except Exception as e:
        logger.warning("Predictive model check encountered error: %s", e)

    inp = DecisionInput(
        symbol=sym,
        timestamp=bar_ts,
        current_price=close_p,
        model_prediction=model_pred,
        stock_strength=ss_res,
        sentiment=sent_res,
        fundamentals=fund_res,
        market_regime=reg_res,
        strategy_signal=signal,
        pipeline_id=req.pipeline_id,
        investment_horizon=req.investment_horizon,
    )

    decision = decision_engine.make_decision_with_risk(
        inp=inp,
        risk_engine=risk_engine,
        current_capital=1_000_000.0,
    )

    return DecisionResponse(
        symbol=sym,
        verdict=decision.verdict,
        display_label=decision.display_label,
        composite_score=decision.composite_score,
        confidence=decision.confidence,
        action_type=decision.action_type,
        risk_status=decision.risk_status,
        entry_reference_price=decision.entry_reference_price,
        suggested_stop_loss=decision.suggested_stop_loss,
        suggested_take_profit=decision.suggested_take_profit,
        explanation=decision.explanation.narrative if decision.explanation else "",
        positive_factors=decision.explanation.positive_factors if decision.explanation else [],
        negative_factors=decision.explanation.negative_factors if decision.explanation else [],
        conflicting_signals=decision.explanation.conflicting_signals if decision.explanation else [],
        warnings=[],
        timestamp=str(decision.timestamp),
    )
