"""Data engineering package for MIRAI (M01)."""

from src.data_engineering.clean_data import (
    validate_chronological_order,
    handle_missing_values,
    detect_outliers_iqr,
    split_time_series_chronological,
)
from src.data_engineering.load_fi2010 import load_fi2010_file, process_dataset
from src.data_engineering.load_multistock import (
    load_all_daily_stocks,
    get_pivot_prices,
    get_daily_returns,
)
from src.data_engineering.load_nifty50 import (
    load_nifty_daily_official,
    load_nifty_intraday,
)
from src.data_engineering.preprocess import (
    TimeSeriesScaler,
    clip_outliers,
    align_multi_asset_calendar,
)
from src.data_engineering.data_access import (
    DataAccessService,
    get_data_access_service,
)

__all__ = [
    "validate_chronological_order",
    "handle_missing_values",
    "detect_outliers_iqr",
    "split_time_series_chronological",
    "load_fi2010_file",
    "process_dataset",
    "load_all_daily_stocks",
    "get_pivot_prices",
    "get_daily_returns",
    "load_nifty_daily_official",
    "load_nifty_intraday",
    "TimeSeriesScaler",
    "clip_outliers",
    "align_multi_asset_calendar",
    "DataAccessService",
    "get_data_access_service",
]
