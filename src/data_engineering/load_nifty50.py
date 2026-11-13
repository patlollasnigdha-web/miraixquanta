"""
ASTRAQUANT X — NIFTY 50 Index Data Loader
Loads and standardizes daily and intraday (1-minute and 15-second) NIFTY 50 index data.
"""

from pathlib import Path
from typing import List, Optional
import pandas as pd

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.data_engineering.clean_data import validate_chronological_order, handle_missing_values

logger = get_logger("LoadNifty50")


def get_nifty_intraday_raw_dir() -> Path:
    cfg = get_config()
    rel_path = cfg.get("paths.raw_nifty_intraday_dir", "nifty50-historical-data-main/nifty50-historical-data-main")
    return (PROJECT_ROOT / rel_path).resolve()


def get_nifty_processed_dir() -> Path:
    cfg = get_config()
    rel_path = cfg.get("paths.processed_nifty_dir", "data/processed/nifty50")
    path = (PROJECT_ROOT / rel_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_nifty_daily_official(csv_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Loads official daily historical close data from root CSV.
    Original columns: "Index Name","Date","Open","High","Low","Close"
    """
    if csv_path is None:
        csv_path = PROJECT_ROOT / "NIFTY 50_Historical_PR_13112025to13112026.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Daily NIFTY CSV not found at: {csv_path}")

    df = pd.read_csv(csv_path)
    df.columns = [c.strip().replace('"', '').lower() for c in df.columns]

    # Map 'date' to 'timestamp'
    if "date" in df.columns:
        df["timestamp"] = pd.to_datetime(df["date"], format="%d %b %Y", errors="coerce")
        df = df.drop(columns=["date"])

    # Cast numeric prices
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = validate_chronological_order(df, time_col="timestamp", sort_if_unordered=True)
    df = handle_missing_values(df, numeric_cols=["open", "high", "low", "close"])

    min_ts = df["timestamp"].min().strftime("%Y-%m-%d") if not df.empty and pd.notna(df["timestamp"].min()) else "N/A"
    max_ts = df["timestamp"].max().strftime("%Y-%m-%d") if not df.empty and pd.notna(df["timestamp"].max()) else "N/A"
    logger.info("Loaded official daily NIFTY data: %d rows (%s to %s)", len(df), min_ts, max_ts)
    return df


def load_nifty_intraday(
    timeframe: str = "1min",
    years: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    Loads historical intraday candles (1-minute or 15-second).
    Columns: timestamp, open, high, low, close, volume (if available)
    """
    raw_dir = get_nifty_intraday_raw_dir()
    tf_dir = raw_dir / timeframe

    if not tf_dir.exists():
        raise FileNotFoundError(f"Timeframe directory not found: {tf_dir}")

    csv_files = sorted(tf_dir.rglob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV candle files found under: {tf_dir}")

    frames = []
    for f in csv_files:
        # Check year filtering if requested
        if years:
            matched = any(str(yr) in f.stem for yr in years)
            if not matched:
                continue

        logger.debug("Loading intraday candle file: %s", f.name)
        df = pd.read_csv(f)
        frames.append(df)

    if not frames:
        raise ValueError(f"No intraday data matched filter for timeframe '{timeframe}' and years {years}.")

    combined = pd.concat(frames, ignore_index=True)
    combined.columns = [c.strip().lower() for c in combined.columns]

    # Parse timestamp
    if "timestamp" in combined.columns:
        combined["timestamp"] = pd.to_datetime(combined["timestamp"])
    elif "epoch" in combined.columns:
        combined["timestamp"] = pd.to_datetime(combined["epoch"], unit="s")

    # Drop epoch column if timestamp is available
    if "epoch" in combined.columns and "timestamp" in combined.columns:
        combined = combined.drop(columns=["epoch"])

    combined = validate_chronological_order(combined, time_col="timestamp", sort_if_unordered=True)

    numeric_cols = ["open", "high", "low", "close"]
    if "volume" in combined.columns:
        numeric_cols.append("volume")

    combined = handle_missing_values(combined, numeric_cols=numeric_cols)

    min_ts = combined["timestamp"].min().strftime("%Y-%m-%d %H:%M") if not combined.empty and pd.notna(combined["timestamp"].min()) else "N/A"
    max_ts = combined["timestamp"].max().strftime("%Y-%m-%d %H:%M") if not combined.empty and pd.notna(combined["timestamp"].max()) else "N/A"
    logger.info("Loaded intraday %s NIFTY candles: %d rows (%s to %s)", timeframe, len(combined), min_ts, max_ts)
    return combined
