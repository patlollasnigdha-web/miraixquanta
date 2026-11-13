"""
MIRAI — Unit Tests for Data Access & Preprocessing (Batch 1 - M01)
"""

import numpy as np
import pandas as pd
import pytest

from src.data_engineering.preprocess import (
    TimeSeriesScaler,
    clip_outliers,
    align_multi_asset_calendar,
)
from src.data_engineering.data_access import get_data_access_service


def test_time_series_scaler_zscore():
    """Verify z-score scaling fit, transform, and inverse_transform."""
    X = np.array([[10.0, 20.0], [20.0, 40.0], [30.0, 60.0]], dtype=np.float32)
    scaler = TimeSeriesScaler(method="zscore")
    X_scaled = scaler.fit_transform(X)

    # Mean of scaled should be ~0, std should be ~1
    assert np.allclose(np.mean(X_scaled, axis=0), 0.0, atol=1e-5)
    assert np.allclose(np.std(X_scaled, axis=0), 1.0, atol=1e-5)

    # Inverse transform recovers original
    X_rec = scaler.inverse_transform(X_scaled)
    assert np.allclose(X, X_rec, atol=1e-4)


def test_time_series_scaler_minmax():
    """Verify minmax scaling bounded strictly in [0, 1]."""
    X = np.array([5.0, 10.0, 15.0, 20.0], dtype=np.float32)
    scaler = TimeSeriesScaler(method="minmax")
    X_scaled = scaler.fit_transform(X)

    assert X_scaled.min() == 0.0
    assert X_scaled.max() == 1.0
    assert np.allclose(X, scaler.inverse_transform(X_scaled))


def test_clip_outliers():
    """Verify winsorization clips extreme tail values."""
    df = pd.DataFrame({"val": [1.0, 50.0, 52.0, 55.0, 1000.0]})
    df_clipped = clip_outliers(df, lower_quantile=0.1, upper_quantile=0.9)
    assert df_clipped["val"].min() > 1.0
    assert df_clipped["val"].max() < 1000.0


def test_align_multi_asset_calendar():
    """Verify calendar alignment fills missing dates."""
    dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
    df = pd.DataFrame({"A": [10.0, np.nan, 12.0], "B": [np.nan, 20.0, 21.0]}, index=dates)
    aligned = align_multi_asset_calendar(df, fill_method="ffill")
    assert aligned.isna().sum().sum() == 0
    assert aligned.loc["2024-01-02", "A"] == 10.0  # Forward filled


def test_data_access_fi2010():
    """Verify DataAccessService loads FI-2010 benchmark data with caching."""
    service = get_data_access_service()
    X, y = service.get_fi2010_data(market="auction", split="training", horizon=100)

    assert X.shape == (47342, 144)
    assert y.shape == (47342,)

    # Second call should hit in-memory cache
    X_cached, y_cached = service.get_fi2010_data(market="auction", split="training", horizon=100)
    assert X is X_cached  # Same object reference in memory


def test_data_access_nifty_daily():
    """Verify DataAccessService retrieves NIFTY daily index data."""
    service = get_data_access_service()
    df = service.get_nifty_daily_index()
    assert len(df) > 200
    assert "close" in df.columns
    assert "timestamp" in df.columns


def test_data_access_multistock_prices_and_returns():
    """Verify multi-stock price pivot and percentage return matrix."""
    service = get_data_access_service()
    prices = service.get_multistock_prices(years=[2024])
    assert prices.shape[0] > 200
    assert prices.shape[1] >= 45

    returns = service.get_multistock_returns(years=[2024])
    assert returns.shape[0] == prices.shape[0] - 1
    assert returns.shape[1] == prices.shape[1]
