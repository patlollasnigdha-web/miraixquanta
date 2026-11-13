"""
ASTRAQUANT X — Master Feature Pipeline
Assembles, lags, normalizes, and packages features for machine learning pipelines.
"""

from typing import List, Optional
import numpy as np
import pandas as pd

from src.features.technical_indicators import add_all_technical_indicators
from src.features.volatility_features import (
    compute_realized_volatility,
    compute_parkinson_volatility,
    compute_garman_klass_volatility,
)
from src.features.orderbook_features import (
    compute_bid_ask_spread,
    compute_mid_price,
    compute_micro_price,
    compute_depth_imbalance,
)


class FeaturePipeline:
    """Master pipeline for transforming raw market series into ML feature matrices."""

    def __init__(self, lag_periods: Optional[List[int]] = None):
        self.lag_periods = lag_periods or [1, 2, 3, 5]

    def process_ohlcv(
        self,
        df: pd.DataFrame,
        add_lags: bool = True,
        dropna: bool = True,
    ) -> pd.DataFrame:
        """
        Enriches OHLCV DataFrame with technical indicators, volatility estimators,
        and lagged returns.
        """
        out = add_all_technical_indicators(df)

        # Compute multi-estimator volatilities
        if "high" in out.columns and "low" in out.columns:
            out["vol_parkinson"] = compute_parkinson_volatility(out["high"], out["low"], window=20)
            if "open" in out.columns and "close" in out.columns:
                out["vol_garman_klass"] = compute_garman_klass_volatility(
                    out["open"], out["high"], out["low"], out["close"], window=20
                )
        out["vol_realized"] = compute_realized_volatility(out["close"], window=20)

        # Returns
        out["return_1d"] = out["close"].pct_change(1)
        out["return_5d"] = out["close"].pct_change(5)

        # Lag features to avoid any lookahead
        if add_lags:
            for lag in self.lag_periods:
                out[f"close_lag_{lag}"] = out["close"].shift(lag)
                out[f"return_lag_{lag}"] = out["return_1d"].shift(lag)
                out[f"rsi_lag_{lag}"] = out["rsi_14"].shift(lag)

        if dropna:
            out = out.dropna().reset_index(drop=True)

        return out

    def extract_lob_core_features(self, X_40: np.ndarray) -> np.ndarray:
        """
        Given the first 40 basic LOB features:
        [p_a1, v_a1, p_b1, v_b1, ..., p_a10, v_a10, p_b10, v_b10]
        Computes 5 core dynamic microstructure features for level 1:
        1. Spread (nominal)
        2. Relative Spread
        3. Mid Price
        4. Micro Price
        5. Depth Imbalance
        """
        p_a1 = X_40[:, 0]
        v_a1 = X_40[:, 1]
        p_b1 = X_40[:, 2]
        v_b1 = X_40[:, 3]

        spread = compute_bid_ask_spread(p_a1, p_b1)
        mid = compute_mid_price(p_a1, p_b1)
        micro = compute_micro_price(p_a1, v_a1, p_b1, v_b1)
        imbalance = compute_depth_imbalance(v_b1, v_a1)

        return np.column_stack([spread, mid, micro, imbalance])
