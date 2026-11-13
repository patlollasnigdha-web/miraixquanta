"""
ASTRAQUANT X — Data Cleaning and Validation Module
Ensures chronological integrity, handles missing values, detects anomalies,
and prevents data leakage.
"""

from typing import Tuple, Optional
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("DataCleaning")


def validate_chronological_order(
    df: pd.DataFrame,
    time_col: str = "timestamp",
    sort_if_unordered: bool = True
) -> pd.DataFrame:
    """
    Validates that the DataFrame is strictly chronological.
    """
    if time_col not in df.columns:
        raise KeyError(f"Timestamp column '{time_col}' not found in DataFrame.")

    # Convert to datetime if not already
    if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
        df[time_col] = pd.to_datetime(df[time_col])

    is_monotonic = df[time_col].is_monotonic_increasing
    if not is_monotonic:
        if sort_if_unordered:
            logger.warning("DataFrame is not chronologically sorted. Sorting by '%s'...", time_col)
            df = df.sort_values(by=time_col).reset_index(drop=True)
        else:
            raise ValueError(f"DataFrame time index '{time_col}' is not monotonically increasing.")

    # Check for duplicate timestamps if single-series
    duplicate_count = df.duplicated(subset=[time_col]).sum()
    if duplicate_count > 0:
        logger.warning("Found %d duplicate timestamps in series.", duplicate_count)

    return df


def handle_missing_values(
    df: pd.DataFrame,
    numeric_cols: Optional[list] = None,
    max_missing_ratio: float = 0.10,
    strategy: str = "ffill"
) -> pd.DataFrame:
    """
    Checks and handles missing values without forward-looking leakage.
    Forward fill followed by backward fill or zero fill.
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    df_clean = df.copy()
    for col in numeric_cols:
        missing_count = df_clean[col].isna().sum()
        missing_ratio = missing_count / len(df_clean) if len(df_clean) > 0 else 0.0

        if missing_ratio > max_missing_ratio:
            logger.warning(
                "Column '%s' has %.2f%% missing values (exceeds threshold %.2f%%).",
                col, missing_ratio * 100, max_missing_ratio * 100
            )

        if missing_count > 0:
            if strategy == "ffill":
                # Forward fill first (no lookahead), then backward fill edge cases
                df_clean[col] = df_clean[col].ffill().bfill()
            elif strategy == "drop":
                df_clean = df_clean.dropna(subset=[col])
            elif strategy == "zero":
                df_clean[col] = df_clean[col].fillna(0.0)

    return df_clean


def detect_outliers_iqr(
    series: pd.Series,
    factor: float = 3.0
) -> pd.Series:
    """
    Identifies extreme outliers using interquartile range (IQR).
    Returns boolean Series where True indicates an outlier.
    """
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - factor * iqr
    upper_bound = q3 + factor * iqr
    return (series < lower_bound) | (series > upper_bound)


def split_time_series_chronological(
    df: pd.DataFrame,
    train_ratio: float = 0.8,
    embargo_steps: int = 0
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Performs a strict chronological train/test split.
    Prevents leakage by respecting causality and applying an optional embargo.
    """
    if not (0.0 < train_ratio < 1.0):
        raise ValueError(f"train_ratio must be between 0 and 1. Got: {train_ratio}")

    n = len(df)
    train_end = int(n * train_ratio)
    test_start = train_end + embargo_steps

    if test_start >= n:
        raise ValueError("Embargo steps push test start beyond the end of the dataset.")

    train_df = df.iloc[:train_end].copy().reset_index(drop=True)
    test_df = df.iloc[test_start:].copy().reset_index(drop=True)

    logger.info(
        "Chronological split completed: Train=%d samples, Test=%d samples, Embargo=%d",
        len(train_df), len(test_df), embargo_steps
    )
    return train_df, test_df
