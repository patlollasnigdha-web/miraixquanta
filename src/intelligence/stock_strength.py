"""
MIRAI — Stock Strength Intelligence Engine (M05)
Evaluates dynamic relative stock strength (0 to 100) across six quantitative pillars:
Momentum, Relative Strength (vs NIFTY 50), Volume, Trend, Volatility-Adjusted Return, and Liquidity.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.features.technical_indicators import (
    compute_sma,
    compute_ema,
    compute_rsi,
    compute_macd,
    compute_bollinger_bands,
)
from src.features.volatility_features import compute_garman_klass_volatility, compute_realized_volatility

logger = get_logger("StockStrength")


@dataclass
class StockStrengthResult:
    """Standardized output structure for stock strength evaluation."""
    symbol: str
    evaluation_timestamp: pd.Timestamp
    evaluation_timeframe: str
    overall_score: float
    classification: str
    factor_scores: Dict[str, float]
    factor_contributions: Dict[str, float]
    factor_weights: Dict[str, float]
    trend_status: str  # 'Strengthening', 'Weakening', 'Stable', 'Potential Reversal'
    data_coverage: float  # Fraction of factors with complete data [0.0, 1.0]
    confidence: float  # Confidence level [0.0, 1.0]
    missing_data_warnings: List[str] = field(default_factory=list)
    strongest_factor: Optional[str] = None
    weakest_factor: Optional[str] = None
    lob_depth_available: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Converts result dataclass to dictionary."""
        return {
            "symbol": self.symbol,
            "evaluation_timestamp": self.evaluation_timestamp.isoformat() if hasattr(self.evaluation_timestamp, "isoformat") else str(self.evaluation_timestamp),
            "evaluation_timeframe": self.evaluation_timeframe,
            "overall_score": round(self.overall_score, 2),
            "classification": self.classification,
            "trend_status": self.trend_status,
            "factor_scores": {k: round(v, 2) for k, v in self.factor_scores.items()},
            "factor_contributions": {k: round(v, 2) for k, v in self.factor_contributions.items()},
            "factor_weights": {k: round(v, 3) for k, v in self.factor_weights.items()},
            "data_coverage": round(self.data_coverage, 3),
            "confidence": round(self.confidence, 3),
            "strongest_factor": self.strongest_factor,
            "weakest_factor": self.weakest_factor,
            "missing_data_warnings": self.missing_data_warnings,
            "lob_depth_available": self.lob_depth_available,
        }


class StockStrengthEngine:
    """
    Computes time-specific Stock Strength Score from 0 to 100 for individual equities.
    Integrates momentum, benchmark-relative performance, volume confirmation,
    trend quality, risk-adjusted returns, and liquidity proxies.
    """

    DEFAULT_WEIGHTS = {
        "momentum": 0.20,
        "relative_strength": 0.25,
        "volume": 0.15,
        "trend": 0.20,
        "volatility_adjusted": 0.10,
        "liquidity": 0.10,
    }

    CLASSIFICATION_THRESHOLDS = {
        "Very Strong": 80.0,
        "Strong": 65.0,
        "Neutral": 45.0,
        "Weak": 30.0,
        "Very Weak": 0.0,
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        short_window: int = 5,
        medium_window: int = 20,
        long_window: int = 60,
        movement_threshold: float = 3.0,
    ):
        cfg = get_config()
        self.weights = weights or cfg.get("stock_strength.weights", self.DEFAULT_WEIGHTS)
        # Normalize weights to sum to 1.0
        total_w = sum(self.weights.values())
        if total_w > 0:
            self.weights = {k: v / total_w for k, v in self.weights.items()}

        self.short_window = short_window
        self.medium_window = medium_window
        self.long_window = long_window
        self.movement_threshold = movement_threshold

    @staticmethod
    def _scale_to_100(val: float, min_val: float, max_val: float) -> float:
        """Clips and linearly scales a continuous metric into the [0, 100] interval."""
        if np.isnan(val) or np.isinf(val):
            return 50.0
        clipped = np.clip(val, min_val, max_val)
        return float(((clipped - min_val) / (max_val - min_val)) * 100.0)

    # -------------------------------------------------------------
    # FACTOR 1: MOMENTUM STRENGTH
    # -------------------------------------------------------------
    def _compute_momentum_factor(self, df_stock: pd.DataFrame) -> Tuple[Optional[float], List[str]]:
        """
        Evaluates multi-window momentum: returns over short, medium, and long windows,
        plus moving average alignment.
        """
        warnings = []
        close = df_stock["close"]
        n_bars = len(close)

        if n_bars < self.short_window:
            return None, ["Insufficient history for momentum factor (need >= 5 bars)."]

        # 1. Multi-window returns
        ret_5 = (close.iloc[-1] / close.iloc[-self.short_window] - 1.0) if n_bars >= self.short_window else 0.0
        ret_20 = (close.iloc[-1] / close.iloc[-self.medium_window] - 1.0) if n_bars >= self.medium_window else ret_5
        ret_60 = (close.iloc[-1] / close.iloc[-self.long_window] - 1.0) if n_bars >= self.long_window else ret_20

        # Scale returns: 5d [-6%, +6%], 20d [-12%, +12%], 60d [-20%, +20%]
        score_5 = self._scale_to_100(ret_5, -0.06, 0.06)
        score_20 = self._scale_to_100(ret_20, -0.12, 0.12)
        score_60 = self._scale_to_100(ret_60, -0.20, 0.20)

        # 2. Moving Average Alignment (Price > SMA20 > SMA50)
        ma_bonus = 50.0
        if n_bars >= 50:
            sma_20 = close.iloc[-20:].mean()
            sma_50 = close.iloc[-50:].mean()
            p = close.iloc[-1]
            if p > sma_20 and sma_20 > sma_50:
                ma_bonus = 85.0
            elif p > sma_20:
                ma_bonus = 65.0
            elif p < sma_20 and sma_20 < sma_50:
                ma_bonus = 15.0
            else:
                ma_bonus = 40.0

        # 3. Momentum Acceleration (ROC change: short-term return minus medium-term daily pace)
        daily_pace_20 = ret_20 / max(self.medium_window, 1)
        daily_pace_5 = ret_5 / max(self.short_window, 1)
        accel = daily_pace_5 - daily_pace_20
        score_accel = self._scale_to_100(accel, -0.01, 0.01)

        # Weighted combination
        score = 0.25 * score_5 + 0.30 * score_20 + 0.20 * score_60 + 0.15 * ma_bonus + 0.10 * score_accel
        return float(np.clip(score, 0.0, 100.0)), warnings

    # -------------------------------------------------------------
    # FACTOR 2: RELATIVE STRENGTH (VS BENCHMARK)
    # -------------------------------------------------------------
    def _compute_relative_strength_factor(
        self, df_stock: pd.DataFrame, df_benchmark: Optional[pd.DataFrame]
    ) -> Tuple[Optional[float], List[str]]:
        """
        Evaluates stock performance relative to NIFTY 50 benchmark over matching windows.
        """
        if df_benchmark is None or df_benchmark.empty:
            return None, ["Benchmark data unavailable for relative strength factor."]

        close_stock = df_stock["close"]
        close_bench = df_benchmark["close"]
        n_bars = min(len(close_stock), len(close_bench))

        if n_bars < self.short_window:
            return None, ["Insufficient overlapping history with benchmark (need >= 5 bars)."]

        # Calculate relative alphas
        alpha_5 = (close_stock.iloc[-1] / close_stock.iloc[-self.short_window]) - (close_bench.iloc[-1] / close_bench.iloc[-self.short_window])
        alpha_20 = 0.0
        if n_bars >= self.medium_window:
            alpha_20 = (close_stock.iloc[-1] / close_stock.iloc[-self.medium_window]) - (close_bench.iloc[-1] / close_bench.iloc[-self.medium_window])
        else:
            alpha_20 = alpha_5

        alpha_60 = 0.0
        if n_bars >= self.long_window:
            alpha_60 = (close_stock.iloc[-1] / close_stock.iloc[-self.long_window]) - (close_bench.iloc[-1] / close_bench.iloc[-self.long_window])
        else:
            alpha_60 = alpha_20

        # Scale alphas: [-5%, +5%], [-10%, +10%], [-15%, +15%]
        score_a5 = self._scale_to_100(alpha_5, -0.05, 0.05)
        score_a20 = self._scale_to_100(alpha_20, -0.10, 0.10)
        score_a60 = self._scale_to_100(alpha_60, -0.15, 0.15)

        score = 0.35 * score_a5 + 0.40 * score_a20 + 0.25 * score_a60
        return float(np.clip(score, 0.0, 100.0)), []

    # -------------------------------------------------------------
    # FACTOR 3: VOLUME STRENGTH
    # -------------------------------------------------------------
    def _compute_volume_factor(self, df_stock: pd.DataFrame) -> Tuple[Optional[float], List[str]]:
        """
        Evaluates Relative Volume (RVOL), volume expansion on up vs down days,
        and price-volume trend confirmation.
        """
        if "volume" not in df_stock.columns:
            return None, ["Volume column missing from input data."]

        vol = df_stock["volume"]
        close = df_stock["close"]
        n_bars = len(vol)

        if n_bars < self.short_window or vol.sum() == 0:
            return None, ["Insufficient or zero volume history."]

        # 1. Relative Volume (RVOL = current volume / 20d avg volume)
        avg_vol_20 = vol.iloc[-self.medium_window:].mean() if n_bars >= self.medium_window else vol.mean()
        rvol = (vol.iloc[-1] / max(avg_vol_20, 1.0))
        # Scale RVOL: [0.3x, 2.5x] -> [0, 100]
        score_rvol = self._scale_to_100(rvol, 0.3, 2.5)

        # 2. Volume Confirmation (Price up on high volume = bullish; Price down on high volume = bearish)
        ret_1d = close.iloc[-1] / close.iloc[-2] - 1.0 if n_bars >= 2 else 0.0
        if ret_1d > 0 and rvol > 1.2:
            score_confirm = 85.0
        elif ret_1d > 0 and rvol <= 1.0:
            score_confirm = 55.0  # Up on light volume
        elif ret_1d < 0 and rvol > 1.2:
            score_confirm = 15.0  # Heavy volume selling
        elif ret_1d < 0 and rvol <= 1.0:
            score_confirm = 45.0  # Light pullback
        else:
            score_confirm = 50.0

        # 3. Up/Down Volume Ratio over trailing 20 days
        w = min(n_bars, self.medium_window)
        trailing_rets = close.diff().iloc[-w:]
        trailing_vols = vol.iloc[-w:]
        up_vol = trailing_vols[trailing_rets > 0].sum()
        down_vol = trailing_vols[trailing_rets < 0].sum()
        total_vol = up_vol + down_vol
        ratio = (up_vol / total_vol) if total_vol > 0 else 0.5
        score_ratio = float(ratio * 100.0)

        score = 0.35 * score_rvol + 0.35 * score_confirm + 0.30 * score_ratio
        return float(np.clip(score, 0.0, 100.0)), []

    # -------------------------------------------------------------
    # FACTOR 4: TREND STRENGTH
    # -------------------------------------------------------------
    def _compute_trend_factor(self, df_stock: pd.DataFrame) -> Tuple[Optional[float], List[str]]:
        """
        Evaluates trend direction, trend consistency (% positive bars),
        and indicator confirmation (RSI, MACD).
        """
        close = df_stock["close"]
        n_bars = len(close)

        if n_bars < self.medium_window:
            return None, ["Insufficient history for trend factor (need >= 20 bars)."]

        # 1. EMA Alignment & Slope
        ema_12 = compute_ema(close, 12).iloc[-1]
        ema_26 = compute_ema(close, 26).iloc[-1]
        ema_diff_pct = (ema_12 - ema_26) / max(ema_26, 1e-8)
        score_ema = self._scale_to_100(ema_diff_pct, -0.04, 0.04)

        # 2. Trend Consistency (% of positive days over trailing 20 days)
        w = min(n_bars, 20)
        daily_diffs = close.diff().iloc[-w:]
        pos_days_pct = float(np.mean(daily_diffs > 0))
        score_cons = self._scale_to_100(pos_days_pct, 0.25, 0.75)

        # 3. RSI Confirmation
        rsi_series = compute_rsi(close, 14)
        rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty and not np.isnan(rsi_series.iloc[-1]) else 50.0
        # Optimal bullish zone is 55 to 70; > 80 is overbought risk; < 35 is oversold/downtrend
        if 55.0 <= rsi <= 72.0:
            score_rsi = 85.0
        elif 45.0 <= rsi < 55.0:
            score_rsi = 55.0
        elif rsi > 72.0:
            score_rsi = 65.0  # Overbought caution
        elif 35.0 <= rsi < 45.0:
            score_rsi = 35.0
        else:
            score_rsi = 15.0

        score = 0.40 * score_ema + 0.30 * score_cons + 0.30 * score_rsi
        return float(np.clip(score, 0.0, 100.0)), []

    # -------------------------------------------------------------
    # FACTOR 5: VOLATILITY-ADJUSTED STRENGTH
    # -------------------------------------------------------------
    def _compute_volatility_adjusted_factor(self, df_stock: pd.DataFrame) -> Tuple[Optional[float], List[str]]:
        """
        Evaluates risk-adjusted returns (return / volatility) and trend stability.
        """
        close = df_stock["close"]
        n_bars = len(close)

        if n_bars < self.medium_window:
            return None, ["Insufficient history for volatility-adjusted factor (need >= 20 bars)."]

        # Trailing 20d return
        ret_20 = close.iloc[-1] / close.iloc[-self.medium_window] - 1.0

        # Volatility estimate
        if "open" in df_stock.columns and "high" in df_stock.columns and "low" in df_stock.columns:
            gk_vol = compute_garman_klass_volatility(
                df_stock["open"], df_stock["high"], df_stock["low"], close, window=min(n_bars, 20)
            )
            vol = float(gk_vol.iloc[-1]) if not np.isnan(gk_vol.iloc[-1]) else 0.20
        else:
            rv = compute_realized_volatility(close, window=min(n_bars, 20))
            vol = float(rv.iloc[-1]) if not np.isnan(rv.iloc[-1]) else 0.20

        vol = max(vol, 0.05)  # Floor at 5% annualized vol
        # Sharpe proxy = annualized return / annualized vol
        ann_return = ret_20 * (252.0 / 20.0)
        sharpe_proxy = ann_return / vol

        # Scale Sharpe proxy: [-2.0, +3.0] -> [0, 100]
        score_sharpe = self._scale_to_100(sharpe_proxy, -2.0, 3.0)

        # Volatility stability: standard deviation of rolling returns
        log_rets = np.log(close / close.shift(1)).iloc[-20:]
        ret_stability = float(log_rets.std())
        score_stability = self._scale_to_100(-ret_stability, -0.035, -0.005)

        score = 0.70 * score_sharpe + 0.30 * score_stability
        return float(np.clip(score, 0.0, 100.0)), []

    # -------------------------------------------------------------
    # FACTOR 6: LIQUIDITY STRENGTH
    # -------------------------------------------------------------
    def _compute_liquidity_factor(self, df_stock: pd.DataFrame) -> Tuple[Optional[float], List[str], bool]:
        """
        Evaluates trading liquidity and turnover proxies.
        Explicitly distinguishes between daily turnover proxies and actual LOB depth.
        """
        warnings = []
        lob_available = False

        # Check if actual LOB columns exist (Pipeline A features)
        if "bid_size_1" in df_stock.columns and "ask_size_1" in df_stock.columns:
            lob_available = True
            # Real LOB depth imbalance available
            bid = df_stock["bid_size_1"].iloc[-1]
            ask = df_stock["ask_size_1"].iloc[-1]
            imb = (bid - ask) / max(bid + ask, 1.0)
            score_lob = self._scale_to_100(imb, -0.5, 0.5)
            return float(np.clip(score_lob, 0.0, 100.0)), warnings, lob_available

        # Otherwise evaluate turnover & Amihud illiquidity proxy on equity data
        if "turnover" in df_stock.columns:
            turnover_series = df_stock["turnover"]
        elif "volume" in df_stock.columns and "close" in df_stock.columns:
            turnover_series = df_stock["volume"] * df_stock["close"]
        else:
            return None, ["Neither turnover nor volume available for liquidity factor."], False

        n_bars = len(turnover_series)
        w = min(n_bars, 20)
        avg_turnover = float(turnover_series.iloc[-w:].mean())

        # Scale average daily turnover in ₹ INR: [₹5 Crore (5e7), ₹500 Crore (5e9)]
        # For NIFTY constituents, turnover typically ranges from ₹20 Cr to ₹1000+ Cr
        log_to = np.log10(max(avg_turnover, 1e6))
        score_turnover = self._scale_to_100(log_to, 7.5, 9.5)  # 10^7.5 = ₹3.16 Cr, 10^9.5 = ₹316 Cr

        # Amihud Illiquidity Proxy = |Return| / Turnover
        close = df_stock["close"]
        rets = (close / close.shift(1) - 1.0).abs().iloc[-w:]
        to_norm = turnover_series.iloc[-w:] / 1e7  # in Crores
        amihud = float((rets / to_norm.replace(0.0, 1e-4)).mean())
        # Lower Amihud = higher liquidity: scale [-log10(amihud)]
        log_amihud = np.log10(max(amihud, 1e-6))
        score_amihud = self._scale_to_100(-log_amihud, -1.0, 4.0)

        score = 0.60 * score_turnover + 0.40 * score_amihud
        return float(np.clip(score, 0.0, 100.0)), warnings, False

    # -------------------------------------------------------------
    # DYNAMIC MOVEMENT & REVERSAL CLASSIFIER
    # -------------------------------------------------------------
    def _determine_trend_status(
        self,
        current_score: float,
        prior_score: Optional[float],
        df_stock: pd.DataFrame,
    ) -> str:
        """
        Determines if the stock is Strengthening, Weakening, Stable, or experiencing a Potential Reversal.
        """
        close = df_stock["close"]
        rsi_series = compute_rsi(close, 14)
        rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty and not np.isnan(rsi_series.iloc[-1]) else 50.0

        # Check for potential reversal conditions:
        # e.g., Extreme overbought (RSI > 75) with falling 3-day momentum, or extreme oversold (RSI < 25) with turning momentum
        if len(close) >= 4:
            ret_3d = close.iloc[-1] / close.iloc[-4] - 1.0
            if rsi > 75.0 and ret_3d < -0.015:
                return "Potential Reversal"
            if rsi < 25.0 and ret_3d > 0.015:
                return "Potential Reversal"

        if prior_score is None:
            return "Stable"

        delta = current_score - prior_score
        if delta >= self.movement_threshold:
            return "Strengthening"
        elif delta <= -self.movement_threshold:
            return "Weakening"
        else:
            return "Stable"

    # -------------------------------------------------------------
    # MASTER STRENGTH EVALUATION
    # -------------------------------------------------------------
    def evaluate_stock_strength(
        self,
        df_stock: pd.DataFrame,
        symbol: str,
        df_benchmark: Optional[pd.DataFrame] = None,
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        timeframe: str = "1d",
        prior_score: Optional[float] = None,
    ) -> StockStrengthResult:
        """
        Computes the comprehensive Stock Strength Score (0 to 100) for an individual stock.
        Guarantees strict chronological conditioning: only data up to as_of_date is used.
        """
        # 1. Filter data up to as_of_date (strictly no future data leakage)
        df_s = df_stock.copy()
        if "timestamp" in df_s.columns:
            df_s["timestamp"] = pd.to_datetime(df_s["timestamp"])
            if as_of_date is not None:
                as_of_ts = pd.to_datetime(as_of_date)
                df_s = df_s[df_s["timestamp"] <= as_of_ts]
            df_s = df_s.sort_values("timestamp").reset_index(drop=True)
            eval_time = df_s["timestamp"].iloc[-1] if not df_s.empty else pd.Timestamp.now()
        else:
            eval_time = pd.Timestamp.now()

        df_b = None
        if df_benchmark is not None and not df_benchmark.empty:
            df_b = df_benchmark.copy()
            if "timestamp" in df_b.columns:
                df_b["timestamp"] = pd.to_datetime(df_b["timestamp"])
                if as_of_date is not None:
                    as_of_ts = pd.to_datetime(as_of_date)
                    df_b = df_b[df_b["timestamp"] <= as_of_ts]
                df_b = df_b.sort_values("timestamp").reset_index(drop=True)

        if df_s.empty or len(df_s) < 5:
            return StockStrengthResult(
                symbol=symbol,
                evaluation_timestamp=eval_time,
                evaluation_timeframe=timeframe,
                overall_score=50.0,
                classification="Neutral",
                factor_scores={},
                factor_contributions={},
                factor_weights={},
                trend_status="Stable",
                data_coverage=0.0,
                confidence=0.0,
                missing_data_warnings=["Insufficient historical bars to compute strength score (minimum 5 required)."],
            )

        # 2. Compute individual factor scores
        all_warnings: List[str] = []
        raw_scores: Dict[str, Optional[float]] = {}

        # Momentum
        s_mom, w_mom = self._compute_momentum_factor(df_s)
        raw_scores["momentum"] = s_mom
        all_warnings.extend(w_mom)

        # Relative Strength
        s_rel, w_rel = self._compute_relative_strength_factor(df_s, df_b)
        raw_scores["relative_strength"] = s_rel
        all_warnings.extend(w_rel)

        # Volume
        s_vol, w_vol = self._compute_volume_factor(df_s)
        raw_scores["volume"] = s_vol
        all_warnings.extend(w_vol)

        # Trend
        s_trd, w_trd = self._compute_trend_factor(df_s)
        raw_scores["trend"] = s_trd
        all_warnings.extend(w_trd)

        # Volatility-Adjusted
        s_vola, w_vola = self._compute_volatility_adjusted_factor(df_s)
        raw_scores["volatility_adjusted"] = s_vola
        all_warnings.extend(w_vola)

        # Liquidity
        s_liq, w_liq, lob_available = self._compute_liquidity_factor(df_s)
        raw_scores["liquidity"] = s_liq
        all_warnings.extend(w_liq)

        # 3. Dynamic weight re-normalization for missing factors
        available_scores = {k: v for k, v in raw_scores.items() if v is not None}
        missing_factors = [k for k, v in raw_scores.items() if v is None]
        for mf in missing_factors:
            all_warnings.append(f"Missing factor '{mf}' omitted from weighted score.")

        if not available_scores:
            return StockStrengthResult(
                symbol=symbol,
                evaluation_timestamp=eval_time,
                evaluation_timeframe=timeframe,
                overall_score=50.0,
                classification="Neutral",
                factor_scores={},
                factor_contributions={},
                factor_weights={},
                trend_status="Stable",
                data_coverage=0.0,
                confidence=0.0,
                missing_data_warnings=all_warnings,
            )

        # Re-weight available factors
        sum_avail_weights = sum(self.weights[k] for k in available_scores.keys())
        norm_weights = {k: self.weights[k] / sum_avail_weights for k in available_scores.keys()}

        # 4. Overall score and factor contributions
        contributions = {k: available_scores[k] * norm_weights[k] for k in available_scores.keys()}
        overall_score = float(sum(contributions.values()))
        overall_score = float(np.clip(overall_score, 0.0, 100.0))

        # 5. Classification
        classification = "Very Weak"
        for label, thresh in self.CLASSIFICATION_THRESHOLDS.items():
            if overall_score >= thresh:
                classification = label
                break

        # 6. Coverage and Confidence
        coverage = len(available_scores) / len(self.weights)
        history_len = len(df_s)
        history_confidence = min(1.0, history_len / max(self.long_window, 1))
        confidence = float(coverage * history_confidence)

        # 7. Identify strongest and weakest factors
        strongest = max(available_scores.items(), key=lambda x: x[1])[0]
        weakest = min(available_scores.items(), key=lambda x: x[1])[0]

        # 8. Trend status (Strengthening / Weakening / Reversal)
        trend_status = self._determine_trend_status(overall_score, prior_score, df_s)

        return StockStrengthResult(
            symbol=symbol,
            evaluation_timestamp=eval_time,
            evaluation_timeframe=timeframe,
            overall_score=overall_score,
            classification=classification,
            factor_scores=available_scores,
            factor_contributions=contributions,
            factor_weights=norm_weights,
            trend_status=trend_status,
            data_coverage=coverage,
            confidence=confidence,
            missing_data_warnings=all_warnings,
            strongest_factor=strongest,
            weakest_factor=weakest,
            lob_depth_available=lob_available,
        )

    # -------------------------------------------------------------
    # HISTORICAL TIMELINE & CROSS-SECTIONAL RANKING
    # -------------------------------------------------------------
    def compute_strength_timeline(
        self,
        df_stock: pd.DataFrame,
        symbol: str,
        df_benchmark: Optional[pd.DataFrame] = None,
        min_bars: int = 20,
    ) -> pd.DataFrame:
        """
        Calculates rolling stock strength score timeline across entire history.
        Ensures zero future lookahead bias by scoring only on trailing data at each bar.
        """
        df_s = df_stock.copy().sort_values("timestamp").reset_index(drop=True)
        records = []
        prior_score = None

        for idx in range(min_bars, len(df_s)):
            trailing_slice = df_s.iloc[: idx + 1]
            as_of_ts = df_s["timestamp"].iloc[idx]

            bench_slice = None
            if df_benchmark is not None:
                bench_slice = df_benchmark[df_benchmark["timestamp"] <= as_of_ts]

            res = self.evaluate_stock_strength(
                df_stock=trailing_slice,
                symbol=symbol,
                df_benchmark=bench_slice,
                as_of_date=as_of_ts,
                prior_score=prior_score,
            )
            prior_score = res.overall_score
            row = res.to_dict()
            records.append(row)

        return pd.DataFrame(records)

    def rank_stocks(
        self,
        stock_dfs: Dict[str, pd.DataFrame],
        df_benchmark: Optional[pd.DataFrame] = None,
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
    ) -> pd.DataFrame:
        """
        Ranks multiple stocks cross-sectionally for a given evaluation date.
        """
        rows = []
        for sym, df_s in stock_dfs.items():
            res = self.evaluate_stock_strength(
                df_stock=df_s,
                symbol=sym,
                df_benchmark=df_benchmark,
                as_of_date=as_of_date,
            )
            rows.append({
                "symbol": sym,
                "overall_score": res.overall_score,
                "classification": res.classification,
                "trend_status": res.trend_status,
                "confidence": res.confidence,
                "momentum": res.factor_scores.get("momentum"),
                "relative_strength": res.factor_scores.get("relative_strength"),
                "volume": res.factor_scores.get("volume"),
                "trend": res.factor_scores.get("trend"),
                "volatility_adjusted": res.factor_scores.get("volatility_adjusted"),
                "liquidity": res.factor_scores.get("liquidity"),
            })

        df_rank = pd.DataFrame(rows)
        if not df_rank.empty:
            df_rank = df_rank.sort_values("overall_score", ascending=False).reset_index(drop=True)
            df_rank["rank"] = df_rank.index + 1
        return df_rank
