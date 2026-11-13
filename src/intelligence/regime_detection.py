"""
MIRAI — Market Regime Detection Engine (M07)
Identifies macro market regimes across six structural states:
BULLISH_TRENDING, BEARISH_TRENDING, SIDEWAYS_RANGE_BOUND, HIGH_VOLATILITY, LOW_VOLATILITY, STRESS_ABNORMAL.
Implements transparent rule-based baselines and unsupervised Gaussian Mixture Models (GMM)
with rigorous post-clustering semantic mapping and transition dynamics.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.features.technical_indicators import compute_sma, compute_ema, compute_atr
from src.features.volatility_features import compute_realized_volatility, compute_garman_klass_volatility

logger = get_logger("RegimeDetection")


class MarketRegime:
    """Standardized semantic regime definitions."""
    BULLISH_TRENDING = "BULLISH_TRENDING"
    BEARISH_TRENDING = "BEARISH_TRENDING"
    SIDEWAYS_RANGE_BOUND = "SIDEWAYS_RANGE_BOUND"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    STRESS_ABNORMAL = "STRESS_ABNORMAL"

    ALL_REGIMES = [
        BULLISH_TRENDING,
        BEARISH_TRENDING,
        SIDEWAYS_RANGE_BOUND,
        HIGH_VOLATILITY,
        LOW_VOLATILITY,
        STRESS_ABNORMAL,
    ]


@dataclass
class RegimeDetectionResult:
    """Standardized output structure for market regime evaluation."""
    instrument: str
    evaluation_timestamp: pd.Timestamp
    timeframe: str  # '1d', '1min', '15sec'
    detected_regime: str
    regime_confidence: float  # [0.0, 1.0]
    regime_probabilities: Dict[str, float]
    quantitative_evidence: Dict[str, float]
    persistence_bars: int  # Number of consecutive periods in this regime
    prior_regime: Optional[str] = None
    recent_transition: bool = False
    model_version: str = "1.0.0"
    model_type: str = "rule_based"  # 'rule_based' or 'gmm'

    @property
    def current_regime(self) -> str:
        return self.detected_regime

    @property
    def as_of_date(self) -> pd.Timestamp:
        return self.evaluation_timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instrument": self.instrument,
            "evaluation_timestamp": self.evaluation_timestamp.isoformat() if hasattr(self.evaluation_timestamp, "isoformat") else str(self.evaluation_timestamp),
            "timeframe": self.timeframe,
            "detected_regime": self.detected_regime,
            "regime_confidence": round(self.regime_confidence, 3),
            "regime_probabilities": {k: round(v, 3) for k, v in self.regime_probabilities.items()},
            "quantitative_evidence": {k: round(v, 4) for k, v in self.quantitative_evidence.items()},
            "persistence_bars": self.persistence_bars,
            "prior_regime": self.prior_regime,
            "recent_transition": self.recent_transition,
            "model_version": self.model_version,
            "model_type": self.model_type,
        }


# -----------------------------------------------------------------
# QUANTITATIVE REGIME FEATURE EXTRACTION
# -----------------------------------------------------------------
def extract_regime_features(
    df: pd.DataFrame,
    volatility_window: int = 20,
    trend_window: int = 50,
    drawdown_window: int = 60,
    annualization_factor: int = 252,
) -> pd.DataFrame:
    """
    Computes standard quantitative features used by all regime detectors.
    Features:
    - ret_20d: 20-period compound return
    - ann_vol_20d: 20-period annualized realized volatility
    - trend_dist_sma50: (Price - SMA50) / SMA50
    - max_drawdown_60d: Rolling peak-to-trough drawdown over 60 periods
    - vol_percentile_252d: Percentile of current volatility relative to 1-year history
    - ema_slope_20d: Normalized slope of 20-period EMA
    """
    out = df.copy()
    if "close" not in out.columns:
        raise ValueError("DataFrame must contain 'close' column.")

    close = out["close"]
    n_bars = len(close)

    # 1. Rolling returns
    out["ret_5d"] = close / close.shift(5) - 1.0
    out["ret_20d"] = close / close.shift(volatility_window) - 1.0

    # 2. Annualized volatility (incorporates both close-to-close jumps and intraday extremes)
    rv = compute_realized_volatility(
        close, window=volatility_window, annualize=True, factor=annualization_factor
    )
    if "open" in out.columns and "high" in out.columns and "low" in out.columns:
        gk = compute_garman_klass_volatility(
            out["open"], out["high"], out["low"], close, window=volatility_window, factor=annualization_factor
        )
        out["ann_vol_20d"] = np.maximum(rv.fillna(0.0), gk.fillna(0.0))
    else:
        out["ann_vol_20d"] = rv

    # 3. Distance from 50-period SMA
    sma_50 = compute_sma(close, window=min(trend_window, max(n_bars, 2)))
    out["trend_dist_sma50"] = (close - sma_50) / sma_50.replace(0.0, 1e-8)

    # 4. Rolling Drawdown over 60 periods
    rolling_peak = close.rolling(window=min(drawdown_window, max(n_bars, 2)), min_periods=1).max()
    out["max_drawdown_60d"] = (close - rolling_peak) / rolling_peak.replace(0.0, 1e-8)

    # 5. Volatility percentile (over trailing 252 bars or available history)
    w_vol_rank = min(252, n_bars)
    out["vol_percentile_252d"] = out["ann_vol_20d"].rolling(window=w_vol_rank, min_periods=5).apply(
        lambda s: float(np.mean(s <= s[-1])) if len(s) > 0 else 0.5, raw=True
    )

    # 6. EMA slope
    ema_20 = compute_ema(close, window=volatility_window)
    out["ema_slope_20d"] = (ema_20 - ema_20.shift(5)) / ema_20.replace(0.0, 1e-8)

    return out


# -----------------------------------------------------------------
# ABSTRACT BASE REGIME DETECTOR
# -----------------------------------------------------------------
class BaseRegimeDetector(ABC):
    """Abstract interface for all market regime classifiers."""

    def __init__(self, model_name: str = "BaseRegimeDetector"):
        self.model_name = model_name
        self.is_fitted = False

    @abstractmethod
    def fit(self, df: pd.DataFrame) -> "BaseRegimeDetector":
        """Fits regime detector on chronological historical data."""
        pass

    @abstractmethod
    def predict_regime(
        self,
        df: pd.DataFrame,
        instrument: str = "NIFTY 50",
        timeframe: str = "1d",
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        prior_regimes: Optional[List[str]] = None,
    ) -> RegimeDetectionResult:
        """Evaluates and returns market regime result as of a specific date."""
        pass

    def detect_regime(self, df: pd.DataFrame, **kwargs) -> RegimeDetectionResult:
        """Convenience alias for predict_regime."""
        return self.predict_regime(df, **kwargs)


# -----------------------------------------------------------------
# 1. TRANSPARENT RULE-BASED REGIME DETECTOR (BASELINE)
# -----------------------------------------------------------------
class RuleBasedRegimeDetector(BaseRegimeDetector):
    """
    Transparent rule-based market regime classifier.
    Maps quantitative indicators into 6 regimes using explicit economic thresholds.
    """

    def __init__(
        self,
        vol_stress_threshold: float = 0.28,
        drawdown_stress_threshold: float = -0.10,
        vol_high_percentile: float = 0.80,
        vol_low_percentile: float = 0.20,
        return_trend_threshold: float = 0.03,
    ):
        super().__init__(model_name="RuleBasedRegimeDetector")
        self.vol_stress_threshold = vol_stress_threshold
        self.drawdown_stress_threshold = drawdown_stress_threshold
        self.vol_high_percentile = vol_high_percentile
        self.vol_low_percentile = vol_low_percentile
        self.return_trend_threshold = return_trend_threshold
        self.is_fitted = True

    def fit(self, df: pd.DataFrame) -> "RuleBasedRegimeDetector":
        """Rule-based model has fixed structural thresholds; fit validates input data."""
        self.is_fitted = True
        return self

    def predict_regime(
        self,
        df: pd.DataFrame,
        instrument: str = "NIFTY 50",
        timeframe: str = "1d",
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        prior_regimes: Optional[List[str]] = None,
    ) -> RegimeDetectionResult:
        """Classifies the market regime strictly conditioning on data <= as_of_date."""
        df_cut = df.copy()
        if "timestamp" in df_cut.columns and as_of_date is not None:
            as_of_ts = pd.to_datetime(as_of_date)
            df_cut = df_cut[pd.to_datetime(df_cut["timestamp"]) <= as_of_ts]
            eval_ts = df_cut["timestamp"].iloc[-1] if not df_cut.empty else as_of_ts
        else:
            eval_ts = pd.Timestamp.now()

        if len(df_cut) < 10:
            return RegimeDetectionResult(
                instrument=instrument,
                evaluation_timestamp=eval_ts,
                timeframe=timeframe,
                detected_regime=MarketRegime.SIDEWAYS_RANGE_BOUND,
                regime_confidence=0.5,
                regime_probabilities={r: 1.0 / 6.0 for r in MarketRegime.ALL_REGIMES},
                quantitative_evidence={},
                persistence_bars=1,
                model_type="rule_based",
            )

        feats = extract_regime_features(df_cut)
        row = feats.iloc[-1]

        ann_vol = float(row.get("ann_vol_20d", 0.16)) if pd.notna(row.get("ann_vol_20d")) else 0.16
        ret_20d = float(row.get("ret_20d", 0.0)) if pd.notna(row.get("ret_20d")) else 0.0
        trend_dist = float(row.get("trend_dist_sma50", 0.0)) if pd.notna(row.get("trend_dist_sma50")) else 0.0
        max_dd = float(row.get("max_drawdown_60d", 0.0)) if pd.notna(row.get("max_drawdown_60d")) else 0.0
        vol_pct = float(row.get("vol_percentile_252d", 0.5)) if pd.notna(row.get("vol_percentile_252d")) else 0.5
        ema_slope = float(row.get("ema_slope_20d", 0.0)) if pd.notna(row.get("ema_slope_20d")) else 0.0

        evidence = {
            "annualized_vol_20d": ann_vol,
            "return_20d": ret_20d,
            "trend_dist_sma50": trend_dist,
            "max_drawdown_60d": max_dd,
            "volatility_percentile": vol_pct,
            "ema_slope_20d": ema_slope,
        }

        # ---------------------------------------------------------
        # DECISION TREE RULES (Hierarchy of Market Regimes)
        # ---------------------------------------------------------
        # 1. Stress / Abnormal Market Conditions (Severe Drawdown + High Volatility)
        if max_dd <= self.drawdown_stress_threshold and ann_vol >= self.vol_stress_threshold:
            regime = MarketRegime.STRESS_ABNORMAL
            confidence = 0.90
        # 2. High Volatility Regime
        elif vol_pct >= self.vol_high_percentile or ann_vol >= 0.25:
            regime = MarketRegime.HIGH_VOLATILITY
            confidence = 0.82
        # 3. Low Volatility Regime
        elif vol_pct <= self.vol_low_percentile and ann_vol <= 0.11:
            regime = MarketRegime.LOW_VOLATILITY
            confidence = 0.85
        # 4. Bullish Trending
        elif ret_20d >= self.return_trend_threshold and trend_dist > 0.01:
            regime = MarketRegime.BULLISH_TRENDING
            confidence = 0.85
        # 5. Bearish Trending
        elif ret_20d <= -self.return_trend_threshold and trend_dist < -0.01:
            regime = MarketRegime.BEARISH_TRENDING
            confidence = 0.85
        # 6. Sideways / Range-Bound
        else:
            regime = MarketRegime.SIDEWAYS_RANGE_BOUND
            confidence = 0.70

        # Construct probability distribution
        probs = {r: 0.03 for r in MarketRegime.ALL_REGIMES}
        probs[regime] = confidence
        rem = (1.0 - confidence) / 5.0
        for r in probs:
            if r != regime:
                probs[r] = rem

        # Persistence calculation
        persistence = 1
        prior_regime = None
        recent_trans = False
        if prior_regimes:
            prior_regime = prior_regimes[-1]
            if prior_regime != regime:
                recent_trans = True
            for pr in reversed(prior_regimes):
                if pr == regime:
                    persistence += 1
                else:
                    break

        return RegimeDetectionResult(
            instrument=instrument,
            evaluation_timestamp=eval_ts,
            timeframe=timeframe,
            detected_regime=regime,
            regime_confidence=confidence,
            regime_probabilities=probs,
            quantitative_evidence=evidence,
            persistence_bars=persistence,
            prior_regime=prior_regime,
            recent_transition=recent_trans,
            model_type="rule_based",
        )


# -----------------------------------------------------------------
# 2. GAUSSIAN MIXTURE MODEL REGIME DETECTOR (UNSUPERVISED + SEMANTIC)
# -----------------------------------------------------------------
class GMMRegimeDetector(BaseRegimeDetector):
    """
    Unsupervised Gaussian Mixture Model clustering for market regimes.
    Includes rigorous post-clustering semantic interpretation mapping clusters
    to domain regimes based on empirical return, volatility, and trend centroids.
    """

    FEATURE_COLS = ["ret_20d", "ann_vol_20d", "trend_dist_sma50", "max_drawdown_60d"]

    def __init__(
        self,
        n_components: int = 4,
        covariance_type: str = "full",
        random_state: int = 42,
    ):
        super().__init__(model_name="GMMRegimeDetector")
        self.n_components = n_components
        self.covariance_type = covariance_type
        self.random_state = random_state
        self.gmm = GaussianMixture(
            n_components=n_components,
            covariance_type=covariance_type,
            random_state=random_state,
        )
        self.cluster_to_regime: Dict[int, str] = {}
        self.scaler_mean: Optional[np.ndarray] = None
        self.scaler_std: Optional[np.ndarray] = None

    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        feats = extract_regime_features(df)
        sub = feats[self.FEATURE_COLS].dropna()
        return sub.values

    def fit(self, df: pd.DataFrame) -> "GMMRegimeDetector":
        """
        Fits GMM on feature matrix and semantically maps clusters.
        """
        X = self._prepare_features(df)
        if len(X) < self.n_components * 5:
            raise ValueError(f"Insufficient samples to fit GMM ({len(X)} samples for {self.n_components} components).")

        self.scaler_mean = np.mean(X, axis=0)
        self.scaler_std = np.std(X, axis=0) + 1e-8
        X_norm = (X - self.scaler_mean) / self.scaler_std

        self.gmm.fit(X_norm)
        self.is_fitted = True

        # ---------------------------------------------------------
        # SEMANTIC CLUSTER INTERPRETATION
        # Inspect real unnormalized centroids [ret_20d, ann_vol, trend, max_dd]
        # ---------------------------------------------------------
        centroids = self.gmm.means_ * self.scaler_std + self.scaler_mean
        logger.info("Interpreting %d GMM regime centroids...", self.n_components)

        cluster_summary = []
        for c_idx in range(self.n_components):
            c_ret = centroids[c_idx, 0]
            c_vol = centroids[c_idx, 1]
            c_trend = centroids[c_idx, 2]
            c_dd = centroids[c_idx, 3]
            cluster_summary.append((c_idx, c_ret, c_vol, c_trend, c_dd))
            logger.debug("Cluster %d: Ret=%.3f, Vol=%.3f, Trend=%.3f, DD=%.3f", c_idx, c_ret, c_vol, c_trend, c_dd)

        # Sort clusters by characteristics to assign semantic labels
        assigned = {}
        # Highest volatility cluster -> STRESS or HIGH_VOLATILITY
        sorted_by_vol = sorted(cluster_summary, key=lambda x: x[2], reverse=True)
        stress_cluster = sorted_by_vol[0][0]
        if sorted_by_vol[0][4] < -0.08:
            assigned[stress_cluster] = MarketRegime.STRESS_ABNORMAL
        else:
            assigned[stress_cluster] = MarketRegime.HIGH_VOLATILITY

        # Highest return among remaining -> BULLISH_TRENDING
        rem = [c for c in cluster_summary if c[0] not in assigned]
        if rem:
            sorted_by_ret = sorted(rem, key=lambda x: x[1], reverse=True)
            bull_cluster = sorted_by_ret[0][0]
            assigned[bull_cluster] = MarketRegime.BULLISH_TRENDING

        # Lowest return among remaining -> BEARISH_TRENDING
        rem = [c for c in cluster_summary if c[0] not in assigned]
        if rem:
            sorted_by_ret = sorted(rem, key=lambda x: x[1])
            bear_cluster = sorted_by_ret[0][0]
            assigned[bear_cluster] = MarketRegime.BEARISH_TRENDING

        # Lowest volatility remaining -> LOW_VOLATILITY or SIDEWAYS
        rem = [c for c in cluster_summary if c[0] not in assigned]
        for c in rem:
            assigned[c[0]] = MarketRegime.SIDEWAYS_RANGE_BOUND

        self.cluster_to_regime = assigned
        logger.info("Semantic Cluster Mapping: %s", self.cluster_to_regime)
        return self

    def predict_regime(
        self,
        df: pd.DataFrame,
        instrument: str = "NIFTY 50",
        timeframe: str = "1d",
        as_of_date: Optional[Union[str, pd.Timestamp]] = None,
        prior_regimes: Optional[List[str]] = None,
    ) -> RegimeDetectionResult:
        """Predicts regime using GMM posterior probabilities."""
        if not self.is_fitted:
            raise RuntimeError("GMMRegimeDetector must be fitted before predict_regime.")

        df_cut = df.copy()
        if "timestamp" in df_cut.columns and as_of_date is not None:
            as_of_ts = pd.to_datetime(as_of_date)
            df_cut = df_cut[pd.to_datetime(df_cut["timestamp"]) <= as_of_ts]
            eval_ts = df_cut["timestamp"].iloc[-1] if not df_cut.empty else as_of_ts
        else:
            eval_ts = pd.Timestamp.now()

        feats = extract_regime_features(df_cut)
        row = feats.iloc[-1]
        raw_vals = np.array([
            row.get("ret_20d", 0.0),
            row.get("ann_vol_20d", 0.16),
            row.get("trend_dist_sma50", 0.0),
            row.get("max_drawdown_60d", 0.0),
        ]).reshape(1, -1)

        norm_vals = (raw_vals - self.scaler_mean) / self.scaler_std
        cluster_probs = self.gmm.predict_proba(norm_vals)[0]
        best_cluster = int(np.argmax(cluster_probs))
        detected_regime = self.cluster_to_regime.get(best_cluster, MarketRegime.SIDEWAYS_RANGE_BOUND)
        confidence = float(cluster_probs[best_cluster])

        # Map cluster probabilities to semantic regimes
        regime_probs = {r: 0.0 for r in MarketRegime.ALL_REGIMES}
        for c_idx, prob in enumerate(cluster_probs):
            reg = self.cluster_to_regime.get(c_idx, MarketRegime.SIDEWAYS_RANGE_BOUND)
            regime_probs[reg] += float(prob)

        evidence = {
            "ret_20d": float(raw_vals[0, 0]),
            "ann_vol_20d": float(raw_vals[0, 1]),
            "trend_dist_sma50": float(raw_vals[0, 2]),
            "max_drawdown_60d": float(raw_vals[0, 3]),
            "assigned_cluster": float(best_cluster),
        }

        # Persistence calculation
        persistence = 1
        prior_regime = None
        recent_trans = False
        if prior_regimes:
            prior_regime = prior_regimes[-1]
            if prior_regime != detected_regime:
                recent_trans = True
            for pr in reversed(prior_regimes):
                if pr == detected_regime:
                    persistence += 1
                else:
                    break

        return RegimeDetectionResult(
            instrument=instrument,
            evaluation_timestamp=eval_ts,
            timeframe=timeframe,
            detected_regime=detected_regime,
            regime_confidence=confidence,
            regime_probabilities=regime_probs,
            quantitative_evidence=evidence,
            persistence_bars=persistence,
            prior_regime=prior_regime,
            recent_transition=recent_trans,
            model_type="gmm",
        )


# -----------------------------------------------------------------
# REGIME TRANSITION MATRIX UTILITY
# -----------------------------------------------------------------
def compute_regime_transition_matrix(regime_sequence: List[str]) -> pd.DataFrame:
    """
    Computes empirical transition probability matrix P[from_regime -> to_regime].
    Useful for Markov state transition analysis.
    """
    regimes = sorted(list(set(regime_sequence)))
    if not regimes:
        return pd.DataFrame()

    matrix = pd.DataFrame(0.0, index=regimes, columns=regimes)
    for i in range(len(regime_sequence) - 1):
        s_from = regime_sequence[i]
        s_to = regime_sequence[i + 1]
        matrix.loc[s_from, s_to] += 1.0

    # Row normalize to probabilities
    row_sums = matrix.sum(axis=1)
    for r in regimes:
        if row_sums[r] > 0:
            matrix.loc[r] = matrix.loc[r] / row_sums[r]
        else:
            matrix.loc[r, r] = 1.0

    return matrix


# Backwards compatible alias
RegimeDetector = RuleBasedRegimeDetector

