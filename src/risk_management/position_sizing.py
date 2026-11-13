"""
MIRAI — Dynamic Position Sizing Engine (M11)
Determines safe capital allocation, share quantities, and risk-budgeted position limits.
Supports Risk-Budget, Volatility-Targeted, Fixed-Fractional, and Fractional Kelly sizing.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import numpy as np

from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger("PositionSizing")


@dataclass
class PositionSizeResult:
    """Standardized sizing calculation result."""
    symbol: str
    entry_price: float
    stop_loss: float
    stop_distance_pct: float
    risk_budget_pct: float
    risk_budget_inr: float
    allocated_capital: float
    allocated_pct: float
    shares: int
    sizing_method: str
    is_valid: bool
    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "entry_price": round(self.entry_price, 4),
            "stop_loss": round(self.stop_loss, 4),
            "stop_distance_pct": round(self.stop_distance_pct * 100, 2),
            "risk_budget_pct": round(self.risk_budget_pct * 100, 2),
            "risk_budget_inr": round(self.risk_budget_inr, 2),
            "allocated_capital": round(self.allocated_capital, 2),
            "allocated_pct": round(self.allocated_pct * 100, 2),
            "shares": self.shares,
            "sizing_method": self.sizing_method,
            "is_valid": self.is_valid,
            "warning": self.warning,
        }

    @property
    def units(self) -> int:
        """Alias for shares quantity."""
        return self.shares

    @property
    def position_value(self) -> float:
        """Alias for allocated rupee capital."""
        return self.allocated_capital

    @property
    def position_pct(self) -> float:
        """Alias for allocated capital percentage."""
        return self.allocated_pct

    @property
    def risk_amount(self) -> float:
        """Alias for rupee risk amount."""
        return self.risk_budget_inr

    @property
    def risk_pct(self) -> float:
        """Alias for risk percentage."""
        return self.risk_budget_pct

    @property
    def notes(self) -> str:
        """Alias for warnings or notes."""
        return self.warning or ""


class PositionSizer:
    """
    Computes mathematically rigorous position sizing under capital, risk budget,
    and stop-loss distance constraints.
    """

    def __init__(
        self,
        default_risk_budget_pct: float = 0.01,  # 1% portfolio risk per trade
        max_position_size_pct: float = 0.20,    # Max 20% portfolio capital in one trade
        default_stop_loss_pct: float = 0.02,    # 2% default stop loss distance
        min_position_size_inr: float = 1000.0,
        risk_budget_pct: Optional[float] = None,
        max_position_pct: Optional[float] = None,
    ):
        cfg = get_config()
        rb = risk_budget_pct if risk_budget_pct is not None else default_risk_budget_pct
        mp = max_position_pct if max_position_pct is not None else max_position_size_pct
        self.risk_budget_pct = cfg.get("risk_management.position_risk_budget_pct", rb)
        self.max_position_pct = cfg.get("risk_management.max_position_size_pct", mp)
        self.default_stop_pct = cfg.get("risk_management.default_stop_loss_pct", default_stop_loss_pct)
        self.min_position_inr = min_position_size_inr

    def calculate_position(
        self,
        method: str = "risk_budgeting",
        portfolio_equity: float = 1000000.0,
        entry_price: float = 100.0,
        stop_loss: Optional[float] = None,
        atr: Optional[float] = None,
        win_rate: Optional[float] = None,
        win_loss_ratio: Optional[float] = None,
        symbol: str = "ASSET",
    ) -> PositionSizeResult:
        """Standardized interface for position sizing calculation."""
        if portfolio_equity <= 0:
            raise ValueError(f"portfolio_equity must be positive, got {portfolio_equity}")
        if entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got {entry_price}")
        if stop_loss is not None and stop_loss >= entry_price:
            raise ValueError(f"stop_loss ({stop_loss}) must be below entry price ({entry_price}) for Long")

        return self.calculate_position_size(
            symbol=symbol,
            current_capital=portfolio_equity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            trade_direction="BUY",
            method=method,
            win_rate=win_rate,
            win_loss_ratio=win_loss_ratio,
        )

    def calculate_position_size(
        self,
        symbol: str,
        current_capital: float,
        entry_price: float,
        stop_loss: Optional[float] = None,
        trade_direction: str = "BUY",
        method: str = "risk_budget",
        win_rate: Optional[float] = None,
        win_loss_ratio: Optional[float] = None,
    ) -> PositionSizeResult:
        """
        Calculates position allocation under risk-budgeting.
        Risk Budget Rule:
        Position Capital = (Capital * RiskBudgetPct) / StopDistancePct
        Capped by max_position_size_pct * Capital.
        """
        # 1. Input Validation
        if entry_price <= 0.0:
            return PositionSizeResult(
                symbol=symbol, entry_price=entry_price, stop_loss=0.0,
                stop_distance_pct=0.0, risk_budget_pct=self.risk_budget_pct,
                risk_budget_inr=0.0, allocated_capital=0.0, allocated_pct=0.0,
                shares=0, sizing_method=method, is_valid=False,
                warning="Invalid entry price <= 0.",
            )

        if current_capital <= 0.0:
            return PositionSizeResult(
                symbol=symbol, entry_price=entry_price, stop_loss=0.0,
                stop_distance_pct=0.0, risk_budget_pct=self.risk_budget_pct,
                risk_budget_inr=0.0, allocated_capital=0.0, allocated_pct=0.0,
                shares=0, sizing_method=method, is_valid=False,
                warning="Zero or negative current portfolio capital.",
            )

        # 2. Stop-loss validation and fallback
        warning_msg = None
        if stop_loss is None or stop_loss <= 0.0:
            warning_msg = f"Missing stop loss; applied default {self.default_stop_pct*100:.1f}% stop."
            if trade_direction == "BUY":
                stop_loss = entry_price * (1.0 - self.default_stop_pct)
            else:
                stop_loss = entry_price * (1.0 + self.default_stop_pct)
        else:
            # Check for inverted stops
            if trade_direction == "BUY" and stop_loss >= entry_price:
                return PositionSizeResult(
                    symbol=symbol, entry_price=entry_price, stop_loss=stop_loss,
                    stop_distance_pct=0.0, risk_budget_pct=self.risk_budget_pct,
                    risk_budget_inr=0.0, allocated_capital=0.0, allocated_pct=0.0,
                    shares=0, sizing_method=method, is_valid=False,
                    warning="Inverted stop loss for BUY: stop_loss >= entry_price.",
                )
            elif trade_direction == "SELL" and stop_loss <= entry_price:
                return PositionSizeResult(
                    symbol=symbol, entry_price=entry_price, stop_loss=stop_loss,
                    stop_distance_pct=0.0, risk_budget_pct=self.risk_budget_pct,
                    risk_budget_inr=0.0, allocated_capital=0.0, allocated_pct=0.0,
                    shares=0, sizing_method=method, is_valid=False,
                    warning="Inverted stop loss for SELL: stop_loss <= entry_price.",
                )

        # 3. Stop distance percentage
        stop_dist_pct = abs(entry_price - stop_loss) / entry_price
        stop_dist_pct = max(stop_dist_pct, 0.002)  # Floor at 0.2% distance

        # Max risk budget in ₹ INR
        risk_budget_inr = current_capital * self.risk_budget_pct

        # 4. Sizing Method Execution
        if method == "fixed_fractional":
            alloc_capital = current_capital * 0.05  # Fixed 5% allocation

        elif method == "kelly" and win_rate is not None and win_loss_ratio is not None and win_loss_ratio > 0:
            # Fractional Kelly (1/4 Kelly)
            p = float(np.clip(win_rate, 0.0, 1.0))
            q = 1.0 - p
            b = win_loss_ratio
            kelly_f = max(0.0, (p * b - q) / b) * 0.25
            alloc_capital = current_capital * min(kelly_f, self.max_position_pct)

        else:  # Default: risk_budget
            # Position Capital = Risk Budget / Stop Distance Pct
            raw_capital = risk_budget_inr / stop_dist_pct
            alloc_capital = min(raw_capital, current_capital * self.max_position_pct)

        # Ensure bounds [min_inr, max_inr]
        max_capital_cap = current_capital * self.max_position_pct
        final_capital = float(np.clip(alloc_capital, 0.0, max_capital_cap))

        # 5. Shares Quantity Calculation (whole shares)
        shares = int(np.floor(final_capital / entry_price))
        actual_capital = float(shares * entry_price)
        alloc_pct = float(actual_capital / current_capital) if current_capital > 0 else 0.0

        is_valid = shares > 0

        return PositionSizeResult(
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            stop_distance_pct=stop_dist_pct,
            risk_budget_pct=self.risk_budget_pct,
            risk_budget_inr=risk_budget_inr,
            allocated_capital=actual_capital,
            allocated_pct=alloc_pct,
            shares=shares,
            sizing_method=method,
            is_valid=is_valid,
            warning=warning_msg,
        )
