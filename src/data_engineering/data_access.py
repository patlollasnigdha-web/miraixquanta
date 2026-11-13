"""
MIRAI — Unified Data Access & Integration Service (M01)
Provides standardized, cached, and validated access to both Pipeline A (FI-2010)
and Pipeline B (NIFTY 50) datasets.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.data_engineering.load_fi2010 import load_fi2010_file
from src.data_engineering.load_multistock import (
    load_all_daily_stocks,
    get_pivot_prices,
    get_daily_returns,
)
from src.data_engineering.load_nifty50 import (
    load_nifty_daily_official,
    load_nifty_intraday,
)

logger = get_logger("DataAccessService")


class DataAccessService:
    """
    Centralized data broker for MIRAI.
    Manages in-memory caching and clean I/O for all downstream intelligence modules.
    """

    def __init__(self):
        self.cfg = get_config()
        self._cache: Dict[str, Any] = {}

    def clear_cache(self):
        """Clears in-memory cached datasets."""
        self._cache.clear()
        logger.info("Cleared DataAccessService in-memory cache.")

    # ---------------------------------------------------------
    # PIPELINE A: FI-2010 MICROSTRUCTURE DATA ACCESS
    # ---------------------------------------------------------
    def get_fi2010_data(
        self,
        market: str = "auction",
        split: str = "training",
        horizon: int = 100,
        use_cache: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Retrieves processed FI-2010 feature matrix X and target labels y.
        """
        cache_key = f"fi2010_{market}_{split}_{horizon}"
        if use_cache and cache_key in self._cache:
            logger.debug("Cache hit for '%s'", cache_key)
            return self._cache[cache_key]

        data_dir = PROJECT_ROOT / "data" / "processed" / "fi2010"
        file_path = data_dir / f"{market}_{split}_horizon_{horizon}.npz"

        if not file_path.exists():
            raise FileNotFoundError(
                f"Processed FI-2010 dataset not found at: {file_path}. "
                f"Run load_fi2010.py first."
            )

        with np.load(file_path) as data:
            X = data["X"]
            y = data["y"]

        if use_cache:
            self._cache[cache_key] = (X, y)

        logger.info("Loaded FI-2010 %s %s (H=%d): X=%s, y=%s", market, split, horizon, X.shape, y.shape)
        return X, y

    # ---------------------------------------------------------
    # PIPELINE B: NIFTY STOCK MARKET DATA ACCESS
    # ---------------------------------------------------------
    def get_nifty_daily_index(self, use_cache: bool = True) -> pd.DataFrame:
        """Retrieves official daily historical OHLC for NIFTY 50 index."""
        cache_key = "nifty_daily_index"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key].copy()

        df = load_nifty_daily_official()
        if use_cache:
            self._cache[cache_key] = df

        return df.copy()

    def get_nifty_intraday_candles(
        self,
        timeframe: str = "1min",
        years: Optional[List[int]] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """Retrieves historical intraday NIFTY index candles (1-min or 15-sec)."""
        cache_key = f"nifty_intraday_{timeframe}_{years}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key].copy()

        df = load_nifty_intraday(timeframe=timeframe, years=years)
        if use_cache:
            self._cache[cache_key] = df

        return df.copy()

    def get_multistock_daily(
        self,
        years: Optional[List[int]] = None,
        symbols: Optional[List[str]] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """Retrieves multi-stock daily data for NIFTY 50 constituent equities."""
        cache_key = f"multistock_daily_{years}_{symbols}"
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key].copy()

        df = load_all_daily_stocks(years=years, symbols=symbols)
        if use_cache:
            self._cache[cache_key] = df

        return df.copy()

    def get_multistock_prices(
        self,
        years: Optional[List[int]] = None,
        symbols: Optional[List[str]] = None,
        value_col: str = "close",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Retrieves wide (T dates x N symbols) price matrix for multi-asset strategies.
        """
        df = self.get_multistock_daily(years=years, symbols=symbols, use_cache=use_cache)
        return get_pivot_prices(df, value_col=value_col)

    # Alias for API & Portfolio consumers
    get_multistock_prices_matrix = get_multistock_prices

    def get_multistock_returns(
        self,
        years: Optional[List[int]] = None,
        symbols: Optional[List[str]] = None,
        value_col: str = "close",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Retrieves wide (T dates x N symbols) percentage returns matrix.
        """
        prices = self.get_multistock_prices(
            years=years, symbols=symbols, value_col=value_col, use_cache=use_cache
        )
        return prices.pct_change().dropna()

    # ---------------------------------------------------------
    # PARQUET STORAGE BUILDERS
    # ---------------------------------------------------------
    def export_processed_nifty_daily(self, filename: str = "nifty50_daily.parquet") -> Path:
        """Exports clean daily index data to Parquet in data/processed/nifty50/."""
        df = self.get_nifty_daily_index(use_cache=False)
        out_dir = PROJECT_ROOT / "data" / "processed" / "nifty50"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        df.to_parquet(out_path, index=False)
        logger.info("Saved processed NIFTY daily to Parquet: %s", out_path)
        return out_path

    def export_processed_multistock(
        self,
        years: Optional[List[int]] = None,
        filename: str = "nifty50_constituents.parquet",
    ) -> Path:
        """Exports clean multi-stock data to Parquet in data/processed/multistock/."""
        df = self.get_multistock_daily(years=years, use_cache=False)
        out_dir = PROJECT_ROOT / "data" / "processed" / "multistock"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / filename
        df.to_parquet(out_path, index=False)
        logger.info("Saved processed multi-stock to Parquet: %s (%d rows)", out_path, len(df))
        return out_path


# Global singleton factory
_service_instance: Optional[DataAccessService] = None


def get_data_access_service() -> DataAccessService:
    """Factory helper to retrieve singleton DataAccessService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DataAccessService()
    return _service_instance
