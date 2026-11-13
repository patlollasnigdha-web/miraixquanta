"""
MIRAI — Adaptive Mean-Reversion Trading Strategy (M08)
Identifies statistical price extremes using Bollinger Bands, RSI exhaustion,
and volatility-aware thresholds. Suppressed during trending or stress regimes.
"""

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.features.technical_indicators import (
    compute_sma,
    compute_rsi,
    compute_bollinger_bands,
    compute_atr,
)
from src.strategies.base_strategy import BaseTradingStrategy, StrategySignal, SignalAction

logger = get_logger("MeanReversionStrategy")


class MeanReversionStrategy(BaseTradingStrategy):
    """
    Mean-reversion strategy.
    Emits BUY when price drops below the lower Bollinger Band with RSI <= oversold.
    Emits SELL when price exceeds the upper Bollinger Band with RSI >= overbought.
    Target is typically the middle band (SMA 20).
    Safeguards: Suppressed during directional trending regimes or extreme stress.
    """

    SUPPRESSED_REGIMES = ["BULLISH_TRENDING", "BEARISH_TRENDING", "STRESS_ABNORMAL", "HIGH_VOLATILITY"]

    def __init__(
        self,
        bb_window: int = 20,
        bb_std: float = 2.0,
        rsi_window: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        atr_window: int = 14,
        atr_stop_multiplier: float = 1.5,
        atr_target_multiplier: float = 2.0,
        prediction_horizon: Union[int, str] = "1d",
    ):
        super().__init__(
            strategy_name="MeanReversionStrategy",
            strategy_version="1.0.0",
            pipeline_id="pipeline_b_nifty",
            prediction_horizon=prediction_horizon,
        )
        cfg = get_config()
        self.bb_window = cfg.get("strategies.mean_reversion.bb_window", bb_window)
        self.bb_std = cfg.get("strategies.mean_reversion.bb_std", bb_std)
        self.rsi_window = cfg.get("strategies.mean_reversion.rsi_window", rsi_window)
        self.rsi_oversold = cfg.get("strategies.mean_reversion.rsi_oversold", rsi_oversold)
        self.rsi_overbought = cfg.get("strategies.mean_reversion.rsi_overbought", rsi_overbought)
        self.atr_window = cfg.get("strategies.mean_reversion.atr_window", atr_window)
        self.atr_stop_multiplier = cfg.get("strategies.mean_reversion.atr_stop_multiplier", atr_stop_multiplier)
        self.atr_target_multiplier = cfg.get("strategies.mean_reversion.atr_target_multiplier", atr_target_multiplier)

    def generate_signal(
        self,
        df_market: pd.DataFrame,
        symbol: str,
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        market_regime: Optional[str] = None,
        intelligence: Optional[Any] = None,
        **kwargs: Any,
    ) -> StrategySignal:
        """Generates mean-reversion signal with regime safeguard filtering."""
        # 1. Conditioning on as_of_date
        df = df_market.copy()
        if "timestamp" in df.columns and as_of_date is not None:
            as_of_ts = pd.to_datetime(as_of_date)
            df = df[pd.to_datetime(df["timestamp"]) <= as_of_ts]
            eval_time = df["timestamp"].iloc[-1] if not df.empty else as_of_ts
        else:
            eval_time = pd.Timestamp.now()

        # 2. Input validation
        self.validate_market_data(df, required_cols=["close"], min_bars=self.bb_window + 5)
        close = df["close"]
        n_bars = len(close)
        current_price = float(close.iloc[-1])

        # 3. Regime Safeguard Check
        # Mean reversion is dangerous during strong trending or stress regimes
        if market_regime in self.SUPPRESSED_REGIMES:
            logger.debug(
                "MeanReversionStrategy suppressed for %s: regime '%s' favors directional movement.",
                symbol, market_regime
            )
            return StrategySignal(
                symbol=symbol,
                pipeline_id=self.pipeline_id,
                strategy_name=self.strategy_name,
                strategy_version=self.strategy_version,
                signal=SignalAction.NO_SIGNAL,
                signal_strength=0.0,
                prediction_horizon=self.prediction_horizon,
                timestamp=eval_time,
                entry_reference_price=current_price,
                applicable_market_regime=market_regime,
                supporting_evidence={
                    "suppression_reason": f"Regime '{market_regime}' is unsuitable for mean-reversion.",
                    "current_price": current_price,
                },
                data_quality={"history_bars": n_bars, "regime_suppressed": True},
            )

        # 4. Technical Indicator Calculations
        upper_s, middle_s, lower_s, bw_s, pct_b_s = compute_bollinger_bands(close, self.bb_window, self.bb_std)
        upper = float(upper_s.iloc[-1])
        middle = float(middle_s.iloc[-1])
        lower = float(lower_s.iloc[-1])
        pct_b = float(pct_b_s.iloc[-1])
        bandwidth = float(bw_s.iloc[-1])

        rsi_series = compute_rsi(close, self.rsi_window)
        rsi = float(rsi_series.iloc[-1]) if not np.isnan(rsi_series.iloc[-1]) else 50.0

        if "high" in df.columns and "low" in df.columns:
            atr_series = compute_atr(df["high"], df["low"], close, self.atr_window)
            atr = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else (current_price * 0.015)
        else:
            atr = current_price * 0.015

        evidence = {
            "current_price": current_price,
            "bb_upper": upper,
            "bb_middle": middle,
            "bb_lower": lower,
            "bb_percent_b": pct_b,
            "bb_bandwidth": bandwidth,
            "rsi": rsi,
            "atr": atr,
        }

        signal = SignalAction.NO_SIGNAL
        conviction = 0.5
        stop_loss = None
        take_profit = None

        # BUY condition (Oversold Dip): Price <= Lower BB (pct_b <= 0.05) and RSI <= oversold
        if pct_b <= 0.05 and rsi <= self.rsi_oversold:
            signal = SignalAction.BUY
            # Deeper oversold gives higher conviction
            conviction = float(np.clip(0.60 + (self.rsi_oversold - rsi) * 0.015, 0.50, 0.90))
            stop_loss = current_price - (atr * self.atr_stop_multiplier)
            take_profit = middle  # Target reversion to middle band (SMA 20)

        # SELL condition (Overbought Spike): Price >= Upper BB (pct_b >= 0.95) and RSI >= overbought
        elif pct_b >= 0.95 and rsi >= self.rsi_overbought:
            signal = SignalAction.SELL
            conviction = float(np.clip(0.60 + (rsi - self.rsi_overbought) * 0.015, 0.50, 0.90))
            stop_loss = current_price + (atr * self.atr_stop_multiplier)
            take_profit = middle  # Target reversion to middle band (SMA 20)

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
            data_quality={"history_bars": n_bars, "regime_suppressed": False},
        )
