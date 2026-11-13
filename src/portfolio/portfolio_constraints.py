"""
MIRAI — Portfolio Constraints and Validation (M10)
Defines portfolio-level investment boundaries, cash reserves, and mathematical validity checks.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger("PortfolioConstraints")


@dataclass
class PortfolioConstraints:
    """
    Mathematical and operational boundaries for portfolio construction.
    """
    max_asset_weight: float = 0.25      # Max 25% allocation to any single asset
    min_asset_weight: float = 0.0       # Minimum allocation for selected assets
    cash_reserve: float = 0.05          # Cash buffer [0.0, 1.0]
    max_total_exposure: float = 0.95    # Max invested fraction (1.0 - cash_reserve)
    max_holdings: Optional[int] = None  # Maximum number of active assets in portfolio
    long_only: bool = True              # Strict long-only constraint (w_i >= 0)
    sector_limits: Optional[Dict[str, float]] = None

    def __post_init__(self):
        # Ensure cash_reserve + max_total_exposure <= 1.0
        if self.cash_reserve < 0.0 or self.cash_reserve > 1.0:
            raise ValueError(f"cash_reserve must be in [0.0, 1.0], got {self.cash_reserve}")
        if self.max_asset_weight <= 0.0 or self.max_asset_weight > 1.0:
            raise ValueError(f"max_asset_weight must be in (0.0, 1.0], got {self.max_asset_weight}")

        if self.min_asset_weight > self.max_asset_weight:
            raise ValueError(
                f"min_asset_weight ({self.min_asset_weight}) cannot exceed max_asset_weight ({self.max_asset_weight})"
            )

        # Sync max_total_exposure if default
        if self.max_total_exposure > (1.0 - self.cash_reserve + 1e-6):
            self.max_total_exposure = float(1.0 - self.cash_reserve)

    @property
    def investable_weight(self) -> float:
        """Portion of portfolio available for risky asset allocation."""
        return float(1.0 - self.cash_reserve)

    @classmethod
    def from_config(cls) -> "PortfolioConstraints":
        """Instantiates constraints from central configuration file."""
        cfg = get_config()
        return cls(
            max_asset_weight=cfg.get("portfolio.max_asset_weight", 0.25),
            min_asset_weight=cfg.get("portfolio.min_asset_weight", 0.0),
            cash_reserve=cfg.get("portfolio.cash_reserve", 0.05),
            max_total_exposure=cfg.get("portfolio.max_total_exposure", 0.95),
            long_only=cfg.get("portfolio.long_only", True),
        )

    def check_feasibility(self, n_assets: int) -> Tuple[bool, Optional[str]]:
        """
        Validates whether constraints are mathematically satisfiable for n_assets.
        """
        if n_assets == 0:
            return False, "Cannot construct portfolio with 0 assets."

        investable_target = 1.0 - self.cash_reserve

        # Condition 1: Can we allocate the minimum weights without exceeding target?
        if (n_assets * self.min_asset_weight) > (investable_target + 1e-6):
            return False, (
                f"Infeasible: {n_assets} assets * min_weight ({self.min_asset_weight}) = "
                f"{n_assets * self.min_asset_weight:.2f} > investable target ({investable_target:.2f})."
            )

        # Condition 2: Can we reach the investable target with the maximum weights?
        if (n_assets * self.max_asset_weight) < (investable_target - 1e-6):
            return False, (
                f"Infeasible: {n_assets} assets * max_weight ({self.max_asset_weight}) = "
                f"{n_assets * self.max_asset_weight:.2f} < investable target ({investable_target:.2f}). "
                f"Increase asset universe or raise max_asset_weight."
            )

        return True, None

    def validate_weights(
        self,
        weights: np.ndarray,
        cash_weight: Optional[float] = None,
        tolerance: float = 1e-4,
    ) -> Tuple[bool, List[str]]:
        """
        Validates that computed portfolio weights satisfy all mathematical constraints.
        """
        issues = []
        cw = self.cash_reserve if cash_weight is None else cash_weight
        total_invested = float(np.sum(weights))
        total_portfolio = total_invested + cw

        # 1. Total allocation sum == 1.0
        if abs(total_portfolio - 1.0) > tolerance:
            issues.append(
                f"Total allocation sum mismatch: invested ({total_invested:.4f}) + "
                f"cash ({cw:.4f}) = {total_portfolio:.4f} != 1.0"
            )

        # 2. Long-only constraint
        if self.long_only and np.any(weights < -tolerance):
            min_w = float(np.min(weights))
            issues.append(f"Long-only violation: negative weight detected ({min_w:.4f}).")

        # 3. Maximum asset weight constraint
        max_observed = float(np.max(weights)) if len(weights) > 0 else 0.0
        if max_observed > (self.max_asset_weight + tolerance):
            issues.append(
                f"Max weight violation: observed {max_observed:.4f} > limit {self.max_asset_weight:.4f}."
            )

        return len(issues) == 0, issues
