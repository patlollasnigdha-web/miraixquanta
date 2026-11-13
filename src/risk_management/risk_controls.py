"""
MIRAI — Dynamic Risk Controls (M11)
Implements circuit-breaker monitors, trailing stop managers with high-water-mark tracking,
breakeven protection, and portfolio exposure limit verifiers.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger("RiskControls")


class CircuitBreakerState(str, Enum):
    """
    Operational safety states for the MIRAI trading system.
    """
    NORMAL = "NORMAL"          # Normal trading operations, standard limits
    CAUTION = "CAUTION"        # Heightened risk, scaled-down sizing (50%), defensive filters
    RESTRICTED = "RESTRICTED"  # No new long positions, only exits and risk-reducing trades allowed
    HALTED = "HALTED"          # Critical risk breached, all trading suspended, immediate safety stop


@dataclass
class TrailingStopState:
    """State container for an asset's dynamic trailing stop."""
    symbol: str
    entry_price: float
    highest_price: float
    current_stop: float
    is_active: bool
    activation_pct: float = 0.03
    distance_pct: float = 0.015
    breakeven_pct: float = 0.015


class TrailingStopManager:
    """
    Manages high-water-mark tracking and ratcheting trailing stops.
    Also incorporates breakeven protection when price reaches breakeven threshold.
    """

    def __init__(
        self,
        activation_pct: Optional[float] = None,
        distance_pct: Optional[float] = None,
        breakeven_pct: Optional[float] = None,
    ):
        cfg = get_config()
        self.activation_pct = (
            activation_pct
            if activation_pct is not None
            else cfg.get("risk_management.trailing_stop_activation", 0.03)
        )
        self.distance_pct = (
            distance_pct
            if distance_pct is not None
            else cfg.get("risk_management.trailing_stop_distance", 0.015)
        )
        self.breakeven_pct = (
            breakeven_pct
            if breakeven_pct is not None
            else cfg.get("risk_management.breakeven_pct", 0.015)
        )

    def initialize_stop(
        self,
        symbol: str,
        entry_price: float,
        initial_stop: float,
    ) -> TrailingStopState:
        """Initializes a trailing stop state for a newly entered position."""
        if entry_price <= 0:
            raise ValueError(f"Entry price must be positive, got {entry_price}")
        if initial_stop >= entry_price:
            raise ValueError(f"Initial stop ({initial_stop}) must be below entry price ({entry_price}) for Long")

        return TrailingStopState(
            symbol=symbol,
            entry_price=entry_price,
            highest_price=entry_price,
            current_stop=initial_stop,
            is_active=False,
            activation_pct=self.activation_pct,
            distance_pct=self.distance_pct,
            breakeven_pct=self.breakeven_pct,
        )

    def update_stop(
        self,
        state: TrailingStopState,
        current_price: float,
    ) -> TrailingStopState:
        """
        Ratchets the stop loss upward as current price advances.
        Trailing stops never move downward.
        """
        if current_price <= 0:
            return state

        # 1. Update high-water mark
        if current_price > state.highest_price:
            state.highest_price = current_price

        gain_from_entry = (state.highest_price - state.entry_price) / state.entry_price

        # 2. Breakeven logic: if price gained breakeven_pct, stop moves to at least entry price
        if gain_from_entry >= state.breakeven_pct:
            if state.current_stop < state.entry_price:
                state.current_stop = state.entry_price
                logger.debug(
                    "[%s] Breakeven stop triggered: stop moved to entry price %.2f",
                    state.symbol, state.entry_price
                )

        # 3. Trailing activation: if price gained activation_pct, ratcheting stop activates
        if gain_from_entry >= state.activation_pct:
            state.is_active = True
            ratchet_stop = state.highest_price * (1.0 - state.distance_pct)
            if ratchet_stop > state.current_stop:
                state.current_stop = ratchet_stop
                logger.debug(
                    "[%s] Trailing stop ratcheted to %.2f (HWM: %.2f)",
                    state.symbol, state.current_stop, state.highest_price
                )

        return state


def update_trailing_stop(
    entry_price: float,
    current_price: float,
    current_stop: float,
    highest_price: Optional[float] = None,
    activation_pct: float = 0.03,
    distance_pct: float = 0.015,
) -> Tuple[float, float, bool]:
    """
    Stateless functional utility to calculate updated trailing stop.

    Returns:
        (updated_stop, updated_highest_price, is_active)
    """
    hwm = max(highest_price or entry_price, current_price)
    gain = (hwm - entry_price) / entry_price if entry_price > 0 else 0.0
    is_active = gain >= activation_pct

    updated_stop = current_stop
    if is_active:
        trail_level = hwm * (1.0 - distance_pct)
        updated_stop = max(current_stop, trail_level)

    return updated_stop, hwm, is_active


class CircuitBreakerMonitor:
    """
    Tracks portfolio performance against safety thresholds to transition
    between NORMAL, CAUTION, RESTRICTED, and HALTED states.
    """

    def __init__(
        self,
        max_portfolio_drawdown: Optional[float] = None,
        daily_loss_limit: Optional[float] = None,
        volatility_shock_multiplier: float = 2.5,
    ):
        cfg = get_config()
        self.max_portfolio_drawdown = (
            max_portfolio_drawdown
            if max_portfolio_drawdown is not None
            else cfg.get("risk_management.max_portfolio_drawdown", 0.15)
        )
        self.daily_loss_limit = (
            daily_loss_limit
            if daily_loss_limit is not None
            else cfg.get("risk_management.daily_loss_limit", 0.03)
        )
        self.volatility_shock_multiplier = volatility_shock_multiplier

    def evaluate_state(
        self,
        current_equity: float,
        daily_start_equity: float,
        peak_equity: float,
        current_volatility: Optional[float] = None,
        baseline_volatility: Optional[float] = None,
    ) -> Tuple[CircuitBreakerState, str]:
        """
        Evaluates current portfolio state and returns operational safety state and rationale.
        """
        if daily_start_equity <= 0 or peak_equity <= 0:
            return CircuitBreakerState.HALTED, "Invalid or zero equity baseline"

        # Calculate metrics
        daily_loss_pct = max(0.0, (daily_start_equity - current_equity) / daily_start_equity)
        drawdown_pct = max(0.0, (peak_equity - current_equity) / peak_equity)

        # 1. HALTED checks
        if drawdown_pct >= self.max_portfolio_drawdown:
            msg = (
                f"Portfolio drawdown ({drawdown_pct:.1%}) breached maximum threshold "
                f"({self.max_portfolio_drawdown:.1%}). Trading HALTED."
            )
            logger.critical(msg)
            return CircuitBreakerState.HALTED, msg

        if daily_loss_pct >= self.daily_loss_limit * 1.5:
            msg = (
                f"Severe daily loss ({daily_loss_pct:.1%}) breached emergency halt limit "
                f"({self.daily_loss_limit * 1.5:.1%}). Trading HALTED."
            )
            logger.critical(msg)
            return CircuitBreakerState.HALTED, msg

        # 2. RESTRICTED checks
        if daily_loss_pct >= self.daily_loss_limit:
            msg = (
                f"Daily loss limit ({daily_loss_pct:.1%}) reached threshold "
                f"({self.daily_loss_limit:.1%}). Trading RESTRICTED to risk-reduction only."
            )
            logger.warning(msg)
            return CircuitBreakerState.RESTRICTED, msg

        if drawdown_pct >= self.max_portfolio_drawdown * 0.75:
            msg = (
                f"Elevated portfolio drawdown ({drawdown_pct:.1%}) approaching maximum limit. "
                f"Trading RESTRICTED to risk-reduction only."
            )
            logger.warning(msg)
            return CircuitBreakerState.RESTRICTED, msg

        # 3. CAUTION checks
        if daily_loss_pct >= self.daily_loss_limit * 0.60:
            msg = f"Moderate daily loss ({daily_loss_pct:.1%}). Trading in CAUTION state."
            return CircuitBreakerState.CAUTION, msg

        if drawdown_pct >= self.max_portfolio_drawdown * 0.50:
            msg = f"Moderate portfolio drawdown ({drawdown_pct:.1%}). Trading in CAUTION state."
            return CircuitBreakerState.CAUTION, msg

        if current_volatility and baseline_volatility and baseline_volatility > 0:
            vol_ratio = current_volatility / baseline_volatility
            if vol_ratio >= self.volatility_shock_multiplier:
                msg = (
                    f"Volatility shock detected (current {current_volatility:.2%} vs "
                    f"baseline {baseline_volatility:.2%}, ratio {vol_ratio:.1f}x). "
                    f"Trading in CAUTION state."
                )
                return CircuitBreakerState.CAUTION, msg

        return CircuitBreakerState.NORMAL, "Normal trading conditions"


class ExposureLimitValidator:
    """
    Validates single-asset, total portfolio exposure, and minimum cash reserve constraints.
    """

    def __init__(
        self,
        max_position_size_pct: Optional[float] = None,
        max_total_exposure: Optional[float] = None,
        cash_reserve: Optional[float] = None,
    ):
        cfg = get_config()
        self.max_position_size_pct = (
            max_position_size_pct
            if max_position_size_pct is not None
            else cfg.get("risk_management.max_position_size_pct", 0.20)
        )
        self.max_total_exposure = (
            max_total_exposure
            if max_total_exposure is not None
            else cfg.get("portfolio.max_total_exposure", 0.95)
        )
        self.cash_reserve = (
            cash_reserve
            if cash_reserve is not None
            else cfg.get("portfolio.cash_reserve", 0.05)
        )

    def validate_trade_exposure(
        self,
        portfolio_equity: float,
        current_asset_exposure: float,
        current_total_exposure: float,
        proposed_trade_value: float,
        symbol: str,
    ) -> Tuple[bool, List[str]]:
        """
        Validates if adding proposed_trade_value violates position or portfolio limits.

        Returns:
            (is_valid, violation_reasons)
        """
        violations = []

        if portfolio_equity <= 0:
            violations.append("Portfolio equity is zero or negative.")
            return False, violations

        max_asset_capital = self.max_position_size_pct * portfolio_equity
        new_asset_exposure = current_asset_exposure + proposed_trade_value

        if new_asset_exposure > max_asset_capital + 1e-4:
            excess = new_asset_exposure - max_asset_capital
            violations.append(
                f"Proposed trade for {symbol} ({proposed_trade_value:,.2f}) raises asset exposure "
                f"to {new_asset_exposure:,.2f} ({new_asset_exposure / portfolio_equity:.1%}), "
                f"exceeding max single-asset limit {self.max_position_size_pct:.1%} by {excess:,.2f}."
            )

        max_allowed_total = min(self.max_total_exposure, 1.0 - self.cash_reserve) * portfolio_equity
        new_total_exposure = current_total_exposure + proposed_trade_value

        if new_total_exposure > max_allowed_total + 1e-4:
            excess = new_total_exposure - max_allowed_total
            violations.append(
                f"Proposed trade raises total portfolio exposure to {new_total_exposure:,.2f} "
                f"({new_total_exposure / portfolio_equity:.1%}), exceeding max portfolio exposure "
                f"limit of {max_allowed_total:,.2f} (Cash reserve required: {self.cash_reserve:.1%})."
            )

        return len(violations) == 0, violations
