"""
MIRAI — Paper Trading Package (M14)
Provides virtual execution orchestration, session management, cash accounting,
position lifecycle tracking, idempotency enforcement, and continuous performance evaluation.
"""

from src.paper_trading.paper_trading_schemas import (
    PaperTradingMode,
    SessionStatus,
    SessionConfig,
    PaperPosition,
    PaperAccountState,
    PaperTradingEvent,
    InvalidSessionStateError,
    validate_session_transition,
)
from src.paper_trading.paper_account import PaperAccount
from src.paper_trading.paper_portfolio import PaperPortfolio
from src.paper_trading.paper_order_manager import PaperOrderManager
from src.paper_trading.paper_trade_manager import PaperTradeManager
from src.paper_trading.market_data_adapter import MarketDataAdapter
from src.paper_trading.trading_session import TradingSession
from src.paper_trading.paper_state_manager import PaperStateManager
from src.paper_trading.paper_performance import PaperPerformanceTracker
from src.paper_trading.paper_trading_report import PaperTradingReport
from src.paper_trading.paper_trading_engine import PaperTradingEngine

__all__ = [
    "PaperTradingMode",
    "SessionStatus",
    "SessionConfig",
    "PaperPosition",
    "PaperAccountState",
    "PaperTradingEvent",
    "InvalidSessionStateError",
    "validate_session_transition",
    "PaperAccount",
    "PaperPortfolio",
    "PaperOrderManager",
    "PaperTradeManager",
    "MarketDataAdapter",
    "TradingSession",
    "PaperStateManager",
    "PaperPerformanceTracker",
    "PaperTradingReport",
    "PaperTradingEngine",
]
