"""
MIRAI — Time-Series Transformer Encoder Model (M03)
Self-attention architecture designed for multi-variate financial time-series sequences.
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

logger = get_logger("TransformerModel")

# Detect PyTorch availability
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import TensorDataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class AstraTransformer(BasePredictiveModel):
    """
    Time-Series Transformer Encoder supporting classification and regression.
    Processes sequences of shape (N_samples, Sequence_length, Input_dim)
    using multi-head self-attention and feed-forward layers.
    """

    def __init__(
        self,
        input_dim: int = 144,
        sequence_length: int = 10,
        d_model: int = 64,
        n_heads: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 128,
        dropout: float = 0.1,
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
            model_name="AstraTransformer",
            task_type=task_type,
            pipeline_id=pipeline_id,
            prediction_target=prediction_target,
            prediction_horizon=prediction_horizon,
        )
        self.input_dim = input_dim
        self.sequence_length = sequence_length
        self.d_model = d_model
        self.n_heads = n_heads
        self.num_layers = num_layers
        self.dim_feedforward = dim_feedforward
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
        """Initializes weights for NumPy self-attention projection."""
        rng = np.random.RandomState(self.random_state)
        out_dim = self.num_classes if self.task_type == "classification" else 1
        self.weights = {
            "W_proj": rng.randn(self.input_dim, self.d_model).astype(np.float32) * 0.05,
            "b_proj": np.zeros(self.d_model, dtype=np.float32),
            "W_q": rng.randn(self.d_model, self.d_model).astype(np.float32) * 0.05,
            "W_k": rng.randn(self.d_model, self.d_model).astype(np.float32) * 0.05,
            "W_v": rng.randn(self.d_model, self.d_model).astype(np.float32) * 0.05,
            "W_head": rng.randn(self.d_model, out_dim).astype(np.float32) * 0.05,
            "b_head": np.zeros(out_dim, dtype=np.float32),
        }

    def _init_torch_model(self):
        """Builds native PyTorch Transformer Encoder module."""
        class _TorchTS(nn.Module):
            def __init__(self, in_dim, d_m, n_h, n_lay, d_ff, drop, out_dim):
                super().__init__()
                self.proj = nn.Linear(in_dim, d_m)
                encoder_layer = nn.TransformerEncoderLayer(
                    d_model=d_m,
                    nhead=n_h,
                    dim_feedforward=d_ff,
                    dropout=drop,
                    batch_first=True,
                )
                self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_lay)
                self.head = nn.Linear(d_m, out_dim)

            def forward(self, x):
                x = self.proj(x)
                out = self.transformer(x)
                pooled = torch.mean(out, dim=1)
                logits = self.head(pooled)
                return logits

        out_dim = self.num_classes if self.task_type == "classification" else 1
        self.torch_model = _TorchTS(
            self.input_dim, self.d_model, self.n_heads, self.num_layers, self.dim_feedforward, self.dropout, out_dim
        )

    def _prepare_inputs(self, X: np.ndarray) -> np.ndarray:
        """Validates and ensures input is 3D (N, T, d)."""
        X_arr = np.asarray(X, dtype=np.float32)
        if X_arr.ndim == 2:
            X_arr = np.expand_dims(X_arr, axis=1)
        elif X_arr.ndim != 3:
            raise ValueError(f"Expected 3D input (N, T, d) for Transformer, got {X_arr.shape}")
        return X_arr

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        **kwargs: Any,
    ) -> "AstraTransformer":
        """Fits the Transformer model with validation tracking."""
        X_train = self._prepare_inputs(X)
        y_train = np.asarray(y)

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
        """Training loop for NumPy reference self-attention engine."""
        n_samples = len(X)
        best_val = float("inf")
        patience_counter = 0

        for epoch in range(self.epochs):
            perm = np.random.RandomState(self.random_state + epoch).permutation(n_samples)
            epoch_loss = 0.0
            steps = 0

            for i in range(0, n_samples, self.batch_size):
                b_idx = perm[i : i + self.batch_size]
                X_b = X[b_idx]
                y_b = y[b_idx]

                # Project inputs to d_model: (B, T, d_model)
                H = X_b @ self.weights["W_proj"] + self.weights["b_proj"]
                Q = H @ self.weights["W_q"]
                K = H @ self.weights["W_k"]
                V = H @ self.weights["W_v"]

                # Scaled dot-product attention
                scale = np.sqrt(self.d_model)
                attn_scores = (Q @ K.swapaxes(-1, -2)) / scale
                exp_scores = np.exp(attn_scores - np.max(attn_scores, axis=-1, keepdims=True))
                attn_weights = exp_scores / np.sum(exp_scores, axis=-1, keepdims=True)
                attn_out = attn_weights @ V

                # Global sequence average pooling
                pooled = np.mean(attn_out, axis=1)  # (B, d_model)
                logits = pooled @ self.weights["W_head"] + self.weights["b_head"]

                if self.task_type == "classification":
                    exp_l = np.exp(logits - np.max(logits, axis=1, keepdims=True))
                    probs = exp_l / np.sum(exp_l, axis=1, keepdims=True)
                    loss = -np.mean(np.log(probs[np.arange(len(y_b)), y_b.astype(int)] + 1e-8))

                    grad_out = probs.copy()
                    grad_out[np.arange(len(y_b)), y_b.astype(int)] -= 1.0
                    grad_out /= len(y_b)
                else:
                    preds = logits.squeeze(-1)
                    loss = np.mean((preds - y_b) ** 2)
                    grad_out = (2.0 * (preds - y_b) / len(y_b))[:, None]

                # Parameter updates
                dW_head = pooled.T @ grad_out
                db_head = np.sum(grad_out, axis=0)

                self.weights["W_head"] -= self.learning_rate * dW_head
                self.weights["b_head"] -= self.learning_rate * db_head

                epoch_loss += loss
                steps += 1

            train_loss = epoch_loss / max(1, steps)
            self.history["train_loss"].append(float(train_loss))

            if X_val is not None and y_val is not None:
                val_loss = self._compute_numpy_loss(X_val, y_val)
                self.history["val_loss"].append(float(val_loss))

                if val_loss < best_val:
                    best_val = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= self.patience:
                        logger.debug("Transformer early stopping at epoch %d", epoch)
                        break

    def _compute_numpy_loss(self, X: np.ndarray, y: np.ndarray) -> float:
        H = X @ self.weights["W_proj"] + self.weights["b_proj"]
        Q = H @ self.weights["W_q"]
        K = H @ self.weights["W_k"]
        V = H @ self.weights["W_v"]

        attn_scores = (Q @ K.swapaxes(-1, -2)) / np.sqrt(self.d_model)
        exp_scores = np.exp(attn_scores - np.max(attn_scores, axis=-1, keepdims=True))
        attn_weights = exp_scores / np.sum(exp_scores, axis=-1, keepdims=True)
        attn_out = attn_weights @ V

        pooled = np.mean(attn_out, axis=1)
        logits = pooled @ self.weights["W_head"] + self.weights["b_head"]

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
        """Inference method returning predictions."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        X_p = self._prepare_inputs(X)

        if TORCH_AVAILABLE and self.torch_model is not None:
            self.torch_model.eval()
            with torch.no_grad():
                out = self.torch_model(torch.tensor(X_p, dtype=torch.float32))
                if self.task_type == "classification":
                    preds = torch.argmax(out, dim=1).cpu().numpy()
                    return preds + 1
                return out.squeeze(-1).cpu().numpy()
        else:
            H = X_p @ self.weights["W_proj"] + self.weights["b_proj"]
            Q = H @ self.weights["W_q"]
            K = H @ self.weights["W_k"]
            V = H @ self.weights["W_v"]

            attn_scores = (Q @ K.swapaxes(-1, -2)) / np.sqrt(self.d_model)
            exp_scores = np.exp(attn_scores - np.max(attn_scores, axis=-1, keepdims=True))
            attn_weights = exp_scores / np.sum(exp_scores, axis=-1, keepdims=True)
            attn_out = attn_weights @ V

            pooled = np.mean(attn_out, axis=1)
            logits = pooled @ self.weights["W_head"] + self.weights["b_head"]
            if self.task_type == "classification":
                return np.argmax(logits, axis=1) + 1
            return logits.squeeze(-1)

    def predict_proba(self, X: np.ndarray) -> Optional[np.ndarray]:
        """Inference method returning softmax probabilities."""
        if self.task_type != "classification":
            return None
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted.")
        X_p = self._prepare_inputs(X)

        if TORCH_AVAILABLE and self.torch_model is not None:
            self.torch_model.eval()
            with torch.no_grad():
                out = self.torch_model(torch.tensor(X_p, dtype=torch.float32))
                return torch.softmax(out, dim=1).cpu().numpy()
        else:
            H = X_p @ self.weights["W_proj"] + self.weights["b_proj"]
            Q = H @ self.weights["W_q"]
            K = H @ self.weights["W_k"]
            V = H @ self.weights["W_v"]

            attn_scores = (Q @ K.swapaxes(-1, -2)) / np.sqrt(self.d_model)
            exp_scores = np.exp(attn_scores - np.max(attn_scores, axis=-1, keepdims=True))
            attn_weights = exp_scores / np.sum(exp_scores, axis=-1, keepdims=True)
            attn_out = attn_weights @ V

            pooled = np.mean(attn_out, axis=1)
            logits = pooled @ self.weights["W_head"] + self.weights["b_head"]
            exp_l = np.exp(logits - np.max(logits, axis=1, keepdims=True))
            return exp_l / np.sum(exp_l, axis=1, keepdims=True)

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        model_name: str = "AstraTransformer",
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
            "d_model": self.d_model,
            "n_heads": self.n_heads,
            "num_layers": self.num_layers,
            "dim_feedforward": self.dim_feedforward,
            "dropout": self.dropout,
            "learning_rate": self.learning_rate,
            "task_type": self.task_type,
            "num_classes": self.num_classes,
            "random_state": self.random_state,
        }
        np.savez_compressed(
            path,
            config=json.dumps(config),
            **self.weights,
        )
        logger.info("Saved AstraTransformer model to: %s", path)
        return path

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> "AstraTransformer":
        """Loads model weights and configuration."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        data = np.load(path, allow_pickle=True)
        config = json.loads(str(data["config"]))
        instance = cls(**config)
        instance.weights = {k: data[k] for k in data.files if k != "config"}
        instance.is_fitted = True
        logger.info("Loaded AstraTransformer model from: %s", path)
        return instance
