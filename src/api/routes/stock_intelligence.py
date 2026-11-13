"""
MIRAI — Stock Intelligence Endpoints (M15)
"""

from fastapi import APIRouter, Depends, HTTPException, status
import pandas as pd

from src.api.dependencies import (
    get_data_access_service,
    get_stock_strength_analyzer,
    get_sentiment_analyzer,
    get_fundamental_analyzer,
)
from src.data_engineering.data_access import DataAccessService
from src.intelligence.stock_strength import StockStrengthAnalyzer
from src.intelligence.sentiment_analysis import NewsSentimentAnalyzer
from src.intelligence.fundamental_analysis import FundamentalAnalyzer
from src.api.api_schemas import StockStrengthResponse, StockSentimentResponse

router = APIRouter(prefix="/stock", tags=["Stock Intelligence"])


@router.get("/{symbol}/strength", response_model=StockStrengthResponse)
def get_stock_strength(
    symbol: str,
    data_service: DataAccessService = Depends(get_data_access_service),
    analyzer: StockStrengthAnalyzer = Depends(get_stock_strength_analyzer),
):
    """Computes Stock Strength Score (0-100) and factor contributions."""
    sym_clean = symbol.strip().upper()
    df = data_service.get_multistock_daily(symbols=[sym_clean])
    if df.empty:
        df = data_service.get_nifty_daily_index()

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Insufficient market data to compute stock strength for '{sym_clean}'.",
        )

    score = analyzer.compute_stock_strength_score(df, symbol=sym_clean)
    return StockStrengthResponse(
        symbol=sym_clean,
        stock_strength_score=score.total_score,
        status=score.status,
        factor_scores=score.factor_scores,
        factor_contributions=score.factor_contributions,
        confidence=score.confidence,
        as_of_date=str(score.as_of_date),
    )


@router.get("/{symbol}/sentiment", response_model=StockSentimentResponse)
def get_stock_sentiment(
    symbol: str,
    sentiment_analyzer: NewsSentimentAnalyzer = Depends(get_sentiment_analyzer),
    fundamental_analyzer: FundamentalAnalyzer = Depends(get_fundamental_analyzer),
):
    """Retrieves news sentiment analysis and fundamental intelligence for symbol."""
    sym_clean = symbol.strip().upper()
    sent_res = sentiment_analyzer.analyze_symbol_sentiment(sym_clean)
    fund_res = fundamental_analyzer.get_fundamental_score(sym_clean)

    return StockSentimentResponse(
        symbol=sym_clean,
        sentiment_score=sent_res.sentiment_score,
        sentiment_label=sent_res.sentiment_label,
        sentiment_confidence=sent_res.confidence,
        news_count=sent_res.news_count,
        fundamental_score=fund_res.total_score,
        fundamental_classification=fund_res.classification,
        recent_headlines=sent_res.recent_headlines[:5],
        as_of_date=str(sent_res.as_of_date),
    )
