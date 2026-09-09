"""§5.4 Activity tools."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.domain.activity import Activity
from p6_mcp.mcp.context import AppContext, build_activity_filter, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.services.analysis.constraints import constraints as constraints_service
from p6_mcp.services.analysis.milestones import milestones as milestones_service
from p6_mcp.services.export.tabular import to_csv, to_markdown
from p6_mcp.services.query.activities import filter_activities
from p6_mcp.services.query.serialize import activity_to_dict, iso

SORT_FIELDS = (
    "task_code",
    "task_name",
    "start",
    "finish",
    "early_start",
    "early_finish",
    "late_start",
    "late_finish",
    "total_float_days",
    "remaining_duration_days",
    "percent_complete",
    "status",
    "wbs_path",
)


def _sort_key(sch: Any) -> Any:
    def key_of(a: Activity, field: str) -> Any:
        mapping = {
            "task_code": a.code,
            "task_name": a.name,
            "start": a.start,
            "finish": a.finish,
            "early_start": a.early_start,
            "early_finish": a.early_finish,
            "late_start": a.late_start,
            "late_finish": a.late_finish,
            "total_float_days": a.total_float_hours,
            "remaining_duration_days": a.remaining_duration_hours,
            "percent_complete": a.percent_complete(),
            "status": a.status_label,
            "wbs_path": sch.wbs_path(a.wbs_id),
        }
        return mapping.get(field, a.code)

    return key_of


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register activity tools."""

    @mcp.tool(title="Get activities", annotations=READ_ONLY)
    @tool_errors
    def get_activities(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        status: list[str] | None = None,
        task_type: list[str] | None = None,
        wbs_id: int | None = None,
        wbs_path_prefix: str | None = None,
        activity_code: dict[str, str] | None = None,
        udf: dict[str, Any] | None = None,
        calendar_id: int | None = None,
        resource_id: int | None = None,
        resource_name: str | None = None,
        role_id: int | None = None,
        name_contains: str | None = None,
        code_contains: str | None = None,
        code_regex: str | None = None,
        start_after: str | None = None,
        start_before: str | None = None,
        finish_after: str | None = None,
        finish_before: str | None = None,
        float_min_days: float | None = None,
        float_max_days: float | None = None,
        remaining_duration_min_days: float | None = None,
        remaining_duration_max_days: float | None = None,
        has_constraint: bool | None = None,
        constraint_type: str | None = None,
        is_critical: bool | None = None,
        on_longest_path: bool | None = None,
        has_no_predecessors: bool | None = None,
        has_no_successors: bool | None = None,
        is_behind_schedule: bool | None = None,
        has_actuals: bool | None = None,
        sort_by: str = "task_code",
        sort_dir: str = "asc",
        limit: int = 100,
        offset: int = 0,
        fields: list[str] | None = None,
        verbosity: str = "standard",
        output_format: str = "json",
    ) -> dict[str, Any]:
        """Query activities with the full filter set; all filters combine with AND.

        This is the main workhorse. Durations and float come back in hours *and*
        calendar-aware days (using each activity's own calendar, never a fixed
        8 h/day). Use `verbosity='compact'` or `fields=[...]` to shrink results,
        and page with `limit`/`offset`.

        Status accepts "Not Started" / "In Progress" / "Completed" or the raw
        TK_* codes. task_type accepts TT_Task, TT_Mile, TT_FinMile, TT_LOE,
        TT_Rsrc, TT_WBS. activity_code is {code_type: value}; udf is
        {udf_name: value} or {udf_name: {"min": x, "max": y}}.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        flt = build_activity_filter(
            status=status,
            task_type=task_type,
            wbs_id=wbs_id,
            wbs_path_prefix=wbs_path_prefix,
            activity_code=activity_code,
            udf=udf,
            calendar_id=calendar_id,
            resource_id=resource_id,
            resource_name=resource_name,
            role_id=role_id,
            name_contains=name_contains,
            code_contains=code_contains,
            code_regex=code_regex,
            start_after=start_after,
            start_before=start_before,
            finish_after=finish_after,
            finish_before=finish_before,
            float_min_days=float_min_days,
            float_max_days=float_max_days,
            remaining_duration_min_days=remaining_duration_min_days,
            remaining_duration_max_days=remaining_duration_max_days,
            has_constraint=has_constraint,
            constraint_type=constraint_type,
            is_critical=is_critical,
            on_longest_path=on_longest_path,
            has_no_predecessors=has_no_predecessors,
            has_no_successors=has_no_successors,
            is_behind_schedule=is_behind_schedule,
            has_actuals=has_actuals,
        )
        acts = filter_activities(sch, sch.activities_of(projects), flt)
        result = ctx.page(
            acts,
            limit,
            offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
            key_of=_sort_key(sch),
            render=lambda a: activity_to_dict(sch, a, verbosity, fields),
            extra={"sortable_fields": list(SORT_FIELDS)},
        )
        return _formatted(result, output_format)

    @mcp.tool(title="Search activities", annotations=READ_ONLY)
    @tool_errors
    def search_activities(
        file_path: str,
        query: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        fuzzy: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Free-text search across activity code, name, notebook entries, and UDF
        values. Use when you know roughly what an activity is called but not its
        code. For structured filtering use get_activities instead."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        needle = query.lower().strip()
        terms = needle.split() if fuzzy else [needle]
        hits: list[tuple[int, Activity, list[str]]] = []
        for a in sch.activities_of(projects):
            haystacks = {
                "code": a.code.lower(),
                "name": a.name.lower(),
                "notes": " ".join(
                    str(m.get("memo") or "") for m in sch.memos_by_task.get(a.task_id, [])
                ).lower(),
                "udf": " ".join(
                    str(u.get("value") or "") for u in sch.task_udfs(a.task_id)
                ).lower(),
            }
            matched = [where for where, text in haystacks.items() if all(t in text for t in terms)]
            if matched:
                score = (0 if "code" in matched else 1, 0 if "name" in matched else 1)
                hits.append((score[0] * 2 + score[1], a, matched))
        hits.sort(key=lambda h: (h[0], h[1].code))
        return ctx.page(
            hits,
            limit,
            offset,
            render=lambda h: {**activity_to_dict(sch, h[1], "compact"), "matched_in": h[2]},
            extra={"query": query, "fuzzy": fuzzy},
        )

    @mcp.tool(title="Get activity detail", annotations=READ_ONLY)
    @tool_errors
    def get_activity_detail(
        file_path: str, task_code: str, project_id: int | None = None
    ) -> dict[str, Any]:
        """Everything about one activity: all TASK fields, WBS path, calendar,
        predecessors and successors with lag and driving flags, resource
        assignments, expenses, steps, activity codes, UDFs, notebooks, and
        decoded constraints.

        Accepts a task_code or a numeric task_id.
        """
        sch = ctx.schedule(file_path)
        scope = {project_id} if project_id is not None else None
        a = sch.resolve_activity(task_code, scope)
        cal = sch.calendar_for(a)

        def rel_row(r: Any, other_id: int, role: str) -> dict[str, Any]:
            other = sch.activities_by_id.get(other_id)
            return {
                role: other.code if other else other_id,
                f"{role}_name": other.name if other else None,
                "type": r.short_type,
                "lag_hours": r.lag_hours,
                "lag_days": sch.hours_to_days(a, r.lag_hours),
                "driving": bool(other and other.driving_path_flag and a.driving_path_flag),
                "relationship_float_hours": r.f("float_path"),
                "crosses_projects": r.crosses_projects,
            }

        preds = [
            rel_row(r, r.pred_task_id, "predecessor")
            for r in sch.predecessors_of.get(a.task_id, [])
        ]
        succs = [rel_row(r, r.task_id, "successor") for r in sch.successors_of.get(a.task_id, [])]
        assignments = []
        for x in sch.assignments_by_task.get(a.task_id, []):
            rsrc = sch.resources_by_id.get(x.rsrc_id) if x.rsrc_id else None
            assignments.append(
                {
                    "resource": rsrc.name if rsrc else None,
                    "resource_type": rsrc.type_label if rsrc else x.rsrc_type,
                    "budgeted_qty": x.budgeted_qty,
                    "actual_qty": x.actual_qty,
                    "remaining_qty": x.remaining_qty,
                    "budgeted_cost": round(x.budgeted_cost, 2),
                    "actual_cost": round(x.actual_cost, 2),
                    "remaining_cost": round(x.remaining_cost, 2),
                    "all_fields": x.to_dict(),
                }
            )
        primary = sch.resources_by_id.get(int(a.f("rsrc_id"))) if a.f("rsrc_id") else None
        return ctx.guard(
            {
                **activity_to_dict(sch, a, "standard"),
                "all_fields": a.to_dict(),
                "calendar": {"clndr_id": cal.clndr_id, "name": cal.name, "day_hours": cal.day_hours}
                if cal
                else None,
                "constraint": {
                    "primary": {"type": a.cstr_type, "label": a.cstr_label, "date": a.cstr_date},
                    "secondary": {"type": a.f("cstr_type2"), "date": a.date("cstr_date2")},
                    "is_hard": a.has_hard_constraint,
                },
                "duration_type": a.raw("duration_type"),
                "percent_complete_type": a.raw("complete_pct_type"),
                "primary_resource": primary.name if primary else None,
                "predecessors": sorted(preds, key=lambda d: str(d["predecessor"])),
                "successors": sorted(succs, key=lambda d: str(d["successor"])),
                "assignments": assignments,
                "expenses": sch.expenses_by_task.get(a.task_id, []),
                "steps": sch.steps_by_task.get(a.task_id, []),
                "activity_codes": sch.codes_by_task.get(a.task_id, []),
                "udfs": sch.task_udfs(a.task_id),
                "notebooks": sch.memos_by_task.get(a.task_id, []),
            }
        )

    @mcp.tool(title="Get milestones", annotations=READ_ONLY)
    @tool_errors
    def get_milestones(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        status: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Start and finish milestones with planned/early/late/actual/baseline
        dates and variance in working days."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        rows = milestones_service(sch, projects, status)
        return ctx.page(iso(rows), limit, offset)

    @mcp.tool(title="Get constraints", annotations=READ_ONLY)
    @tool_errors
    def get_constraints(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        constraint_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Constrained activities with hard/soft classification and a flag for
        constraints dated before the data date.

        Hard constraints (Mandatory Start/Finish, Start On, Finish On) override
        network logic and are what DCMA check 5 counts.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        res = constraints_service(sch, projects, constraint_type)
        rows = res.pop("constraints")
        return ctx.page(iso(rows), limit, offset, extra=iso(res))

    @mcp.tool(title="Get activity codes", annotations=READ_ONLY)
    @tool_errors
    def get_activity_codes(file_path: str, scope: str | None = None) -> dict[str, Any]:
        """Activity code types and their value hierarchy.

        `scope` filters to AS_Global, AS_EPS, or AS_Project code types.
        """
        sch = ctx.schedule(file_path)
        types = []
        for tid, d in sorted(sch.code_types_by_id.items()):
            if scope and str(d.get("actv_code_type_scope")) != scope:
                continue
            values = [
                {
                    "actv_code_id": vid,
                    "value": v.get("actv_code_name"),
                    "short_name": v.get("short_name"),
                    "parent_actv_code_id": v.get("parent_actv_code_id"),
                    "assigned_activities": len(sch.tasks_by_code_value.get(vid, [])),
                }
                for vid, v in sorted(sch.code_values_by_id.items())
                if int(v.get("actv_code_type_id") or 0) == tid
            ]
            types.append(
                {
                    "actv_code_type_id": tid,
                    "code_type": d.get("actv_code_type"),
                    "scope": d.get("actv_code_type_scope"),
                    "proj_id": d.get("proj_id"),
                    "values": values,
                }
            )
        return ctx.guard({"total": len(types), "items": iso(types)})

    @mcp.tool(title="Get activity code assignments", annotations=READ_ONLY)
    @tool_errors
    def get_activity_code_assignments(
        file_path: str, code_type: str, value: str | None = None, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        """Activities carrying a given code type (optionally a specific value)."""
        sch = ctx.schedule(file_path)
        rows = []
        for tid, codes in sch.codes_by_task.items():
            act = sch.activities_by_id.get(tid)
            if act is None:
                continue
            for c in codes:
                if str(c.get("code_type") or "").lower() != code_type.lower():
                    continue
                if value and value.lower() not in (
                    str(c.get("code_value") or "").lower(),
                    str(c.get("short_name") or "").lower(),
                ):
                    continue
                rows.append(
                    {
                        "task_code": act.code,
                        "task_name": act.name,
                        "status": act.status_label,
                        "code_type": c.get("code_type"),
                        "code_value": c.get("code_value"),
                    }
                )
        rows.sort(key=lambda d: str(d["task_code"]))
        return ctx.page(rows, limit, offset, extra={"code_type": code_type})

    @mcp.tool(title="Group activities by code", annotations=READ_ONLY)
    @tool_errors
    def group_activities_by_code(
        file_path: str,
        code_type: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
    ) -> dict[str, Any]:
        """Counts, date ranges, and status split per activity-code value.

        Good for "how much work sits under each phase/area/discipline".
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        groups: dict[str, list[Activity]] = {}
        for a in sch.activities_of(projects):
            found = [
                str(c.get("code_value"))
                for c in sch.codes_by_task.get(a.task_id, [])
                if str(c.get("code_type") or "").lower() == code_type.lower()
            ]
            for value in found or ["(unassigned)"]:
                groups.setdefault(value, []).append(a)
        out = []
        for value, acts in sorted(groups.items()):
            starts = [a.start for a in acts if a.start]
            finishes = [a.finish for a in acts if a.finish]
            out.append(
                {
                    "code_value": value,
                    "activity_count": len(acts),
                    "completed": sum(1 for a in acts if a.is_completed),
                    "in_progress": sum(1 for a in acts if a.is_in_progress),
                    "not_started": sum(1 for a in acts if a.is_not_started),
                    "earliest_start": min(starts) if starts else None,
                    "latest_finish": max(finishes) if finishes else None,
                    "critical_count": sum(
                        1 for a in acts if not a.is_completed and (a.total_float_hours or 1) <= 0
                    ),
                }
            )
        return ctx.guard({"code_type": code_type, "items": iso(out)})

    @mcp.tool(title="Get UDFs", annotations=READ_ONLY)
    @tool_errors
    def get_udfs(
        file_path: str, entity_type: str | None = None, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        """User-defined field definitions and their values.

        `entity_type` filters to TASK, PROJWBS, PROJECT, RSRC, or TASKRSRC.
        """
        sch = ctx.schedule(file_path)
        types = [
            {
                "udf_type_id": tid,
                "table": d.get("table_name"),
                "name": d.get("udf_type_name"),
                "label": d.get("udf_type_label"),
                "data_type": d.get("logical_data_type"),
            }
            for tid, d in sorted(sch.udf_types_by_id.items())
            if not entity_type or str(d.get("table_name")).upper() == entity_type.upper()
        ]
        rows = []
        for (table, fk), udfs in sch.udfs_by_entity.items():
            if entity_type and table.upper() != entity_type.upper():
                continue
            ref: Any = fk
            if table == "TASK" and fk in sch.activities_by_id:
                ref = sch.activities_by_id[fk].code
            for u in udfs:
                rows.append({"entity_table": table, "entity": ref, **u})
        rows.sort(key=lambda d: (str(d["entity_table"]), str(d["entity"])))
        return ctx.page(iso(rows), limit, offset, extra={"udf_types": iso(types)})

    @mcp.tool(title="Get activity steps", annotations=READ_ONLY)
    @tool_errors
    def get_activity_steps(file_path: str, task_code: str) -> dict[str, Any]:
        """Steps (TASKPROC) on one activity, with weights and completion flags."""
        sch = ctx.schedule(file_path)
        a = sch.resolve_activity(task_code)
        return ctx.guard({"task_code": a.code, "steps": iso(sch.steps_by_task.get(a.task_id, []))})

    @mcp.tool(title="Get activity notes", annotations=READ_ONLY)
    @tool_errors
    def get_activity_notes(
        file_path: str, task_code: str | None = None, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        """Notebook entries (TASKMEMO) with their topic names, for one activity
        or the whole file."""
        sch = ctx.schedule(file_path)
        if task_code:
            a = sch.resolve_activity(task_code)
            rows = [{"task_code": a.code, **m} for m in sch.memos_by_task.get(a.task_id, [])]
        else:
            rows = [
                {"task_code": sch.activities_by_id[tid].code, **m}
                for tid, memos in sch.memos_by_task.items()
                if tid in sch.activities_by_id
                for m in memos
            ]
            rows.sort(key=lambda d: str(d["task_code"]))
        return ctx.page(iso(rows), limit, offset)

    @mcp.tool(title="Get activity documents", annotations=READ_ONLY)
    @tool_errors
    def get_activity_documents(
        file_path: str, task_code: str | None = None, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        """Work-product and document references (TASKDOC joined to DOCUMENT)."""
        sch = ctx.schedule(file_path)
        docs = {
            int(d["doc_id"]): d
            for d in sch.table("DOCUMENT").iter_dicts()
            if d.get("doc_id") is not None
        }
        rows = []
        for d in sch.table("TASKDOC").iter_dicts():
            tid = d.get("task_id")
            act = sch.activities_by_id.get(int(tid)) if tid is not None else None
            if task_code and (act is None or act.code != task_code):
                continue
            doc = docs.get(int(d.get("doc_id") or 0), {})
            rows.append(
                {
                    "task_code": act.code if act else tid,
                    "document": doc.get("doc_name"),
                    "document_number": doc.get("doc_short_name"),
                    "location": doc.get("doc_path_name") or doc.get("doc_location"),
                    **d,
                }
            )
        return ctx.page(iso(rows), limit, offset)

    @mcp.tool(title="Get activity feedback", annotations=READ_ONLY)
    @tool_errors
    def get_activity_feedback(
        file_path: str, task_code: str | None = None, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        """Timesheet/progress feedback rows (TASKFDBK) from resources."""
        sch = ctx.schedule(file_path)
        rows = []
        for d in sch.table("TASKFDBK").iter_dicts():
            tid = d.get("task_id")
            act = sch.activities_by_id.get(int(tid)) if tid is not None else None
            if task_code and (act is None or act.code != task_code):
                continue
            rows.append({"task_code": act.code if act else tid, **d})
        return ctx.page(iso(rows), limit, offset)

    @mcp.tool(title="Get expenses", annotations=READ_ONLY)
    @tool_errors
    def get_expenses(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        task_code: str | None = None,
        cost_account: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Project expenses (PROJCOST) with budgeted/actual/remaining cost,
        vendor, PO number, and cost account."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        proj_ids = {p.proj_id for p in projects}
        accounts = {
            int(d["acct_id"]): d.get("acct_name")
            for d in sch.table("ACCOUNT").iter_dicts()
            if d.get("acct_id") is not None
        }
        rows = []
        totals = {"budgeted": 0.0, "actual": 0.0, "remaining": 0.0}
        for tid, expenses in sch.expenses_by_task.items():
            act = sch.activities_by_id.get(tid)
            if act is None or act.proj_id not in proj_ids:
                continue
            if task_code and act.code != task_code:
                continue
            for e in expenses:
                acct = accounts.get(int(e.get("acct_id") or 0))
                if cost_account and str(acct or "").lower() != cost_account.lower():
                    continue
                totals["budgeted"] += float(e.get("target_cost") or 0)
                totals["actual"] += float(e.get("act_cost") or 0)
                totals["remaining"] += float(e.get("remain_cost") or 0)
                rows.append(
                    {
                        "task_code": act.code,
                        "task_name": act.name,
                        "cost_name": e.get("cost_name"),
                        "cost_account": acct,
                        "category": e.get("cost_type"),
                        "vendor": e.get("vendor_name"),
                        "po_number": e.get("po_number"),
                        "budgeted_cost": e.get("target_cost"),
                        "actual_cost": e.get("act_cost"),
                        "remaining_cost": e.get("remain_cost"),
                    }
                )
        rows.sort(key=lambda d: (str(d["task_code"]), str(d["cost_name"])))
        return ctx.page(
            iso(rows), limit, offset, extra={"totals": {k: round(v, 2) for k, v in totals.items()}}
        )

    _ = (
        get_activities,
        search_activities,
        get_activity_detail,
        get_milestones,
        get_constraints,
        get_activity_codes,
        get_activity_code_assignments,
        group_activities_by_code,
        get_udfs,
        get_activity_steps,
        get_activity_notes,
        get_activity_documents,
        get_activity_feedback,
        get_expenses,
    )


def _formatted(result: dict[str, Any], output_format: str) -> dict[str, Any]:
    """Optionally render the envelope's items as csv or markdown."""
    if output_format == "json":
        return result
    items = result.get("items") or []
    if output_format == "csv":
        result["csv"] = to_csv(items)
    elif output_format == "markdown":
        result["markdown"] = to_markdown(items)
    if output_format in ("csv", "markdown"):
        result.pop("items", None)
    return result
