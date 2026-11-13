"""
ASTRAQUANT X — Configuration Manager
Provides centralized, validated configuration loading across all modules.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml

# Determine Project Root (two levels up from this file: src/utils/config.py -> root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "config.yaml"


class ConfigManager:
    """Singleton-style or instance-based configuration manager."""

    _instance: Optional["ConfigManager"] = None
    _config: Dict[str, Any] = {}

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load YAML configuration from file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            raw_cfg = yaml.safe_load(f) or {}

        return raw_cfg

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a configuration value using dot notation (e.g. 'paths.raw_fi2010_dir').
        """
        tokens = key.split(".")
        current = self.config
        for token in tokens:
            if isinstance(current, dict) and token in current:
                current = current[token]
            else:
                return default
        return current

    def get_path(self, key: str, default: Optional[str] = None) -> Path:
        """
        Retrieve a path value and resolve it relative to PROJECT_ROOT.
        """
        raw_val = self.get(key, default)
        if raw_val is None:
            raise KeyError(f"Path key '{key}' not found in configuration.")
        return (PROJECT_ROOT / raw_val).resolve()

    def __getitem__(self, item: str) -> Any:
        return self.config[item]


def get_config(config_path: Optional[Path] = None) -> ConfigManager:
    """Factory helper to obtain a ConfigManager instance."""
    return ConfigManager(config_path)
