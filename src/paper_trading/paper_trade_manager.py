"""
MIRAI — Paper Trade Manager & Round-Trip Tracking (M14)
Tracks completed round-trip paper trades, trade lifecycles, exit reasons,
and realized performance.
"""

from typing import Any, Dict, List, Optional
import uuid
import pandas as pd

from src.utils.logger import get_logger
from src.backtesting.trade_simulator import Trade

logger = get_logger("PaperTradeManager")


class PaperTradeManager:
    """
    Tracks open and closed round-trip trades within a paper trading session.
    """

    def __init__(self):
        self._trades: List[Trade] = []
        self._active_trades: Dict[str, Trade] = {}  # symbol -> Trade

    def open_trade(
        self,
        symbol: str,
        quantity: int,
        entry_price: float,
        entry_time: pd.Timestamp,
        entry_costs: float,
        entry_slippage: float,
        direction: str = "LONG",
    ) -> Trade:
        """Opens a new round-trip trade record."""
        trade_id = f"PTRD_{uuid.uuid4().hex[:6].upper()}"
        trade = Trade(
            trade_id=trade_id,
            symbol=symbol.upper(),
            direction=direction,
            quantity=quantity,
            entry_time=entry_time,
            entry_price=entry_price,
            entry_costs=entry_costs,
            entry_slippage=entry_slippage,
        )
        self._trades.append(trade)
        self._active_trades[symbol.upper()] = trade
        logger.info("Opened paper trade %s for %s (%d units @ %.2f)", trade_id, symbol, quantity, entry_price)
        return trade

    def close_trade(
        self,
        symbol: str,
        exit_price: float,
        exit_time: pd.Timestamp,
        exit_costs: float,
        exit_slippage: float,
        exit_reason: str = "SIGNAL_EXIT",
        bars_held: int = 0,
    ) -> Optional[Trade]:
        """
        Closes active trade for symbol and finalizes gross and net PnL.
        """
        sym = symbol.upper()
        if sym not in self._active_trades:
            logger.warning("No active paper trade found to close for %s", sym)
            return None

        trade = self._active_trades.pop(sym)
        trade.close(
            exit_time=exit_time,
            exit_price=exit_price,
            exit_costs=exit_costs,
            exit_slippage=exit_slippage,
            exit_reason=exit_reason,
            bars_held=bars_held,
        )
        logger.info(
            "Closed paper trade %s for %s: Net PnL %.2f INR (%s)",
            trade.trade_id, sym, trade.net_pnl, exit_reason
        )
        return trade

    def get_open_trades(self) -> List[Trade]:
        """Returns all currently open trades."""
        return list(self._active_trades.values())

    def get_closed_trades(self) -> List[Trade]:
        """Returns all finalized round-trip trades."""
        return [t for t in self._trades if t.is_closed]

    def get_all_trades(self) -> List[Trade]:
        """Returns full trade history."""
        return list(self._trades)

    def clear(self) -> None:
        """Clears all trades (for explicit reset)."""
        self._trades.clear()
        self._active_trades.clear()
