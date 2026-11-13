"""
MIRAI — Portfolio Simulator & Position Lifecycle (M13)
Tracks cash balance, open positions, mark-to-market equity curves,
and conservative intrabar stop-loss / take-profit executions.
"""

from typing import Any, Dict, List, Optional, Tuple
import uuid
import numpy as np
import pandas as pd

from src.utils.logger import get_logger
from src.execution.execution_schemas import Order, OrderSide, OrderStatus
from src.backtesting.trade_simulator import Trade

logger = get_logger("PortfolioSimulator")


class PortfolioSimulator:
    """
    Maintains historical portfolio state bar-by-bar during backtesting.
    Enforces cash accounting, position tracking, and conservative intrabar stop logic.
    """

    def __init__(self, initial_capital: float = 1_000_000.0):
        self.initial_capital = float(initial_capital)
        self.current_cash = float(initial_capital)
        self.peak_equity = float(initial_capital)

        # Active positions: symbol -> dict
        self.positions: Dict[str, Dict[str, Any]] = {}

        # History
        self.equity_history: Dict[pd.Timestamp, float] = {}
        self.cash_history: Dict[pd.Timestamp, float] = {}
        self.trades: List[Trade] = []
        self._active_trade_map: Dict[str, Trade] = {}  # symbol -> Trade

    @property
    def current_equity(self) -> float:
        """Total portfolio equity (cash + open positions market value)."""
        invested = sum(
            pos["units"] * pos.get("current_price", pos["average_price"])
            for pos in self.positions.values()
        )
        return float(self.current_cash + invested)

    def apply_fill(
        self,
        order: Order,
        timestamp: pd.Timestamp,
        bar_index: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Optional[Trade]:
        """
        Updates cash and positions from an executed Order fill.
        Returns closed Trade object if this was an exit order.
        """
        if order.status != OrderStatus.FILLED and order.status != OrderStatus.PARTIALLY_FILLED:
            return None

        sym = order.symbol
        side = order.side
        qty = order.filled_quantity
        avg_price = order.average_price

        if side == OrderSide.BUY:
            # Cash deducted: net_value includes brokerage, fees, and taxes
            self.current_cash -= order.net_value

            trade_id = f"TRD_{uuid.uuid4().hex[:6].upper()}"
            trade = Trade(
                trade_id=trade_id,
                symbol=sym,
                direction="LONG",
                quantity=qty,
                entry_time=timestamp,
                entry_price=avg_price,
                entry_costs=order.total_transaction_cost,
                entry_slippage=order.total_slippage,
            )
            self.trades.append(trade)
            self._active_trade_map[sym] = trade

            # Create or update position
            if sym in self.positions:
                cur = self.positions[sym]
                total_units = cur["units"] + qty
                cur_cost = (cur["units"] * cur["average_price"]) + (qty * avg_price)
                cur["units"] = total_units
                cur["average_price"] = cur_cost / total_units
                cur["stop_loss"] = stop_loss or cur.get("stop_loss")
                cur["take_profit"] = take_profit or cur.get("take_profit")
            else:
                self.positions[sym] = {
                    "units": qty,
                    "average_price": avg_price,
                    "current_price": avg_price,
                    "entry_bar": bar_index,
                    "entry_time": timestamp,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "trade_id": trade_id,
                }
            return None

        else:  # OrderSide.SELL
            # Cash added: net_value is gross proceeds minus transaction fees
            self.current_cash += order.net_value

            closed_trade = None
            if sym in self._active_trade_map:
                trade = self._active_trade_map.pop(sym)
                pos = self.positions.get(sym, {})
                bars_held = bar_index - pos.get("entry_bar", bar_index)
                trade.close(
                    exit_time=timestamp,
                    exit_price=avg_price,
                    exit_costs=order.total_transaction_cost,
                    exit_slippage=order.total_slippage,
                    exit_reason="SIGNAL_EXIT",
                    bars_held=bars_held,
                )
                closed_trade = trade

            # Remove or decrement position
            if sym in self.positions:
                cur = self.positions[sym]
                if cur["units"] <= qty:
                    del self.positions[sym]
                else:
                    cur["units"] -= qty

            return closed_trade

    def check_intrabar_exits(
        self,
        bar: pd.Series,
        symbol: str,
        bar_index: int,
    ) -> Optional[Tuple[str, float]]:
        """
        Conservative intrabar stop-loss and take-profit detection.

        Rules:
        1. If both stop-loss and take-profit thresholds are breached in the same bar,
           the conservative assumption mandates that STOP-LOSS triggered first.
        2. If bar opened below stop-loss (gap down), exit is executed at bar open (worse than stop price).
        3. Returns (exit_reason, exit_price) or None.
        """
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]
        stop_loss = pos.get("stop_loss")
        take_profit = pos.get("take_profit")

        bar_high = float(bar.get("high", bar.get("close", 100.0)))
        bar_low = float(bar.get("low", bar.get("close", 100.0)))
        bar_open = float(bar.get("open", bar.get("close", 100.0)))

        stop_hit = stop_loss is not None and bar_low <= stop_loss
        target_hit = take_profit is not None and bar_high >= take_profit

        # Rule 1: Dual hit in same bar -> conservative rule executes STOP LOSS
        if stop_hit and target_hit:
            logger.info("[%s] Intrabar dual hit (stop & target). Conservative rule executes STOP_LOSS.", symbol)
            exit_price = min(bar_open, stop_loss)  # Rule 2: Gap down protection
            return "STOP_LOSS", exit_price

        if stop_hit:
            exit_price = min(bar_open, stop_loss)
            return "STOP_LOSS", exit_price

        if target_hit:
            return "TAKE_PROFIT", take_profit

        return None

    def mark_to_market(self, prices: Dict[str, float], timestamp: pd.Timestamp) -> float:
        """
        Updates market price for all open positions and logs current equity and cash.
        """
        for sym, pos in self.positions.items():
            if sym in prices:
                pos["current_price"] = prices[sym]

        eq = self.current_equity
        if eq > self.peak_equity:
            self.peak_equity = eq

        self.equity_history[timestamp] = eq
        self.cash_history[timestamp] = self.current_cash
        return eq

    def get_equity_series(self) -> pd.Series:
        """Returns the full equity curve as a time-indexed pandas Series."""
        return pd.Series(self.equity_history, dtype=np.float64)

    def get_cash_series(self) -> pd.Series:
        """Returns the cash curve as a time-indexed pandas Series."""
        return pd.Series(self.cash_history, dtype=np.float64)
