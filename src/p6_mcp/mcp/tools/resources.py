"""§5.9 Resource, role, and cost-account tools."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.parser.coercion import parse_date
from p6_mcp.services.analysis.resources import leveling_report, utilization
from p6_mcp.services.query.serialize import (
    assignment_to_dict,
    iso,
    resource_to_dict,
)


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register resource, role, and account tools."""

    @mcp.tool(title="Get resources", annotations=READ_ONLY)
    @tool_errors
    def get_resources(
        file_path: str,
        rsrc_type: str | None = None,
        as_tree: bool = False,
        active_only: bool = False,
        name_contains: str | None = None,
        limit: int = 100,
        offset: int = 0,
        verbosity: str = "standard",
    ) -> dict[str, Any]:
        """The resource pool with hierarchy, calendar, unit of measure, and
        current rate. `rsrc_type` takes RT_Labor, RT_Mat, or RT_Equip."""
        sch = ctx.schedule(file_path)
        rows = sch.resources
        if rsrc_type:
            rows = [r for r in rows if r.rsrc_type == rsrc_type]
        if active_only:
            rows = [r for r in rows if r.is_active]
        if name_contains:
            needle = name_contains.lower()
            rows = [r for r in rows if needle in r.name.lower() or needle in r.short_name.lower()]
        if as_tree:
            by_parent: dict[int | None, list[Any]] = {}
            for r in rows:
                by_parent.setdefault(r.parent_rsrc_id, []).append(r)

            def subtree(parent: int | None) -> list[dict[str, Any]]:
                return [
                    {**resource_to_dict(sch, r, verbosity), "children": subtree(r.rsrc_id)}
                    for r in sorted(by_parent.get(parent, []), key=lambda x: x.name)
                ]

            known = {r.rsrc_id for r in rows}
            roots = [p for p in by_parent if p is None or p not in known]
            tree = [node for p in roots for node in subtree(p)]
            return ctx.guard({"total": len(rows), "tree": iso(tree)})
        return ctx.page(rows, limit, offset, render=lambda r: resource_to_dict(sch, r, verbosity))

    @mcp.tool(title="Get resource detail", annotations=READ_ONLY)
    @tool_errors
    def get_resource_detail(file_path: str, resource: str) -> dict[str, Any]:
        """One resource with rate history, role assignments, resource codes,
        calendar, shift, and an assignment summary.

        `resource` accepts an rsrc_id, short name, or full name.
        """
        sch = ctx.schedule(file_path)
        r = sch.resolve_resource(resource)
        assignments = sch.assignments_by_rsrc.get(r.rsrc_id, [])
        roles = [d for d in sch.table("RSRCROLE").iter_dicts() if d.get("rsrc_id") == r.rsrc_id]
        codes = [d for d in sch.table("RSRCRCAT").iter_dicts() if d.get("rsrc_id") == r.rsrc_id]
        return ctx.guard(
            {
                **resource_to_dict(sch, r, "full"),
                "rates": sch.rates_by_rsrc.get(r.rsrc_id, []),
                "roles": roles,
                "codes": codes,
                "assignment_summary": {
                    "count": len(assignments),
                    "budgeted_qty": round(sum(x.budgeted_qty for x in assignments), 2),
                    "actual_qty": round(sum(x.actual_qty for x in assignments), 2),
                    "remaining_qty": round(sum(x.remaining_qty for x in assignments), 2),
                    "budgeted_cost": round(sum(x.budgeted_cost for x in assignments), 2),
                },
            }
        )

    @mcp.tool(title="Get resource rates", annotations=READ_ONLY)
    @tool_errors
    def get_resource_rates(file_path: str, resource: str | None = None) -> dict[str, Any]:
        """Rate history (RSRCRATE): price per unit, max units per hour, and the
        effective start date of each rate row."""
        sch = ctx.schedule(file_path)
        if resource:
            r = sch.resolve_resource(resource)
            rows = [{"resource": r.name, **d} for d in sch.rates_by_rsrc.get(r.rsrc_id, [])]
        else:
            rows = [
                {"resource": sch.resources_by_id[rid].name, **d}
                for rid, rates in sorted(sch.rates_by_rsrc.items())
                if rid in sch.resources_by_id
                for d in rates
            ]
        return ctx.guard({"total": len(rows), "items": iso(rows)})

    @mcp.tool(title="Get resource codes", annotations=READ_ONLY)
    @tool_errors
    def get_resource_codes(file_path: str) -> dict[str, Any]:
        """Resource code types (RCATTYPE) and values (RCATVAL)."""
        sch = ctx.schedule(file_path)
        types = {
            int(d["rsrc_catg_type_id"]): d
            for d in sch.table("RCATTYPE").iter_dicts()
            if d.get("rsrc_catg_type_id") is not None
        }
        values = [
            {
                "code_type": types.get(int(d.get("rsrc_catg_type_id") or 0), {}).get(
                    "rsrc_catg_type"
                ),
                "value": d.get("rsrc_catg_short_name"),
                "description": d.get("rsrc_catg_name"),
            }
            for d in sch.table("RCATVAL").iter_dicts()
        ]
        return ctx.guard(
            {
                "code_types": [
                    {"id": k, "name": v.get("rsrc_catg_type")} for k, v in sorted(types.items())
                ],
                "values": iso(values),
            }
        )

    @mcp.tool(title="Get resource curves", annotations=READ_ONLY)
    @tool_errors
    def get_resource_curves(file_path: str) -> dict[str, Any]:
        """Resource distribution curves (RSRCCURVDATA) used to shape non-linear
        spreading in analyze_resource_utilization and get_cash_flow."""
        sch = ctx.schedule(file_path)
        rows = list(sch.table("RSRCCURVDATA").iter_dicts())
        return ctx.guard({"total": len(rows), "items": iso(rows)})

    @mcp.tool(title="Get roles", annotations=READ_ONLY)
    @tool_errors
    def get_roles(file_path: str, as_tree: bool = False) -> dict[str, Any]:
        """The role dictionary (ROLES), optionally as a hierarchy."""
        sch = ctx.schedule(file_path)
        rows = list(sch.table("ROLES").iter_dicts())
        if not as_tree:
            return ctx.guard({"total": len(rows), "items": iso(rows)})
        by_parent: dict[Any, list[dict[str, Any]]] = {}
        for d in rows:
            by_parent.setdefault(d.get("parent_role_id"), []).append(d)

        def subtree(parent: Any) -> list[dict[str, Any]]:
            return [
                {**d, "children": subtree(d.get("role_id"))}
                for d in sorted(by_parent.get(parent, []), key=lambda x: str(x.get("role_name")))
            ]

        return ctx.guard({"total": len(rows), "tree": iso(subtree(None))})

    @mcp.tool(title="Get role rates", annotations=READ_ONLY)
    @tool_errors
    def get_role_rates(file_path: str) -> dict[str, Any]:
        """Role price rates (ROLERATE)."""
        sch = ctx.schedule(file_path)
        rows = list(sch.table("ROLERATE").iter_dicts())
        return ctx.guard({"total": len(rows), "items": iso(rows)})

    @mcp.tool(title="Get role limits", annotations=READ_ONLY)
    @tool_errors
    def get_role_limits(file_path: str) -> dict[str, Any]:
        """Role availability limits over time (ROLELIMIT)."""
        sch = ctx.schedule(file_path)
        rows = list(sch.table("ROLELIMIT").iter_dicts())
        return ctx.guard({"total": len(rows), "items": iso(rows)})

    @mcp.tool(title="Get role codes", annotations=READ_ONLY)
    @tool_errors
    def get_role_codes(file_path: str) -> dict[str, Any]:
        """Role code types (ROLECATTYPE), values (ROLECATVAL), and assignments."""
        sch = ctx.schedule(file_path)
        return ctx.guard(
            {
                "code_types": iso(list(sch.table("ROLECATTYPE").iter_dicts())),
                "values": iso(list(sch.table("ROLECATVAL").iter_dicts())),
                "assignments": iso(list(sch.table("ROLERCAT").iter_dicts())),
            }
        )

    @mcp.tool(title="Get resource assignments", annotations=READ_ONLY)
    @tool_errors
    def get_resource_assignments(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        resource: str | None = None,
        task_code: str | None = None,
        role_id: int | None = None,
        acct_id: int | None = None,
        limit: int = 100,
        offset: int = 0,
        verbosity: str = "standard",
    ) -> dict[str, Any]:
        """Resource/role assignments (TASKRSRC) with quantities and costs,
        enriched with activity and resource names."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        proj_ids = {p.proj_id for p in projects}
        rows = [x for x in sch.assignments if x.proj_id in proj_ids]
        if resource:
            r = sch.resolve_resource(resource)
            rows = [x for x in rows if x.rsrc_id == r.rsrc_id]
        if task_code:
            a = sch.resolve_activity(task_code)
            rows = [x for x in rows if x.task_id == a.task_id]
        if role_id is not None:
            rows = [x for x in rows if x.role_id == role_id]
        if acct_id is not None:
            rows = [x for x in rows if x.f("acct_id") == acct_id]
        rows.sort(key=lambda x: (x.task_id, x.rsrc_id or 0))
        return ctx.page(rows, limit, offset, render=lambda x: assignment_to_dict(sch, x, verbosity))

    @mcp.tool(title="Analyze resource utilization", annotations=READ_ONLY)
    @tool_errors
    def analyze_resource_utilization(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        period: str = "week",
        start: str | None = None,
        end: str | None = None,
        rsrc_ids: list[int] | None = None,
        use_curves: bool = True,
        compare_to: str | None = "max_units",
    ) -> dict[str, Any]:
        """Time-phased planned/actual/remaining units and cost per resource per
        period, with per-period over-allocation flags.

        Demand is spread across each resource's *own* calendar working hours (so
        holidays reduce capacity correctly) and compared against RSRCRATE
        max_qty_per_hr x the working hours in that period. `period` takes day,
        week, month, quarter, or year. Set compare_to=null to skip limits.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        return ctx.guard(
            utilization(
                sch,
                projects,
                period,
                parse_date(start) if start else None,
                parse_date(end) if end else None,
                rsrc_ids,
                use_curves,
                compare_to,
            )
        )

    @mcp.tool(title="Get resource histogram", annotations=READ_ONLY)
    @tool_errors
    def get_resource_histogram(
        file_path: str,
        resource: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        period: str = "week",
    ) -> dict[str, Any]:
        """A single resource's demand per period — the histogram view.

        Narrower output than analyze_resource_utilization; use that tool when
        you need the whole pool at once.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        r = sch.resolve_resource(resource)
        res = utilization(sch, projects, period, rsrc_ids=[r.rsrc_id])
        entry = (
            res["resources"][0]
            if res["resources"]
            else {"resource": r.name, "periods": [], "totals": {}}
        )
        return ctx.guard({"period": period, **entry})

    @mcp.tool(title="Get resource leveling report", annotations=READ_ONLY)
    @tool_errors
    def get_resource_leveling_report(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        period: str = "week",
    ) -> dict[str, Any]:
        """Peak demand period per resource and every period exceeding its limit.

        The starting point for levelling: fix the peaks with the least float
        first.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        return ctx.guard(leveling_report(sch, projects, period))

    @mcp.tool(title="Get cost accounts", annotations=READ_ONLY)
    @tool_errors
    def get_cost_accounts(file_path: str, as_tree: bool = False) -> dict[str, Any]:
        """The cost account breakdown structure (ACCOUNT)."""
        sch = ctx.schedule(file_path)
        rows = list(sch.table("ACCOUNT").iter_dicts())
        if not as_tree:
            return ctx.guard({"total": len(rows), "items": iso(rows)})
        by_parent: dict[Any, list[dict[str, Any]]] = {}
        for d in rows:
            by_parent.setdefault(d.get("parent_acct_id"), []).append(d)

        def subtree(parent: Any) -> list[dict[str, Any]]:
            return [
                {**d, "children": subtree(d.get("acct_id"))}
                for d in sorted(
                    by_parent.get(parent, []), key=lambda x: str(x.get("acct_short_name"))
                )
            ]

        return ctx.guard({"total": len(rows), "tree": iso(subtree(None))})

    @mcp.tool(title="Get units of measure", annotations=READ_ONLY)
    @tool_errors
    def get_units_of_measure(file_path: str) -> dict[str, Any]:
        """Material units of measure (UMEASURE)."""
        sch = ctx.schedule(file_path)
        return ctx.guard({"items": iso(list(sch.table("UMEASURE").iter_dicts()))})

    @mcp.tool(title="Get currencies", annotations=READ_ONLY)
    @tool_errors
    def get_currencies(file_path: str) -> dict[str, Any]:
        """Currency definitions (CURRTYPE) with symbols and decimal settings."""
        sch = ctx.schedule(file_path)
        return ctx.guard({"items": iso(list(sch.table("CURRTYPE").iter_dicts()))})

    @mcp.tool(title="Get shifts", annotations=READ_ONLY)
    @tool_errors
    def get_shifts(file_path: str) -> dict[str, Any]:
        """Resource shift definitions (SHIFT) and their periods (SHIFTPER)."""
        sch = ctx.schedule(file_path)
        return ctx.guard(
            {
                "shifts": iso(list(sch.table("SHIFT").iter_dicts())),
                "periods": iso(list(sch.table("SHIFTPER").iter_dicts())),
            }
        )

    @mcp.tool(title="Get OBS", annotations=READ_ONLY)
    @tool_errors
    def get_obs(file_path: str, as_tree: bool = False) -> dict[str, Any]:
        """The organizational breakdown structure (OBS) used for WBS ownership."""
        sch = ctx.schedule(file_path)
        rows = list(sch.table("OBS").iter_dicts())
        if not as_tree:
            return ctx.guard({"total": len(rows), "items": iso(rows)})
        by_parent: dict[Any, list[dict[str, Any]]] = {}
        for d in rows:
            by_parent.setdefault(d.get("parent_obs_id"), []).append(d)

        def subtree(parent: Any) -> list[dict[str, Any]]:
            return [
                {**d, "children": subtree(d.get("obs_id"))}
                for d in sorted(by_parent.get(parent, []), key=lambda x: str(x.get("obs_name")))
            ]

        known = {d.get("obs_id") for d in rows}
        roots = [p for p in by_parent if p is None or p not in known]
        return ctx.guard({"total": len(rows), "tree": iso([n for p in roots for n in subtree(p)])})

    _ = (
        get_resources,
        get_resource_detail,
        get_resource_rates,
        get_resource_codes,
        get_resource_curves,
        get_roles,
        get_role_rates,
        get_role_limits,
        get_role_codes,
        get_resource_assignments,
        analyze_resource_utilization,
        get_resource_histogram,
        get_resource_leveling_report,
        get_cost_accounts,
        get_units_of_measure,
        get_currencies,
        get_shifts,
        get_obs,
    )
