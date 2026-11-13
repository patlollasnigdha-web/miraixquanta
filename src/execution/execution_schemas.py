"""
MIRAI — Execution Engine Data Schemas & Lifecycle State Graph (M12)
Defines structured order requests, lifecycle states, execution results,
and strict order state transition validators.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid
import pandas as pd


class OrderSide(str, Enum):
    """Trading direction for an order."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Execution algorithm / order style."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    TWAP = "TWAP"
    VWAP = "VWAP"


class OrderStatus(str, Enum):
    """
    Standardized lifecycle states of an order in MIRAI.
    CREATED -> VALIDATED -> SUBMITTED -> PARTIALLY_FILLED -> FILLED
    Terminal failure/cancel states: REJECTED, CANCELLED, EXPIRED.
    """
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class InvalidOrderStateError(Exception):
    """Raised when an illegal order status transition is attempted."""
    pass


# State Transition Rules Table
# Defines allowed target states from each source state
ALLOWED_TRANSITIONS: Dict[OrderStatus, Set[OrderStatus]] = {
    OrderStatus.CREATED: {
        OrderStatus.VALIDATED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.VALIDATED: {
        OrderStatus.SUBMITTED,
        OrderStatus.REJECTED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.SUBMITTED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
        OrderStatus.REJECTED,
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.PARTIALLY_FILLED,  # Successive fills
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
    },
    OrderStatus.FILLED: set(),    # Terminal state
    OrderStatus.REJECTED: set(),  # Terminal state
    OrderStatus.CANCELLED: set(), # Terminal state
    OrderStatus.EXPIRED: set(),   # Terminal state
}


def validate_status_transition(current_status: OrderStatus, target_status: OrderStatus) -> bool:
    """
    Validates whether transition from current_status to target_status is permitted.
    Raises InvalidOrderStateError if the transition is illegal.
    """
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise InvalidOrderStateError(
            f"Illegal order lifecycle transition: cannot move from {current_status.value} to {target_status.value}. "
            f"Allowed target states: {[s.value for s in allowed]}"
        )
    return True


@dataclass
class OrderRequest:
    """
    Structured inbound request to place a trading order.
    Originates from M09 InvestmentDecision and M11 Risk approvals.
    """
    symbol: str
    side: Union[OrderSide, str]
    order_type: Union[OrderType, str]
    quantity: int
    limit_price: Optional[float] = None
    time_in_force: str = "DAY"  # DAY, GTC, IOC
    pipeline_id: str = "pipeline_b_nifty"
    strategy_id: Optional[str] = None
    decision_id: Optional[str] = None
    order_id: str = field(default_factory=lambda: f"ORD_{uuid.uuid4().hex[:8].upper()}")
    created_at: pd.Timestamp = field(default_factory=pd.Timestamp.now)
    reference_price: Optional[float] = None
    execution_params: Dict[str, Any] = field(default_factory=dict)  # e.g. twap_slices, duration

    def __post_init__(self):
        if isinstance(self.side, str):
            self.side = OrderSide(self.side.upper())
        if isinstance(self.order_type, str):
            self.order_type = OrderType(self.order_type.upper())
        if self.quantity <= 0:
            raise ValueError(f"Requested quantity must be positive, got {self.quantity}")
        if self.order_type == OrderType.LIMIT:
            if self.limit_price is None or self.limit_price <= 0.0:
                raise ValueError("Limit orders must specify a positive limit_price.")


@dataclass
class ExecutionSlice:
    """A partial execution slice belonging to an order (e.g. TWAP/VWAP child fill)."""
    slice_id: str
    quantity: int
    price: float
    slippage: float
    slippage_bps: float
    transaction_cost: float
    timestamp: pd.Timestamp


@dataclass
class Order:
    """
    Master Order entity tracking full execution lifecycle, costs, and fills.
    """
    request: OrderRequest
    status: OrderStatus = OrderStatus.CREATED
    filled_quantity: int = 0
    remaining_quantity: int = 0
    average_price: float = 0.0
    gross_value: float = 0.0
    net_value: float = 0.0
    total_slippage: float = 0.0
    slippage_bps: float = 0.0
    total_transaction_cost: float = 0.0
    transaction_cost_breakdown: Dict[str, float] = field(default_factory=dict)
    rejection_reason: Optional[str] = None
    slices: List[ExecutionSlice] = field(default_factory=list)
    state_history: List[Tuple[OrderStatus, pd.Timestamp, str]] = field(default_factory=list)

    def __post_init__(self):
        self.remaining_quantity = self.request.quantity
        self.record_state(self.status, "Order initialized")

    @property
    def order_id(self) -> str:
        return self.request.order_id

    @property
    def symbol(self) -> str:
        return self.request.symbol

    @property
    def side(self) -> OrderSide:
        return self.request.side

    @property
    def order_type(self) -> OrderType:
        return self.request.order_type

    @property
    def is_complete(self) -> bool:
        return self.status in (OrderStatus.FILLED, OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.EXPIRED)

    def record_state(self, new_status: OrderStatus, note: str = ""):
        """Records an authorized lifecycle transition with timestamp."""
        ts = pd.Timestamp.now()
        self.status = new_status
        self.state_history.append((new_status, ts, note))

    def transition_to(self, target_status: OrderStatus, note: str = ""):
        """Transitions order to target_status if permitted by the lifecycle state machine."""
        validate_status_transition(self.status, target_status)
        self.record_state(target_status, note)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "requested_quantity": self.request.quantity,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "average_price": round(self.average_price, 4),
            "gross_value": round(self.gross_value, 2),
            "net_value": round(self.net_value, 2),
            "total_slippage": round(self.total_slippage, 4),
            "slippage_bps": round(self.slippage_bps, 2),
            "total_transaction_cost": round(self.total_transaction_cost, 2),
            "cost_breakdown": self.transaction_cost_breakdown,
            "rejection_reason": self.rejection_reason,
            "slices_count": len(self.slices),
        }


@dataclass
class ExecutionResult:
    """
    Standardized execution event emitted after an order fill or partial fill.
    """
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    filled_quantity: int
    execution_price: float
    reference_price: float
    slippage: float
    slippage_bps: float
    gross_value: float
    total_cost: float
    net_value: float
    cost_breakdown: Dict[str, float]
    status: OrderStatus
    timestamp: pd.Timestamp
    execution_duration_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "filled_quantity": self.filled_quantity,
            "execution_price": round(self.execution_price, 4),
            "reference_price": round(self.reference_price, 4),
            "slippage": round(self.slippage, 4),
            "slippage_bps": round(self.slippage_bps, 2),
            "gross_value": round(self.gross_value, 2),
            "total_cost": round(self.total_cost, 2),
            "net_value": round(self.net_value, 2),
            "cost_breakdown": self.cost_breakdown,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat() if hasattr(self.timestamp, "isoformat") else str(self.timestamp),
            "execution_duration_sec": self.execution_duration_sec,
        }
