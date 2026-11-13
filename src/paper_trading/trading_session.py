"""
MIRAI — Paper Trading Session Management (M14)
Manages session lifecycles (CREATED -> RUNNING -> PAUSED -> STOPPED -> CLOSED),
metadata, and execution boundaries.
"""

from typing import Any, Dict, List, Optional
import pandas as pd

from src.utils.logger import get_logger
from src.paper_trading.paper_trading_schemas import (
    SessionConfig,
    SessionStatus,
    InvalidSessionStateError,
    validate_session_transition,
)

logger = get_logger("TradingSession")


class TradingSession:
    """
    Manages state and lifecycle boundaries for an isolated paper trading session.
    """

    def __init__(self, config: Optional[SessionConfig] = None):
        self.config = config or SessionConfig()
        self.session_id = self.config.session_id
        self.status = SessionStatus.CREATED
        self.start_time: Optional[pd.Timestamp] = None
        self.end_time: Optional[pd.Timestamp] = None
        self.bars_processed: int = 0
        self.orders_count: int = 0
        self.trades_count: int = 0

    @property
    def is_active(self) -> bool:
        """True if session is actively executing (RUNNING)."""
        return self.status == SessionStatus.RUNNING

    @property
    def is_terminal(self) -> bool:
        """True if session is finished and cannot execute further orders."""
        return self.status in (SessionStatus.STOPPED, SessionStatus.CLOSED)

    def start(self) -> None:
        """Starts the session."""
        validate_session_transition(self.status, SessionStatus.RUNNING)
        self.status = SessionStatus.RUNNING
        self.start_time = pd.Timestamp.now()
        logger.info("Session %s started at %s", self.session_id, self.start_time)

    def pause(self) -> None:
        """Pauses order execution."""
        validate_session_transition(self.status, SessionStatus.PAUSED)
        self.status = SessionStatus.PAUSED
        logger.info("Session %s paused", self.session_id)

    def resume(self) -> None:
        """Resumes a paused session."""
        validate_session_transition(self.status, SessionStatus.RUNNING)
        self.status = SessionStatus.RUNNING
        logger.info("Session %s resumed", self.session_id)

    def stop(self) -> None:
        """Stops trading in this session."""
        validate_session_transition(self.status, SessionStatus.STOPPED)
        self.status = SessionStatus.STOPPED
        self.end_time = pd.Timestamp.now()
        logger.info("Session %s stopped at %s", self.session_id, self.end_time)

    def close(self) -> None:
        """Permanently closes the session."""
        validate_session_transition(self.status, SessionStatus.CLOSED)
        self.status = SessionStatus.CLOSED
        if self.end_time is None:
            self.end_time = pd.Timestamp.now()
        logger.info("Session %s closed", self.session_id)

    def record_bar_processed(self) -> None:
        """Increments processed bar count."""
        if not self.is_active:
            raise RuntimeError(f"Cannot process bars when session is in {self.status.value} state.")
        self.bars_processed += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_name": self.config.session_name,
            "status": self.status.value,
            "mode": self.config.mode.value,
            "start_time": (
                self.start_time.isoformat()
                if self.start_time is not None and hasattr(self.start_time, "isoformat")
                else (str(self.start_time) if self.start_time is not None else None)
            ),
            "end_time": (
                self.end_time.isoformat()
                if self.end_time is not None and hasattr(self.end_time, "isoformat")
                else (str(self.end_time) if self.end_time is not None else None)
            ),
            "bars_processed": self.bars_processed,
            "orders_count": self.orders_count,
            "trades_count": self.trades_count,
            "initial_capital": self.config.initial_capital,
            "symbols": self.config.symbols,
        }
