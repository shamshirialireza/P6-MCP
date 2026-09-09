"""Tool groups. Each module exposes ``register(mcp, ctx)``.

Modules are imported on demand in :func:`register_all` so that importing a
single tool module never pulls in the whole tree.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from mcp.server.mcpserver import MCPServer

    from p6_mcp.mcp.context import AppContext

#: Registration order; also the order tools appear in tools/list.
GROUPS: tuple[str, ...] = (
    "files",
    "projects",
    "wbs",
    "activities",
    "logic",
    "critical",
    "quality",
    "progress",
    "resources",
    "cost",
    "calendars",
    "compare",
    "reports",
    "exports",
    "mutations",
    "meta",
)


def register_all(mcp: MCPServer, ctx: AppContext) -> None:
    """Register every tool group on the server."""
    for name in GROUPS:
        module = importlib.import_module(f"p6_mcp.mcp.tools.{name}")
        module.register(mcp, ctx)
