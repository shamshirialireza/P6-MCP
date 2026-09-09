"""§5.8 Progress and forecast tools."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.parser.coercion import parse_date
from p6_mcp.services.analysis import progress as prog
from p6_mcp.services.analysis.dcma import run_dcma_assessment
from p6_mcp.services.analysis.lookahead import lookahead as lookahead_service


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register progress and forecast tools."""

    @mcp.tool(title="Get progress summary", annotations=READ_ONLY)
    @tool_errors
    def get_progress_summary(
        file_path: str, project_id: int | None = None, project_short_name: str | None = None
    ) -> dict[str, Any]:
        """Overall progress: percent complete measured five ways (activity count,
        duration, units, cost, duration-weighted), activity status counts, cost
        totals, forecast finish, working days remaining, plus BEI and CPLI.

        The five percent-complete measures often disagree; a large gap between
        duration and cost percent usually means front- or back-loaded spending.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        summary = prog.progress_summary(sch, projects)
        dcma = run_dcma_assessment(sch, projects)
        indices = {c["name"]: c["metric"] for c in dcma["checks"] if c["check"] in (13, 14)}
        return ctx.guard(
            {**summary, "CPLI": indices.get("CPLI"), "BEI": indices.get("Baseline Execution Index")}
        )

    @mcp.tool(title="Get behind schedule activities", annotations=READ_ONLY)
    @tool_errors
    def get_behind_schedule_activities(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        days_late_min: float = 0.0,
        compare_to: str = "baseline",
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Activities finishing later than their baseline (or planned) finish,
        ranked by working days late."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        rows = prog.behind_schedule(sch, projects, days_late_min, compare_to)
        return ctx.page(
            rows, limit, offset, extra={"days_late_min": days_late_min, "compare_to": compare_to}
        )

    @mcp.tool(title="Get lookahead", annotations=READ_ONLY)
    @tool_errors
    def get_lookahead(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        window_days: int = 28,
        start_from: str | None = None,
        group_by: str = "wbs",
    ) -> dict[str, Any]:
        """What starts, finishes, or continues in the next N days from the data
        date, grouped by WBS path or an activity code type.

        The classic construction lookahead: 14 / 28 / 42 / 90 day windows.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        anchor = parse_date(start_from) if start_from else None
        return ctx.guard(lookahead_service(sch, projects, window_days, anchor, group_by))

    @mcp.tool(title="Get status update check", annotations=READ_ONLY)
    @tool_errors
    def get_status_update_check(
        file_path: str, project_id: int | None = None, project_short_name: str | None = None
    ) -> dict[str, Any]:
        """Data-date hygiene: work that should have started or finished by the
        data date but hasn't, in-progress activities missing an actual start,
        completed activities missing an actual finish, actuals in the future,
        and remaining-duration anomalies.

        Run this on every schedule update before believing the forecast.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        return ctx.guard(prog.status_update_check(sch, projects))

    @mcp.tool(title="Get activity variances", annotations=READ_ONLY)
    @tool_errors
    def get_activity_variances(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        compare_to: str = "baseline",
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Start and finish variance in working days per activity, versus the
        baseline or the planned dates, sorted by largest finish slip."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        rows = prog.activity_variances(sch, projects, compare_to)
        return ctx.page(rows, limit, offset, extra={"compare_to": compare_to})

    _ = (
        get_progress_summary,
        get_behind_schedule_activities,
        get_lookahead,
        get_status_update_check,
        get_activity_variances,
    )
