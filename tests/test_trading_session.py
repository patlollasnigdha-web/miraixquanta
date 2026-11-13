"""
Tests for MIRAI Paper Trading Session Management (M14)
Validates lifecycle boundaries, state transitions, and operational invariants.
"""

import pytest
import pandas as pd
from src.paper_trading.trading_session import TradingSession
from src.paper_trading.paper_trading_schemas import (
    SessionConfig,
    SessionStatus,
    InvalidSessionStateError,
)


def test_session_lifecycle_happy_path():
    cfg = SessionConfig(session_name="DailyReplay", symbols=["TCS", "INFY"])
    session = TradingSession(cfg)

    assert session.status == SessionStatus.CREATED
    assert session.is_active is False
    assert session.is_terminal is False

    # Start
    session.start()
    assert session.status == SessionStatus.RUNNING
    assert session.is_active is True
    assert session.start_time is not None

    # Process bar
    session.record_bar_processed()
    assert session.bars_processed == 1

    # Pause
    session.pause()
    assert session.status == SessionStatus.PAUSED
    assert session.is_active is False

    # Resume
    session.resume()
    assert session.status == SessionStatus.RUNNING
    assert session.is_active is True

    # Stop
    session.stop()
    assert session.status == SessionStatus.STOPPED
    assert session.is_active is False
    assert session.is_terminal is True
    assert session.end_time is not None

    # Close
    session.close()
    assert session.status == SessionStatus.CLOSED
    assert session.is_terminal is True


def test_invalid_lifecycle_transitions():
    session = TradingSession()
    # Cannot pause or stop from CREATED
    with pytest.raises(InvalidSessionStateError):
        session.pause()

    # Start session
    session.start()

    # Cannot transition RUNNING directly to CLOSED (must stop first)
    with pytest.raises(InvalidSessionStateError):
        session.close()

    # Stop session
    session.stop()

    # Terminal state cannot be restarted
    with pytest.raises(InvalidSessionStateError):
        session.start()

    with pytest.raises(InvalidSessionStateError):
        session.resume()


def test_record_bar_while_paused_or_stopped_raises():
    session = TradingSession()
    # While CREATED
    with pytest.raises(RuntimeError, match="Cannot process bars"):
        session.record_bar_processed()

    session.start()
    session.pause()
    # While PAUSED
    with pytest.raises(RuntimeError, match="Cannot process bars"):
        session.record_bar_processed()


def test_session_serialization():
    cfg = SessionConfig(session_name="TestExport", symbols=["RELIANCE"])
    session = TradingSession(cfg)
    session.start()
    session.record_bar_processed()

    d = session.to_dict()
    assert d["session_name"] == "TestExport"
    assert d["status"] == "RUNNING"
    assert d["bars_processed"] == 1
    assert "start_time" in d
