"""
MIRAI — Dynamic Risk Management Engine (M11)
Coordinates portfolio risk monitoring, dynamic position sizing, circuit breakers,
trailing stop ratcheting, exposure constraint validation, and integration
with M09 Investment Decision Engine.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.decision.decision_schemas import (
    DecisionVerdict,
    DisplayLabel,
    RiskStatus,
    InvestmentDecision,
)
from src.risk_management.risk_controls import (
    CircuitBreakerState,
    CircuitBreakerMonitor,
    TrailingStopManager,
    TrailingStopState,
    ExposureLimitValidator,
)
from src.risk_management.position_sizing import (
    PositionSizer,
    PositionSizeResult,
)

logger = get_logger("RiskEngine")


@dataclass
class RiskEvaluationResult:
    """Structured result returned by trade risk evaluation."""
    symbol: str
    is_approved: bool
    risk_status: str  # RiskStatus.RISK_APPROVED or RiskStatus.RISK_BLOCKED
    circuit_breaker_state: CircuitBreakerState
    allocated_capital: float
    recommended_position: Optional[PositionSizeResult]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    rejection_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "is_approved": self.is_approved,
            "risk_status": self.risk_status,
            "circuit_breaker_state": self.circuit_breaker_state.value,
            "allocated_capital": round(self.allocated_capital, 2),
            "recommended_units": self.recommended_position.units if self.recommended_position else 0.0,
            "stop_loss": round(self.stop_loss, 4) if self.stop_loss is not None else None,
            "take_profit": round(self.take_profit, 4) if self.take_profit is not None else None,
            "rejection_reasons": self.rejection_reasons,
            "warnings": self.warnings,
        }


class RiskManagementEngine:
    """
    Central risk management engine for MIRAI.
    Monitors portfolio state, enforces risk-budgeting position sizing,
    executes circuit-breaker transitions, and approves or blocks M09 investment decisions.
    """

    def __init__(
        self,
        initial_capital: Optional[float] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        cfg = get_config()
        self.initial_capital = (
            initial_capital
            if initial_capital is not None
            else cfg.get("backtesting.initial_capital", 1_000_000.0)
        )
        self.portfolio_equity = self.initial_capital
        self.peak_equity = self.initial_capital
        self.daily_start_equity = self.initial_capital
        self.current_cash = self.initial_capital

        # Active positions: symbol -> dict(units, entry_price, current_price, market_value, stop_loss, trailing_stop_state)
        self.active_positions: Dict[str, Dict[str, Any]] = {}

        # Sub-components
        self.circuit_monitor = CircuitBreakerMonitor()
        self.position_sizer = PositionSizer()
        self.exposure_validator = ExposureLimitValidator()
        self.trailing_manager = TrailingStopManager()

        self.circuit_breaker_state = CircuitBreakerState.NORMAL
        self.circuit_breaker_reason = "Initial normal trading conditions"

    @property
    def max_drawdown_pct(self) -> float:
        return self.circuit_monitor.max_portfolio_drawdown * 100.0

    @property
    def max_position_size_pct(self) -> float:
        return self.exposure_validator.max_position_size_pct * 100.0

    @property
    def cash_reserve_required_pct(self) -> float:
        return self.exposure_validator.cash_reserve * 100.0

    def reset_daily_equity(self, starting_equity: Optional[float] = None) -> None:
        """Resets the daily starting equity baseline (e.g. at trading session open)."""
        self.daily_start_equity = starting_equity if starting_equity is not None else self.portfolio_equity
        logger.info("Daily starting equity baseline set to %.2f", self.daily_start_equity)

    def update_portfolio_state(
        self,
        current_prices: Optional[Dict[str, float]] = None,
        current_volatility: Optional[float] = None,
        baseline_volatility: Optional[float] = None,
        total_equity: Optional[float] = None,
    ) -> CircuitBreakerState:
        """
        Updates market values of all open positions, updates total portfolio equity,
        ratchets trailing stops, and evaluates the circuit breaker state.
        """
        if total_equity is not None:
            self.portfolio_equity = total_equity
            self.current_cash = min(self.current_cash, total_equity)
        else:
            current_prices = current_prices or {}
            invested_capital = 0.0

            for sym, pos in self.active_positions.items():
                if sym in current_prices:
                    price = current_prices[sym]
                    pos["current_price"] = price
                    pos["market_value"] = pos["units"] * price

                    # Ratchet trailing stop if active
                    if pos.get("trailing_stop_state"):
                        pos["trailing_stop_state"] = self.trailing_manager.update_stop(
                            pos["trailing_stop_state"], price
                        )
                        pos["stop_loss"] = pos["trailing_stop_state"].current_stop

                invested_capital += pos.get("market_value", 0.0)

            if self.active_positions:
                self.portfolio_equity = self.current_cash + invested_capital

        if self.portfolio_equity > self.peak_equity:
            self.peak_equity = self.portfolio_equity

        # Evaluate circuit breaker state
        self.circuit_breaker_state, self.circuit_breaker_reason = self.circuit_monitor.evaluate_state(
            current_equity=self.portfolio_equity,
            daily_start_equity=self.daily_start_equity,
            peak_equity=self.peak_equity,
            current_volatility=current_volatility,
            baseline_volatility=baseline_volatility,
        )

        return self.circuit_breaker_state

    def evaluate_trade_approval(
        self,
        decision: InvestmentDecision,
        current_price: float,
        current_capital: Optional[float] = None,
        atr: Optional[float] = None,
        win_rate: Optional[float] = None,
        win_loss_ratio: Optional[float] = None,
        sizing_method: str = "risk_budgeting",
    ) -> RiskEvaluationResult:
        """
        Evaluates an M09 InvestmentDecision against active risk constraints,
        circuit-breaker states, and portfolio limits.
        """
        rejection_reasons: List[str] = []
        warnings: List[str] = []
        symbol = decision.symbol
        capital = current_capital if current_capital is not None else self.portfolio_equity

        # 1. Circuit Breaker Checks
        if self.circuit_breaker_state == CircuitBreakerState.HALTED:
            rejection_reasons.append(
                f"Trading HALTED by circuit breaker: {self.circuit_breaker_reason}"
            )
            return RiskEvaluationResult(
                symbol=symbol,
                is_approved=False,
                risk_status=RiskStatus.RISK_BLOCKED,
                circuit_breaker_state=self.circuit_breaker_state,
                allocated_capital=0.0,
                recommended_position=None,
                stop_loss=None,
                take_profit=None,
                rejection_reasons=rejection_reasons,
                warnings=warnings,
            )

        # For restricted state: only non-entry or exit actions are permitted
        if self.circuit_breaker_state == CircuitBreakerState.RESTRICTED:
            if decision.verdict == DecisionVerdict.YES or decision.action_type in ["ENTRY_LONG", "BUY"]:
                rejection_reasons.append(
                    f"New long entries RESTRICTED by circuit breaker: {self.circuit_breaker_reason}"
                )
                return RiskEvaluationResult(
                    symbol=symbol,
                    is_approved=False,
                    risk_status=RiskStatus.RISK_BLOCKED,
                    circuit_breaker_state=self.circuit_breaker_state,
                    allocated_capital=0.0,
                    recommended_position=None,
                    stop_loss=None,
                    take_profit=None,
                    rejection_reasons=rejection_reasons,
                    warnings=warnings,
                )

        # 2. Determine Stop Loss level
        stop_loss = decision.suggested_stop_loss
        if stop_loss is None or stop_loss <= 0:
            if atr is not None and atr > 0:
                stop_loss = current_price - (2.0 * atr)
                warnings.append(f"Derived ATR stop-loss: {stop_loss:.2f}")
            else:
                cfg = get_config()
                def_pct = cfg.get("risk_management.default_stop_loss_pct", 0.02)
                stop_loss = current_price * (1.0 - def_pct)
                warnings.append(f"Derived default {def_pct:.1%} stop-loss: {stop_loss:.2f}")

        # Check for inverted or invalid stop loss for Long trade
        if stop_loss >= current_price:
            rejection_reasons.append(
                f"Inverted stop loss: stop ({stop_loss:.2f}) must be strictly below entry price ({current_price:.2f})."
            )
            return RiskEvaluationResult(
                symbol=symbol,
                is_approved=False,
                risk_status=RiskStatus.RISK_BLOCKED,
                circuit_breaker_state=self.circuit_breaker_state,
                allocated_capital=0.0,
                recommended_position=None,
                stop_loss=stop_loss,
                take_profit=decision.suggested_take_profit,
                rejection_reasons=rejection_reasons,
                warnings=warnings,
            )

        # 3. Position Sizing
        try:
            position_size = self.position_sizer.calculate_position(
                method=sizing_method,
                portfolio_equity=capital,
                entry_price=current_price,
                stop_loss=stop_loss,
                atr=atr,
                win_rate=win_rate,
                win_loss_ratio=win_loss_ratio,
            )
        except Exception as e:
            rejection_reasons.append(f"Position sizing calculation failed: {str(e)}")
            return RiskEvaluationResult(
                symbol=symbol,
                is_approved=False,
                risk_status=RiskStatus.RISK_BLOCKED,
                circuit_breaker_state=self.circuit_breaker_state,
                allocated_capital=0.0,
                recommended_position=None,
                stop_loss=stop_loss,
                take_profit=decision.suggested_take_profit,
                rejection_reasons=rejection_reasons,
                warnings=warnings,
            )

        # In CAUTION state: scale down position size by 50%
        if self.circuit_breaker_state == CircuitBreakerState.CAUTION:
            scaled_units = int(position_size.units * 0.5)
            scaled_val = scaled_units * current_price
            scaled_risk = scaled_units * (current_price - stop_loss)
            position_size = PositionSizeResult(
                symbol=position_size.symbol,
                units=scaled_units,
                position_value=scaled_val,
                position_pct=scaled_val / capital if capital > 0 else 0.0,
                risk_amount=scaled_risk,
                risk_pct=scaled_risk / capital if capital > 0 else 0.0,
                method=position_size.method,
                notes=position_size.notes + " (Scaled 50% under CAUTION circuit state)",
            )
            warnings.append("Position scaled down 50% due to CAUTION circuit breaker state.")

        if position_size.units <= 0:
            rejection_reasons.append("Calculated position size is 0 units under current risk constraints.")
            return RiskEvaluationResult(
                symbol=symbol,
                is_approved=False,
                risk_status=RiskStatus.RISK_BLOCKED,
                circuit_breaker_state=self.circuit_breaker_state,
                allocated_capital=0.0,
                recommended_position=position_size,
                stop_loss=stop_loss,
                take_profit=decision.suggested_take_profit,
                rejection_reasons=rejection_reasons,
                warnings=warnings,
            )

        # 4. Exposure Limit Validation
        current_sym_val = self.active_positions.get(symbol, {}).get("market_value", 0.0)
        current_total_val = sum(pos.get("market_value", 0.0) for pos in self.active_positions.values())

        is_exposure_valid, exposure_violations = self.exposure_validator.validate_trade_exposure(
            portfolio_equity=capital,
            current_asset_exposure=current_sym_val,
            current_total_exposure=current_total_val,
            proposed_trade_value=position_size.position_value,
            symbol=symbol,
        )

        if not is_exposure_valid:
            rejection_reasons.extend(exposure_violations)
            return RiskEvaluationResult(
                symbol=symbol,
                is_approved=False,
                risk_status=RiskStatus.RISK_BLOCKED,
                circuit_breaker_state=self.circuit_breaker_state,
                allocated_capital=0.0,
                recommended_position=position_size,
                stop_loss=stop_loss,
                take_profit=decision.suggested_take_profit,
                rejection_reasons=rejection_reasons,
                warnings=warnings,
            )

        # All checks passed!
        return RiskEvaluationResult(
            symbol=symbol,
            is_approved=True,
            risk_status=RiskStatus.RISK_APPROVED,
            circuit_breaker_state=self.circuit_breaker_state,
            allocated_capital=position_size.position_value,
            recommended_position=position_size,
            stop_loss=stop_loss,
            take_profit=decision.suggested_take_profit,
            rejection_reasons=[],
            warnings=warnings,
        )

    def apply_risk_to_decision(
        self,
        decision: InvestmentDecision,
        current_price: float,
        current_capital: Optional[float] = None,
        atr: Optional[float] = None,
        win_rate: Optional[float] = None,
        win_loss_ratio: Optional[float] = None,
        sizing_method: str = "risk_budgeting",
    ) -> Tuple[InvestmentDecision, RiskEvaluationResult]:
        """
        Validates an InvestmentDecision through M11 risk rules, returning an updated
        InvestmentDecision with risk_status transitioned to RISK_APPROVED or RISK_BLOCKED,
        and blocking YES decisions when risk limits are breached.
        """
        eval_result = self.evaluate_trade_approval(
            decision=decision,
            current_price=current_price,
            current_capital=current_capital,
            atr=atr,
            win_rate=win_rate,
            win_loss_ratio=win_loss_ratio,
            sizing_method=sizing_method,
        )

        decision.risk_status = eval_result.risk_status
        if eval_result.stop_loss is not None:
            decision.suggested_stop_loss = eval_result.stop_loss

        if not eval_result.is_approved:
            # Risk limit breached: block YES verdict
            if decision.verdict == DecisionVerdict.YES:
                decision.verdict = DecisionVerdict.NO
                decision.display_label = DisplayLabel.NO_ACTION
                decision.action_type = "OBSERVE"

            for reason in eval_result.rejection_reasons:
                decision.explanation.conflicting_signals.append(f"RISK VETO: {reason}")
            decision.explanation.risk_notes = f"RISK BLOCKED: {'; '.join(eval_result.rejection_reasons)}"
            logger.warning(
                "Decision for %s BLOCKED by Risk Engine: %s",
                decision.symbol, eval_result.rejection_reasons
            )
        else:
            # Risk approved
            sizing_info = ""
            if eval_result.recommended_position:
                sizing_info = (
                    f"Approved {eval_result.recommended_position.units} units "
                    f"({eval_result.recommended_position.position_value:,.2f} INR, "
                    f"{eval_result.recommended_position.position_pct:.1%} capital). "
                    f"Stop: {eval_result.stop_loss:.2f}."
                )
            decision.explanation.risk_notes = (
                f"RISK APPROVED under {eval_result.circuit_breaker_state.value} state. {sizing_info}"
            )
            logger.info("Decision for %s APPROVED by Risk Engine. %s", decision.symbol, sizing_info)

        return decision, eval_result
