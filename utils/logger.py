import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

__all__ = ["setup_logger"]

_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def _load_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """Load configuration from JSON once and cache the result."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    path = Path(config_path) if config_path else Path(__file__).resolve().parents[1] / "config.json"
    with path.open("r", encoding="utf-8") as fp:
        _CONFIG_CACHE = json.load(fp)
    return _CONFIG_CACHE


def _get_log_level(level: Optional[Union[int, str]]) -> int:
    """Convert a log level string or int into the logging module constant."""
    if isinstance(level, int):
        return level

    if isinstance(level, str):
        return getattr(logging, level.upper(), logging.INFO)

    return logging.INFO


def setup_logger(
    name: str,
    *,
    config_path: Optional[Union[str, Path]] = None,
    log_dir: Optional[Union[str, Path]] = None,
    level: Optional[Union[int, str]] = None,
) -> logging.Logger:
    """
    Configure and return a logger that writes to both console and rotating daily files.

    Args:
        name: Logger name.
        config_path: Optional custom config path.
        log_dir: Directory to store log files. Defaults to config paths.log_dir.
        level: Desired log level; falls back to config logging.level or INFO.
    """
    config = _load_config(config_path)
    default_log_dir = Path(log_dir or config["paths"]["log_dir"])
    default_log_dir.mkdir(parents=True, exist_ok=True)

    level_name = level or config.get("logging", {}).get("level", "INFO")
    resolved_level = _get_log_level(level_name)

    logger = logging.getLogger(name)
    logger.setLevel(resolved_level)

    if logger.handlers:
        return logger

    log_file = default_log_dir / f"{datetime.now().strftime('%Y%m%d')}.log"
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(resolved_level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(resolved_level)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
