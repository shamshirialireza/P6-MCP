"""§5.12 Baseline comparison, XER diff, and trend tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.services.analysis.baseline_compare import compare_to_baseline as bl_service
from p6_mcp.services.analysis.schedule_diff import diff_schedules as diff_service
from p6_mcp.services.analysis.schedule_diff import schedule_trend
from p6_mcp.services.query.serialize import iso


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register comparison tools."""

    @mcp.tool(title="Compare to baseline", annotations=READ_ONLY)
    @tool_errors
    def compare_to_baseline(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        baseline_project_id: int | None = None,
        baseline_file_path: str | None = None,
        tolerance_days: float = 0.0,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Compare the current schedule against its baseline.

        The baseline can be a project inside the same file (the default — it
        uses the linked baseline) or a separate XER via `baseline_file_path`.
        Returns per-activity start/finish/duration variance in working days,
        added and deleted activities, logic and assignment changes, milestone
        variance, and critical-path movement.

        `tolerance_days` suppresses variances smaller than the given threshold.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        bl_sch = ctx.schedule(baseline_file_path) if baseline_file_path else None
        res = bl_service(sch, projects, baseline_project_id, bl_sch, tolerance_days)
        variances = res.pop("variances")
        return ctx.page(iso(variances), limit, offset, extra=iso(res))

    @mcp.tool(title="Diff schedules", annotations=READ_ONLY)
    @tool_errors
    def diff_schedules(
        current_file_path: str,
        previous_file_path: str,
        project_match: str = "short_name",
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Compare two XER files — typically this month's update against last
        month's — and report everything that changed.

        Covers activities added, deleted, renamed, re-statused, re-dated,
        re-durationed, and progressed; relationships added or removed; cost
        changes; calendar changes; and the movement of the project finish date.

        `project_match` pairs projects by short_name (default), id, or guid.
        """
        cur = ctx.schedule(current_file_path)
        prev = ctx.schedule(previous_file_path)
        res = diff_service(cur, prev, project_match)
        changes = res.pop("changes")
        return ctx.page(iso(changes), limit, offset, extra=iso(res))

    @mcp.tool(title="Get schedule trend", annotations=READ_ONLY)
    @tool_errors
    def get_schedule_trend(
        file_paths: list[str], project_short_name: str | None = None
    ) -> dict[str, Any]:
        """Track key metrics across a series of schedule updates.

        Pass the files in chronological order; returns data date, forecast
        finish, percent complete, critical activity count, CPI, and SPI for each
        so you can see whether the finish is drifting and whether performance is
        improving or decaying.
        """
        pairs = [(Path(path).name, ctx.schedule(path)) for path in file_paths]
        return ctx.guard(schedule_trend(pairs, project_short_name))

    _ = (compare_to_baseline, diff_schedules, get_schedule_trend)
