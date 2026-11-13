"""
MIRAI — Paper State Manager & SQLite Persistence (M14)
Provides transactional ACID persistence and crash recovery for paper trading
sessions, accounts, positions, orders, and trades.
Guarantees state consistency across application restarts.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import sqlite3
import pandas as pd

from src.utils.logger import get_logger
from src.paper_trading.paper_trading_schemas import (
    PaperPosition,
    PaperAccountState,
    SessionConfig,
    SessionStatus,
)
from src.paper_trading.paper_account import PaperAccount
from src.paper_trading.paper_portfolio import PaperPortfolio
from src.paper_trading.trading_session import TradingSession
from src.execution.execution_schemas import (
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
)
from src.backtesting.trade_simulator import Trade

logger = get_logger("PaperStateManager")

SCHEMA_VERSION = 1


class PaperStateManager:
    """
    Manages persistent SQLite storage for paper trading sessions.
    Supports transactional atomic saves, restart recovery, and audit trails.
    """

    def __init__(self, db_path: str = "data/paper_trading.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns SQLite connection with foreign keys and row factory enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Creates versioned database schema if not present."""
        with self._get_connection() as conn:
            conn.executescript(f"""
                CREATE TABLE IF NOT EXISTS schema_meta (
                    version INTEGER PRIMARY KEY,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    initial_capital REAL NOT NULL,
                    symbols TEXT NOT NULL,
                    start_time TEXT,
                    end_time TEXT,
                    config_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS account_states (
                    account_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    initial_capital REAL NOT NULL,
                    available_cash REAL NOT NULL,
                    reserved_cash REAL NOT NULL,
                    invested_capital REAL NOT NULL,
                    portfolio_market_value REAL NOT NULL,
                    total_equity REAL NOT NULL,
                    realized_pnl REAL NOT NULL,
                    unrealized_pnl REAL NOT NULL,
                    circuit_breaker_state TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (account_id, session_id),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS positions (
                    session_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    units INTEGER NOT NULL,
                    average_entry_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    cost_basis REAL NOT NULL,
                    market_value REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    entry_time TEXT NOT NULL,
                    bars_held INTEGER NOT NULL,
                    trade_id TEXT,
                    PRIMARY KEY (session_id, symbol),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_quantity INTEGER NOT NULL,
                    filled_quantity INTEGER NOT NULL,
                    remaining_quantity INTEGER NOT NULL,
                    average_price REAL NOT NULL,
                    total_cost REAL NOT NULL,
                    rejection_reason TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    gross_pnl REAL NOT NULL,
                    net_pnl REAL NOT NULL,
                    exit_reason TEXT NOT NULL,
                    bars_held INTEGER NOT NULL,
                    is_closed INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                INSERT OR IGNORE INTO schema_meta (version, updated_at)
                VALUES ({SCHEMA_VERSION}, datetime('now'));
            """)
            conn.commit()

    def save_session_state(
        self,
        session: TradingSession,
        account: PaperAccount,
        portfolio: PaperPortfolio,
        orders: List[Order],
        trades: List[Trade],
    ) -> None:
        """
        Transactionally persists full session state (atomic commit).
        """
        sess_dict = session.to_dict()
        acc_state = account.get_state()
        conn = self._get_connection()

        try:
            with conn:
                # 1. Upsert session
                conn.execute(
                    """
                    INSERT INTO sessions (
                        session_id, name, mode, status, initial_capital,
                        symbols, start_time, end_time, config_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        status = excluded.status,
                        end_time = excluded.end_time;
                    """,
                    (
                        session.session_id,
                        session.config.session_name,
                        session.config.mode.value,
                        session.status.value,
                        session.config.initial_capital,
                        ",".join(session.config.symbols),
                        sess_dict["start_time"],
                        sess_dict["end_time"],
                        json.dumps(sess_dict),
                    ),
                )

                # 2. Upsert account state
                conn.execute(
                    """
                    INSERT INTO account_states (
                        account_id, session_id, initial_capital, available_cash,
                        reserved_cash, invested_capital, portfolio_market_value,
                        total_equity, realized_pnl, unrealized_pnl,
                        circuit_breaker_state, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(account_id, session_id) DO UPDATE SET
                        available_cash = excluded.available_cash,
                        reserved_cash = excluded.reserved_cash,
                        invested_capital = excluded.invested_capital,
                        portfolio_market_value = excluded.portfolio_market_value,
                        total_equity = excluded.total_equity,
                        realized_pnl = excluded.realized_pnl,
                        unrealized_pnl = excluded.unrealized_pnl,
                        circuit_breaker_state = excluded.circuit_breaker_state,
                        last_updated = excluded.last_updated;
                    """,
                    (
                        account.account_id,
                        session.session_id,
                        acc_state.initial_capital,
                        acc_state.available_cash,
                        acc_state.reserved_cash,
                        acc_state.invested_capital,
                        acc_state.portfolio_market_value,
                        acc_state.total_equity,
                        acc_state.realized_pnl,
                        acc_state.unrealized_pnl,
                        acc_state.circuit_breaker_state,
                        acc_state.last_updated.isoformat(),
                    ),
                )

                # 3. Synchronize open positions
                conn.execute("DELETE FROM positions WHERE session_id = ?", (session.session_id,))
                for pos in portfolio.get_all_positions():
                    conn.execute(
                        """
                        INSERT INTO positions (
                            session_id, symbol, units, average_entry_price,
                            current_price, cost_basis, market_value, stop_loss,
                            take_profit, entry_time, bars_held, trade_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            session.session_id,
                            pos.symbol,
                            pos.units,
                            pos.average_entry_price,
                            pos.current_price,
                            pos.cost_basis,
                            pos.market_value,
                            pos.stop_loss,
                            pos.take_profit,
                            pos.entry_time.isoformat() if hasattr(pos.entry_time, "isoformat") else str(pos.entry_time),
                            pos.bars_held,
                            pos.trade_id,
                        ),
                    )

                # 4. Upsert orders
                for order in orders:
                    conn.execute(
                        """
                        INSERT INTO orders (
                            order_id, session_id, symbol, side, order_type,
                            status, requested_quantity, filled_quantity,
                            remaining_quantity, average_price, total_cost,
                            rejection_reason, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(order_id) DO UPDATE SET
                            status = excluded.status,
                            filled_quantity = excluded.filled_quantity,
                            remaining_quantity = excluded.remaining_quantity,
                            average_price = excluded.average_price,
                            total_cost = excluded.total_cost,
                            rejection_reason = excluded.rejection_reason;
                        """,
                        (
                            order.order_id,
                            session.session_id,
                            order.symbol,
                            order.side.value,
                            order.order_type.value,
                            order.status.value,
                            order.request.quantity,
                            order.filled_quantity,
                            order.remaining_quantity,
                            order.average_price,
                            order.total_transaction_cost,
                            order.rejection_reason,
                            order.request.created_at.isoformat() if hasattr(order.request.created_at, "isoformat") else str(order.request.created_at),
                        ),
                    )

                # 5. Upsert trades
                for trade in trades:
                    conn.execute(
                        """
                        INSERT INTO trades (
                            trade_id, session_id, symbol, direction, quantity,
                            entry_price, exit_price, entry_time, exit_time,
                            gross_pnl, net_pnl, exit_reason, bars_held, is_closed
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(trade_id) DO UPDATE SET
                            exit_price = excluded.exit_price,
                            exit_time = excluded.exit_time,
                            gross_pnl = excluded.gross_pnl,
                            net_pnl = excluded.net_pnl,
                            exit_reason = excluded.exit_reason,
                            bars_held = excluded.bars_held,
                            is_closed = excluded.is_closed;
                        """,
                        (
                            trade.trade_id,
                            session.session_id,
                            trade.symbol,
                            trade.direction,
                            trade.quantity,
                            trade.entry_price,
                            trade.exit_price,
                            trade.entry_time.isoformat() if hasattr(trade.entry_time, "isoformat") else str(trade.entry_time),
                            trade.exit_time.isoformat() if trade.exit_time and hasattr(trade.exit_time, "isoformat") else (str(trade.exit_time) if trade.exit_time else None),
                            trade.gross_pnl,
                            trade.net_pnl,
                            trade.exit_reason,
                            trade.bars_held,
                            1 if trade.is_closed else 0,
                        ),
                    )

            logger.info("Persisted state for session %s (orders: %d, positions: %d)", session.session_id, len(orders), len(portfolio.get_all_positions()))
        finally:
            conn.close()

    def restore_session_state(
        self,
        session_id: str,
    ) -> Optional[Tuple[TradingSession, PaperAccount, PaperPortfolio, List[Order], List[Trade]]]:
        """
        Recovers and restores consistent state for a given session_id.
        Returns None if session does not exist.
        """
        conn = self._get_connection()
        try:
            # 1. Load session
            sess_row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            if not sess_row:
                return None

            cfg_dict = json.loads(sess_row["config_json"])
            cfg = SessionConfig(
                session_id=session_id,
                session_name=sess_row["name"],
                initial_capital=float(sess_row["initial_capital"]),
                symbols=sess_row["symbols"].split(","),
            )
            session = TradingSession(cfg)
            session.status = SessionStatus(sess_row["status"])
            if sess_row["start_time"]:
                session.start_time = pd.Timestamp(sess_row["start_time"])
            if sess_row["end_time"]:
                session.end_time = pd.Timestamp(sess_row["end_time"])

            # 2. Load account state
            acc_row = conn.execute("SELECT * FROM account_states WHERE session_id = ?", (session_id,)).fetchone()
            account = PaperAccount(
                account_id=acc_row["account_id"] if acc_row else "RESTORED_ACC",
                initial_capital=float(acc_row["initial_capital"]) if acc_row else cfg.initial_capital,
            )
            if acc_row:
                account.available_cash = float(acc_row["available_cash"])
                account.reserved_cash = float(acc_row["reserved_cash"])
                account.invested_capital = float(acc_row["invested_capital"])
                account.portfolio_market_value = float(acc_row["portfolio_market_value"])
                account.realized_pnl = float(acc_row["realized_pnl"])
                account.unrealized_pnl = float(acc_row["unrealized_pnl"])
                account.circuit_breaker_state = acc_row["circuit_breaker_state"]
                account.last_updated = pd.Timestamp(acc_row["last_updated"])

            # 3. Load positions
            portfolio = PaperPortfolio()
            pos_rows = conn.execute("SELECT * FROM positions WHERE session_id = ?", (session_id,)).fetchall()
            for r in pos_rows:
                portfolio.add_or_update_position(
                    symbol=r["symbol"],
                    units=int(r["units"]),
                    entry_price=float(r["average_entry_price"]),
                    entry_time=pd.Timestamp(r["entry_time"]),
                    stop_loss=float(r["stop_loss"]) if r["stop_loss"] is not None else None,
                    take_profit=float(r["take_profit"]) if r["take_profit"] is not None else None,
                    trade_id=r["trade_id"],
                )
                pos = portfolio.get_position(r["symbol"])
                if pos:
                    pos.update_price(float(r["current_price"]))
                    pos.bars_held = int(r["bars_held"])

            # 4. Load orders
            order_rows = conn.execute("SELECT * FROM orders WHERE session_id = ?", (session_id,)).fetchall()
            orders: List[Order] = []
            for r in order_rows:
                req = OrderRequest(
                    order_id=r["order_id"],
                    symbol=r["symbol"],
                    side=OrderSide(r["side"]),
                    order_type=OrderType(r["order_type"]),
                    quantity=int(r["requested_quantity"]),
                    created_at=pd.Timestamp(r["created_at"]),
                )
                ord_obj = Order(request=req)
                ord_obj.status = OrderStatus(r["status"])
                ord_obj.filled_quantity = int(r["filled_quantity"])
                ord_obj.remaining_quantity = int(r["remaining_quantity"])
                ord_obj.average_price = float(r["average_price"])
                ord_obj.total_transaction_cost = float(r["total_cost"])
                ord_obj.rejection_reason = r["rejection_reason"]
                orders.append(ord_obj)

            # 5. Load trades
            trade_rows = conn.execute("SELECT * FROM trades WHERE session_id = ?", (session_id,)).fetchall()
            trades: List[Trade] = []
            for r in trade_rows:
                t = Trade(
                    trade_id=r["trade_id"],
                    symbol=r["symbol"],
                    direction=r["direction"],
                    quantity=int(r["quantity"]),
                    entry_time=pd.Timestamp(r["entry_time"]),
                    entry_price=float(r["entry_price"]),
                    entry_costs=0.0,
                    entry_slippage=0.0,
                    exit_time=pd.Timestamp(r["exit_time"]) if r["exit_time"] else None,
                    exit_price=float(r["exit_price"]) if r["exit_price"] is not None else None,
                    gross_pnl=float(r["gross_pnl"]),
                    net_pnl=float(r["net_pnl"]),
                    exit_reason=r["exit_reason"],
                    bars_held=int(r["bars_held"]),
                    is_closed=bool(r["is_closed"]),
                )
                trades.append(t)

            logger.info("Restored session %s from SQLite (equity: %.2f)", session_id, account.total_equity)
            return session, account, portfolio, orders, trades
        finally:
            conn.close()

    def reset_database(self, confirm: bool = False) -> bool:
        """
        Explicitly clears all paper trading history from the database.
        Requires confirm=True to avoid accidental data loss.
        """
        if not confirm:
            logger.warning("reset_database() called without confirm=True. Operation aborted.")
            return False

        with self._get_connection() as conn:
            conn.execute("DELETE FROM trades;")
            conn.execute("DELETE FROM orders;")
            conn.execute("DELETE FROM positions;")
            conn.execute("DELETE FROM account_states;")
            conn.execute("DELETE FROM sessions;")
            conn.commit()

        logger.info("Paper trading database successfully reset.")
        return True
