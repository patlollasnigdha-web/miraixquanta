"""
MIRAI — Trade Simulator & Trade Tracking (M13)
Records, manages, and evaluates individual round-trip trades.
Tracks entry, exit, holding duration, transaction costs, slippage, and gross/net PnL.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
import pandas as pd


@dataclass
class Trade:
    """Master record of an executed individual round-trip trade."""
    trade_id: str
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    quantity: int
    entry_time: pd.Timestamp
    entry_price: float
    entry_costs: float
    entry_slippage: float
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_costs: float = 0.0
    exit_slippage: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    return_pct: float = 0.0
    exit_reason: str = "OPEN"  # 'STOP_LOSS', 'TAKE_PROFIT', 'SIGNAL_EXIT', 'END_OF_DATA', 'OPEN'
    bars_held: int = 0
    is_closed: bool = False

    def close(
        self,
        exit_time: pd.Timestamp,
        exit_price: float,
        exit_costs: float,
        exit_slippage: float,
        exit_reason: str,
        bars_held: int,
    ) -> None:
        """Closes the round-trip trade and computes exact gross and net PnL."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_costs = exit_costs
        self.exit_slippage = exit_slippage
        self.exit_reason = exit_reason
        self.bars_held = bars_held
        self.is_closed = True

        total_costs = self.entry_costs + self.exit_costs

        if self.direction == "LONG":
            self.gross_pnl = float((self.exit_price - self.entry_price) * self.quantity)
        else:  # SHORT
            self.gross_pnl = float((self.entry_price - self.exit_price) * self.quantity)

        self.net_pnl = float(self.gross_pnl - total_costs)
        invested_capital = max(1.0, self.entry_price * self.quantity)
        self.return_pct = float(self.net_pnl / invested_capital)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "quantity": self.quantity,
            "entry_time": self.entry_time.isoformat() if hasattr(self.entry_time, "isoformat") else str(self.entry_time),
            "entry_price": round(self.entry_price, 4),
            "entry_costs": round(self.entry_costs, 2),
            "entry_slippage": round(self.entry_slippage, 4),
            "exit_time": (
                self.exit_time.isoformat()
                if self.exit_time is not None and hasattr(self.exit_time, "isoformat")
                else (str(self.exit_time) if self.exit_time is not None else None)
            ),
            "exit_price": round(self.exit_price, 4) if self.exit_price is not None else None,
            "exit_costs": round(self.exit_costs, 2),
            "exit_slippage": round(self.exit_slippage, 4),
            "gross_pnl": round(self.gross_pnl, 2),
            "net_pnl": round(self.net_pnl, 2),
            "return_pct": round(self.return_pct * 100.0, 2),
            "exit_reason": self.exit_reason,
            "bars_held": self.bars_held,
            "is_closed": self.is_closed,
        }
