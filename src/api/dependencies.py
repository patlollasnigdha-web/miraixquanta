"""
MIRAI — API Dependency Injection (M15)
Provides shared, lazily-loaded singleton service instances for all FastAPI routes.
"""

from functools import lru_cache
from typing import Optional

from src.data_engineering.data_access import DataAccessService
from src.intelligence.stock_strength import StockStrengthAnalyzer
from src.intelligence.regime_detection import RegimeDetector
from src.intelligence.sentiment_analysis import NewsSentimentAnalyzer
from src.intelligence.fundamental_analysis import FundamentalAnalyzer
from src.decision.decision_engine import InvestmentDecisionEngine
from src.risk_management.risk_engine import RiskManagementEngine
from src.execution.execution_engine import IntelligentExecutionEngine
from src.portfolio.portfolio_optimizer import PortfolioOptimizer
from src.paper_trading.paper_state_manager import PaperStateManager
from src.assistant.assistant_engine import AssistantEngine, default_assistant
from src.monitoring.health_monitor import HealthMonitor, default_health
from src.monitoring.metrics_collector import MetricsCollector, default_metrics
from src.monitoring.alert_manager import AlertManager, default_alerts
from src.monitoring.system_monitor import SystemMonitor, default_system_monitor


# Cached singleton factories
@lru_cache()
def get_data_access_service() -> DataAccessService:
    return DataAccessService()


@lru_cache()
def get_stock_strength_analyzer() -> StockStrengthAnalyzer:
    return StockStrengthAnalyzer()


@lru_cache()
def get_regime_detector() -> RegimeDetector:
    return RegimeDetector()


@lru_cache()
def get_sentiment_analyzer() -> NewsSentimentAnalyzer:
    return NewsSentimentAnalyzer()


@lru_cache()
def get_fundamental_analyzer() -> FundamentalAnalyzer:
    return FundamentalAnalyzer()


@lru_cache()
def get_decision_engine() -> InvestmentDecisionEngine:
    return InvestmentDecisionEngine()


@lru_cache()
def get_risk_engine() -> RiskManagementEngine:
    return RiskManagementEngine()


@lru_cache()
def get_execution_engine() -> IntelligentExecutionEngine:
    return IntelligentExecutionEngine()


@lru_cache()
def get_portfolio_optimizer() -> PortfolioOptimizer:
    return PortfolioOptimizer()


@lru_cache()
def get_paper_state_manager() -> PaperStateManager:
    return PaperStateManager()


def get_assistant_engine() -> AssistantEngine:
    return default_assistant


def get_health_monitor() -> HealthMonitor:
    return default_health


def get_metrics_collector() -> MetricsCollector:
    return default_metrics


def get_alert_manager() -> AlertManager:
    return default_alerts


def get_system_monitor() -> SystemMonitor:
    return default_system_monitor
