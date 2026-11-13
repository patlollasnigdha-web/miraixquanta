"""
MIRAI — Random Forest Classifier Model (M03)
Modular, reproducible Random Forest implementation for market movement prediction.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.models.base_model import BasePredictiveModel
from src.models.model_evaluation import evaluate_classifier

logger = get_logger("RandomForestModel")


class AstraRandomForest(BasePredictiveModel):
    """
    Random Forest wrapper supporting configurable hyperparameters, class weighting,
    prediction, feature importance analysis, and model serialization.
    """

    def __init__(
        self,
        n_estimators: Optional[int] = None,
        max_depth: Optional[int] = None,
        min_samples_leaf: Optional[int] = None,
        class_weight: Optional[Union[str, dict]] = None,
        random_state: Optional[int] = None,
        n_jobs: Optional[int] = None,
        pipeline_id: str = "pipeline_a_fi2010",
        prediction_target: str = "mid_price_movement",
        prediction_horizon: int = 100,
    ):
        super().__init__(
            model_name="AstraRandomForest",
            task_type="classification",
            pipeline_id=pipeline_id,
            prediction_target=prediction_target,
            prediction_horizon=prediction_horizon,
        )
        cfg = get_config()
        rf_cfg = cfg.get("models.random_forest", {})

        self.n_estimators = n_estimators or rf_cfg.get("n_estimators", 150)
        self.max_depth = max_depth if max_depth is not None else rf_cfg.get("max_depth", 20)
        self.min_samples_leaf = min_samples_leaf or rf_cfg.get("min_samples_leaf", 5)
        self.class_weight = class_weight or rf_cfg.get("class_weight", "balanced_subsample")
        self.random_state = random_state or rf_cfg.get("random_state", 42)
        self.n_jobs = n_jobs or rf_cfg.get("n_jobs", -1)

        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_leaf=self.min_samples_leaf,
            class_weight=self.class_weight,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
        )
        self.is_fitted = False

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        **kwargs: Any,
    ) -> "AstraRandomForest":
        """Fits the Random Forest model on training data."""
        X_arr = self.validate_input_shape(X, expected_dim=2)
        y_arr = np.asarray(y)

        logger.info(
            "Fitting RandomForest (n_estimators=%d, max_depth=%s, class_weight=%s)...",
            self.n_estimators, str(self.max_depth), str(self.class_weight)
        )
        self.model.fit(X_arr, y_arr)
        self.is_fitted = True
        logger.info("RandomForest fitting complete.")
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predicts class labels for samples in X."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet. Call fit() before predicting.")
        X_arr = self.validate_input_shape(X, expected_dim=2)
        return self.model.predict(X_arr)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predicts class probabilities for samples in X."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet. Call fit() before predicting.")
        X_arr = self.validate_input_shape(X, expected_dim=2)
        return self.model.predict_proba(X_arr)

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        model_name: str = "AstraRandomForest",
    ) -> Dict[str, Any]:
        """Evaluates model on test data using unified evaluation harness."""
        preds = self.predict(X_test)
        probas = self.predict_proba(X_test)
        return evaluate_classifier(
            y_true=y_test,
            y_pred=preds,
            y_prob=probas,
            labels=(1, 2, 3),
            model_name=model_name,
        )

    def get_feature_importances(self) -> np.ndarray:
        """Returns Gini feature importances."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        return self.model.feature_importances_

    def save(self, file_path: Union[str, Path]) -> Path:
        """Serializes fitted model to disk using joblib."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)
        logger.info("Saved RandomForest model to: %s", path)
        return path

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> "AstraRandomForest":
        """Loads a serialized RandomForest model from disk."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        loaded_model = joblib.load(path)
        instance = cls()
        instance.model = loaded_model
        instance.is_fitted = True
        logger.info("Loaded RandomForest model from: %s", path)
        return instance
