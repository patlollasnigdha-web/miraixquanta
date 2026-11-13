"""
ASTRAQUANT X — Technical Indicators
Computes trend, momentum, mean-reversion, and volume indicators on OHLCV series.
"""

from typing import Tuple
import numpy as np
import pandas as pd


def compute_sma(series: pd.Series, window: int = 20) -> pd.Series:
    """Computes Simple Moving Average."""
    return series.rolling(window=window).mean()


def compute_ema(series: pd.Series, window: int = 20) -> pd.Series:
    """Computes Exponential Moving Average."""
    return series.ewm(span=window, adjust=False).mean()


def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """
    Computes Relative Strength Index (RSI) using Wilder's smoothed moving average.
    Output bounded in [0, 100].
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0.0, 1e-8)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Computes MACD: MACD Line, Signal Line, and MACD Histogram.
    """
    ema_fast = compute_ema(close, window=fast)
    ema_slow = compute_ema(close, window=slow)
    macd_line = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, window=signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def compute_bollinger_bands(
    close: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Computes Bollinger Bands:
    Returns (upper, middle, lower, bandwidth, percent_b).
    """
    middle = compute_sma(close, window=window)
    std = close.rolling(window=window).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)

    bandwidth = (upper - lower) / middle.replace(0.0, 1e-8)
    percent_b = (close - lower) / (upper - lower).replace(0.0, 1e-8)
    return upper, middle, lower, bandwidth, percent_b


def compute_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    """
    Computes Average True Range (ATR).
    True Range = max(H - L, |H - C_prev|, |L - C_prev|)
    """
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1.0 / window, adjust=False).mean()
    return atr


def compute_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """
    Computes Volume-Weighted Average Price (cumulative or session-based).
    Typical Price = (High + Low + Close) / 3
    """
    typical_price = (high + low + close) / 3.0
    cum_vol_price = (typical_price * volume).cumsum()
    cum_vol = volume.cumsum().replace(0.0, 1e-8)
    return cum_vol_price / cum_vol


def add_all_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Appends full suite of technical indicators to an OHLCV DataFrame.
    Expects columns: ['open', 'high', 'low', 'close'] and optionally ['volume'].
    """
    out = df.copy()
    close = out["close"]

    # Moving averages
    out["sma_10"] = compute_sma(close, 10)
    out["sma_20"] = compute_sma(close, 20)
    out["sma_50"] = compute_sma(close, 50)
    out["ema_12"] = compute_ema(close, 12)
    out["ema_26"] = compute_ema(close, 26)

    # Momentum
    out["rsi_14"] = compute_rsi(close, 14)
    macd, signal, hist = compute_macd(close, 12, 26, 9)
    out["macd"] = macd
    out["macd_signal"] = signal
    out["macd_hist"] = hist

    # Volatility / Bands
    upper, middle, lower, bw, pct_b = compute_bollinger_bands(close, 20, 2.0)
    out["bb_upper"] = upper
    out["bb_middle"] = middle
    out["bb_lower"] = lower
    out["bb_bandwidth"] = bw
    out["bb_percent_b"] = pct_b

    # ATR
    if "high" in out.columns and "low" in out.columns:
        out["atr_14"] = compute_atr(out["high"], out["low"], close, 14)

    # VWAP if volume exists
    if "volume" in out.columns and "high" in out.columns and "low" in out.columns:
        out["vwap"] = compute_vwap(out["high"], out["low"], close, out["volume"])

    return out
