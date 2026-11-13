"""
ASTRAQUANT X — Unit Tests for Predictive AI Models
"""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from src.utils.config import PROJECT_ROOT
from src.models.model_evaluation import evaluate_classifier, format_evaluation_report
from src.models.random_forest import AstraRandomForest
from src.models.xgboost_model import AstraXGBoost


def test_evaluate_classifier_metrics():
    """Verify evaluation metric computation against known ground truth."""
    y_true = np.array([1, 1, 2, 2, 3, 3])
    y_pred = np.array([1, 2, 2, 2, 3, 1])

    metrics = evaluate_classifier(y_true, y_pred, labels=(1, 2, 3), model_name="TestModel")

    # Accuracy: 4 out of 6 correct = 0.6667
    assert pytest.approx(metrics["accuracy"], 0.01) == 0.6667
    assert "per_class" in metrics
    assert len(metrics["confusion_matrix"]) == 3

    report = format_evaluation_report(metrics)
    assert "EVALUATION REPORT: TestModel" in report


def test_random_forest_workflow():
    """Verify RandomForest fit, predict, evaluate, save, and reload."""
    np.random.seed(42)
    X = np.random.randn(60, 10).astype(np.float32)
    y = np.random.choice([1, 2, 3], size=60).astype(np.int8)

    rf = AstraRandomForest(n_estimators=10, max_depth=3, random_state=42)
    rf.fit(X, y)

    preds = rf.predict(X)
    assert len(preds) == 60
    assert set(preds).issubset({1, 2, 3})

    probas = rf.predict_proba(X)
    assert probas.shape == (60, 3)
    assert np.allclose(probas.sum(axis=1), 1.0)

    # Save and reload
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "test_rf.joblib"
        rf.save(tmp_path)
        assert tmp_path.exists()

        loaded_rf = AstraRandomForest.load(tmp_path)
        loaded_preds = loaded_rf.predict(X)
        assert np.array_equal(preds, loaded_preds)


def test_xgboost_workflow():
    """Verify XGBoost label conversion, fit, predict, evaluate, save, and reload."""
    np.random.seed(42)
    X = np.random.randn(60, 10).astype(np.float32)
    y = np.random.choice([1, 2, 3], size=60).astype(np.int8)

    xgb = AstraXGBoost(n_estimators=10, max_depth=3, random_state=42)
    xgb.fit(X, y)

    preds = xgb.predict(X)
    assert len(preds) == 60
    # Must preserve 1-based labels {1, 2, 3}
    assert set(preds).issubset({1, 2, 3})

    probas = xgb.predict_proba(X)
    assert probas.shape == (60, 3)
    assert np.allclose(probas.sum(axis=1), 1.0)

    # Save and reload
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "test_xgb.joblib"
        xgb.save(tmp_path)
        assert tmp_path.exists()

        loaded_xgb = AstraXGBoost.load(tmp_path)
        loaded_preds = loaded_xgb.predict(X)
        assert np.array_equal(preds, loaded_preds)


def test_load_existing_trained_models():
    """Verify the 4 pre-existing models in models/ load and predict valid classes."""
    model_dir = PROJECT_ROOT / "models"
    model_files = [
        "auction_baseline_rf.joblib",
        "auction_balanced_rf.joblib",
        "non_auction_baseline_rf.joblib",
        "non_auction_balanced_rf.joblib",
    ]

    # Create synthetic test batch with 144 features
    dummy_lob_sample = np.zeros((5, 144), dtype=np.float32)

    for mfile in model_files:
        path = model_dir / mfile
        assert path.exists(), f"Model file missing: {path}"
        rf = AstraRandomForest.load(path)
        preds = rf.predict(dummy_lob_sample)
        assert len(preds) == 5
        assert set(preds).issubset({1, 2, 3})
