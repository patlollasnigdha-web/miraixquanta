"""
MIRAI — Benchmark Comparison Engine (M13)
Compares strategy equity curves against market benchmarks (e.g. NIFTY 50 Buy-and-Hold).
Computes CAPM Alpha, Beta, Tracking Error, and Information Ratio.
Enforces strict pipeline separation: rejects comparing FI-2010 microstructure with equity benchmarks.
"""

from typing import Any, Dict, Optional, Tuple
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("BenchmarkComparison")


class BenchmarkComparator:
    """
    Evaluates relative strategy performance against buy-and-hold market benchmarks.
    """

    def __init__(
        self,
        risk_free_rate: float = 0.065,
        annualization_factor: int = 252,
    ):
        self.risk_free_rate = risk_free_rate
        self.annualization_factor = annualization_factor

    def compare(
        self,
        strategy_equity: pd.Series,
        benchmark_prices_or_equity: pd.Series,
        pipeline_id: str = "pipeline_b_nifty",
        benchmark_name: str = "NIFTY50_BUY_HOLD",
    ) -> Dict[str, Any]:
        """
        Calculates relative benchmark metrics.
        Strictly enforces Pipeline B constraint.
        """
        # Pipeline Isolation Guard
        if pipeline_id == "pipeline_a_fi2010":
            raise ValueError(
                "BenchmarkComparator: Cannot compare FI-2010 microstructure tick arrays directly "
                "against daily equity portfolio benchmarks (NIFTY 50). Use event-level classification metrics instead."
            )

        clean_strat = strategy_equity.dropna()
        clean_bench = benchmark_prices_or_equity.dropna()

        if len(clean_strat) < 5 or len(clean_bench) < 5:
            return {
                "benchmark_name": benchmark_name,
                "status": "INSUFFICIENT_DATA",
                "notes": "Fewer than 5 observations available for benchmark alignment.",
            }

        # Normalize benchmark to same initial capital as strategy
        strat_init = float(clean_strat.iloc[0])
        bench_normalized = (clean_bench / float(clean_bench.iloc[0])) * strat_init

        # Align series by index
        aligned = pd.DataFrame({
            "strategy": clean_strat.pct_change(),
            "benchmark": bench_normalized.pct_change(),
        }).dropna()

        if len(aligned) < 5:
            return {
                "benchmark_name": benchmark_name,
                "status": "INSUFFICIENT_OVERLAP",
                "notes": "Insufficient chronological overlap between strategy and benchmark.",
            }

        strat_rets = aligned["strategy"]
        bench_rets = aligned["benchmark"]

        # Annualized metrics
        strat_ann_ret = float(strat_rets.mean() * self.annualization_factor)
        bench_ann_ret = float(bench_rets.mean() * self.annualization_factor)
        strat_ann_vol = float(strat_rets.std() * np.sqrt(self.annualization_factor))
        bench_ann_vol = float(bench_rets.std() * np.sqrt(self.annualization_factor))

        total_strat_return = float((clean_strat.iloc[-1] - strat_init) / strat_init)
        total_bench_return = float((clean_bench.iloc[-1] - clean_bench.iloc[0]) / clean_bench.iloc[0])

        # CAPM Beta and Alpha
        cov_matrix = np.cov(strat_rets, bench_rets)
        var_bench = float(cov_matrix[1, 1])
        beta = float(cov_matrix[0, 1] / var_bench) if var_bench > 1e-9 else 1.0

        # Alpha (Jensen's Alpha annualized)
        alpha = strat_ann_ret - (self.risk_free_rate + beta * (bench_ann_ret - self.risk_free_rate))

        # Tracking Error & Information Ratio
        excess_daily_rets = strat_rets - bench_rets
        tracking_error = float(excess_daily_rets.std() * np.sqrt(self.annualization_factor))
        excess_annual_ret = strat_ann_ret - bench_ann_ret
        information_ratio = (excess_annual_ret / tracking_error) if tracking_error > 1e-6 else 0.0

        # Correlation
        corr = float(strat_rets.corr(bench_rets))

        return {
            "benchmark_name": benchmark_name,
            "status": "OPTIMAL",
            "strategy_total_return_pct": round(total_strat_return * 100.0, 2),
            "benchmark_total_return_pct": round(total_bench_return * 100.0, 2),
            "excess_return_pct": round(excess_annual_ret * 100.0, 2),
            "alpha_pct": round(alpha * 100.0, 2),
            "beta": round(beta, 3),
            "correlation": round(corr, 3),
            "tracking_error_pct": round(tracking_error * 100.0, 2),
            "information_ratio": round(information_ratio, 3),
            "benchmark_annualized_volatility_pct": round(bench_ann_vol * 100.0, 2),
        }
