"""
MIRAI — Persistent Model Registry & Lifecycle Engine (M04)
Tracks model versions, algorithms, hyperparameter configurations, feature schemas,
evaluation metrics, approval statuses, and artifact binaries.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.models.random_forest import AstraRandomForest
from src.models.xgboost_model import AstraXGBoost
from src.models.lstm_model import AstraLSTM
from src.models.transformer_model import AstraTransformer

logger = get_logger("ModelRegistry")

VALID_STATUSES = ("experimental", "validated", "approved", "deprecated")


class ModelRegistry:
    """
    Persistent model catalog maintaining metadata, versions, and validation history.
    """

    def __init__(self, registry_file: Optional[Path] = None):
        if registry_file is None:
            self.registry_file = PROJECT_ROOT / "models" / "registry.json"
        else:
            self.registry_file = Path(registry_file)

        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.entries: Dict[str, Dict[str, Any]] = self._load_registry()

    def _load_registry(self) -> Dict[str, Dict[str, Any]]:
        """Loads JSON registry from disk."""
        if not self.registry_file.exists():
            return {}
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.error("Failed to load registry from %s: %s", self.registry_file, exc)
            return {}

    def _save_registry(self):
        """Persists JSON registry to disk."""
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2)
        logger.debug("Persisted registry with %d models to: %s", len(self.entries), self.registry_file)

    def register_model(
        self,
        model_name: str,
        algorithm: str,
        version: str,
        pipeline_id: str,
        prediction_target: str,
        prediction_horizon: int,
        task_type: str,
        feature_schema: List[str],
        artifact_path: Union[str, Path],
        hyperparameters: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        preprocessing_config: Optional[Dict[str, Any]] = None,
        training_period: Optional[Dict[str, str]] = None,
        status: str = "experimental",
        overwrite: bool = False,
    ) -> str:
        """
        Registers a new model version. Prevents silent overwrites.
        Returns unique `model_id`.
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {VALID_STATUSES}")

        model_id = f"{model_name}_v{version}".replace(" ", "_").lower()

        if model_id in self.entries and not overwrite:
            raise ValueError(
                f"Model ID '{model_id}' already exists in registry. "
                "Specify a new version or set overwrite=True."
            )

        # Resolve artifact path relative to PROJECT_ROOT for portability
        artifact_abs = (PROJECT_ROOT / artifact_path).resolve() if not Path(artifact_path).is_absolute() else Path(artifact_path)
        if not artifact_abs.exists():
            raise FileNotFoundError(f"Model artifact file does not exist at: {artifact_abs}")

        try:
            rel_artifact = str(artifact_abs.relative_to(PROJECT_ROOT)).replace("\\", "/")
        except ValueError:
            rel_artifact = str(artifact_abs).replace("\\", "/")

        now_utc = datetime.now(timezone.utc).isoformat()

        record: Dict[str, Any] = {
            "model_id": model_id,
            "model_name": model_name,
            "algorithm": algorithm,
            "version": version,
            "pipeline_id": pipeline_id,
            "prediction_target": prediction_target,
            "prediction_horizon": int(prediction_horizon),
            "task_type": task_type,
            "feature_count": len(feature_schema),
            "feature_schema": list(feature_schema),
            "artifact_path": rel_artifact,
            "hyperparameters": hyperparameters or {},
            "metrics": metrics or {},
            "preprocessing_config": preprocessing_config or {},
            "training_period": training_period or {"start": "N/A", "end": "N/A"},
            "status": status,
            "created_at": now_utc,
            "history": [
                {
                    "action": "registered",
                    "timestamp": now_utc,
                    "status": status,
                    "metrics": metrics or {},
                }
            ],
        }

        self.entries[model_id] = record
        self._save_registry()
        logger.info("Successfully registered model '%s' (Algorithm: %s, Version: %s)", model_id, algorithm, version)
        return model_id

    def get_model_metadata(self, model_id: str) -> Dict[str, Any]:
        """Retrieves registered metadata record for a model ID."""
        if model_id not in self.entries:
            raise KeyError(f"Model ID '{model_id}' not found in registry.")
        return self.entries[model_id].copy()

    def list_models(
        self,
        pipeline_id: Optional[str] = None,
        status: Optional[str] = None,
        algorithm: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Queries registered models with optional filtering."""
        matched = []
        for m in self.entries.values():
            if pipeline_id and m.get("pipeline_id") != pipeline_id:
                continue
            if status and m.get("status") != status:
                continue
            if algorithm and m.get("algorithm") != algorithm:
                continue
            matched.append(m.copy())
        return matched

    def set_model_status(
        self,
        model_id: str,
        status: str,
        notes: Optional[str] = None,
    ):
        """Updates the status (experimental -> validated -> approved -> deprecated)."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {VALID_STATUSES}")
        if model_id not in self.entries:
            raise KeyError(f"Model ID '{model_id}' not found.")

        old_status = self.entries[model_id]["status"]
        self.entries[model_id]["status"] = status
        now_utc = datetime.now(timezone.utc).isoformat()

        self.entries[model_id]["history"].append({
            "action": f"status_change_{old_status}_to_{status}",
            "timestamp": now_utc,
            "notes": notes or "",
        })
        self._save_registry()
        logger.info("Updated status for '%s': %s -> %s", model_id, old_status, status)

    def get_approved_model(
        self,
        pipeline_id: str,
        prediction_target: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves the officially approved model record for a specific pipeline and target.
        """
        for m in self.entries.values():
            if (
                m.get("pipeline_id") == pipeline_id
                and m.get("prediction_target") == prediction_target
                and m.get("status") == "approved"
            ):
                return m.copy()
        return None

    def save_evaluation(
        self,
        model_id: str,
        metrics: Dict[str, Any],
        notes: Optional[str] = None,
    ):
        """Appends new out-of-sample evaluation metrics to model history."""
        if model_id not in self.entries:
            raise KeyError(f"Model ID '{model_id}' not found.")

        self.entries[model_id]["metrics"] = metrics
        now_utc = datetime.now(timezone.utc).isoformat()
        self.entries[model_id]["history"].append({
            "action": "evaluation_updated",
            "timestamp": now_utc,
            "metrics": metrics,
            "notes": notes or "",
        })
        self._save_registry()
        logger.info("Recorded evaluation metrics for '%s'", model_id)

    def validate_feature_schema(
        self,
        model_id: str,
        feature_names: List[str],
    ) -> bool:
        """
        Validates that an incoming feature list strictly matches the registered schema.
        Detects missing or misaligned feature columns before running inference.
        """
        if model_id not in self.entries:
            raise KeyError(f"Model ID '{model_id}' not found.")

        reg_schema = self.entries[model_id].get("feature_schema", [])
        if len(reg_schema) != len(feature_names):
            logger.warning(
                "Schema count mismatch for '%s': expected %d features, got %d",
                model_id, len(reg_schema), len(feature_names)
            )
            return False

        if list(reg_schema) != list(feature_names):
            logger.warning("Feature column names do not match registered schema for '%s'", model_id)
            return False

        return True

    def compare_models(self, model_ids: List[str]) -> pd.DataFrame:
        """Compares registered models side by side."""
        records = []
        for mid in model_ids:
            if mid not in self.entries:
                continue
            entry = self.entries[mid]
            mets = entry.get("metrics", {})
            row = {
                "Model ID": mid,
                "Algorithm": entry.get("algorithm"),
                "Version": entry.get("version"),
                "Status": entry.get("status"),
                "Task": entry.get("task_type"),
                "Pipeline": entry.get("pipeline_id"),
                "Accuracy (%)": round(mets.get("accuracy", 0.0) * 100, 2) if "accuracy" in mets else None,
                "Balanced Acc (%)": round(mets.get("balanced_accuracy", 0.0) * 100, 2) if "balanced_accuracy" in mets else None,
                "Macro F1 (%)": round(mets.get("f1_macro", 0.0) * 100, 2) if "f1_macro" in mets else None,
                "MAE": mets.get("mae"),
                "RMSE": mets.get("rmse"),
                "R²": mets.get("r2_score"),
            }
            records.append(row)
        return pd.DataFrame(records)

    def load_model_artifact(self, model_id: str) -> Any:
        """Loads and returns the trained model object using the registered algorithm loader."""
        if model_id not in self.entries:
            raise KeyError(f"Model ID '{model_id}' not found.")

        meta = self.entries[model_id]
        algo = meta.get("algorithm")
        rel_path = meta.get("artifact_path")
        abs_path = PROJECT_ROOT / rel_path

        if not abs_path.exists():
            raise FileNotFoundError(f"Model binary artifact missing at: {abs_path}")

        if algo == "RandomForest":
            return AstraRandomForest.load(abs_path)
        elif algo == "XGBoost":
            return AstraXGBoost.load(abs_path)
        elif algo == "LSTM":
            return AstraLSTM.load(abs_path)
        elif algo == "Transformer":
            return AstraTransformer.load(abs_path)
        else:
            raise ValueError(f"Unknown algorithm '{algo}' for artifact loading.")

    def register_existing_baselines(self):
        """
        Scans models/ for the pre-existing 4 Random Forest baseline models
        and registers them with their verified academic benchmark metrics.
        """
        baselines = [
            {
                "name": "FI2010_Auction_Baseline_RF",
                "algo": "RandomForest",
                "ver": "1.0.0",
                "pipeline": "pipeline_a_fi2010",
                "target": "mid_price_movement_h100",
                "horizon": 100,
                "task": "classification",
                "path": "models/auction_baseline_rf.joblib",
                "metrics": {
                    "accuracy": 0.5263,
                    "balanced_accuracy": 0.4377,
                    "f1_macro": 0.3997,
                },
                "status": "validated",
            },
            {
                "name": "FI2010_Auction_Balanced_RF",
                "algo": "RandomForest",
                "ver": "1.0.0",
                "pipeline": "pipeline_a_fi2010",
                "target": "mid_price_movement_h100",
                "horizon": 100,
                "task": "classification",
                "path": "models/auction_balanced_rf.joblib",
                "metrics": {
                    "accuracy": 0.5274,
                    "balanced_accuracy": 0.4433,
                    "f1_macro": 0.4139,
                },
                "status": "approved",
            },
            {
                "name": "FI2010_NoAuction_Baseline_RF",
                "algo": "RandomForest",
                "ver": "1.0.0",
                "pipeline": "pipeline_a_fi2010",
                "target": "mid_price_movement_h100",
                "horizon": 100,
                "task": "classification",
                "path": "models/non_auction_baseline_rf.joblib",
                "metrics": {
                    "accuracy": 0.5262,
                    "balanced_accuracy": 0.4289,
                    "f1_macro": 0.3855,
                },
                "status": "validated",
            },
            {
                "name": "FI2010_NoAuction_Balanced_RF",
                "algo": "RandomForest",
                "ver": "1.0.0",
                "pipeline": "pipeline_a_fi2010",
                "target": "mid_price_movement_h100",
                "horizon": 100,
                "task": "classification",
                "path": "models/non_auction_balanced_rf.joblib",
                "metrics": {
                    "accuracy": 0.5261,
                    "balanced_accuracy": 0.4304,
                    "f1_macro": 0.3904,
                },
                "status": "approved",
            },
        ]

        dummy_144_schema = [f"lob_feature_{i}" for i in range(144)]

        for b in baselines:
            artifact_file = PROJECT_ROOT / b["path"]
            if artifact_file.exists():
                try:
                    self.register_model(
                        model_name=b["name"],
                        algorithm=b["algo"],
                        version=b["ver"],
                        pipeline_id=b["pipeline"],
                        prediction_target=b["target"],
                        prediction_horizon=b["horizon"],
                        task_type=b["task"],
                        feature_schema=dummy_144_schema,
                        artifact_path=b["path"],
                        hyperparameters={"n_estimators": 150, "max_depth": 20, "min_samples_leaf": 5},
                        metrics=b["metrics"],
                        status=b["status"],
                        overwrite=True,
                    )
                except Exception as exc:
                    logger.debug("Could not auto-register %s: %s", b["name"], exc)


# Global singleton factory
_registry_instance: Optional[ModelRegistry] = None


def get_model_registry(registry_file: Optional[Path] = None) -> ModelRegistry:
    """Factory helper to obtain singleton ModelRegistry instance."""
    global _registry_instance
    if _registry_instance is None or registry_file is not None:
        _registry_instance = ModelRegistry(registry_file=registry_file)
    return _registry_instance
