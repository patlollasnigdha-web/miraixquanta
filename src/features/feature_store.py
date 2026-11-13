"""
MIRAI — Quantitative Feature Store (M02)
Provides standardized persistence, metadata registration, offline feature retrieval,
and online feature serving for all predictive models.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from src.utils.config import get_config, PROJECT_ROOT
from src.utils.logger import get_logger
from src.features.feature_pipeline import FeaturePipeline
from src.data_engineering.data_access import get_data_access_service

logger = get_logger("FeatureStore")


class FeatureStore:
    """
    Centralized quantitative feature store.
    Stores and serves computed features in high-performance Parquet format
    with accompanying JSON metadata schemas.
    """

    def __init__(self, store_dir: Optional[Path] = None):
        if store_dir is None:
            self.store_dir = PROJECT_ROOT / "data" / "processed" / "features"
        else:
            self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.pipeline = FeaturePipeline()
        self.data_service = get_data_access_service()

    def _get_feature_path(self, entity_id: str, feature_group: str) -> Path:
        clean_entity = entity_id.replace("/", "_").replace("\\", "_")
        return self.store_dir / f"{feature_group}_{clean_entity}.parquet"

    def _get_metadata_path(self, entity_id: str, feature_group: str) -> Path:
        clean_entity = entity_id.replace("/", "_").replace("\\", "_")
        return self.store_dir / f"{feature_group}_{clean_entity}_meta.json"

    def save_features(
        self,
        entity_id: str,
        df: pd.DataFrame,
        feature_group: str = "technical",
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Persists a feature DataFrame to Parquet and registers its metadata schema.
        """
        if df.empty:
            raise ValueError(f"Cannot save empty DataFrame for entity '{entity_id}'")

        feat_path = self._get_feature_path(entity_id, feature_group)
        meta_path = self._get_metadata_path(entity_id, feature_group)

        # Write Parquet
        df.to_parquet(feat_path, index=False)

        # Metadata record
        time_col = "timestamp" if "timestamp" in df.columns else None
        time_min = str(df[time_col].min()) if time_col else "N/A"
        time_max = str(df[time_col].max()) if time_col else "N/A"

        meta: Dict[str, Any] = {
            "entity_id": entity_id,
            "feature_group": feature_group,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "dtypes": {c: str(d) for c, d in df.dtypes.items()},
            "time_range": {"min": time_min, "max": time_max},
            "missing_counts": df.isna().sum().to_dict(),
        }
        if extra_metadata:
            meta["extra"] = extra_metadata

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        logger.info(
            "Saved %d features (%d rows) for '%s' [%s] to: %s",
            len(df.columns), len(df), entity_id, feature_group, feat_path
        )
        return feat_path

    def load_features(
        self,
        entity_id: str,
        feature_group: str = "technical",
    ) -> pd.DataFrame:
        """
        Loads precomputed features from the Feature Store.
        """
        feat_path = self._get_feature_path(entity_id, feature_group)
        if not feat_path.exists():
            raise FileNotFoundError(f"Feature set not found at: {feat_path}")

        df = pd.read_parquet(feat_path)
        logger.debug("Loaded features for '%s' [%s]: shape=%s", entity_id, feature_group, df.shape)
        return df

    def has_features(self, entity_id: str, feature_group: str = "technical") -> bool:
        """Checks if a feature set exists in the store."""
        return self._get_feature_path(entity_id, feature_group).exists()

    def get_feature_metadata(self, entity_id: str, feature_group: str = "technical") -> Dict[str, Any]:
        """Retrieves registered JSON metadata for a feature set."""
        meta_path = self._get_metadata_path(entity_id, feature_group)
        if not meta_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {meta_path}")

        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_available_features(self) -> List[Dict[str, Any]]:
        """Lists all registered feature sets in the store."""
        results = []
        for meta_file in sorted(self.store_dir.glob("*_meta.json")):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    results.append(json.load(f))
            except Exception as exc:
                logger.warning("Could not read metadata %s: %s", meta_file.name, exc)
        return results

    def compute_and_store_nifty_daily_features(self) -> pd.DataFrame:
        """
        End-to-end convenience workflow:
        Loads raw NIFTY daily data, executes FeaturePipeline, and persists to store.
        """
        df_raw = self.data_service.get_nifty_daily_index(use_cache=False)
        df_features = self.pipeline.process_ohlcv(df_raw, add_lags=True, dropna=True)
        self.save_features(entity_id="NIFTY50", df=df_features, feature_group="daily_technical")
        return df_features

    def compute_and_store_stock_features(
        self, symbol: str, years: Optional[List[int]] = None
    ) -> pd.DataFrame:
        """
        End-to-end convenience workflow:
        Loads constituent equity daily data for `symbol`, generates features, and stores them.
        """
        df_multi = self.data_service.get_multistock_daily(years=years, symbols=[symbol], use_cache=False)
        if df_multi.empty:
            raise ValueError(f"No stock data found for symbol '{symbol}'")

        df_features = self.pipeline.process_ohlcv(df_multi, add_lags=True, dropna=True)
        self.save_features(entity_id=symbol, df=df_features, feature_group="daily_technical")
        return df_features


# Global singleton factory
_store_instance: Optional[FeatureStore] = None


def get_feature_store(store_dir: Optional[Path] = None) -> FeatureStore:
    """Factory helper to obtain singleton FeatureStore instance."""
    global _store_instance
    if _store_instance is None or store_dir is not None:
        _store_instance = FeatureStore(store_dir=store_dir)
    return _store_instance
