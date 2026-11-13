"""
MIRAI — Unit Tests for Fundamental Analysis Intelligence (M06)
"""

from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from src.intelligence.fundamental_analysis import (
    FundamentalAnalyzer,
    FundamentalRecord,
    FundamentalAssessment,
    get_combined_financial_intelligence,
)
from src.intelligence.sentiment_analysis import NewsItem


def test_fundamental_record_schema_validation():
    """Verify validation raises error if publication date is earlier than period end date."""
    # Valid record: Q4 ended 2023-03-31, published 2023-05-10
    rec = FundamentalRecord(
        symbol="INFY",
        publication_date="2023-05-10",
        period_end_date="2023-03-31",
        pe_ratio=24.5,
        roe=0.28,
    )
    assert rec.symbol == "INFY"
    assert rec.publication_date == pd.Timestamp("2023-05-10")

    # Invalid record: published BEFORE the quarter even ended (impossible point-in-time)
    with pytest.raises(ValueError, match="cannot be earlier"):
        FundamentalRecord(
            symbol="INFY",
            publication_date="2023-03-15",
            period_end_date="2023-03-31",
        )


def test_point_in_time_filtering():
    """Verify results published in the future are never accessed on an earlier date."""
    records = [
        # Q3 results published Jan 15, 2023
        FundamentalRecord(
            symbol="TCS",
            publication_date="2023-01-15",
            period_end_date="2022-12-31",
            pe_ratio=30.0,
            roe=0.35,
            revenue_growth_yoy=0.10,
        ),
        # Q4 results published April 25, 2023
        FundamentalRecord(
            symbol="TCS",
            publication_date="2023-04-25",
            period_end_date="2023-03-31",
            pe_ratio=28.0,
            roe=0.40,
            revenue_growth_yoy=0.15,
        ),
    ]

    analyzer = FundamentalAnalyzer()

    # Evaluation on March 1, 2023: must ONLY see the Jan 15 filing, NOT the April 25 filing!
    eval_march = analyzer.evaluate_fundamentals(records, "TCS", as_of_date="2023-03-01")
    assert eval_march.status == "VALID"
    assert eval_march.publication_date == pd.Timestamp("2023-01-15")
    assert eval_march.key_ratios["pe_ratio"] == 30.0

    # Evaluation on May 1, 2023: now sees the newer April 25 filing
    eval_may = analyzer.evaluate_fundamentals(records, "TCS", as_of_date="2023-05-01")
    assert eval_may.publication_date == pd.Timestamp("2023-04-25")
    assert eval_may.key_ratios["pe_ratio"] == 28.0


def test_missing_fundamentals_insufficient_data():
    """Verify querying an unfiled symbol returns INSUFFICIENT_DATA and None score."""
    analyzer = FundamentalAnalyzer()
    res = analyzer.evaluate_fundamentals(
        records=[],
        symbol="UNKNOWN_SYM",
        as_of_date="2023-05-01",
    )

    assert isinstance(res, FundamentalAssessment)
    assert res.status == "INSUFFICIENT_DATA"
    assert res.fundamental_score is None
    assert res.classification == "INSUFFICIENT_DATA"
    assert res.data_coverage == 0.0
    assert len(res.warnings) > 0


def test_stale_data_warning():
    """Verify filing older than max_stale_days triggers explicit stale data warning."""
    # Filing published 220 days prior to evaluation date
    old_filing = FundamentalRecord(
        symbol="RELIANCE",
        publication_date="2022-06-01",
        period_end_date="2022-03-31",
        pe_ratio=22.0,
        roe=0.14,
        debt_to_equity=0.40,
    )

    analyzer = FundamentalAnalyzer(max_stale_days=180)
    res = analyzer.evaluate_fundamentals([old_filing], "RELIANCE", as_of_date="2023-01-15")

    assert res.status == "VALID"
    assert res.staleness_days > 180
    assert any("STALE DATA WARNING" in w for w in res.warnings)


def test_fundamental_scoring_and_classification():
    """Verify healthy fundamentals receive high scores and healthy classification."""
    healthy_record = FundamentalRecord(
        symbol="TITAN",
        publication_date="2023-04-20",
        period_end_date="2023-03-31",
        pe_ratio=18.0,
        pb_ratio=3.5,
        eps_growth_yoy=0.25,
        revenue_growth_yoy=0.22,
        operating_margin=0.20,
        roe=0.24,
        debt_to_equity=0.30,
        current_ratio=1.8,
    )

    analyzer = FundamentalAnalyzer()
    res = analyzer.evaluate_fundamentals([healthy_record], "TITAN", as_of_date="2023-05-01")

    assert res.status == "VALID"
    assert res.fundamental_score >= 65.0
    assert res.classification in ("HEALTHY", "FAIR")
    assert len(res.positive_factors) >= 2


def test_combined_financial_intelligence():
    """Verify combined financial intelligence synthesizes sentiment and fundamentals without forcing scores."""
    news = [
        NewsItem(headline="TCS signs multi-billion dollar mega deal", symbol="TCS", timestamp=pd.Timestamp("2023-04-20")),
    ]
    fund = [
        FundamentalRecord(
            symbol="TCS",
            publication_date="2023-04-15",
            period_end_date="2023-03-31",
            pe_ratio=26.0,
            roe=0.38,
            revenue_growth_yoy=0.12,
        )
    ]

    # Both present -> valid composite score
    res = get_combined_financial_intelligence("TCS", as_of_date="2023-04-25", news_items=news, fundamental_records=fund)
    assert res["sentiment_score"] is not None
    assert res["fundamental_score"] is not None
    assert res["composite_financial_score"] is not None
    assert len(res["key_positive_factors"]) > 0

    # Fundamentals missing -> composite score is None (does not force combination)
    res_no_fund = get_combined_financial_intelligence("TCS", as_of_date="2023-04-25", news_items=news, fundamental_records=[])
    assert res_no_fund["fundamental_score"] is None
    assert res_no_fund["composite_financial_score"] is None
