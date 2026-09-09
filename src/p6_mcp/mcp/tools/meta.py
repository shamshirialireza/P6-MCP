"""§5.16 Meta and help tools."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp import __version__
from p6_mcp.domain.base import ENUMS
from p6_mcp.exceptions import NotFoundError
from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.data_dictionary import dictionary, explain_field
from p6_mcp.mcp.tools.files import READ_ONLY

#: Human grouping used by list_capabilities.
GROUP_TITLES: dict[str, str] = {
    "files": "File & workspace",
    "projects": "Projects & EPS",
    "wbs": "WBS",
    "activities": "Activities",
    "logic": "Relationships & logic",
    "critical": "Critical path & float",
    "quality": "Schedule quality (DCMA)",
    "progress": "Progress & forecast",
    "resources": "Resources, roles & accounts",
    "cost": "Cost & earned value",
    "calendars": "Calendars",
    "compare": "Baselines & comparison",
    "reports": "Reports",
    "exports": "Export",
    "mutations": "Mutation (write-back)",
    "meta": "Meta & help",
}


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register meta tools."""

    @mcp.tool(title="List capabilities", annotations=READ_ONLY)
    @tool_errors
    async def list_capabilities() -> dict[str, Any]:
        """Every tool this server exposes, grouped by concern, with a one-line
        description each — plus the server version and current limits.

        Call this when you want an overview before choosing a tool.
        """
        tools = await mcp.list_tools()
        by_name = {t.name: (t.description or "").strip().split("\n")[0] for t in tools}
        groups: dict[str, list[dict[str, str]]] = {}
        for module_name, title in GROUP_TITLES.items():
            names = _names_for(module_name)
            entries = [{"tool": n, "summary": by_name[n]} for n in names if n in by_name]
            if entries:
                groups[title] = entries
        placed = {e["tool"] for entries in groups.values() for e in entries}
        leftover = [{"tool": n, "summary": s} for n, s in by_name.items() if n not in placed]
        if leftover:
            groups["Other"] = leftover
        return ctx.guard(
            {
                "server": "p6-mcp",
                "version": __version__,
                "tool_count": len(tools),
                "groups": groups,
                "limits": {
                    "default_page_size": ctx.settings.default_limit,
                    "max_page_size": ctx.settings.max_limit,
                    "max_output_bytes": ctx.settings.max_output_bytes,
                },
                "mutation_enabled": ctx.settings.mutation_allowed(),
                "allowed_directories": [str(d) for d in ctx.workspace.allowed],
            }
        )

    @mcp.tool(name="explain_field", title="Explain field", annotations=READ_ONLY)
    @tool_errors
    def explain_field_tool(table: str, field: str) -> dict[str, Any]:
        """Explain any P6 table column in plain language, with its units and
        enum values.

        Use this whenever a raw field name is unclear — e.g.
        explain_field("TASK", "total_float_hr_cnt").
        """
        return ctx.guard(explain_field(table, field))

    @mcp.tool(title="Get enum values", annotations=READ_ONLY)
    @tool_errors
    def get_enum_values(enum_name: str | None = None) -> dict[str, Any]:
        """P6 enum codes with human labels.

        Without an argument, returns every enum. Known names: task_type,
        status_code, cstr_type, pred_type, rsrc_type, duration_type,
        complete_pct_type, critical_path_type, clndr_type, wbs_status,
        ev_compute_type, udf_data_type.
        """
        if enum_name is None:
            return ctx.guard({"enums": ENUMS})
        vocab = ENUMS.get(enum_name)
        if vocab is None:
            raise NotFoundError(
                f"Unknown enum {enum_name!r}",
                hint=f"Known enums: {sorted(ENUMS)}",
            )
        return ctx.guard({"enum": enum_name, "values": vocab})

    @mcp.tool(title="Get data dictionary", annotations=READ_ONLY)
    @tool_errors
    def get_data_dictionary() -> dict[str, Any]:
        """The full P6 data dictionary: table purposes, field meanings, enum
        vocabularies, and the column-suffix naming conventions."""
        return ctx.guard(dictionary())

    _ = (list_capabilities, explain_field_tool, get_enum_values, get_data_dictionary)


def _names_for(module_name: str) -> list[str]:
    """Tool names declared by a tool module, in source order."""
    import importlib
    import inspect
    import re

    module = importlib.import_module(f"p6_mcp.mcp.tools.{module_name}")
    source = inspect.getsource(module)
    names: list[str] = []
    for match in re.finditer(
        r"@mcp\.tool\((?P<args>[^)]*)\)\s*(?:@\w+\s*)*(?:async\s+)?def\s+(?P<fn>\w+)",
        source,
        re.S,
    ):
        explicit = re.search(r'name="([^"]+)"', match.group("args"))
        names.append(explicit.group(1) if explicit else match.group("fn"))
    return names
