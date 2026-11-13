"""
MIRAI — Paper Portfolio & Position Management (M14)
Tracks virtual holdings, weighted entry prices, unrealized profit & loss,
and stop-loss / take-profit price levels.
"""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from src.utils.logger import get_logger
from src.paper_trading.paper_trading_schemas import PaperPosition

logger = get_logger("PaperPortfolio")


class PaperPortfolio:
    """
    Manages active virtual positions held within a paper trading session.
    """

    def __init__(self):
        self._positions: Dict[str, PaperPosition] = {}

    def get_position(self, symbol: str) -> Optional[PaperPosition]:
        """Retrieves active position for a symbol, if any."""
        return self._positions.get(symbol.upper())

    def get_all_positions(self) -> List[PaperPosition]:
        """Returns list of all active open positions."""
        return list(self._positions.values())

    @property
    def total_market_value(self) -> float:
        """Sum of market values of all open positions."""
        return sum(pos.market_value for pos in self._positions.values())

    @property
    def total_cost_basis(self) -> float:
        """Sum of cost bases of all open positions."""
        return sum(pos.cost_basis for pos in self._positions.values())

    @property
    def total_unrealized_pnl(self) -> float:
        """Total unrealized P&L across all active holdings."""
        return sum(pos.unrealized_pnl for pos in self._positions.values())

    def add_or_update_position(
        self,
        symbol: str,
        units: int,
        entry_price: float,
        entry_time: pd.Timestamp,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        trade_id: Optional[str] = None,
    ) -> PaperPosition:
        """
        Adds units to an existing position or opens a new holding.
        Recomputes weighted average entry price and cost basis.
        """
        sym = symbol.upper()
        if sym in self._positions:
            pos = self._positions[sym]
            new_units = pos.units + units
            new_cost_basis = pos.cost_basis + (units * entry_price)
            new_avg_price = new_cost_basis / new_units if new_units > 0 else entry_price

            pos.units = new_units
            pos.average_entry_price = new_avg_price
            pos.cost_basis = new_cost_basis
            if stop_loss is not None:
                pos.stop_loss = stop_loss
            if take_profit is not None:
                pos.take_profit = take_profit
            pos.update_price(entry_price)
            return pos
        else:
            pos = PaperPosition(
                symbol=sym,
                units=units,
                average_entry_price=entry_price,
                current_price=entry_price,
                entry_time=entry_time,
                stop_loss=stop_loss,
                take_profit=take_profit,
                trade_id=trade_id,
            )
            self._positions[sym] = pos
            return pos

    def reduce_or_close_position(
        self,
        symbol: str,
        units_to_sell: int,
    ) -> Tuple[int, float]:
        """
        Reduces or liquidates a position.

        Returns:
            (actual_units_sold, cost_basis_of_sold_units)
        """
        sym = symbol.upper()
        if sym not in self._positions:
            logger.warning("Attempted to close non-existent position in %s", sym)
            return 0, 0.0

        pos = self._positions[sym]
        sold_units = min(pos.units, units_to_sell)
        cost_basis_sold = float(sold_units * pos.average_entry_price)

        if pos.units <= sold_units:
            # Completely liquidated
            del self._positions[sym]
            logger.info("Position in %s fully liquidated (%d units)", sym, sold_units)
        else:
            # Partially reduced
            pos.units -= sold_units
            pos.cost_basis -= cost_basis_sold
            pos.update_price(pos.current_price)
            logger.info("Position in %s reduced by %d units (remaining: %d)", sym, sold_units, pos.units)

        return sold_units, cost_basis_sold

    def mark_prices(self, price_map: Dict[str, float]) -> None:
        """
        Updates current market price on all active positions.
        """
        for sym, price in price_map.items():
            sym_upper = sym.upper()
            if sym_upper in self._positions:
                self._positions[sym_upper].update_price(price)
                self._positions[sym_upper].bars_held += 1

    def clear(self) -> None:
        """Clears all holdings (used during explicit account resets)."""
        self._positions.clear()
