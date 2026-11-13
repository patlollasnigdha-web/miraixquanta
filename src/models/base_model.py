"""
MIRAI — Base Predictive Model Interface (M03)
Establishes a uniform contract for Classical ML, Deep Learning, and Transformer models.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


class BasePredictiveModel(ABC):
    """
    Abstract Base Class for all predictive models in MIRAI.
    Ensures unified lifecycle: configuration, training, evaluation, inference, and serialization.
    """

    def __init__(
        self,
        model_name: str = "BaseModel",
        task_type: str = "classification",  # 'classification' or 'regression'
        pipeline_id: str = "pipeline_a_fi2010",
        prediction_target: str = "mid_price_movement",
        prediction_horizon: int = 100,
    ):
        self.model_name = model_name
        self.task_type = task_type
        self.pipeline_id = pipeline_id
        self.prediction_target = prediction_target
        self.prediction_horizon = prediction_horizon
        self.is_fitted = False
        self.feature_names: Optional[List[str]] = None

    @abstractmethod
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        **kwargs: Any,
    ) -> "BasePredictiveModel":
        """Fits the model on training data with optional validation tracking."""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generates predictions (class labels for classification, continuous values for regression)."""
        pass

    def predict_proba(self, X: np.ndarray) -> Optional[np.ndarray]:
        """
        Generates class probability distributions for classification models.
        Returns None for regression models.
        """
        return None

    @abstractmethod
    def save(self, file_path: Union[str, Path]) -> Path:
        """Serializes model weights and configuration to disk."""
        pass

    @classmethod
    @abstractmethod
    def load(cls, file_path: Union[str, Path]) -> "BasePredictiveModel":
        """Deserializes a saved model from disk."""
        pass

    def get_feature_importances(self) -> Optional[np.ndarray]:
        """Returns feature importances if supported by the algorithm, else None."""
        return None

    def validate_input_shape(
        self, X: np.ndarray, expected_dim: int = 2
    ) -> np.ndarray:
        """Validates that input array matches expected dimensionality."""
        X_arr = np.asarray(X)
        if X_arr.ndim != expected_dim:
            raise ValueError(
                f"Model '{self.model_name}' expected input with {expected_dim} dimensions, "
                f"got shape {X_arr.shape} ({X_arr.ndim} dimensions)."
            )
        if np.isnan(X_arr).any():
            raise ValueError(f"Input features to '{self.model_name}' contain NaN values.")
        if np.isinf(X_arr).any():
            raise ValueError(f"Input features to '{self.model_name}' contain infinite values.")
        return X_arr
