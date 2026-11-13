
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "fi2010"

FILES = [
    "auction_training_horizon_100.npz",
    "auction_testing_horizon_100.npz",
    "non_auction_training_horizon_100.npz",
    "non_auction_testing_horizon_100.npz",
]

LABEL_NAMES = {
    1: "Class 1",
    2: "Class 2",
    3: "Class 3",
}


def inspect_file(filename):
    path = DATA_DIR / filename

    print("\n" + "=" * 60)
    print(filename)
    print("=" * 60)

    with np.load(path) as data:
        X = data["X"]
        y = data["y"]

        print("Feature shape:", X.shape)
        print("Target shape:", y.shape)

        print("Missing values:", np.isnan(X).sum())
        print("Infinite values:", np.isinf(X).sum())

        print("\nClass distribution:")

        labels, counts = np.unique(
            y, return_counts=True
        )

        for label, count in zip(labels, counts):
            percentage = count / len(y) * 100

            print(
                f"{LABEL_NAMES.get(int(label), label)}: "
                f"{count:,} ({percentage:.2f}%)"
            )

        print("\nFeature statistics:")
        print("Minimum:", np.min(X))
        print("Maximum:", np.max(X))
        print("Mean:", np.mean(X))
        print("Standard deviation:", np.std(X))


def main():
    print("ASTRAQUANT X - DATA QUALITY INSPECTION")

    for filename in FILES:
        inspect_file(filename)

    print("\nDATA QUALITY INSPECTION COMPLETED")


if __name__ == "__main__":
    main()
