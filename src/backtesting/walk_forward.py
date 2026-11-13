"""
MIRAI — Walk-Forward Validation Engine (M13)
Implements chronological, non-overlapping train/validation/test walk-forward splits.
Guarantees zero forward-looking data leakage across rolling or expanding windows.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("WalkForward")


@dataclass
class WalkForwardFold:
    """Chronological boundary definition for a walk-forward split."""
    fold_index: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    val_start: pd.Timestamp
    val_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    train_bars: int
    val_bars: int
    test_bars: int
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fold_index": self.fold_index,
            "train_start": str(self.train_start),
            "train_end": str(self.train_end),
            "val_start": str(self.val_start),
            "val_end": str(self.val_end),
            "test_start": str(self.test_start),
            "test_end": str(self.test_end),
            "train_bars": self.train_bars,
            "val_bars": self.val_bars,
            "test_bars": self.test_bars,
            "metrics": self.metrics,
        }


class WalkForwardValidator:
    """
    Splits chronological market data into expanding or rolling walk-forward windows.
    Enforces strict temporal ordering to prevent lookahead bias.
    """

    def __init__(
        self,
        train_window_bars: int = 150,
        val_window_bars: int = 30,
        test_window_bars: int = 30,
        expanding: bool = False,
        step_bars: Optional[int] = None,
    ):
        self.train_bars = train_window_bars
        self.val_bars = val_window_bars
        self.test_bars = test_window_bars
        self.expanding = expanding
        self.step_bars = step_bars or test_window_bars

    def generate_splits(
        self,
        data: pd.DataFrame,
    ) -> List[WalkForwardFold]:
        """
        Generates non-overlapping chronological fold windows.
        Raises ValueError if data is insufficient for at least one full fold.
        """
        n_bars = len(data)
        min_required = self.train_bars + self.val_bars + self.test_bars
        if n_bars < min_required:
            raise ValueError(
                f"Insufficient data for walk-forward validation: required at least {min_required} bars, "
                f"got {n_bars} bars."
            )

        folds: List[WalkForwardFold] = []
        fold_idx = 1
        current_train_start_idx = 0

        while True:
            train_end_idx = current_train_start_idx + self.train_bars
            val_start_idx = train_end_idx
            val_end_idx = val_start_idx + self.val_bars
            test_start_idx = val_end_idx
            test_end_idx = test_start_idx + self.test_bars

            if test_end_idx > n_bars:
                break

            train_df = data.iloc[current_train_start_idx:train_end_idx]
            val_df = data.iloc[val_start_idx:val_end_idx]
            test_df = data.iloc[test_start_idx:test_end_idx]

            fold = WalkForwardFold(
                fold_index=fold_idx,
                train_start=train_df.index[0],
                train_end=train_df.index[-1],
                val_start=val_df.index[0],
                val_end=val_df.index[-1],
                test_start=test_df.index[0],
                test_end=test_df.index[-1],
                train_bars=len(train_df),
                val_bars=len(val_df),
                test_bars=len(test_df),
            )
            folds.append(fold)
            fold_idx += 1

            if not self.expanding:
                current_train_start_idx += self.step_bars
            else:
                self.train_bars += self.step_bars

        return folds

    def evaluate_strategy(
        self,
        data: pd.DataFrame,
        eval_fn: Callable[[pd.DataFrame, pd.DataFrame, pd.DataFrame], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Executes walk-forward evaluation using a user-supplied evaluation callback.

        Parameters:
            data: Chronological market dataframe
            eval_fn: Callback accepting (train_df, val_df, test_df) and returning metrics dictionary.

        Returns:
            Aggregated summary across all out-of-sample test windows.
        """
        folds = self.generate_splits(data)
        fold_results: List[Dict[str, Any]] = []

        for fold in folds:
            train_sub = data.loc[fold.train_start:fold.train_end]
            val_sub = data.loc[fold.val_start:fold.val_end]
            test_sub = data.loc[fold.test_start:fold.test_end]

            metrics = eval_fn(train_sub, val_sub, test_sub)
            fold.metrics = metrics
            fold_results.append(fold.to_dict())

        # Aggregate test performance metrics across folds
        test_sharpes = [
            f["metrics"].get("sharpe_ratio", 0.0)
            for f in fold_results
            if "sharpe_ratio" in f.get("metrics", {})
        ]
        test_returns = [
            f["metrics"].get("total_return_pct", 0.0)
            for f in fold_results
            if "total_return_pct" in f.get("metrics", {})
        ]

        return {
            "num_folds": len(folds),
            "expanding_window": self.expanding,
            "average_test_sharpe": round(float(np.mean(test_sharpes)), 3) if test_sharpes else 0.0,
            "average_test_return_pct": round(float(np.mean(test_returns)), 2) if test_returns else 0.0,
            "fold_details": fold_results,
        }
