"""
ASTRAQUANT X — Structured Logging Utility
Configures consistent, timestamped console and file logging.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from src.utils.config import PROJECT_ROOT, get_config


def get_logger(name: str = "ASTRAQUANT_X", log_file: Optional[Path] = None) -> logging.Logger:
    """
    Creates and configures a standard logger instance.
    Prevents adding duplicate handlers on repeated calls.
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers if already configured
    if logger.handlers:
        return logger

    # Load logging level from config if available
    try:
        cfg = get_config()
        level_str = cfg.get("system.log_level", "INFO").upper()
        if log_file is None:
            log_rel = cfg.get("system.log_file", "logs/astraquant.log")
            log_file = PROJECT_ROOT / log_rel
    except Exception:
        level_str = "INFO"
        if log_file is None:
            log_file = PROJECT_ROOT / "logs" / "astraquant.log"

    level = getattr(logging, level_str, logging.INFO)
    logger.setLevel(level)

    # Standard formatter
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(filename)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    try:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as exc:
        logger.warning("Could not initialize file logging handler: %s", exc)

    return logger
