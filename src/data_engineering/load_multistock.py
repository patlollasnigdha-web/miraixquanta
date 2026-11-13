"""
ASTRAQUANT X — Multi-Stock Data Loader
Loads, validates, and standardizes multi-asset equity data (NIFTY 50 constituents).
"""

from pathlib import Path
from typing import List, Optional
import pandas as pd

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.data_engineering.clean_data import validate_chronological_order, handle_missing_values

logger = get_logger("LoadMultiStock")


def get_multistock_raw_dir() -> Path:
    cfg = get_config()
    rel_path = cfg.get("paths.raw_nifty_daily_dir", "NIFTY-50-Stock-Market-Data-main/NIFTY-50-Stock-Market-Data-main/data")
    return (PROJECT_ROOT / rel_path).resolve()


def get_multistock_processed_dir() -> Path:
    cfg = get_config()
    rel_path = cfg.get("paths.processed_multistock_dir", "data/processed/multistock")
    path = (PROJECT_ROOT / rel_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_all_daily_stocks(
    years: Optional[List[int]] = None,
    symbols: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Loads daily constituent stock files from raw directory.
    Standardizes schema: ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'previous_close', 'volume', 'turnover'].
    """
    raw_dir = get_multistock_raw_dir()
    if not raw_dir.exists():
        raise FileNotFoundError(f"Multi-stock raw directory does not exist: {raw_dir}")

    csv_files = sorted(raw_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {raw_dir}")

    frames = []
    for f in csv_files:
        year_str = f.stem
        try:
            year = int(year_str)
            if years and year not in years:
                continue
        except ValueError:
            pass

        logger.debug("Loading multi-stock file: %s", f.name)
        df = pd.read_csv(f)

        # Drop unnamed index column if present
        unnamed = [col for col in df.columns if "Unnamed" in col or col == ""]
        if unnamed:
            df = df.drop(columns=unnamed)

        frames.append(df)

    if not frames:
        raise ValueError("No stock data could be loaded for specified criteria.")

    combined = pd.concat(frames, ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"])

    if symbols:
        combined = combined[combined["symbol"].isin(symbols)]

    # Standardize column names to lower case
    combined.columns = [c.strip().lower() for c in combined.columns]

    # Sort by symbol and timestamp
    combined = combined.sort_values(by=["symbol", "timestamp"]).reset_index(drop=True)

    # Validate missing values
    numeric_cols = ["open", "high", "low", "close", "previous_close", "volume", "turnover"]
    existing_numeric = [c for c in numeric_cols if c in combined.columns]
    combined = handle_missing_values(combined, numeric_cols=existing_numeric, strategy="ffill")

    min_ts_str = combined["timestamp"].min().strftime("%Y-%m-%d") if not combined.empty and pd.notna(combined["timestamp"].min()) else "N/A"
    max_ts_str = combined["timestamp"].max().strftime("%Y-%m-%d") if not combined.empty and pd.notna(combined["timestamp"].max()) else "N/A"
    logger.info(
        "Successfully loaded multi-stock data: %d rows, %d distinct symbols, date range %s to %s",
        len(combined),
        combined["symbol"].nunique() if not combined.empty else 0,
        min_ts_str,
        max_ts_str
    )
    return combined


def get_pivot_prices(
    df: pd.DataFrame,
    value_col: str = "close"
) -> pd.DataFrame:
    """
    Transforms multi-stock long-format DataFrame into a wide (T dates x N symbols) price matrix.
    Essential for portfolio optimization, correlation, and covariance calculation.
    """
    if "symbol" not in df.columns or "timestamp" not in df.columns:
        raise KeyError("DataFrame must contain 'symbol' and 'timestamp' columns.")

    if value_col not in df.columns:
        raise KeyError(f"Value column '{value_col}' not found.")

    pivot = df.pivot(index="timestamp", columns="symbol", values=value_col)
    pivot = pivot.sort_index()

    # Forward fill missing daily observations (e.g. trading halts) then backward fill
    pivot = pivot.ffill().bfill()
    return pivot


def get_daily_returns(
    df: pd.DataFrame,
    value_col: str = "close"
) -> pd.DataFrame:
    """
    Calculates percentage daily returns across all assets in wide format.
    """
    prices = get_pivot_prices(df, value_col=value_col)
    returns = prices.pct_change().dropna()
    return returns
