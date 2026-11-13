"""
MIRAI — Paper Trading Endpoints (M15)
Integrates Module M14 paper trading sessions, accounts, positions, and orders.
Strictly virtual simulation; zero real-money connectivity.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
import json

from src.api.dependencies import get_paper_state_manager
from src.paper_trading.paper_state_manager import PaperStateManager
from src.paper_trading.trading_session import TradingSession
from src.paper_trading.paper_trading_schemas import (
    PaperTradingMode,
    SessionConfig,
    SessionStatus,
    InvalidSessionStateError,
    validate_session_transition,
)
from src.paper_trading.paper_account import PaperAccount
from src.paper_trading.paper_portfolio import PaperPortfolio
from src.api.api_schemas import (
    APIResponse,
    PaperSessionCreateRequest,
    PaperSessionResponse,
)

router = APIRouter(prefix="/paper-trading", tags=["Paper Trading"])


@router.get("/account")
def get_paper_account(state_manager: PaperStateManager = Depends(get_paper_state_manager)) -> Dict[str, Any]:
    """Returns virtual paper trading account state."""
    with state_manager._get_connection() as conn:
        row = conn.execute("SELECT * FROM account_states ORDER BY rowid DESC LIMIT 1").fetchone()
        if row:
            return dict(row)

    return {
        "account_id": "DEFAULT_PAPER_ACC",
        "initial_capital": 1_000_000.0,
        "available_cash": 1_000_000.0,
        "reserved_cash": 0.0,
        "invested_capital": 0.0,
        "total_equity": 1_000_000.0,
        "circuit_breaker_state": "NORMAL",
        "message": "Default paper trading account initialized.",
    }


@router.get("/positions")
def get_paper_positions(state_manager: PaperStateManager = Depends(get_paper_state_manager)) -> Dict[str, Any]:
    """Returns all active virtual positions in the paper portfolio."""
    with state_manager._get_connection() as conn:
        rows = conn.execute("SELECT * FROM positions").fetchall()
        positions = [dict(r) for r in rows]
    return {"positions": positions, "count": len(positions)}


@router.get("/orders")
def get_paper_orders(
    limit: int = 50,
    state_manager: PaperStateManager = Depends(get_paper_state_manager),
) -> Dict[str, Any]:
    """Returns recent paper trading orders."""
    with state_manager._get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM orders ORDER BY rowid DESC LIMIT ?", (limit,)
        ).fetchall()
        orders = [dict(r) for r in rows]
    return {"orders": orders, "count": len(orders)}


@router.get("/sessions", response_model=List[PaperSessionResponse])
def list_paper_sessions(state_manager: PaperStateManager = Depends(get_paper_state_manager)):
    """Lists all registered paper trading sessions from SQLite state."""
    with state_manager._get_connection() as conn:
        rows = conn.execute("SELECT * FROM sessions ORDER BY rowid DESC").fetchall()
        sessions = [
            PaperSessionResponse(
                session_id=r["session_id"],
                session_name=r["name"],
                status=r["status"],
                mode=r["mode"],
                initial_capital=r["initial_capital"],
                symbols=r["symbols"].split(",") if r["symbols"] else [],
                start_time=r["start_time"],
                end_time=r["end_time"],
            )
            for r in rows
        ]
    return sessions


@router.post("/sessions", response_model=PaperSessionResponse, status_code=status.HTTP_201_CREATED)
def create_paper_session(
    req: PaperSessionCreateRequest,
    state_manager: PaperStateManager = Depends(get_paper_state_manager),
):
    """Creates a new isolated paper trading session."""
    mode_enum = PaperTradingMode.HISTORICAL_REPLAY if "REPLAY" in req.mode.upper() else PaperTradingMode.LIVE_FEED
    cfg = SessionConfig(
        session_name=req.session_name,
        initial_capital=req.initial_capital,
        symbols=req.symbols,
        mode=mode_enum,
    )
    session = TradingSession(cfg)
    account = PaperAccount(
        account_id=f"ACC_{session.session_id}",
        initial_capital=req.initial_capital,
    )
    portfolio = PaperPortfolio()

    state_manager.save_session_state(
        session=session,
        account=account,
        portfolio=portfolio,
        orders=[],
        trades=[],
    )

    return PaperSessionResponse(
        session_id=session.session_id,
        session_name=session.config.session_name,
        status=session.status.value,
        mode=session.config.mode.value,
        initial_capital=session.config.initial_capital,
        symbols=session.config.symbols,
    )


def _transition_session_state(
    session_id: str,
    target_status: SessionStatus,
    state_manager: PaperStateManager,
) -> PaperSessionResponse:
    """Helper to transition session status safely with persistence."""
    restored = state_manager.restore_session_state(session_id)
    if not restored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper trading session '{session_id}' not found.",
        )

    session, account, portfolio, orders, trades = restored

    # Check transition legality (raises InvalidSessionStateError if illegal)
    if target_status == SessionStatus.RUNNING:
        if session.status == SessionStatus.PAUSED:
            session.resume()
        else:
            session.start()
    elif target_status == SessionStatus.PAUSED:
        session.pause()
    elif target_status == SessionStatus.STOPPED:
        session.stop()
    elif target_status == SessionStatus.CLOSED:
        session.close()

    state_manager.save_session_state(
        session=session,
        account=account,
        portfolio=portfolio,
        orders=orders,
        trades=trades,
    )

    return PaperSessionResponse(
        session_id=session.session_id,
        session_name=session.config.session_name,
        status=session.status.value,
        mode=session.config.mode.value,
        initial_capital=session.config.initial_capital,
        symbols=session.config.symbols,
        start_time=str(session.start_time) if session.start_time else None,
        end_time=str(session.end_time) if session.end_time else None,
    )


@router.post("/sessions/{session_id}/start", response_model=PaperSessionResponse)
def start_paper_session(
    session_id: str,
    state_manager: PaperStateManager = Depends(get_paper_state_manager),
):
    """Starts execution for a created paper trading session."""
    return _transition_session_state(session_id, SessionStatus.RUNNING, state_manager)


@router.post("/sessions/{session_id}/pause", response_model=PaperSessionResponse)
def pause_paper_session(
    session_id: str,
    state_manager: PaperStateManager = Depends(get_paper_state_manager),
):
    """Pauses an active paper trading session."""
    return _transition_session_state(session_id, SessionStatus.PAUSED, state_manager)


@router.post("/sessions/{session_id}/resume", response_model=PaperSessionResponse)
def resume_paper_session(
    session_id: str,
    state_manager: PaperStateManager = Depends(get_paper_state_manager),
):
    """Resumes a paused paper trading session."""
    return _transition_session_state(session_id, SessionStatus.RUNNING, state_manager)


@router.post("/sessions/{session_id}/stop", response_model=PaperSessionResponse)
def stop_paper_session(
    session_id: str,
    state_manager: PaperStateManager = Depends(get_paper_state_manager),
):
    """Stops execution for a paper trading session."""
    return _transition_session_state(session_id, SessionStatus.STOPPED, state_manager)


@router.post("/sessions/{session_id}/close", response_model=PaperSessionResponse)
def close_paper_session(
    session_id: str,
    state_manager: PaperStateManager = Depends(get_paper_state_manager),
):
    """Permanently closes a stopped paper trading session."""
    return _transition_session_state(session_id, SessionStatus.CLOSED, state_manager)
