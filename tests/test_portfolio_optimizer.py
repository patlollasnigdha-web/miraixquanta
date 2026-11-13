"""
Unit and Integration Tests for Portfolio Optimisation Engine (M10).
Tests constraints, correlation analysis, concentration metrics, diversification ratio,
asset allocation strategies (Equal-Weight, Inverse-Vol, Min-Variance, Mean-Variance),
and Pipeline A isolation.
"""

import numpy as np
import pandas as pd
import pytest

from src.portfolio.portfolio_constraints import PortfolioConstraints
from src.portfolio.correlation_analysis import (
    compute_covariance_and_correlation,
    identify_highly_correlated_pairs,
    compute_concentration_metrics,
    compute_portfolio_risk_and_diversification,
)
from src.portfolio.asset_allocation import AssetAllocationEngine
from src.portfolio.portfolio_optimizer import PortfolioOptimizer, PortfolioReport


@pytest.fixture
def sample_returns_df():
    """Generates synthetic daily returns for 4 assets over 100 days."""
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=100, freq="B")
    ret_a = np.random.normal(0.0008, 0.015, 100) # High vol, positive return
    ret_b = np.random.normal(0.0005, 0.010, 100) # Low vol, moderate return
    ret_c = 0.8 * ret_a + np.random.normal(0.0, 0.005, 100) # Highly correlated with A
    ret_d = np.random.normal(0.0003, 0.008, 100) # Very low vol
    df = pd.DataFrame({"RELIANCE": ret_a, "TCS": ret_b, "INFY": ret_c, "HDFCBANK": ret_d}, index=dates)
    return df


def test_portfolio_constraints_validation():
    """Tests validation rules for PortfolioConstraints."""
    # Valid constraints
    c = PortfolioConstraints(max_asset_weight=0.30, min_asset_weight=0.05, cash_reserve=0.10)
    assert c.investable_weight == pytest.approx(0.90)

    # Infeasible: min_asset_weight > max_asset_weight
    with pytest.raises(ValueError, match="min_asset_weight"):
        PortfolioConstraints(max_asset_weight=0.10, min_asset_weight=0.20)

    # Infeasible cash reserve
    with pytest.raises(ValueError, match="cash_reserve must be in"):
        PortfolioConstraints(cash_reserve=1.2)


def test_portfolio_constraints_feasibility():
    """Tests feasibility check for given universe size."""
    c = PortfolioConstraints(max_asset_weight=0.20, min_asset_weight=0.05, cash_reserve=0.10)
    # 4 assets * 0.20 max = 0.80 max exposure < 0.90 investable -> infeasible
    is_feasible, reason = c.check_feasibility(n_assets=4)
    assert not is_feasible
    assert reason is not None
    assert "Infeasible" in reason

    # 5 assets * 0.20 = 1.0 >= 0.90 -> feasible
    is_feasible, reason = c.check_feasibility(n_assets=5)
    assert is_feasible
    assert reason is None


def test_correlation_and_covariance_analysis(sample_returns_df):
    """Tests covariance, correlation, and high-correlation pair detection."""
    cov, corr, vols = compute_covariance_and_correlation(sample_returns_df)
    assert cov.shape == (4, 4)
    assert corr.shape == (4, 4)
    assert len(vols) == 4
    assert np.allclose(np.diag(corr), 1.0)

    # Check high correlation detection between RELIANCE and INFY
    high_pairs = identify_highly_correlated_pairs(corr, threshold=0.70)
    assert len(high_pairs) >= 1
    found = any(
        (p["asset_1"] == "RELIANCE" and p["asset_2"] == "INFY") or
        (p["asset_1"] == "INFY" and p["asset_2"] == "RELIANCE")
        for p in high_pairs
    )
    assert found


def test_concentration_and_diversification_metrics(sample_returns_df):
    """Tests HHI, effective N, and diversification ratio."""
    weights = np.array([0.25, 0.25, 0.25, 0.25])
    metrics = compute_concentration_metrics(weights)
    assert metrics["hhi"] == pytest.approx(0.25)
    assert metrics["effective_n"] == pytest.approx(4.0)

    # Concentrated weights
    conc_weights = np.array([0.70, 0.10, 0.10, 0.10])
    conc_metrics = compute_concentration_metrics(conc_weights)
    assert conc_metrics["hhi"] == pytest.approx(0.49 + 0.03)
    assert conc_metrics["effective_n"] < 2.0

    # Diversification ratio
    cov, _, vols = compute_covariance_and_correlation(sample_returns_df)
    port_vol, div_ratio = compute_portfolio_risk_and_diversification(weights, cov.values, vols.values)
    assert port_vol > 0.0
    # Diversification ratio >= 1.0 for non-perfectly correlated assets
    assert div_ratio >= 1.0


def test_asset_allocation_equal_weight():
    """Tests equal-weight allocation with cash reserve."""
    engine = AssetAllocationEngine()
    symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]
    weights, cash, meta = engine.allocate_equal_weight(symbols)
    # Investable = 0.95 (default 5% cash), so 0.95 / 4 = 0.2375
    assert len(weights) == 4
    for w in weights:
        assert w == pytest.approx(0.95 / 4.0, abs=1e-4)
    assert np.sum(weights) == pytest.approx(0.95, abs=1e-4)
    assert cash == pytest.approx(0.05, abs=1e-4)


def test_asset_allocation_inverse_volatility(sample_returns_df):
    """Tests inverse volatility allocation."""
    engine = AssetAllocationEngine()
    symbols = list(sample_returns_df.columns)
    _, _, vols = compute_covariance_and_correlation(sample_returns_df)
    weights, cash, meta = engine.allocate_inverse_volatility(symbols, vols)

    # Total weight should equal investable weight (0.95)
    assert np.sum(weights) == pytest.approx(0.95, abs=1e-3)
    # Asset D (HDFCBANK, index 3) has lowest vol, so it should receive higher weight than A (RELIANCE, index 0)
    assert weights[3] > weights[0]


def test_asset_allocation_minimum_variance(sample_returns_df):
    """Tests minimum-variance portfolio allocation using SLSQP."""
    engine = AssetAllocationEngine()
    symbols = list(sample_returns_df.columns)
    cov, _, _ = compute_covariance_and_correlation(sample_returns_df)
    weights, cash, meta = engine.allocate_minimum_variance(symbols, cov)

    # Verify bounds and budget
    assert np.sum(weights) == pytest.approx(0.95, abs=1e-3)
    for w in weights:
        assert w <= 0.25 + 1e-4 # max_asset_weight
        assert w >= 0.0 - 1e-4


def test_asset_allocation_mean_variance(sample_returns_df):
    """Tests mean-variance (Max Sharpe) allocation."""
    engine = AssetAllocationEngine()
    symbols = list(sample_returns_df.columns)
    expected_returns = sample_returns_df.mean() * 252 # Annualized
    cov, _, _ = compute_covariance_and_correlation(sample_returns_df)
    weights, cash, meta = engine.allocate_mean_variance(symbols, expected_returns, cov)

    assert np.sum(weights) == pytest.approx(0.95, abs=1e-3)
    for w in weights:
        assert w <= 0.25 + 1e-4


def test_pipeline_a_isolation_in_portfolio(sample_returns_df):
    """Verifies that PortfolioOptimizer strictly rejects Pipeline A (FI-2010 microstructure) inputs."""
    optimizer = PortfolioOptimizer()
    with pytest.raises(ValueError, match="strictly isolated to Pipeline B"):
        optimizer.optimize_portfolio(sample_returns_df, pipeline_id="pipeline_a_fi2010")


def test_portfolio_optimizer_full_flow(sample_returns_df):
    """Tests end-to-end PortfolioOptimizer execution and report generation."""
    optimizer = PortfolioOptimizer()
    report = optimizer.optimize_portfolio(
        returns_df=sample_returns_df,
        pipeline_id="pipeline_b_nifty",
        objective="min_variance",
        asset_universe=["RELIANCE", "TCS", "INFY", "HDFCBANK"],
    )

    assert isinstance(report, PortfolioReport)
    assert report.optimization_objective == "min_variance"
    assert report.cash_percentage == pytest.approx(5.0, abs=0.1)
    assert report.estimated_portfolio_volatility > 0.0
    assert report.diversification_ratio >= 1.0
    assert len(report.allocations) == 4
    assert sum(report.allocations.values()) == pytest.approx(0.95, abs=1e-3)

    report_dict = report.to_dict()
    assert "allocations" in report_dict
    assert "concentration_metrics" in report_dict
    assert "estimated_portfolio_volatility" in report_dict
