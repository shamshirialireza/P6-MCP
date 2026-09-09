"""§5.7 Schedule quality tools: DCMA 14-point and health scoring."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.services.analysis.dcma import run_dcma_assessment as dcma_service
from p6_mcp.services.analysis.health_score import check_schedule_quality, health_score
from p6_mcp.services.analysis.progress import invalid_dates
from p6_mcp.services.analysis.thresholds import DcmaThresholds


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register schedule-quality tools."""

    @mcp.tool(title="Run DCMA assessment", annotations=READ_ONLY)
    @tool_errors
    def run_dcma_assessment(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        missing_logic_pct_max: float = 5.0,
        leads_max: int = 0,
        lags_pct_max: float = 5.0,
        fs_pct_min: float = 90.0,
        hard_constraints_pct_max: float = 5.0,
        high_float_days: float = 44.0,
        high_float_pct_max: float = 5.0,
        negative_float_max: int = 0,
        high_duration_days: float = 44.0,
        high_duration_pct_max: float = 5.0,
        invalid_dates_max: int = 0,
        missed_tasks_pct_max: float = 5.0,
        cpli_min: float = 0.95,
        bei_min: float = 0.95,
        exempt_loe: bool = True,
        exempt_wbs_summary: bool = True,
        exempt_completed: bool = True,
        exempt_milestones_from_duration_checks: bool = True,
        exempt_milestones_from_resource_check: bool = True,
    ) -> dict[str, Any]:
        """Run the full DCMA 14-point schedule assessment.

        Returns pass/fail, the measured metric, the threshold, and the offending
        activity codes for each of: 1 Logic, 2 Leads, 3 Lags, 4 Relationship
        Types, 5 Hard Constraints, 6 High Float, 7 Negative Float, 8 High
        Duration, 9 Invalid Dates, 10 Resources, 11 Missed Tasks, 12 Critical
        Path Test, 13 CPLI, 14 BEI.

        Defaults are the DCMA-EA PAM 200.1 values; every threshold and exemption
        is overridable. LOE, WBS summary, and completed activities are exempt by
        default, and milestones are exempt from the duration and resource checks.

        Checks 11 and 14 need a baseline: a linked baseline project in the file
        is used when present, otherwise planned dates stand in and the check
        says so in its `note`.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        th = DcmaThresholds(
            missing_logic_pct_max=missing_logic_pct_max,
            leads_max=leads_max,
            lags_pct_max=lags_pct_max,
            fs_pct_min=fs_pct_min,
            hard_constraints_pct_max=hard_constraints_pct_max,
            high_float_days=high_float_days,
            high_float_pct_max=high_float_pct_max,
            negative_float_max=negative_float_max,
            high_duration_days=high_duration_days,
            high_duration_pct_max=high_duration_pct_max,
            invalid_dates_max=invalid_dates_max,
            missed_tasks_pct_max=missed_tasks_pct_max,
            cpli_min=cpli_min,
            bei_min=bei_min,
            exempt_loe=exempt_loe,
            exempt_wbs_summary=exempt_wbs_summary,
            exempt_completed=exempt_completed,
            exempt_milestones_from_duration_checks=(exempt_milestones_from_duration_checks),
            exempt_milestones_from_resource_check=(exempt_milestones_from_resource_check),
        )
        return ctx.guard(dcma_service(sch, projects, th))

    @mcp.tool(name="check_schedule_quality", title="Check schedule quality", annotations=READ_ONLY)
    @tool_errors
    def check_schedule_quality_tool(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        long_duration_days: float = 44.0,
        high_float_days: float = 44.0,
    ) -> dict[str, Any]:
        """Fast quality sweep returning offending activity codes per defect type:
        missing logic, long durations, high or negative float, unresourced work,
        missing dates, hard constraints, invalid dates, out-of-sequence progress,
        LOE without logic, milestones with duration, and status anomalies.

        Use this for a quick triage; use run_dcma_assessment for formal scoring.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        return ctx.guard(check_schedule_quality(sch, projects, long_duration_days, high_float_days))

    @mcp.tool(title="Get schedule health score", annotations=READ_ONLY)
    @tool_errors
    def get_schedule_health_score(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """A composite 0-100 schedule health score with a per-component breakdown
        and prioritized recommendations.

        Components (default weights): logic 20, float 15, invalid dates 15,
        leads/lags 10, constraints 10, duration 10, resources 10, progress 10,
        relationship types 5. Override any of them via `weights`.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        return ctx.guard(health_score(sch, projects, weights))

    @mcp.tool(title="Get invalid dates", annotations=READ_ONLY)
    @tool_errors
    def get_invalid_dates(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Activities whose dates contradict the data date: actuals in the future,
        or forecast work left in the past. These must be zero before a schedule
        update is credible."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        rows = invalid_dates(sch, projects)
        return ctx.page(
            rows,
            limit,
            offset,
            extra={"data_date": sch.data_date(projects[0] if projects else None)},
        )

    _ = (
        run_dcma_assessment,
        check_schedule_quality_tool,
        get_schedule_health_score,
        get_invalid_dates,
    )
