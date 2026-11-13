"""
MIRAI — Backtesting and Performance Evaluation (M13)
Exports backtesting engine, portfolio simulator, trade tracking,
performance metrics, benchmark comparison, walk-forward validation, and stress testing.
"""

from src.backtesting.trade_simulator import Trade
from src.backtesting.performance_metrics import (
    calculate_performance_metrics,
    compute_drawdown_curve,
)
from src.backtesting.portfolio_simulator import PortfolioSimulator
from src.backtesting.benchmark_comparison import BenchmarkComparator
from src.backtesting.walk_forward import WalkForwardFold, WalkForwardValidator
from src.backtesting.backtest_report import BacktestReport
from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.stress_testing import StressTestEngine

__all__ = [
    "Trade",
    "calculate_performance_metrics",
    "compute_drawdown_curve",
    "PortfolioSimulator",
    "BenchmarkComparator",
    "WalkForwardFold",
    "WalkForwardValidator",
    "BacktestReport",
    "BacktestEngine",
    "StressTestEngine",
]
