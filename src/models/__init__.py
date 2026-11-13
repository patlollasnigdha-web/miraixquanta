"""Predictive AI Models & Registry Package for MIRAI (M03, M04)."""

from src.models.base_model import BasePredictiveModel
from src.models.model_evaluation import (
    evaluate_classifier,
    evaluate_regression,
    format_evaluation_report,
    compare_evaluation_metrics,
    save_metrics_to_results,
)
from src.models.random_forest import AstraRandomForest
from src.models.xgboost_model import AstraXGBoost
from src.models.lstm_model import AstraLSTM
from src.models.transformer_model import AstraTransformer
from src.models.model_registry import ModelRegistry, get_model_registry

__all__ = [
    "BasePredictiveModel",
    "AstraRandomForest",
    "AstraXGBoost",
    "AstraLSTM",
    "AstraTransformer",
    "ModelRegistry",
    "get_model_registry",
    "evaluate_classifier",
    "evaluate_regression",
    "format_evaluation_report",
    "compare_evaluation_metrics",
    "save_metrics_to_results",
]
