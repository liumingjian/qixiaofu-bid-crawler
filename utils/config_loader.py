from __future__ import annotations

import json
import sys
from copy import deepcopy
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from core.default_config import default_config_copy
from utils.config_migrator import migrate_to_v2


def load_config(base_path: str | Path, *, custom_name: str = "custom.yml") -> dict[str, Any]:
    """
    Load configuration with the following precedence:
    1. Built-in defaults (never exposed to users).
    2. Optional base config file (config.yml/config.json) when present.
    3. Optional custom overrides (custom.yml/custom.json) placed next to the binary/script.
    
    Auto-migrates old single-account format to new multi-account format.
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
        config = _deep_merge(config, _load_structured_file(path))

    base_file = _find_file(Path(base_path))
    base_dir = None
    if base_file:
        config = _deep_merge(config, _load_structured_file(base_file))
        base_dir = base_file.parent

    custom_file = _find_file(Path(custom_name), extra_dirs=_candidate_dirs(base_dir))
    if custom_file:
        config = _deep_merge(config, _load_structured_file(custom_file))
    
    config = migrate_to_v2(config)
    
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
    candidates.extend(_alternate_paths(path))

    for directory in extra_dirs:
        candidates.append(directory / path.name)
        candidates.extend(_alternate_paths(directory / path.name))

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / path.name)
        candidates.extend(_alternate_paths(Path(meipass) / path.name))

    exe_dir = Path(sys.argv[0]).resolve().parent
    candidates.append(exe_dir / path.name)
    candidates.append(Path.cwd() / path.name)
    candidates.extend(_alternate_paths(exe_dir / path.name))
    candidates.extend(_alternate_paths(Path.cwd() / path.name))

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


def _load_structured_file(path: Path) -> Mapping[str, Any]:
    suffix = path.suffix.lower()
    with path.open("r", encoding="utf-8") as fp:
        if suffix in {".yml", ".yaml"}:
            data = _yaml_safe_load(fp.read()) or {}
        elif suffix == ".json":
            data = json.load(fp)
        else:
            raise ValueError(f"Unsupported config format: {path}")
    if not isinstance(data, Mapping):
        raise ValueError(f"Configuration file {path} must contain a mapping.")
    return data


def dump_config(path: Path, data: Mapping[str, Any]) -> None:
    suffix = path.suffix.lower()
    path.parent.mkdir(parents=True, exist_ok=True)
    if suffix in {".yml", ".yaml"}:
        _dump_yaml(path, data)
    elif suffix == ".json":
        with path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
    else:
        raise ValueError(f"Unsupported config format: {path}")


def _alternate_paths(path: Path) -> list[Path]:
    suffix = path.suffix.lower()
    base = path.with_suffix("")
    alternates: list[Path] = []
    if suffix == ".json":
        alternates.append(base.with_suffix(".yml"))
        alternates.append(base.with_suffix(".yaml"))
    elif suffix in {".yml", ".yaml"}:
        alternates.append(base.with_suffix(".json"))
    return alternates


def read_config_file(path: Path) -> Mapping[str, Any]:
    return _load_structured_file(path)


class _YamlNode:
    def __init__(
        self,
        indent: int,
        value: Any,
        parent: Optional["_YamlNode"] = None,
        key: Optional[str] = None,
        can_convert: bool = False,
    ) -> None:
        self.indent = indent
        self.value = value
        self.parent = parent
        self.key = key
        self.can_convert = can_convert


def _yaml_safe_load(text: str) -> Mapping[str, Any]:
    root = _YamlNode(-1, {}, None, None, False)
    stack = [root]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        stripped = line.lstrip()
        if not stripped:
            continue
        indent = len(line) - len(stripped)
        while indent <= stack[-1].indent:
            stack.pop()
        node = stack[-1]
        if stripped.startswith("- "):
            _ensure_list(node)
            content = stripped[2:].strip()
            if content:
                node.value.append(_parse_scalar(content))
            else:
                new_dict: dict[str, Any] = {}
                node.value.append(new_dict)
                stack.append(
                    _YamlNode(indent, new_dict, parent=node, key=None, can_convert=True)
                )
            continue
        if ":" in stripped:
            key, value_text = stripped.split(":", 1)
            key = key.strip()
            value_text = value_text.strip()
            if value_text:
                node.value[key] = _parse_scalar(value_text)
            else:
                new_dict = {}
                node.value[key] = new_dict
                stack.append(
                    _YamlNode(indent, new_dict, parent=node, key=key, can_convert=True)
                )
            continue
        raise ValueError(f"Unsupported YAML line: {raw_line!r}")
    return root.value


def _ensure_list(node: _YamlNode) -> None:
    if isinstance(node.value, list):
        return
    if node.can_convert and isinstance(node.value, dict) and not node.value:
        new_list: list[Any] = []
        node.value = new_list
        node.can_convert = False
        if node.parent and node.key is not None:
            node.parent.value[node.key] = new_list
        return
    raise ValueError("Invalid YAML structure: expected list")


def _parse_scalar(value: str) -> Any:
    if not value:
        return ""
    if value[0] in "\"'":
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None
    if value[0] in "[{":
        try:
            return json.loads(value)
        except Exception:
            pass
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    return value


def _dump_yaml(path: Path, data: Mapping[str, Any]) -> None:
    lines = _yaml_dump_lines(data, indent=0)
    with path.open("w", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")


def _yaml_dump_lines(value: Any, indent: int) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent
    if isinstance(value, Mapping):
        for key, val in value.items():
            if isinstance(val, (Mapping, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(_yaml_dump_lines(val, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_format_scalar(val)}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (Mapping, list)):
                lines.append(f"{prefix}-")
                lines.extend(_yaml_dump_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}- {_format_scalar(item)}")
    else:
        lines.append(f"{prefix}{_format_scalar(value)}")
    return lines


def _format_scalar(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    text = str(value)
    if not text or any(ch in text for ch in ":#{}[]") or text.strip() != text or " " in text:
        return '"' + text.replace('"', '\\"') + '"'
    return text
