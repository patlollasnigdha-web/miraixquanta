"""
MIRAI — Transaction Cost Model (M12)
Provides realistic, configurable transaction cost calculations for Indian equities
(NSE delivery/intraday blend) and customizable fee schedules.
Covers Brokerage, Exchange Turnover Charges, STT, SEBI Charges, Stamp Duty, and GST.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.execution.execution_schemas import OrderSide

logger = get_logger("TransactionCosts")


@dataclass
class TransactionCostBreakdown:
    """Itemized breakdown of all execution costs."""
    gross_value: float
    brokerage: float
    exchange_turnover_fee: float
    sebi_charges: float
    stamp_duty: float
    stt: float  # Securities Transaction Tax
    gst: float  # Goods & Services Tax (18% on brokerage + turnover)
    total_cost: float
    net_value: float  # Gross + total_cost for BUY, Gross - total_cost for SELL
    side: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gross_value": round(self.gross_value, 2),
            "brokerage": round(self.brokerage, 2),
            "exchange_turnover_fee": round(self.exchange_turnover_fee, 2),
            "sebi_charges": round(self.sebi_charges, 4),
            "stamp_duty": round(self.stamp_duty, 2),
            "stt": round(self.stt, 2),
            "gst": round(self.gst, 2),
            "total_cost": round(self.total_cost, 2),
            "net_value": round(self.net_value, 2),
            "side": self.side,
        }


class TransactionCostModel:
    """
    Configurable transaction cost engine for Indian equities and algorithmic trading.
    Prevents double-counting and accurately computes gross and net transaction values.
    """

    def __init__(
        self,
        brokerage_pct: Optional[float] = None,
        stt_pct: Optional[float] = None,
        exchange_turnover_fee_pct: Optional[float] = None,
        sebi_charges_pct: Optional[float] = None,
        stamp_duty_pct: Optional[float] = None,
        gst_pct: Optional[float] = None,
        fixed_brokerage_cap: Optional[float] = 20.0,  # e.g. Zerodha/Groww 20 INR cap
    ):
        cfg = get_config()
        self.brokerage_pct = (
            brokerage_pct
            if brokerage_pct is not None
            else cfg.get("execution.brokerage_pct", 0.0003)
        )
        self.stt_pct = (
            stt_pct
            if stt_pct is not None
            else cfg.get("execution.stt_pct", 0.00025)
        )
        self.exchange_turnover_fee_pct = (
            exchange_turnover_fee_pct
            if exchange_turnover_fee_pct is not None
            else cfg.get("execution.exchange_turnover_fee_pct", 0.0000345)
        )
        self.sebi_charges_pct = (
            sebi_charges_pct
            if sebi_charges_pct is not None
            else cfg.get("execution.sebi_charges_pct", 0.000001)
        )
        self.stamp_duty_pct = (
            stamp_duty_pct
            if stamp_duty_pct is not None
            else cfg.get("execution.stamp_duty_pct", 0.00003)
        )
        self.gst_pct = (
            gst_pct
            if gst_pct is not None
            else cfg.get("execution.gst_pct", 0.18)
        )
        self.fixed_brokerage_cap = fixed_brokerage_cap

    def calculate_costs(
        self,
        side: Union[OrderSide, str],
        quantity: int,
        execution_price: float,
    ) -> TransactionCostBreakdown:
        """
        Computes accurate itemized transaction costs for a filled trade.

        Parameters:
            side: OrderSide.BUY or OrderSide.SELL (or string 'BUY'/'SELL')
            quantity: Number of shares/units
            execution_price: Average executed price per share

        Returns:
            TransactionCostBreakdown with itemized fees and net values.
        """
        if quantity <= 0 or execution_price <= 0.0:
            return TransactionCostBreakdown(
                gross_value=0.0,
                brokerage=0.0,
                exchange_turnover_fee=0.0,
                sebi_charges=0.0,
                stamp_duty=0.0,
                stt=0.0,
                gst=0.0,
                total_cost=0.0,
                net_value=0.0,
                side=str(side),
            )

        side_str = side.value if isinstance(side, OrderSide) else str(side).upper()
        gross_value = float(quantity * execution_price)

        # 1. Brokerage (percentage with optional per-order cap)
        raw_brokerage = gross_value * self.brokerage_pct
        if self.fixed_brokerage_cap is not None and self.fixed_brokerage_cap > 0:
            brokerage = min(raw_brokerage, self.fixed_brokerage_cap)
        else:
            brokerage = raw_brokerage

        # 2. Exchange Turnover Charges (NSE)
        exchange_fee = gross_value * self.exchange_turnover_fee_pct

        # 3. SEBI Regulatory Charges
        sebi_charges = gross_value * self.sebi_charges_pct

        # 4. Stamp Duty (Applies only to BUY orders in India)
        stamp_duty = (gross_value * self.stamp_duty_pct) if side_str == "BUY" else 0.0

        # 5. Securities Transaction Tax (STT)
        stt = gross_value * self.stt_pct

        # 6. GST (18% applied strictly to Brokerage + Exchange Turnover Fee)
        gst = (brokerage + exchange_fee) * self.gst_pct

        # Total transaction cost sum (prevents double counting)
        total_cost = brokerage + exchange_fee + sebi_charges + stamp_duty + stt + gst

        # Net value: for BUY, buyer pays gross + total_cost; for SELL, seller receives gross - total_cost
        if side_str == "BUY":
            net_value = gross_value + total_cost
        else:
            net_value = max(0.0, gross_value - total_cost)

        return TransactionCostBreakdown(
            gross_value=gross_value,
            brokerage=brokerage,
            exchange_turnover_fee=exchange_fee,
            sebi_charges=sebi_charges,
            stamp_duty=stamp_duty,
            stt=stt,
            gst=gst,
            total_cost=total_cost,
            net_value=net_value,
            side=side_str,
        )

    @classmethod
    def zero_cost(cls) -> "TransactionCostModel":
        """Factory for a zero-cost theoretical model for benchmarking."""
        return cls(
            brokerage_pct=0.0,
            stt_pct=0.0,
            exchange_turnover_fee_pct=0.0,
            sebi_charges_pct=0.0,
            stamp_duty_pct=0.0,
            gst_pct=0.0,
            fixed_brokerage_cap=0.0,
        )
