"""
MIRAI — Paper Order Manager & Idempotency Engine (M14)
Manages virtual order placement, idempotency tracking, cash reservation,
and execution dispatch through M12 IntelligentExecutionEngine.
"""

from typing import Any, Dict, List, Optional, Set
import hashlib
import pandas as pd

from src.utils.logger import get_logger
from src.execution.execution_schemas import (
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
)
from src.execution.execution_engine import IntelligentExecutionEngine
from src.paper_trading.paper_account import PaperAccount

logger = get_logger("PaperOrderManager")


class PaperOrderManager:
    """
    Manages the lifecycle of paper trading orders with idempotency guarantees.
    Prevents duplicate submissions from identical signals or repeated loop triggers.
    """

    def __init__(
        self,
        account: PaperAccount,
        execution_engine: Optional[IntelligentExecutionEngine] = None,
    ):
        self.account = account
        self.execution_engine = execution_engine or IntelligentExecutionEngine()

        self._orders: Dict[str, Order] = {}
        self._processed_idempotency_keys: Set[str] = set()

    def generate_idempotency_key(
        self,
        symbol: str,
        side: str,
        quantity: int,
        timestamp: pd.Timestamp,
        strategy_id: Optional[str] = None,
    ) -> str:
        """
        Constructs a unique deterministic fingerprint for a trade intent.
        """
        ts_str = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)
        payload = f"{symbol.upper()}:{side.upper()}:{quantity}:{ts_str}:{strategy_id or ''}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def place_order(
        self,
        request: OrderRequest,
        current_bar: pd.Series,
        idempotency_key: Optional[str] = None,
        volatility: Optional[float] = None,
    ) -> Order:
        """
        Validates idempotency, reserves cash if limit order, and submits to execution engine.
        """
        # 1. Idempotency Check
        idem_key = idempotency_key or self.generate_idempotency_key(
            symbol=request.symbol,
            side=request.side.value if isinstance(request.side, OrderSide) else str(request.side),
            quantity=request.quantity,
            timestamp=request.created_at,
            strategy_id=request.strategy_id,
        )

        if idem_key in self._processed_idempotency_keys:
            logger.warning("[%s] Duplicate order detected (Key: %s). Rejecting.", request.symbol, idem_key)
            order = Order(request=request)
            order.rejection_reason = f"Duplicate order intent rejected by idempotency guard ({idem_key})"
            order.transition_to(OrderStatus.REJECTED, order.rejection_reason)
            self._orders[order.order_id] = order
            return order

        self._processed_idempotency_keys.add(idem_key)

        # 2. Buying Power & Pre-Trade Cash Check for BUY orders
        ref_price = request.limit_price or float(current_bar.get("open", current_bar.get("close", 100.0)))
        estimated_cost = request.quantity * ref_price * 1.002  # +0.2% buffer for fees/slippage

        if request.side == OrderSide.BUY:
            if estimated_cost > self.account.available_cash + 1e-4:
                logger.warning(
                    "[%s] Order rejected: estimated cost (%.2f INR) exceeds available cash (%.2f INR)",
                    request.symbol, estimated_cost, self.account.available_cash
                )
                order = Order(request=request)
                order.rejection_reason = (
                    f"Insufficient available cash: required {estimated_cost:,.2f} INR, "
                    f"available {self.account.available_cash:,.2f} INR"
                )
                order.transition_to(OrderStatus.REJECTED, order.rejection_reason)
                self._orders[order.order_id] = order
                return order

            # If LIMIT order, reserve cash while pending
            if request.order_type == OrderType.LIMIT:
                self.account.reserve_cash(estimated_cost)

        # 3. Submit Order to Execution Engine
        order = self.execution_engine.submit_order(
            request=request,
            current_bar=current_bar,
            volatility=volatility,
        )

        # 4. Release Reserved Cash if Limit Order Expired or Rejected
        if request.side == OrderSide.BUY and request.order_type == OrderType.LIMIT:
            if order.status in (OrderStatus.EXPIRED, OrderStatus.REJECTED, OrderStatus.CANCELLED):
                self.account.release_reserved_cash(estimated_cost)

        self._orders[order.order_id] = order
        return order

    def cancel_order(self, order_id: str, reason: str = "User requested cancellation") -> bool:
        """
        Cancels an open or submitted order and releases any reserved cash.
        """
        if order_id not in self._orders:
            logger.warning("Order ID %s not found for cancellation", order_id)
            return False

        order = self._orders[order_id]
        if order.is_complete:
            logger.warning("Order %s already terminal (%s). Cannot cancel.", order_id, order.status.value)
            return False

        # Release cash if BUY limit
        if order.side == OrderSide.BUY and order.order_type == OrderType.LIMIT:
            ref_price = order.request.limit_price or 100.0
            reserved_amt = order.remaining_quantity * ref_price * 1.002
            self.account.release_reserved_cash(reserved_amt)

        order.transition_to(OrderStatus.CANCELLED, reason)
        logger.info("Order %s cancelled: %s", order_id, reason)
        return True

    def get_order(self, order_id: str) -> Optional[Order]:
        """Retrieves order by ID."""
        return self._orders.get(order_id)

    def get_all_orders(self) -> List[Order]:
        """Returns full order history."""
        return list(self._orders.values())

    def get_open_orders(self) -> List[Order]:
        """Returns all non-terminal orders."""
        return [o for o in self._orders.values() if not o.is_complete]
