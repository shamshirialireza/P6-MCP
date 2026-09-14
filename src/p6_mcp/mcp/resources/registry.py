"""`p6://` resource templates (§6).

Resources are addressed by the ``schedule_id`` returned from ``open_schedule``,
so a client can browse a parsed file without re-passing paths. JSON resources
return ``application/json``; summary views return ``text/markdown``.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.mcp.context import AppContext
from p6_mcp.mcp.data_dictionary import dictionary
from p6_mcp.services.analysis.critical_path import get_critical_path
from p6_mcp.services.analysis.dcma import run_dcma_assessment
from p6_mcp.services.analysis.earned_value import earned_value
from p6_mcp.services.analysis.health_score import health_score
from p6_mcp.services.analysis.milestones import milestones
from p6_mcp.services.export.tabular import to_json_text
from p6_mcp.services.query.serialize import (
    activity_to_dict,
    calendar_to_dict,
    iso,
    project_to_dict,
    relationship_to_dict,
    resource_to_dict,
    wbs_to_dict,
)
from p6_mcp.services.report import build_report

JSON = "application/json"
MD = "text/markdown"


def register_resources(mcp: MCPServer, ctx: AppContext) -> None:
    """Register every p6:// resource template."""

    def _sched(schedule_id: str) -> Any:
        return ctx.loader.load(schedule_id)

    def _projects(sch: Any, project_id: str) -> Any:
        return sch.resolve_projects(int(project_id))

    def _json(payload: Any) -> str:
        return to_json_text(ctx.guard(payload) if isinstance(payload, dict) else {"items": payload})

    @mcp.resource(
        "p6://{schedule_id}/header",
        mime_type=JSON,
        name="XER file header",
        description="ERMHDR provenance: P6 version, export date, user, database, currency.",
    )
    def header(schedule_id: str) -> str:
        sch = _sched(schedule_id)
        return _json({"encoding": sch.doc.encoding, **sch.doc.header.to_dict()})

    @mcp.resource(
        "p6://{schedule_id}/tables",
        mime_type=JSON,
        name="Table inventory",
        description="Every table in the file with row and field counts.",
    )
    def tables(schedule_id: str) -> str:
        sch = _sched(schedule_id)
        return _json({"items": sch.doc.inventory()})

    @mcp.resource(
        "p6://{schedule_id}/tables/{table_name}",
        mime_type=JSON,
        name="Raw table rows",
        description="Raw rows of any XER table (first 500).",
    )
    def table_rows(schedule_id: str, table_name: str) -> str:
        sch = _sched(schedule_id)
        table = sch.doc.table(table_name)
        if table is None:
            return _json({"error": f"no table {table_name}"})
        return _json(
            {
                "table": table.name,
                "fields": table.fields,
                "total_rows": len(table.rows),
                "items": [iso(table.row_dict(r)) for r in table.rows[:500]],
            }
        )

    @mcp.resource(
        "p6://{schedule_id}/projects",
        mime_type=JSON,
        name="Projects",
        description="All projects and baselines in the file.",
    )
    def projects(schedule_id: str) -> str:
        sch = _sched(schedule_id)
        return _json({"items": [project_to_dict(sch, p) for p in sch.projects]})

    @mcp.resource(
        "p6://{schedule_id}/projects/{project_id}",
        mime_type=JSON,
        name="Project detail",
        description="One project's fields.",
    )
    def project(schedule_id: str, project_id: str) -> str:
        sch = _sched(schedule_id)
        p = _projects(sch, project_id)[0]
        return _json({**project_to_dict(sch, p), "all_fields": iso(p.to_dict())})

    @mcp.resource(
        "p6://{schedule_id}/projects/{project_id}/summary",
        mime_type=MD,
        name="Executive summary",
        description="Markdown executive summary for a project.",
    )
    def project_summary(schedule_id: str, project_id: str) -> str:
        sch = _sched(schedule_id)
        return build_report(sch, _projects(sch, project_id), "executive").to_markdown()

    @mcp.resource(
        "p6://{schedule_id}/projects/{project_id}/critical-path",
        mime_type=JSON,
        name="Critical path",
        description="Critical activities by total float and longest path.",
    )
    def critical_path(schedule_id: str, project_id: str) -> str:
        sch = _sched(schedule_id)
        res = get_critical_path(sch, _projects(sch, project_id), "both")
        return _json(
            {
                "method": "both",
                "total_float_critical": [
                    activity_to_dict(sch, a, "compact") for a in res.get("total_float_critical", [])
                ],
                "longest_path": [
                    activity_to_dict(sch, a, "compact") for a in res.get("longest_path", [])
                ],
                "longest_path_note": res.get("longest_path_note"),
            }
        )

    @mcp.resource(
        "p6://{schedule_id}/projects/{project_id}/milestones",
        mime_type=JSON,
        name="Milestones",
        description="Milestones with dates and baseline variance.",
    )
    def project_milestones(schedule_id: str, project_id: str) -> str:
        sch = _sched(schedule_id)
        return _json({"items": milestones(sch, _projects(sch, project_id))})

    @mcp.resource(
        "p6://{schedule_id}/projects/{project_id}/dcma",
        mime_type=JSON,
        name="DCMA assessment",
        description="Full DCMA 14-point result with default thresholds.",
    )
    def dcma(schedule_id: str, project_id: str) -> str:
        sch = _sched(schedule_id)
        return _json(run_dcma_assessment(sch, _projects(sch, project_id)))

    @mcp.resource(
        "p6://{schedule_id}/projects/{project_id}/earned-value",
        mime_type=JSON,
        name="Earned value",
        description="EVM metrics with PV time-phased to the data date.",
    )
    def ev(schedule_id: str, project_id: str) -> str:
        sch = _sched(schedule_id)
        return _json(earned_value(sch, _projects(sch, project_id), time_phased=False))

    @mcp.resource(
        "p6://{schedule_id}/projects/{project_id}/health",
        mime_type=JSON,
        name="Health score",
        description="Composite 0-100 health score with breakdown.",
    )
    def health(schedule_id: str, project_id: str) -> str:
        sch = _sched(schedule_id)
        return _json(health_score(sch, _projects(sch, project_id)))

    @mcp.resource(
        "p6://{schedule_id}/activities",
        mime_type=JSON,
        name="Activities",
        description="All activities (first 500) in compact form.",
    )
    def activities(schedule_id: str) -> str:
        sch = _sched(schedule_id)
        acts = sorted(sch.activities_of(sch.active_projects or sch.projects), key=lambda a: a.code)
        return _json(
            {
                "total": len(acts),
                "items": [activity_to_dict(sch, a, "compact") for a in acts[:500]],
            }
        )

    @mcp.resource(
        "p6://{schedule_id}/activities/{task_code}",
        mime_type=JSON,
        name="Activity detail",
        description="One activity with logic, assignments, and codes.",
    )
    def activity(schedule_id: str, task_code: str) -> str:
        sch = _sched(schedule_id)
        a = sch.resolve_activity(task_code)
        return _json(
            {
                **activity_to_dict(sch, a, "standard"),
                "all_fields": iso(a.to_dict()),
                "predecessors": [
                    relationship_to_dict(sch, r) for r in sch.predecessors_of.get(a.task_id, [])
                ],
                "successors": [
                    relationship_to_dict(sch, r) for r in sch.successors_of.get(a.task_id, [])
                ],
                "activity_codes": sch.codes_by_task.get(a.task_id, []),
                "udfs": sch.task_udfs(a.task_id),
            }
        )

    @mcp.resource(
        "p6://{schedule_id}/wbs",
        mime_type=JSON,
        name="WBS",
        description="Work breakdown structure with paths and levels.",
    )
    def wbs(schedule_id: str) -> str:
        sch = _sched(schedule_id)
        return _json({"items": [wbs_to_dict(sch, w) for w in sch.wbs_nodes]})

    @mcp.resource(
        "p6://{schedule_id}/wbs/{wbs_id}",
        mime_type=JSON,
        name="WBS node",
        description="One WBS node and its activities.",
    )
    def wbs_node(schedule_id: str, wbs_id: str) -> str:
        sch = _sched(schedule_id)
        node = sch.wbs_by_id.get(int(wbs_id))
        if node is None:
            return _json({"error": f"no wbs node {wbs_id}"})
        return _json(
            {
                **wbs_to_dict(sch, node, "full"),
                "activities": [
                    activity_to_dict(sch, a, "compact")
                    for a in sch.activities_by_wbs.get(node.wbs_id, [])
                ],
            }
        )

    @mcp.resource(
        "p6://{schedule_id}/resources",
        mime_type=JSON,
        name="Resources",
        description="The resource pool.",
    )
    def resources(schedule_id: str) -> str:
        sch = _sched(schedule_id)
        return _json({"items": [resource_to_dict(sch, r) for r in sch.resources]})

    @mcp.resource(
        "p6://{schedule_id}/resources/{rsrc_id}",
        mime_type=JSON,
        name="Resource detail",
        description="One resource with rates and assignment totals.",
    )
    def resource(schedule_id: str, rsrc_id: str) -> str:
        sch = _sched(schedule_id)
        r = sch.resolve_resource(rsrc_id)
        assignments = sch.assignments_by_rsrc.get(r.rsrc_id, [])
        return _json(
            {
                **resource_to_dict(sch, r, "full"),
                "rates": sch.rates_by_rsrc.get(r.rsrc_id, []),
                "assignment_count": len(assignments),
                "budgeted_qty": round(sum(x.budgeted_qty for x in assignments), 2),
            }
        )

    @mcp.resource(
        "p6://{schedule_id}/calendars/{clndr_id}",
        mime_type=JSON,
        name="Calendar",
        description="A calendar's work week and holiday exceptions.",
    )
    def calendar(schedule_id: str, clndr_id: str) -> str:
        sch = _sched(schedule_id)
        c = sch.calendars_by_id.get(int(clndr_id))
        if c is None:
            return _json({"error": f"no calendar {clndr_id}"})
        return _json(calendar_to_dict(sch, c))

    @mcp.resource(
        "p6://{schedule_id}/relationships",
        mime_type=JSON,
        name="Relationships",
        description="The relationship network (first 1000 links).",
    )
    def relationships(schedule_id: str) -> str:
        sch = _sched(schedule_id)
        return _json(
            {
                "total": len(sch.relationships),
                "items": [relationship_to_dict(sch, r) for r in sch.relationships[:1000]],
            }
        )

    @mcp.resource(
        "p6://{schedule_id}/data-dictionary",
        mime_type=JSON,
        name="P6 data dictionary",
        description="Plain-language P6 table, field, and enum reference.",
    )
    def data_dictionary(schedule_id: str) -> str:
        _ = schedule_id
        return to_json_text(dictionary())

    _ = (
        header,
        tables,
        table_rows,
        projects,
        project,
        project_summary,
        critical_path,
        project_milestones,
        dcma,
        ev,
        health,
        activities,
        activity,
        wbs,
        wbs_node,
        resources,
        resource,
        calendar,
        relationships,
        data_dictionary,
    )


# Live P6 EPPM resources (§15.6)
def _register_live_resources(mcp: MCPServer, ctx: AppContext) -> None:
    """Register live P6 EPPM resource templates."""

    @mcp.resource(
        "p6://{connection}/projects",
        mime_type=JSON,
        name="P6 EPPM projects",
        description="Projects and baselines from a P6 EPPM connection.",
    )
    def p6_projects(connection: str) -> str:
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Use the P6EppmRepository to get projects
        # 3. Return project information
        return '{"error": "Live P6 EPPM resources not yet implemented"}'

    @mcp.resource(
        "p6://{connection}/projects/{project_id}/summary",
        mime_type="text/markdown",
        name="P6 EPPM project summary",
        description="Executive summary for a P6 EPPM project.",
    )
    def p6_project_summary(connection: str, project_id: str) -> str:
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Use the P6EppmRepository to load the project
        # 3. Generate an executive summary
        return "# P6 EPPM Project Summary\n\nLive P6 EPPM resources not yet implemented."

    @mcp.resource(
        "p6://{connection}/projects/{project_id}/critical-path",
        mime_type=JSON,
        name="P6 EPPM critical path",
        description="Critical activities by total float and longest path.",
    )
    def p6_project_critical_path(connection: str, project_id: str) -> str:
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Use the P6EppmRepository to load the project
        # 3. Calculate and return critical path
        return '{"error": "Live P6 EPPM resources not yet implemented"}'

    @mcp.resource(
        "p6://{connection}/projects/{project_id}/milestones",
        mime_type=JSON,
        name="P6 EPPM milestones",
        description="Milestones with dates and baseline variance.",
    )
    def p6_project_milestones(connection: str, project_id: str) -> str:
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Use the P6EppmRepository to load the project
        # 3. Return milestone information
        return '{"error": "Live P6 EPPM resources not yet implemented"}'

    @mcp.resource(
        "p6://{connection}/projects/{project_id}/dcma",
        mime_type=JSON,
        name="P6 EPPM DCMA assessment",
        description="Full DCMA 14-point result with default thresholds.",
    )
    def p6_project_dcma(connection: str, project_id: str) -> str:
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Use the P6EppmRepository to load the project
        # 3. Run DCMA assessment and return results
        return '{"error": "Live P6 EPPM resources not yet implemented"}'

    @mcp.resource(
        "p6://{connection}/projects/{project_id}/earned-value",
        mime_type=JSON,
        name="P6 EPPM earned value",
        description="EVM metrics with PV time-phased to the data date.",
    )
    def p6_project_earned_value(connection: str, project_id: str) -> str:
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Use the P6EppmRepository to load the project
        # 3. Calculate and return EVM metrics
        return '{"error": "Live P6 EPPM resources not yet implemented"}'

    @mcp.resource(
        "p6://{connection}/projects/{project_id}/health",
        mime_type=JSON,
        name="P6 EPPM health score",
        description="Composite 0-100 health score with breakdown.",
    )
    def p6_project_health(connection: str, project_id: str) -> str:
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Use the P6EppmRepository to load the project
        # 3. Calculate and return health score
        return '{"error": "Live P6 EPPM resources not yet implemented"}'

    @mcp.resource(
        "p6://{connection}/fields/{service}",
        mime_type=JSON,
        name="P6 EPPM service fields",
        description="Field definitions for a P6 EPPM REST service.",
    )
    def p6_service_fields(connection: str, service: str) -> str:
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Use the P6EppmRepository to get field definitions
        # 3. Return the field information
        return '{"error": "Live P6 EPPM resources not yet implemented"}'
