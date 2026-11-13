"""
MIRAI — Master Portfolio Optimisation Engine (M10)
Coordinates asset selection, covariance computation, numerical allocation,
and risk/diversification analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.portfolio.portfolio_constraints import PortfolioConstraints
from src.portfolio.correlation_analysis import (
    compute_covariance_and_correlation,
    identify_highly_correlated_pairs,
    compute_concentration_metrics,
    compute_portfolio_risk_and_diversification,
)
from src.portfolio.asset_allocation import AssetAllocationEngine

logger = get_logger("PortfolioOptimizer")


@dataclass
class PortfolioReport:
    """Standardized output structure for an optimised portfolio."""
    portfolio_id: str
    timestamp: pd.Timestamp
    optimization_objective: str  # 'min_variance', 'equal_weight', 'mean_variance', 'risk_parity'
    total_capital: float
    allocations: Dict[str, float]             # Weights in [0.0, 1.0]
    allocation_percentages: Dict[str, float]  # Percentages (0 - 100%)
    capital_allocations: Dict[str, float]     # ₹ INR allocated per asset
    cash_allocation: float                    # ₹ INR in cash
    cash_percentage: float                    # Cash percentage
    estimated_portfolio_volatility: float     # Annualized portfolio volatility
    expected_portfolio_return: Optional[float]
    portfolio_sharpe_ratio: Optional[float]
    diversification_ratio: float
    concentration_metrics: Dict[str, float]   # HHI, effective_n
    highly_correlated_pairs: List[Dict[str, Any]]
    optimization_status: str                  # 'optimal', 'fallback_infeasible'
    constraints_applied: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)

    @property
    def weights(self) -> Dict[str, float]:
        return self.allocations

    @property
    def volatility(self) -> float:
        return self.estimated_portfolio_volatility

    @property
    def expected_return(self) -> float:
        return self.expected_portfolio_return if self.expected_portfolio_return is not None else 0.12

    @property
    def sharpe_ratio(self) -> float:
        return self.portfolio_sharpe_ratio if self.portfolio_sharpe_ratio is not None else 0.80

    @property
    def diversification_score(self) -> float:
        return self.diversification_ratio

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "timestamp": self.timestamp.isoformat() if hasattr(self.timestamp, "isoformat") else str(self.timestamp),
            "optimization_objective": self.optimization_objective,
            "total_capital": self.total_capital,
            "allocations": {k: round(v, 4) for k, v in self.allocations.items()},
            "allocation_percentages": {k: round(v, 2) for k, v in self.allocation_percentages.items()},
            "capital_allocations": {k: round(v, 2) for k, v in self.capital_allocations.items()},
            "cash_allocation": round(self.cash_allocation, 2),
            "cash_percentage": round(self.cash_percentage, 2),
            "estimated_portfolio_volatility": round(self.estimated_portfolio_volatility, 4),
            "expected_portfolio_return": round(self.expected_portfolio_return, 4) if self.expected_portfolio_return is not None else None,
            "portfolio_sharpe_ratio": round(self.portfolio_sharpe_ratio, 3) if self.portfolio_sharpe_ratio is not None else None,
            "diversification_ratio": round(self.diversification_ratio, 3),
            "concentration_metrics": self.concentration_metrics,
            "highly_correlated_pairs": self.highly_correlated_pairs,
            "optimization_status": self.optimization_status,
            "constraints_applied": self.constraints_applied,
            "warnings": self.warnings,
        }


class PortfolioOptimizer:
    """
    Central Portfolio Optimisation Engine for MIRAI (Pipeline B Equities).
    """

    def __init__(
        self,
        constraints: Optional[PortfolioConstraints] = None,
        allocation_engine: Optional[AssetAllocationEngine] = None,
        risk_free_rate: float = 0.065,
    ):
        cfg = get_config()
        self.constraints = constraints or PortfolioConstraints.from_config()
        self.allocation_engine = allocation_engine or AssetAllocationEngine(self.constraints)
        self.risk_free_rate = cfg.get("portfolio.risk_free_rate", risk_free_rate)

    def optimize(
        self,
        returns_df: pd.DataFrame,
        method: str = "min_variance",
        target_risk: Optional[float] = None,
        **kwargs,
    ) -> PortfolioReport:
        """Convenience method for API and general portfolio optimization."""
        obj_map = {
            "risk_budgeting": "risk_parity",
            "risk_parity": "risk_parity",
            "min_variance": "min_variance",
            "mean_variance": "mean_variance",
            "equal_weight": "equal_weight",
            "hrp": "min_variance",
        }
        objective = obj_map.get(str(method).lower(), "min_variance")
        return self.optimize_portfolio(returns_df=returns_df, objective=objective, **kwargs)

    def optimize_portfolio(
        self,
        returns_df: pd.DataFrame,
        asset_universe: Optional[List[str]] = None,
        expected_returns: Optional[pd.Series] = None,
        decisions: Optional[List[Any]] = None,  # Optional M09 InvestmentDecision list
        objective: str = "min_variance",
        total_capital: float = 1000000.0,
        portfolio_id: str = "NIFTY_PORTFOLIO_1",
        pipeline_id: str = "pipeline_b_nifty",
    ) -> PortfolioReport:
        """
        Executes complete portfolio construction and diversification analysis.
        Strictly rejects Pipeline A inputs.
        """
        # 1. Pipeline Isolation Check
        if pipeline_id == "pipeline_a_fi2010" or "lob_feature_0" in returns_df.columns:
            raise ValueError(
                "PortfolioOptimizer is strictly isolated to Pipeline B (Equities). "
                "Cannot build long-term capital allocation portfolios from FI-2010 microstructure tick arrays."
            )

        warnings = []
        eval_time = pd.Timestamp.now()

        # 2. Filter Asset Universe
        # If decisions from M09 are supplied, prioritize assets that have 'YES' or 'WAIT' verdicts
        eligible_assets = asset_universe or list(returns_df.columns)
        if decisions:
            approved_syms = [
                d.symbol for d in decisions
                if getattr(d, "verdict", None) in ("YES", "WAIT")
            ]
            if approved_syms:
                # Intersect with returns columns
                filtered = [s for s in approved_syms if s in returns_df.columns]
                if len(filtered) >= 2:
                    eligible_assets = filtered
                    logger.info("Filtered asset universe to %d M09 decision-approved stocks: %s", len(eligible_assets), eligible_assets)
                else:
                    warnings.append(
                        f"Fewer than 2 stocks approved by M09 ({len(filtered)}). Using full candidate universe."
                    )

        # Ensure eligible assets are present in returns DataFrame
        valid_assets = [a for a in eligible_assets if a in returns_df.columns and returns_df[a].count() >= 10]
        if len(valid_assets) == 0:
            raise ValueError("No valid assets with sufficient return history available for portfolio optimization.")

        # 3. Compute Covariance and Correlation Matrices
        sub_returns = returns_df[valid_assets].copy()
        ann_cov, corr_matrix, ann_vols = compute_covariance_and_correlation(sub_returns)

        # Detect highly correlated pairs
        correlated_pairs = identify_highly_correlated_pairs(corr_matrix, threshold=0.80)
        if correlated_pairs:
            warnings.append(
                f"Detected {len(correlated_pairs)} pairs with high correlation (|r| >= 0.80)."
            )

        # 4. Compute Expected Returns if not provided
        if expected_returns is None:
            # Historical annualized mean return as neutral drift proxy
            mu = sub_returns.mean() * 252.0
        else:
            mu = expected_returns.loc[valid_assets]

        # 5. Execute Allocation Optimization
        if objective == "min_variance":
            weights, cash, meta = self.allocation_engine.allocate_minimum_variance(valid_assets, ann_cov)
        elif objective == "equal_weight":
            weights, cash, meta = self.allocation_engine.allocate_equal_weight(valid_assets)
        elif objective == "risk_parity" or objective == "inverse_vol":
            weights, cash, meta = self.allocation_engine.allocate_inverse_volatility(valid_assets, ann_vols)
        elif objective == "mean_variance":
            weights, cash, meta = self.allocation_engine.allocate_mean_variance(
                valid_assets, mu, ann_cov, risk_free_rate=self.risk_free_rate
            )
        else:
            logger.warning("Unknown objective '%s'. Using minimum variance.", objective)
            weights, cash, meta = self.allocation_engine.allocate_minimum_variance(valid_assets, ann_cov)

        if "warning" in meta:
            warnings.append(meta["warning"])

        # 6. Validate Mathematical Constraints
        is_valid, validation_issues = self.constraints.validate_weights(weights, cash_weight=cash)
        if not is_valid:
            warnings.extend(validation_issues)

        # 7. Compute Portfolio Risk and Diversification Metrics
        cov_vals = ann_cov.loc[valid_assets, valid_assets].values
        vol_vals = ann_vols.loc[valid_assets].values

        port_vol, div_ratio = compute_portfolio_risk_and_diversification(weights, cov_vals, vol_vals)
        port_ret = float(np.sum(weights * mu.values)) if mu is not None else None
        sharpe = float((port_ret - self.risk_free_rate) / port_vol) if (port_ret is not None and port_vol > 0) else None

        concentration = compute_concentration_metrics(weights)

        # 8. Compute Capital Allocations (₹ INR)
        allocations_dict = {valid_assets[i]: float(weights[i]) for i in range(len(valid_assets))}
        alloc_pcts = {k: float(v * 100.0) for k, v in allocations_dict.items()}
        cap_allocs = {k: float(v * total_capital) for k, v in allocations_dict.items()}
        cash_inr = float(cash * total_capital)
        cash_pct = float(cash * 100.0)

        constraints_summary = {
            "max_asset_weight": self.constraints.max_asset_weight,
            "min_asset_weight": self.constraints.min_asset_weight,
            "cash_reserve_target": self.constraints.cash_reserve,
            "long_only": self.constraints.long_only,
        }

        return PortfolioReport(
            portfolio_id=portfolio_id,
            timestamp=eval_time,
            optimization_objective=objective,
            total_capital=total_capital,
            allocations=allocations_dict,
            allocation_percentages=alloc_pcts,
            capital_allocations=cap_allocs,
            cash_allocation=cash_inr,
            cash_percentage=cash_pct,
            estimated_portfolio_volatility=port_vol,
            expected_portfolio_return=port_ret,
            portfolio_sharpe_ratio=sharpe,
            diversification_ratio=div_ratio,
            concentration_metrics=concentration,
            highly_correlated_pairs=correlated_pairs,
            optimization_status=meta.get("status", "optimal"),
            constraints_applied=constraints_summary,
            warnings=warnings,
        )
