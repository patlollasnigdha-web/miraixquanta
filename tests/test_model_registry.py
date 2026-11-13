"""
MIRAI — Unit Tests for Model Registry (Batch 2 - M04)
"""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from src.models.model_registry import ModelRegistry
from src.models.random_forest import AstraRandomForest


def test_model_registration_and_retrieval():
    """Verify model registration, metadata persistence, and retrieval."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_file = Path(tmpdir) / "registry.json"
        registry = ModelRegistry(registry_file=reg_file)

        # Create dummy model artifact
        artifact = Path(tmpdir) / "dummy_model.joblib"
        rf = AstraRandomForest(n_estimators=5, max_depth=2, random_state=42)
        rf.save(artifact)

        schema = ["feat_1", "feat_2", "feat_3"]
        metrics = {"accuracy": 0.65, "f1_macro": 0.62}

        model_id = registry.register_model(
            model_name="TestRF",
            algorithm="RandomForest",
            version="1.0.0",
            pipeline_id="pipeline_a_fi2010",
            prediction_target="mid_price_movement_h100",
            prediction_horizon=100,
            task_type="classification",
            feature_schema=schema,
            artifact_path=artifact,
            metrics=metrics,
            status="experimental",
        )

        assert model_id == "testrf_v1.0.0"
        meta = registry.get_model_metadata(model_id)
        assert meta["algorithm"] == "RandomForest"
        assert meta["feature_count"] == 3
        assert meta["metrics"]["accuracy"] == 0.65
        assert meta["status"] == "experimental"


def test_model_versioning_and_overwrite_prevention():
    """Verify overwrite protection raises error unless overwrite=True."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_file = Path(tmpdir) / "registry.json"
        registry = ModelRegistry(registry_file=reg_file)

        artifact = Path(tmpdir) / "dummy.joblib"
        rf = AstraRandomForest(n_estimators=5, max_depth=2)
        rf.save(artifact)

        registry.register_model(
            model_name="ModelX",
            algorithm="RandomForest",
            version="1.0.0",
            pipeline_id="pipeline_a_fi2010",
            prediction_target="target",
            prediction_horizon=10,
            task_type="classification",
            feature_schema=["f1"],
            artifact_path=artifact,
        )

        # Second registration with same version without overwrite must raise ValueError
        with pytest.raises(ValueError, match="already exists"):
            registry.register_model(
                model_name="ModelX",
                algorithm="RandomForest",
                version="1.0.0",
                pipeline_id="pipeline_a_fi2010",
                prediction_target="target",
                prediction_horizon=10,
                task_type="classification",
                feature_schema=["f1"],
                artifact_path=artifact,
                overwrite=False,
            )


def test_list_models_filtering():
    """Verify list_models filters by pipeline_id, status, and algorithm."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_file = Path(tmpdir) / "registry.json"
        registry = ModelRegistry(registry_file=reg_file)

        artifact = Path(tmpdir) / "dummy.joblib"
        rf = AstraRandomForest(n_estimators=5, max_depth=2)
        rf.save(artifact)

        registry.register_model(
            model_name="M1", algorithm="RandomForest", version="1.0.0",
            pipeline_id="pipeline_a_fi2010", prediction_target="t1",
            prediction_horizon=100, task_type="classification",
            feature_schema=["f1"], artifact_path=artifact, status="experimental"
        )
        registry.register_model(
            model_name="M2", algorithm="XGBoost", version="1.0.0",
            pipeline_id="pipeline_b_nifty", prediction_target="return_1d",
            prediction_horizon=1, task_type="regression",
            feature_schema=["f1"], artifact_path=artifact, status="validated"
        )

        assert len(registry.list_models(pipeline_id="pipeline_a_fi2010")) == 1
        assert len(registry.list_models(pipeline_id="pipeline_b_nifty")) == 1
        assert len(registry.list_models(status="validated")) == 1
        assert len(registry.list_models(algorithm="XGBoost")) == 1


def test_set_model_status_and_get_approved():
    """Verify status lifecycle and retrieval of approved model."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_file = Path(tmpdir) / "registry.json"
        registry = ModelRegistry(registry_file=reg_file)

        artifact = Path(tmpdir) / "dummy.joblib"
        rf = AstraRandomForest(n_estimators=5, max_depth=2)
        rf.save(artifact)

        mid = registry.register_model(
            model_name="ProdModel", algorithm="RandomForest", version="1.0.0",
            pipeline_id="pipeline_b_nifty", prediction_target="return_1d",
            prediction_horizon=1, task_type="regression",
            feature_schema=["f1"], artifact_path=artifact, status="experimental"
        )

        assert registry.get_approved_model("pipeline_b_nifty", "return_1d") is None

        registry.set_model_status(mid, "approved", notes="Passed walk-forward benchmark")
        approved = registry.get_approved_model("pipeline_b_nifty", "return_1d")
        assert approved is not None
        assert approved["model_id"] == mid


def test_compare_models_table():
    """Verify side-by-side comparison DataFrame generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_file = Path(tmpdir) / "registry.json"
        registry = ModelRegistry(registry_file=reg_file)

        artifact = Path(tmpdir) / "dummy.joblib"
        rf = AstraRandomForest(n_estimators=5, max_depth=2)
        rf.save(artifact)

        m1 = registry.register_model(
            model_name="A1", algorithm="RandomForest", version="1.0.0",
            pipeline_id="pipeline_a_fi2010", prediction_target="t",
            prediction_horizon=100, task_type="classification",
            feature_schema=["f1"], artifact_path=artifact, metrics={"accuracy": 0.53, "f1_macro": 0.41}
        )
        m2 = registry.register_model(
            model_name="A2", algorithm="XGBoost", version="1.0.0",
            pipeline_id="pipeline_a_fi2010", prediction_target="t",
            prediction_horizon=100, task_type="classification",
            feature_schema=["f1"], artifact_path=artifact, metrics={"accuracy": 0.55, "f1_macro": 0.44}
        )

        df_comp = registry.compare_models([m1, m2])
        assert len(df_comp) == 2
        assert "Accuracy (%)" in df_comp.columns
        assert pytest.approx(df_comp.loc[df_comp["Model ID"] == m2, "Accuracy (%)"].iloc[0], 0.01) == 55.0


def test_feature_schema_validation():
    """Verify feature schema alignment checks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_file = Path(tmpdir) / "registry.json"
        registry = ModelRegistry(registry_file=reg_file)

        artifact = Path(tmpdir) / "dummy.joblib"
        rf = AstraRandomForest(n_estimators=5, max_depth=2)
        rf.save(artifact)

        mid = registry.register_model(
            model_name="SchemaTest", algorithm="RandomForest", version="1.0.0",
            pipeline_id="p1", prediction_target="t", prediction_horizon=1,
            task_type="classification", feature_schema=["rsi", "macd", "vol"],
            artifact_path=artifact
        )

        # Correct schema
        assert registry.validate_feature_schema(mid, ["rsi", "macd", "vol"]) is True
        # Wrong count
        assert registry.validate_feature_schema(mid, ["rsi", "macd"]) is False
        # Wrong names
        assert registry.validate_feature_schema(mid, ["rsi", "macd", "atr"]) is False


def test_register_existing_baselines():
    """Verify auto-registration of the four pre-existing FI-2010 RF baseline binaries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        reg_file = Path(tmpdir) / "registry.json"
        registry = ModelRegistry(registry_file=reg_file)
        registry.register_existing_baselines()

        models = registry.list_models(pipeline_id="pipeline_a_fi2010")
        assert len(models) >= 4

        # Check approved auction model
        approved = registry.get_approved_model("pipeline_a_fi2010", "mid_price_movement_h100")
        assert approved is not None
        assert "balanced" in approved["model_name"].lower()
