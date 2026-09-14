"""Server construction: build an MCPServer with every tool, resource, and prompt.

Note (ADR-0006): p6-mcp targets the mcp 2.x SDK, where FastMCP is named
MCPServer. The decorator surface, annotations, and the three transports are the
same; 1.x is not supported.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from p6_mcp import __version__
from p6_mcp.config import Settings
from p6_mcp.logging import get_logger
from p6_mcp.mcp.context import AppContext
from p6_mcp.mcp.prompts import register_prompts
from p6_mcp.mcp.resources import register_resources
from p6_mcp.mcp.tools import register_all

log = get_logger("server")

INSTRUCTIONS = """\
p6-mcp reads, analyzes, compares, edits, and exports Primavera P6 .xer schedule
files.

Getting started: call `list_xer_files` to find schedules, then `open_schedule`
to parse one and get a `schedule_id` you can pass as `file_path` to every other
tool (faster than re-parsing). `list_capabilities` lists every tool by group.

Conventions worth knowing:
- Durations and float are returned in hours AND calendar-aware days, using each
  activity's own calendar. Never assume 8 hours per day.
- The data date (last_recalc_date) separates actuals from forecast; most
  progress and earned-value figures depend on it.
- A file may contain several projects plus baselines (project_flag='N'). Tools
  default to all non-baseline projects; pass project_id or project_short_name to
  narrow.
- List tools paginate: `{total, offset, limit, returned, next_offset, items}`.
  Large results are truncated to a byte budget and say so via `truncated`.
- Write-back tools require `confirm=true` and write to a NEW file unless
  `overwrite=true`.
"""


def build_server(settings: Settings | None = None) -> MCPServer:
    """Construct a fully registered MCP server."""
    settings = settings or Settings()
    ctx = AppContext(settings)
    mcp = MCPServer(
        name="p6-mcp",
        title="Primavera P6 XER",
        version=__version__,
        instructions=INSTRUCTIONS,
        website_url="https://github.com/shamshirialireza/P6-MCP",
        log_level=settings.log_level.upper(),  # type: ignore[arg-type]
    )
    register_all(mcp, ctx)
    register_resources(mcp, ctx)
    register_prompts(mcp, ctx)
    log.info(
        "p6-mcp %s ready (mutation=%s, allowed=%s)",
        __version__,
        settings.mutation_allowed(),
        [str(d) for d in ctx.workspace.allowed],
    )
    return mcp
