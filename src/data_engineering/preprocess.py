"""
MIRAI — Data Preprocessing & Normalization Engine (M01)
Provides leakage-free scaling, outlier clipping, and multi-asset calendar alignment.
"""

from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("DataPreprocessing")


class TimeSeriesScaler:
    """
    Chronological scaler that strictly fits parameters on training data
    and applies them to out-of-sample test data, preventing forward-looking leakage.
    Supports 'zscore', 'minmax', and 'robust'.
    """

    def __init__(self, method: str = "zscore"):
        if method not in ("zscore", "minmax", "robust"):
            raise ValueError(f"Method must be 'zscore', 'minmax', or 'robust'. Got: {method}")
        self.method = method
        self.params: Dict[str, Union[float, np.ndarray, pd.Series]] = {}
        self.is_fitted = False

    def fit(self, X: Union[np.ndarray, pd.DataFrame, pd.Series]) -> "TimeSeriesScaler":
        """Computes scaling parameters on training data only."""
        if isinstance(X, (pd.DataFrame, pd.Series)):
            values = X.values
        else:
            values = np.asarray(X)

        if self.method == "zscore":
            mean = np.nanmean(values, axis=0)
            std = np.nanstd(values, axis=0)
            # Avoid division by zero
            std = np.where(std == 0, 1e-8, std)
            self.params = {"mean": mean, "std": std}

        elif self.method == "minmax":
            min_val = np.nanmin(values, axis=0)
            max_val = np.nanmax(values, axis=0)
            diff = max_val - min_val
            diff = np.where(diff == 0, 1e-8, diff)
            self.params = {"min": min_val, "diff": diff}

        elif self.method == "robust":
            median = np.nanmedian(values, axis=0)
            q25 = np.nanpercentile(values, 25, axis=0)
            q75 = np.nanpercentile(values, 75, axis=0)
            iqr = q75 - q25
            iqr = np.where(iqr == 0, 1e-8, iqr)
            self.params = {"median": median, "iqr": iqr}

        self.is_fitted = True
        logger.debug("Fitted TimeSeriesScaler using method='%s'", self.method)
        return self

    def transform(
        self, X: Union[np.ndarray, pd.DataFrame, pd.Series]
    ) -> Union[np.ndarray, pd.DataFrame, pd.Series]:
        """Applies fitted parameters to transform incoming data."""
        if not self.is_fitted:
            raise RuntimeError("Scaler is not fitted yet. Call fit() before transform().")

        is_pandas_df = isinstance(X, pd.DataFrame)
        is_pandas_series = isinstance(X, pd.Series)

        if is_pandas_df or is_pandas_series:
            values = X.values
        else:
            values = np.asarray(X)

        if self.method == "zscore":
            scaled = (values - self.params["mean"]) / self.params["std"]
        elif self.method == "minmax":
            scaled = (values - self.params["min"]) / self.params["diff"]
        elif self.method == "robust":
            scaled = (values - self.params["median"]) / self.params["iqr"]

        if is_pandas_df:
            return pd.DataFrame(scaled, index=X.index, columns=X.columns)
        elif is_pandas_series:
            return pd.Series(scaled, index=X.index, name=X.name)
        return scaled

    def fit_transform(
        self, X: Union[np.ndarray, pd.DataFrame, pd.Series]
    ) -> Union[np.ndarray, pd.DataFrame, pd.Series]:
        """Convenience method to fit and transform training set."""
        return self.fit(X).transform(X)

    def inverse_transform(
        self, X: Union[np.ndarray, pd.DataFrame, pd.Series]
    ) -> Union[np.ndarray, pd.DataFrame, pd.Series]:
        """Reverses scaling back to original scale."""
        if not self.is_fitted:
            raise RuntimeError("Scaler is not fitted.")

        is_pandas_df = isinstance(X, pd.DataFrame)
        is_pandas_series = isinstance(X, pd.Series)
        values = X.values if (is_pandas_df or is_pandas_series) else np.asarray(X)

        if self.method == "zscore":
            orig = (values * self.params["std"]) + self.params["mean"]
        elif self.method == "minmax":
            orig = (values * self.params["diff"]) + self.params["min"]
        elif self.method == "robust":
            orig = (values * self.params["iqr"]) + self.params["median"]

        if is_pandas_df:
            return pd.DataFrame(orig, index=X.index, columns=X.columns)
        elif is_pandas_series:
            return pd.Series(orig, index=X.index, name=X.name)
        return orig


def clip_outliers(
    df: pd.DataFrame,
    numeric_cols: Optional[List[str]] = None,
    lower_quantile: float = 0.001,
    upper_quantile: float = 0.999,
) -> pd.DataFrame:
    """
    Winsorizes extreme outliers beyond specified quantiles to protect models from tail anomalies.
    """
    out = df.copy()
    if numeric_cols is None:
        numeric_cols = out.select_dtypes(include=[np.number]).columns.tolist()

    for col in numeric_cols:
        low = out[col].quantile(lower_quantile)
        high = out[col].quantile(upper_quantile)
        out[col] = out[col].clip(lower=low, upper=high)

    logger.debug("Winsorized outliers on %d numeric columns [%.3f, %.3f]", len(numeric_cols), lower_quantile, upper_quantile)
    return out


def align_multi_asset_calendar(
    price_matrix: pd.DataFrame,
    fill_method: str = "ffill",
) -> pd.DataFrame:
    """
    Enforces a synchronous calendar across all constituent stocks in wide format.
    Fills trading halts / missing days using forward fill followed by backward fill.
    """
    aligned = price_matrix.sort_index()
    if fill_method == "ffill":
        aligned = aligned.ffill().bfill()
    elif fill_method == "drop":
        aligned = aligned.dropna()
    return aligned
