"""
Unit and Integration Tests for Dynamic Risk Management Engine (M11)
and M09 Investment Decision Integration.
Tests risk metrics, position sizing, circuit-breaker transitions,
trailing stop ratcheting, exposure limits, and decision risk approval/blocking.
"""

import numpy as np
import pandas as pd
import pytest

from src.risk_management.risk_metrics import (
    RiskMetrics,
    compute_drawdown_series,
    compute_historical_var,
    compute_historical_cvar,
    compute_parametric_var,
    compute_parametric_cvar,
    compute_sharpe_ratio,
    compute_sortino_ratio,
    compute_calmar_ratio,
    compute_risk_summary,
)
from src.risk_management.position_sizing import PositionSizer, PositionSizeResult
from src.risk_management.risk_controls import (
    CircuitBreakerState,
    CircuitBreakerMonitor,
    TrailingStopManager,
    update_trailing_stop,
    ExposureLimitValidator,
)
from src.risk_management.risk_engine import RiskManagementEngine, RiskEvaluationResult
from src.decision.decision_schemas import (
    DecisionInput,
    DecisionVerdict,
    DisplayLabel,
    RiskStatus,
    InvestmentDecision,
    DecisionExplanation,
)
from src.decision.decision_engine import InvestmentDecisionEngine
from src.strategies.base_strategy import StrategySignal, SignalAction


@pytest.fixture
def sample_daily_returns():
    """Generates 250 daily returns with positive drift and 15% annual vol."""
    np.random.seed(42)
    # mean daily ~ 0.05%, daily std ~ 0.95% (approx 15% annualized)
    returns = np.random.normal(0.0005, 0.0095, 250)
    return pd.Series(returns)


# =========================================================================
# 1. RISK METRICS TESTS
# =========================================================================

def test_risk_metrics_volatility(sample_daily_returns):
    """Tests realized volatility calculation."""
    vol = RiskMetrics.realized_volatility(sample_daily_returns)
    assert vol == pytest.approx(0.15, abs=0.03)

    # Empty or zero returns
    assert RiskMetrics.realized_volatility(pd.Series([])) == 0.0
    assert RiskMetrics.realized_volatility(pd.Series([0.0, 0.0, 0.0])) == 0.0


def test_drawdown_series():
    """Tests drawdown series, max drawdown, and current drawdown."""
    # Prices: 100 -> 120 (peak) -> 90 (dd = (90-120)/120 = -25%) -> 100
    prices = pd.Series([100.0, 110.0, 120.0, 105.0, 90.0, 100.0])
    dd_series, max_dd, cur_dd = compute_drawdown_series(prices)

    assert max_dd == pytest.approx(-0.25, abs=1e-4)
    assert cur_dd == pytest.approx((100.0 - 120.0) / 120.0, abs=1e-4)
    assert dd_series.iloc[2] == 0.0 # At peak
    assert dd_series.iloc[4] == pytest.approx(-0.25, abs=1e-4)


def test_var_and_cvar(sample_daily_returns):
    """Tests historical and parametric VaR and CVaR."""
    hist_var = compute_historical_var(sample_daily_returns, confidence=0.95)
    hist_cvar = compute_historical_cvar(sample_daily_returns, confidence=0.95)
    param_var = compute_parametric_var(sample_daily_returns, confidence=0.95)
    param_cvar = compute_parametric_cvar(sample_daily_returns, confidence=0.95)

    assert hist_var > 0.0
    assert hist_cvar >= hist_var # CVaR is always >= VaR
    assert param_var > 0.0
    assert param_cvar >= param_var


def test_risk_adjusted_ratios(sample_daily_returns):
    """Tests Sharpe, Sortino, and Calmar ratios."""
    sharpe = compute_sharpe_ratio(sample_daily_returns, risk_free_rate=0.065)
    sortino = compute_sortino_ratio(sample_daily_returns, risk_free_rate=0.065)
    calmar = compute_calmar_ratio(sample_daily_returns, max_drawdown=0.10)

    assert isinstance(sharpe, float)
    assert isinstance(sortino, float)
    assert isinstance(calmar, float)

    # Full summary dictionary
    summary = compute_risk_summary(sample_daily_returns, max_drawdown=0.12, current_drawdown=0.04)
    assert "realized_volatility" in summary
    assert "max_drawdown" in summary
    assert "historical_var_95" in summary
    assert "sharpe_ratio" in summary


# =========================================================================
# 2. POSITION SIZING TESTS
# =========================================================================

def test_position_sizing_risk_budgeting():
    """Tests risk-budgeting position sizing."""
    sizer = PositionSizer(risk_budget_pct=0.01, max_position_size_pct=0.20)
    # Capital = 1,000,000; Risk budget 1% = 10,000
    # Entry = 100, Stop = 95 -> Stop distance = 5.0
    # Raw units = 10,000 / 5 = 2,000 units
    # Position value = 2,000 * 100 = 200,000 (20% of capital, exactly at max position size)
    res = sizer.calculate_position(
        method="risk_budgeting",
        portfolio_equity=1_000_000.0,
        entry_price=100.0,
        stop_loss=95.0,
    )
    assert res.units == 2000
    assert res.position_value == 200_000.0
    assert res.risk_amount == 10_000.0

    # With tighter stop (e.g. 98 -> distance 2.0 -> raw units 5,000 -> 500,000 val > 20% cap)
    # Capped at 200,000 val -> 2,000 units
    res_capped = sizer.calculate_position(
        method="risk_budgeting",
        portfolio_equity=1_000_000.0,
        entry_price=100.0,
        stop_loss=98.0,
    )
    assert res_capped.position_value <= 200_000.0 + 1e-4
    assert res_capped.units == 2000


def test_position_sizing_invalid_inputs():
    """Tests position sizing validation against invalid prices and stop distances."""
    sizer = PositionSizer()
    with pytest.raises(ValueError, match="must be positive"):
        sizer.calculate_position("risk_budgeting", portfolio_equity=-1000, entry_price=100, stop_loss=95)

    with pytest.raises(ValueError, match="must be below entry price"):
        sizer.calculate_position("risk_budgeting", portfolio_equity=100000, entry_price=100, stop_loss=105)


# =========================================================================
# 3. RISK CONTROLS & CIRCUIT BREAKER TESTS
# =========================================================================

def test_trailing_stop_manager():
    """Tests trailing stop ratcheting and breakeven protection."""
    manager = TrailingStopManager(activation_pct=0.03, distance_pct=0.015, breakeven_pct=0.015)
    # Entry: 100, Initial Stop: 97
    state = manager.initialize_stop(symbol="TCS", entry_price=100.0, initial_stop=97.0)
    assert not state.is_active
    assert state.current_stop == 97.0

    # Price moves to 101.8 (+1.8% gain >= 1.5% breakeven)
    state = manager.update_stop(state, current_price=101.8)
    assert state.current_stop == pytest.approx(100.0) # Moved to breakeven!

    # Price moves to 105.0 (+5% gain >= 3.0% activation)
    state = manager.update_stop(state, current_price=105.0)
    assert state.is_active
    expected_stop = 105.0 * (1.0 - 0.015) # 103.425
    assert state.current_stop == pytest.approx(expected_stop)

    # Price pulls back to 104.0 -> Stop MUST NOT drop
    state = manager.update_stop(state, current_price=104.0)
    assert state.current_stop == pytest.approx(expected_stop)


def test_circuit_breaker_transitions():
    """Tests circuit-breaker transitions across NORMAL, CAUTION, RESTRICTED, and HALTED."""
    monitor = CircuitBreakerMonitor(max_portfolio_drawdown=0.15, daily_loss_limit=0.03)

    # 1. NORMAL state
    state, msg = monitor.evaluate_state(current_equity=1_000_000, daily_start_equity=1_000_000, peak_equity=1_000_000)
    assert state == CircuitBreakerState.NORMAL

    # 2. CAUTION state (daily loss 2.0% >= 1.8%)
    state, msg = monitor.evaluate_state(current_equity=980_000, daily_start_equity=1_000_000, peak_equity=1_000_000)
    assert state == CircuitBreakerState.CAUTION

    # 3. RESTRICTED state (daily loss 3.2% >= 3.0%)
    state, msg = monitor.evaluate_state(current_equity=968_000, daily_start_equity=1_000_000, peak_equity=1_000_000)
    assert state == CircuitBreakerState.RESTRICTED

    # 4. HALTED state (drawdown 16% >= 15%)
    state, msg = monitor.evaluate_state(current_equity=840_000, daily_start_equity=1_000_000, peak_equity=1_000_000)
    assert state == CircuitBreakerState.HALTED


def test_exposure_limit_validator():
    """Tests single-asset and total exposure limit checks."""
    validator = ExposureLimitValidator(max_position_size_pct=0.20, max_total_exposure=0.95, cash_reserve=0.05)

    # Valid trade
    valid, violations = validator.validate_trade_exposure(
        portfolio_equity=1_000_000,
        current_asset_exposure=50_000,
        current_total_exposure=400_000,
        proposed_trade_value=100_000,
        symbol="TCS",
    )
    assert valid
    assert len(violations) == 0

    # Violates single-asset limit (current 150k + proposed 100k = 250k > 200k)
    valid, violations = validator.validate_trade_exposure(
        portfolio_equity=1_000_000,
        current_asset_exposure=150_000,
        current_total_exposure=400_000,
        proposed_trade_value=100_000,
        symbol="TCS",
    )
    assert not valid
    assert any("exceeding max single-asset limit" in v for v in violations)


# =========================================================================
# 4. RISK MANAGEMENT ENGINE & M09 DECISION INTEGRATION TESTS
# =========================================================================

def test_risk_engine_trade_approval_flow():
    """Tests approval flow of M09 InvestmentDecision under normal conditions."""
    engine = RiskManagementEngine(initial_capital=1_000_000.0)

    decision = InvestmentDecision(
        symbol="TCS",
        pipeline_id="pipeline_b_nifty",
        timestamp=pd.Timestamp("2026-03-30"),
        verdict=DecisionVerdict.YES,
        display_label=DisplayLabel.BUY,
        action_type="ENTRY_LONG",
        composite_score=75.0,
        confidence=0.80,
        investment_horizon="1d",
        entry_reference_price=3500.0,
        suggested_stop_loss=3430.0, # 2% stop
        suggested_take_profit=3640.0,
        factor_contributions={},
        factor_scores={},
        risk_status=RiskStatus.RISK_PENDING,
        explanation=DecisionExplanation(verdict_rationale="Bullish confirmation"),
    )

    eval_result = engine.evaluate_trade_approval(decision=decision, current_price=3500.0)
    assert eval_result.is_approved
    assert eval_result.risk_status == RiskStatus.RISK_APPROVED
    assert eval_result.recommended_position is not None
    assert eval_result.recommended_position.units > 0

    # Apply risk to decision
    updated_dec, res = engine.apply_risk_to_decision(decision=decision, current_price=3500.0)
    assert updated_dec.risk_status == RiskStatus.RISK_APPROVED
    assert updated_dec.verdict == DecisionVerdict.YES
    assert "RISK APPROVED" in updated_dec.explanation.risk_notes


def test_risk_engine_blocks_decision_on_halted_circuit():
    """Tests that a HALTED circuit breaker immediately blocks YES decisions."""
    engine = RiskManagementEngine(initial_capital=1_000_000.0)
    # Simulate severe drawdown
    engine.peak_equity = 1_000_000.0
    engine.update_portfolio_state(total_equity=800_000.0)
    assert engine.circuit_breaker_state == CircuitBreakerState.HALTED

    decision = InvestmentDecision(
        symbol="INFY",
        pipeline_id="pipeline_b_nifty",
        timestamp=pd.Timestamp("2026-03-30"),
        verdict=DecisionVerdict.YES,
        display_label=DisplayLabel.BUY,
        action_type="ENTRY_LONG",
        composite_score=80.0,
        confidence=0.85,
        investment_horizon="1d",
        entry_reference_price=1600.0,
        suggested_stop_loss=1560.0,
        suggested_take_profit=1680.0,
        factor_contributions={},
        factor_scores={},
        risk_status=RiskStatus.RISK_PENDING,
        explanation=DecisionExplanation(verdict_rationale="Strong technicals"),
    )

    updated_dec, res = engine.apply_risk_to_decision(decision=decision, current_price=1600.0)
    assert not res.is_approved
    assert updated_dec.risk_status == RiskStatus.RISK_BLOCKED
    # YES verdict must be flipped to NO
    assert updated_dec.verdict == DecisionVerdict.NO
    assert updated_dec.display_label == DisplayLabel.NO_ACTION
    assert any("Trading HALTED by circuit breaker" in c for c in updated_dec.explanation.conflicting_signals)


def test_risk_engine_blocks_inverted_stop_loss():
    """Tests rejection when stop loss is inverted (>= entry price for Long)."""
    engine = RiskManagementEngine(initial_capital=1_000_000.0)

    decision = InvestmentDecision(
        symbol="RELIANCE",
        pipeline_id="pipeline_b_nifty",
        timestamp=pd.Timestamp("2026-03-30"),
        verdict=DecisionVerdict.YES,
        display_label=DisplayLabel.BUY,
        action_type="ENTRY_LONG",
        composite_score=72.0,
        confidence=0.75,
        investment_horizon="1d",
        entry_reference_price=2500.0,
        suggested_stop_loss=2600.0, # INVERTED!
        suggested_take_profit=2700.0,
        factor_contributions={},
        factor_scores={},
        risk_status=RiskStatus.RISK_PENDING,
        explanation=DecisionExplanation(verdict_rationale="Bullish signal"),
    )

    updated_dec, res = engine.apply_risk_to_decision(decision=decision, current_price=2500.0)
    assert not res.is_approved
    assert updated_dec.risk_status == RiskStatus.RISK_BLOCKED
    assert updated_dec.verdict == DecisionVerdict.NO
    assert any("Inverted stop loss" in c for c in updated_dec.explanation.conflicting_signals)


def test_decision_engine_with_risk_integration():
    """Tests end-to-end integration via InvestmentDecisionEngine.make_decision_with_risk()."""
    dec_engine = InvestmentDecisionEngine()
    risk_engine = RiskManagementEngine(initial_capital=1_000_000.0)

    inp = DecisionInput(
        symbol="TCS",
        pipeline_id="pipeline_b_nifty",
        timestamp=pd.Timestamp("2026-03-30"),
        current_price=3500.0,
        strategy_signal=StrategySignal(
            symbol="TCS",
            pipeline_id="pipeline_b_nifty",
            strategy_name="MomentumBreakout",
            strategy_version="1.0",
            signal=SignalAction.BUY,
            signal_strength=0.85,
            prediction_horizon="1d",
            timestamp=pd.Timestamp("2026-03-30"),
            entry_reference_price=3500.0,
            suggested_stop_loss=3430.0,
            suggested_take_profit=3640.0,
        ),
    )

    decision = dec_engine.make_decision_with_risk(inp=inp, risk_engine=risk_engine)
    assert decision.risk_status in [RiskStatus.RISK_APPROVED, RiskStatus.RISK_BLOCKED]
    assert decision.risk_status != RiskStatus.RISK_PENDING
