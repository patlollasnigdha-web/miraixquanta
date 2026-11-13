"""
MIRAI — API Request & Response Schemas (M15)
Pydantic models for strict input validation, serialization, and OpenAPI documentation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Common & Health Schemas
# -----------------------------------------------------------------------------

class APIResponse(BaseModel):
    """Standard envelope for successful API responses."""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    overall_status: str
    version: str
    timestamp: datetime
    components: Dict[str, Any]


# -----------------------------------------------------------------------------
# Market Data Schemas
# -----------------------------------------------------------------------------

class MarketDataResponse(BaseModel):
    symbol: str
    bars_count: int
    latest_bar: Dict[str, Any]
    source_timestamp: str
    pipeline: str = "pipeline_b_nifty"


class StockCandle(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class StockCandlesResponse(BaseModel):
    symbol: str
    pipeline: str = "pipeline_b_nifty"
    timeframe: str = "ALL"
    bars_count: int
    latest_timestamp: str
    latest_price: float
    daily_return_pct: Optional[float] = None
    weekly_return_pct: Optional[float] = None
    nifty_relative_return_pct: Optional[float] = None
    candles: List[StockCandle]


# -----------------------------------------------------------------------------
# Stock Intelligence Schemas
# -----------------------------------------------------------------------------

class StockStrengthResponse(BaseModel):
    symbol: str
    stock_strength_score: float
    status: str
    factor_scores: Dict[str, float]
    factor_contributions: Dict[str, float]
    confidence: float
    as_of_date: str


class StockSentimentResponse(BaseModel):
    symbol: str
    sentiment_score: float
    sentiment_label: str
    sentiment_confidence: float
    news_count: int
    fundamental_score: Optional[float] = None
    fundamental_classification: Optional[str] = None
    recent_headlines: List[str] = Field(default_factory=list)
    as_of_date: str


# -----------------------------------------------------------------------------
# Predictions Schemas
# -----------------------------------------------------------------------------

class PredictionRequest(BaseModel):
    symbol: str = Field(..., example="TCS")
    pipeline: str = Field(default="pipeline_b_nifty", example="pipeline_b_nifty")
    horizon: str = Field(default="1d", example="1d")
    model_name: Optional[str] = Field(default="random_forest", example="random_forest")


class PredictionResponse(BaseModel):
    symbol: str
    pipeline: str
    horizon: str
    predicted_direction: str
    confidence: float
    model_version: str
    limitations: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# -----------------------------------------------------------------------------
# Strategy Schemas
# -----------------------------------------------------------------------------

class StrategyInfo(BaseModel):
    name: str
    strategy_id: str
    description: str
    supported_pipelines: List[str]


class StrategyEvaluateRequest(BaseModel):
    strategy_id: str = Field(default="MOMENTUM_STRATEGY", example="MOMENTUM_STRATEGY")
    symbol: str = Field(..., example="TCS")
    pipeline: str = Field(default="pipeline_b_nifty", example="pipeline_b_nifty")


class StrategySignalResponse(BaseModel):
    symbol: str
    strategy_name: str
    signal: str
    signal_strength: float
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    timestamp: str


# -----------------------------------------------------------------------------
# Decision Schemas
# -----------------------------------------------------------------------------

class DecisionEvaluateRequest(BaseModel):
    symbol: str = Field(..., example="TCS")
    pipeline_id: str = Field(default="pipeline_b_nifty", example="pipeline_b_nifty")
    investment_horizon: str = Field(default="1d", example="1d")


class DecisionResponse(BaseModel):
    symbol: str
    verdict: str
    display_label: str
    composite_score: Optional[float] = None
    confidence: float
    action_type: str
    risk_status: str
    entry_reference_price: Optional[float] = None
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    explanation: str
    positive_factors: List[str] = Field(default_factory=list)
    negative_factors: List[str] = Field(default_factory=list)
    conflicting_signals: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    timestamp: str


# -----------------------------------------------------------------------------
# Portfolio Schemas
# -----------------------------------------------------------------------------

class PortfolioOptimiseRequest(BaseModel):
    symbols: List[str] = Field(default_factory=lambda: ["TCS", "INFY", "RELIANCE"], example=["TCS", "INFY", "RELIANCE"])
    method: str = Field(default="risk_budgeting", example="risk_budgeting")
    target_risk_pct: float = Field(default=0.15, example=0.15)


class PortfolioOptimiseResponse(BaseModel):
    method: str
    weights: Dict[str, float]
    expected_annual_return_pct: float
    annual_volatility_pct: float
    sharpe_ratio: float
    diversification_score: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# -----------------------------------------------------------------------------
# Risk Schemas
# -----------------------------------------------------------------------------

class RiskStatusResponse(BaseModel):
    circuit_breaker_state: str
    max_drawdown_limit_pct: float
    max_position_size_pct: float
    cash_reserve_required_pct: float
    status_message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# -----------------------------------------------------------------------------
# Execution Schemas
# -----------------------------------------------------------------------------

class ExecutionSimulateRequest(BaseModel):
    symbol: str = Field(..., example="TCS")
    side: str = Field(..., example="BUY")
    quantity: int = Field(..., example=50)
    order_type: str = Field(default="MARKET", example="MARKET")
    limit_price: Optional[float] = None


class ExecutionSimulateResponse(BaseModel):
    order_id: str
    symbol: str
    side: str
    order_type: str
    status: str
    requested_quantity: int
    filled_quantity: int
    average_price: float
    total_transaction_cost: float
    total_slippage: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# -----------------------------------------------------------------------------
# Backtesting Schemas
# -----------------------------------------------------------------------------

class BacktestRunRequest(BaseModel):
    strategy_id: str = Field(default="MOMENTUM_STRATEGY", example="MOMENTUM_STRATEGY")
    symbols: List[str] = Field(default_factory=lambda: ["TCS"], example=["TCS"])
    initial_capital: float = Field(default=1_000_000.0, example=1_000_000.0)


class BacktestRunResponse(BaseModel):
    backtest_id: str
    status: str
    metrics: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# -----------------------------------------------------------------------------
# Paper Trading Schemas
# -----------------------------------------------------------------------------

class PaperSessionCreateRequest(BaseModel):
    session_name: str = Field(default="ReplaySession", example="DailyReplaySession")
    initial_capital: float = Field(default=1_000_000.0, example=1_000_000.0)
    symbols: List[str] = Field(default_factory=lambda: ["TCS"], example=["TCS"])
    mode: str = Field(default="HISTORICAL_REPLAY", example="HISTORICAL_REPLAY")


class PaperSessionResponse(BaseModel):
    session_id: str
    session_name: str
    status: str
    mode: str
    initial_capital: float
    symbols: List[str]
    start_time: Optional[str] = None
    end_time: Optional[str] = None


# -----------------------------------------------------------------------------
# Assistant Schemas
# -----------------------------------------------------------------------------

class AssistantChatRequest(BaseModel):
    query: str = Field(..., example="Should I invest in TCS?")
    conversation_id: Optional[str] = None


class AssistantChatResponse(BaseModel):
    message: str
    conversation_id: str
    intent: Optional[str] = None
    tools_called: List[str] = Field(default_factory=list)
    verdict: Optional[str] = None
    confidence: Optional[float] = None
    disclaimer: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
