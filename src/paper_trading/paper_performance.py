"""
MIRAI — Paper Performance Tracking & Analytics (M14)
Tracks real-time continuous equity curves, cash balances, drawdowns,
risk-adjusted performance metrics, and transaction costs for paper trading.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.utils.logger import get_logger
from src.backtesting.trade_simulator import Trade
from src.backtesting.performance_metrics import calculate_performance_metrics, compute_drawdown_curve

logger = get_logger("PaperPerformanceTracker")


class PaperPerformanceTracker:
    """
    Tracks continuous performance for an active paper trading session.
    Records periodic equity snapshots and calculates standard quantitative metrics.
    """

    def __init__(self, initial_capital: float = 1_000_000.0):
        self.initial_capital = float(initial_capital)
        self.snapshots: List[Dict[str, Any]] = []
        self._peak_equity: float = self.initial_capital
        self._max_drawdown: float = 0.0

    def record_snapshot(
        self,
        timestamp: pd.Timestamp,
        equity: float,
        cash: float,
        portfolio_market_value: float = 0.0,
        realized_pnl: float = 0.0,
        unrealized_pnl: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Records a point-in-time account valuation snapshot.
        Updates high-water mark and current drawdown.
        """
        eq = float(equity)
        if eq > self._peak_equity:
            self._peak_equity = eq

        current_dd = (eq - self._peak_equity) / self._peak_equity if self._peak_equity > 0 else 0.0
        if current_dd < self._max_drawdown:
            self._max_drawdown = current_dd

        snapshot = {
            "timestamp": timestamp,
            "equity": eq,
            "cash": float(cash),
            "portfolio_market_value": float(portfolio_market_value),
            "realized_pnl": float(realized_pnl),
            "unrealized_pnl": float(unrealized_pnl),
            "peak_equity": self._peak_equity,
            "drawdown": current_dd,
        }
        self.snapshots.append(snapshot)
        return snapshot

    def get_equity_curve(self) -> pd.Series:
        """Returns time series of total account equity."""
        if not self.snapshots:
            return pd.Series(dtype=np.float64)
        df = pd.DataFrame(self.snapshots)
        series = pd.Series(df["equity"].values, index=pd.to_datetime(df["timestamp"]))
        return series[~series.index.duplicated(keep="last")]

    def get_drawdown_curve(self) -> pd.Series:
        """Returns time series of account drawdowns (values <= 0.0)."""
        eq_curve = self.get_equity_curve()
        if eq_curve.empty:
            return pd.Series(dtype=np.float64)
        dd_series, _, _ = compute_drawdown_curve(eq_curve)
        return dd_series

    def calculate_metrics(
        self,
        trades: Optional[List[Trade]] = None,
        risk_free_rate: float = 0.065,
        annualization_factor: int = 252,
    ) -> Dict[str, Any]:
        """
        Calculates institutional performance metrics from recorded snapshots and trades.
        """
        eq_curve = self.get_equity_curve()
        trade_list = trades or []

        if eq_curve.empty:
            return {
                "initial_capital": self.initial_capital,
                "current_equity": self.initial_capital,
                "total_return_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "current_drawdown_pct": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "calmar_ratio": 0.0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "total_trades": len(trade_list),
                "total_snapshots": 0,
            }

        # Leverage M13 calculation
        base_metrics = calculate_performance_metrics(
            equity_curve=eq_curve,
            trades=trade_list,
            risk_free_rate=risk_free_rate,
            annualization_factor=annualization_factor,
        )

        base_metrics.update({
            "initial_capital": self.initial_capital,
            "current_equity": float(eq_curve.iloc[-1]),
            "peak_equity": self._peak_equity,
            "total_snapshots": len(self.snapshots),
        })
        return base_metrics

    def clear(self) -> None:
        """Clears all recorded snapshots and resets tracking."""
        self.snapshots.clear()
        self._peak_equity = self.initial_capital
        self._max_drawdown = 0.0
