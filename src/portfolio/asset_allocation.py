"""
MIRAI — Portfolio Asset Allocation Algorithms (M10)
Implements Equal-Weight, Minimum-Variance, Mean-Variance (Max Sharpe), and Risk-Parity allocation.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.utils.logger import get_logger
from src.portfolio.portfolio_constraints import PortfolioConstraints

logger = get_logger("AssetAllocation")


class AssetAllocationEngine:
    """
    Executes numerical portfolio optimisation across multiple objective functions
    under user-defined constraints.
    """

    def __init__(self, constraints: Optional[PortfolioConstraints] = None):
        self.constraints = constraints or PortfolioConstraints.from_config()

    # -------------------------------------------------------------
    # 1. EQUAL-WEIGHT ALLOCATION (BASELINE)
    # -------------------------------------------------------------
    def allocate_equal_weight(
        self,
        asset_names: List[str],
    ) -> Tuple[np.ndarray, float, Dict[str, Any]]:
        """
        Baseline equal-weight allocation: w_i = (1 - cash_reserve) / N.
        """
        n = len(asset_names)
        if n == 0:
            raise ValueError("Asset universe cannot be empty.")

        cash = self.constraints.cash_reserve
        investable = 1.0 - cash
        w_each = investable / n

        # Check against max_asset_weight
        if w_each > self.constraints.max_asset_weight:
            logger.warning(
                "Equal-weight (%0.3f) exceeds max_asset_weight (%0.3f). Capping.",
                w_each, self.constraints.max_asset_weight
            )
            weights = np.full(n, self.constraints.max_asset_weight)
            cash = 1.0 - float(np.sum(weights))
        else:
            weights = np.full(n, w_each)

        meta = {"method": "equal_weight", "status": "optimal", "cash_reserve": cash}
        return weights, cash, meta

    # -------------------------------------------------------------
    # 2. INVERSE-VOLATILITY / RISK-PARITY ALLOCATION
    # -------------------------------------------------------------
    def allocate_inverse_volatility(
        self,
        asset_names: List[str],
        asset_vols: pd.Series,
    ) -> Tuple[np.ndarray, float, Dict[str, Any]]:
        """
        Allocates inversely proportional to asset volatility: w_i ~ 1 / sigma_i.
        Assets with lower volatility receive higher allocations.
        """
        n = len(asset_names)
        vols = asset_vols.loc[asset_names].values
        inv_vols = 1.0 / np.maximum(vols, 1e-4)

        cash = self.constraints.cash_reserve
        investable = 1.0 - cash

        # Unconstrained weights
        raw_w = (inv_vols / np.sum(inv_vols)) * investable

        # Iterative redistribution up to max_asset_weight
        w = raw_w.copy()
        max_w = self.constraints.max_asset_weight
        for _ in range(10):
            capped = w >= max_w - 1e-7
            if not np.any(capped) or np.all(capped):
                break
            excess = float(np.sum(w[capped] - max_w))
            w[capped] = max_w
            uncapped = ~capped
            if np.sum(uncapped) == 0:
                break
            uncapped_sum = float(np.sum(w[uncapped]))
            if uncapped_sum > 0:
                w[uncapped] += excess * (w[uncapped] / uncapped_sum)
            else:
                w[uncapped] += excess / float(np.sum(uncapped))
            w = np.clip(w, 0.0, max_w)

        actual_invested = float(np.sum(w))
        final_cash = float(1.0 - actual_invested)

        meta = {"method": "inverse_volatility", "status": "optimal", "cash_reserve": final_cash}
        return w, final_cash, meta

    # -------------------------------------------------------------
    # 3. MINIMUM-VARIANCE OPTIMISATION
    # -------------------------------------------------------------
    def allocate_minimum_variance(
        self,
        asset_names: List[str],
        cov_matrix: pd.DataFrame,
    ) -> Tuple[np.ndarray, float, Dict[str, Any]]:
        """
        Solves: min_w (w^T * Sigma * w)
        s.t. sum(w_i) = 1 - cash_reserve, 0 <= w_i <= max_weight.
        """
        n = len(asset_names)
        feasible, reason = self.constraints.check_feasibility(n)
        if not feasible:
            logger.warning("Constraints infeasible (%s). Falling back to equal weight.", reason)
            weights, cash, _ = self.allocate_equal_weight(asset_names)
            return weights, cash, {"method": "min_variance", "status": "fallback_infeasible", "warning": reason}

        cash = self.constraints.cash_reserve
        target_sum = 1.0 - cash
        sigma = cov_matrix.loc[asset_names, asset_names].values

        # Objective function: portfolio variance
        def objective(w: np.ndarray) -> float:
            return float(w.T @ sigma @ w)

        def gradient(w: np.ndarray) -> np.ndarray:
            return 2.0 * (sigma @ w)

        # Initial guess: equal weight
        w0 = np.full(n, target_sum / n)

        # Bounds: [0, max_asset_weight]
        bounds = [(0.0, self.constraints.max_asset_weight) for _ in range(n)]

        # Constraint: sum(w) == target_sum
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - target_sum}]

        res = minimize(
            objective,
            w0,
            method="SLSQP",
            jac=gradient,
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 500, "ftol": 1e-9},
        )

        if res.success:
            weights = np.clip(res.x, 0.0, self.constraints.max_asset_weight)
            # Re-normalize to exact target sum
            weights = (weights / np.sum(weights)) * target_sum
            meta = {"method": "min_variance", "status": "optimal", "cash_reserve": cash, "nit": res.nit}
            return weights, cash, meta
        else:
            logger.warning("Min-variance solver failed (%s). Falling back to inverse vol.", res.message)
            vols = pd.Series(np.sqrt(np.diag(sigma)), index=asset_names)
            return self.allocate_inverse_volatility(asset_names, vols)

    # -------------------------------------------------------------
    # 4. MEAN-VARIANCE OPTIMISATION (MAXIMUM SHARPE RATIO)
    # -------------------------------------------------------------
    def allocate_mean_variance(
        self,
        asset_names: List[str],
        expected_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        risk_free_rate: float = 0.065,
    ) -> Tuple[np.ndarray, float, Dict[str, Any]]:
        """
        Solves: max_w (w^T * mu - r_f) / sqrt(w^T * Sigma * w)
        s.t. sum(w_i) = 1 - cash_reserve, 0 <= w_i <= max_weight.
        """
        n = len(asset_names)
        feasible, reason = self.constraints.check_feasibility(n)
        if not feasible:
            logger.warning("Constraints infeasible (%s). Falling back to equal weight.", reason)
            return self.allocate_equal_weight(asset_names)

        cash = self.constraints.cash_reserve
        target_sum = 1.0 - cash
        sigma = cov_matrix.loc[asset_names, asset_names].values
        mu = expected_returns.loc[asset_names].values

        # Objective: minimize negative Sharpe ratio
        def neg_sharpe(w: np.ndarray) -> float:
            p_ret = float(w.T @ mu)
            p_vol = float(np.sqrt(max(w.T @ sigma @ w, 1e-8)))
            return -float((p_ret - risk_free_rate) / p_vol)

        w0 = np.full(n, target_sum / n)
        bounds = [(0.0, self.constraints.max_asset_weight) for _ in range(n)]
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - target_sum}]

        res = minimize(
            neg_sharpe,
            w0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 500, "ftol": 1e-9},
        )

        if res.success:
            weights = np.clip(res.x, 0.0, self.constraints.max_asset_weight)
            weights = (weights / np.sum(weights)) * target_sum
            meta = {
                "method": "mean_variance",
                "status": "optimal",
                "cash_reserve": cash,
                "optimized_sharpe": -float(res.fun),
            }
            return weights, cash, meta
        else:
            logger.warning("Mean-variance solver failed (%s). Falling back to min-variance.", res.message)
            return self.allocate_minimum_variance(asset_names, cov_matrix)
