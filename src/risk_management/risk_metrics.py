"""
MIRAI — Dynamic Risk Metrics Engine (M11)
Calculates historical/rolling volatility, Value at Risk (VaR), Conditional VaR (CVaR),
maximum/current drawdown, Sharpe, Sortino, and Calmar ratios.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy import stats

from src.utils.logger import get_logger

logger = get_logger("RiskMetrics")


def compute_realized_volatility(
    returns: pd.Series,
    annualization_factor: int = 252,
) -> float:
    """Computes annualized realized volatility from return series."""
    clean_rets = returns.dropna()
    if len(clean_rets) < 2:
        return 0.0
    return float(clean_rets.std() * np.sqrt(annualization_factor))


def compute_drawdown_series(prices_or_equity: pd.Series) -> Tuple[pd.Series, float, float]:
    """
    Computes rolling peak, drawdown series, maximum drawdown, and current drawdown.
    Returns: (drawdown_series, max_drawdown, current_drawdown) where drawdowns are negative or zero.
    """
    series = prices_or_equity.dropna()
    if series.empty:
        return pd.Series(dtype=np.float64), 0.0, 0.0

    peak = series.cummax()
    dd = (series - peak) / peak.replace(0.0, 1e-8)
    max_dd = float(dd.min())
    current_dd = float(dd.iloc[-1])
    return dd, max_dd, current_dd


def compute_var_and_cvar(
    returns: pd.Series,
    confidence_level: float = 0.95,
    method: str = "historical",
) -> Tuple[float, float]:
    """
    Calculates Value at Risk (VaR) and Conditional VaR (CVaR / Expected Shortfall).
    Reported as positive numbers representing expected loss percentage:
    e.g. VaR 0.02 = 2% maximum expected loss at specified confidence level.
    """
    clean_rets = returns.dropna().values
    if len(clean_rets) < 5:
        return 0.0, 0.0

    alpha = 1.0 - confidence_level

    if method == "historical":
        # Empirical quantile of returns
        var_threshold = np.percentile(clean_rets, alpha * 100.0)
        var = float(-var_threshold) if var_threshold < 0 else 0.0

        # CVaR is the mean of returns that fall below the VaR threshold
        tail_losses = clean_rets[clean_rets <= var_threshold]
        if len(tail_losses) > 0:
            cvar = float(-np.mean(tail_losses))
        else:
            cvar = var

    else:  # Parametric (Gaussian)
        mu = np.mean(clean_rets)
        sigma = np.std(clean_rets)
        z = stats.norm.ppf(confidence_level)
        var = float(-(mu - z * sigma))
        # Expected Shortfall for normal distribution
        cvar = float(-(mu - sigma * (stats.norm.pdf(z) / alpha)))

    return max(0.0, var), max(0.0, cvar)


def compute_risk_adjusted_ratios(
    returns: pd.Series,
    risk_free_rate: float = 0.065,
    annualization_factor: int = 252,
) -> Dict[str, float]:
    """
    Computes annualized Sharpe Ratio, Sortino Ratio, and Calmar Ratio.
    """
    clean_rets = returns.dropna()
    if len(clean_rets) < 5:
        return {"sharpe_ratio": 0.0, "sortino_ratio": 0.0, "calmar_ratio": 0.0}

    ann_ret = float(clean_rets.mean() * annualization_factor)
    ann_vol = float(clean_rets.std() * np.sqrt(annualization_factor))

    # 1. Sharpe Ratio
    sharpe = (ann_ret - risk_free_rate) / ann_vol if ann_vol > 0 else 0.0

    # 2. Sortino Ratio (Downside deviation)
    negative_rets = clean_rets[clean_rets < 0.0]
    if len(negative_rets) > 0:
        downside_std = float(np.sqrt(np.mean(negative_rets ** 2)) * np.sqrt(annualization_factor))
        sortino = (ann_ret - risk_free_rate) / downside_std if downside_std > 0 else 0.0
    else:
        sortino = sharpe * 1.5  # Zero downside risk proxy

    # 3. Calmar Ratio (Ann Return / Max Drawdown)
    cum_equity = (1.0 + clean_rets).cumprod()
    _, max_dd, _ = compute_drawdown_series(cum_equity)
    calmar = (ann_ret - risk_free_rate) / abs(max_dd) if abs(max_dd) > 0.001 else 0.0

    return {
        "annualized_return": round(ann_ret, 4),
        "annualized_volatility": round(ann_vol, 4),
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "calmar_ratio": round(calmar, 3),
        "max_drawdown": round(max_dd, 4),
    }


def compute_portfolio_risk_summary(
    equity_or_returns: pd.Series,
    is_equity_curve: bool = True,
    confidence_level: float = 0.95,
    risk_free_rate: float = 0.065,
) -> Dict[str, Any]:
    """
    Aggregates full risk metrics report for portfolio equity curve or return stream.
    """
    if is_equity_curve:
        equity = equity_or_returns.dropna()
        returns = equity.pct_change().dropna()
        _, max_dd, curr_dd = compute_drawdown_series(equity)
    else:
        returns = equity_or_returns.dropna()
        cum_equity = (1.0 + returns).cumprod()
        _, max_dd, curr_dd = compute_drawdown_series(cum_equity)

    ann_vol = compute_realized_volatility(returns)
    var_95, cvar_95 = compute_var_and_cvar(returns, confidence_level=confidence_level)
    ratios = compute_risk_adjusted_ratios(returns, risk_free_rate=risk_free_rate)

    return {
        "annualized_volatility": round(ann_vol, 4),
        "max_drawdown": round(max_dd, 4),
        "current_drawdown": round(curr_dd, 4),
        "value_at_risk_95": round(var_95, 4),
        "conditional_var_95": round(cvar_95, 4),
        "sharpe_ratio": ratios["sharpe_ratio"],
        "sortino_ratio": ratios["sortino_ratio"],
        "calmar_ratio": ratios["calmar_ratio"],
    }


def compute_historical_var(returns: pd.Series, confidence: float = 0.95) -> float:
    var, _ = compute_var_and_cvar(returns, confidence_level=confidence, method="historical")
    return var


def compute_historical_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    _, cvar = compute_var_and_cvar(returns, confidence_level=confidence, method="historical")
    return cvar


def compute_parametric_var(returns: pd.Series, confidence: float = 0.95) -> float:
    var, _ = compute_var_and_cvar(returns, confidence_level=confidence, method="parametric")
    return var


def compute_parametric_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    _, cvar = compute_var_and_cvar(returns, confidence_level=confidence, method="parametric")
    return cvar


def compute_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.065) -> float:
    r = compute_risk_adjusted_ratios(returns, risk_free_rate=risk_free_rate)
    return r["sharpe_ratio"]


def compute_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.065) -> float:
    r = compute_risk_adjusted_ratios(returns, risk_free_rate=risk_free_rate)
    return r["sortino_ratio"]


def compute_calmar_ratio(
    returns: pd.Series,
    max_drawdown: Optional[float] = None,
    risk_free_rate: float = 0.065,
) -> float:
    clean_rets = returns.dropna()
    if len(clean_rets) < 2:
        return 0.0
    ann_ret = float(clean_rets.mean() * 252)
    if max_drawdown is None:
        cum_equity = (1.0 + clean_rets).cumprod()
        _, max_dd, _ = compute_drawdown_series(cum_equity)
    else:
        max_dd = max_drawdown
    return round((ann_ret - risk_free_rate) / abs(max_dd), 3) if abs(max_dd) > 0.001 else 0.0


def compute_risk_summary(
    returns: pd.Series,
    max_drawdown: Optional[float] = None,
    current_drawdown: Optional[float] = None,
) -> Dict[str, Any]:
    summary = compute_portfolio_risk_summary(returns, is_equity_curve=False)
    if max_drawdown is not None:
        summary["max_drawdown"] = max_drawdown
    if current_drawdown is not None:
        summary["current_drawdown"] = current_drawdown
    summary["realized_volatility"] = summary["annualized_volatility"]
    summary["historical_var_95"] = summary["value_at_risk_95"]
    return summary


class RiskMetrics:
    """Namespace container for risk metrics calculations."""

    @staticmethod
    def realized_volatility(returns: pd.Series, annualization_factor: int = 252) -> float:
        return compute_realized_volatility(returns, annualization_factor)

    @staticmethod
    def drawdown_series(prices: pd.Series) -> Tuple[pd.Series, float, float]:
        return compute_drawdown_series(prices)

    @staticmethod
    def var_cvar(returns: pd.Series, confidence: float = 0.95, method: str = "historical") -> Tuple[float, float]:
        return compute_var_and_cvar(returns, confidence_level=confidence, method=method)

    @staticmethod
    def ratios(returns: pd.Series, risk_free_rate: float = 0.065) -> Dict[str, float]:
        return compute_risk_adjusted_ratios(returns, risk_free_rate=risk_free_rate)

    @staticmethod
    def summary(returns_or_equity: pd.Series, is_equity: bool = True) -> Dict[str, Any]:
        return compute_portfolio_risk_summary(returns_or_equity, is_equity_curve=is_equity)

