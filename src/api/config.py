"""
MIRAI — API Settings & Configuration (M15)
Provides runtime configuration for FastAPI host, port, CORS, and endpoint paths.
"""

import os
from typing import List
from pydantic import BaseModel, Field

from src.utils.config import get_config


class APISettings(BaseModel):
    """FastAPI application settings."""
    title: str = "MIRAI Quantitative Trading API"
    description: str = (
        "AI-Driven Adaptive Quantitative Trading and Intelligent Execution Framework. "
        "REST API serving real-time intelligence, predictions, decisions, risk controls, "
        "and paper trading simulation."
    )
    version: str = "1.0.0"
    host: str = Field(default_factory=lambda: os.getenv("MIRAI_API_HOST", "0.0.0.0"))
    port: int = Field(default_factory=lambda: int(os.getenv("MIRAI_API_PORT", 8000)))
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("MIRAI_CORS_ORIGINS", "*").split(",")
        ]
    )
    enable_docs: bool = True
    prefix: str = "/api/v1"


def get_api_settings() -> APISettings:
    """Loads API configuration from central config and environment overrides."""
    cfg = get_config()
    api_cfg = cfg.get("api", {})

    return APISettings(
        title=api_cfg.get("title", "MIRAI Quantitative Trading API"),
        version=api_cfg.get("version", "1.0.0"),
        host=os.getenv("MIRAI_API_HOST", api_cfg.get("host", "0.0.0.0")),
        port=int(os.getenv("MIRAI_API_PORT", api_cfg.get("port", 8000))),
        cors_origins=[
            o.strip()
            for o in os.getenv("MIRAI_CORS_ORIGINS", ",".join(api_cfg.get("cors_origins", ["*"]))).split(",")
        ],
        enable_docs=api_cfg.get("enable_docs", True),
    )
