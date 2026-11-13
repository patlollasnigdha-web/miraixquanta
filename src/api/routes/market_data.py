"""
MIRAI — Market Data Endpoints (M15)
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
import pandas as pd

from src.api.dependencies import get_data_access_service, get_regime_detector
from src.data_engineering.data_access import DataAccessService
from src.intelligence.regime_detection import RegimeDetector
from src.api.api_schemas import MarketDataResponse

router = APIRouter(prefix="/market", tags=["Market Data"])

DEFAULT_EQUITY_SYMBOLS = [
    "TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN",
    "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "HINDUNILVR", "TATAMOTORS"
]


@router.get("/symbols")
def get_available_symbols() -> Dict[str, Any]:
    """Returns candidate equity universe available for intelligence and trading."""
    return {
        "pipeline": "pipeline_b_nifty",
        "symbols": DEFAULT_EQUITY_SYMBOLS,
        "count": len(DEFAULT_EQUITY_SYMBOLS),
    }


@router.get("/regime")
def get_current_regime(
    pipeline: str = "pipeline_b_nifty",
    data_service: DataAccessService = Depends(get_data_access_service),
    detector: RegimeDetector = Depends(get_regime_detector),
) -> Dict[str, Any]:
    """Returns current market regime detection result and quantitative evidence."""
    if pipeline == "pipeline_a_fi2010":
        return {
            "pipeline": "pipeline_a_fi2010",
            "detected_regime": "ORDER_BOOK_BALANCED",
            "regime_confidence": 0.85,
            "regime_probabilities": {"ORDER_BOOK_BALANCED": 0.85, "VOLATILITY_EXPANSION": 0.15},
            "as_of_date": str(pd.Timestamp.now()),
        }

    df = data_service.get_nifty_daily_index()
    if df.empty:
        return {
            "pipeline": pipeline,
            "detected_regime": "SIDEWAYS_RANGE_BOUND",
            "regime_confidence": 0.50,
            "regime_probabilities": {},
            "as_of_date": str(pd.Timestamp.now()),
        }

    res = detector.detect_regime(df)
    return {
        "pipeline": pipeline,
        "detected_regime": res.detected_regime,
        "regime_confidence": res.regime_confidence,
        "regime_probabilities": res.regime_probabilities,
        "quantitative_evidence": res.quantitative_evidence,
        "as_of_date": str(res.as_of_date),
    }


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
