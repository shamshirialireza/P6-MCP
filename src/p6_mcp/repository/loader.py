"""ScheduleLoader: path → cached, indexed Schedule.

Cache keys include mtime + size, so an updated file on disk is transparently
re-parsed. ``open_schedule`` handles ("sched-xxxxxxxx") map to cached entries
and remain valid until closed, evicted, or the file changes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from p6_mcp.config import Settings
from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import NotFoundError
from p6_mcp.logging import get_logger
from p6_mcp.parser.reader import XerReader
from p6_mcp.repository.cache import LruCache
from p6_mcp.repository.workspace import Workspace

log = get_logger("loader")


@dataclass(slots=True)
class CacheEntry:
    schedule: Schedule
    path: Path
    mtime_ns: int
    size: int


class ScheduleLoader:
    """Loads and caches schedules; resolves schedule_id handles."""

    def __init__(self, settings: Settings, workspace: Workspace) -> None:
        self._settings = settings
        self.workspace = workspace
        self._cache: LruCache[str, CacheEntry] = LruCache(settings.cache_size)
        self._handles: dict[str, str] = {}  # schedule_id -> cache key

    @staticmethod
    def _make_id(path: Path, mtime_ns: int, size: int) -> str:
        digest = hashlib.sha256(f"{path}|{mtime_ns}|{size}".encode()).hexdigest()[:12]
        return f"sched-{digest}"

    def load(self, file_ref: str, encoding: str | None = None) -> Schedule:
        """Load by file path or a schedule_id returned by open_schedule."""
        if file_ref.startswith("sched-"):
            key = self._handles.get(file_ref)
            entry = self._cache.get(key) if key else None
            if entry is None:
                raise NotFoundError(
                    f"Unknown or expired schedule_id {file_ref!r}",
                    hint="Call open_schedule again to obtain a fresh handle.",
                )
            return entry.schedule
        path = self.workspace.validate_read(file_ref)
        stat = path.stat()
        key = str(path)
        entry = self._cache.get(key)
        if entry is not None and entry.mtime_ns == stat.st_mtime_ns and entry.size == stat.st_size:
            return entry.schedule
        enc = encoding or self._settings.default_encoding
        doc = XerReader(enc).read_path(path)
        schedule_id = self._make_id(path, stat.st_mtime_ns, stat.st_size)
        schedule = Schedule(doc, schedule_id)
        self._cache.put(key, CacheEntry(schedule, path, stat.st_mtime_ns, stat.st_size))
        self._handles[schedule_id] = key
        log.info(
            "parsed %s (%d tables, %d warnings) as %s",
            path.name,
            len(doc.tables),
            len(doc.warnings),
            schedule_id,
        )
        return schedule

    def open_schedules(self) -> list[Schedule]:
        """Schedules currently cached (for resources/list)."""
        return [e.schedule for e in self._cache.values()]

    def close(self, schedule_id: str) -> bool:
        key = self._handles.pop(schedule_id, None)
        if key is None:
            return False
        return self._cache.pop(key) is not None

    def clear(self) -> int:
        self._handles.clear()
        return self._cache.clear()
