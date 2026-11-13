"""
MIRAI — FI-2010 Microstructure Order-Book Strategy (M08)
Dedicated strategy for Pipeline A. Consumes high-frequency limit order book (LOB)
features, depth imbalances, and predictive model class probabilities over tick horizons.
"""

from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.strategies.base_strategy import BaseTradingStrategy, StrategySignal, SignalAction

logger = get_logger("FI2010Strategy")


class FI2010MicrostructureStrategy(BaseTradingStrategy):
    """
    High-frequency order-book strategy strictly isolated to Pipeline A.
    Evaluates depth imbalances, spread compression, and model probabilities
    over tick-based horizons (10, 20, 50, 100 ticks).
    """

    def __init__(
        self,
        prediction_horizon: int = 100,
        min_imbalance: float = 0.20,
        prob_threshold: float = 0.50,
    ):
        super().__init__(
            strategy_name="FI2010MicrostructureStrategy",
            strategy_version="1.0.0",
            pipeline_id="pipeline_a_fi2010",
            prediction_horizon=prediction_horizon,
        )
        cfg = get_config()
        self.min_imbalance = cfg.get("strategies.fi2010_microstructure.min_imbalance", min_imbalance)
        self.prob_threshold = cfg.get("strategies.fi2010_microstructure.prob_threshold", prob_threshold)

    def generate_signal(
        self,
        df_market: pd.DataFrame,
        symbol: str = "FI2010_LOB",
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        market_regime: Optional[str] = None,
        intelligence: Optional[Any] = None,
        model_prediction: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> StrategySignal:
        """
        Generates tick microstructure signals from LOB features or model predictions.
        Strictly rejects equity daily/intraday OHLCV to prevent pipeline mixing.
        """
        # Pipeline isolation guard: reject NIFTY equity OHLCV
        if "close" in df_market.columns and "volume" in df_market.columns and "lob_feature_0" not in df_market.columns and "bid_price_1" not in df_market.columns:
            raise ValueError(
                "FI2010MicrostructureStrategy is strictly isolated to Pipeline A (FI-2010). "
                "Cannot consume Pipeline B equity OHLCV data."
            )

        eval_time = pd.Timestamp.now()
        if "timestamp" in df_market.columns:
            eval_time = pd.to_datetime(df_market["timestamp"].iloc[-1])

        # 1. Evaluate from Model Prediction if supplied
        signal = SignalAction.NO_SIGNAL
        conviction = 0.5
        evidence = {}

        if model_prediction is not None:
            pred_class = model_prediction.get("predicted_class")  # 1: Upward, 2: Stationary, 3: Downward
            probs = model_prediction.get("probabilities", [])

            evidence["model_predicted_class"] = pred_class
            evidence["probabilities"] = probs

            if pred_class == 1:  # Upward
                prob = probs[0] if len(probs) >= 1 else 0.65
                if prob >= self.prob_threshold:
                    signal = SignalAction.BUY
                    conviction = float(prob)
            elif pred_class == 3:  # Downward
                prob = probs[2] if len(probs) >= 3 else 0.65
                if prob >= self.prob_threshold:
                    signal = SignalAction.SELL
                    conviction = float(prob)
            elif pred_class == 2:  # Stationary
                signal = SignalAction.HOLD
                conviction = float(probs[1]) if len(probs) >= 2 else 0.50

        # 2. Evaluate from LOB depth features if available
        elif "bid_size_1" in df_market.columns and "ask_size_1" in df_market.columns:
            bid = float(df_market["bid_size_1"].iloc[-1])
            ask = float(df_market["ask_size_1"].iloc[-1])
            mid = float((df_market["bid_price_1"].iloc[-1] + df_market["ask_price_1"].iloc[-1]) / 2.0)
            imbalance = (bid - ask) / max(bid + ask, 1.0)

            evidence["bid_size_1"] = bid
            evidence["ask_size_1"] = ask
            evidence["depth_imbalance"] = imbalance
            evidence["mid_price"] = mid

            if imbalance >= self.min_imbalance:
                signal = SignalAction.BUY
                conviction = float(np.clip(0.55 + imbalance * 0.35, 0.50, 0.90))
            elif imbalance <= -self.min_imbalance:
                signal = SignalAction.SELL
                conviction = float(np.clip(0.55 + abs(imbalance) * 0.35, 0.50, 0.90))
            else:
                signal = SignalAction.HOLD
                conviction = 0.50

        return StrategySignal(
            symbol=symbol,
            pipeline_id=self.pipeline_id,
            strategy_name=self.strategy_name,
            strategy_version=self.strategy_version,
            signal=signal,
            signal_strength=conviction,
            prediction_horizon=self.prediction_horizon,
            timestamp=eval_time,
            entry_reference_price=evidence.get("mid_price"),
            applicable_market_regime=market_regime,
            supporting_evidence=evidence,
            data_quality={"is_lob_data": True, "pipeline": "Pipeline A"},
        )
