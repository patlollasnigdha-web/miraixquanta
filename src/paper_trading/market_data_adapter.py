"""
MIRAI — Market Data Adapter for Paper Trading (M14)
Provides chronological market bar delivery in HISTORICAL_REPLAY mode
and safe LIVE_FEED polling mode. Enforces strict pipeline separation
and stale-data rejection.
"""

from typing import Any, Dict, Generator, List, Optional, Tuple, Union
import time
import pandas as pd

from src.utils.logger import get_logger
from src.data_engineering.data_access import DataAccessService
from src.paper_trading.paper_trading_schemas import PaperTradingMode

logger = get_logger("MarketDataAdapter")


class MarketDataAdapter:
    """
    Supplies market data bars to the paper trading engine.
    Supports deterministic chronological replay and live-feed simulation.
    """

    def __init__(
        self,
        mode: PaperTradingMode = PaperTradingMode.HISTORICAL_REPLAY,
        data_service: Optional[DataAccessService] = None,
        stale_data_timeout_sec: float = 300.0,
        replay_speed_multiplier: float = 1.0,
        pipeline_id: str = "pipeline_b_nifty",
    ):
        self.mode = mode
        self.data_service = data_service or DataAccessService()
        self.stale_timeout_sec = stale_data_timeout_sec
        self.replay_speed = max(0.01, replay_speed_multiplier)
        self.pipeline_id = pipeline_id

        # Replay cursor state
        self._replay_data: Optional[pd.DataFrame] = None
        self._cursor: int = 0
        self._is_paused: bool = False
        self._is_stopped: bool = False

    def load_replay_data(
        self,
        symbol: str = "TCS",
        years: Optional[List[int]] = None,
        custom_df: Optional[pd.DataFrame] = None,
    ) -> int:
        """
        Loads market data for replay.
        Enforces strict pipeline isolation: rejects FI-2010 microstructure in equity mode.
        """
        if self.pipeline_id == "pipeline_a_fi2010":
            if custom_df is not None and "close" in custom_df.columns:
                raise ValueError("Cannot load equity OHLCV DataFrame into FI-201 micro pipeline.")
            logger.info("MarketDataAdapter configured for Pipeline A (FI-2010) microstructure replay.")
            self._replay_data = custom_df
            self._cursor = 0
            return len(custom_df) if custom_df is not None else 0

        # Pipeline B: Indian Equity
        if custom_df is not None:
            if "lob_feature_0" in custom_df.columns:
                raise ValueError(
                    "Pipeline Isolation Breach: Cannot pass FI-2010 LOB microstructure arrays "
                    "as Indian stock market prices in Pipeline B."
                )
            self._replay_data = custom_df.copy()
        else:
            # Load from DataAccessService
            daily_stocks = self.data_service.get_multistock_daily(years=years, symbols=[symbol])
            if daily_stocks.empty:
                # Fallback to NIFTY index
                self._replay_data = self.data_service.get_nifty_daily_index()
            else:
                self._replay_data = daily_stocks

        self._cursor = 0
        self._is_paused = False
        self._is_stopped = False
        n_bars = len(self._replay_data)
        logger.info("Loaded %d bars for replay (%s, %s)", n_bars, symbol, self.pipeline_id)
        return n_bars

    def has_next_bar(self) -> bool:
        """Checks if replay has unconsumed bars remaining and is not stopped."""
        if self._is_stopped or self._replay_data is None:
            return False
        return self._cursor < len(self._replay_data)

    def get_next_bar(self) -> Optional[Tuple[pd.Series, pd.DataFrame]]:
        """
        Advances the replay cursor and emits:
        (current_bar, historical_slice_up_to_current_bar)
        Guarantees zero forward lookahead: history is strictly <= current bar.
        """
        if not self.has_next_bar() or self._is_paused:
            return None

        current_bar = self._replay_data.iloc[self._cursor]
        history_slice = self._replay_data.iloc[: self._cursor + 1]
        self._cursor += 1

        return current_bar, history_slice

    def pause(self) -> None:
        """Pauses historical replay."""
        self._is_paused = True
        logger.info("MarketDataAdapter replay paused at bar %d", self._cursor)

    def resume(self) -> None:
        """Resumes historical replay."""
        self._is_paused = False
        logger.info("MarketDataAdapter replay resumed at bar %d", self._cursor)

    def stop(self) -> None:
        """Stops historical replay completely."""
        self._is_stopped = True
        logger.info("MarketDataAdapter replay stopped at bar %d", self._cursor)

    def is_data_stale(self, bar_timestamp: pd.Timestamp, current_time: Optional[pd.Timestamp] = None) -> bool:
        """
        Evaluates whether a market bar's timestamp is stale.
        In HISTORICAL_REPLAY mode, bars are deterministic historical events so staleness is not triggered.
        In LIVE_FEED mode, checks if age exceeds stale_data_timeout_sec.
        """
        if self.mode == PaperTradingMode.HISTORICAL_REPLAY:
            return False

        now_ts = current_time or pd.Timestamp.now()
        age_sec = (now_ts - bar_timestamp).total_seconds()
        return age_sec > self.stale_timeout_sec
