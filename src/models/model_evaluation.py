"""
MIRAI — Model Evaluation & Metric Engine (M04)
Computes academic-grade metrics for both Classification (FI-2010 mid-price & NIFTY direction)
and Regression (NIFTY returns & volatility).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger("ModelEvaluation")


# -------------------------------------------------------------
# CLASSIFICATION EVALUATION
# -------------------------------------------------------------
def evaluate_classifier(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
    labels: Tuple[int, ...] = (1, 2, 3),
    model_name: str = "Classifier",
) -> Dict[str, Any]:
    """
    Computes comprehensive evaluation metrics for multi-class market movement prediction.
    Default labels: 1 = Upward, 2 = Stationary, 3 = Downward.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    acc = float(accuracy_score(y_true, y_pred))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))

    # Macro metrics (unweighted, treats each class equally)
    prec_macro = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    rec_macro = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    f1_macro = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

    # Weighted metrics (accounts for class imbalance)
    prec_weighted = float(precision_score(y_true, y_pred, average="weighted", zero_division=0))
    rec_weighted = float(recall_score(y_true, y_pred, average="weighted", zero_division=0))
    f1_weighted = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    # Per-class breakdown
    prec_per_class = precision_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    rec_per_class = recall_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    f1_per_class = f1_score(y_true, y_pred, labels=labels, average=None, zero_division=0)

    per_class_metrics: Dict[str, Any] = {}
    cfg = get_config()
    label_map = cfg.get("fi2010.label_mapping", {1: "Upward", 2: "Stationary", 3: "Downward"})

    for idx, lbl in enumerate(labels):
        name = label_map.get(lbl, f"Class_{lbl}")
        per_class_metrics[name] = {
            "label": int(lbl),
            "precision": float(prec_per_class[idx]),
            "recall": float(rec_per_class[idx]),
            "f1_score": float(f1_per_class[idx]),
            "true_count": int(np.sum(y_true == lbl)),
            "pred_count": int(np.sum(y_pred == lbl)),
        }

    conf_mat = confusion_matrix(y_true, y_pred, labels=labels).tolist()

    metrics: Dict[str, Any] = {
        "model_name": model_name,
        "task_type": "classification",
        "sample_count": len(y_true),
        "accuracy": acc,
        "balanced_accuracy": bal_acc,
        "precision_macro": prec_macro,
        "recall_macro": rec_macro,
        "f1_macro": f1_macro,
        "precision_weighted": prec_weighted,
        "recall_weighted": rec_weighted,
        "f1_weighted": f1_weighted,
        "per_class": per_class_metrics,
        "confusion_matrix": conf_mat,
        "labels": list(labels),
    }

    # Optional Log Loss & ROC-AUC
    if y_prob is not None:
        try:
            metrics["log_loss"] = float(log_loss(y_true, y_prob, labels=labels))
        except Exception as exc:
            logger.debug("Could not compute log_loss: %s", exc)

        try:
            # Multi-class OvR ROC-AUC
            if len(labels) > 2 and y_prob.shape[1] == len(labels):
                metrics["roc_auc_ovr"] = float(
                    roc_auc_score(y_true, y_prob, labels=labels, multi_class="ovr", average="macro")
                )
        except Exception as exc:
            logger.debug("Could not compute roc_auc: %s", exc)

    return metrics


# -------------------------------------------------------------
# REGRESSION EVALUATION
# -------------------------------------------------------------
def evaluate_regression(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str = "Regressor",
) -> Dict[str, Any]:
    """
    Computes regression evaluation metrics for return and volatility predictions.
    Includes Mean Absolute Error, Root Mean Squared Error, R², and Directional Accuracy.
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)

    if len(y_true) != len(y_pred):
        raise ValueError(f"Shape mismatch: y_true {y_true.shape} vs y_pred {y_pred.shape}")

    mae = float(mean_absolute_error(y_true, y_pred))
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(np.sqrt(mse))
    r2 = float(r2_score(y_true, y_pred))

    # Directional Accuracy: percentage of samples where sign matches
    # (crucial for return forecasts: did it predict positive/negative correctly?)
    valid_signs = (y_true != 0)
    if np.any(valid_signs):
        directional_acc = float(np.mean(np.sign(y_true[valid_signs]) == np.sign(y_pred[valid_signs])))
    else:
        directional_acc = 0.0

    mean_bias = float(np.mean(y_pred - y_true))
    max_err = float(np.max(np.abs(y_pred - y_true)))

    metrics: Dict[str, Any] = {
        "model_name": model_name,
        "task_type": "regression",
        "sample_count": len(y_true),
        "mae": mae,
        "mse": mse,
        "rmse": rmse,
        "r2_score": r2,
        "directional_accuracy": directional_acc,
        "mean_bias": mean_bias,
        "max_error": max_err,
    }
    return metrics


# -------------------------------------------------------------
# REPORT FORMATTERS
# -------------------------------------------------------------
def format_evaluation_report(metrics: Dict[str, Any]) -> str:
    """Formats classification or regression metrics dictionary into a readable report."""
    task = metrics.get("task_type", "classification")

    if task == "regression":
        lines = [
            "=" * 65,
            f"  REGRESSION EVALUATION REPORT: {metrics.get('model_name', 'Model')}",
            "=" * 65,
            f"Total Test Samples:    {metrics.get('sample_count', 0):,}",
            f"MAE (Mean Abs Error):  {metrics.get('mae', 0.0):.6f}",
            f"RMSE (Root MSE):       {metrics.get('rmse', 0.0):.6f}",
            f"R² Score:              {metrics.get('r2_score', 0.0):.4f}",
            f"Directional Accuracy:  {metrics.get('directional_accuracy', 0.0) * 100:.2f}%",
            f"Mean Bias (Pred-True): {metrics.get('mean_bias', 0.0):.6f}",
            f"Max Absolute Error:    {metrics.get('max_error', 0.0):.6f}",
            "=" * 65,
        ]
        return "\n".join(lines)

    # Classification report
    lines = [
        "=" * 65,
        f"  CLASSIFICATION REPORT: {metrics.get('model_name', 'Model')}",
        "=" * 65,
        f"Total Test Samples:  {metrics.get('sample_count', 0):,}",
        f"Overall Accuracy:    {metrics.get('accuracy', 0.0) * 100:.2f}%",
        f"Balanced Accuracy:   {metrics.get('balanced_accuracy', 0.0) * 100:.2f}%",
        f"Macro Precision:     {metrics.get('precision_macro', 0.0) * 100:.2f}%",
        f"Macro Recall:        {metrics.get('recall_macro', 0.0) * 100:.2f}%",
        f"Macro F1 Score:      {metrics.get('f1_macro', 0.0) * 100:.2f}%",
        f"Weighted F1 Score:   {metrics.get('f1_weighted', 0.0) * 100:.2f}%",
    ]
    if "roc_auc_ovr" in metrics:
        lines.append(f"ROC-AUC (OvR Macro): {metrics['roc_auc_ovr'] * 100:.2f}%")
    if "log_loss" in metrics:
        lines.append(f"Log Loss:            {metrics['log_loss']:.4f}")

    lines.extend([
        "-" * 65,
        f"{'Class Name':<22} {'Precision':>10} {'Recall':>10} {'F1-Score':>10} {'True':>8}",
        "-" * 65,
    ])

    for cname, cdata in metrics.get("per_class", {}).items():
        lines.append(
            f"{cname:<22} "
            f"{cdata['precision'] * 100:>9.2f}% "
            f"{cdata['recall'] * 100:>9.2f}% "
            f"{cdata['f1_score'] * 100:>9.2f}% "
            f"{cdata['true_count']:>8,}"
        )

    lines.append("-" * 65)
    lines.append("Confusion Matrix (rows: true, cols: pred):")
    for row in metrics.get("confusion_matrix", []):
        lines.append(f"  {row}")
    lines.append("=" * 65)

    return "\n".join(lines)


def compare_evaluation_metrics(metrics_list: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Builds a structured side-by-side comparison DataFrame from multiple model evaluations.
    """
    rows = []
    for m in metrics_list:
        row = {"Model": m.get("model_name", "Unknown"), "Task": m.get("task_type", "N/A"), "Samples": m.get("sample_count", 0)}
        if m.get("task_type") == "regression":
            row["MAE"] = m.get("mae")
            row["RMSE"] = m.get("rmse")
            row["R²"] = m.get("r2_score")
            row["Directional Acc (%)"] = m.get("directional_accuracy", 0.0) * 100
        else:
            row["Accuracy (%)"] = m.get("accuracy", 0.0) * 100
            row["Balanced Acc (%)"] = m.get("balanced_accuracy", 0.0) * 100
            row["Macro F1 (%)"] = m.get("f1_macro", 0.0) * 100
            row["Weighted F1 (%)"] = m.get("f1_weighted", 0.0) * 100
            if "roc_auc_ovr" in m:
                row["ROC-AUC (%)"] = m.get("roc_auc_ovr", 0.0) * 100
        rows.append(row)
    return pd.DataFrame(rows)


def save_metrics_to_results(metrics: Dict[str, Any], filename: str) -> Path:
    """Saves metrics dictionary to a JSON file in results directory."""
    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / filename

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Saved evaluation results to: %s", out_path)
    return out_path
