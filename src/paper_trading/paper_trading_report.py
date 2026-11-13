"""
MIRAI — Paper Trading Reporting (M14)
Encapsulates comprehensive paper trading session results, accounting reconciliation,
risk events, and formal assumptions into structured reports.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("PaperTradingReport")

STANDARD_PAPER_LIMITATIONS = [
    "Simulation only: All trades, orders, and balances are strictly virtual.",
    "No live exchange interaction or real-money brokerage connectivity.",
    "Execution prices assume fill modeling (conservative slippage and fee deduction) based on available bar data.",
    "Order queue priority and actual market impact in large order sizes are theoretical approximations.",
    "Dividends, corporate actions, and overnight margin rates are not credited or charged unless explicitly provided.",
]


@dataclass
class PaperTradingReport:
    """
    Standardized report container for a completed or ongoing paper trading session.
    """
    session_id: str
    session_name: str
    mode: str
    status: str
    start_time: Optional[pd.Timestamp]
    end_time: Optional[pd.Timestamp]
    initial_capital: float
    final_equity: float
    final_cash: float
    total_return_pct: float
    realized_pnl: float
    unrealized_pnl: float
    max_drawdown_pct: float
    win_rate_pct: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_orders: int
    rejected_orders: int
    total_transaction_costs: float
    total_slippage_cost: float
    open_positions: List[Dict[str, Any]] = field(default_factory=list)
    circuit_breaker_events: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=lambda: list(STANDARD_PAPER_LIMITATIONS))
    generated_at: pd.Timestamp = field(default_factory=pd.Timestamp.now)

    def to_dict(self) -> Dict[str, Any]:
        """Converts report to serializable dictionary."""
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "mode": self.mode,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time is not None else None,
            "end_time": self.end_time.isoformat() if self.end_time is not None else None,
            "initial_capital": self.initial_capital,
            "final_equity": self.final_equity,
            "final_cash": self.final_cash,
            "total_return_pct": self.total_return_pct,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "max_drawdown_pct": self.max_drawdown_pct,
            "win_rate_pct": self.win_rate_pct,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_orders": self.total_orders,
            "rejected_orders": self.rejected_orders,
            "total_transaction_costs": self.total_transaction_costs,
            "total_slippage_cost": self.total_slippage_cost,
            "open_positions": self.open_positions,
            "circuit_breaker_events": self.circuit_breaker_events,
            "limitations": self.limitations,
            "generated_at": self.generated_at.isoformat(),
        }

    def to_summary_markdown(self) -> str:
        """Renders executive summary in GitHub Flavored Markdown."""
        lines = [
            f"# MIRAI Paper Trading Report — {self.session_name}",
            f"**Session ID:** `{self.session_id}` | **Mode:** `{self.mode}` | **Status:** `{self.status}`",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 1. Capital & Financial Performance",
            f"- **Initial Capital:** ₹{self.initial_capital:,.2f}",
            f"- **Final Equity:** ₹{self.final_equity:,.2f}",
            f"- **Final Cash:** ₹{self.final_cash:,.2f}",
            f"- **Total Return:** {self.total_return_pct:.2f}%",
            f"- **Realized P&L:** ₹{self.realized_pnl:,.2f}",
            f"- **Unrealized P&L:** ₹{self.unrealized_pnl:,.2f}",
            f"- **Maximum Drawdown:** {abs(self.max_drawdown_pct):.2f}%",
            "",
            "## 2. Trade & Execution Statistics",
            f"- **Total Completed Trades:** {self.total_trades}",
            f"- **Winning Trades:** {self.winning_trades} | **Losing Trades:** {self.losing_trades}",
            f"- **Win Rate:** {self.win_rate_pct:.2f}%",
            f"- **Profit Factor:** {self.profit_factor:.2f}",
            f"- **Total Orders Placed:** {self.total_orders} (Rejected: {self.rejected_orders})",
            f"- **Total Transaction Costs:** ₹{self.total_transaction_costs:,.2f}",
            f"- **Total Estimated Slippage:** ₹{self.total_slippage_cost:,.2f}",
            "",
            f"## 3. Active Positions ({len(self.open_positions)})",
        ]

        if not self.open_positions:
            lines.append("No active open positions remaining.")
        else:
            lines.append("| Symbol | Units | Avg Entry (₹) | Current Price (₹) | Market Value (₹) | Unrealized P&L (₹) |")
            lines.append("|:-------|------:|--------------:|------------------:|-----------------:|-------------------:|")
            for pos in self.open_positions:
                lines.append(
                    f"| {pos.get('symbol', 'N/A')} | {pos.get('units', 0)} | "
                    f"{pos.get('average_entry_price', 0.0):.2f} | {pos.get('current_price', 0.0):.2f} | "
                    f"{pos.get('market_value', 0.0):,.2f} | {pos.get('unrealized_pnl', 0.0):,.2f} |"
                )

        lines.extend([
            "",
            f"## 4. Risk & Circuit Breaker Events ({len(self.circuit_breaker_events)})",
        ])
        if not self.circuit_breaker_events:
            lines.append("No adverse circuit breaker trips or emergency halt events recorded.")
        else:
            for ev in self.circuit_breaker_events:
                lines.append(f"- `[{ev.get('timestamp')}]` **{ev.get('event_type')}:** {ev.get('description')}")

        lines.extend([
            "",
            "## 5. Methodological Notes & Assumptions",
        ])
        for lim in self.limitations:
            lines.append(f"- {lim}")

        return "\n".join(lines)
