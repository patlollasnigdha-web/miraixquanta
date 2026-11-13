"""
ASTRAQUANT X — Unit Tests for Data Ingestion and Validation
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.data_engineering.clean_data import (
    validate_chronological_order,
    handle_missing_values,
    split_time_series_chronological,
)
from src.data_engineering.load_multistock import (
    load_all_daily_stocks,
    get_pivot_prices,
    get_daily_returns,
)
from src.data_engineering.load_nifty50 import load_nifty_daily_official


def test_config_loading():
    """Verify central configuration manager loads config.yaml properly."""
    cfg = get_config()
    assert cfg.get("system.project_name") == "ASTRAQUANT X"
    assert cfg.get("fi2010.num_features") == 144
    assert cfg.get("fi2010.default_horizon") == 100
    assert cfg.get("backtesting.initial_capital") == 1000000.0


def test_logger_creation():
    """Verify logger setup produces valid logger without error."""
    logger = get_logger("TestLogger")
    assert logger.name == "TestLogger"
    logger.info("Test logging message.")


def test_chronological_validation():
    """Verify chronological validation enforces time order."""
    dates = pd.to_datetime(["2024-01-03", "2024-01-01", "2024-01-02"])
    df = pd.DataFrame({"timestamp": dates, "value": [3, 1, 2]})

    # Should re-sort chronologically
    df_sorted = validate_chronological_order(df, time_col="timestamp", sort_if_unordered=True)
    assert df_sorted["timestamp"].is_monotonic_increasing
    assert df_sorted["value"].tolist() == [1, 2, 3]


def test_missing_values_ffill():
    """Verify handle_missing_values fills without lookahead."""
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=5),
        "price": [100.0, np.nan, 102.0, np.nan, 105.0]
    })
    df_clean = handle_missing_values(df, numeric_cols=["price"], strategy="ffill")
    assert df_clean["price"].isna().sum() == 0
    assert df_clean["price"].tolist() == [100.0, 100.0, 102.0, 102.0, 105.0]


def test_chronological_split():
    """Verify train/test split has zero lookahead and respects embargo."""
    n = 100
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n),
        "value": np.arange(n)
    })
    train_df, test_df = split_time_series_chronological(df, train_ratio=0.8, embargo_steps=5)

    assert len(train_df) == 80
    assert len(test_df) == 15
    assert train_df["timestamp"].max() < test_df["timestamp"].min()


def test_fi2010_processed_npz_files_exist():
    """Verify the four processed FI-2010 npz datasets exist and have valid shape."""
    data_dir = PROJECT_ROOT / "data" / "processed" / "fi2010"

    expected = {
        "auction_training_horizon_100.npz": (47342, 144),
        "auction_testing_horizon_100.npz": (45114, 144),
        "non_auction_training_horizon_100.npz": (39512, 144),
        "non_auction_testing_horizon_100.npz": (38397, 144),
    }

    for fname, (expected_samples, expected_features) in expected.items():
        path = data_dir / fname
        assert path.exists(), f"Missing dataset: {fname}"
        with np.load(path) as data:
            assert "X" in data and "y" in data
            assert data["X"].shape == (expected_samples, expected_features)
            assert data["y"].shape == (expected_samples,)
            assert not np.isnan(data["X"]).any()
            assert not np.isnan(data["y"]).any()


def test_load_daily_official_nifty():
    """Verify loading official NIFTY daily data from root CSV."""
    df = load_nifty_daily_official()
    assert len(df) > 200
    assert "timestamp" in df.columns
    assert "close" in df.columns
    assert (df["close"] > 0).all()
    assert df["timestamp"].is_monotonic_increasing


def test_multistock_subset_loading():
    """Verify loading multi-stock constituent data for a single year (2024)."""
    df = load_all_daily_stocks(years=[2024])
    assert len(df) > 1000
    assert "symbol" in df.columns
    assert "close" in df.columns

    # Test pivot matrix
    pivot = get_pivot_prices(df, value_col="close")
    assert pivot.shape[0] > 200  # Over 200 trading days
    assert pivot.shape[1] >= 45  # At least 45 NIFTY-50 symbols present

    # Test returns
    returns = get_daily_returns(df, value_col="close")
    assert returns.shape == (pivot.shape[0] - 1, pivot.shape[1])
