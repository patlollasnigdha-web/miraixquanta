"""
MIRAI — Base Trading Strategy Interface (M08)
Defines common strategy contracts, signal data structures, and input validation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("BaseStrategy")


class SignalAction:
    """Standardized trading action directives."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NO_SIGNAL = "NO_SIGNAL"

    ALL_ACTIONS = [BUY, SELL, HOLD, NO_SIGNAL]


@dataclass
class StrategySignal:
    """
    Standardized trading signal emitted by candidate strategies.
    Contains actionable price levels, confidence, regime context, and evidence.
    """
    symbol: str
    pipeline_id: str  # 'pipeline_a_fi2010' or 'pipeline_b_nifty'
    strategy_name: str
    strategy_version: str
    signal: str  # BUY, SELL, HOLD, NO_SIGNAL
    signal_strength: float  # [0.0, 1.0] conviction/strength
    prediction_horizon: Union[int, str]  # ticks (e.g. 100) or bars (e.g. '1d', '1min')
    timestamp: pd.Timestamp
    entry_reference_price: Optional[float] = None
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    applicable_market_regime: Optional[str] = None
    supporting_evidence: Dict[str, Any] = field(default_factory=dict)
    data_quality: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Converts signal dataclass to dictionary."""
        return {
            "symbol": self.symbol,
            "pipeline_id": self.pipeline_id,
            "strategy_name": self.strategy_name,
            "strategy_version": self.strategy_version,
            "signal": self.signal,
            "signal_strength": round(self.signal_strength, 3),
            "prediction_horizon": str(self.prediction_horizon),
            "timestamp": self.timestamp.isoformat() if hasattr(self.timestamp, "isoformat") else str(self.timestamp),
            "entry_reference_price": round(self.entry_reference_price, 4) if self.entry_reference_price is not None else None,
            "suggested_stop_loss": round(self.suggested_stop_loss, 4) if self.suggested_stop_loss is not None else None,
            "suggested_take_profit": round(self.suggested_take_profit, 4) if self.suggested_take_profit is not None else None,
            "applicable_market_regime": self.applicable_market_regime,
            "supporting_evidence": self.supporting_evidence,
            "data_quality": self.data_quality,
        }


class BaseTradingStrategy(ABC):
    """
    Abstract Base Class for all MIRAI trading strategies.
    Ensures uniform signal generation, parameterization, and validation.
    """

    def __init__(
        self,
        strategy_name: str = "BaseStrategy",
        strategy_version: str = "1.0.0",
        pipeline_id: str = "pipeline_b_nifty",
        prediction_horizon: Union[int, str] = "1d",
    ):
        self.strategy_name = strategy_name
        self.strategy_version = strategy_version
        self.pipeline_id = pipeline_id
        self.prediction_horizon = prediction_horizon

    def validate_market_data(
        self,
        df: pd.DataFrame,
        required_cols: List[str],
        min_bars: int = 20,
    ) -> pd.DataFrame:
        """
        Validates input market DataFrame format, required columns, and minimum bar history.
        Rejects data with NaNs in recent active rows.
        """
        if df is None or df.empty:
            raise ValueError(f"Strategy '{self.strategy_name}' received empty DataFrame.")

        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Strategy '{self.strategy_name}' missing required columns: {missing}")

        if len(df) < min_bars:
            raise ValueError(
                f"Strategy '{self.strategy_name}' requires >= {min_bars} bars, got {len(df)}."
            )

        # Check for NaN in the latest bar
        latest_row = df.iloc[-1]
        for c in required_cols:
            if pd.isna(latest_row[c]):
                raise ValueError(
                    f"Strategy '{self.strategy_name}' detected NaN in latest bar column '{c}'."
                )

        return df

    @abstractmethod
    def generate_signal(
        self,
        df_market: pd.DataFrame,
        symbol: str,
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        market_regime: Optional[str] = None,
        intelligence: Optional[Any] = None,
        **kwargs: Any,
    ) -> StrategySignal:
        """
        Evaluates market intelligence and emits a standardized StrategySignal.
        Must strictly condition on data <= as_of_date to eliminate lookahead bias.
        """
        pass


# Convenience alias for backwards compatibility
BaseStrategy = BaseTradingStrategy

