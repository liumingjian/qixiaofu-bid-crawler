import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Optional

from utils.logger import setup_logger


class FileStorage:
    """Utility for resilient JSON persistence with backup support."""

    def __init__(self, *, logger=None) -> None:
        self.logger = logger or setup_logger(self.__class__.__name__)

    def load_json(self, file_path: Path, default: Optional[List[dict]] = None) -> List[dict]:
        """
        Load JSON data from disk.

        Returns default (or empty list) when file is missing or invalid.
        """
        path = Path(file_path)
        if not path.exists():
            return list(default or [])

        try:
            with path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            if isinstance(data, list):
                return data
            self.logger.warning("JSON file %s does not contain a list; returning default.", path)
        except json.JSONDecodeError as exc:
            self.logger.error("JSON parse error for %s: %s", path, exc)
            self._quarantine_corrupt_file(path)
        except OSError as exc:
            self.logger.error("Unable to read %s: %s", path, exc)

        return list(default or [])

    def save_json(self, file_path: Path, data: Iterable[dict]) -> bool:
        """
        Persist JSON data to disk with backup + rollback semantics.

        Returns True on success.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        backup_path = None
        if path.exists():
            backup_path = self.backup_file(path)

        tmp_path = path.with_suffix(path.suffix + ".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as fp:
                json.dump(list(data), fp, ensure_ascii=False, indent=2)
            tmp_path.replace(path)
            return True
        except OSError as exc:
            self.logger.error("Failed to save %s: %s", path, exc)
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            if backup_path:
                self._restore_backup(backup_path, path)
            return False

    def backup_file(self, file_path: Path) -> Optional[Path]:
        """Create a timestamped backup and trim history to the latest 3 copies."""
        path = Path(file_path)
        if not path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_name(f"{path.name}.{timestamp}.bak")
        shutil.copy2(path, backup_path)
        self._cleanup_old_backups(path, keep=3)
        return backup_path

    def _cleanup_old_backups(self, file_path: Path, *, keep: int = 3) -> None:
        pattern = f"{file_path.name}.*.bak"
        backups = sorted(file_path.parent.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[keep:]:
            try:
                old.unlink()
            except OSError as exc:
                self.logger.warning("Failed to remove old backup %s: %s", old, exc)

    def _quarantine_corrupt_file(self, file_path: Path) -> None:
        """Move corrupt files aside to preserve inspection history."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_path = file_path.with_name(f"{file_path.name}.{timestamp}.corrupt")
        try:
            shutil.move(str(file_path), str(quarantine_path))
            self.logger.info("Quarantined corrupt file %s to %s", file_path, quarantine_path)
        except OSError as exc:
            self.logger.error("Failed to quarantine corrupt file %s: %s", file_path, exc)

    def _restore_backup(self, backup_path: Path, target_path: Path) -> None:
        try:
            shutil.copy2(backup_path, target_path)
            self.logger.info("Restored backup %s after failed save.", backup_path)
        except OSError as exc:
            self.logger.error("Failed to restore backup %s: %s", backup_path, exc)
