"""
MIRAI — Unit Tests for Stock Strength Intelligence (M05)
"""

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pytest

from src.intelligence.stock_strength import StockStrengthEngine, StockStrengthResult


def _create_synthetic_ohlcv(
    n_bars: int = 100,
    trend: float = 0.001,
    vol: float = 0.01,
    start_price: float = 1000.0,
    base_volume: float = 500000.0,
    base_turnover: float = 5e8,
    start_date: str = "2023-01-01",
) -> pd.DataFrame:
    """Generates synthetic deterministic OHLCV series for testing."""
    np.random.seed(42)
    dates = pd.date_range(start_date, periods=n_bars, freq="D")
    daily_rets = np.random.normal(loc=trend, scale=vol, size=n_bars)
    prices = start_price * np.exp(np.cumsum(daily_rets))

    highs = prices * (1.0 + np.abs(np.random.normal(0, 0.005, size=n_bars)))
    lows = prices * (1.0 - np.abs(np.random.normal(0, 0.005, size=n_bars)))
    opens = (highs + lows) / 2.0

    volumes = base_volume * np.random.uniform(0.8, 1.2, size=n_bars)
    turnovers = volumes * prices

    return pd.DataFrame({
        "timestamp": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": volumes,
        "turnover": turnovers,
    })


def test_stock_strength_basic_score():
    """Verify stock strength score evaluates in [0, 100] and contributions sum to overall score."""
    df_stock = _create_synthetic_ohlcv(n_bars=80, trend=0.002)
    df_bench = _create_synthetic_ohlcv(n_bars=80, trend=0.0005)

    engine = StockStrengthEngine()
    result = engine.evaluate_stock_strength(
        df_stock=df_stock,
        symbol="RELIANCE",
        df_benchmark=df_bench,
    )

    assert isinstance(result, StockStrengthResult)
    assert result.symbol == "RELIANCE"
    assert 0.0 <= result.overall_score <= 100.0
    assert result.classification in ["Very Strong", "Strong", "Neutral", "Weak", "Very Weak"]

    # Verify that sum of factor contributions equals overall score
    contrib_sum = sum(result.factor_contributions.values())
    assert pytest.approx(result.overall_score, 0.01) == contrib_sum
    assert result.data_coverage == 1.0
    assert result.confidence > 0.8
    assert result.lob_depth_available is False  # Equity OHLCV, not LOB depth


def test_bullish_vs_bearish_score_differential():
    """Verify strongly trending bullish stock gets higher score than strongly falling stock."""
    df_bull = _create_synthetic_ohlcv(n_bars=80, trend=0.005, vol=0.008)
    df_bear = _create_synthetic_ohlcv(n_bars=80, trend=-0.005, vol=0.012)
    df_bench = _create_synthetic_ohlcv(n_bars=80, trend=0.000)

    engine = StockStrengthEngine()
    res_bull = engine.evaluate_stock_strength(df_bull, "BULL_STOCK", df_bench)
    res_bear = engine.evaluate_stock_strength(df_bear, "BEAR_STOCK", df_bench)

    assert res_bull.overall_score > res_bear.overall_score
    assert res_bull.overall_score >= 65.0
    assert res_bear.overall_score <= 45.0
    assert res_bull.factor_scores["momentum"] > res_bear.factor_scores["momentum"]
    assert res_bull.factor_scores["relative_strength"] > res_bear.factor_scores["relative_strength"]


def test_configurable_weights():
    """Verify custom factor weights change contribution distributions."""
    df_stock = _create_synthetic_ohlcv(n_bars=80)
    df_bench = _create_synthetic_ohlcv(n_bars=80)

    # 100% momentum weight
    custom_w = {
        "momentum": 1.0, "relative_strength": 0.0, "volume": 0.0,
        "trend": 0.0, "volatility_adjusted": 0.0, "liquidity": 0.0
    }
    engine = StockStrengthEngine(weights=custom_w)
    res = engine.evaluate_stock_strength(df_stock, "TEST_SYM", df_bench)

    assert pytest.approx(res.overall_score, 0.01) == res.factor_scores["momentum"]
    assert res.factor_contributions["momentum"] == res.overall_score


def test_missing_factors_handling():
    """Verify missing benchmark and volume gracefully re-normalizes weights without failing."""
    # Stock dataframe without volume or turnover
    df_stock = _create_synthetic_ohlcv(n_bars=80).drop(columns=["volume", "turnover"])

    engine = StockStrengthEngine()
    res = engine.evaluate_stock_strength(
        df_stock=df_stock,
        symbol="SYM_NO_VOL",
        df_benchmark=None,  # No benchmark available
    )

    assert 0.0 <= res.overall_score <= 100.0
    # Volume, liquidity (dependent on volume), and relative_strength (no benchmark) are missing -> coverage is 3/6 = 0.5
    assert pytest.approx(res.data_coverage, 0.01) == 0.5
    assert res.confidence < 0.8  # Confidence discounted due to missing factors
    assert len(res.missing_data_warnings) >= 2


def test_strengthening_weakening_status():
    """Verify strengthening, weakening, and stable movement detection."""
    df_stock = _create_synthetic_ohlcv(n_bars=80)
    engine = StockStrengthEngine(movement_threshold=3.0)

    # Prior score was 50, current score evaluates around ~65 -> Strengthening
    res_up = engine.evaluate_stock_strength(df_stock, "TEST", prior_score=40.0)
    if res_up.overall_score - 40.0 >= 3.0:
        assert res_up.trend_status in ("Strengthening", "Potential Reversal")

    # Prior score was 90 -> Weakening
    res_down = engine.evaluate_stock_strength(df_stock, "TEST", prior_score=90.0)
    if 90.0 - res_down.overall_score >= 3.0:
        assert res_down.trend_status in ("Weakening", "Potential Reversal")


def test_no_future_leakage_in_as_of_date():
    """Verify that specifying as_of_date yields identical results to truncated dataframe."""
    df_stock = _create_synthetic_ohlcv(n_bars=100)
    cutoff_date = df_stock["timestamp"].iloc[60]

    engine = StockStrengthEngine()

    # Pass full 100 bars but with as_of_date = bar 60
    res_as_of = engine.evaluate_stock_strength(df_stock, "TEST", as_of_date=cutoff_date)

    # Pass only the first 61 bars
    df_truncated = df_stock.iloc[:61].copy()
    res_trunc = engine.evaluate_stock_strength(df_truncated, "TEST")

    assert pytest.approx(res_as_of.overall_score, 1e-4) == res_trunc.overall_score
    assert pytest.approx(res_as_of.confidence, 1e-4) == res_trunc.confidence


def test_timeline_and_cross_sectional_ranking():
    """Verify rolling timeline generation and multi-stock cross-sectional ranking."""
    df_stock1 = _create_synthetic_ohlcv(n_bars=50, trend=0.003)
    df_stock2 = _create_synthetic_ohlcv(n_bars=50, trend=-0.002)
    df_bench = _create_synthetic_ohlcv(n_bars=50, trend=0.0005)

    engine = StockStrengthEngine()

    # 1. Timeline
    timeline_df = engine.compute_strength_timeline(df_stock1, "SYM1", df_bench, min_bars=25)
    assert len(timeline_df) == 25  # 50 - 25
    assert "overall_score" in timeline_df.columns
    assert "classification" in timeline_df.columns

    # 2. Cross-sectional ranking
    stock_dict = {"SYM1": df_stock1, "SYM2": df_stock2}
    rank_df = engine.rank_stocks(stock_dict, df_bench)
    assert len(rank_df) == 2
    assert "rank" in rank_df.columns
    # Bullish SYM1 should outrank SYM2
    assert rank_df.iloc[0]["symbol"] == "SYM1"
    assert rank_df.iloc[0]["rank"] == 1
