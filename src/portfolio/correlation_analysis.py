"""
MIRAI — Portfolio Correlation and Diversification Analysis (M10)
Calculates asset covariance, correlation matrices, concentration metrics (HHI, N_eff),
and portfolio diversification ratios.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("CorrelationAnalysis")


def compute_covariance_and_correlation(
    returns_df: pd.DataFrame,
    annualization_factor: int = 252,
    shrinkage: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """
    Computes annualized covariance matrix, correlation matrix, and individual asset volatilities.
    Handles missing values using pairwise complete observations.
    """
    if returns_df.empty or len(returns_df) < 5:
        raise ValueError("Returns DataFrame must have at least 5 observations.")

    # Drop columns that are completely NaN
    valid_returns = returns_df.dropna(how="all", axis=1)

    # Daily covariance and correlation
    daily_cov = valid_returns.cov()
    corr_matrix = valid_returns.corr()

    # Annualize covariance
    ann_cov = daily_cov * annualization_factor

    # Individual annualized volatilities
    daily_std = valid_returns.std()
    ann_vol = daily_std * np.sqrt(annualization_factor)

    return ann_cov, corr_matrix, ann_vol


def identify_highly_correlated_pairs(
    corr_matrix: pd.DataFrame,
    threshold: float = 0.80,
) -> List[Dict[str, Any]]:
    """
    Detects pairs of assets with correlation exceeding threshold.
    Helps avoid concentration in redundant assets.
    """
    pairs = []
    assets = corr_matrix.columns.tolist()
    n = len(assets)

    for i in range(n):
        for j in range(i + 1, n):
            c_val = corr_matrix.iloc[i, j]
            if not np.isnan(c_val) and abs(c_val) >= threshold:
                pairs.append({
                    "asset_1": assets[i],
                    "asset_2": assets[j],
                    "correlation": round(float(c_val), 3),
                })

    # Sort descending by correlation strength
    pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
    return pairs


def compute_concentration_metrics(weights: np.ndarray) -> Dict[str, float]:
    """
    Calculates portfolio concentration metrics:
    - Herfindahl-Hirschman Index (HHI = sum(w^2)) in [1/N, 1.0]
    - Effective Number of Constituents (N_eff = 1 / HHI)
    - Maximum Weight
    """
    w = np.asarray(weights, dtype=np.float64)
    # Exclude zero or negligible weights
    w = w[w > 1e-6]

    if len(w) == 0:
        return {"hhi": 1.0, "effective_n": 0.0, "max_weight": 0.0}

    # Normalize invested weights to 1 for concentration assessment
    w_norm = w / np.sum(w)
    hhi = float(np.sum(w_norm ** 2))
    eff_n = float(1.0 / hhi) if hhi > 0 else 0.0
    max_w = float(np.max(w))

    return {
        "hhi": round(hhi, 4),
        "effective_n": round(eff_n, 2),
        "max_weight": round(max_w, 4),
    }


def compute_portfolio_risk_and_diversification(
    weights: np.ndarray,
    ann_cov_matrix: np.ndarray,
    ann_asset_vols: np.ndarray,
) -> Tuple[float, float]:
    """
    Calculates:
    1. Estimated annualized portfolio volatility: sigma_p = sqrt(w^T * Sigma * w)
    2. Diversification Ratio: DR = sum(w_i * sigma_i) / sigma_p >= 1.0
       (Higher DR signifies greater risk reduction through diversification).
    """
    w = np.asarray(weights, dtype=np.float64)
    sigma_sq = float(w.T @ ann_cov_matrix @ w)
    portfolio_vol = float(np.sqrt(max(sigma_sq, 1e-8)))

    # Weighted sum of constituent individual volatilities
    weighted_individual_vol = float(np.sum(w * ann_asset_vols))

    # Diversification Ratio
    dr = float(weighted_individual_vol / portfolio_vol) if portfolio_vol > 0 else 1.0
    return portfolio_vol, dr
