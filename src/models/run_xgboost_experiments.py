"""
ASTRAQUANT X — XGBoost Baseline Experiments
Trains and evaluates AstraXGBoost on FI-2010 auction and non-auction datasets.
Saves metrics to results/ and models to models/.
"""

from pathlib import Path
import numpy as np

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.models.xgboost_model import AstraXGBoost
from src.models.model_evaluation import format_evaluation_report, save_metrics_to_results

logger = get_logger("RunXGBoost")


def load_data(market: str):
    data_dir = PROJECT_ROOT / "data" / "processed" / "fi2010"
    train_path = data_dir / f"{market}_training_horizon_100.npz"
    test_path = data_dir / f"{market}_testing_horizon_100.npz"

    with np.load(train_path) as train:
        X_train = train["X"]
        y_train = train["y"]

    with np.load(test_path) as test:
        X_test = test["X"]
        y_test = test["y"]

    return X_train, y_train, X_test, y_test


def run_xgboost_experiment(market: str):
    logger.info("=" * 60)
    logger.info("STARTING XGBOOST EXPERIMENT: %s (Horizon 100)", market.upper())
    logger.info("=" * 60)

    X_train, y_train, X_test, y_test = load_data(market)
    logger.info("Train set: %d samples, %d features", len(X_train), X_train.shape[1])
    logger.info("Test set: %d samples", len(X_test))

    model = AstraXGBoost()
    model.fit(X_train, y_train)

    metrics = model.evaluate(
        X_test=X_test,
        y_test=y_test,
        model_name=f"XGBoost_{market.capitalize()}_H100"
    )

    report = format_evaluation_report(metrics)
    print("\n" + report + "\n")

    # Save results JSON
    json_name = f"xgboost_{market}_horizon_100.json"
    save_metrics_to_results(metrics, json_name)

    # Save model
    model_dir = PROJECT_ROOT / "models"
    model_path = model_dir / f"{market}_xgboost.joblib"
    model.save(model_path)

    return metrics


def main():
    auction_metrics = run_xgboost_experiment("auction")
    non_auction_metrics = run_xgboost_experiment("non_auction")

    print("\n" + "=" * 60)
    print("XGBOOST BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Auction     -> Accuracy: {auction_metrics['accuracy']*100:.2f}%, "
          f"Balanced Acc: {auction_metrics['balanced_accuracy']*100:.2f}%, "
          f"Macro F1: {auction_metrics['f1_macro']*100:.2f}%")
    print(f"Non-Auction -> Accuracy: {non_auction_metrics['accuracy']*100:.2f}%, "
          f"Balanced Acc: {non_auction_metrics['balanced_accuracy']*100:.2f}%, "
          f"Macro F1: {non_auction_metrics['f1_macro']*100:.2f}%")
    print("=" * 60)


if __name__ == "__main__":
    main()
