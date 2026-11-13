"""
MIRAI — API Routes Package (M15)
"""

from src.api.routes.health import router as health_router
from src.api.routes.market_data import router as market_data_router
from src.api.routes.stock_intelligence import router as stock_intelligence_router
from src.api.routes.predictions import router as predictions_router
from src.api.routes.strategies import router as strategies_router
from src.api.routes.decisions import router as decisions_router
from src.api.routes.portfolio import router as portfolio_router
from src.api.routes.risk import router as risk_router
from src.api.routes.execution import router as execution_router
from src.api.routes.backtesting import router as backtesting_router
from src.api.routes.paper_trading import router as paper_trading_router
from src.api.routes.assistant import router as assistant_router
from src.api.routes.monitoring import router as monitoring_router

__all__ = [
    "health_router",
    "market_data_router",
    "stock_intelligence_router",
    "predictions_router",
    "strategies_router",
    "decisions_router",
    "portfolio_router",
    "risk_router",
    "execution_router",
    "backtesting_router",
    "paper_trading_router",
    "assistant_router",
    "monitoring_router",
]
