"""
MIRAI — Execution Quality & Implementation Shortfall Report (M12)
Computes comprehensive post-trade execution quality metrics including
fill rates, price slippage, transaction drag, and Implementation Shortfall.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd

from src.execution.execution_schemas import Order, OrderSide


@dataclass
class ExecutionQualityReport:
    """Standardized post-trade execution analysis container."""
    order_id: str
    symbol: str
    side: str
    execution_method: str
    requested_quantity: int
    filled_quantity: int
    remaining_quantity: int
    fill_percentage: float
    reference_price: Optional[float]
    average_execution_price: float
    slippage_amount: float
    slippage_bps: float
    brokerage_cost: float
    statutory_costs: float
    total_transaction_cost: float
    total_cost_drag_bps: float
    implementation_shortfall_bps: Optional[float]
    market_impact_estimate_bps: float
    execution_duration_sec: float
    is_fully_filled: bool
    status: str
    assumptions_and_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "execution_method": self.execution_method,
            "requested_quantity": self.requested_quantity,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "fill_percentage": round(self.fill_percentage, 2),
            "reference_price": round(self.reference_price, 4) if self.reference_price is not None else None,
            "average_execution_price": round(self.average_execution_price, 4),
            "slippage_amount": round(self.slippage_amount, 4),
            "slippage_bps": round(self.slippage_bps, 2),
            "brokerage_cost": round(self.brokerage_cost, 2),
            "statutory_costs": round(self.statutory_costs, 2),
            "total_transaction_cost": round(self.total_transaction_cost, 2),
            "total_cost_drag_bps": round(self.total_cost_drag_bps, 2),
            "implementation_shortfall_bps": (
                round(self.implementation_shortfall_bps, 2)
                if self.implementation_shortfall_bps is not None
                else None
            ),
            "market_impact_estimate_bps": round(self.market_impact_estimate_bps, 2),
            "execution_duration_sec": self.execution_duration_sec,
            "is_fully_filled": self.is_fully_filled,
            "status": self.status,
            "assumptions_and_notes": self.assumptions_and_notes,
        }


def generate_execution_quality_report(
    order: Order,
    reference_arrival_price: Optional[float] = None,
    market_impact_bps: float = 0.0,
    duration_sec: float = 0.0,
) -> ExecutionQualityReport:
    """
    Constructs an ExecutionQualityReport from an executed Order object.
    Calculates implementation shortfall when arrival price is present.
    """
    notes: List[str] = []
    req_qty = order.request.quantity
    filled_qty = order.filled_quantity
    rem_qty = order.remaining_quantity
    fill_pct = (filled_qty / req_qty * 100.0) if req_qty > 0 else 0.0

    avg_price = order.average_price
    ref_price = reference_arrival_price or order.request.reference_price

    # 1. Implementation Shortfall calculation
    # Shortfall = (Execution Price - Arrival Price) for BUY, (Arrival Price - Execution Price) for SELL
    shortfall_bps = None
    if ref_price is not None and ref_price > 0 and filled_qty > 0:
        if order.side == OrderSide.BUY:
            price_drag_bps = ((avg_price - ref_price) / ref_price) * 10_000.0
        else:
            price_drag_bps = ((ref_price - avg_price) / ref_price) * 10_000.0

        # Cost drag in bps = (Total Cost / Gross Value) * 10000
        gross_val = max(1.0, order.gross_value)
        cost_drag_bps = (order.total_transaction_cost / gross_val) * 10_000.0
        shortfall_bps = price_drag_bps + cost_drag_bps
    else:
        notes.append("Reference arrival price unavailable. Implementation shortfall omitted.")

    gross = max(1.0, order.gross_value)
    cost_drag_bps = (order.total_transaction_cost / gross) * 10_000.0

    # Itemize brokerage vs statutory
    breakdown = order.transaction_cost_breakdown
    brokerage = breakdown.get("brokerage", 0.0)
    statutory = order.total_transaction_cost - brokerage

    if order.status.value in ("REJECTED", "CANCELLED", "EXPIRED"):
        notes.append(f"Order terminated in {order.status.value} state: {order.rejection_reason or 'No reason provided'}")

    return ExecutionQualityReport(
        order_id=order.order_id,
        symbol=order.symbol,
        side=order.side.value,
        execution_method=order.order_type.value,
        requested_quantity=req_qty,
        filled_quantity=filled_qty,
        remaining_quantity=rem_qty,
        fill_percentage=fill_pct,
        reference_price=ref_price,
        average_execution_price=avg_price,
        slippage_amount=order.total_slippage / max(filled_qty, 1),
        slippage_bps=order.slippage_bps,
        brokerage_cost=brokerage,
        statutory_costs=statutory,
        total_transaction_cost=order.total_transaction_cost,
        total_cost_drag_bps=cost_drag_bps,
        implementation_shortfall_bps=shortfall_bps,
        market_impact_estimate_bps=market_impact_bps,
        execution_duration_sec=duration_sec,
        is_fully_filled=(rem_qty == 0 and filled_qty > 0),
        status=order.status.value,
        assumptions_and_notes=notes,
    )
