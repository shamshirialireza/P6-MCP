"""§5.13 Report tools."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.exceptions import InvalidArgumentError
from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.services.analysis.cost import cost_summary
from p6_mcp.services.analysis.critical_path import get_critical_path
from p6_mcp.services.analysis.health_score import health_score
from p6_mcp.services.analysis.milestones import milestones
from p6_mcp.services.analysis.progress import progress_summary
from p6_mcp.services.report import REPORT_TYPES, build_report


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register report tools."""

    @mcp.tool(title="Generate report", annotations=READ_ONLY)
    @tool_errors
    def generate_report(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        report_type: str = "executive",
        output_format: str = "markdown",
        sections: list[str] | None = None,
    ) -> dict[str, Any]:
        """Produce a formatted schedule report ready to paste into a status pack.

        report_type: executive, detailed, critical_path, milestone, resource,
        cost, dcma, progress, baseline_variance, lookahead, or logic_health.

        output_format 'markdown' returns prose and tables; 'json' returns the
        same content as structured sections; 'html' wraps the markdown. Use
        `sections` to keep only named sections of the structured output.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        rep = build_report(sch, projects, report_type, sections)
        if output_format == "markdown":
            return ctx.guard(
                {"report_type": report_type, "title": rep.title, "markdown": rep.to_markdown()}
            )
        if output_format == "html":
            return ctx.guard(
                {
                    "report_type": report_type,
                    "title": rep.title,
                    "html": _html(rep.title, rep.to_markdown()),
                }
            )
        if output_format == "json":
            return ctx.guard(rep.to_dict())
        raise InvalidArgumentError(
            f"Unknown output_format {output_format!r}",
            hint="Use markdown, json, or html.",
        )

    @mcp.tool(title="Get schedule summary", annotations=READ_ONLY)
    @tool_errors
    def get_schedule_summary(
        file_path: str, project_id: int | None = None, project_short_name: str | None = None
    ) -> dict[str, Any]:
        """A one-call at-a-glance summary: counts, data date, project dates,
        critical activity count, milestones, float statistics, cost totals, and
        the composite health score.

        Best first call for "how is this project doing?". Follow up with the
        specialised tools for any figure you want to drill into.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        prog = progress_summary(sch, projects)
        crit = get_critical_path(sch, projects, "total_float")
        costs = cost_summary(sch, projects, "wbs")
        ms = milestones(sch, projects)
        acts = sch.activities_of(projects)
        floats = [
            sch.hours_to_days(a, a.total_float_hours)
            for a in acts
            if not a.is_completed and a.total_float_hours is not None
        ]
        floats = [f for f in floats if f is not None]
        return ctx.guard(
            {
                "projects": [
                    {
                        "proj_id": p.proj_id,
                        "name": p.short_name,
                        "data_date": p.data_date,
                        "plan_start": p.plan_start,
                        "plan_end": p.plan_end,
                    }
                    for p in projects
                ],
                "counts": {
                    "activities": len(acts),
                    "relationships": len(sch.relationships),
                    "wbs_nodes": len(sch.wbs_nodes),
                    "resources": len(sch.resources),
                    "assignments": len(sch.assignments),
                    "calendars": len(sch.calendars),
                    "milestones": len(ms),
                    **prog["activity_counts"],
                },
                "percent_complete": prog["percent_complete"],
                "forecast_finish": prog["forecast_finish"],
                "working_days_to_finish": prog["working_days_to_finish"],
                "critical_activity_count": len(crit["total_float_critical"]),
                "float_stats": {
                    "min_days": round(min(floats), 1) if floats else None,
                    "max_days": round(max(floats), 1) if floats else None,
                    "negative_float_count": sum(1 for f in floats if f < 0),
                },
                "cost": costs["totals"],
                "health": health_score(sch, projects),
                "milestones": ms[:15],
            }
        )

    _ = (generate_report, get_schedule_summary)
    _ = REPORT_TYPES


def _html(title: str, markdown: str) -> str:
    """Minimal self-contained HTML wrapper (markdown kept as readable <pre>)."""
    escaped = markdown.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title><style>"
        "body{font-family:-apple-system,Segoe UI,Helvetica,sans-serif;"
        "max-width:60rem;margin:2rem auto;padding:0 1rem;line-height:1.5}"
        "pre{white-space:pre-wrap;font-family:ui-monospace,Menlo,monospace;"
        "font-size:.9rem}</style></head><body>"
        f"<pre>{escaped}</pre></body></html>"
    )
