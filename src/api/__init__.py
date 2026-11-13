"""
MIRAI — API Package (M15)
FastAPI backend providing REST and monitoring interfaces.
"""

from src.api.main import app, create_app
from src.api.config import get_api_settings, APISettings

__all__ = ["app", "create_app", "get_api_settings", "APISettings"]
