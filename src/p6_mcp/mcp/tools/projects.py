"""§5.2 Project and EPS tools."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.exceptions import NotFoundError
from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.services.query.serialize import iso, project_to_dict


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register project and EPS tools."""

    @mcp.tool(title="Get projects", annotations=READ_ONLY)
    @tool_errors
    def get_projects(
        file_path: str, include_baselines: bool = True, verbosity: str = "standard"
    ) -> dict[str, Any]:
        """List every project in the file with dates, settings, and counts.

        An XER can hold many projects plus their baselines (project_flag='N').
        Start here on a multi-project file to get the proj_id / short name you
        will pass to other tools.
        """
        sch = ctx.schedule(file_path)
        projects = sch.projects if include_baselines else sch.active_projects
        return ctx.guard(
            {
                "total": len(projects),
                "items": [project_to_dict(sch, p, verbosity) for p in projects],
            }
        )

    @mcp.tool(title="Get project detail", annotations=READ_ONLY)
    @tool_errors
    def get_project_detail(
        file_path: str, project_id: int | None = None, project_short_name: str | None = None
    ) -> dict[str, Any]:
        """Every PROJECT field for one project, plus WBS/activity/resource counts
        and its baseline linkage."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        p = projects[0]
        acts = [a for a in sch.activities if a.proj_id == p.proj_id]
        baselines = [
            {"proj_id": b.proj_id, "short_name": b.short_name}
            for b in sch.baseline_projects
            if b.orig_proj_id == p.proj_id or p.sum_base_proj_id == b.proj_id
        ]
        return ctx.guard(
            {
                **project_to_dict(sch, p, "standard"),
                "all_fields": p.to_dict(),
                "wbs_node_count": sum(1 for w in sch.wbs_nodes if w.proj_id == p.proj_id),
                "relationship_count": sum(1 for r in sch.relationships if r.proj_id == p.proj_id),
                "assignment_count": sum(1 for x in sch.assignments if x.proj_id == p.proj_id),
                "status_counts": {
                    "completed": sum(1 for a in acts if a.is_completed),
                    "in_progress": sum(1 for a in acts if a.is_in_progress),
                    "not_started": sum(1 for a in acts if a.is_not_started),
                },
                "baselines": baselines,
            }
        )

    @mcp.tool(title="Get project codes", annotations=READ_ONLY)
    @tool_errors
    def get_project_codes(file_path: str) -> dict[str, Any]:
        """Project code types (PCATTYPE) and their values (PCATVAL)."""
        sch = ctx.schedule(file_path)
        types = {
            int(d["proj_catg_type_id"]): d
            for d in sch.table("PCATTYPE").iter_dicts()
            if d.get("proj_catg_type_id") is not None
        }
        values = [
            {
                "code_type": types.get(int(d.get("proj_catg_type_id") or 0), {}).get(
                    "proj_catg_type"
                ),
                "code_value": d.get("proj_catg_short_name"),
                "description": d.get("proj_catg_name"),
                "proj_catg_id": d.get("proj_catg_id"),
            }
            for d in sch.table("PCATVAL").iter_dicts()
        ]
        return ctx.guard(
            {
                "code_types": [
                    {"proj_catg_type_id": k, "name": v.get("proj_catg_type")}
                    for k, v in sorted(types.items())
                ],
                "values": sorted(values, key=lambda d: (str(d["code_type"]), str(d["code_value"]))),
            }
        )

    @mcp.tool(title="Get project code assignments", annotations=READ_ONLY)
    @tool_errors
    def get_project_code_assignments(
        file_path: str, project_id: int | None = None
    ) -> dict[str, Any]:
        """Which project codes are assigned to which projects (PROJPCAT)."""
        sch = ctx.schedule(file_path)
        types = {
            int(d["proj_catg_type_id"]): d.get("proj_catg_type")
            for d in sch.table("PCATTYPE").iter_dicts()
            if d.get("proj_catg_type_id") is not None
        }
        values = {
            int(d["proj_catg_id"]): d.get("proj_catg_short_name")
            for d in sch.table("PCATVAL").iter_dicts()
            if d.get("proj_catg_id") is not None
        }
        rows = []
        for d in sch.table("PROJPCAT").iter_dicts():
            pid = d.get("proj_id")
            if project_id is not None and pid != project_id:
                continue
            proj = sch.projects_by_id.get(int(pid)) if pid is not None else None
            rows.append(
                {
                    "proj_id": pid,
                    "project": proj.short_name if proj else None,
                    "code_type": types.get(int(d.get("proj_catg_type_id") or 0)),
                    "code_value": values.get(int(d.get("proj_catg_id") or 0)),
                }
            )
        return ctx.guard({"total": len(rows), "items": iso(rows)})

    @mcp.tool(title="Get schedule options", annotations=READ_ONLY)
    @tool_errors
    def get_schedule_options(
        file_path: str, project_id: int | None = None, project_short_name: str | None = None
    ) -> dict[str, Any]:
        """Decoded SCHEDOPTIONS: retained logic vs progress override, whether the
        longest path is used for criticality, which calendar applies to lag, and
        the float calculation basis.

        These settings explain *why* P6 produced the stored dates, so check them
        before disputing a critical path or a float value.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        out = []
        for p in projects:
            opts = sch.schedoptions_by_proj.get(p.proj_id)
            if opts is None:
                continue
            decoded = {
                "retained_logic": opts.get("sched_retained_logic"),
                "progress_override": opts.get("sched_progress_override"),
                "outer_dependency_type": opts.get("sched_outer_depend_type"),
                "open_ends_are_critical": opts.get("sched_open_critical_flag"),
                "lag_calendar": opts.get("sched_calendar_on_relationship_lag"),
                "float_basis": opts.get("sched_float_type"),
                "use_expected_finish": opts.get("sched_use_expect_end_flag"),
                "use_project_end_date_for_float": opts.get("sched_use_project_end_date_for_float"),
                "level_float_threshold_hours": opts.get("level_float_thrs_cnt"),
            }
            out.append(
                {
                    "proj_id": p.proj_id,
                    "project": p.short_name,
                    "critical_path_type": p.critical_path_type_label,
                    "critical_float_threshold_hours": p.critical_drtn_hr_cnt,
                    "options": decoded,
                    "all_fields": opts,
                }
            )
        if not out:
            raise NotFoundError(
                "This file has no SCHEDOPTIONS rows",
                hint="Schedule options are only present when P6 exports them.",
            )
        return ctx.guard({"items": iso(out)})

    @mcp.tool(title="Get data date", annotations=READ_ONLY)
    @tool_errors
    def get_data_date(
        file_path: str, project_id: int | None = None, project_short_name: str | None = None
    ) -> dict[str, Any]:
        """The data date (last_recalc_date) — the 'as of' moment that separates
        actuals from forecast. Every progress and EVM figure depends on it."""
        _, projects = ctx.scope(file_path, project_id, project_short_name)
        return ctx.guard(
            {
                "items": [
                    {
                        "proj_id": p.proj_id,
                        "project": p.short_name,
                        "data_date": p.data_date,
                        "next_data_date": p.date("next_data_date"),
                        "last_baseline_update": p.date("last_baseline_update_date"),
                    }
                    for p in projects
                ]
            }
        )

    @mcp.tool(title="Get baselines", annotations=READ_ONLY)
    @tool_errors
    def get_baselines(file_path: str) -> dict[str, Any]:
        """Baseline projects present in the file and which live project each
        belongs to. Use the returned proj_id with compare_to_baseline."""
        sch = ctx.schedule(file_path)
        rows = []
        for b in sch.baseline_projects:
            parent = None
            if b.orig_proj_id is not None:
                parent = sch.projects_by_id.get(b.orig_proj_id)
            if parent is None:
                parent = next(
                    (p for p in sch.active_projects if p.sum_base_proj_id == b.proj_id),
                    None,
                )
            rows.append(
                {
                    "baseline_proj_id": b.proj_id,
                    "baseline_name": b.short_name,
                    "linked_to_proj_id": parent.proj_id if parent else None,
                    "linked_to": parent.short_name if parent else None,
                    "activity_count": sum(1 for a in sch.activities if a.proj_id == b.proj_id),
                    "plan_start": b.plan_start,
                    "plan_end": b.plan_end,
                }
            )
        return ctx.guard({"total": len(rows), "items": iso(rows)})

    _ = (
        get_projects,
        get_project_detail,
        get_project_codes,
        get_project_code_assignments,
        get_schedule_options,
        get_data_date,
        get_baselines,
    )
