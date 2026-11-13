"""
MIRAI — Financial News Sentiment Intelligence (M06)
Analyzes financial headlines and news items with symbol-specific mapping,
recency decay weighting, deduplication, and pluggable NLP engines (FinBERT or calibrated Financial Lexicon).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger("SentimentAnalysis")

# Gracefully inspect FinBERT / transformers availability
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    FINBERT_AVAILABLE = True
except ImportError:
    FINBERT_AVAILABLE = False


@dataclass
class NewsItem:
    """Standardized news article data container."""
    headline: str
    symbol: str
    timestamp: pd.Timestamp
    content: Optional[str] = None
    source: str = "imported"
    article_id: Optional[str] = None
    url: Optional[str] = None

    def __post_init__(self):
        if not self.article_id:
            raw_id = f"{self.symbol}_{self.headline}_{str(self.timestamp)}"
            self.article_id = hashlib.md5(raw_id.encode("utf-8")).hexdigest()[:12]

    def fingerprint(self) -> str:
        """Normalized string for deduplication."""
        norm_hl = re.sub(r"[^\w\s]", "", self.headline.lower()).strip()
        norm_hl = " ".join(norm_hl.split())
        return f"{self.symbol.upper()}_{norm_hl}"


@dataclass
class SentimentResult:
    """Standardized output structure for symbol sentiment evaluation."""
    symbol: str
    evaluation_timestamp: pd.Timestamp
    sentiment_score: float  # [0.0, 100.0], where 50 is neutral, >50 bullish, <50 bearish
    sentiment_label: str  # 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
    confidence: float  # [0.0, 1.0]
    p_positive: float
    p_negative: float
    p_neutral: float
    news_count: int
    articles_analyzed: List[Dict[str, Any]] = field(default_factory=list)
    engine_used: str = "financial_lexicon"
    status: str = "VALID"  # 'VALID' or 'INSUFFICIENT_DATA'
    warning: Optional[str] = None

    @property
    def as_of_date(self) -> pd.Timestamp:
        return self.evaluation_timestamp

    @property
    def recent_headlines(self) -> List[str]:
        if not self.articles_analyzed:
            return []
        headlines = []
        for a in self.articles_analyzed:
            if isinstance(a, dict):
                headlines.append(a.get("headline", str(a)))
            elif hasattr(a, "headline"):
                headlines.append(a.headline)
        return headlines

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "evaluation_timestamp": self.evaluation_timestamp.isoformat() if hasattr(self.evaluation_timestamp, "isoformat") else str(self.evaluation_timestamp),
            "sentiment_score": round(self.sentiment_score, 2),
            "sentiment_label": self.sentiment_label,
            "confidence": round(self.confidence, 3),
            "p_positive": round(self.p_positive, 3),
            "p_negative": round(self.p_negative, 3),
            "p_neutral": round(self.p_neutral, 3),
            "news_count": self.news_count,
            "engine_used": self.engine_used,
            "status": self.status,
            "warning": self.warning,
            "articles_analyzed": self.articles_analyzed,
        }


# -----------------------------------------------------------------
# CALIBRATED FINANCIAL LEXICON (ZERO-DEPENDENCY BASELINE ENGINE)
# -----------------------------------------------------------------
class FinancialLexiconAnalyzer:
    """
    High-precision domain-specific financial sentiment analyzer.
    Calibrated with Loughran-McDonald & financial press terminology.
    """

    POSITIVE_TERMS = {
        "surge": 2.0, "rally": 2.0, "outperform": 2.0, "record profit": 2.5, "dividend hike": 2.0,
        "upgrade": 1.8, "bullish": 1.8, "expansion": 1.5, "growth": 1.2, "beat": 1.5,
        "strong earnings": 2.0, "revenue jump": 2.0, "contract win": 1.8, "acquisition": 1.2,
        "partnership": 1.2, "breakthrough": 2.0, "rebound": 1.5, "buyback": 1.8,
        "approval": 1.5, "gain": 1.0, "optimistic": 1.2, "resilient": 1.2, "soar": 2.0,
        "stellar": 2.0, "all-time high": 2.2, "margin expansion": 2.0, "order win": 1.8,
        "wins": 1.5, "win": 1.5, "contract": 1.2, "deal": 1.2, "order": 1.0,
    }

    NEGATIVE_TERMS = {
        "slump": 2.0, "plunge": 2.2, "crash": 2.5, "downgrade": 2.0, "profit drop": 2.2,
        "revenue miss": 2.0, "miss": 1.5, "default": 3.0, "fraud": 3.0, "probe": 2.0,
        "investigation": 2.0, "lawsuit": 1.8, "penalty": 2.0, "bearish": 1.8,
        "loss": 1.5, "decline": 1.2, "debt crisis": 2.5, "layoffs": 1.8, "cut": 1.2,
        "subdued": 1.2, "inflation pressure": 1.5, "margin contraction": 2.0, "selloff": 2.0,
        "warning": 1.5, "bankruptcy": 3.0, "scam": 3.0, "regulatory hurdle": 1.8,
    }

    def analyze_text(self, text: str) -> Tuple[float, float, float, float]:
        """
        Analyzes financial text.
        Returns (p_positive, p_negative, p_neutral, compound_polarity in [-1.0, 1.0]).
        """
        lower = text.lower()
        pos_score = 0.0
        neg_score = 0.0

        for term, weight in self.POSITIVE_TERMS.items():
            if term in lower:
                pos_score += weight

        for term, weight in self.NEGATIVE_TERMS.items():
            if term in lower:
                neg_score += weight

        total = pos_score + neg_score
        if total == 0:
            return 0.10, 0.10, 0.80, 0.0

        # Compute softmax probabilities
        p_pos = (pos_score / (total + 1.0)) * 0.8
        p_neg = (neg_score / (total + 1.0)) * 0.8
        p_neu = max(0.05, 1.0 - (p_pos + p_neg))

        # Normalize
        s = p_pos + p_neg + p_neu
        p_pos /= s
        p_neg /= s
        p_neu /= s

        # Compound polarity: [-1.0, 1.0]
        compound = (pos_score - neg_score) / (total + 0.5)
        return float(p_pos), float(p_neg), float(p_neu), float(compound)


# -----------------------------------------------------------------
# MASTER SENTIMENT ANALYZER & INTEGRATION SERVICE
# -----------------------------------------------------------------
class SentimentAnalyzer:
    """
    Financial News Sentiment Engine supporting recency weighting,
    duplicate elimination, and symbol-specific aggregation.
    """

    def __init__(
        self,
        engine_type: str = "lexicon",
        recency_decay_hours: float = 48.0,
        neutral_score: float = 50.0,
    ):
        cfg = get_config()
        self.engine_type = cfg.get("sentiment.engine", engine_type)
        self.recency_decay_hours = cfg.get("sentiment.recency_decay_hours", recency_decay_hours)
        self.neutral_score = cfg.get("sentiment.neutral_score", neutral_score)

        self.lexicon_engine = FinancialLexiconAnalyzer()
        self.finbert_model = None
        self.finbert_tokenizer = None

        if self.engine_type == "finbert":
            if FINBERT_AVAILABLE:
                try:
                    logger.info("Initializing FinBERT tokenizer and model...")
                    self.finbert_tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
                    self.finbert_model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
                    self.finbert_model.eval()
                    logger.info("FinBERT successfully loaded.")
                except Exception as exc:
                    logger.warning("Could not load FinBERT from HuggingFace (%s). Falling back to Financial Lexicon.", exc)
                    self.engine_type = "lexicon"
            else:
                logger.info("Transformers/Torch not installed. Using calibrated Financial Lexicon engine.")
                self.engine_type = "lexicon"

    def deduplicate_news(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """Eliminates duplicate news items based on symbol and headline fingerprint."""
        seen = set()
        unique = []
        for item in news_items:
            fp = item.fingerprint()
            if fp not in seen:
                seen.add(fp)
                unique.append(item)
            else:
                logger.debug("Deduplicated news item: %s", item.headline[:40])
        return unique

    def score_single_news(self, text: str) -> Tuple[float, float, float, float]:
        """Scores a single headline/article text."""
        if self.engine_type == "finbert" and self.finbert_model is not None:
            try:
                inputs = self.finbert_tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
                with torch.no_grad():
                    logits = self.finbert_model(**inputs).logits
                    probs = torch.softmax(logits, dim=1).numpy()[0]
                    # FinBERT classes: 0: positive, 1: negative, 2: neutral
                    p_pos, p_neg, p_neu = float(probs[0]), float(probs[1]), float(probs[2])
                    compound = p_pos - p_neg
                    return p_pos, p_neg, p_neu, compound
            except Exception as exc:
                logger.debug("FinBERT inference error: %s. Using lexicon fallback.", exc)

        return self.lexicon_engine.analyze_text(text)

    def evaluate_symbol_sentiment(
        self,
        news_items: List[NewsItem],
        symbol: str,
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        max_lookback_days: int = 7,
    ) -> SentimentResult:
        """
        Evaluates aggregated sentiment score for a given stock symbol as of a specific date.
        Filters strictly by `timestamp <= as_of_date` (no future leakage).
        Applies exponential recency decay weighting.
        """
        as_of_ts = pd.to_datetime(as_of_date) if as_of_date else pd.Timestamp.now()
        min_ts = as_of_ts - pd.Timedelta(days=max_lookback_days)

        # 1. Filter by symbol and time window
        sym_upper = symbol.upper()
        matching_items = [
            item for item in news_items
            if item.symbol.upper() == sym_upper
            and item.timestamp <= as_of_ts
            and item.timestamp >= min_ts
        ]

        # 2. Deduplicate
        unique_items = self.deduplicate_news(matching_items)

        # 3. Handle zero news case gracefully
        if not unique_items:
            return SentimentResult(
                symbol=symbol,
                evaluation_timestamp=as_of_ts,
                sentiment_score=self.neutral_score,
                sentiment_label="NEUTRAL",
                confidence=0.0,
                p_positive=0.0,
                p_negative=0.0,
                p_neutral=1.0,
                news_count=0,
                engine_used=self.engine_type,
                status="INSUFFICIENT_DATA",
                warning=f"No news items found for {symbol} within trailing {max_lookback_days} days.",
            )

        # 4. Score each news item and compute recency weights
        scored_articles = []
        weighted_scores = []
        weights = []
        sum_p_pos, sum_p_neg, sum_p_neu = 0.0, 0.0, 0.0

        for item in unique_items:
            combined_text = f"{item.headline} {item.content or ''}".strip()
            p_pos, p_neg, p_neu, compound = self.score_single_news(combined_text)

            # Map compound polarity [-1.0, 1.0] to score [0.0, 100.0]
            item_score = float((compound + 1.0) * 50.0)

            # Exponential recency decay: weight = exp(-age_hours / half_life)
            age_hours = max(0.0, (as_of_ts - item.timestamp).total_seconds() / 3600.0)
            weight = float(np.exp(-age_hours / max(self.recency_decay_hours, 1.0)))

            weights.append(weight)
            weighted_scores.append(item_score * weight)
            sum_p_pos += p_pos * weight
            sum_p_neg += p_neg * weight
            sum_p_neu += p_neu * weight

            scored_articles.append({
                "article_id": item.article_id,
                "headline": item.headline,
                "timestamp": item.timestamp.isoformat() if hasattr(item.timestamp, "isoformat") else str(item.timestamp),
                "source": item.source,
                "score": round(item_score, 2),
                "polarity": round(compound, 3),
                "weight": round(weight, 3),
                "p_positive": round(p_pos, 3),
                "p_negative": round(p_neg, 3),
                "p_neutral": round(p_neu, 3),
            })

        # 5. Compute recency-weighted aggregated sentiment
        total_w = sum(weights)
        agg_score = float(sum(weighted_scores) / total_w)
        agg_p_pos = float(sum_p_pos / total_w)
        agg_p_neg = float(sum_p_neg / total_w)
        agg_p_neu = float(sum_p_neu / total_w)

        # Classification label
        if agg_score >= 58.0:
            label = "POSITIVE"
        elif agg_score <= 42.0:
            label = "NEGATIVE"
        else:
            label = "NEUTRAL"

        # Confidence scaled by article count and recency
        confidence = float(min(1.0, (len(unique_items) / 5.0) * min(total_w, 1.0)))

        return SentimentResult(
            symbol=symbol,
            evaluation_timestamp=as_of_ts,
            sentiment_score=agg_score,
            sentiment_label=label,
            confidence=confidence,
            p_positive=agg_p_pos,
            p_negative=agg_p_neg,
            p_neutral=agg_p_neu,
            news_count=len(unique_items),
            articles_analyzed=scored_articles,
            engine_used=self.engine_type,
            status="VALID",
        )

    # -------------------------------------------------------------
    # FILE IMPORT PROVIDER
    # -------------------------------------------------------------
    @staticmethod
    def load_news_from_file(file_path: Union[str, Path]) -> List[NewsItem]:
        """
        Loads news items from CSV or JSON file.
        Expected schema: ['headline', 'symbol', 'timestamp', 'content' (optional), 'source' (optional)].
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"News data file not found: {path}")

        items = []
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                items.append(
                    NewsItem(
                        headline=str(row["headline"]),
                        symbol=str(row["symbol"]).upper(),
                        timestamp=pd.to_datetime(row["timestamp"]),
                        content=str(row["content"]) if "content" in row and pd.notna(row["content"]) else None,
                        source=str(row["source"]) if "source" in row and pd.notna(row["source"]) else "imported",
                        article_id=str(row["article_id"]) if "article_id" in row and pd.notna(row["article_id"]) else None,
                        url=str(row["url"]) if "url" in row and pd.notna(row["url"]) else None,
                    )
                )
        elif path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            records = data if isinstance(data, list) else data.get("articles", [])
            for r in records:
                items.append(
                    NewsItem(
                        headline=str(r["headline"]),
                        symbol=str(r["symbol"]).upper(),
                        timestamp=pd.to_datetime(r["timestamp"]),
                        content=r.get("content"),
                        source=r.get("source", "imported"),
                        article_id=r.get("article_id"),
                        url=r.get("url"),
                    )
                )
        else:
            raise ValueError(f"Unsupported news file format: {path.suffix}. Use CSV or JSON.")

        logger.info("Loaded %d news items from %s", len(items), path)
        return items

    def analyze_symbol_sentiment(
        self,
        symbol: str,
        news_items: Optional[List[NewsItem]] = None,
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        lookback_days: Optional[int] = None,
    ) -> SentimentResult:
        """Convenience method evaluating sentiment for a symbol."""
        items = news_items if news_items is not None else []
        lb = lookback_days if lookback_days is not None else 7
        return self.evaluate_symbol_sentiment(
            news_items=items,
            symbol=symbol,
            as_of_date=as_of_date,
            max_lookback_days=lb,
        )


# Class alias for backwards compatibility
NewsSentimentAnalyzer = SentimentAnalyzer

