"""
MIRAI — Adaptive Trading Strategy Engine (M08)
Coordinates candidate strategy generation, executes adaptive regime-based selection,
and emits the primary strategy signal.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from src.utils.logger import get_logger
from src.intelligence.regime_detection import MarketRegime
from src.strategies.base_strategy import BaseTradingStrategy, StrategySignal, SignalAction
from src.strategies.momentum_strategy import MomentumStrategy
from src.strategies.mean_reversion_strategy import MeanReversionStrategy
from src.strategies.breakout_strategy import BreakoutStrategy
from src.strategies.strategy_selector import AdaptiveStrategySelector, StrategySelectionResult

logger = get_logger("AdaptiveStrategyEngine")


class AdaptiveStrategyEngine:
    """
    Central strategy orchestration engine.
    Executes all candidate strategies for a symbol, filters and ranks them
    using the prevailing market regime, and emits the optimal signal.
    """

    def __init__(
        self,
        strategies: Optional[List[BaseTradingStrategy]] = None,
        selector: Optional[AdaptiveStrategySelector] = None,
        pipeline_id: str = "pipeline_b_nifty",
    ):
        self.pipeline_id = pipeline_id
        self.strategies = strategies or [
            MomentumStrategy(),
            MeanReversionStrategy(),
            BreakoutStrategy(),
        ]
        self.selector = selector or AdaptiveStrategySelector()

    def evaluate_strategies(
        self,
        df_market: pd.DataFrame,
        symbol: str,
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        market_regime: str = MarketRegime.SIDEWAYS_RANGE_BOUND,
        regime_confidence: float = 0.80,
        persistence_bars: int = 1,
        intelligence: Optional[Any] = None,
    ) -> Tuple[StrategySignal, StrategySelectionResult]:
        """
        Executes candidate strategies and adaptively selects the best signal.
        """
        candidate_signals: List[StrategySignal] = []

        # 1. Run each strategy
        for strat in self.strategies:
            try:
                sig = strat.generate_signal(
                    df_market=df_market,
                    symbol=symbol,
                    as_of_date=as_of_date,
                    market_regime=market_regime,
                    intelligence=intelligence,
                )
                candidate_signals.append(sig)
            except Exception as exc:
                logger.warning(
                    "Strategy '%s' execution failed for %s: %s",
                    strat.strategy_name, symbol, exc
                )

        # 2. Adaptive selection via regime selector
        selection_res = self.selector.select_strategy(
            candidate_signals=candidate_signals,
            market_regime=market_regime,
            regime_confidence=regime_confidence,
            persistence_bars=persistence_bars,
        )

        # 3. Match selected signal
        if selection_res.selected_strategy:
            selected_sig = next(
                (s for s in candidate_signals if s.strategy_name == selection_res.selected_strategy),
                None
            )
            if selected_sig:
                return selected_sig, selection_res

        # 4. Fallback if no strategy qualified or all suppressed
        fallback_time = pd.to_datetime(as_of_date) if as_of_date else pd.Timestamp.now()
        fallback_price = float(df_market["close"].iloc[-1]) if "close" in df_market.columns and not df_market.empty else None

        fallback_sig = StrategySignal(
            symbol=symbol,
            pipeline_id=self.pipeline_id,
            strategy_name="AdaptiveEnsemble",
            strategy_version="1.0.0",
            signal=SignalAction.NO_SIGNAL,
            signal_strength=0.0,
            prediction_horizon="1d",
            timestamp=fallback_time,
            entry_reference_price=fallback_price,
            applicable_market_regime=market_regime,
            supporting_evidence={"reason": selection_res.selection_reason},
            data_quality={"candidates_evaluated": len(candidate_signals)},
        )

        return fallback_sig, selection_res
