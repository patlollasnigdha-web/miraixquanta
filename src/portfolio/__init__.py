"""
MIRAI — Portfolio Optimisation Package (M10)
"""

from src.portfolio.portfolio_constraints import PortfolioConstraints
from src.portfolio.correlation_analysis import (
    compute_covariance_and_correlation,
    identify_highly_correlated_pairs,
    compute_concentration_metrics,
    compute_portfolio_risk_and_diversification,
)
from src.portfolio.asset_allocation import AssetAllocationEngine
from src.portfolio.portfolio_optimizer import (
    PortfolioOptimizer,
    PortfolioReport,
)

__all__ = [
    "PortfolioConstraints",
    "compute_covariance_and_correlation",
    "identify_highly_correlated_pairs",
    "compute_concentration_metrics",
    "compute_portfolio_risk_and_diversification",
    "AssetAllocationEngine",
    "PortfolioOptimizer",
    "PortfolioReport",
]
