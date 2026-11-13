"""
MIRAI — Unit Tests for Adaptive Trading Strategies (M08)
"""

import numpy as np
import pandas as pd
import pytest

from src.intelligence.regime_detection import MarketRegime
from src.strategies.base_strategy import StrategySignal, SignalAction
from src.strategies.momentum_strategy import MomentumStrategy
from src.strategies.mean_reversion_strategy import MeanReversionStrategy
from src.strategies.breakout_strategy import BreakoutStrategy
from src.strategies.fi2010_strategy import FI2010MicrostructureStrategy
from src.strategies.strategy_selector import AdaptiveStrategySelector, StrategySelectionResult
from src.strategies.adaptive_strategy_engine import AdaptiveStrategyEngine


def _create_synthetic_ohlcv(
    n_bars: int = 100,
    trend: float = 0.002,
    vol: float = 0.01,
    start_price: float = 1000.0,
    start_date: str = "2023-01-01",
) -> pd.DataFrame:
    """Generates synthetic deterministic OHLCV series."""
    np.random.seed(42)
    dates = pd.date_range(start_date, periods=n_bars, freq="D")
    daily_rets = np.random.normal(loc=trend, scale=vol, size=n_bars)
    prices = start_price * np.exp(np.cumsum(daily_rets))

    highs = prices * (1.0 + np.abs(np.random.normal(0, 0.005, size=n_bars)))
    lows = prices * (1.0 - np.abs(np.random.normal(0, 0.005, size=n_bars)))
    opens = (highs + lows) / 2.0
    volumes = np.random.uniform(500000, 1000000, size=n_bars)

    return pd.DataFrame({
        "timestamp": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": volumes,
    })


def test_momentum_strategy_signal_generation():
    """Verify MomentumStrategy emits BUY on strong bullish trend and computes stop loss/target."""
    df_bull = _create_synthetic_ohlcv(n_bars=80, trend=0.005, vol=0.006)
    strat = MomentumStrategy(fast_window=10, slow_window=40)

    sig = strat.generate_signal(df_bull, "RELIANCE")
    assert isinstance(sig, StrategySignal)
    assert sig.symbol == "RELIANCE"
    assert sig.pipeline_id == "pipeline_b_nifty"
    assert sig.signal in (SignalAction.BUY, SignalAction.HOLD)
    assert 0.0 <= sig.signal_strength <= 1.0

    if sig.signal == SignalAction.BUY:
        assert sig.suggested_stop_loss is not None
        assert sig.suggested_take_profit is not None
        assert sig.suggested_stop_loss < sig.entry_reference_price < sig.suggested_take_profit


def test_mean_reversion_strategy_oversold_and_suppression():
    """Verify MeanReversionStrategy triggers on oversold in range regime, but suppressed in trending regime."""
    df = _create_synthetic_ohlcv(n_bars=60)
    # Force last bar to drop drastically below lower Bollinger Band (oversold dip)
    df.loc[df.index[-1], "close"] = df["close"].iloc[-2] * 0.90
    df.loc[df.index[-1], "low"] = df["close"].iloc[-1] * 0.99
    df.loc[df.index[-1], "high"] = df["close"].iloc[-2]

    strat = MeanReversionStrategy(bb_window=20, rsi_oversold=40.0)

    # 1. In SIDEWAYS regime: should generate BUY on oversold dip
    sig_range = strat.generate_signal(df, "HDFCBANK", market_regime=MarketRegime.SIDEWAYS_RANGE_BOUND)
    assert sig_range.signal == SignalAction.BUY
    assert sig_range.suggested_take_profit > sig_range.entry_reference_price  # Target middle band

    # 2. In BULLISH_TRENDING or STRESS_ABNORMAL regime: must be suppressed
    sig_stress = strat.generate_signal(df, "HDFCBANK", market_regime=MarketRegime.STRESS_ABNORMAL)
    assert sig_stress.signal == SignalAction.NO_SIGNAL
    assert sig_stress.data_quality["regime_suppressed"] is True


def test_breakout_strategy_no_lookahead():
    """Verify BreakoutStrategy computes historical channel strictly excluding current bar."""
    df = _create_synthetic_ohlcv(n_bars=60)
    strat = BreakoutStrategy(channel_window=20, rvol_threshold=1.1)

    # Force last bar to spike above 20-day high with high volume
    max_prev = df["high"].iloc[-21:-1].max()
    df.loc[df.index[-1], "close"] = max_prev * 1.03
    df.loc[df.index[-1], "high"] = max_prev * 1.04
    df.loc[df.index[-1], "volume"] = df["volume"].iloc[-20:].mean() * 2.0  # 2.0x RVOL

    sig = strat.generate_signal(df, "INFY")
    assert sig.signal == SignalAction.BUY
    assert sig.supporting_evidence["channel_high"] == pytest.approx(max_prev)
    assert sig.supporting_evidence["volume_confirmed"] is True
    assert sig.suggested_stop_loss < sig.entry_reference_price < sig.suggested_take_profit


def test_strategy_input_validation():
    """Verify strategies reject empty DataFrames, missing columns, or insufficient bars."""
    strat = MomentumStrategy(fast_window=10, slow_window=50)

    # Empty DataFrame
    with pytest.raises(ValueError, match="empty DataFrame"):
        strat.generate_signal(pd.DataFrame(), "TEST")

    # Insufficient bars
    short_df = _create_synthetic_ohlcv(n_bars=15)
    with pytest.raises(ValueError, match="requires >="):
        strat.generate_signal(short_df, "TEST")

    # Missing required column
    missing_col_df = _create_synthetic_ohlcv(n_bars=60).drop(columns=["close"])
    with pytest.raises(ValueError, match="missing required columns"):
        strat.generate_signal(missing_col_df, "TEST")


def test_fi2010_pipeline_isolation():
    """Verify FI2010MicrostructureStrategy rejects equity OHLCV data to prevent pipeline mixing."""
    fi_strat = FI2010MicrostructureStrategy(prediction_horizon=100)

    # Attempt to feed NIFTY equity OHLCV into FI-2010 strategy -> MUST raise ValueError
    equity_df = _create_synthetic_ohlcv(n_bars=40)
    with pytest.raises(ValueError, match="strictly isolated to Pipeline A"):
        fi_strat.generate_signal(equity_df, "NIFTY_STOCK")

    # Valid Pipeline A LOB input with model prediction
    mock_pred = {"predicted_class": 1, "probabilities": [0.72, 0.15, 0.13]}
    dummy_lob_df = pd.DataFrame({"timestamp": [pd.Timestamp.now()], "lob_feature_0": [0.5]})
    sig = fi_strat.generate_signal(dummy_lob_df, "FI2010_LOB", model_prediction=mock_pred)

    assert sig.pipeline_id == "pipeline_a_fi2010"
    assert sig.signal == SignalAction.BUY
    assert sig.prediction_horizon == 100
    assert sig.signal_strength == 0.72


def test_adaptive_strategy_selector_regime_routing():
    """Verify strategy selector prioritizes Momentum in Bullish and MeanReversion in Sideways."""
    now = pd.Timestamp.now()
    sig_mom = StrategySignal("TEST", "pipeline_b_nifty", "MomentumStrategy", "1.0", SignalAction.BUY, 0.80, "1d", now)
    sig_mr = StrategySignal("TEST", "pipeline_b_nifty", "MeanReversionStrategy", "1.0", SignalAction.BUY, 0.80, "1d", now)
    sig_bo = StrategySignal("TEST", "pipeline_b_nifty", "BreakoutStrategy", "1.0", SignalAction.BUY, 0.80, "1d", now)

    candidates = [sig_mom, sig_mr, sig_bo]
    selector = AdaptiveStrategySelector()

    # 1. Bullish regime -> selects Momentum
    res_bull = selector.select_strategy(candidates, market_regime=MarketRegime.BULLISH_TRENDING)
    assert res_bull.selected_strategy == "MomentumStrategy"
    assert res_bull.compatibility_score >= 0.90

    # 2. Sideways regime -> selects Mean-Reversion
    res_side = selector.select_strategy(candidates, market_regime=MarketRegime.SIDEWAYS_RANGE_BOUND)
    assert res_side.selected_strategy == "MeanReversionStrategy"
    assert res_side.compatibility_score >= 0.85

    # 3. Stress abnormal regime -> all suppressed
    res_stress = selector.select_strategy(candidates, market_regime=MarketRegime.STRESS_ABNORMAL)
    assert res_stress.selected_strategy is None
    assert "suppressed" in res_stress.selection_reason.lower()


def test_adaptive_strategy_engine_integration():
    """Verify AdaptiveStrategyEngine executes candidate strategies and emits top signal."""
    df = _create_synthetic_ohlcv(n_bars=80, trend=0.003)
    engine = AdaptiveStrategyEngine()

    sig, selection_res = engine.evaluate_strategies(
        df_market=df,
        symbol="TCS",
        market_regime=MarketRegime.BULLISH_TRENDING,
    )

    assert isinstance(sig, StrategySignal)
    assert sig.symbol == "TCS"
    assert sig.pipeline_id == "pipeline_b_nifty"
    assert isinstance(selection_res, StrategySelectionResult)
    assert selection_res.market_regime == MarketRegime.BULLISH_TRENDING
