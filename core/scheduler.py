"""Simple scheduler that triggers crawl tasks based on configuration."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

try:  # Python 3.9+
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore


@dataclass
class SchedulerConfig:
    enabled: bool = False
    timezone: str = "Asia/Shanghai"
    interval_minutes: Optional[float] = None
    cron: Optional[str] = None
    daily_time: Optional[str] = None  # backward compatibility


class CrawlScheduler:
    """Background scheduler that triggers CrawlController at a fixed time or interval."""

    def __init__(self, controller, config: SchedulerConfig, logger=None) -> None:
        self.controller = controller
        self.config = config
        self.logger = logger
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._tzinfo = self._resolve_timezone(config.timezone)
        self._cron_expr = self._normalize_cron(config)

    def start(self) -> None:
        if not self.config.enabled:
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()
        if self.logger:
            mode = (
                f"every {self.config.interval_minutes} minute(s)"
                if self.config.interval_minutes
                else f"daily at {self.config.daily_time}"
            )
            self.logger.info("Scheduler enabled (%s).", mode)

    def stop(self) -> None:
        if not self._thread:
            return
        self._stop_event.set()
        self._thread.join(timeout=1)

    def _run_forever(self) -> None:
        while not self._stop_event.is_set():
            wait_seconds = self._next_interval_seconds()
            if wait_seconds <= 0:
                wait_seconds = 1
            finished = self._stop_event.wait(wait_seconds)
            if finished:
                break
            self._trigger_crawl()

    def _trigger_crawl(self) -> None:
        started = self.controller.start()
        if self.logger:
            if started:
                self.logger.info("Scheduler triggered a crawl task.")
            else:
                self.logger.info("Scheduler skip: crawl already running.")

    def _next_interval_seconds(self) -> float:
        if self.config.interval_minutes and self.config.interval_minutes > 0:
            return float(self.config.interval_minutes) * 60.0
        if self._cron_expr:
            now = datetime.now(self._tzinfo)
            try:
                cron = SimpleCron(self._cron_expr)
                next_time = cron.next_after(now)
                return (next_time - now).total_seconds()
            except Exception:
                return 3600
        # fallback daily at 07:00 local time
        now = datetime.now(self._tzinfo)
        target = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return (target - now).total_seconds()

    @staticmethod
    def _resolve_timezone(name: str):
        if ZoneInfo:
            try:
                return ZoneInfo(name)
            except Exception:  # pragma: no cover - fallback when tz missing
                pass
        return datetime.now().astimezone().tzinfo or timezone.utc

    def _normalize_cron(self, config: SchedulerConfig) -> Optional[str]:
        if config.cron:
            return config.cron.strip()
        if config.daily_time:
            try:
                hours, minutes = config.daily_time.split(":")
                return f"{int(minutes)} {int(hours)} * * *"
            except Exception:
                return None
        return None


class SimpleCron:
    """Minimal cron parser supporting 5-field expressions (min hour dom mon dow)."""

    def __init__(self, expr: str) -> None:
        parts = expr.split()
        if len(parts) != 5:
            raise ValueError("Cron expression must have 5 fields.")
        self.minutes = self._parse_field(parts[0], 0, 59)
        self.hours = self._parse_field(parts[1], 0, 23)
        self.days = self._parse_field(parts[2], 1, 31)
        self.months = self._parse_field(parts[3], 1, 12)
        self.weekdays = self._parse_field(parts[4], 0, 6, allow_sunday_seven=True)

    def next_after(self, now: datetime) -> datetime:
        candidate = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        for _ in range(525600):  # up to one year
            if self._match(candidate):
                return candidate
            candidate += timedelta(minutes=1)
        raise ValueError("Cron expression did not match within a year.")

    def _match(self, dt: datetime) -> bool:
        if self.minutes is not None and dt.minute not in self.minutes:
            return False
        if self.hours is not None and dt.hour not in self.hours:
            return False
        if self.days is not None and dt.day not in self.days:
            return False
        if self.months is not None and dt.month not in self.months:
            return False
        weekday = dt.weekday()
        if self.weekdays is not None and weekday not in self.weekdays:
            return False
        return True

    def _parse_field(
        self,
        field: str,
        min_value: int,
        max_value: int,
        *,
        allow_sunday_seven: bool = False,
    ) -> Optional[set[int]]:
        field = field.strip()
        if not field or field == "*":
            return None
        values: set[int] = set()
        for part in field.split(","):
            part = part.strip()
            if not part:
                continue
            values.update(
                self._expand_part(part, min_value, max_value, allow_sunday_seven)
            )
        if not values:
            return None
        return values

    def _expand_part(
        self,
        part: str,
        min_value: int,
        max_value: int,
        allow_sunday_seven: bool,
    ) -> set[int]:
        step = 1
        if "/" in part:
            base, step_str = part.split("/", 1)
            step = max(1, int(step_str))
        else:
            base = part

        if base == "*":
            start, end = min_value, max_value
        elif "-" in base:
            start_str, end_str = base.split("-", 1)
            start = int(start_str)
            end = int(end_str)
        else:
            start = end = int(base)

        start = max(min_value, start)
        end = min(max_value, end)

        values = set(range(start, end + 1, step))
        if allow_sunday_seven and 7 in values:
            values.add(0)
            values.discard(7)
        return values
