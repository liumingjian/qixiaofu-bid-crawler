#!/usr/bin/env python3
"""
Helper script to bundle the crawler into a standalone binary via PyInstaller.

Usage:
    python scripts/package.py
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ENTRY = PROJECT_ROOT / "app.py"


def detect_platform() -> str:
    name = platform.system().lower()
    if "windows" in name:
        return "windows"
    if "darwin" in name:
        return "macos"
    if "linux" in name:
        return "linux"
    return name or "unknown"


def data_arg(source: Path, target: str) -> str:
    """
    PyInstaller uses different separators for data mappings on Windows vs others.
    """
    separator = ";" if platform.system().lower().startswith("win") else ":"
    return f"{source}{separator}{target}"


def ensure_pyinstaller() -> None:
    if shutil.which("pyinstaller"):
        return
    print("PyInstaller not found. Please install via `pip install pyinstaller`.", file=sys.stderr)
    sys.exit(1)


def build() -> None:
    ensure_pyinstaller()
    os_slug = detect_platform()
    binary_name = f"qixiaofu-bid-crawler-{os_slug}"
    dist_dir = PROJECT_ROOT / "dist"

    cmd = [
        "pyinstaller",
        "--onefile",
        "--name",
        binary_name,
        "--add-data",
        data_arg(PROJECT_ROOT / "web" / "templates", "web/templates"),
        "--add-data",
        data_arg(PROJECT_ROOT / "web" / "static", "web/static"),
        str(APP_ENTRY),
    ]

    print("Running:", " ".join(str(part) for part in cmd))
    subprocess.run(cmd, check=True, cwd=PROJECT_ROOT)

    print("\nBundle complete!")
    print(f"Output directory: {dist_dir}")
    print("Place optional `custom.json` and Chromedriver next to the executable if needed.")


if __name__ == "__main__":
    build()
