from __future__ import annotations

import json
import sys
from copy import deepcopy
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from core.default_config import default_config_copy


def load_config(base_path: str | Path, *, custom_name: str = "custom.json") -> dict[str, Any]:
    """
    Load configuration with the following precedence:
    1. Built-in defaults (never exposed to users).
    2. Optional base config file (config.json) when present.
    3. Optional custom overrides (custom.json) placed next to the binary/script.
    """
    config = default_config_copy()

    env_json = os.environ.get("QIXIAOFU_CONFIG_JSON")
    env_path = os.environ.get("QIXIAOFU_CONFIG_PATH")
    if env_json:
        config = _deep_merge(config, json.loads(env_json))
    elif env_path:
        path = Path(env_path)
        if not path.exists():
            raise FileNotFoundError(f"Environment config path '{env_path}' not found.")
        with path.open("r", encoding="utf-8") as fp:
            config = _deep_merge(config, json.load(fp))

    base_file = _find_file(Path(base_path))
    base_dir = None
    if base_file:
        with base_file.open("r", encoding="utf-8") as fp:
            config = _deep_merge(config, json.load(fp))
        base_dir = base_file.parent

    custom_file = _find_file(Path(custom_name), extra_dirs=_candidate_dirs(base_dir))
    if custom_file:
        with custom_file.open("r", encoding="utf-8") as fp:
            config = _deep_merge(config, json.load(fp))
    return config


def _candidate_dirs(base_dir: Optional[Path]) -> list[Path]:
    dirs = []
    if base_dir:
        dirs.append(base_dir)
    exe_dir = Path(sys.argv[0]).resolve().parent
    dirs.append(exe_dir)
    dirs.append(Path.cwd())
    return dirs


def _find_file(path: Path, *, extra_dirs: Iterable[Path] = ()) -> Optional[Path]:
    candidates: list[Path] = []
    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.append(path)

    for directory in extra_dirs:
        candidates.append(directory / path.name)

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / path.name)

    exe_dir = Path(sys.argv[0]).resolve().parent
    candidates.append(exe_dir / path.name)
    candidates.append(Path.cwd() / path.name)

    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _deep_merge(base: Mapping[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overrides.items():
        if (
            key in merged
            and isinstance(merged[key], Mapping)
            and isinstance(value, Mapping)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged
