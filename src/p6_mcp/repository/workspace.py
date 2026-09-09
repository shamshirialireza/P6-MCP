"""Allowed-directory enforcement and .xer file discovery."""

from __future__ import annotations

import os
from pathlib import Path

from p6_mcp.config import Settings
from p6_mcp.exceptions import FileAccessError, WorkspaceError


class Workspace:
    """Validates every read/write path against the allowed-directory allowlist."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.allowed = settings.resolved_allowed_dirs()
        self.output_dir = settings.resolved_output_dir()

    def _inside_allowed(self, p: Path) -> bool:
        return any(p == d or d in p.parents for d in [*self.allowed, self.output_dir])

    def validate_read(self, path: str) -> Path:
        """Resolve a read path; raises if outside allowed dirs or missing."""
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self.allowed[0] / p
        p = p.resolve()
        if not self._inside_allowed(p):
            raise WorkspaceError(
                f"{path!r} is outside the allowed directories",
                hint=f"Allowed: {[str(d) for d in self.allowed]}. "
                "Start the server with --allowed-dir to add locations.",
            )
        if not p.is_file():
            raise FileAccessError(
                f"{p} does not exist or is not a file",
                hint="Use list_xer_files to discover available schedules.",
            )
        return p

    def validate_write(self, path: str) -> Path:
        """Resolve a write path inside allowed/output dirs (parents may not exist yet)."""
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self.output_dir / p
        p = Path(os.path.normpath(p))
        if not self._inside_allowed(p):
            raise WorkspaceError(
                f"{path!r} is outside the allowed output locations",
                hint=f"Writable roots: {[str(d) for d in [*self.allowed, self.output_dir]]}",
            )
        return p

    def discover(self, directory: str | None = None, recursive: bool = False) -> list[Path]:
        """All .xer files in the given (or every allowed) directory, sorted."""
        roots: list[Path]
        if directory is not None:
            d = Path(directory).expanduser()
            if not d.is_absolute():
                d = self.allowed[0] / d
            d = d.resolve()
            if not self._inside_allowed(d):
                raise WorkspaceError(
                    f"{directory!r} is outside the allowed directories",
                    hint=f"Allowed: {[str(x) for x in self.allowed]}",
                )
            roots = [d]
        else:
            roots = list(self.allowed)
        found: set[Path] = set()
        for root in roots:
            if not root.is_dir():
                continue
            pattern = "**/*" if recursive else "*"
            for p in root.glob(pattern):
                if p.is_file() and p.suffix.lower() == ".xer":
                    found.add(p.resolve())
        return sorted(found)
