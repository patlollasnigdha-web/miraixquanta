"""
MIRAI — Unit Tests for Market Regime Detection (M07) and Integrated Intelligence
"""

import numpy as np
import pandas as pd
import pytest

from src.intelligence.regime_detection import (
    MarketRegime,
    RuleBasedRegimeDetector,
    GMMRegimeDetector,
    RegimeDetectionResult,
    extract_regime_features,
    compute_regime_transition_matrix,
)
from src.intelligence.market_intelligence import (
    MarketIntelligenceService,
    IntegratedStockIntelligence,
)


def _create_synthetic_index_data(
    n_bars: int = 200,
    regime_scenario: str = "bullish",
    start_date: str = "2023-01-01",
) -> pd.DataFrame:
    """Generates synthetic index daily data for distinct regime scenarios."""
    np.random.seed(42)
    dates = pd.date_range(start_date, periods=n_bars, freq="D")

    if regime_scenario == "bullish":
        # Upward drift, moderate volatility
        vol_scale = 0.008
        rets = np.random.normal(loc=0.0015, scale=vol_scale, size=n_bars)
    elif regime_scenario == "bearish":
        # Downward drift
        vol_scale = 0.012
        rets = np.random.normal(loc=-0.0018, scale=vol_scale, size=n_bars)
    elif regime_scenario == "stress":
        # Sharp drawdown + high volatility
        vol_scale = 0.025
        rets = np.random.normal(loc=-0.003, scale=vol_scale, size=n_bars)
    elif regime_scenario == "low_vol":
        # Flat drift, extremely low volatility
        vol_scale = 0.003
        rets = np.random.normal(loc=0.0001, scale=vol_scale, size=n_bars)
    else:  # sideways
        vol_scale = 0.009
        rets = np.random.normal(loc=0.0, scale=vol_scale, size=n_bars)

    prices = 18000.0 * np.exp(np.cumsum(rets))
    highs = prices * (1.0 + np.abs(np.random.normal(0, vol_scale * 0.8, size=n_bars)))
    lows = prices * (1.0 - np.abs(np.random.normal(0, vol_scale * 0.8, size=n_bars)))
    opens = (highs + lows) / 2.0
    vols = np.random.uniform(1e7, 2e7, size=n_bars)

    return pd.DataFrame({
        "timestamp": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": prices,
        "volume": vols,
    })


def test_extract_regime_features():
    """Verify quantitative regime features are calculated without NaNs in warm regions."""
    df = _create_synthetic_index_data(n_bars=80)
    feats = extract_regime_features(df)

    assert "ret_20d" in feats.columns
    assert "ann_vol_20d" in feats.columns
    assert "trend_dist_sma50" in feats.columns
    assert "max_drawdown_60d" in feats.columns
    assert "vol_percentile_252d" in feats.columns

    # Check last row values
    last = feats.iloc[-1]
    assert not np.isnan(last["ret_20d"])
    assert last["ann_vol_20d"] > 0
    assert last["max_drawdown_60d"] <= 0.0


def test_rule_based_regime_scenarios():
    """Verify rule-based detector distinguishes bullish, stress, and low volatility scenarios."""
    detector = RuleBasedRegimeDetector()

    # 1. Bullish scenario
    df_bull = _create_synthetic_index_data(n_bars=100, regime_scenario="bullish")
    res_bull = detector.predict_regime(df_bull, "NIFTY 50", timeframe="1d")
    assert res_bull.detected_regime in (MarketRegime.BULLISH_TRENDING, MarketRegime.LOW_VOLATILITY)
    assert res_bull.regime_confidence > 0.6
    assert pytest.approx(sum(res_bull.regime_probabilities.values()), 0.01) == 1.0

    # 2. Stress scenario
    df_stress = _create_synthetic_index_data(n_bars=100, regime_scenario="stress")
    res_stress = detector.predict_regime(df_stress, "NIFTY 50", timeframe="1d")
    assert res_stress.detected_regime in (MarketRegime.STRESS_ABNORMAL, MarketRegime.HIGH_VOLATILITY, MarketRegime.BEARISH_TRENDING)

    # 3. Low volatility scenario
    df_low = _create_synthetic_index_data(n_bars=100, regime_scenario="low_vol")
    res_low = detector.predict_regime(df_low, "NIFTY 50", timeframe="1d")
    assert res_low.detected_regime in (MarketRegime.LOW_VOLATILITY, MarketRegime.SIDEWAYS_RANGE_BOUND)


def test_gmm_regime_clustering_and_semantic_mapping():
    """Verify GMM detector fits, interprets clusters semantically, and returns valid posteriors."""
    df_train = _create_synthetic_index_data(n_bars=180, regime_scenario="bullish")
    # Concatenate with a stress period to ensure diverse regimes in train set
    df_stress = _create_synthetic_index_data(n_bars=60, regime_scenario="stress", start_date="2023-07-01")
    df_all = pd.concat([df_train, df_stress]).reset_index(drop=True)

    gmm_det = GMMRegimeDetector(n_components=3, random_state=42)
    gmm_det.fit(df_all)

    assert gmm_det.is_fitted is True
    assert len(gmm_det.cluster_to_regime) == 3
    # Check that assigned regimes are valid MarketRegime values
    for c_id, reg in gmm_det.cluster_to_regime.items():
        assert reg in MarketRegime.ALL_REGIMES

    # Predict on test slice
    res = gmm_det.predict_regime(df_all, "NIFTY 50", as_of_date=df_all["timestamp"].iloc[-1])
    assert isinstance(res, RegimeDetectionResult)
    assert res.detected_regime in MarketRegime.ALL_REGIMES
    assert 0.0 <= res.regime_confidence <= 1.0
    assert pytest.approx(sum(res.regime_probabilities.values()), 0.01) == 1.0


def test_regime_persistence_and_transitions():
    """Verify persistence counter and transition detection across sequence."""
    detector = RuleBasedRegimeDetector()
    df = _create_synthetic_index_data(n_bars=80)

    # Previous 3 periods were also detected regime
    res1 = detector.predict_regime(df, prior_regimes=["BULLISH_TRENDING", "BULLISH_TRENDING"])
    if res1.detected_regime == "BULLISH_TRENDING":
        assert res1.persistence_bars >= 3
        assert res1.recent_transition is False

    # Previous was opposite regime -> transition detected
    res2 = detector.predict_regime(df, prior_regimes=["STRESS_ABNORMAL"])
    if res2.detected_regime != "STRESS_ABNORMAL":
        assert res2.recent_transition is True
        assert res2.prior_regime == "STRESS_ABNORMAL"


def test_regime_transition_matrix():
    """Verify transition matrix sums to 1 across rows."""
    sequence = [
        "BULLISH_TRENDING", "BULLISH_TRENDING", "SIDEWAYS_RANGE_BOUND",
        "SIDEWAYS_RANGE_BOUND", "HIGH_VOLATILITY", "BULLISH_TRENDING"
    ]
    matrix = compute_regime_transition_matrix(sequence)
    assert not matrix.empty
    for r in matrix.index:
        assert pytest.approx(matrix.loc[r].sum(), 0.01) == 1.0


def test_integrated_market_intelligence_service():
    """Verify MarketIntelligenceService coordinates M05, M06, and M07 seamlessly."""
    df_stock = _create_synthetic_index_data(n_bars=80, regime_scenario="bullish")
    df_bench = _create_synthetic_index_data(n_bars=80, regime_scenario="bullish")

    service = MarketIntelligenceService()
    intel = service.get_stock_intelligence(
        df_stock=df_stock,
        symbol="RELIANCE",
        df_benchmark=df_bench,
        as_of_date=df_stock["timestamp"].iloc[-1],
    )

    assert isinstance(intel, IntegratedStockIntelligence)
    assert intel.symbol == "RELIANCE"
    assert intel.stock_strength.overall_score >= 0.0
    assert intel.market_regime_daily.detected_regime in MarketRegime.ALL_REGIMES
    assert len(intel.composite_assessment) > 20
    assert isinstance(intel.key_drivers, list)
    assert isinstance(intel.risk_factors, list)

    report_dict = intel.to_dict()
    assert "stock_strength" in report_dict
    assert "market_regime_daily" in report_dict
    assert "composite_assessment" in report_dict
