"""
MIRAI — Integrated Paper Trading Engine (M14)
Coordinates paper trading sessions, market data streaming/replay,
strategy signal generation, multi-pillar investment decision evaluation,
dynamic risk limits, virtual order execution, portfolio/account state tracking,
and continuous performance reporting.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from src.utils.logger import get_logger
from src.paper_trading.paper_trading_schemas import (
    PaperTradingMode,
    SessionConfig,
    SessionStatus,
)
from src.paper_trading.trading_session import TradingSession
from src.paper_trading.paper_account import PaperAccount
from src.paper_trading.paper_portfolio import PaperPortfolio
from src.paper_trading.paper_order_manager import PaperOrderManager
from src.paper_trading.paper_trade_manager import PaperTradeManager
from src.paper_trading.market_data_adapter import MarketDataAdapter
from src.paper_trading.paper_performance import PaperPerformanceTracker
from src.paper_trading.paper_state_manager import PaperStateManager
from src.paper_trading.paper_trading_report import PaperTradingReport

from src.execution.execution_schemas import (
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
)
from src.execution.execution_engine import IntelligentExecutionEngine
from src.strategies.base_strategy import SignalAction
from src.decision.decision_schemas import DecisionInput, DecisionVerdict, RiskStatus

logger = get_logger("PaperTradingEngine")


class PaperTradingEngine:
    """
    Main orchestration engine for MIRAI Paper Trading (M14).
    Integrates upstream signals, decisions, and risk controls with execution and accounting.
    """

    def __init__(
        self,
        session_config: Optional[SessionConfig] = None,
        account: Optional[PaperAccount] = None,
        portfolio: Optional[PaperPortfolio] = None,
        market_adapter: Optional[MarketDataAdapter] = None,
        order_manager: Optional[PaperOrderManager] = None,
        trade_manager: Optional[PaperTradeManager] = None,
        performance_tracker: Optional[PaperPerformanceTracker] = None,
        state_manager: Optional[PaperStateManager] = None,
        execution_engine: Optional[IntelligentExecutionEngine] = None,
        strategy: Optional[Any] = None,
        decision_engine: Optional[Any] = None,
        risk_engine: Optional[Any] = None,
        auto_persist: bool = True,
        db_path: str = "data/paper_trading.db",
    ):
        self.session = TradingSession(session_config or SessionConfig())
        self.account = account or PaperAccount(
            account_id=f"ACC_{self.session.session_id}",
            initial_capital=self.session.config.initial_capital,
        )
        self.portfolio = portfolio or PaperPortfolio()
        self.market_adapter = market_adapter or MarketDataAdapter()
        self.execution_engine = execution_engine or IntelligentExecutionEngine()
        self.order_manager = order_manager or PaperOrderManager(
            account=self.account,
            execution_engine=self.execution_engine,
        )
        self.trade_manager = trade_manager or PaperTradeManager()
        self.performance_tracker = performance_tracker or PaperPerformanceTracker(
            initial_capital=self.account.initial_capital
        )
        self.state_manager = state_manager or PaperStateManager(db_path=db_path)

        # Intelligence & strategy hooks
        self.strategy = strategy
        self.decision_engine = decision_engine
        self.risk_engine = risk_engine

        self.auto_persist = auto_persist
        self.circuit_breaker_events: List[Dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Session Controls
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Starts the paper trading session."""
        self.session.start()
        logger.info("PaperTradingEngine session %s started.", self.session.session_id)
        if self.auto_persist:
            self._persist_current_state()

    def pause(self) -> None:
        """Pauses the paper trading session."""
        self.session.pause()
        self.market_adapter.pause()
        logger.info("PaperTradingEngine session %s paused.", self.session.session_id)
        if self.auto_persist:
            self._persist_current_state()

    def resume(self) -> None:
        """Resumes a paused paper trading session."""
        self.session.resume()
        self.market_adapter.resume()
        logger.info("PaperTradingEngine session %s resumed.", self.session.session_id)
        if self.auto_persist:
            self._persist_current_state()

    def stop(self) -> None:
        """Stops trading in this session."""
        if not self.session.is_terminal:
            self.session.stop()
        self.market_adapter.stop()
        logger.info("PaperTradingEngine session %s stopped.", self.session.session_id)
        if self.auto_persist:
            self._persist_current_state()

    def close(self) -> None:
        """Permanently closes the session."""
        if self.session.status not in (SessionStatus.STOPPED, SessionStatus.CLOSED):
            self.stop()
        if self.session.status != SessionStatus.CLOSED:
            self.session.close()
        self.market_adapter.stop()
        logger.info("PaperTradingEngine session %s closed.", self.session.session_id)
        if self.auto_persist:
            self._persist_current_state()

    def emergency_stop(self, reason: str = "Emergency stop manually activated") -> None:
        """
        Immediately halts all trading activity, locks the circuit breaker to HALTED,
        and cancels any pending open orders.
        """
        self.account.circuit_breaker_state = "HALTED"
        if self.risk_engine and hasattr(self.risk_engine, "trip_circuit_breaker"):
            self.risk_engine.trip_circuit_breaker(reason)

        open_orders = self.order_manager.get_open_orders()
        for ord_obj in open_orders:
            self.order_manager.cancel_order(ord_obj.order_id, reason="Emergency halt")

        event = {
            "timestamp": pd.Timestamp.now().isoformat(),
            "event_type": "EMERGENCY_HALT",
            "description": reason,
        }
        self.circuit_breaker_events.append(event)
        logger.critical("[%s] EMERGENCY STOP ACTIVATED: %s", self.session.session_id, reason)

        if self.auto_persist:
            self._persist_current_state()

    # -------------------------------------------------------------------------
    # Stepping & Replay Loop
    # -------------------------------------------------------------------------

    def step_bar(self) -> Optional[pd.Series]:
        """
        Executes a single market bar processing cycle:
        1. Emits next chronological bar from MarketDataAdapter.
        2. Marks active portfolio positions to market.
        3. Checks intrabar stop-loss / take-profit exits.
        4. If strategy attached: generates signal, evaluates decision & risk, submits orders.
        5. Updates account valuation and performance snapshot.
        6. Persists session state if auto_persist is True.
        """
        if not self.session.is_active:
            logger.debug("Session %s is not RUNNING. Cannot step.", self.session.session_id)
            return None

        if self.account.circuit_breaker_state == "HALTED":
            logger.warning("[%s] Account is HALTED by circuit breaker. Order processing blocked.", self.session.session_id)
            return None

        next_data = self.market_adapter.get_next_bar()
        if next_data is None:
            logger.info("[%s] Replay stream complete. Stopping session.", self.session.session_id)
            self.stop()
            return None

        current_bar, history_slice = next_data

        # Determine symbol and bar timestamp
        symbol = str(
            current_bar.get("symbol", self.session.config.symbols[0] if self.session.config.symbols else "NIFTY")
        ).upper()

        if isinstance(current_bar.name, pd.Timestamp):
            bar_ts = current_bar.name
        else:
            ts_val = current_bar.get("timestamp", pd.Timestamp.now())
            bar_ts = pd.to_datetime(ts_val)

        close_price = float(current_bar.get("close", current_bar.get("price", 100.0)))
        high_price = float(current_bar.get("high", close_price))
        low_price = float(current_bar.get("low", close_price))
        open_price = float(current_bar.get("open", close_price))

        # 1. Update Portfolio Valuation with current mark prices
        self.portfolio.mark_prices({symbol: close_price})
        self.account.update_market_valuation(self.portfolio.total_market_value)

        # 2. Check Intrabar Stop-Loss and Take-Profit Exits
        self._check_intrabar_exits(
            symbol=symbol,
            high_price=high_price,
            low_price=low_price,
            open_price=open_price,
            bar_ts=bar_ts,
            current_bar=current_bar,
        )

        # 3. Strategy Signal Evaluation & Decision Execution
        if self.strategy is not None:
            self._evaluate_signals_and_execute(
                symbol=symbol,
                history_slice=history_slice,
                current_bar=current_bar,
                close_price=close_price,
                bar_ts=bar_ts,
            )

        # 4. Final Mark-to-Market after orders
        self.portfolio.mark_prices({symbol: close_price})
        self.account.update_market_valuation(self.portfolio.total_market_value)

        # 5. Record Performance Snapshot
        self.performance_tracker.record_snapshot(
            timestamp=bar_ts,
            equity=self.account.total_equity,
            cash=self.account.total_cash,
            portfolio_market_value=self.portfolio.total_market_value,
            realized_pnl=self.account.realized_pnl,
            unrealized_pnl=self.portfolio.total_unrealized_pnl,
        )

        # 6. Session Accounting
        self.session.record_bar_processed()
        self.session.orders_count = len(self.order_manager.get_all_orders())
        self.session.trades_count = len(self.trade_manager.get_all_trades())

        # 7. Persistence
        if self.auto_persist:
            self._persist_current_state()

        return current_bar

    def run_replay(self, num_bars: Optional[int] = None) -> int:
        """
        Executes continuous replay loop for num_bars or until data exhaustion.
        Returns the total number of bars successfully processed in this run.
        """
        if self.session.status == SessionStatus.CREATED:
            self.start()

        bars_run = 0
        while self.session.is_active and self.market_adapter.has_next_bar():
            if num_bars is not None and bars_run >= num_bars:
                break
            bar = self.step_bar()
            if bar is None:
                break
            bars_run += 1

        if not self.market_adapter.has_next_bar() and not self.session.is_terminal:
            self.stop()

        logger.info("[%s] Replay run finished: %d bars processed.", self.session.session_id, bars_run)
        return bars_run

    # -------------------------------------------------------------------------
    # Internal Handlers: Intrabar Exits & Signal Execution
    # -------------------------------------------------------------------------

    def _check_intrabar_exits(
        self,
        symbol: str,
        high_price: float,
        low_price: float,
        open_price: float,
        bar_ts: pd.Timestamp,
        current_bar: pd.Series,
    ) -> None:
        """
        Checks active positions against stop-loss and take-profit thresholds.
        Executes immediate protective market exits if breached.
        """
        pos = self.portfolio.get_position(symbol)
        if not pos or pos.units <= 0:
            return

        exit_triggered = False
        exit_reason = ""
        target_exit_price = pos.current_price

        # Check Stop Loss
        if pos.stop_loss is not None and low_price <= pos.stop_loss:
            exit_triggered = True
            exit_reason = "STOP_LOSS_HIT"
            target_exit_price = min(pos.stop_loss, open_price)

        # Check Take Profit (if stop loss was not triggered)
        elif pos.take_profit is not None and high_price >= pos.take_profit:
            exit_triggered = True
            exit_reason = "TAKE_PROFIT_HIT"
            target_exit_price = max(pos.take_profit, open_price)

        if exit_triggered:
            logger.info(
                "[%s] Intrabar exit triggered for %s (%s at %.2f)",
                self.session.session_id, symbol, exit_reason, target_exit_price
            )
            req = OrderRequest(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=pos.units,
                order_type=OrderType.MARKET,
                created_at=bar_ts,
                strategy_id="INTRABAR_PROTECTION",
            )
            order = self.order_manager.place_order(req, current_bar=current_bar)
            if order.status == OrderStatus.FILLED:
                units_sold, cost_basis = self.portfolio.reduce_or_close_position(
                    symbol=symbol,
                    units_to_sell=order.filled_quantity,
                )
                trans_cost = getattr(order, "total_transaction_cost", getattr(order, "total_transaction_costs", 0.0))
                slippage_cost = getattr(order, "total_slippage", getattr(order, "total_slippage_cost", 0.0))

                self.account.process_sell_fill(
                    symbol=symbol,
                    units=units_sold,
                    execution_price=order.average_price,
                    total_transaction_cost=trans_cost,
                    cost_basis=cost_basis,
                )
                self.trade_manager.close_trade(
                    symbol=symbol,
                    exit_price=order.average_price,
                    exit_time=bar_ts,
                    exit_costs=trans_cost,
                    exit_slippage=slippage_cost,
                    exit_reason=exit_reason,
                    bars_held=pos.bars_held,
                )

    def _evaluate_signals_and_execute(
        self,
        symbol: str,
        history_slice: pd.DataFrame,
        current_bar: pd.Series,
        close_price: float,
        bar_ts: pd.Timestamp,
    ) -> None:
        """
        Evaluates strategy signals, applies investment decision rules,
        enforces dynamic risk limits, and executes orders.
        """
        # Circuit Breaker state policy
        cb_state = self.account.circuit_breaker_state
        if cb_state == "HALTED":
            return

        try:
            signal = self.strategy.generate_signal(history_slice, symbol=symbol)
        except Exception as e:
            logger.warning("[%s] Strategy signal generation failed: %s", self.session.session_id, e)
            return

        if signal is None:
            return

        sig_action = getattr(signal, "signal", None) or getattr(signal, "action", None)
        if isinstance(sig_action, str):
            sig_action_upper = sig_action.upper()
        else:
            sig_action_upper = getattr(sig_action, "value", str(sig_action)).upper()

        # Handle SELL / SHORT exits
        if sig_action_upper in (SignalAction.SELL, "SHORT", "STRONG_SELL"):
            pos = self.portfolio.get_position(symbol)
            if pos and pos.units > 0:
                req = OrderRequest(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=pos.units,
                    order_type=OrderType.MARKET,
                    created_at=bar_ts,
                    strategy_id=getattr(self.strategy, "strategy_name", "STRATEGY"),
                )
                order = self.order_manager.place_order(req, current_bar=current_bar)
                if order.status == OrderStatus.FILLED:
                    units_sold, cost_basis = self.portfolio.reduce_or_close_position(
                        symbol=symbol,
                        units_to_sell=order.filled_quantity,
                    )
                    trans_cost = getattr(order, "total_transaction_cost", getattr(order, "total_transaction_costs", 0.0))
                    slippage_cost = getattr(order, "total_slippage", getattr(order, "total_slippage_cost", 0.0))

                    self.account.process_sell_fill(
                        symbol=symbol,
                        units=units_sold,
                        execution_price=order.average_price,
                        total_transaction_cost=trans_cost,
                        cost_basis=cost_basis,
                    )
                    self.trade_manager.close_trade(
                        symbol=symbol,
                        exit_price=order.average_price,
                        exit_time=bar_ts,
                        exit_costs=trans_cost,
                        exit_slippage=slippage_cost,
                        exit_reason="STRATEGY_EXIT_SIGNAL",
                        bars_held=pos.bars_held,
                    )
            return

        # Handle BUY / LONG entries
        if sig_action_upper in (SignalAction.BUY, "LONG", "STRONG_BUY"):
            # RESTRICTED mode forbids new long entries
            if cb_state == "RESTRICTED":
                logger.info("[%s] Circuit breaker RESTRICTED: skipping BUY signal for %s", self.session.session_id, symbol)
                return

            # Check Decision Engine if available
            is_approved = True
            suggested_stop = getattr(signal, "suggested_stop_loss", None)
            suggested_tp = getattr(signal, "suggested_take_profit", None)

            if self.decision_engine is not None:
                inp = DecisionInput(
                    symbol=symbol,
                    timestamp=bar_ts,
                    current_price=close_price,
                    strategy_signal=signal,
                    pipeline_id="pipeline_b_nifty",
                )
                if self.risk_engine is not None:
                    decision = self.decision_engine.make_decision_with_risk(
                        inp=inp,
                        risk_engine=self.risk_engine,
                        current_capital=self.account.total_equity,
                    )
                    is_approved = (
                        decision.verdict == DecisionVerdict.YES
                        and decision.risk_status == RiskStatus.RISK_APPROVED
                    )
                else:
                    decision = self.decision_engine.make_decision(inp)
                    is_approved = (decision.verdict == DecisionVerdict.YES)

                if decision.suggested_stop_loss is not None:
                    suggested_stop = decision.suggested_stop_loss
                if decision.suggested_take_profit is not None:
                    suggested_tp = decision.suggested_take_profit

            if not is_approved:
                logger.debug("[%s] Signal for %s not approved by decision/risk engine.", self.session.session_id, symbol)
                return

            # Determine position sizing
            target_notional = self.account.buying_power * 0.10
            units = int(target_notional // close_price) if close_price > 0 else 0

            # CAUTION mode scales sizing by 50%
            if cb_state == "CAUTION":
                units = max(1, units // 2)

            max_affordable = int(self.account.buying_power // (close_price * 1.002)) if close_price > 0 else 0
            units = min(units, max_affordable)

            if units <= 0:
                logger.debug("[%s] Sized units is 0 for %s. Insufficient buying power.", self.session.session_id, symbol)
                return

            req = OrderRequest(
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=units,
                order_type=OrderType.MARKET,
                created_at=bar_ts,
                strategy_id=getattr(self.strategy, "strategy_name", "STRATEGY"),
            )
            order = self.order_manager.place_order(req, current_bar=current_bar)
            if order.status == OrderStatus.FILLED:
                trans_cost = getattr(order, "total_transaction_cost", getattr(order, "total_transaction_costs", 0.0))
                slippage_cost = getattr(order, "total_slippage", getattr(order, "total_slippage_cost", 0.0))

                self.account.process_buy_fill(
                    symbol=symbol,
                    units=order.filled_quantity,
                    execution_price=order.average_price,
                    total_transaction_cost=trans_cost,
                )
                self.portfolio.add_or_update_position(
                    symbol=symbol,
                    units=order.filled_quantity,
                    entry_price=order.average_price,
                    entry_time=bar_ts,
                    stop_loss=suggested_stop,
                    take_profit=suggested_tp,
                )
                self.trade_manager.open_trade(
                    symbol=symbol,
                    quantity=order.filled_quantity,
                    entry_price=order.average_price,
                    entry_time=bar_ts,
                    entry_costs=trans_cost,
                    entry_slippage=slippage_cost,
                    direction="LONG",
                )

    # -------------------------------------------------------------------------
    # Persistence & Reporting
    # -------------------------------------------------------------------------

    def _persist_current_state(self) -> None:
        """Persists session, account, portfolio, orders, and trades to SQLite."""
        try:
            self.state_manager.save_session_state(
                session=self.session,
                account=self.account,
                portfolio=self.portfolio,
                orders=self.order_manager.get_all_orders(),
                trades=self.trade_manager.get_all_trades(),
            )
        except Exception as e:
            logger.error("[%s] State persistence failed: %s", self.session.session_id, e)

    def generate_report(self) -> PaperTradingReport:
        """Generates institutional-grade paper trading performance report."""
        closed_trades = self.trade_manager.get_closed_trades()
        metrics = self.performance_tracker.calculate_metrics(trades=closed_trades)

        all_orders = self.order_manager.get_all_orders()
        rejected_count = sum(1 for o in all_orders if o.status == OrderStatus.REJECTED)

        total_tx_costs = sum(
            getattr(o, "total_transaction_cost", getattr(o, "total_transaction_costs", 0.0))
            for o in all_orders
        )
        total_slippage = sum(
            getattr(o, "total_slippage", getattr(o, "total_slippage_cost", 0.0))
            for o in all_orders
        )

        open_pos_dicts = [p.to_dict() for p in self.portfolio.get_all_positions()]

        return PaperTradingReport(
            session_id=self.session.session_id,
            session_name=self.session.config.session_name,
            mode=self.session.config.mode.value,
            status=self.session.status.value,
            start_time=self.session.start_time,
            end_time=self.session.end_time,
            initial_capital=self.account.initial_capital,
            final_equity=self.account.total_equity,
            final_cash=self.account.total_cash,
            total_return_pct=float(metrics.get("total_return_pct", 0.0)),
            realized_pnl=self.account.realized_pnl,
            unrealized_pnl=self.portfolio.total_unrealized_pnl,
            max_drawdown_pct=float(metrics.get("max_drawdown_pct", 0.0)),
            win_rate_pct=float(metrics.get("win_rate_pct", 0.0)),
            profit_factor=float(metrics.get("profit_factor", 0.0)),
            total_trades=len(closed_trades),
            winning_trades=int(metrics.get("winning_trades", 0)),
            losing_trades=int(metrics.get("losing_trades", 0)),
            total_orders=len(all_orders),
            rejected_orders=rejected_count,
            total_transaction_costs=total_tx_costs,
            total_slippage_cost=total_slippage,
            open_positions=open_pos_dicts,
            circuit_breaker_events=list(self.circuit_breaker_events),
        )

    def restore_from_db(self, session_id: str) -> bool:
        """Restores state from an existing database record."""
        restored = self.state_manager.restore_session_state(session_id)
        if not restored:
            return False

        sess, acc, port, orders, trades = restored
        self.session = sess
        self.account = acc
        self.portfolio = port

        # Re-attach order and trade managers
        self.order_manager = PaperOrderManager(
            account=self.account,
            execution_engine=self.execution_engine,
        )
        for ord_obj in orders:
            self.order_manager._orders[ord_obj.order_id] = ord_obj

        self.trade_manager = PaperTradeManager()
        for t in trades:
            self.trade_manager._trades.append(t)
            if not t.is_closed:
                self.trade_manager._active_trades[t.symbol] = t

        return True
