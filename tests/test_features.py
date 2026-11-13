"""
ASTRAQUANT X — Unit Tests for Feature Engineering Modules
"""

import numpy as np
import pandas as pd
import pytest

from src.features.orderbook_features import (
    compute_bid_ask_spread,
    compute_mid_price,
    compute_micro_price,
    compute_depth_imbalance,
    compute_order_flow_imbalance,
)
from src.features.technical_indicators import (
    compute_sma,
    compute_ema,
    compute_rsi,
    compute_bollinger_bands,
    compute_atr,
    add_all_technical_indicators,
)
from src.features.volatility_features import (
    compute_realized_volatility,
    compute_parkinson_volatility,
    compute_garman_klass_volatility,
)
from src.features.feature_pipeline import FeaturePipeline


def test_orderbook_spread_and_mid():
    """Verify nominal spread and arithmetic mid price."""
    ask = np.array([100.5, 101.0, 102.0])
    bid = np.array([100.0, 100.0, 101.5])

    spread = compute_bid_ask_spread(ask, bid)
    assert np.allclose(spread, [0.5, 1.0, 0.5])

    mid = compute_mid_price(ask, bid)
    assert np.allclose(mid, [100.25, 100.5, 101.75])


def test_micro_price():
    """Verify volume-weighted micro price behavior."""
    ask_p = np.array([101.0])
    bid_p = np.array([100.0])

    # If ask volume is 3x bid volume, price is closer to bid
    micro_heavy_ask = compute_micro_price(ask_p, np.array([30.0]), bid_p, np.array([10.0]))
    assert micro_heavy_ask[0] == 100.25

    # If bid volume is 3x ask volume, price is closer to ask
    micro_heavy_bid = compute_micro_price(ask_p, np.array([10.0]), bid_p, np.array([30.0]))
    assert micro_heavy_bid[0] == 100.75


def test_depth_imbalance():
    """Verify depth imbalance is strictly bounded in [-1, +1]."""
    bid_v = np.array([100.0, 50.0, 0.0])
    ask_v = np.array([0.0, 50.0, 100.0])

    imb = compute_depth_imbalance(bid_v, ask_v)
    assert np.allclose(imb, [1.0, 0.0, -1.0])


def test_order_flow_imbalance():
    """Verify Order Flow Imbalance logic."""
    bid_p = np.array([100.0, 101.0, 101.0])
    bid_v = np.array([10.0, 20.0, 25.0])
    ask_p = np.array([102.0, 102.0, 101.5])
    ask_v = np.array([15.0, 15.0, 10.0])

    ofi = compute_order_flow_imbalance(bid_p, bid_v, ask_p, ask_v)
    assert len(ofi) == 3
    assert ofi[0] == 0.0  # Initial index
    # Step 1: bid price increased -> delta_v_bid = 20; ask price flat -> delta_v_ask = 0 -> ofi = 20
    assert ofi[1] == 20.0


def test_technical_indicators_range():
    """Verify RSI, Bollinger Bands, and ATR on synthetic OHLCV."""
    np.random.seed(42)
    n = 100
    close = pd.Series(100.0 + np.cumsum(np.random.randn(n)))
    high = close + np.random.uniform(0.5, 2.0, n)
    low = close - np.random.uniform(0.5, 2.0, n)
    open_ = close.shift(1).fillna(close.iloc[0])
    volume = pd.Series(np.random.randint(1000, 5000, n))

    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})
    df_tech = add_all_technical_indicators(df)

    # RSI must be strictly in [0, 100]
    rsi_valid = df_tech["rsi_14"].dropna()
    assert (rsi_valid >= 0.0).all() and (rsi_valid <= 100.0).all()

    # Bollinger bands: upper >= middle >= lower
    bb_valid = df_tech.dropna(subset=["bb_upper", "bb_middle", "bb_lower"])
    assert (bb_valid["bb_upper"] >= bb_valid["bb_middle"]).all()
    assert (bb_valid["bb_middle"] >= bb_valid["bb_lower"]).all()

    # ATR must be strictly positive
    atr_valid = df_tech["atr_14"].dropna()
    assert (atr_valid > 0.0).all()


def test_volatility_estimators():
    """Verify realized, Parkinson, and Garman-Klass volatilities."""
    np.random.seed(42)
    n = 60
    close = pd.Series(100.0 + np.cumsum(np.random.randn(n)))
    high = close + np.random.uniform(0.5, 1.5, n)
    low = close - np.random.uniform(0.5, 1.5, n)
    open_ = close + np.random.uniform(-0.5, 0.5, n)

    rv = compute_realized_volatility(close, window=10).dropna()
    pv = compute_parkinson_volatility(high, low, window=10).dropna()
    gk = compute_garman_klass_volatility(open_, high, low, close, window=10).dropna()

    assert (rv > 0.0).all()
    assert (pv > 0.0).all()
    assert (gk > 0.0).all()


def test_feature_pipeline_ohlcv():
    """Verify Master Feature Pipeline runs without error and generates lag features."""
    np.random.seed(42)
    n = 100
    close = pd.Series(100.0 + np.cumsum(np.random.randn(n)))
    df = pd.DataFrame({
        "open": close + np.random.uniform(-0.5, 0.5, n),
        "high": close + np.random.uniform(0.5, 1.5, n),
        "low": close - np.random.uniform(0.5, 1.5, n),
        "close": close,
        "volume": pd.Series(np.random.randint(1000, 5000, n)),
    })

    pipe = FeaturePipeline(lag_periods=[1, 2])
    out = pipe.process_ohlcv(df, add_lags=True, dropna=True)

    assert "close_lag_1" in out.columns
    assert "close_lag_2" in out.columns
    assert "rsi_lag_1" in out.columns
    assert "vol_realized" in out.columns
    assert out.isna().sum().sum() == 0
