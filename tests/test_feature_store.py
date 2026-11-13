"""
MIRAI — Unit Tests for Feature Store (Batch 1 - M02)
"""

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.features.feature_store import FeatureStore, get_feature_store


def test_feature_store_save_load_lifecycle():
    """Verify FeatureStore Parquet persistence and metadata registry."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = FeatureStore(store_dir=Path(tmpdir))

        dates = pd.date_range("2024-01-01", periods=10)
        df_feat = pd.DataFrame({
            "timestamp": dates,
            "rsi": np.random.uniform(30, 70, 10),
            "macd": np.random.randn(10),
            "vol": np.random.uniform(0.1, 0.3, 10),
        })

        feat_path = store.save_features(entity_id="TEST_STOCK", df=df_feat, feature_group="tech")
        assert feat_path.exists()
        assert store.has_features("TEST_STOCK", feature_group="tech")

        # Load back
        df_loaded = store.load_features("TEST_STOCK", feature_group="tech")
        assert len(df_loaded) == 10
        assert "rsi" in df_loaded.columns
        assert np.allclose(df_feat["rsi"], df_loaded["rsi"])

        # Check metadata
        meta = store.get_feature_metadata("TEST_STOCK", feature_group="tech")
        assert meta["entity_id"] == "TEST_STOCK"
        assert meta["row_count"] == 10
        assert meta["column_count"] == 4
        assert "rsi" in meta["columns"]

        # List available
        avail = store.list_available_features()
        assert len(avail) == 1
        assert avail[0]["entity_id"] == "TEST_STOCK"


def test_feature_store_end_to_end_nifty():
    """Verify compute_and_store_nifty_daily_features generates and stores features."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = FeatureStore(store_dir=Path(tmpdir))
        df_features = store.compute_and_store_nifty_daily_features()

        assert len(df_features) > 100
        assert "rsi_14" in df_features.columns
        assert "bb_upper" in df_features.columns
        assert "vol_realized" in df_features.columns
        assert store.has_features(entity_id="NIFTY50", feature_group="daily_technical")
