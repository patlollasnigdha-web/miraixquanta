"""
ASTRAQUANT X — XGBoost Classifier Model
Gradient-boosted decision tree pipeline for high-frequency market movement prediction.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union
import numpy as np
import joblib
from xgboost import XGBClassifier

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.models.model_evaluation import evaluate_classifier

logger = get_logger("XGBoostModel")


class AstraXGBoost:
    """
    XGBoost classifier supporting multi-class market prediction.
    Automatically handles 1-based FI-2010 labels {1, 2, 3} <-> 0-based {0, 1, 2}.
    """

    def __init__(
        self,
        n_estimators: Optional[int] = None,
        max_depth: Optional[int] = None,
        learning_rate: Optional[float] = None,
        subsample: Optional[float] = None,
        colsample_bytree: Optional[float] = None,
        random_state: Optional[int] = None,
        n_jobs: Optional[int] = None,
    ):
        cfg = get_config()
        xgb_cfg = cfg.get("models.xgboost", {})

        self.n_estimators = n_estimators or xgb_cfg.get("n_estimators", 150)
        self.max_depth = max_depth if max_depth is not None else xgb_cfg.get("max_depth", 6)
        self.learning_rate = learning_rate or xgb_cfg.get("learning_rate", 0.05)
        self.subsample = subsample or xgb_cfg.get("subsample", 0.8)
        self.colsample_bytree = colsample_bytree or xgb_cfg.get("colsample_bytree", 0.8)
        self.random_state = random_state or xgb_cfg.get("random_state", 42)
        self.n_jobs = n_jobs or xgb_cfg.get("n_jobs", 4)
        self.tree_method = xgb_cfg.get("tree_method", "hist")

        self.model = XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
            tree_method=self.tree_method,
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
        )
        self.is_fitted = False
        self.label_offset = 1  # Map {1, 2, 3} -> {0, 1, 2}

    def _to_internal_labels(self, y: np.ndarray) -> np.ndarray:
        if np.min(y) == 1 and np.max(y) == 3:
            return y - self.label_offset
        return y

    def _to_external_labels(self, y: np.ndarray) -> np.ndarray:
        return y + self.label_offset

    def fit(self, X: np.ndarray, y: np.ndarray) -> "AstraXGBoost":
        """Fits XGBoost classifier on training data."""
        y_int = self._to_internal_labels(y)
        logger.info(
            "Fitting XGBoost (n_estimators=%d, max_depth=%d, lr=%.3f)...",
            self.n_estimators, self.max_depth, self.learning_rate
        )
        self.model.fit(X, y_int)
        self.is_fitted = True
        logger.info("XGBoost fitting complete.")
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predicts class labels in original label space {1, 2, 3}."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        preds_int = self.model.predict(X)
        return self._to_external_labels(preds_int)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predicts class probabilities."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        return self.model.predict_proba(X)

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        model_name: str = "AstraXGBoost",
    ) -> Dict[str, Any]:
        """Evaluates model performance against ground truth."""
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
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        return self.model.feature_importances_

    def save(self, file_path: Union[str, Path]) -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)
        logger.info("Saved XGBoost model to: %s", path)
        return path

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> "AstraXGBoost":
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        loaded = joblib.load(path)
        instance = cls()
        instance.model = loaded
        instance.is_fitted = True
        logger.info("Loaded XGBoost model from: %s", path)
        return instance
