"""
MIRAI — Order Execution Simulator (M12)
Simulates order fills across MARKET, LIMIT, TWAP, and VWAP execution strategies.
Supports partial fills, remaining quantity tracking, slippage, and transaction costs.
Produces deterministic, reproducible execution schedules.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.utils.logger import get_logger
from src.execution.execution_schemas import (
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    ExecutionSlice,
    ExecutionResult,
)
from src.execution.slippage_model import BaseSlippageModel, CompositeSlippageModel
from src.execution.transaction_costs import TransactionCostModel

logger = get_logger("ExecutionSimulator")


class ExecutionSimulator:
    """
    Simulates order fills against bar market data (OHLCV).
    Enforces limit price constraints, supports partial fills, and generates slice history.
    """

    def __init__(
        self,
        slippage_model: Optional[BaseSlippageModel] = None,
        cost_model: Optional[TransactionCostModel] = None,
        random_seed: int = 42,
    ):
        self.slippage_model = slippage_model or CompositeSlippageModel()
        self.cost_model = cost_model or TransactionCostModel()
        self.rng = np.random.default_rng(random_seed)

    def execute_order(
        self,
        order: Order,
        current_bar: pd.Series,
        volume_profile: Optional[List[float]] = None,
        volatility: Optional[float] = None,
    ) -> ExecutionResult:
        """
        Executes an order using its configured strategy (MARKET, LIMIT, TWAP, VWAP).
        """
        # Validate order can be submitted
        if order.status == OrderStatus.CREATED:
            order.transition_to(OrderStatus.VALIDATED, "Order validated for simulation")
        if order.status == OrderStatus.VALIDATED:
            order.transition_to(OrderStatus.SUBMITTED, "Order submitted to simulator")

        order_type = order.order_type

        if order_type == OrderType.MARKET:
            return self._execute_market(order, current_bar, volatility)
        elif order_type == OrderType.LIMIT:
            return self._execute_limit(order, current_bar, volatility)
        elif order_type == OrderType.TWAP:
            return self._execute_twap(order, current_bar, volatility)
        elif order_type == OrderType.VWAP:
            return self._execute_vwap(order, current_bar, volume_profile, volatility)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

    def _execute_market(
        self,
        order: Order,
        bar: pd.Series,
        volatility: Optional[float],
    ) -> ExecutionResult:
        """Immediate market order fill at open/close with modeled slippage."""
        ref_price = float(bar.get("open", bar.get("close", 100.0)))
        volume = float(bar.get("volume", 0.0)) if "volume" in bar else None
        side = order.side
        qty = order.remaining_quantity
        ts = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp.now()

        # Check for partial fill if order exceeds safe participation rate
        fill_qty = qty
        if volume is not None and volume > 0:
            max_fill = int(volume * 0.20)  # Cannot fill more than 20% of bar volume in one hit
            if max_fill > 0 and qty > max_fill:
                fill_qty = max_fill
                logger.warning(
                    "[%s] Liquidity cap: partial fill %d of %d requested",
                    order.symbol, fill_qty, qty
                )

        slip_res = self.slippage_model.calculate_slippage(
            reference_price=ref_price,
            side=side,
            quantity=fill_qty,
            daily_volume=volume,
            volatility=volatility,
        )

        cost_breakdown = self.cost_model.calculate_costs(
            side=side,
            quantity=fill_qty,
            execution_price=slip_res.execution_price,
        )

        # Update order state
        order.filled_quantity += fill_qty
        order.remaining_quantity = order.request.quantity - order.filled_quantity
        order.average_price = slip_res.execution_price
        order.gross_value = cost_breakdown.gross_value
        order.net_value = cost_breakdown.net_value
        order.total_slippage = slip_res.total_slippage_cost
        order.slippage_bps = slip_res.slippage_bps
        order.total_transaction_cost = cost_breakdown.total_cost
        order.transaction_cost_breakdown = cost_breakdown.to_dict()

        target_status = (
            OrderStatus.FILLED
            if order.remaining_quantity == 0
            else OrderStatus.PARTIALLY_FILLED
        )
        order.transition_to(target_status, f"Market fill {fill_qty} @ {slip_res.execution_price:.2f}")

        slice_obj = ExecutionSlice(
            slice_id=f"{order.order_id}_S1",
            quantity=fill_qty,
            price=slip_res.execution_price,
            slippage=slip_res.slippage_amount,
            slippage_bps=slip_res.slippage_bps,
            transaction_cost=cost_breakdown.total_cost,
            timestamp=ts,
        )
        order.slices.append(slice_obj)

        return ExecutionResult(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            filled_quantity=fill_qty,
            execution_price=slip_res.execution_price,
            reference_price=ref_price,
            slippage=slip_res.slippage_amount,
            slippage_bps=slip_res.slippage_bps,
            gross_value=cost_breakdown.gross_value,
            total_cost=cost_breakdown.total_cost,
            net_value=cost_breakdown.net_value,
            cost_breakdown=cost_breakdown.to_dict(),
            status=order.status,
            timestamp=ts,
        )

    def _execute_limit(
        self,
        order: Order,
        bar: pd.Series,
        volatility: Optional[float],
    ) -> ExecutionResult:
        """
        Executes a limit order against bar high/low.
        Enforces strict limit price ceiling (BUY) or floor (SELL).
        """
        limit_price = order.request.limit_price
        side = order.side
        bar_high = float(bar.get("high", bar.get("close", 100.0)))
        bar_low = float(bar.get("low", bar.get("close", 100.0)))
        bar_open = float(bar.get("open", bar.get("close", 100.0)))
        volume = float(bar.get("volume", 0.0)) if "volume" in bar else None
        ts = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp.now()

        is_fillable = False
        exec_price = limit_price

        if side == OrderSide.BUY:
            # Buy limit order fills if bar low touches or dips below limit price
            if bar_low <= limit_price:
                is_fillable = True
                # Execution price: best of open or limit price, plus modeled slippage (capped at limit)
                raw_ref = min(bar_open, limit_price)
                slip_res = self.slippage_model.calculate_slippage(
                    reference_price=raw_ref,
                    side=side,
                    quantity=order.remaining_quantity,
                    daily_volume=volume,
                    volatility=volatility,
                )
                exec_price = min(limit_price, slip_res.execution_price)
        else:  # SELL
            # Sell limit order fills if bar high reaches or exceeds limit price
            if bar_high >= limit_price:
                is_fillable = True
                raw_ref = max(bar_open, limit_price)
                slip_res = self.slippage_model.calculate_slippage(
                    reference_price=raw_ref,
                    side=side,
                    quantity=order.remaining_quantity,
                    daily_volume=volume,
                    volatility=volatility,
                )
                exec_price = max(limit_price, slip_res.execution_price)

        if not is_fillable:
            # Cannot fill in this bar; order remains SUBMITTED (or EXPIRED if DAY order)
            order.transition_to(OrderStatus.EXPIRED, "Limit price not touched in current bar")
            return ExecutionResult(
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                filled_quantity=0,
                execution_price=0.0,
                reference_price=limit_price,
                slippage=0.0,
                slippage_bps=0.0,
                gross_value=0.0,
                total_cost=0.0,
                net_value=0.0,
                cost_breakdown={},
                status=OrderStatus.EXPIRED,
                timestamp=ts,
            )

        # Limit filled!
        qty = order.remaining_quantity
        cost_breakdown = self.cost_model.calculate_costs(
            side=side,
            quantity=qty,
            execution_price=exec_price,
        )

        order.filled_quantity += qty
        order.remaining_quantity = 0
        order.average_price = exec_price
        order.gross_value = cost_breakdown.gross_value
        order.net_value = cost_breakdown.net_value
        order.total_transaction_cost = cost_breakdown.total_cost
        order.transaction_cost_breakdown = cost_breakdown.to_dict()
        order.total_slippage = abs(exec_price - limit_price) * qty
        order.slippage_bps = (abs(exec_price - limit_price) / limit_price) * 10_000.0

        order.transition_to(OrderStatus.FILLED, f"Limit filled @ {exec_price:.2f}")

        slice_obj = ExecutionSlice(
            slice_id=f"{order.order_id}_LIM",
            quantity=qty,
            price=exec_price,
            slippage=abs(exec_price - limit_price),
            slippage_bps=order.slippage_bps,
            transaction_cost=cost_breakdown.total_cost,
            timestamp=ts,
        )
        order.slices.append(slice_obj)

        return ExecutionResult(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            filled_quantity=qty,
            execution_price=exec_price,
            reference_price=limit_price,
            slippage=abs(exec_price - limit_price),
            slippage_bps=order.slippage_bps,
            gross_value=cost_breakdown.gross_value,
            total_cost=cost_breakdown.total_cost,
            net_value=cost_breakdown.net_value,
            cost_breakdown=cost_breakdown.to_dict(),
            status=OrderStatus.FILLED,
            timestamp=ts,
        )

    def _execute_twap(
        self,
        order: Order,
        bar: pd.Series,
        volatility: Optional[float],
    ) -> ExecutionResult:
        """
        Executes a TWAP schedule by dividing the order into K equal chronological slices.
        """
        num_slices = int(order.request.execution_params.get("num_slices", 4))
        num_slices = max(2, min(20, num_slices))
        total_qty = order.remaining_quantity
        base_slice_qty = total_qty // num_slices
        remainder = total_qty % num_slices

        ref_price = float(bar.get("close", 100.0))
        high_price = float(bar.get("high", ref_price * 1.005))
        low_price = float(bar.get("low", ref_price * 0.995))
        volume = float(bar.get("volume", 0.0)) if "volume" in bar else None
        ts = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp.now()

        # Simulate synthetic intraday price trajectory between low and high
        step_prices = np.linspace(low_price, high_price, num_slices)
        # Deterministic shuffle/drift for realistic trajectory
        np.random.seed(42)
        step_prices += np.random.normal(0, (high_price - low_price) * 0.1, num_slices)

        slice_fills: List[ExecutionSlice] = []
        total_gross = 0.0
        total_costs = 0.0
        total_slip_cost = 0.0

        for i in range(num_slices):
            slice_qty = base_slice_qty + (1 if i < remainder else 0)
            if slice_qty <= 0:
                continue

            slice_ref = float(step_prices[i])
            slice_slip = self.slippage_model.calculate_slippage(
                reference_price=slice_ref,
                side=order.side,
                quantity=slice_qty,
                daily_volume=(volume / num_slices) if volume else None,
                volatility=volatility,
            )

            slice_costs = self.cost_model.calculate_costs(
                side=order.side,
                quantity=slice_qty,
                execution_price=slice_slip.execution_price,
            )

            total_gross += slice_costs.gross_value
            total_costs += slice_costs.total_cost
            total_slip_cost += slice_slip.total_slippage_cost

            slice_fills.append(
                ExecutionSlice(
                    slice_id=f"{order.order_id}_TWAP_{i+1}",
                    quantity=slice_qty,
                    price=slice_slip.execution_price,
                    slippage=slice_slip.slippage_amount,
                    slippage_bps=slice_slip.slippage_bps,
                    transaction_cost=slice_costs.total_cost,
                    timestamp=ts,
                )
            )

        avg_price = total_gross / total_qty if total_qty > 0 else ref_price
        order.filled_quantity += total_qty
        order.remaining_quantity = 0
        order.average_price = avg_price
        order.gross_value = total_gross
        order.total_transaction_cost = total_costs
        order.total_slippage = total_slip_cost
        order.slippage_bps = (total_slip_cost / max(total_gross, 1.0)) * 10_000.0
        order.slices.extend(slice_fills)

        net_val = (
            total_gross + total_costs
            if order.side == OrderSide.BUY
            else max(0.0, total_gross - total_costs)
        )
        order.net_value = net_val
        order.transition_to(OrderStatus.FILLED, f"TWAP ({num_slices} slices) filled @ {avg_price:.2f}")

        return ExecutionResult(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            filled_quantity=total_qty,
            execution_price=avg_price,
            reference_price=ref_price,
            slippage=total_slip_cost / max(total_qty, 1),
            slippage_bps=order.slippage_bps,
            gross_value=total_gross,
            total_cost=total_costs,
            net_value=net_val,
            cost_breakdown={"total_cost": total_costs},
            status=OrderStatus.FILLED,
            timestamp=ts,
        )

    def _execute_vwap(
        self,
        order: Order,
        bar: pd.Series,
        volume_profile: Optional[List[float]],
        volatility: Optional[float],
    ) -> ExecutionResult:
        """
        Executes a VWAP schedule where slice quantities are proportional to historical volume profile.
        """
        ref_price = float(bar.get("close", 100.0))
        high_price = float(bar.get("high", ref_price * 1.005))
        low_price = float(bar.get("low", ref_price * 0.995))
        total_vol = float(bar.get("volume", 100000.0)) if "volume" in bar else 100000.0
        ts = bar.name if isinstance(bar.name, pd.Timestamp) else pd.Timestamp.now()

        # Default U-shaped intraday volume profile if not provided
        profile = volume_profile or [0.35, 0.15, 0.15, 0.35]
        profile_weights = np.array(profile, dtype=np.float64) / sum(profile)
        num_intervals = len(profile_weights)

        total_qty = order.remaining_quantity
        raw_qtys = np.round(profile_weights * total_qty).astype(int)
        # Ensure sum matches total_qty
        diff = total_qty - int(np.sum(raw_qtys))
        raw_qtys[0] += diff

        # Synthetic price curve weighted towards mid-day
        step_prices = np.linspace(bar.get("open", ref_price), ref_price, num_intervals)

        slice_fills: List[ExecutionSlice] = []
        total_gross = 0.0
        total_costs = 0.0
        total_slip_cost = 0.0

        for i, q in enumerate(raw_qtys):
            if q <= 0:
                continue
            slice_vol = total_vol * profile_weights[i]
            slice_slip = self.slippage_model.calculate_slippage(
                reference_price=float(step_prices[i]),
                side=order.side,
                quantity=int(q),
                daily_volume=slice_vol,
                volatility=volatility,
            )

            slice_costs = self.cost_model.calculate_costs(
                side=order.side,
                quantity=int(q),
                execution_price=slice_slip.execution_price,
            )

            total_gross += slice_costs.gross_value
            total_costs += slice_costs.total_cost
            total_slip_cost += slice_slip.total_slippage_cost

            slice_fills.append(
                ExecutionSlice(
                    slice_id=f"{order.order_id}_VWAP_{i+1}",
                    quantity=int(q),
                    price=slice_slip.execution_price,
                    slippage=slice_slip.slippage_amount,
                    slippage_bps=slice_slip.slippage_bps,
                    transaction_cost=slice_costs.total_cost,
                    timestamp=ts,
                )
            )

        avg_price = total_gross / total_qty if total_qty > 0 else ref_price
        order.filled_quantity += total_qty
        order.remaining_quantity = 0
        order.average_price = avg_price
        order.gross_value = total_gross
        order.total_transaction_cost = total_costs
        order.total_slippage = total_slip_cost
        order.slippage_bps = (total_slip_cost / max(total_gross, 1.0)) * 10_000.0
        order.slices.extend(slice_fills)

        net_val = (
            total_gross + total_costs
            if order.side == OrderSide.BUY
            else max(0.0, total_gross - total_costs)
        )
        order.net_value = net_val
        order.transition_to(OrderStatus.FILLED, f"VWAP ({num_intervals} intervals) filled @ {avg_price:.2f}")

        return ExecutionResult(
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            filled_quantity=total_qty,
            execution_price=avg_price,
            reference_price=ref_price,
            slippage=total_slip_cost / max(total_qty, 1),
            slippage_bps=order.slippage_bps,
            gross_value=total_gross,
            total_cost=total_costs,
            net_value=net_val,
            cost_breakdown={"total_cost": total_costs},
            status=OrderStatus.FILLED,
            timestamp=ts,
        )
