"""§5.3 WBS tools."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.exceptions import NotFoundError
from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.services.analysis.wbs_rollup import wbs_rollup
from p6_mcp.services.query.serialize import activity_to_dict, iso, wbs_to_dict


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register WBS tools."""

    @mcp.tool(title="Get WBS", annotations=READ_ONLY)
    @tool_errors
    def get_wbs(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        as_tree: bool = False,
        include_rollups: bool = False,
        limit: int = 200,
        offset: int = 0,
        verbosity: str = "standard",
    ) -> dict[str, Any]:
        """The work breakdown structure with computed level and dotted path.

        `as_tree=True` nests children instead of returning a flat list;
        `include_rollups=True` adds dates, counts, and cost per subtree (slower).
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        proj_ids = {p.proj_id for p in projects}
        nodes = [w for w in sch.wbs_nodes if w.proj_id in proj_ids]
        rollups: dict[int, dict[str, Any]] = {}
        if include_rollups:
            rollups = {int(r["wbs_id"]): r for r in wbs_rollup(sch, projects)}

        def render(w: Any) -> dict[str, Any]:
            d = wbs_to_dict(sch, w, verbosity)
            if include_rollups:
                d["rollup"] = rollups.get(w.wbs_id)
            return d

        if as_tree:

            def subtree(parent: int | None) -> list[dict[str, Any]]:
                out = []
                for child in sch.wbs_children.get(parent, []):
                    if child.proj_id not in proj_ids:
                        continue
                    node = render(child)
                    node["children"] = subtree(child.wbs_id)
                    out.append(node)
                return out

            return ctx.guard({"total": len(nodes), "tree": iso(subtree(None))})
        return ctx.page(nodes, limit, offset, render=render)

    @mcp.tool(title="Get WBS detail", annotations=READ_ONLY)
    @tool_errors
    def get_wbs_detail(
        file_path: str,
        wbs_id: int | None = None,
        wbs_short_name: str | None = None,
        include_activities: bool = True,
    ) -> dict[str, Any]:
        """One WBS node with its activities, notes, budgets, and steps."""
        sch = ctx.schedule(file_path)
        node = None
        if wbs_id is not None:
            node = sch.wbs_by_id.get(wbs_id)
        elif wbs_short_name:
            node = next(
                (w for w in sch.wbs_nodes if w.short_name.lower() == wbs_short_name.lower()), None
            )
        if node is None:
            raise NotFoundError(
                "No matching WBS node",
                hint="Call get_wbs to list nodes with their ids and paths.",
            )
        acts = sch.activities_by_wbs.get(node.wbs_id, [])
        out: dict[str, Any] = {
            **wbs_to_dict(sch, node, "full"),
            "children": [
                {"wbs_id": c.wbs_id, "name": c.name, "short_name": c.short_name}
                for c in sch.wbs_children.get(node.wbs_id, [])
            ],
            "notes": [
                d for d in sch.table("WBSMEMO").iter_dicts() if d.get("wbs_id") == node.wbs_id
            ],
            "budgets": [
                d for d in sch.table("WBSBUDG").iter_dicts() if d.get("wbs_id") == node.wbs_id
            ],
            "steps": [
                d for d in sch.table("WBSSTEP").iter_dicts() if d.get("wbs_id") == node.wbs_id
            ],
        }
        if include_activities:
            out["activities"] = [
                activity_to_dict(sch, a, "compact") for a in sorted(acts, key=lambda a: a.code)
            ]
        return ctx.guard(out)

    @mcp.tool(title="Get WBS rollup", annotations=READ_ONLY)
    @tool_errors
    def get_wbs_rollup(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        level: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Per-WBS aggregates: activity counts by status, subtree dates, minimum
        total float, budgeted/actual/remaining cost and units, and percent
        complete.

        Use `level` to stop at a summary depth (1 = project node).
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        rows = wbs_rollup(sch, projects, level)
        return ctx.page(rows, limit, offset)

    @mcp.tool(title="Get WBS budgets", annotations=READ_ONLY)
    @tool_errors
    def get_wbs_budgets(file_path: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """Top-down budget log entries per WBS node (WBSBUDG)."""
        sch = ctx.schedule(file_path)
        rows = [
            {
                **d,
                "wbs_path": sch.wbs_path(int(d["wbs_id"])) if d.get("wbs_id") is not None else None,
            }
            for d in sch.table("WBSBUDG").iter_dicts()
        ]
        return ctx.page(iso(rows), limit, offset)

    @mcp.tool(title="Get WBS notes", annotations=READ_ONLY)
    @tool_errors
    def get_wbs_notes(file_path: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """Notebook entries attached to WBS nodes (WBSMEMO)."""
        sch = ctx.schedule(file_path)
        rows = [
            {
                **d,
                "wbs_path": sch.wbs_path(int(d["wbs_id"])) if d.get("wbs_id") is not None else None,
            }
            for d in sch.table("WBSMEMO").iter_dicts()
        ]
        return ctx.page(iso(rows), limit, offset)

    @mcp.tool(title="Get WBS steps", annotations=READ_ONLY)
    @tool_errors
    def get_wbs_steps(file_path: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """WBS milestones used for weighted percent-complete (WBSSTEP)."""
        sch = ctx.schedule(file_path)
        rows = [
            {
                **d,
                "wbs_path": sch.wbs_path(int(d["wbs_id"])) if d.get("wbs_id") is not None else None,
            }
            for d in sch.table("WBSSTEP").iter_dicts()
        ]
        return ctx.page(iso(rows), limit, offset)

    _ = (get_wbs, get_wbs_detail, get_wbs_rollup, get_wbs_budgets, get_wbs_notes, get_wbs_steps)
