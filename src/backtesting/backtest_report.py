"""
MIRAI — Backtest Report Data Container (M13)
Encapsulates complete backtest results, trade logs, performance metrics,
equity & drawdown series, benchmark comparisons, and institutional limitations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd


@dataclass
class BacktestReport:
    """Master report structure for a completed strategy backtest."""
    backtest_id: str
    symbol: str
    pipeline_id: str
    strategy_name: str
    strategy_version: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    total_bars: int
    initial_capital: float
    final_equity: float
    performance_metrics: Dict[str, Any]
    equity_curve: pd.Series
    drawdown_curve: pd.Series
    cash_curve: pd.Series
    trades: List[Dict[str, Any]]
    execution_summary: Dict[str, Any]
    benchmark_comparison: Optional[Dict[str, Any]] = None
    walk_forward_summary: Optional[Dict[str, Any]] = None
    risk_configuration: Dict[str, Any] = field(default_factory=dict)
    limitations_and_assumptions: List[str] = field(default_factory=list)

    @property
    def metrics(self) -> Dict[str, Any]:
        return self.performance_metrics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backtest_id": self.backtest_id,
            "symbol": self.symbol,
            "pipeline_id": self.pipeline_id,
            "strategy_name": self.strategy_name,
            "strategy_version": self.strategy_version,
            "start_date": self.start_date.isoformat() if hasattr(self.start_date, "isoformat") else str(self.start_date),
            "end_date": self.end_date.isoformat() if hasattr(self.end_date, "isoformat") else str(self.end_date),
            "total_bars": self.total_bars,
            "initial_capital": round(self.initial_capital, 2),
            "final_equity": round(self.final_equity, 2),
            "metrics": self.performance_metrics,
            "trades_count": len(self.trades),
            "trades": self.trades,
            "execution_summary": self.execution_summary,
            "benchmark_comparison": self.benchmark_comparison,
            "walk_forward_summary": self.walk_forward_summary,
            "risk_configuration": self.risk_configuration,
            "limitations_and_assumptions": self.limitations_and_assumptions,
        }
