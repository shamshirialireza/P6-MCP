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
from p6_mcp.repository.p6eppm.repository import P6EppmRepository
from p6_mcp.repository.protocol import ScheduleRepository
from p6_mcp.repository.workspace import Workspace

log = get_logger("loader")


@dataclass(slots=True)
class CacheEntry:
    schedule: Schedule
    path: Path | None
    mtime_ns: int
    size: int


class ScheduleLoader:
    """Loads and caches schedules; resolves schedule_id handles."""

    def __init__(self, settings: Settings, workspace: Workspace) -> None:
        self._settings = settings
        self.workspace = workspace
        self._cache: LruCache[str, CacheEntry] = LruCache(settings.cache_size)
        self._handles: dict[str, str] = {}  # schedule_id -> cache key
        self._p6_connections: dict[str, P6EppmRepository] = {}  # connection_name -> repository

    @staticmethod
    def _make_id(path: Path | None, mtime_ns: int, size: int) -> str:
        path_str = str(path) if path is not None else "p6"
        digest = hashlib.sha256(f"{path_str}|{mtime_ns}|{size}".encode()).hexdigest()[:12]
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

        # Handle P6 EPPM connections: p6://connection_name/project_id
        if file_ref.startswith("p6://"):
            return self._load_p6_project(file_ref)

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

    def _load_p6_project(self, file_ref: str) -> Schedule:
        """Load a project from P6 EPPM."""
        # Parse p6://connection_name/project_id[?scope=...]
        if not file_ref.startswith("p6://"):
            raise ValueError(f"Invalid P6 reference: {file_ref}")

        # Remove p6:// prefix
        ref_without_scheme = file_ref[5:]

        # Split connection and project parts
        if "/" not in ref_without_scheme:
            raise ValueError(f"P6 reference must include connection and project: {file_ref}")

        connection_name, project_part = ref_without_scheme.split("/", 1)

        # Parse project ID and optional scope
        project_id_str = project_part.split("?")[0]
        try:
            project_id = int(project_id_str)
        except ValueError:
            raise ValueError(f"Project ID must be an integer: {project_id_str}")

        # Get or create P6 EPPM repository for this connection
        if connection_name not in self._p6_connections:
            # In a real implementation, we'd get connection settings from config/env
            # For now, we'll use placeholder values - these would come from configuration
            self._p6_connections[connection_name] = P6EppmRepository(
                base_url="https://placeholder.example.com:8206/p6ws",
                database="placeholder",
                auth_mode="session",
                username="placeholder",
                password="placeholder",
            )

        repository = self._p6_connections[connection_name]

        # Load the project from P6 EPPM
        try:
            schedule_data = repository.load(project_id)
            # For now, create a basic Schedule - this would be enhanced
            # to properly convert the P6 EPPM data to our Schedule format
            from p6_mcp.parser.reader import XerDocument
            doc = XerDocument(encoding="UTF-8")
            # TODO: Convert schedule_data to proper XerDocument format
            schedule_id = self._make_id(None, 0, 0)  # Placeholder for P6 schedules
            schedule = Schedule(doc, schedule_id)
            # TODO: Populate schedule with actual data from schedule_data
            return schedule
        except Exception as e:
            raise NotFoundError(
                f"Failed to load P6 project {project_id} from connection {connection_name}: {e}",
                hint="Check connection name, project ID, and P6 EPPM availability.",
            )

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
        # Also clear P6 EPPM connections
        self._p6_connections.clear()
        return self._cache.clear()
