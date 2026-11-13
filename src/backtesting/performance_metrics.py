"""
MIRAI — Performance Metrics & Quantitative Evaluation (M13)
Calculates institutional-grade backtesting and strategy performance metrics.
Handles edge cases (0 trades, zero downside volatility, zero denominator) safely.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.utils.logger import get_logger
from src.backtesting.trade_simulator import Trade

logger = get_logger("PerformanceMetrics")


def compute_drawdown_curve(equity_curve: pd.Series) -> Tuple[pd.Series, float, float]:
    """
    Computes running peak, drawdown series, maximum drawdown, and current drawdown.
    Returns: (drawdown_series, max_drawdown, current_drawdown)
    Drawdown series values are in [-1.0, 0.0].
    """
    clean_eq = equity_curve.dropna()
    if clean_eq.empty:
        return pd.Series(dtype=np.float64), 0.0, 0.0

    peak = clean_eq.cummax()
    dd_series = (clean_eq - peak) / peak.replace(0.0, 1e-8)
    max_dd = float(dd_series.min())
    curr_dd = float(dd_series.iloc[-1])
    return dd_series, max_dd, curr_dd


def calculate_performance_metrics(
    equity_curve: pd.Series,
    trades: List[Trade],
    risk_free_rate: float = 0.065,
    annualization_factor: int = 252,
    benchmark_equity: Optional[pd.Series] = None,
) -> Dict[str, Any]:
    """
    Computes comprehensive performance statistics for an equity curve and trade log.

    Parameters:
        equity_curve: Series of portfolio equity over time
        trades: List of Trade records
        risk_free_rate: Annualized benchmark rate (e.g. 0.065 for 6.5% G-Sec)
        annualization_factor: 252 for daily, 252*375 for 1-minute
        benchmark_equity: Optional benchmark equity curve for relative metrics

    Returns:
        Structured dictionary of performance metrics.
    """
    clean_equity = equity_curve.dropna()
    if len(clean_equity) < 2:
        return {
            "total_return_pct": 0.0,
            "annualized_return_pct": 0.0,
            "cagr_pct": 0.0,
            "annualized_volatility_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "current_drawdown_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "win_loss_ratio": 0.0,
            "average_holding_bars": 0.0,
            "exposure_time_pct": 0.0,
            "total_transaction_costs": 0.0,
            "total_slippage_cost": 0.0,
            "notes": "Insufficient data points (<2 observations)",
        }

    init_equity = float(clean_equity.iloc[0])
    final_equity = float(clean_equity.iloc[-1])
    total_bars = len(clean_equity)

    # 1. Returns & CAGR
    total_return = (final_equity - init_equity) / init_equity if init_equity > 0 else 0.0

    # CAGR: (final / initial) ^ (annualization_factor / total_bars) - 1
    if total_bars >= annualization_factor and init_equity > 0 and final_equity > 0:
        cagr = (final_equity / init_equity) ** (annualization_factor / total_bars) - 1.0
    else:
        # Fallback to simple annualized return for shorter horizons
        cagr = total_return * (annualization_factor / total_bars) if total_bars > 0 else 0.0

    returns = clean_equity.pct_change().dropna()
    mean_ret = float(returns.mean()) if len(returns) > 0 else 0.0
    std_ret = float(returns.std()) if len(returns) > 0 else 0.0

    ann_return = mean_ret * annualization_factor
    ann_volatility = std_ret * np.sqrt(annualization_factor)

    # 2. Drawdowns
    dd_series, max_dd, curr_dd = compute_drawdown_curve(clean_equity)

    # 3. Sharpe & Sortino Ratios
    excess_ann_return = ann_return - risk_free_rate
    sharpe = (excess_ann_return / ann_volatility) if ann_volatility > 1e-6 else 0.0

    negative_rets = returns[returns < 0.0]
    if len(negative_rets) > 0:
        downside_std = float(np.sqrt(np.mean(negative_rets ** 2)) * np.sqrt(annualization_factor))
        sortino = (excess_ann_return / downside_std) if downside_std > 1e-6 else 0.0
    else:
        sortino = sharpe * 1.5 if sharpe > 0 else 0.0

    # 4. Calmar Ratio
    calmar = (ann_return / abs(max_dd)) if abs(max_dd) > 1e-4 else 0.0

    # 5. Trade-level Statistics
    closed_trades = [t for t in trades if t.is_closed]
    total_trades = len(closed_trades)

    winning_trades = [t for t in closed_trades if t.net_pnl > 0.0]
    losing_trades = [t for t in closed_trades if t.net_pnl < 0.0]

    n_wins = len(winning_trades)
    n_losses = len(losing_trades)
    win_rate = (n_wins / total_trades) if total_trades > 0 else 0.0

    gross_profit = sum(t.net_pnl for t in winning_trades)
    gross_loss = abs(sum(t.net_pnl for t in losing_trades))

    if gross_loss > 1e-6:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = 999.0  # Infinite profit factor capped for reporting
    else:
        profit_factor = 0.0

    avg_win = (gross_profit / n_wins) if n_wins > 0 else 0.0
    avg_loss = (gross_loss / n_losses) if n_losses > 0 else 0.0
    win_loss_ratio = (avg_win / avg_loss) if avg_loss > 1e-6 else 0.0

    avg_holding = (sum(t.bars_held for t in closed_trades) / total_trades) if total_trades > 0 else 0.0

    total_costs = sum(t.entry_costs + t.exit_costs for t in closed_trades)
    total_slip = sum(t.entry_slippage + t.exit_slippage for t in closed_trades)

    # 6. Exposure Time
    bars_with_position = sum(t.bars_held for t in closed_trades)
    exposure_pct = min(1.0, bars_with_position / total_bars) if total_bars > 0 else 0.0

    # 7. Benchmark Comparison (if provided)
    bench_metrics = {}
    if benchmark_equity is not None and len(benchmark_equity) >= 2:
        clean_bench = benchmark_equity.dropna()
        bench_ret = clean_bench.pct_change().dropna()
        # Align series
        aligned_df = pd.DataFrame({"strat": returns, "bench": bench_ret}).dropna()
        if len(aligned_df) >= 5:
            cov_mat = np.cov(aligned_df["strat"], aligned_df["bench"])
            var_bench = cov_mat[1, 1]
            beta = cov_mat[0, 1] / var_bench if var_bench > 1e-8 else 1.0
            bench_ann_ret = float(aligned_df["bench"].mean() * annualization_factor)
            alpha = ann_return - (risk_free_rate + beta * (bench_ann_ret - risk_free_rate))

            track_err = float((aligned_df["strat"] - aligned_df["bench"]).std() * np.sqrt(annualization_factor))
            info_ratio = (ann_return - bench_ann_ret) / track_err if track_err > 1e-6 else 0.0

            bench_metrics = {
                "benchmark_total_return_pct": round(((clean_bench.iloc[-1] - clean_bench.iloc[0]) / clean_bench.iloc[0]) * 100.0, 2),
                "alpha_pct": round(alpha * 100.0, 2),
                "beta": round(beta, 3),
                "tracking_error_pct": round(track_err * 100.0, 2),
                "information_ratio": round(info_ratio, 3),
            }

    metrics = {
        "initial_capital": round(init_equity, 2),
        "final_capital": round(final_equity, 2),
        "total_return_pct": round(total_return * 100.0, 2),
        "annualized_return_pct": round(ann_return * 100.0, 2),
        "cagr_pct": round(cagr * 100.0, 2),
        "annualized_volatility_pct": round(ann_volatility * 100.0, 2),
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "calmar_ratio": round(calmar, 3),
        "max_drawdown_pct": round(abs(max_dd) * 100.0, 2),
        "current_drawdown_pct": round(abs(curr_dd) * 100.0, 2),
        "win_rate_pct": round(win_rate * 100.0, 2),
        "profit_factor": round(profit_factor, 2),
        "total_trades": total_trades,
        "winning_trades": n_wins,
        "losing_trades": n_losses,
        "average_win": round(avg_win, 2),
        "average_loss": round(avg_loss, 2),
        "win_loss_ratio": round(win_loss_ratio, 2),
        "average_holding_bars": round(avg_holding, 1),
        "exposure_time_pct": round(exposure_pct * 100.0, 2),
        "total_transaction_costs": round(total_costs, 2),
        "total_slippage_cost": round(total_slip, 2),
        "annualization_factor": annualization_factor,
        "risk_free_rate": risk_free_rate,
    }
    metrics.update(bench_metrics)
    return metrics
