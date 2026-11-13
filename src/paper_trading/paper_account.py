"""
MIRAI — Paper Trading Account Management (M14)
Maintains simulated virtual capital, available cash, reserved cash,
invested capital, buying power, and realized / unrealized PnL.
Strictly prevents negative cash balances and invalid account states.
"""

from typing import Any, Dict, Optional, Tuple
import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.paper_trading.paper_trading_schemas import PaperAccountState

logger = get_logger("PaperAccount")


class PaperAccount:
    """
    Virtual capital and cash accounting engine for paper trading.
    All operations are strictly simulated; no real-money transactions occur.
    """

    def __init__(
        self,
        account_id: str = "PAPER_ACC_1",
        initial_capital: Optional[float] = None,
        cash_reserve_pct: float = 0.05,
        allow_margin: bool = False,
    ):
        cfg = get_config()
        self.account_id = account_id
        self.initial_capital = float(
            initial_capital
            if initial_capital is not None
            else cfg.get("paper_trading.initial_capital", 1_000_000.0)
        )
        self.cash_reserve_pct = float(cash_reserve_pct)
        self.allow_margin = allow_margin

        # Accounting state
        self.available_cash = self.initial_capital
        self.reserved_cash = 0.0
        self.invested_capital = 0.0
        self.portfolio_market_value = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.circuit_breaker_state = "NORMAL"
        self.last_updated = pd.Timestamp.now()

    @property
    def total_cash(self) -> float:
        """Total cash balance (available + reserved)."""
        return float(self.available_cash + self.reserved_cash)

    @property
    def total_equity(self) -> float:
        """Total account equity: cash + portfolio market value."""
        return float(self.total_cash + self.portfolio_market_value)

    @property
    def buying_power(self) -> float:
        """
        Available buying power after respecting the mandatory cash reserve.
        Buying Power = max(0.0, available_cash - (cash_reserve_pct * total_equity))
        """
        min_cash_required = self.cash_reserve_pct * self.total_equity
        return max(0.0, float(self.available_cash - min_cash_required))

    def reserve_cash(self, amount: float) -> bool:
        """
        Reserves cash for pending open orders.
        Returns True if successful, False if insufficient available cash.
        """
        if amount <= 0.0:
            return True
        if amount > self.available_cash + 1e-6:
            logger.warning(
                "[%s] Cannot reserve %.2f INR: exceeds available cash %.2f INR",
                self.account_id, amount, self.available_cash
            )
            return False

        self.available_cash -= amount
        self.reserved_cash += amount
        self.last_updated = pd.Timestamp.now()
        return True

    def release_reserved_cash(self, amount: float) -> None:
        """Releases previously reserved cash back to available cash."""
        if amount <= 0.0:
            return
        released = min(self.reserved_cash, amount)
        self.reserved_cash -= released
        self.available_cash += released
        self.last_updated = pd.Timestamp.now()

    def process_buy_fill(
        self,
        symbol: str,
        units: int,
        execution_price: float,
        total_transaction_cost: float,
        reserved_amount: float = 0.0,
    ) -> None:
        """
        Applies a completed BUY order to the account balances.
        Deducts gross value + transaction costs from cash.
        """
        if units <= 0 or execution_price <= 0.0:
            raise ValueError(f"Invalid BUY parameters: units={units}, price={execution_price}")

        gross_value = float(units * execution_price)
        net_cash_required = float(gross_value + total_transaction_cost)

        # Release any previously reserved cash for this order
        if reserved_amount > 0.0:
            self.release_reserved_cash(reserved_amount)

        # Ensure cash availability
        if not self.allow_margin and net_cash_required > self.available_cash + 1e-4:
            raise ValueError(
                f"[{self.account_id}] Insufficient cash for BUY: required {net_cash_required:,.2f} INR, "
                f"available {self.available_cash:,.2f} INR."
            )

        self.available_cash -= net_cash_required
        self.invested_capital += gross_value
        self.last_updated = pd.Timestamp.now()
        logger.info(
            "[%s] BUY fill applied: %s %d @ %.2f (Total cash spent: %.2f, Remaining cash: %.2f)",
            self.account_id, symbol, units, execution_price, net_cash_required, self.available_cash
        )

    def process_sell_fill(
        self,
        symbol: str,
        units: int,
        execution_price: float,
        total_transaction_cost: float,
        cost_basis: float,
    ) -> float:
        """
        Applies a completed SELL order to the account balances.
        Adds net proceeds to cash and records realized PnL.

        Returns:
            trade_realized_pnl: Realized P&L in INR for this sale.
        """
        if units <= 0 or execution_price <= 0.0:
            raise ValueError(f"Invalid SELL parameters: units={units}, price={execution_price}")

        gross_value = float(units * execution_price)
        net_proceeds = max(0.0, float(gross_value - total_transaction_cost))

        trade_realized_pnl = float(net_proceeds - cost_basis)

        self.available_cash += net_proceeds
        self.invested_capital = max(0.0, float(self.invested_capital - cost_basis))
        self.realized_pnl += trade_realized_pnl
        self.last_updated = pd.Timestamp.now()

        logger.info(
            "[%s] SELL fill applied: %s %d @ %.2f (Net proceeds: %.2f, Realized PnL: %.2f)",
            self.account_id, symbol, units, execution_price, net_proceeds, trade_realized_pnl
        )
        return trade_realized_pnl

    def update_market_valuation(
        self,
        portfolio_market_value: float,
        portfolio_cost_basis: Optional[float] = None,
    ) -> None:
        """
        Updates portfolio market value and recalculates unrealized PnL and total equity.
        """
        cost_basis = portfolio_cost_basis if portfolio_cost_basis is not None else self.invested_capital
        self.mark_to_market(portfolio_market_value=portfolio_market_value, portfolio_cost_basis=cost_basis)

    def mark_to_market(
        self,
        portfolio_market_value: float,
        portfolio_cost_basis: float,
        circuit_breaker_state: Optional[str] = None,
    ) -> None:
        """
        Updates portfolio valuation and calculates unrealized PnL.
        """
        self.portfolio_market_value = float(portfolio_market_value)
        self.invested_capital = float(portfolio_cost_basis)
        self.unrealized_pnl = float(self.portfolio_market_value - self.invested_capital)
        if circuit_breaker_state:
            self.circuit_breaker_state = circuit_breaker_state
        self.last_updated = pd.Timestamp.now()

    def get_state(self) -> PaperAccountState:
        """Returns structured immutable account snapshot."""
        return PaperAccountState(
            account_id=self.account_id,
            initial_capital=self.initial_capital,
            available_cash=self.available_cash,
            reserved_cash=self.reserved_cash,
            invested_capital=self.invested_capital,
            portfolio_market_value=self.portfolio_market_value,
            total_equity=self.total_equity,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl,
            buying_power=self.buying_power,
            circuit_breaker_state=self.circuit_breaker_state,
            last_updated=self.last_updated,
            is_paper_trading=True,
        )

    def reset(self, initial_capital: Optional[float] = None, confirm: bool = True) -> bool:
        """
        Explicitly resets account state.
        Must be called intentionally with confirm=True; never resets silently.
        """
        if not confirm:
            logger.warning("[%s] Account reset requested without confirm=True. Aborted.", self.account_id)
            return False

        if initial_capital is not None:
            self.initial_capital = float(initial_capital)
        self.available_cash = self.initial_capital
        self.reserved_cash = 0.0
        self.invested_capital = 0.0
        self.portfolio_market_value = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.circuit_breaker_state = "NORMAL"
        self.last_updated = pd.Timestamp.now()
        logger.info("[%s] Paper account explicitly reset to %.2f INR.", self.account_id, self.initial_capital)
        return True
