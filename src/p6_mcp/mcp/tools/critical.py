"""§5.6 Critical path and float tools."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.parser.coercion import parse_date
from p6_mcp.services.analysis import critical_path as cp
from p6_mcp.services.analysis.cpm import compare_to_stored, compute_cpm
from p6_mcp.services.query.serialize import activity_to_dict, iso


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register critical path and float tools."""

    @mcp.tool(title="Get critical path", annotations=READ_ONLY)
    @tool_errors
    def get_critical_path(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        method: str = "total_float",
        float_threshold_hours: float | None = None,
        include_completed: bool = False,
        limit: int = 200,
        offset: int = 0,
        verbosity: str = "compact",
    ) -> dict[str, Any]:
        """The critical path by total float, longest path, or both.

        `total_float` selects activities at or below the float threshold (the
        project's own critical_drtn_hr_cnt by default). `longest_path` uses P6's
        driving_path_flag from its last schedule run — this is the better answer
        when calendars differ across the network, because a low-float activity
        on a 7-day calendar is not necessarily driving the finish.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        res = cp.get_critical_path(sch, projects, method, float_threshold_hours, include_completed)
        out: dict[str, Any] = {
            "method": res["method"],
            "float_threshold_hours": res["float_threshold_hours"],
            "project_critical_path_setting": res["project_critical_path_setting"],
        }
        if "total_float_critical" in res:
            acts = res["total_float_critical"]
            out["total_float_critical_count"] = len(acts)
            out["total_float_critical"] = [
                activity_to_dict(sch, a, verbosity)
                for a in acts[offset : offset + ctx.clamp_limit(limit)]
            ]
        if "longest_path" in res:
            acts = res["longest_path"]
            out["longest_path_note"] = res["longest_path_note"]
            out["longest_path_count"] = len(acts)
            out["longest_path"] = [
                activity_to_dict(sch, a, verbosity)
                for a in acts[offset : offset + ctx.clamp_limit(limit)]
            ]
        return ctx.guard(out)

    @mcp.tool(title="Get near critical", annotations=READ_ONLY)
    @tool_errors
    def get_near_critical(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        threshold_days: float = 5.0,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Activities with float above zero but at or below the threshold.

        These are the paths most likely to become critical after the next slip.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        pairs = cp.get_near_critical(sch, projects, threshold_days)
        return ctx.page(
            pairs,
            limit,
            offset,
            render=lambda t: {
                **activity_to_dict(sch, t[0], "compact"),
                "float_days": round(t[1], 1),
            },
            extra={"threshold_days": threshold_days},
        )

    @mcp.tool(title="Get float paths", annotations=READ_ONLY)
    @tool_errors
    def get_float_paths(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        max_paths: int = 5,
    ) -> dict[str, Any]:
        """Ranked parallel paths through the network.

        Uses P6's multiple-float-path fields (float_path / float_path_order)
        when the file was scheduled with that option; otherwise groups by total
        float value and says so in `source`.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        res = cp.get_float_paths(sch, projects, max_paths)
        return ctx.guard(
            {
                "source": res["source"],
                "path_count": len(res["paths"]),
                "paths": {
                    str(k): [activity_to_dict(sch, a, "compact") for a in members]
                    for k, members in res["paths"].items()
                },
            }
        )

    @mcp.tool(title="Get negative float", annotations=READ_ONLY)
    @tool_errors
    def get_negative_float(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Activities with negative total float — work already past the point
        where it can finish on time. DCMA requires zero."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        pairs = cp.get_negative_float(sch, projects)
        return ctx.page(
            pairs,
            limit,
            offset,
            render=lambda t: {
                **activity_to_dict(sch, t[0], "compact"),
                "float_days": round(t[1], 1),
            },
        )

    @mcp.tool(title="Get float distribution", annotations=READ_ONLY)
    @tool_errors
    def get_float_distribution(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        bins: list[float] | None = None,
    ) -> dict[str, Any]:
        """Histogram of total float across incomplete activities, plus min/max/
        median/mean. A schedule with most activities in a single high-float bin
        usually has missing logic rather than genuine slack."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        return ctx.guard(cp.get_float_distribution(sch, projects, bins))

    @mcp.tool(title="Recompute CPM", annotations=READ_ONLY)
    @tool_errors
    def recompute_cpm(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        data_date: str | None = None,
        tolerance_hours: float = 1.0,
    ) -> dict[str, Any]:
        """Run an independent forward/backward pass and compare it to the dates
        stored in the file.

        Use this to validate that the file was actually rescheduled after its
        last edit: large deviations mean the stored dates are stale. Limitations
        vs the P6 engine: retained logic only (no progress override), no
        resource levelling, no ALAP repositioning.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        dd = parse_date(data_date) if data_date else None
        res = compute_cpm(sch, projects, dd)
        comparison = compare_to_stored(sch, res, tolerance_hours)
        return ctx.guard(
            {
                "project_finish": res.project_finish,
                "data_date_used": dd or sch.data_date(projects[0] if projects else None),
                "notes": res.notes,
                "comparison": iso(comparison),
                "limitations": [
                    "retained logic only (progress override not modelled)",
                    "no resource levelling",
                    "ALAP constraints are not repositioned",
                ],
            }
        )

    _ = (
        get_critical_path,
        get_near_critical,
        get_float_paths,
        get_negative_float,
        get_float_distribution,
        recompute_cpm,
    )
