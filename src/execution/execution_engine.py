"""
MIRAI — Intelligent Execution Engine (M12)
Orchestrates order creation, liquidity assessment, risk-guard enforcement,
order routing, simulated fills, and post-trade execution quality reporting.
Directly interfaces with M09 InvestmentDecision and M11 RiskManagementEngine.
"""

from typing import Any, Dict, List, Optional, Union
import pandas as pd

from src.utils.logger import get_logger
from src.decision.decision_schemas import (
    InvestmentDecision,
    DecisionVerdict,
    RiskStatus,
)
from src.risk_management.risk_engine import RiskManagementEngine, CircuitBreakerState
from src.execution.execution_schemas import (
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    ExecutionResult,
)
from src.execution.liquidity_analyzer import LiquidityAnalyzer
from src.execution.execution_simulator import ExecutionSimulator
from src.execution.slippage_model import BaseSlippageModel, CompositeSlippageModel
from src.execution.transaction_costs import TransactionCostModel
from src.execution.execution_report import ExecutionQualityReport, generate_execution_quality_report

logger = get_logger("ExecutionEngine")


class IntelligentExecutionEngine:
    """
    Central execution management system for MIRAI.
    Validates orders against M09 verdicts and M11 risk states, evaluates liquidity,
    and executes orders with realistic slippage and transaction costs.
    """

    def __init__(
        self,
        simulator: Optional[ExecutionSimulator] = None,
        liquidity_analyzer: Optional[LiquidityAnalyzer] = None,
        cost_model: Optional[TransactionCostModel] = None,
        slippage_model: Optional[BaseSlippageModel] = None,
    ):
        self.slippage_model = slippage_model or CompositeSlippageModel()
        self.cost_model = cost_model or TransactionCostModel()
        self.simulator = simulator or ExecutionSimulator(
            slippage_model=self.slippage_model,
            cost_model=self.cost_model,
        )
        self.liquidity_analyzer = liquidity_analyzer or LiquidityAnalyzer()
        self.order_history: List[Order] = []

    def execute_decision(
        self,
        decision: InvestmentDecision,
        current_bar: pd.Series,
        quantity: Optional[int] = None,
        risk_engine: Optional[RiskManagementEngine] = None,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        volume_profile: Optional[List[float]] = None,
        volatility: Optional[float] = None,
    ) -> Order:
        """
        Executes an investment decision following strict M09 and M11 risk guards.
        """
        symbol = decision.symbol
        ref_price = float(current_bar.get("open", current_bar.get("close", 100.0)))
        ts = current_bar.name if isinstance(current_bar.name, pd.Timestamp) else pd.Timestamp.now()

        # 1. Determine Order Side from Decision Action
        if decision.action_type in ("ENTRY_LONG", "BUY"):
            side = OrderSide.BUY
        elif decision.action_type in ("EXIT", "SELL", "ENTRY_SHORT"):
            side = OrderSide.SELL
        else:
            side = OrderSide.BUY

        # 2. Risk Guard 1: Risk Status Check
        if decision.risk_status == RiskStatus.RISK_BLOCKED:
            logger.warning("[%s] Execution REJECTED: decision has RISK_BLOCKED status", symbol)
            req = OrderRequest(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity or 1,
                limit_price=limit_price,
                reference_price=ref_price,
                decision_id=str(decision.timestamp),
            )
            order = Order(request=req)
            order.rejection_reason = "M11 Risk Engine: trade is RISK_BLOCKED"
            order.transition_to(OrderStatus.REJECTED, order.rejection_reason)
            self.order_history.append(order)
            return order

        # 3. Risk Guard 2: Verdict Validation (YES required for entries)
        if decision.action_type in ("ENTRY_LONG", "BUY") and decision.verdict != DecisionVerdict.YES:
            logger.warning("[%s] Execution REJECTED: non-YES verdict (%s) for new entry", symbol, decision.verdict)
            req = OrderRequest(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity or 1,
                limit_price=limit_price,
                reference_price=ref_price,
            )
            order = Order(request=req)
            order.rejection_reason = f"M09 Decision Engine: non-actionable verdict ({decision.verdict})"
            order.transition_to(OrderStatus.REJECTED, order.rejection_reason)
            self.order_history.append(order)
            return order

        # 4. Risk Guard 3: Circuit Breaker State in Risk Engine
        if risk_engine is not None:
            if risk_engine.circuit_breaker_state == CircuitBreakerState.HALTED:
                logger.critical("[%s] Execution REJECTED: Circuit breaker is HALTED", symbol)
                req = OrderRequest(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity or 1,
                    limit_price=limit_price,
                    reference_price=ref_price,
                )
                order = Order(request=req)
                order.rejection_reason = "M11 Circuit Breaker HALTED: all trading suspended"
                order.transition_to(OrderStatus.REJECTED, order.rejection_reason)
                self.order_history.append(order)
                return order

            if (
                risk_engine.circuit_breaker_state == CircuitBreakerState.RESTRICTED
                and side == OrderSide.BUY
            ):
                logger.warning("[%s] Execution REJECTED: Circuit breaker is RESTRICTED (no new entries)", symbol)
                req = OrderRequest(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity or 1,
                    limit_price=limit_price,
                    reference_price=ref_price,
                )
                order = Order(request=req)
                order.rejection_reason = "M11 Circuit Breaker RESTRICTED: new long entries blocked"
                order.transition_to(OrderStatus.REJECTED, order.rejection_reason)
                self.order_history.append(order)
                return order

        # 5. Quantity Determination
        order_qty = quantity
        if order_qty is None or order_qty <= 0:
            if risk_engine is not None:
                # Ask risk engine to evaluate and size
                eval_res = risk_engine.evaluate_trade_approval(
                    decision=decision,
                    current_price=ref_price,
                )
                if eval_res.is_approved and eval_res.recommended_position:
                    order_qty = eval_res.recommended_position.units
                else:
                    logger.warning("[%s] Risk engine sizing rejected trade: %s", symbol, eval_res.rejection_reasons)
                    req = OrderRequest(
                        symbol=symbol,
                        side=side,
                        order_type=order_type,
                        quantity=1,
                        limit_price=limit_price,
                        reference_price=ref_price,
                    )
                    order = Order(request=req)
                    order.rejection_reason = f"Risk engine sizing failed: {'; '.join(eval_res.rejection_reasons)}"
                    order.transition_to(OrderStatus.REJECTED, order.rejection_reason)
                    self.order_history.append(order)
                    return order
            else:
                order_qty = 100  # Default baseline quantity

        if order_qty <= 0:
            logger.warning("[%s] Calculated order quantity <= 0. Sizing yielded zero units.", symbol)
            req = OrderRequest(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=1,
                limit_price=limit_price,
                reference_price=ref_price,
            )
            order = Order(request=req)
            order.rejection_reason = "Calculated order quantity is 0 units."
            order.transition_to(OrderStatus.REJECTED, order.rejection_reason)
            self.order_history.append(order)
            return order

        # 6. Liquidity Assessment & Execution Style Adaptation
        daily_vol = float(current_bar.get("volume", 0.0)) if "volume" in current_bar else None
        liq_eval = self.liquidity_analyzer.assess_order_liquidity(
            symbol=symbol,
            quantity=order_qty,
            daily_volume=daily_vol,
        )

        effective_order_type = order_type
        exec_params: Dict[str, Any] = {}
        if order_type == OrderType.MARKET and liq_eval.recommended_execution_style in ("TWAP", "VWAP"):
            logger.info(
                "[%s] Liquidity analyzer recommends switching MARKET to %s (%d slices)",
                symbol, liq_eval.recommended_execution_style, liq_eval.recommended_slices
            )
            effective_order_type = OrderType(liq_eval.recommended_execution_style)
            exec_params["num_slices"] = liq_eval.recommended_slices

        # 7. Construct Order and Dispatch
        req = OrderRequest(
            symbol=symbol,
            side=side,
            order_type=effective_order_type,
            quantity=order_qty,
            limit_price=limit_price or decision.entry_reference_price,
            reference_price=ref_price,
            execution_params=exec_params,
            decision_id=str(decision.timestamp),
        )
        order = Order(request=req)
        self.simulator.execute_order(
            order=order,
            current_bar=current_bar,
            volume_profile=volume_profile,
            volatility=volatility,
        )

        self.order_history.append(order)
        logger.info(
            "Executed %s for %s: %s %d shares @ avg %.2f (Total cost: %.2f)",
            effective_order_type.value, symbol, side.value, order.filled_quantity,
            order.average_price, order.total_transaction_cost
        )
        return order

    def submit_order(
        self,
        request: OrderRequest,
        current_bar: pd.Series,
        volume_profile: Optional[List[float]] = None,
        volatility: Optional[float] = None,
    ) -> Order:
        """Directly executes an arbitrary OrderRequest through the simulator."""
        order = Order(request=request)
        self.simulator.execute_order(
            order=order,
            current_bar=current_bar,
            volume_profile=volume_profile,
            volatility=volatility,
        )
        self.order_history.append(order)
        return order

    def get_order_report(self, order: Order) -> ExecutionQualityReport:
        """Generates a structured ExecutionQualityReport for a completed order."""
        return generate_execution_quality_report(
            order=order,
            reference_arrival_price=order.request.reference_price,
        )
