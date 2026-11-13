"""
Unit Tests for Chronological Walk-Forward Validation (M13).
Verifies temporal ordering, non-overlapping windows, rolling vs expanding modes,
and out-of-sample performance aggregation.
"""

import pytest
import pandas as pd
import numpy as np

from src.backtesting.walk_forward import WalkForwardValidator, WalkForwardFold


@pytest.fixture
def sample_timeseries_df():
    """Generates 300 daily bars with chronological business day index."""
    dates = pd.date_range("2024-01-01", periods=300, freq="B")
    return pd.DataFrame({"close": np.linspace(100, 200, 300)}, index=dates)


def test_walk_forward_splits_generation(sample_timeseries_df):
    """Tests chronological fold generation with rolling windows."""
    # 150 train, 30 val, 30 test = 210 bars per fold
    # Step = 30 bars -> (300 - 210) / 30 = 3 folds
    validator = WalkForwardValidator(
        train_window_bars=150,
        val_window_bars=30,
        test_window_bars=30,
        expanding=False,
    )
    folds = validator.generate_splits(sample_timeseries_df)

    assert len(folds) >= 3

    for fold in folds:
        assert isinstance(fold, WalkForwardFold)
        assert fold.train_bars == 150
        assert fold.val_bars == 30
        assert fold.test_bars == 30
        # Strict temporal ordering: train < val < test
        assert fold.train_end < fold.val_start
        assert fold.val_end < fold.test_start


def test_walk_forward_expanding_window(sample_timeseries_df):
    """Tests that expanding window increases training size in successive folds."""
    validator = WalkForwardValidator(
        train_window_bars=150,
        val_window_bars=30,
        test_window_bars=30,
        expanding=True,
    )
    folds = validator.generate_splits(sample_timeseries_df)

    assert len(folds) >= 2
    # Second fold training bars should be larger than first fold
    assert folds[1].train_bars > folds[0].train_bars


def test_walk_forward_insufficient_data():
    """Verifies that an error is raised when dataset is too small for one fold."""
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    df = pd.DataFrame({"close": np.linspace(100, 200, 100)}, index=dates)

    validator = WalkForwardValidator(train_window_bars=150, val_window_bars=30, test_window_bars=30)
    with pytest.raises(ValueError, match="Insufficient data for walk-forward validation"):
        validator.generate_splits(df)


def test_walk_forward_strategy_evaluation(sample_timeseries_df):
    """Tests evaluate_strategy callback execution across folds."""
    validator = WalkForwardValidator(
        train_window_bars=150,
        val_window_bars=30,
        test_window_bars=30,
    )

    def dummy_eval(train_df, val_df, test_df):
        # Return mock out-of-sample metrics
        return {"sharpe_ratio": 1.25, "total_return_pct": 5.4}

    results = validator.evaluate_strategy(sample_timeseries_df, dummy_eval)

    assert results["num_folds"] >= 3
    assert results["average_test_sharpe"] == pytest.approx(1.25)
    assert results["average_test_return_pct"] == pytest.approx(5.4)
    assert len(results["fold_details"]) == results["num_folds"]
