"""
ASTRAQUANT X — Unit Tests for Predictive AI Models
"""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from src.utils.config import PROJECT_ROOT
from src.models.base_model import BasePredictiveModel
from src.models.model_evaluation import (
    evaluate_classifier,
    evaluate_regression,
    format_evaluation_report,
    compare_evaluation_metrics,
)
from src.models.random_forest import AstraRandomForest
from src.models.xgboost_model import AstraXGBoost
from src.models.lstm_model import AstraLSTM
from src.models.transformer_model import AstraTransformer


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
    assert "CLASSIFICATION REPORT: TestModel" in report


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


def test_evaluate_regression_metrics():
    """Verify regression metric calculation (MAE, RMSE, R2, Directional Accuracy)."""
    y_true = np.array([0.05, -0.02, 0.03, -0.01, 0.04])
    y_pred = np.array([0.04, -0.01, -0.01, -0.02, 0.05])

    metrics = evaluate_regression(y_true, y_pred, model_name="TestRegressor")
    assert metrics["sample_count"] == 5
    assert metrics["mae"] > 0
    assert metrics["rmse"] >= metrics["mae"]
    assert "r2_score" in metrics
    # Directional accuracy: out of 5, signs match at indices 0, 1, 3, 4 -> 4/5 = 0.80
    assert pytest.approx(metrics["directional_accuracy"], 0.01) == 0.80

    report = format_evaluation_report(metrics)
    assert "REGRESSION EVALUATION REPORT: TestRegressor" in report
    assert "MAE" in report


def test_compare_evaluation_metrics():
    """Verify comparison table generation across model metrics."""
    m1 = evaluate_classifier(np.array([1, 2, 3]), np.array([1, 2, 3]), labels=(1, 2, 3), model_name="M1")
    m2 = evaluate_classifier(np.array([1, 2, 3]), np.array([1, 1, 3]), labels=(1, 2, 3), model_name="M2")

    df = compare_evaluation_metrics([m1, m2])
    assert len(df) == 2
    assert "Accuracy (%)" in df.columns
    assert "Macro F1 (%)" in df.columns


def test_base_model_input_validation():
    """Verify BasePredictiveModel.validate_input_shape enforces dimensionality and checks NaN/Inf."""
    rf = AstraRandomForest()

    # Valid 2D input
    valid_2d = np.ones((10, 5))
    checked = rf.validate_input_shape(valid_2d, expected_dim=2)
    assert checked.shape == (10, 5)

    # Invalid dimension: 3D input to 2D model
    invalid_3d = np.ones((10, 5, 2))
    with pytest.raises(ValueError, match="expected input with 2 dimensions"):
        rf.validate_input_shape(invalid_3d, expected_dim=2)

    # Input with NaN
    nan_arr = np.ones((10, 5))
    nan_arr[0, 0] = np.nan
    with pytest.raises(ValueError, match="contain NaN values"):
        rf.validate_input_shape(nan_arr, expected_dim=2)

    # Input with Inf
    inf_arr = np.ones((10, 5))
    inf_arr[0, 0] = np.inf
    with pytest.raises(ValueError, match="contain infinite values"):
        rf.validate_input_shape(inf_arr, expected_dim=2)


def test_lstm_classification_workflow():
    """Verify AstraLSTM classification training, inference, probabilities, and persistence."""
    np.random.seed(42)
    N, seq_len, d_in = 30, 5, 4
    X = np.random.randn(N, seq_len, d_in).astype(np.float32)
    y = np.random.choice([1, 2, 3], size=N).astype(np.int64)

    lstm = AstraLSTM(
        input_dim=d_in,
        sequence_length=seq_len,
        hidden_dim=8,
        num_layers=1,
        epochs=2,
        batch_size=16,
        task_type="classification",
        num_classes=3,
        random_state=42,
    )
    lstm.fit(X, y)

    preds = lstm.predict(X)
    assert len(preds) == N
    assert set(preds).issubset({1, 2, 3})

    probas = lstm.predict_proba(X)
    assert probas.shape == (N, 3)
    assert np.allclose(probas.sum(axis=1), 1.0)

    # Save and reload
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "test_lstm.npz"
        lstm.save(tmp_path)
        assert tmp_path.exists()

        loaded_lstm = AstraLSTM.load(tmp_path)
        loaded_preds = loaded_lstm.predict(X)
        assert np.array_equal(preds, loaded_preds)


def test_lstm_regression_workflow():
    """Verify AstraLSTM continuous target regression workflow."""
    np.random.seed(42)
    N, seq_len, d_in = 30, 5, 4
    X = np.random.randn(N, seq_len, d_in).astype(np.float32)
    y = np.random.randn(N).astype(np.float32)

    lstm = AstraLSTM(
        input_dim=d_in,
        sequence_length=seq_len,
        hidden_dim=8,
        num_layers=1,
        epochs=2,
        batch_size=16,
        task_type="regression",
        random_state=42,
    )
    lstm.fit(X, y)

    preds = lstm.predict(X)
    assert preds.shape == (N,)
    assert lstm.predict_proba(X) is None

    # Save and reload
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "test_lstm_reg.npz"
        lstm.save(tmp_path)
        assert tmp_path.exists()

        loaded_lstm = AstraLSTM.load(tmp_path)
        loaded_preds = loaded_lstm.predict(X)
        assert np.allclose(preds, loaded_preds)


def test_lstm_early_stopping():
    """Verify validation loss tracking and early stopping mechanism."""
    np.random.seed(42)
    N, seq_len, d_in = 40, 5, 4
    X_train = np.random.randn(N, seq_len, d_in).astype(np.float32)
    y_train = np.random.choice([1, 2, 3], size=N).astype(np.int64)
    X_val = np.random.randn(10, seq_len, d_in).astype(np.float32)
    y_val = np.random.choice([1, 2, 3], size=10).astype(np.int64)

    lstm = AstraLSTM(
        input_dim=d_in,
        sequence_length=seq_len,
        hidden_dim=8,
        epochs=10,
        patience=2,
        batch_size=16,
        random_state=42,
    )
    lstm.fit(X_train, y_train, X_val=X_val, y_val=y_val)

    assert "train_loss" in lstm.history
    assert "val_loss" in lstm.history
    assert len(lstm.history["train_loss"]) > 0


def test_transformer_classification_workflow():
    """Verify AstraTransformer classification training, inference, and persistence."""
    np.random.seed(42)
    N, seq_len, d_in = 30, 5, 4
    X = np.random.randn(N, seq_len, d_in).astype(np.float32)
    y = np.random.choice([1, 2, 3], size=N).astype(np.int64)

    trans = AstraTransformer(
        input_dim=d_in,
        sequence_length=seq_len,
        d_model=8,
        n_heads=2,
        dim_feedforward=16,
        num_layers=1,
        epochs=2,
        batch_size=16,
        task_type="classification",
        num_classes=3,
        random_state=42,
    )
    trans.fit(X, y)

    preds = trans.predict(X)
    assert len(preds) == N
    assert set(preds).issubset({1, 2, 3})

    probas = trans.predict_proba(X)
    assert probas.shape == (N, 3)
    assert np.allclose(probas.sum(axis=1), 1.0)

    # Save and reload
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "test_trans.npz"
        trans.save(tmp_path)
        assert tmp_path.exists()

        loaded_trans = AstraTransformer.load(tmp_path)
        loaded_preds = loaded_trans.predict(X)
        assert np.array_equal(preds, loaded_preds)


def test_transformer_regression_workflow():
    """Verify AstraTransformer regression training and inference."""
    np.random.seed(42)
    N, seq_len, d_in = 30, 5, 4
    X = np.random.randn(N, seq_len, d_in).astype(np.float32)
    y = np.random.randn(N).astype(np.float32)

    trans = AstraTransformer(
        input_dim=d_in,
        sequence_length=seq_len,
        d_model=8,
        n_heads=2,
        dim_feedforward=16,
        num_layers=1,
        epochs=2,
        batch_size=16,
        task_type="regression",
        random_state=42,
    )
    trans.fit(X, y)

    preds = trans.predict(X)
    assert preds.shape == (N,)
    assert trans.predict_proba(X) is None

    # Save and reload
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "test_trans_reg.npz"
        trans.save(tmp_path)
        assert tmp_path.exists()

        loaded_trans = AstraTransformer.load(tmp_path)
        loaded_preds = loaded_trans.predict(X)
        assert np.allclose(preds, loaded_preds)


def test_transformer_invalid_shape():
    """Verify 2D input into 3D Transformer raises ValueError."""
    trans = AstraTransformer(input_dim=4, sequence_length=5)
    invalid_2d = np.ones((10, 4))
    with pytest.raises(ValueError, match="expected input with 3 dimensions"):
        trans.validate_input_shape(invalid_2d, expected_dim=3)
