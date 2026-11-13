"""
MIRAI — Integrated Market Intelligence Service (Batch 3)
Unifies Stock Strength Intelligence (M05), Financial Sentiment & Fundamentals (M06),
and Market Regime Detection (M07) into an integrated decision-support facade.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.data_engineering.data_access import DataAccessService
from src.intelligence.stock_strength import StockStrengthEngine, StockStrengthResult
from src.intelligence.sentiment_analysis import SentimentAnalyzer, NewsItem, SentimentResult
from src.intelligence.fundamental_analysis import FundamentalAnalyzer, FundamentalRecord, FundamentalAssessment, get_combined_financial_intelligence
from src.intelligence.regime_detection import RuleBasedRegimeDetector, GMMRegimeDetector, RegimeDetectionResult, MarketRegime

logger = get_logger("MarketIntelligence")


@dataclass
class IntegratedStockIntelligence:
    """Comprehensive cross-asset intelligence report for a single equity."""
    symbol: str
    as_of_date: pd.Timestamp
    stock_strength: StockStrengthResult
    sentiment: SentimentResult
    fundamentals: FundamentalAssessment
    market_regime_daily: RegimeDetectionResult
    market_regime_intraday: Optional[RegimeDetectionResult] = None
    composite_assessment: str = ""
    key_drivers: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    data_quality_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "as_of_date": self.as_of_date.isoformat() if hasattr(self.as_of_date, "isoformat") else str(self.as_of_date),
            "stock_strength": self.stock_strength.to_dict(),
            "sentiment": self.sentiment.to_dict(),
            "fundamentals": self.fundamentals.to_dict(),
            "market_regime_daily": self.market_regime_daily.to_dict(),
            "market_regime_intraday": self.market_regime_intraday.to_dict() if self.market_regime_intraday else None,
            "composite_assessment": self.composite_assessment,
            "key_drivers": self.key_drivers,
            "risk_factors": self.risk_factors,
            "data_quality_warnings": self.data_quality_warnings,
        }


class MarketIntelligenceService:
    """
    Unified intelligence coordinator.
    Accepts raw or cached data and returns integrated stock and market condition reports.
    """

    def __init__(
        self,
        data_access: Optional[DataAccessService] = None,
        stock_strength_engine: Optional[StockStrengthEngine] = None,
        sentiment_analyzer: Optional[SentimentAnalyzer] = None,
        fundamental_analyzer: Optional[FundamentalAnalyzer] = None,
        regime_detector: Optional[RuleBasedRegimeDetector] = None,
    ):
        self.data_access = data_access or DataAccessService()
        self.strength_engine = stock_strength_engine or StockStrengthEngine()
        self.sentiment_engine = sentiment_analyzer or SentimentAnalyzer()
        self.fundamental_engine = fundamental_analyzer or FundamentalAnalyzer()
        self.regime_detector = regime_detector or RuleBasedRegimeDetector()

    def get_stock_intelligence(
        self,
        df_stock: pd.DataFrame,
        symbol: str,
        df_benchmark: Optional[pd.DataFrame] = None,
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        news_items: Optional[List[NewsItem]] = None,
        fundamental_records: Optional[List[FundamentalRecord]] = None,
        df_intraday_benchmark: Optional[pd.DataFrame] = None,
        prior_strength_score: Optional[float] = None,
        prior_regimes: Optional[List[str]] = None,
    ) -> IntegratedStockIntelligence:
        """
        Coordinates full intelligence workflow for an individual stock.
        """
        as_of_ts = pd.to_datetime(as_of_date) if as_of_date else pd.Timestamp.now()

        # 1. Stock Strength Evaluation (M05)
        strength_res = self.strength_engine.evaluate_stock_strength(
            df_stock=df_stock,
            symbol=symbol,
            df_benchmark=df_benchmark,
            as_of_date=as_of_ts,
            prior_score=prior_strength_score,
        )

        # 2. News Sentiment Evaluation (M06A)
        sent_res = self.sentiment_engine.evaluate_symbol_sentiment(
            news_items=news_items or [],
            symbol=symbol,
            as_of_date=as_of_ts,
        )

        # 3. Fundamental Evaluation (M06B)
        fund_res = self.fundamental_engine.evaluate_fundamentals(
            records=fundamental_records or [],
            symbol=symbol,
            as_of_date=as_of_ts,
        )

        # 4. Daily Market Regime Detection (M07)
        if df_benchmark is not None and not df_benchmark.empty:
            daily_regime = self.regime_detector.predict_regime(
                df=df_benchmark,
                instrument="NIFTY 50",
                timeframe="1d",
                as_of_date=as_of_ts,
                prior_regimes=prior_regimes,
            )
        else:
            # Fallback on stock OHLCV if benchmark is absent
            daily_regime = self.regime_detector.predict_regime(
                df=df_stock,
                instrument=symbol,
                timeframe="1d",
                as_of_date=as_of_ts,
                prior_regimes=prior_regimes,
            )

        # 5. Optional Intraday Market Regime Detection (M07)
        intraday_regime = None
        if df_intraday_benchmark is not None and not df_intraday_benchmark.empty:
            intraday_regime = self.regime_detector.predict_regime(
                df=df_intraday_benchmark,
                instrument="NIFTY 50 Intraday",
                timeframe="1min",
                as_of_date=as_of_ts,
            )

        # 6. Synthesize Drivers, Risks, and Assessment
        drivers = []
        risks = []
        warnings = []

        # Strength factors
        if strength_res.overall_score >= 65.0:
            drivers.append(f"Strong Technical Profile ({strength_res.overall_score:.1f}/100, {strength_res.classification})")
        elif strength_res.overall_score <= 35.0:
            risks.append(f"Deteriorating Technical Profile ({strength_res.overall_score:.1f}/100, {strength_res.classification})")

        if strength_res.strongest_factor:
            drivers.append(f"Key Strength: {strength_res.strongest_factor.replace('_', ' ').title()}")
        if strength_res.weakest_factor:
            risks.append(f"Technical Drag: {strength_res.weakest_factor.replace('_', ' ').title()}")

        # Sentiment factors
        if sent_res.status == "VALID" and sent_res.sentiment_score >= 58.0:
            drivers.append(f"Positive Sentiment ({sent_res.sentiment_score:.1f}/100 from {sent_res.news_count} news items)")
        elif sent_res.status == "VALID" and sent_res.sentiment_score <= 42.0:
            risks.append(f"Negative Sentiment Drag ({sent_res.sentiment_score:.1f}/100 from {sent_res.news_count} news items)")
        elif sent_res.status == "INSUFFICIENT_DATA":
            warnings.append("Sentiment data unavailable (no recent news).")

        # Fundamental factors
        drivers.extend(fund_res.positive_factors)
        risks.extend(fund_res.negative_factors)
        warnings.extend(fund_res.warnings)
        if fund_res.status == "INSUFFICIENT_DATA":
            warnings.append("Fundamental filings unavailable for evaluation date.")

        # Market Regime
        if daily_regime.detected_regime == MarketRegime.BULLISH_TRENDING:
            drivers.append("Macro Environment: Bullish Trending Market")
        elif daily_regime.detected_regime in (MarketRegime.HIGH_VOLATILITY, MarketRegime.STRESS_ABNORMAL):
            risks.append(f"Macro Risk: Market in {daily_regime.detected_regime} State")

        # Warnings rollup
        warnings.extend(strength_res.missing_data_warnings)

        # Composite summary narrative
        assessment = (
            f"{symbol} exhibits a {strength_res.classification.upper()} technical stance "
            f"(Score: {strength_res.overall_score:.1f}/100, Trend: {strength_res.trend_status}) "
            f"within a {daily_regime.detected_regime} macro regime. "
        )
        if sent_res.status == "VALID":
            assessment += f"News sentiment is {sent_res.sentiment_label} ({sent_res.sentiment_score:.1f}/100). "
        else:
            assessment += "News sentiment is unavailable. "

        if fund_res.status == "VALID" and fund_res.fundamental_score is not None:
            assessment += f"Fundamental standing is {fund_res.classification} ({fund_res.fundamental_score:.1f}/100)."
        else:
            assessment += "Point-in-time fundamentals are currently unavailable (INSUFFICIENT_DATA)."

        return IntegratedStockIntelligence(
            symbol=symbol,
            as_of_date=as_of_ts,
            stock_strength=strength_res,
            sentiment=sent_res,
            fundamentals=fund_res,
            market_regime_daily=daily_regime,
            market_regime_intraday=intraday_regime,
            composite_assessment=assessment,
            key_drivers=drivers,
            risk_factors=risks,
            data_quality_warnings=warnings,
        )
