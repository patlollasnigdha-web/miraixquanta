"""
MIRAI — Paper Trading Schemas & Lifecycle States (M14)
Defines structured dataclasses, state enumerations, and events for simulated
live and replay paper trading.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid
import pandas as pd

from src.execution.execution_schemas import OrderSide, OrderType, OrderStatus


class PaperTradingMode(str, Enum):
    """Execution and market data source mode."""
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"  # Deterministic chronological replay of past data
    LIVE_FEED = "LIVE_FEED"                  # Real-time streaming or polling paper mode


class SessionStatus(str, Enum):
    """Lifecycle states of an active paper trading session."""
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    CLOSED = "CLOSED"


class InvalidSessionStateError(Exception):
    """Raised when an illegal paper trading session transition is attempted."""
    pass


# Valid session transition table
SESSION_TRANSITIONS: Dict[SessionStatus, List[SessionStatus]] = {
    SessionStatus.CREATED: [SessionStatus.RUNNING, SessionStatus.CLOSED],
    SessionStatus.RUNNING: [SessionStatus.PAUSED, SessionStatus.STOPPED],
    SessionStatus.PAUSED: [SessionStatus.RUNNING, SessionStatus.STOPPED],
    SessionStatus.STOPPED: [SessionStatus.CLOSED],
    SessionStatus.CLOSED: [],  # Terminal state
}


def validate_session_transition(current: SessionStatus, target: SessionStatus) -> bool:
    """Validates session state transition against allowed lifecycle table."""
    allowed = SESSION_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise InvalidSessionStateError(
            f"Cannot transition paper session from {current.value} to {target.value}. "
            f"Allowed targets: {[s.value for s in allowed]}"
        )
    return True


@dataclass
class PaperPosition:
    """Represents an active virtual position held in the paper portfolio."""
    symbol: str
    units: int
    average_entry_price: float
    current_price: float
    entry_time: pd.Timestamp
    cost_basis: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    bars_held: int = 0
    trade_id: Optional[str] = None

    def __post_init__(self):
        if self.cost_basis <= 0.0:
            self.cost_basis = float(self.units * self.average_entry_price)
        self.update_price(self.current_price)

    def update_price(self, price: float) -> None:
        """Marks position to market at new price."""
        if price <= 0.0:
            return
        self.current_price = float(price)
        self.market_value = float(self.units * self.current_price)
        self.unrealized_pnl = float(self.market_value - self.cost_basis)
        self.unrealized_pnl_pct = (
            float(self.unrealized_pnl / self.cost_basis) if self.cost_basis > 0 else 0.0
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "units": self.units,
            "average_entry_price": round(self.average_entry_price, 4),
            "current_price": round(self.current_price, 4),
            "cost_basis": round(self.cost_basis, 2),
            "market_value": round(self.market_value, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "unrealized_pnl_pct": round(self.unrealized_pnl_pct * 100.0, 2),
            "stop_loss": round(self.stop_loss, 4) if self.stop_loss is not None else None,
            "take_profit": round(self.take_profit, 4) if self.take_profit is not None else None,
            "bars_held": self.bars_held,
            "entry_time": (
                self.entry_time.isoformat()
                if hasattr(self.entry_time, "isoformat")
                else str(self.entry_time)
            ),
            "trade_id": self.trade_id,
        }


@dataclass
class PaperAccountState:
    """Snapshot of paper account capital, cash, buying power, and PnL."""
    account_id: str
    initial_capital: float
    available_cash: float
    reserved_cash: float
    invested_capital: float
    portfolio_market_value: float
    total_equity: float
    realized_pnl: float
    unrealized_pnl: float
    buying_power: float
    circuit_breaker_state: str
    last_updated: pd.Timestamp
    is_paper_trading: bool = True  # Strict paper flag

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "initial_capital": round(self.initial_capital, 2),
            "available_cash": round(self.available_cash, 2),
            "reserved_cash": round(self.reserved_cash, 2),
            "invested_capital": round(self.invested_capital, 2),
            "portfolio_market_value": round(self.portfolio_market_value, 2),
            "total_equity": round(self.total_equity, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "buying_power": round(self.buying_power, 2),
            "circuit_breaker_state": self.circuit_breaker_state,
            "is_paper_trading": self.is_paper_trading,
            "last_updated": (
                self.last_updated.isoformat()
                if hasattr(self.last_updated, "isoformat")
                else str(self.last_updated)
            ),
        }


@dataclass
class SessionConfig:
    """Configuration bundle defining parameters for a paper trading session."""
    session_id: str = field(default_factory=lambda: f"SESS_{uuid.uuid4().hex[:8].upper()}")
    session_name: str = "PaperTradingSession"
    mode: PaperTradingMode = PaperTradingMode.HISTORICAL_REPLAY
    initial_capital: float = 1_000_000.0
    cash_reserve_pct: float = 0.05
    symbols: List[str] = field(default_factory=lambda: ["TCS"])
    pipeline_id: str = "pipeline_b_nifty"
    replay_speed_multiplier: float = 1.0
    stale_data_timeout_sec: float = 300.0
    db_path: str = "data/paper_trading.db"
    enable_stop_loss: bool = True
    enable_take_profit: bool = True


@dataclass
class PaperTradingEvent:
    """Audit log entry for a paper trading lifecycle event."""
    event_id: str
    session_id: str
    event_type: str  # 'ORDER_FILLED', 'SIGNAL_GENERATED', 'RISK_VETO', etc.
    timestamp: pd.Timestamp
    symbol: Optional[str]
    details: Dict[str, Any] = field(default_factory=dict)
