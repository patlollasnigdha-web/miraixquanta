
from pathlib import Path

import numpy as np
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data" / "processed" / "fi2010"
MODEL_DIR = ROOT / "models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


def load_data(market):
    train_path = DATA_DIR / f"{market}_training_horizon_100.npz"
    test_path = DATA_DIR / f"{market}_testing_horizon_100.npz"

    with np.load(train_path) as train:
        X_train = train["X"]
        y_train = train["y"]

    with np.load(test_path) as test:
        X_test = test["X"]
        y_test = test["y"]

    return X_train, y_train, X_test, y_test


def evaluate_model(name, model, X_test, y_test):
    predictions = model.predict(X_test)

    print(f"\n{name} RESULTS")
    print("-" * 55)

    print("Accuracy:",
          round(accuracy_score(y_test, predictions), 4))

    print("Balanced Accuracy:",
          round(balanced_accuracy_score(y_test, predictions), 4))

    print("Precision (Macro):",
          round(precision_score(
              y_test, predictions,
              average="macro", zero_division=0
          ), 4))

    print("Recall (Macro):",
          round(recall_score(
              y_test, predictions,
              average="macro", zero_division=0
          ), 4))

    print("F1 Score (Macro):",
          round(f1_score(
              y_test, predictions,
              average="macro", zero_division=0
          ), 4))

    print("\nClassification Report:")
    print(classification_report(
        y_test,
        predictions,
        labels=[1, 2, 3],
        zero_division=0
    ))

    print("Confusion Matrix:")
    print(confusion_matrix(
        y_test, predictions,
        labels=[1, 2, 3]
    ))

    print("\nPrediction Distribution:")
    for label in [1, 2, 3]:
        count = np.sum(predictions == label)
        percentage = (count / len(predictions)) * 100
        print(f"Class {label}: {count} ({percentage:.2f}%)")


def run_experiment(market):
    print("\n" + "=" * 60)
    print(f"ASTRAQUANT X - {market.upper()} CLASS-WEIGHTED EXPERIMENT")
    print("=" * 60)

    X_train, y_train, X_test, y_test = load_data(market)

    print("Training samples:", len(X_train))
    print("Testing samples:", len(X_test))
    print("Features:", X_train.shape[1])

    print("\nTraining Class Distribution:")
    for label in [1, 2, 3]:
        count = np.sum(y_train == label)
        percentage = (count / len(y_train)) * 100
        print(f"Class {label}: {count} ({percentage:.2f}%)")

    # Majority-class reference
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_train, y_train)

    evaluate_model(
        "MAJORITY CLASS BASELINE",
        dummy,
        X_test,
        y_test
    )

    # Class-weighted Random Forest
    model = RandomForestClassifier(
        n_estimators=150,
        max_depth=20,
        min_samples_leaf=5,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1
    )

    print("\nTraining Class-Weighted Random Forest...")
    model.fit(X_train, y_train)

    evaluate_model(
        "CLASS-WEIGHTED RANDOM FOREST",
        model,
        X_test,
        y_test
    )

    model_path = MODEL_DIR / f"{market}_balanced_rf.joblib"
    joblib.dump(model, model_path)

    print("\nModel saved:", model_path)


def main():
    run_experiment("auction")
    run_experiment("non_auction")

    print("\n" + "=" * 60)
    print("CLASS-WEIGHTED EXPERIMENTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
