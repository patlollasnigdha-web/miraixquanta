"""
MIRAI — Historical Backtesting Engine (M13)
Coordinates bar-by-bar chronological execution across Market Data,
Strategies, Investment Decisions, Risk Management, and Execution Simulation.
Strictly prevents lookahead bias and ensures full pipeline integrity.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import uuid
import numpy as np
import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.strategies.base_strategy import BaseStrategy, SignalAction, StrategySignal
from src.decision.decision_schemas import (
    DecisionInput,
    DecisionVerdict,
    DisplayLabel,
    RiskStatus,
    InvestmentDecision,
    DecisionExplanation,
)
from src.decision.decision_engine import InvestmentDecisionEngine
from src.risk_management.risk_engine import RiskManagementEngine
from src.execution.execution_engine import IntelligentExecutionEngine
from src.execution.execution_schemas import Order, OrderSide, OrderStatus, OrderType
from src.backtesting.portfolio_simulator import PortfolioSimulator
from src.backtesting.trade_simulator import Trade
from src.backtesting.performance_metrics import (
    calculate_performance_metrics,
    compute_drawdown_curve,
)
from src.backtesting.benchmark_comparison import BenchmarkComparator
from src.backtesting.backtest_report import BacktestReport

logger = get_logger("BacktestEngine")


class BacktestEngine:
    """
    Chronological historical simulation engine for MIRAI.
    Simulates execution with realistic slippage, transaction costs,
    intrabar stop-loss exits, and portfolio equity tracking.
    """

    def __init__(
        self,
        initial_capital: Optional[float] = None,
        execution_engine: Optional[IntelligentExecutionEngine] = None,
        risk_engine: Optional[RiskManagementEngine] = None,
        decision_engine: Optional[InvestmentDecisionEngine] = None,
        risk_free_rate: float = 0.065,
    ):
        cfg = get_config()
        self.initial_capital = (
            initial_capital
            if initial_capital is not None
            else cfg.get("backtesting.initial_capital", 1_000_000.0)
        )
        self.risk_free_rate = cfg.get("backtesting.risk_free_rate", risk_free_rate)
        self.execution_engine = execution_engine or IntelligentExecutionEngine()
        self.risk_engine = risk_engine or RiskManagementEngine(initial_capital=self.initial_capital)
        self.decision_engine = decision_engine or InvestmentDecisionEngine()
        self.benchmark_comparator = BenchmarkComparator(risk_free_rate=self.risk_free_rate)

    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy: Any,
        symbol: str = "TCS",
        pipeline_id: str = "pipeline_b_nifty",
        benchmark_series: Optional[pd.Series] = None,
        use_decision_engine: bool = True,
        use_risk_engine: bool = True,
        backtest_id: Optional[str] = None,
    ) -> BacktestReport:
        """
        Executes a complete chronological bar-by-bar backtest.
        Strictly enforces no-lookahead by slicing data up to bar i.
        """
        if data.empty or len(data) < 5:
            raise ValueError("Backtest dataset must contain at least 5 observations.")

        # Pipeline A Isolation Check
        if pipeline_id == "pipeline_a_fi2010" or "lob_feature_0" in data.columns:
            logger.info("Executing FI-2010 microstructure event evaluation.")

        bt_id = backtest_id or f"BT_{uuid.uuid4().hex[:8].upper()}"
        start_ts = data.index[0]
        end_ts = data.index[-1]
        total_bars = len(data)

        # Initialize portfolio state tracker
        portfolio = PortfolioSimulator(initial_capital=self.initial_capital)
        executed_orders: List[Order] = []
        limitations: List[str] = [
            "Intrabar stop-loss execution uses conservative assumptions (gap-down penalty and stop priority over take-profit).",
            "Slippage is modeled using composite volatility and volume sensitivity.",
            "Transaction costs incorporate Indian NSE statutory fees (STT, Stamp Duty, GST, Exchange turnover).",
        ]

        logger.info(
            "Starting backtest %s for %s (%s): %d bars from %s to %s",
            bt_id, symbol, pipeline_id, total_bars, start_ts, end_ts
        )

        # Bar-by-bar Chronological Simulation Loop
        for i in range(total_bars):
            current_bar = data.iloc[i]
            bar_ts = data.index[i] if isinstance(data.index[i], pd.Timestamp) else pd.Timestamp(data.index[i])

            # -------------------------------------------------------------
            # STEP 1: Intrabar Stop-Loss / Take-Profit Check for Open Positions
            # -------------------------------------------------------------
            exit_signal = portfolio.check_intrabar_exits(current_bar, symbol=symbol, bar_index=i)
            if exit_signal is not None:
                exit_reason, exit_price = exit_signal
                pos = portfolio.positions.get(symbol)
                if pos and pos["units"] > 0:
                    exit_qty = pos["units"]
                    # Create simulated exit order
                    exit_decision = InvestmentDecision(
                        symbol=symbol,
                        pipeline_id=pipeline_id,
                        timestamp=bar_ts,
                        verdict=DecisionVerdict.YES,
                        display_label=DisplayLabel.SELL,
                        action_type="EXIT",
                        composite_score=0.0,
                        confidence=1.0,
                        investment_horizon="1d",
                        entry_reference_price=exit_price,
                        suggested_stop_loss=None,
                        suggested_take_profit=None,
                        factor_contributions={},
                        factor_scores={},
                        risk_status=RiskStatus.RISK_APPROVED,
                        explanation=DecisionExplanation(
                            verdict_rationale=f"Intrabar {exit_reason} executed at {exit_price:.2f}"
                        ),
                    )

                    exit_order = self.execution_engine.execute_decision(
                        decision=exit_decision,
                        current_bar=current_bar,
                        quantity=exit_qty,
                        risk_engine=None,  # Exits bypass new-entry risk blocks
                    )
                    executed_orders.append(exit_order)

                    # Update portfolio cash and trade log
                    portfolio.apply_fill(
                        order=exit_order,
                        timestamp=bar_ts,
                        bar_index=i,
                    )
                    logger.debug("[%s] Bar %d: Intrabar %s filled @ %.2f", symbol, i, exit_reason, exit_price)

            # -------------------------------------------------------------
            # STEP 2: Strategy Signal Generation (No Lookahead: data[:i+1])
            # -------------------------------------------------------------
            history_slice = data.iloc[: i + 1]
            strat_signal: Optional[StrategySignal] = None

            try:
                if hasattr(strategy, "generate_signal"):
                    strat_signal = strategy.generate_signal(history_slice, symbol=symbol)
                elif hasattr(strategy, "evaluate_market"):
                    strat_signal = strategy.evaluate_market(history_slice, symbol=symbol)
            except Exception as e:
                logger.error("Strategy error at bar %s: %s", bar_ts, str(e))
                strat_signal = None

            # -------------------------------------------------------------
            # STEP 3: Decision & Risk Evaluation
            # -------------------------------------------------------------
            if strat_signal and strat_signal.signal in (SignalAction.BUY, SignalAction.SELL):
                ref_price = float(current_bar.get("close", 100.0))

                if use_decision_engine:
                    inp = DecisionInput(
                        symbol=symbol,
                        pipeline_id=pipeline_id,
                        timestamp=bar_ts,
                        current_price=ref_price,
                        strategy_signal=strat_signal,
                    )

                    if use_risk_engine:
                        decision = self.decision_engine.make_decision_with_risk(
                            inp=inp,
                            risk_engine=self.risk_engine,
                        )
                    else:
                        decision = self.decision_engine.make_decision(inp=inp)
                else:
                    # Direct bypass into simulated decision
                    decision = InvestmentDecision(
                        symbol=symbol,
                        pipeline_id=pipeline_id,
                        timestamp=bar_ts,
                        verdict=DecisionVerdict.YES if strat_signal.signal == SignalAction.BUY else DecisionVerdict.NO,
                        display_label=DisplayLabel.BUY if strat_signal.signal == SignalAction.BUY else DisplayLabel.SELL,
                        action_type="ENTRY_LONG" if strat_signal.signal == SignalAction.BUY else "EXIT",
                        composite_score=75.0,
                        confidence=strat_signal.signal_strength,
                        investment_horizon=strat_signal.prediction_horizon,
                        entry_reference_price=strat_signal.entry_reference_price or ref_price,
                        suggested_stop_loss=strat_signal.suggested_stop_loss,
                        suggested_take_profit=strat_signal.suggested_take_profit,
                        factor_contributions={},
                        factor_scores={},
                        risk_status=RiskStatus.RISK_APPROVED if use_risk_engine else RiskStatus.RISK_PENDING,
                        explanation=DecisionExplanation(verdict_rationale="Direct strategy signal execution"),
                    )

                # -------------------------------------------------------------
                # STEP 4: Execution Simulation
                # -------------------------------------------------------------
                # If actionable, dispatch order through execution engine
                if decision.verdict == DecisionVerdict.YES and decision.action_type in ("ENTRY_LONG", "BUY"):
                    # Check if already in position to avoid over-concentration
                    if symbol not in portfolio.positions or portfolio.positions[symbol]["units"] == 0:
                        order = self.execution_engine.execute_decision(
                            decision=decision,
                            current_bar=current_bar,
                            risk_engine=self.risk_engine if use_risk_engine else None,
                        )
                        executed_orders.append(order)

                        if order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
                            portfolio.apply_fill(
                                order=order,
                                timestamp=bar_ts,
                                bar_index=i,
                                stop_loss=decision.suggested_stop_loss,
                                take_profit=decision.suggested_take_profit,
                            )
                elif decision.action_type in ("EXIT", "SELL"):
                    # Sell exit order
                    pos = portfolio.positions.get(symbol)
                    if pos and pos["units"] > 0:
                        order = self.execution_engine.execute_decision(
                            decision=decision,
                            current_bar=current_bar,
                            quantity=pos["units"],
                            risk_engine=None,
                        )
                        executed_orders.append(order)
                        if order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
                            portfolio.apply_fill(
                                order=order,
                                timestamp=bar_ts,
                                bar_index=i,
                            )

            # -------------------------------------------------------------
            # STEP 5: Mark to Market at Bar Close
            # -------------------------------------------------------------
            close_price = float(current_bar.get("close", 100.0))
            portfolio.mark_to_market({symbol: close_price}, timestamp=bar_ts)

        # -----------------------------------------------------------------
        # STEP 6: Close Any Remaining Open Positions at End of Dataset
        # -----------------------------------------------------------------
        if symbol in portfolio.positions and portfolio.positions[symbol]["units"] > 0:
            last_bar = data.iloc[-1]
            last_ts = data.index[-1]
            last_price = float(last_bar.get("close", 100.0))
            rem_units = portfolio.positions[symbol]["units"]

            end_decision = InvestmentDecision(
                symbol=symbol,
                pipeline_id=pipeline_id,
                timestamp=last_ts,
                verdict=DecisionVerdict.YES,
                display_label=DisplayLabel.SELL,
                action_type="EXIT",
                composite_score=0.0,
                confidence=1.0,
                investment_horizon="1d",
                entry_reference_price=last_price,
                suggested_stop_loss=None,
                suggested_take_profit=None,
                factor_contributions={},
                factor_scores={},
                risk_status=RiskStatus.RISK_APPROVED,
                explanation=DecisionExplanation(verdict_rationale="End of backtest period liquidating close"),
            )
            end_order = self.execution_engine.execute_decision(
                decision=end_decision,
                current_bar=last_bar,
                quantity=rem_units,
                risk_engine=None,
            )
            executed_orders.append(end_order)
            portfolio.apply_fill(end_order, timestamp=last_ts, bar_index=total_bars - 1)
            portfolio.mark_to_market({symbol: last_price}, timestamp=last_ts)

        # -----------------------------------------------------------------
        # STEP 7: Performance Analytics & Benchmark Comparison
        # -----------------------------------------------------------------
        eq_series = portfolio.get_equity_series()
        cash_series = portfolio.get_cash_series()
        dd_series, max_dd, curr_dd = compute_drawdown_curve(eq_series)

        # Performance metrics
        bench_equity = None
        if benchmark_series is not None:
            bench_equity = benchmark_series

        perf_metrics = calculate_performance_metrics(
            equity_curve=eq_series,
            trades=portfolio.trades,
            risk_free_rate=self.risk_free_rate,
            benchmark_equity=bench_equity,
        )

        # Benchmark comparison
        bench_comp = None
        if benchmark_series is not None and pipeline_id != "pipeline_a_fi2010":
            bench_comp = self.benchmark_comparator.compare(
                strategy_equity=eq_series,
                benchmark_prices_or_equity=benchmark_series,
                pipeline_id=pipeline_id,
            )

        # Execution summary
        exec_summary = {
            "total_orders": len(executed_orders),
            "filled_orders": len([o for o in executed_orders if o.status == OrderStatus.FILLED]),
            "rejected_orders": len([o for o in executed_orders if o.status == OrderStatus.REJECTED]),
            "total_slippage_cost": round(sum(o.total_slippage for o in executed_orders), 2),
            "total_transaction_fees": round(sum(o.total_transaction_cost for o in executed_orders), 2),
        }

        strat_name = getattr(strategy, "strategy_name", type(strategy).__name__)
        strat_ver = getattr(strategy, "strategy_version", "1.0")

        return BacktestReport(
            backtest_id=bt_id,
            symbol=symbol,
            pipeline_id=pipeline_id,
            strategy_name=strat_name,
            strategy_version=strat_ver,
            start_date=start_ts,
            end_date=end_ts,
            total_bars=total_bars,
            initial_capital=self.initial_capital,
            final_equity=portfolio.current_equity,
            performance_metrics=perf_metrics,
            equity_curve=eq_series,
            drawdown_curve=dd_series,
            cash_curve=cash_series,
            trades=[t.to_dict() for t in portfolio.trades],
            execution_summary=exec_summary,
            benchmark_comparison=bench_comp,
            risk_configuration={
                "risk_free_rate": self.risk_free_rate,
                "use_risk_engine": use_risk_engine,
            },
            limitations_and_assumptions=limitations,
        )
