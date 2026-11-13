"""
MIRAI — Adaptive Breakout Trading Strategy (M08)
Detects structural price breakouts from historical channels with volume confirmation.
Strictly excludes the current bar from the reference range to prevent lookahead bias.
"""

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.features.technical_indicators import compute_atr, compute_sma
from src.strategies.base_strategy import BaseTradingStrategy, StrategySignal, SignalAction

logger = get_logger("BreakoutStrategy")


class BreakoutStrategy(BaseTradingStrategy):
    """
    Channel breakout strategy.
    Emits BUY when price breaks above the N-period historical high with RVOL >= 1.3.
    Emits SELL when price breaks below the N-period historical low with high volume.
    Safeguards: Channel boundaries strictly use bars [t-N : t-1] (excluding bar t).
    """

    def __init__(
        self,
        channel_window: int = 20,
        rvol_threshold: float = 1.3,
        atr_window: int = 14,
        atr_stop_multiplier: float = 2.0,
        atr_target_multiplier: float = 4.0,
        prediction_horizon: Union[int, str] = "1d",
    ):
        super().__init__(
            strategy_name="BreakoutStrategy",
            strategy_version="1.0.0",
            pipeline_id="pipeline_b_nifty",
            prediction_horizon=prediction_horizon,
        )
        cfg = get_config()
        self.channel_window = cfg.get("strategies.breakout.channel_window", channel_window)
        self.rvol_threshold = cfg.get("strategies.breakout.rvol_threshold", rvol_threshold)
        self.atr_window = cfg.get("strategies.breakout.atr_window", atr_window)
        self.atr_stop_multiplier = cfg.get("strategies.breakout.atr_stop_multiplier", atr_stop_multiplier)
        self.atr_target_multiplier = cfg.get("strategies.breakout.atr_target_multiplier", atr_target_multiplier)

    def generate_signal(
        self,
        df_market: pd.DataFrame,
        symbol: str,
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        market_regime: Optional[str] = None,
        intelligence: Optional[Any] = None,
        **kwargs: Any,
    ) -> StrategySignal:
        """Generates breakout signal with volume confirmation and strict chronological bounds."""
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
        self.validate_market_data(df, required_cols=req_cols, min_bars=self.channel_window + 5)

        close = df["close"]
        n_bars = len(close)
        current_price = float(close.iloc[-1])

        # 3. Channel Range Calculation: STRICTLY EXCLUDING CURRENT BAR t
        # Channel is computed over slice [: -1] trailing window
        w = self.channel_window
        if "high" in df.columns and "low" in df.columns:
            hist_highs = df["high"].iloc[-w - 1 : -1]
            hist_lows = df["low"].iloc[-w - 1 : -1]
            channel_high = float(hist_highs.max())
            channel_low = float(hist_lows.min())
        else:
            hist_close = close.iloc[-w - 1 : -1]
            channel_high = float(hist_close.max())
            channel_low = float(hist_close.min())

        # 4. Volume Confirmation (RVOL)
        rvol = 1.0
        has_volume = "volume" in df.columns and df["volume"].sum() > 0
        if has_volume:
            vol = df["volume"]
            avg_vol = float(vol.iloc[-w - 1 : -1].mean())
            current_vol = float(vol.iloc[-1])
            rvol = current_vol / max(avg_vol, 1.0)

        # 5. ATR for Stop Loss & Take Profit
        if "high" in df.columns and "low" in df.columns:
            atr_series = compute_atr(df["high"], df["low"], close, self.atr_window)
            atr = float(atr_series.iloc[-1]) if not np.isnan(atr_series.iloc[-1]) else (current_price * 0.015)
        else:
            atr = current_price * 0.015

        evidence = {
            "current_price": current_price,
            "channel_high": channel_high,
            "channel_low": channel_low,
            "channel_window": self.channel_window,
            "rvol": round(rvol, 2),
            "rvol_threshold": self.rvol_threshold,
            "volume_confirmed": rvol >= self.rvol_threshold if has_volume else False,
            "atr": atr,
        }

        signal = SignalAction.NO_SIGNAL
        conviction = 0.5
        stop_loss = None
        take_profit = None

        # BUY Breakout: Current Price > Channel High WITH Volume Confirmation
        if current_price > channel_high:
            if not has_volume or rvol >= self.rvol_threshold:
                signal = SignalAction.BUY
                vol_boost = min(0.20, (rvol - 1.0) * 0.10) if has_volume else 0.0
                conviction = float(np.clip(0.65 + vol_boost, 0.55, 0.95))
                # Stop loss placed at channel midpoint or entry - 2 ATR
                mid_channel = (channel_high + channel_low) / 2.0
                stop_loss = max(mid_channel, current_price - (atr * self.atr_stop_multiplier))
                take_profit = current_price + (atr * self.atr_target_multiplier)
            else:
                evidence["warning"] = "Price broke above channel but lacked volume confirmation (unconfirmed breakout)."

        # SELL Breakdown: Current Price < Channel Low WITH Volume Confirmation
        elif current_price < channel_low:
            if not has_volume or rvol >= self.rvol_threshold:
                signal = SignalAction.SELL
                vol_boost = min(0.20, (rvol - 1.0) * 0.10) if has_volume else 0.0
                conviction = float(np.clip(0.65 + vol_boost, 0.55, 0.95))
                mid_channel = (channel_high + channel_low) / 2.0
                stop_loss = min(mid_channel, current_price + (atr * self.atr_stop_multiplier))
                take_profit = current_price - (atr * self.atr_target_multiplier)
            else:
                evidence["warning"] = "Price broke below channel but lacked volume confirmation (unconfirmed breakdown)."

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
            data_quality={"history_bars": n_bars, "has_volume": has_volume},
        )
