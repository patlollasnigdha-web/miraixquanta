"""
MIRAI — Adaptive Momentum Trading Strategy (M08)
Captures directional trend expansion using moving average alignment,
RSI momentum confirmation, ATR targets, and stock strength intelligence.
"""

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.features.technical_indicators import (
    compute_ema,
    compute_sma,
    compute_rsi,
    compute_macd,
    compute_atr,
)
from src.strategies.base_strategy import BaseTradingStrategy, StrategySignal, SignalAction

logger = get_logger("MomentumStrategy")


class MomentumStrategy(BaseTradingStrategy):
    """
    Momentum trend-following strategy.
    Emits BUY when fast EMA > slow EMA, RSI in healthy bullish band, and MACD hist positive.
    Emits SELL when trend breaks down.
    Integrates Stock Strength Score (M05) to scale conviction.
    """

    def __init__(
        self,
        fast_window: int = 10,
        slow_window: int = 50,
        rsi_window: int = 14,
        rsi_bullish_min: float = 50.0,
        rsi_overbought: float = 75.0,
        atr_window: int = 14,
        atr_stop_multiplier: float = 2.0,
        atr_target_multiplier: float = 3.5,
        min_strength_score: float = 55.0,
        prediction_horizon: Union[int, str] = "1d",
    ):
        super().__init__(
            strategy_name="MomentumStrategy",
            strategy_version="1.0.0",
            pipeline_id="pipeline_b_nifty",
            prediction_horizon=prediction_horizon,
        )
        cfg = get_config()
        self.fast_window = cfg.get("strategies.momentum.fast_window", fast_window)
        self.slow_window = cfg.get("strategies.momentum.slow_window", slow_window)
        self.rsi_window = cfg.get("strategies.momentum.rsi_window", rsi_window)
        self.rsi_bullish_min = cfg.get("strategies.momentum.rsi_bullish_min", rsi_bullish_min)
        self.rsi_overbought = cfg.get("strategies.momentum.rsi_overbought", rsi_overbought)
        self.atr_window = cfg.get("strategies.momentum.atr_window", atr_window)
        self.atr_stop_multiplier = cfg.get("strategies.momentum.atr_stop_multiplier", atr_stop_multiplier)
        self.atr_target_multiplier = cfg.get("strategies.momentum.atr_target_multiplier", atr_target_multiplier)
        self.min_strength_score = min_strength_score

    def generate_signal(
        self,
        df_market: pd.DataFrame,
        symbol: str,
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        market_regime: Optional[str] = None,
        intelligence: Optional[Any] = None,
        **kwargs: Any,
    ) -> StrategySignal:
        """Generates momentum signal with strict no-lookahead conditioning."""
        # 1. Conditioning on as_of_date
        df = df_market.copy()
        if "timestamp" in df.columns and as_of_date is not None:
            as_of_ts = pd.to_datetime(as_of_date)
            df = df[pd.to_datetime(df["timestamp"]) <= as_of_ts]
            eval_time = df["timestamp"].iloc[-1] if not df.empty else as_of_ts
        else:
            eval_time = pd.Timestamp.now()

        # 2. Input validation
        req_cols = ["close"]
        if "high" in df.columns and "low" in df.columns:
            req_cols.extend(["high", "low"])
        self.validate_market_data(df, required_cols=req_cols, min_bars=self.slow_window + 5)

        close = df["close"]
        n_bars = len(close)
        current_price = float(close.iloc[-1])

        # 3. Technical Indicator Calculations
        ema_fast = compute_ema(close, self.fast_window).iloc[-1]
        ema_slow = compute_ema(close, self.slow_window).iloc[-1]
        ema_diff_pct = (ema_fast - ema_slow) / max(ema_slow, 1e-8)

        rsi_series = compute_rsi(close, self.rsi_window)
        rsi = float(rsi_series.iloc[-1]) if not np.isnan(rsi_series.iloc[-1]) else 50.0

        _, _, macd_hist_series = compute_macd(close, fast=12, slow=26, signal=9)
        macd_hist = float(macd_hist_series.iloc[-1]) if not np.isnan(macd_hist_series.iloc[-1]) else 0.0

        # ATR computation for stop loss & target
        if "high" in df.columns and "low" in df.columns:
            atr_series = compute_atr(df["high"], df["low"], close, self.atr_window)
            atr = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else (current_price * 0.015)
        else:
            atr = current_price * 0.015  # 1.5% proxy if high/low absent

        # 4. Integrate Stock Strength (M05) if provided
        stock_strength_val = None
        strength_boost = 1.0
        if intelligence is not None and hasattr(intelligence, "stock_strength"):
            stock_strength_val = intelligence.stock_strength.overall_score
            # Higher stock strength score increases conviction
            if stock_strength_val >= 75.0:
                strength_boost = 1.2
            elif stock_strength_val < 40.0:
                strength_boost = 0.6

        # 5. Signal Decision Logic
        evidence = {
            "current_price": current_price,
            "ema_fast": float(ema_fast),
            "ema_slow": float(ema_slow),
            "ema_diff_pct": float(ema_diff_pct),
            "rsi": rsi,
            "macd_hist": macd_hist,
            "atr": atr,
            "stock_strength_score": stock_strength_val,
        }

        signal = SignalAction.NO_SIGNAL
        conviction = 0.5
        stop_loss = None
        take_profit = None

        # BUY condition: fast EMA > slow EMA, RSI between bullish min and overbought, MACD histogram positive
        if ema_fast > ema_slow and self.rsi_bullish_min <= rsi <= self.rsi_overbought and macd_hist >= 0:
            signal = SignalAction.BUY
            base_conviction = min(0.90, 0.55 + (ema_diff_pct * 10.0) + (macd_hist / current_price * 100.0))
            conviction = float(np.clip(base_conviction * strength_boost, 0.40, 0.95))
            stop_loss = current_price - (atr * self.atr_stop_multiplier)
            take_profit = current_price + (atr * self.atr_target_multiplier)

        # SELL condition: fast EMA < slow EMA or sharp momentum breakdown
        elif ema_fast < ema_slow and (rsi < 45.0 or macd_hist < 0):
            signal = SignalAction.SELL
            base_conviction = min(0.85, 0.50 + abs(ema_diff_pct * 10.0))
            conviction = float(np.clip(base_conviction, 0.40, 0.90))
            stop_loss = current_price + (atr * self.atr_stop_multiplier)
            take_profit = current_price - (atr * self.atr_target_multiplier)

        # HOLD condition: trend active but not an optimal fresh entry
        elif ema_fast > ema_slow and rsi > self.rsi_overbought:
            signal = SignalAction.HOLD
            conviction = 0.60
            stop_loss = current_price - (atr * self.atr_stop_multiplier)
            take_profit = current_price + (atr * self.atr_target_multiplier)
            evidence["note"] = "Trend active but RSI is overbought; trailing hold advised."

        return StrategySignal(
            symbol=symbol,
            pipeline_id=self.pipeline_id,
            strategy_name=self.strategy_name,
            strategy_version=self.strategy_version,
            signal=signal,
            signal_strength=conviction,
            prediction_horizon=self.prediction_horizon,
            timestamp=eval_time,
            entry_reference_price=current_price,
            suggested_stop_loss=stop_loss,
            suggested_take_profit=take_profit,
            applicable_market_regime=market_regime,
            supporting_evidence=evidence,
            data_quality={"history_bars": n_bars, "atr_available": True},
        )
