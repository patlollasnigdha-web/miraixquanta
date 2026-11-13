"""
ASTRAQUANT X — Quantitative Volatility Estimators
Implements classical and extreme-value volatility estimators:
Realized Volatility, Parkinson (High-Low), and Garman-Klass (OHLC).
"""

import numpy as np
import pandas as pd


def compute_realized_volatility(
    close: pd.Series,
    window: int = 20,
    annualize: bool = True,
    factor: int = 252,
) -> pd.Series:
    """
    Computes rolling realized volatility from log returns.
    """
    log_returns = np.log(close / close.shift(1))
    rolling_std = log_returns.rolling(window=window).std()
    if annualize:
        rolling_std = rolling_std * np.sqrt(factor)
    return rolling_std


def compute_parkinson_volatility(
    high: pd.Series,
    low: pd.Series,
    window: int = 20,
    factor: int = 252,
) -> pd.Series:
    """
    Computes Parkinson (1980) extreme-value volatility estimator:
    sigma = sqrt( (1 / (4 * ln(2) * N)) * sum( ln(H / L)^2 ) ) * sqrt(factor)
    More efficient than standard close-to-close volatility.
    """
    log_hl = np.log(high / low.replace(0.0, 1e-8))
    rs = (log_hl ** 2) / (4.0 * np.log(2.0))
    parkinson = np.sqrt(rs.rolling(window=window).mean()) * np.sqrt(factor)
    return parkinson


def compute_garman_klass_volatility(
    open_: pd.Series,
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 20,
    factor: int = 252,
) -> pd.Series:
    """
    Computes Garman-Klass (1980) volatility estimator:
    sigma = sqrt( (1/N) * sum( 0.5 * ln(H/L)^2 - (2*ln(2) - 1) * ln(C/O)^2 ) ) * sqrt(factor)
    Uses open, high, low, close for up to 8x efficiency over standard deviation.
    """
    log_hl = np.log(high / low.replace(0.0, 1e-8))
    log_co = np.log(close / open_.replace(0.0, 1e-8))

    term1 = 0.5 * (log_hl ** 2)
    term2 = (2.0 * np.log(2.0) - 1.0) * (log_co ** 2)
    diff = term1 - term2

    # Clip negative values if any due to rounding
    diff_clipped = diff.clip(lower=0.0)
    gk_vol = np.sqrt(diff_clipped.rolling(window=window).mean()) * np.sqrt(factor)
    return gk_vol


def compute_volatility_percentile(
    volatility: pd.Series,
    window: int = 252,
) -> pd.Series:
    """
    Computes rolling percentile ranking of current volatility over a historical window.
    Output in [0.0, 1.0].
    """
    return volatility.rolling(window=window).apply(
        lambda s: pd.Series(s).rank(pct=True).iloc[-1], raw=False
    )
