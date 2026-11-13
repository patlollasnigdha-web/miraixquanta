"""
MIRAI — Market Data Endpoints (M15)
"""

from fastapi import APIRouter, Depends, HTTPException, status
import pandas as pd

from src.api.dependencies import get_data_access_service
from src.data_engineering.data_access import DataAccessService
from src.api.api_schemas import MarketDataResponse

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/{symbol}", response_model=MarketDataResponse)
def get_market_data(
    symbol: str,
    data_service: DataAccessService = Depends(get_data_access_service),
):
    """Retrieves available market data bars and latest quote for symbol."""
    sym_clean = symbol.strip().upper()
    df = data_service.get_multistock_daily(symbols=[sym_clean])
    if df.empty:
        df = data_service.get_nifty_daily_index()
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Market data for '{sym_clean}' could not be located.",
            )

    latest = df.iloc[-1].to_dict()
    ts_str = str(df.index[-1]) if hasattr(df.index, "__getitem__") else str(pd.Timestamp.now())

    # Format numeric keys safely
    clean_bar = {}
    for k, v in latest.items():
        clean_bar[str(k)] = float(v) if isinstance(v, (int, float)) else str(v)

    return MarketDataResponse(
        symbol=sym_clean,
        bars_count=len(df),
        latest_bar=clean_bar,
        source_timestamp=ts_str,
        pipeline="pipeline_b_nifty",
    )
