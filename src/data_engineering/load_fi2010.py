
from pathlib import Path
import numpy as np


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "fi2010"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "fi2010"

# FI-2010 dataset structure
NUM_FEATURES = 144

# Five prediction horizons available in FI-2010
HORIZONS = [10, 20, 30, 50, 100]


def load_fi2010_file(file_path, horizon=100):
    """
    Load one FI-2010 text file.

    Original structure:
        144 feature rows
        5 target-label rows

    Returns:
        X: Feature matrix
        y: Target labels
    """

    if horizon not in HORIZONS:
        raise ValueError(
            f"Invalid horizon. Choose from {HORIZONS}"
        )

    file_path = Path(file_path)

    print(f"\nLoading: {file_path.name}")

    data = np.loadtxt(file_path, dtype=np.float32)

    print("Original shape:", data.shape)

    if data.ndim != 2:
        raise ValueError("Dataset must be a 2D matrix.")

    if data.shape[0] != 149:
        raise ValueError(
            f"Expected 149 rows, found {data.shape[0]}"
        )

    # First 144 rows are input features
    X = data[:NUM_FEATURES, :].T.copy()

    # Last five rows contain labels for five horizons
    label_row = NUM_FEATURES + HORIZONS.index(horizon)

    y = data[label_row, :].copy()

    # Data validation
    if not np.isfinite(X).all():
        raise ValueError("Features contain NaN or infinity.")

    if not np.isfinite(y).all():
        raise ValueError("Labels contain NaN or infinity.")

    if not np.allclose(y, np.round(y)):
        raise ValueError("Target labels are not integers.")

    y = y.astype(np.int8)

    print("Features shape:", X.shape)
    print("Target shape:", y.shape)
    print("Unique labels:", np.unique(y))

    return X, y


def process_dataset(market, split, horizon=100):
    """
    Load, validate and save one market/split combination.
    """

    file_prefix = "Auction" if market == "auction" else "NoAuction"
    split_prefix = "Train" if split == "training" else "Test"

    input_dir = RAW_DIR / market / split

    file_path = input_dir / (
        f"{split_prefix}_Dst_{file_prefix}_ZScore_CF_1.txt"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {file_path}"
        )

    X, y = load_fi2010_file(file_path, horizon)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    output_path = PROCESSED_DIR / (
        f"{market}_{split}_horizon_{horizon}.npz"
    )

    np.savez_compressed(
        output_path,
        X=X,
        y=y
    )

    print("Saved:", output_path)
    print("")


def main():
    print("=" * 55)
    print("ASTRAQUANT X - FI-2010 DATA LOADER")
    print("=" * 55)

    horizon = 100

    datasets = [
        ("auction", "training"),
        ("auction", "testing"),
        ("non_auction", "training"),
        ("non_auction", "testing")
    ]

    for market, split in datasets:
        process_dataset(market, split, horizon)

    print("=" * 55)
    print("FI-2010 PROCESSING COMPLETED")
    print("=" * 55)


if __name__ == "__main__":
    main()
