"""
MIRAI — Fundamental Analysis Intelligence (M06)
Evaluates point-in-time company financial health, valuation ratios, profitability,
and solvency metrics with strict publication date enforcement and staleness guards.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger("FundamentalAnalysis")


@dataclass
class FundamentalRecord:
    """Standardized point-in-time fundamental financial statement record."""
    symbol: str
    publication_date: pd.Timestamp  # CRITICAL: The date results were officially disclosed to the public
    period_end_date: pd.Timestamp   # The fiscal quarter/year ending date (e.g. 2023-03-31)
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    eps_growth_yoy: Optional[float] = None      # e.g., 0.15 for +15%
    revenue_growth_yoy: Optional[float] = None  # e.g., 0.12 for +12%
    operating_margin: Optional[float] = None    # e.g., 0.22 for 22%
    net_margin: Optional[float] = None          # e.g., 0.16 for 16%
    roe: Optional[float] = None                 # Return on Equity, e.g., 0.18 for 18%
    roce: Optional[float] = None                # Return on Capital Employed
    debt_to_equity: Optional[float] = None      # e.g., 0.45
    current_ratio: Optional[float] = None       # e.g., 1.6
    free_cash_flow_cr: Optional[float] = None   # Free Cash Flow in ₹ Crores

    def __post_init__(self):
        self.publication_date = pd.to_datetime(self.publication_date)
        self.period_end_date = pd.to_datetime(self.period_end_date)
        if self.publication_date < self.period_end_date:
            raise ValueError(
                f"Invalid point-in-time record for {self.symbol}: "
                f"publication_date ({self.publication_date}) cannot be earlier than period_end_date ({self.period_end_date})."
            )


@dataclass
class FundamentalAssessment:
    """Standardized output structure for company fundamental assessment."""
    symbol: str
    evaluation_date: pd.Timestamp
    publication_date: Optional[pd.Timestamp]
    staleness_days: Optional[int]
    fundamental_score: Optional[float]  # [0.0, 100.0] or None if insufficient data
    classification: str  # 'HEALTHY', 'FAIR', 'WEAK', 'DISTRESSED', 'INSUFFICIENT_DATA'
    data_coverage: float  # [0.0, 1.0]
    category_scores: Dict[str, float] = field(default_factory=dict)
    key_ratios: Dict[str, Any] = field(default_factory=dict)
    positive_factors: List[str] = field(default_factory=list)
    negative_factors: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    status: str = "VALID"  # 'VALID' or 'INSUFFICIENT_DATA'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "evaluation_date": self.evaluation_date.isoformat() if hasattr(self.evaluation_date, "isoformat") else str(self.evaluation_date),
            "publication_date": self.publication_date.isoformat() if self.publication_date and hasattr(self.publication_date, "isoformat") else (str(self.publication_date) if self.publication_date else None),
            "staleness_days": self.staleness_days,
            "fundamental_score": round(self.fundamental_score, 2) if self.fundamental_score is not None else None,
            "classification": self.classification,
            "data_coverage": round(self.data_coverage, 3),
            "category_scores": {k: round(v, 2) for k, v in self.category_scores.items()},
            "key_ratios": self.key_ratios,
            "positive_factors": self.positive_factors,
            "negative_factors": self.negative_factors,
            "missing_fields": self.missing_fields,
            "warnings": self.warnings,
            "status": self.status,
        }


class FundamentalAnalyzer:
    """
    Point-in-Time Fundamental Analysis Engine.
    Strictly safeguards against lookahead bias: only financial reports disclosed
    prior to or on the evaluation date are accessed.
    """

    def __init__(
        self,
        max_stale_days: int = 180,
        pe_healthy_max: float = 30.0,
        pb_healthy_max: float = 4.0,
        roe_healthy_min: float = 0.15,
        de_healthy_max: float = 1.5,
    ):
        cfg = get_config()
        self.max_stale_days = cfg.get("fundamentals.max_stale_days", max_stale_days)
        self.pe_healthy_max = cfg.get("fundamentals.pe_healthy_max", pe_healthy_max)
        self.pb_healthy_max = cfg.get("fundamentals.pb_healthy_max", pb_healthy_max)
        self.roe_healthy_min = cfg.get("fundamentals.roe_healthy_min", roe_healthy_min)
        self.de_healthy_max = cfg.get("fundamentals.de_healthy_max", de_healthy_max)

    @staticmethod
    def _scale_to_100(val: float, min_val: float, max_val: float) -> float:
        """Clips and scales continuous metric to [0, 100]."""
        if val is None or np.isnan(val) or np.isinf(val):
            return 50.0
        clipped = np.clip(val, min_val, max_val)
        return float(((clipped - min_val) / (max_val - min_val)) * 100.0)

    def evaluate_fundamentals(
        self,
        records: List[FundamentalRecord],
        symbol: str,
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
    ) -> FundamentalAssessment:
        """
        Evaluates company fundamental health as of an exact point in time.
        Strictly filters records where `publication_date <= as_of_date`.
        """
        as_of_ts = pd.to_datetime(as_of_date) if as_of_date else pd.Timestamp.now()
        sym_upper = symbol.upper()

        # 1. Point-in-time filter: strictly disclosed on or before as_of_ts
        eligible = [
            r for r in records
            if r.symbol.upper() == sym_upper and r.publication_date <= as_of_ts
        ]

        if not eligible:
            return FundamentalAssessment(
                symbol=symbol,
                evaluation_date=as_of_ts,
                publication_date=None,
                staleness_days=None,
                fundamental_score=None,
                classification="INSUFFICIENT_DATA",
                data_coverage=0.0,
                status="INSUFFICIENT_DATA",
                warnings=[f"No point-in-time fundamental filing available for {symbol} as of {as_of_ts.strftime('%Y-%m-%d')}."],
            )

        # 2. Pick the latest officially published filing
        latest: FundamentalRecord = max(eligible, key=lambda x: x.publication_date)
        staleness = (as_of_ts - latest.publication_date).days

        warnings = []
        if staleness > self.max_stale_days:
            warnings.append(
                f"STALE DATA WARNING: Filing is {staleness} days old (exceeds {self.max_stale_days} days threshold)."
            )

        # 3. Factor evaluation across categories
        # A. Valuation Category (30%)
        val_scores = []
        if latest.pe_ratio is not None and latest.pe_ratio > 0:
            # Lower PE = higher score: PE 10 -> 90, PE 45 -> 15
            s_pe = self._scale_to_100(-latest.pe_ratio, -45.0, -10.0)
            val_scores.append(s_pe)
        if latest.pb_ratio is not None and latest.pb_ratio > 0:
            s_pb = self._scale_to_100(-latest.pb_ratio, -8.0, -1.0)
            val_scores.append(s_pb)

        # B. Growth Category (25%)
        growth_scores = []
        if latest.revenue_growth_yoy is not None:
            # -10% to +30%
            s_rev = self._scale_to_100(latest.revenue_growth_yoy, -0.10, 0.30)
            growth_scores.append(s_rev)
        if latest.eps_growth_yoy is not None:
            s_eps = self._scale_to_100(latest.eps_growth_yoy, -0.15, 0.35)
            growth_scores.append(s_eps)

        # C. Profitability Category (25%)
        profit_scores = []
        if latest.roe is not None:
            # ROE: 5% to 25%
            s_roe = self._scale_to_100(latest.roe, 0.05, 0.25)
            profit_scores.append(s_roe)
        if latest.operating_margin is not None:
            s_opm = self._scale_to_100(latest.operating_margin, 0.05, 0.30)
            profit_scores.append(s_opm)

        # D. Solvency & Health Category (20%)
        solv_scores = []
        if latest.debt_to_equity is not None:
            # Lower D/E is better: 0.0 to 2.5
            s_de = self._scale_to_100(-latest.debt_to_equity, -2.5, 0.0)
            solv_scores.append(s_de)
        if latest.current_ratio is not None:
            # Current ratio: 0.8 to 2.5
            s_cr = self._scale_to_100(latest.current_ratio, 0.8, 2.5)
            solv_scores.append(s_cr)

        # 4. Check missing fields
        all_metrics = [
            ("pe_ratio", latest.pe_ratio),
            ("pb_ratio", latest.pb_ratio),
            ("revenue_growth_yoy", latest.revenue_growth_yoy),
            ("eps_growth_yoy", latest.eps_growth_yoy),
            ("roe", latest.roe),
            ("operating_margin", latest.operating_margin),
            ("debt_to_equity", latest.debt_to_equity),
            ("current_ratio", latest.current_ratio),
        ]
        missing = [name for name, val in all_metrics if val is None]
        coverage = (len(all_metrics) - len(missing)) / len(all_metrics)

        # 5. Aggregate category scores
        category_scores = {}
        weighted_cat_scores = []
        cat_weights = []

        if val_scores:
            cat_val = float(np.mean(val_scores))
            category_scores["valuation"] = cat_val
            weighted_cat_scores.append(cat_val * 0.30)
            cat_weights.append(0.30)

        if growth_scores:
            cat_growth = float(np.mean(growth_scores))
            category_scores["growth"] = cat_growth
            weighted_cat_scores.append(cat_growth * 0.25)
            cat_weights.append(0.25)

        if profit_scores:
            cat_profit = float(np.mean(profit_scores))
            category_scores["profitability"] = cat_profit
            weighted_cat_scores.append(cat_profit * 0.25)
            cat_weights.append(0.25)

        if solv_scores:
            cat_solv = float(np.mean(solv_scores))
            category_scores["solvency"] = cat_solv
            weighted_cat_scores.append(cat_solv * 0.20)
            cat_weights.append(0.20)

        if not weighted_cat_scores or sum(cat_weights) == 0:
            return FundamentalAssessment(
                symbol=symbol,
                evaluation_date=as_of_ts,
                publication_date=latest.publication_date,
                staleness_days=staleness,
                fundamental_score=None,
                classification="INSUFFICIENT_DATA",
                data_coverage=coverage,
                status="INSUFFICIENT_DATA",
                warnings=["Insufficient valid ratios in filing."],
            )

        overall_score = float(sum(weighted_cat_scores) / sum(cat_weights))
        overall_score = float(np.clip(overall_score, 0.0, 100.0))

        # Classification
        if overall_score >= 75.0:
            classification = "HEALTHY"
        elif overall_score >= 55.0:
            classification = "FAIR"
        elif overall_score >= 35.0:
            classification = "WEAK"
        else:
            classification = "DISTRESSED"

        # 6. Qualitative factor summaries
        pos_factors = []
        neg_factors = []
        if latest.roe is not None and latest.roe >= self.roe_healthy_min:
            pos_factors.append(f"Strong Return on Equity ({latest.roe * 100:.1f}%)")
        elif latest.roe is not None and latest.roe < 0.08:
            neg_factors.append(f"Subdued Return on Equity ({latest.roe * 100:.1f}%)")

        if latest.debt_to_equity is not None and latest.debt_to_equity <= 0.5:
            pos_factors.append(f"Conservative Debt-to-Equity ({latest.debt_to_equity:.2f}x)")
        elif latest.debt_to_equity is not None and latest.debt_to_equity > self.de_healthy_max:
            neg_factors.append(f"Elevated Leverage: D/E {latest.debt_to_equity:.2f}x exceeds {self.de_healthy_max}x threshold")

        if latest.pe_ratio is not None and latest.pe_ratio > self.pe_healthy_max:
            neg_factors.append(f"High P/E Multiple ({latest.pe_ratio:.1f}x)")
        elif latest.pe_ratio is not None and latest.pe_ratio < 18.0:
            pos_factors.append(f"Attractive P/E Valuation ({latest.pe_ratio:.1f}x)")

        if latest.revenue_growth_yoy is not None and latest.revenue_growth_yoy > 0.15:
            pos_factors.append(f"Robust Revenue Expansion (+{latest.revenue_growth_yoy * 100:.1f}% YoY)")

        key_ratios = {
            "pe_ratio": latest.pe_ratio,
            "pb_ratio": latest.pb_ratio,
            "roe_pct": round(latest.roe * 100, 2) if latest.roe is not None else None,
            "debt_to_equity": latest.debt_to_equity,
            "revenue_growth_pct": round(latest.revenue_growth_yoy * 100, 2) if latest.revenue_growth_yoy is not None else None,
            "operating_margin_pct": round(latest.operating_margin * 100, 2) if latest.operating_margin is not None else None,
        }

        return FundamentalAssessment(
            symbol=symbol,
            evaluation_date=as_of_ts,
            publication_date=latest.publication_date,
            staleness_days=staleness,
            fundamental_score=overall_score,
            classification=classification,
            data_coverage=coverage,
            category_scores=category_scores,
            key_ratios=key_ratios,
            positive_factors=pos_factors,
            negative_factors=neg_factors,
            missing_fields=missing,
            warnings=warnings,
            status="VALID",
        )

    # -------------------------------------------------------------
    # FILE IMPORT PROVIDER
    # -------------------------------------------------------------
    @staticmethod
    def load_fundamentals_from_file(file_path: Union[str, Path]) -> List[FundamentalRecord]:
        """
        Loads fundamental statement filings from CSV or JSON.
        Ensures strict schema validation.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Fundamental file not found: {path}")

        records = []
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
            for _, r in df.iterrows():
                records.append(
                    FundamentalRecord(
                        symbol=str(r["symbol"]).upper(),
                        publication_date=pd.to_datetime(r["publication_date"]),
                        period_end_date=pd.to_datetime(r["period_end_date"]),
                        pe_ratio=float(r["pe_ratio"]) if "pe_ratio" in r and pd.notna(r["pe_ratio"]) else None,
                        pb_ratio=float(r["pb_ratio"]) if "pb_ratio" in r and pd.notna(r["pb_ratio"]) else None,
                        eps_growth_yoy=float(r["eps_growth_yoy"]) if "eps_growth_yoy" in r and pd.notna(r["eps_growth_yoy"]) else None,
                        revenue_growth_yoy=float(r["revenue_growth_yoy"]) if "revenue_growth_yoy" in r and pd.notna(r["revenue_growth_yoy"]) else None,
                        operating_margin=float(r["operating_margin"]) if "operating_margin" in r and pd.notna(r["operating_margin"]) else None,
                        net_margin=float(r["net_margin"]) if "net_margin" in r and pd.notna(r["net_margin"]) else None,
                        roe=float(r["roe"]) if "roe" in r and pd.notna(r["roe"]) else None,
                        roce=float(r["roce"]) if "roce" in r and pd.notna(r["roce"]) else None,
                        debt_to_equity=float(r["debt_to_equity"]) if "debt_to_equity" in r and pd.notna(r["debt_to_equity"]) else None,
                        current_ratio=float(r["current_ratio"]) if "current_ratio" in r and pd.notna(r["current_ratio"]) else None,
                        free_cash_flow_cr=float(r["free_cash_flow_cr"]) if "free_cash_flow_cr" in r and pd.notna(r["free_cash_flow_cr"]) else None,
                    )
                )
        elif path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_list = data if isinstance(data, list) else data.get("records", [])
            for r in raw_list:
                records.append(
                    FundamentalRecord(
                        symbol=str(r["symbol"]).upper(),
                        publication_date=pd.to_datetime(r["publication_date"]),
                        period_end_date=pd.to_datetime(r["period_end_date"]),
                        pe_ratio=r.get("pe_ratio"),
                        pb_ratio=r.get("pb_ratio"),
                        eps_growth_yoy=r.get("eps_growth_yoy"),
                        revenue_growth_yoy=r.get("revenue_growth_yoy"),
                        operating_margin=r.get("operating_margin"),
                        net_margin=r.get("net_margin"),
                        roe=r.get("roe"),
                        roce=r.get("roce"),
                        debt_to_equity=r.get("debt_to_equity"),
                        current_ratio=r.get("current_ratio"),
                        free_cash_flow_cr=r.get("free_cash_flow_cr"),
                    )
                )
        else:
            raise ValueError(f"Unsupported format {path.suffix}. Use CSV or JSON.")

        logger.info("Loaded %d fundamental records from %s", len(records), path)
        return records


# -----------------------------------------------------------------
# COMBINED FINANCIAL INTELLIGENCE HELPER
# -----------------------------------------------------------------
def get_combined_financial_intelligence(
    symbol: str,
    as_of_date: Union[str, pd.Timestamp],
    news_items: Optional[List[Any]] = None,
    fundamental_records: Optional[List[FundamentalRecord]] = None,
    sentiment_analyzer: Optional[Any] = None,
    fundamental_analyzer: Optional[FundamentalAnalyzer] = None,
) -> Dict[str, Any]:
    """
    Synthesizes financial news sentiment and fundamental health into a unified structure.
    Does NOT force a combined composite score if one data source is missing.
    """
    from src.intelligence.sentiment_analysis import SentimentAnalyzer

    sent_engine = sentiment_analyzer or SentimentAnalyzer()
    fund_engine = fundamental_analyzer or FundamentalAnalyzer()

    # 1. Evaluate Sentiment
    sent_res = sent_engine.evaluate_symbol_sentiment(
        news_items=news_items or [],
        symbol=symbol,
        as_of_date=as_of_date,
    )

    # 2. Evaluate Fundamentals
    fund_res = fund_engine.evaluate_fundamentals(
        records=fundamental_records or [],
        symbol=symbol,
        as_of_date=as_of_date,
    )

    # 3. Compile Combined Factors
    positives = list(fund_res.positive_factors)
    negatives = list(fund_res.negative_factors)

    if sent_res.status == "VALID" and sent_res.sentiment_score >= 60.0:
        positives.append(f"Bullish News Sentiment ({sent_res.sentiment_score:.1f}/100, {sent_res.news_count} articles)")
    elif sent_res.status == "VALID" and sent_res.sentiment_score <= 40.0:
        negatives.append(f"Bearish News Sentiment ({sent_res.sentiment_score:.1f}/100, {sent_res.news_count} articles)")

    # Data freshness summary
    freshness = {
        "sentiment_articles_found": sent_res.news_count,
        "sentiment_status": sent_res.status,
        "fundamental_filing_date": fund_res.publication_date.strftime("%Y-%m-%d") if fund_res.publication_date else None,
        "fundamental_staleness_days": fund_res.staleness_days,
        "fundamental_status": fund_res.status,
    }

    # Composite score only if both domains have valid data
    composite_score = None
    if sent_res.status == "VALID" and fund_res.status == "VALID" and fund_res.fundamental_score is not None:
        composite_score = round(0.40 * sent_res.sentiment_score + 0.60 * fund_res.fundamental_score, 2)

    return {
        "symbol": symbol,
        "evaluation_date": str(as_of_date),
        "sentiment_score": sent_res.sentiment_score if sent_res.status == "VALID" else None,
        "sentiment_label": sent_res.sentiment_label,
        "sentiment_confidence": sent_res.confidence,
        "fundamental_score": fund_res.fundamental_score,
        "fundamental_classification": fund_res.classification,
        "fundamental_data_coverage": fund_res.data_coverage,
        "composite_financial_score": composite_score,
        "key_positive_factors": positives,
        "key_negative_factors": negatives,
        "missing_information": fund_res.missing_fields + ([sent_res.warning] if sent_res.warning else []),
        "data_freshness": freshness,
    }
