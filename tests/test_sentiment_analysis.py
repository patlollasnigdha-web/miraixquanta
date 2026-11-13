"""
MIRAI — Unit Tests for Financial Sentiment Intelligence (M06)
"""

import json
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from src.intelligence.sentiment_analysis import (
    SentimentAnalyzer,
    NewsItem,
    SentimentResult,
    FinancialLexiconAnalyzer,
)


def test_lexicon_polarity_and_probabilities():
    """Verify financial lexicon yields valid probabilities and appropriate polarities."""
    lex = FinancialLexiconAnalyzer()

    # Bullish text
    bull_text = "Company reports record profit and strong earnings, announces dividend hike."
    p_pos, p_neg, p_neu, compound = lex.analyze_text(bull_text)
    assert 0.0 <= p_pos <= 1.0
    assert 0.0 <= p_neg <= 1.0
    assert 0.0 <= p_neu <= 1.0
    assert pytest.approx(p_pos + p_neg + p_neu, 0.01) == 1.0
    assert compound > 0.3
    assert p_pos > p_neg

    # Bearish text
    bear_text = "Stock slumps following massive revenue miss and regulatory penalty probe."
    p_pos_b, p_neg_b, p_neu_b, compound_b = lex.analyze_text(bear_text)
    assert compound_b < -0.3
    assert p_neg_b > p_pos_b

    # Neutral text
    neu_text = "Company announces routine annual general meeting schedule for next quarter."
    _, _, p_neu_n, comp_n = lex.analyze_text(neu_text)
    assert p_neu_n >= 0.70
    assert abs(comp_n) < 0.15


def test_sentiment_deduplication():
    """Verify identical or near-identical headlines for the same symbol are deduplicated."""
    now = pd.Timestamp("2023-05-15 10:00:00")
    items = [
        NewsItem(headline="TCS reports strong Q4 profit beat", symbol="TCS", timestamp=now, source="reuters"),
        NewsItem(headline="TCS reports strong Q4 profit beat!", symbol="TCS", timestamp=now, source="bloomberg"),  # duplicate
        NewsItem(headline="TCS wins major cloud transformation contract", symbol="TCS", timestamp=now, source="moneycontrol"),
        NewsItem(headline="INFY announces dividend", symbol="INFY", timestamp=now),
    ]

    analyzer = SentimentAnalyzer(engine_type="lexicon")
    deduped = analyzer.deduplicate_news(items)

    assert len(deduped) == 3  # 1 duplicate TCS headline removed
    tcs_items = [i for i in deduped if i.symbol == "TCS"]
    assert len(tcs_items) == 2


def test_missing_news_insufficient_data():
    """Verify querying a symbol with zero news items returns INSUFFICIENT_DATA and neutral score."""
    analyzer = SentimentAnalyzer(engine_type="lexicon")
    res = analyzer.evaluate_symbol_sentiment(
        news_items=[],
        symbol="HDFCBANK",
        as_of_date="2023-05-15",
    )

    assert isinstance(res, SentimentResult)
    assert res.status == "INSUFFICIENT_DATA"
    assert res.sentiment_score == 50.0
    assert res.sentiment_label == "NEUTRAL"
    assert res.confidence == 0.0
    assert res.news_count == 0
    assert "No news items found" in res.warning


def test_recency_decay_weighting():
    """Verify newer news carries higher weight than older news."""
    as_of = pd.Timestamp("2023-05-15 12:00:00")
    t_new = as_of - pd.Timedelta(hours=2)
    t_old = as_of - pd.Timedelta(hours=72)

    # Old news is positive, new news is negative -> overall score should lean negative due to recency
    items = [
        NewsItem(headline="RELIANCE records strong profit beat", symbol="RELIANCE", timestamp=t_old),
        NewsItem(headline="RELIANCE slumps amid sudden penalty probe", symbol="RELIANCE", timestamp=t_new),
    ]

    analyzer = SentimentAnalyzer(engine_type="lexicon", recency_decay_hours=24.0)
    res = analyzer.evaluate_symbol_sentiment(items, "RELIANCE", as_of_date=as_of)

    assert res.status == "VALID"
    assert res.news_count == 2
    # New negative news has weight exp(-2/24) ~ 0.92, old positive news has weight exp(-72/24) ~ 0.05
    assert res.sentiment_score < 48.0
    assert res.sentiment_label in ("NEGATIVE", "NEUTRAL")


def test_no_future_news_leakage():
    """Verify news published after as_of_date is strictly excluded."""
    as_of = pd.Timestamp("2023-05-15 12:00:00")
    t_past = as_of - pd.Timedelta(hours=4)
    t_future = as_of + pd.Timedelta(hours=10)

    items = [
        NewsItem(headline="TCS wins major order and reports strong profit beat", symbol="TCS", timestamp=t_past),
        NewsItem(headline="TCS profit collapses in massive fraud probe", symbol="TCS", timestamp=t_future),  # FUTURE NEWS
    ]

    analyzer = SentimentAnalyzer(engine_type="lexicon")
    res = analyzer.evaluate_symbol_sentiment(items, "TCS", as_of_date=as_of)

    # Future news must not be included
    assert res.news_count == 1
    assert res.sentiment_score > 55.0  # Only past bullish news evaluated
    for art in res.articles_analyzed:
        assert "fraud" not in art["headline"]


def test_load_news_from_csv_and_json():
    """Verify news loader reads valid CSV and JSON files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # CSV
        csv_path = Path(tmpdir) / "news.csv"
        df_news = pd.DataFrame([
            {"headline": "HDFC Bank quarterly profit surges 20%", "symbol": "HDFCBANK", "timestamp": "2023-04-15 09:30:00", "source": "mint"},
            {"headline": "Infosys raises revenue growth guidance", "symbol": "INFY", "timestamp": "2023-04-15 11:00:00", "source": "reuters"},
        ])
        df_news.to_csv(csv_path, index=False)

        loaded_csv = SentimentAnalyzer.load_news_from_file(csv_path)
        assert len(loaded_csv) == 2
        assert loaded_csv[0].symbol == "HDFCBANK"
        assert loaded_csv[1].symbol == "INFY"

        # JSON
        json_path = Path(tmpdir) / "news.json"
        json_data = [
            {"headline": "Tata Motors commercial vehicle sales expand", "symbol": "TATAMOTORS", "timestamp": "2023-04-16 10:00:00"},
        ]
        with open(json_path, "w") as f:
            json.dump(json_data, f)

        loaded_json = SentimentAnalyzer.load_news_from_file(json_path)
        assert len(loaded_json) == 1
        assert loaded_json[0].symbol == "TATAMOTORS"
