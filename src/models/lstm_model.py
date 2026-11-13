"""
MIRAI — Long Short-Term Memory (LSTM) Sequential Model (M03)
Provides sequence modeling for temporal order-book and candle-bar dynamics.
Supports both PyTorch (when available) and a deterministic NumPy reference engine.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.models.base_model import BasePredictiveModel
from src.models.model_evaluation import evaluate_classifier, evaluate_regression

logger = get_logger("LSTMModel")

# Detect PyTorch availability gracefully
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import TensorDataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.info("PyTorch is not installed in the environment. Using NumPy sequential engine.")


class AstraLSTM(BasePredictiveModel):
    """
    Recurrent Neural Network supporting both classification and regression tasks
    on multi-variate time-series inputs of shape (N_samples, Sequence_length, Feature_dim).
    """

    def __init__(
        self,
        input_dim: int = 144,
        sequence_length: int = 10,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        learning_rate: float = 0.001,
        task_type: str = "classification",  # 'classification' or 'regression'
        num_classes: int = 3,
        batch_size: int = 64,
        epochs: int = 15,
        patience: int = 4,
        random_state: int = 42,
        pipeline_id: str = "pipeline_a_fi2010",
        prediction_target: str = "mid_price_movement",
        prediction_horizon: int = 100,
    ):
        super().__init__(
            model_name="AstraLSTM",
            task_type=task_type,
            pipeline_id=pipeline_id,
            prediction_target=prediction_target,
            prediction_horizon=prediction_horizon,
        )
        self.input_dim = input_dim
        self.sequence_length = sequence_length
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.num_classes = num_classes
        self.batch_size = batch_size
        self.epochs = epochs
        self.patience = patience
        self.random_state = random_state

        self.history: Dict[str, List[float]] = {"train_loss": [], "val_loss": []}
        self.weights: Dict[str, np.ndarray] = {}
        self.torch_model = None

        if TORCH_AVAILABLE:
            self._init_torch_model()
        else:
            self._init_numpy_weights()

    def _init_numpy_weights(self):
        """Initializes lightweight deterministic NumPy weights for sequence projection."""
        rng = np.random.RandomState(self.random_state)
        # Sequence pooling + Linear projection weights
        self.weights = {
            "W_in": rng.randn(self.input_dim, self.hidden_dim).astype(np.float32) * 0.05,
            "b_in": np.zeros(self.hidden_dim, dtype=np.float32),
            "W_rec": rng.randn(self.hidden_dim, self.hidden_dim).astype(np.float32) * 0.05,
            "W_out": rng.randn(
                self.hidden_dim, self.num_classes if self.task_type == "classification" else 1
            ).astype(np.float32) * 0.05,
            "b_out": np.zeros(
                self.num_classes if self.task_type == "classification" else 1, dtype=np.float32
            ),
        }

    def _init_torch_model(self):
        """Builds native PyTorch LSTM module."""
        class _TorchLSTM(nn.Module):
            def __init__(self, in_dim, h_dim, n_layers, drop, out_dim, task):
                super().__init__()
                self.lstm = nn.LSTM(
                    input_size=in_dim,
                    hidden_size=h_dim,
                    num_layers=n_layers,
                    batch_first=True,
                    dropout=drop if n_layers > 1 else 0.0,
                )
                self.fc = nn.Linear(h_dim, out_dim)
                self.task = task

            def forward(self, x):
                out, _ = self.lstm(x)
                last_step = out[:, -1, :]
                logits = self.fc(last_step)
                return logits

        out_dim = self.num_classes if self.task_type == "classification" else 1
        self.torch_model = _TorchLSTM(
            self.input_dim, self.hidden_dim, self.num_layers, self.dropout, out_dim, self.task_type
        )

    def _prepare_inputs(self, X: np.ndarray) -> np.ndarray:
        """Validates and formats input array into (N, T, d)."""
        X_arr = np.asarray(X, dtype=np.float32)
        if X_arr.ndim == 2:
            logger.debug("Input X is 2D (N, d). Expanding to (N, 1, d) for sequence model.")
            X_arr = np.expand_dims(X_arr, axis=1)
        elif X_arr.ndim != 3:
            raise ValueError(f"Expected 3D input (N, T, d) for LSTM, got {X_arr.shape}")
        return X_arr

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        **kwargs: Any,
    ) -> "AstraLSTM":
        """
        Trains the LSTM model with validation monitoring and early stopping.
        """
        X_train = self._prepare_inputs(X)
        y_train = np.asarray(y)

        # Map {1, 2, 3} -> {0, 1, 2} for multi-class classification
        if self.task_type == "classification":
            if np.min(y_train) == 1 and np.max(y_train) == 3:
                y_train = y_train - 1

        val_exists = X_val is not None and y_val is not None
        if val_exists:
            X_val_p = self._prepare_inputs(X_val)
            y_val_p = np.asarray(y_val)
            if self.task_type == "classification" and np.min(y_val_p) == 1 and np.max(y_val_p) == 3:
                y_val_p = y_val_p - 1

        if TORCH_AVAILABLE and self.torch_model is not None:
            self._fit_torch(X_train, y_train, X_val_p if val_exists else None, y_val_p if val_exists else None)
        else:
            self._fit_numpy(X_train, y_train, X_val_p if val_exists else None, y_val_p if val_exists else None)

        self.is_fitted = True
        return self

    def _fit_numpy(self, X: np.ndarray, y: np.ndarray, X_val: Optional[np.ndarray], y_val: Optional[np.ndarray]):
        """Simple, gradient-step training loop for NumPy reference engine."""
        n_samples = len(X)
        best_val_loss = float("inf")
        patience_counter = 0

        for epoch in range(self.epochs):
            # Forward pass on batches
            perm = np.random.RandomState(self.random_state + epoch).permutation(n_samples)
            epoch_loss = 0.0
            steps = 0

            for i in range(0, n_samples, self.batch_size):
                batch_idx = perm[i : i + self.batch_size]
                X_b = X[batch_idx]
                y_b = y[batch_idx]

                # Mean pool sequence + tanh recurrent state
                seq_pooled = np.mean(X_b, axis=1)  # (B, d)
                h = np.tanh(seq_pooled @ self.weights["W_in"] + self.weights["b_in"])
                logits = h @ self.weights["W_out"] + self.weights["b_out"]

                if self.task_type == "classification":
                    # Softmax
                    exp_l = np.exp(logits - np.max(logits, axis=1, keepdims=True))
                    probs = exp_l / np.sum(exp_l, axis=1, keepdims=True)
                    loss = -np.mean(np.log(probs[np.arange(len(y_b)), y_b.astype(int)] + 1e-8))

                    # Gradient step
                    grad_out = probs.copy()
                    grad_out[np.arange(len(y_b)), y_b.astype(int)] -= 1.0
                    grad_out /= len(y_b)
                else:
                    preds = logits.squeeze(-1)
                    loss = np.mean((preds - y_b) ** 2)
                    grad_out = (2.0 * (preds - y_b) / len(y_b))[:, None]

                # Update weights
                dW_out = h.T @ grad_out
                db_out = np.sum(grad_out, axis=0)
                dh = grad_out @ self.weights["W_out"].T * (1.0 - h ** 2)
                dW_in = seq_pooled.T @ dh
                db_in = np.sum(dh, axis=0)

                self.weights["W_out"] -= self.learning_rate * dW_out
                self.weights["b_out"] -= self.learning_rate * db_out
                self.weights["W_in"] -= self.learning_rate * dW_in
                self.weights["b_in"] -= self.learning_rate * db_in

                epoch_loss += loss
                steps += 1

            train_loss = epoch_loss / max(1, steps)
            self.history["train_loss"].append(float(train_loss))

            # Validation loss
            if X_val is not None and y_val is not None:
                val_loss = self._compute_numpy_loss(X_val, y_val)
                self.history["val_loss"].append(float(val_loss))

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= self.patience:
                        logger.debug("Early stopping triggered at epoch %d (val_loss=%.4f)", epoch, val_loss)
                        break

    def _compute_numpy_loss(self, X: np.ndarray, y: np.ndarray) -> float:
        seq_pooled = np.mean(X, axis=1)
        h = np.tanh(seq_pooled @ self.weights["W_in"] + self.weights["b_in"])
        logits = h @ self.weights["W_out"] + self.weights["b_out"]

        if self.task_type == "classification":
            exp_l = np.exp(logits - np.max(logits, axis=1, keepdims=True))
            probs = exp_l / np.sum(exp_l, axis=1, keepdims=True)
            return float(-np.mean(np.log(probs[np.arange(len(y)), y.astype(int)] + 1e-8)))
        else:
            preds = logits.squeeze(-1)
            return float(np.mean((preds - y) ** 2))

    def _fit_torch(self, X: np.ndarray, y: np.ndarray, X_val: Optional[np.ndarray], y_val: Optional[np.ndarray]):
        """Native PyTorch training loop."""
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.torch_model.to(device)

        X_t = torch.tensor(X, dtype=torch.float32)
        y_t = torch.tensor(y, dtype=torch.long if self.task_type == "classification" else torch.float32)

        dataset = TensorDataset(X_t, y_t)
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

        criterion = nn.CrossEntropyLoss() if self.task_type == "classification" else nn.MSELoss()
        optimizer = optim.Adam(self.torch_model.parameters(), lr=self.learning_rate)

        best_val = float("inf")
        patience_counter = 0

        for epoch in range(self.epochs):
            self.torch_model.train()
            total_loss = 0.0
            for bx, by in loader:
                bx, by = bx.to(device), by.to(device)
                optimizer.zero_grad()
                out = self.torch_model(bx)
                if self.task_type != "classification":
                    out = out.squeeze(-1)
                loss = criterion(out, by)
                loss.backward()
                optimizer.step()
                total_loss += loss.item() * len(bx)

            avg_train = total_loss / len(X)
            self.history["train_loss"].append(avg_train)

            if X_val is not None and y_val is not None:
                self.torch_model.eval()
                with torch.no_grad():
                    vx = torch.tensor(X_val, dtype=torch.float32).to(device)
                    vy = torch.tensor(
                        y_val, dtype=torch.long if self.task_type == "classification" else torch.float32
                    ).to(device)
                    vout = self.torch_model(vx)
                    if self.task_type != "classification":
                        vout = vout.squeeze(-1)
                    val_l = criterion(vout, vy).item()
                    self.history["val_loss"].append(val_l)

                    if val_l < best_val:
                        best_val = val_l
                        patience_counter = 0
                    else:
                        patience_counter += 1
                        if patience_counter >= self.patience:
                            break

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predicts class labels (1-based for classification) or values for regression."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        X_p = self._prepare_inputs(X)

        if TORCH_AVAILABLE and self.torch_model is not None:
            self.torch_model.eval()
            with torch.no_grad():
                out = self.torch_model(torch.tensor(X_p, dtype=torch.float32))
                if self.task_type == "classification":
                    preds = torch.argmax(out, dim=1).cpu().numpy()
                    return preds + 1  # Map {0, 1, 2} -> {1, 2, 3}
                return out.squeeze(-1).cpu().numpy()
        else:
            seq_pooled = np.mean(X_p, axis=1)
            h = np.tanh(seq_pooled @ self.weights["W_in"] + self.weights["b_in"])
            logits = h @ self.weights["W_out"] + self.weights["b_out"]
            if self.task_type == "classification":
                preds = np.argmax(logits, axis=1)
                return preds + 1
            return logits.squeeze(-1)

    def predict_proba(self, X: np.ndarray) -> Optional[np.ndarray]:
        """Predicts class probabilities."""
        if self.task_type != "classification":
            return None
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        X_p = self._prepare_inputs(X)

        if TORCH_AVAILABLE and self.torch_model is not None:
            self.torch_model.eval()
            with torch.no_grad():
                out = self.torch_model(torch.tensor(X_p, dtype=torch.float32))
                probs = torch.softmax(out, dim=1).cpu().numpy()
                return probs
        else:
            seq_pooled = np.mean(X_p, axis=1)
            h = np.tanh(seq_pooled @ self.weights["W_in"] + self.weights["b_in"])
            logits = h @ self.weights["W_out"] + self.weights["b_out"]
            exp_l = np.exp(logits - np.max(logits, axis=1, keepdims=True))
            probs = exp_l / np.sum(exp_l, axis=1, keepdims=True)
            return probs

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        model_name: str = "AstraLSTM",
    ) -> Dict[str, Any]:
        """Unified evaluation helper."""
        preds = self.predict(X_test)
        if self.task_type == "classification":
            probas = self.predict_proba(X_test)
            return evaluate_classifier(y_true=y_test, y_pred=preds, y_prob=probas, model_name=model_name)
        else:
            return evaluate_regression(y_true=y_test, y_pred=preds, model_name=model_name)

    def save(self, file_path: Union[str, Path]) -> Path:
        """Saves model weights and hyperparameters."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "input_dim": self.input_dim,
            "sequence_length": self.sequence_length,
            "hidden_dim": self.hidden_dim,
            "num_layers": self.num_layers,
            "dropout": self.dropout,
            "learning_rate": self.learning_rate,
            "task_type": self.task_type,
            "num_classes": self.num_classes,
            "random_state": self.random_state,
        }
        # Save archive
        np.savez_compressed(
            path,
            config=json.dumps(config),
            **self.weights,
        )
        logger.info("Saved AstraLSTM model to: %s", path)
        return path

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> "AstraLSTM":
        """Loads model weights and configuration."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        data = np.load(path, allow_pickle=True)
        config = json.loads(str(data["config"]))
        instance = cls(**config)
        instance.weights = {k: data[k] for k in data.files if k != "config"}
        instance.is_fitted = True
        logger.info("Loaded AstraLSTM model from: %s", path)
        return instance
