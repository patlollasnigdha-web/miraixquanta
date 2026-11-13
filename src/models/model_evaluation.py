"""
ASTRAQUANT X — Model Evaluation Harness
Computes academic-grade classification metrics, confusion matrices,
per-class performance breakdowns, and prediction distributions.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    log_loss,
)

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger("ModelEvaluation")


def evaluate_classifier(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
    labels: Tuple[int, ...] = (1, 2, 3),
    model_name: str = "Classifier",
) -> Dict[str, Any]:
    """
    Computes comprehensive evaluation metrics for 3-class market movement prediction.
    Labels: 1 = Upward, 2 = Stationary, 3 = Downward.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    acc = float(accuracy_score(y_true, y_pred))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))

    prec_macro = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    rec_macro = float(recall_score(y_true, y_pred, average="macro", zero_division=0))
    f1_macro = float(f1_score(y_true, y_pred, average="macro", zero_division=0))

    # Per-class metrics
    prec_per_class = precision_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    rec_per_class = recall_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    f1_per_class = f1_score(y_true, y_pred, labels=labels, average=None, zero_division=0)

    per_class_metrics = {}
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

    metrics = {
        "model_name": model_name,
        "sample_count": len(y_true),
        "accuracy": acc,
        "balanced_accuracy": bal_acc,
        "precision_macro": prec_macro,
        "recall_macro": rec_macro,
        "f1_macro": f1_macro,
        "per_class": per_class_metrics,
        "confusion_matrix": conf_mat,
        "labels": list(labels),
    }

    if y_prob is not None:
        try:
            metrics["log_loss"] = float(log_loss(y_true, y_prob, labels=labels))
        except Exception as exc:
            logger.debug("Could not compute log_loss: %s", exc)

    return metrics


def format_evaluation_report(metrics: Dict[str, Any]) -> str:
    """Formats metrics dictionary into a readable academic report string."""
    lines = [
        "=" * 65,
        f"  EVALUATION REPORT: {metrics.get('model_name', 'Model')}",
        "=" * 65,
        f"Total Test Samples:  {metrics.get('sample_count', 0):,}",
        f"Overall Accuracy:    {metrics.get('accuracy', 0.0) * 100:.2f}%",
        f"Balanced Accuracy:   {metrics.get('balanced_accuracy', 0.0) * 100:.2f}%",
        f"Macro Precision:     {metrics.get('precision_macro', 0.0) * 100:.2f}%",
        f"Macro Recall:        {metrics.get('recall_macro', 0.0) * 100:.2f}%",
        f"Macro F1 Score:      {metrics.get('f1_macro', 0.0) * 100:.2f}%",
        "-" * 65,
        f"{'Class Name':<22} {'Precision':>10} {'Recall':>10} {'F1-Score':>10} {'True':>8}",
        "-" * 65,
    ]

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


def save_metrics_to_results(metrics: Dict[str, Any], filename: str) -> Path:
    """Saves metrics dictionary to a JSON file in results directory."""
    results_dir = PROJECT_ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / filename

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Saved evaluation results to: %s", out_path)
    return out_path
