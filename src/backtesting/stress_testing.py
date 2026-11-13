"""
MIRAI — Stress Testing & Robustness Analysis (M13)
Simulates adverse market conditions including volatility shocks,
slippage multipliers, and extreme gap-down scenarios.
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from src.utils.logger import get_logger
from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.backtest_report import BacktestReport

logger = get_logger("StressTesting")


class StressTestEngine:
    """
    Executes stress scenarios on market data before feeding into BacktestEngine.
    """

    def __init__(self, backtest_engine: Optional[BacktestEngine] = None):
        self.engine = backtest_engine or BacktestEngine()

    def run_slippage_stress(
        self,
        data: pd.DataFrame,
        strategy: Any,
        symbol: str = "TCS",
        slippage_multipliers: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Evaluates strategy sensitivity to 1x, 2x, 5x, and 10x slippage penalties."""
        mults = slippage_multipliers or [1.0, 2.0, 5.0]
        results = {}

        for m in mults:
            # Scale default slippage in execution engine
            original_bps = self.engine.execution_engine.simulator.slippage_model.base_bps
            self.engine.execution_engine.simulator.slippage_model.base_bps = original_bps * m

            report = self.engine.run_backtest(data, strategy, symbol=symbol)
            results[f"{m}x_slippage"] = {
                "total_return_pct": report.performance_metrics["total_return_pct"],
                "sharpe_ratio": report.performance_metrics["sharpe_ratio"],
                "max_drawdown_pct": report.performance_metrics["max_drawdown_pct"],
                "total_slippage": report.execution_summary["total_slippage_cost"],
            }
            # Restore original
            self.engine.execution_engine.simulator.slippage_model.base_bps = original_bps

        return results
