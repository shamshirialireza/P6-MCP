"""Named datasets: Schedule → list of flat rows, ready for any tabular exporter."""

from __future__ import annotations

from typing import Any

from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import InvalidArgumentError, NotFoundError
from p6_mcp.services.query.activities import ActivityFilter, filter_activities
from p6_mcp.services.query.serialize import (
    activity_to_dict,
    assignment_to_dict,
    calendar_to_dict,
    iso,
    relationship_to_dict,
    resource_to_dict,
    wbs_to_dict,
)

DATASETS = (
    "activities",
    "relationships",
    "assignments",
    "wbs",
    "resources",
    "calendars",
    "codes",
    "udfs",
    "expenses",
    "projects",
    "raw_table",
)


def build_dataset(
    sch: Schedule,
    projects: list[Project],
    dataset: str,
    flt: ActivityFilter | None = None,
    table_name: str | None = None,
    verbosity: str = "standard",
) -> list[dict[str, Any]]:
    """Materialize a named dataset as flat rows (deterministic order)."""
    proj_ids = {p.proj_id for p in projects}
    if dataset == "activities":
        acts = sch.activities_of(projects)
        if flt is not None:
            acts = filter_activities(sch, acts, flt)
        return [activity_to_dict(sch, a, verbosity) for a in sorted(acts, key=lambda a: a.code)]
    if dataset == "relationships":
        rels = [r for r in sch.relationships if r.proj_id in proj_ids or r.pred_proj_id in proj_ids]
        rows = [relationship_to_dict(sch, r) for r in rels]
        return sorted(rows, key=lambda d: (str(d["predecessor"]), str(d["successor"])))
    if dataset == "assignments":
        xs = [x for x in sch.assignments if x.proj_id in proj_ids]
        rows = [assignment_to_dict(sch, x, verbosity) for x in xs]
        return sorted(rows, key=lambda d: (str(d["task_code"]), str(d["resource"])))
    if dataset == "wbs":
        nodes = [w for w in sch.wbs_nodes if w.proj_id in proj_ids]
        rows = [wbs_to_dict(sch, w, verbosity) for w in nodes]
        return sorted(rows, key=lambda d: str(d["path"]))
    if dataset == "resources":
        rows = [resource_to_dict(sch, r, verbosity) for r in sch.resources]
        return sorted(rows, key=lambda d: str(d["rsrc_name"]))
    if dataset == "calendars":
        rows = [calendar_to_dict(sch, c) for c in sch.calendars]
        return sorted(rows, key=lambda d: str(d["clndr_name"]))
    if dataset == "codes":
        rows: list[dict[str, Any]] = []
        for tid, codes in sch.codes_by_task.items():
            act = sch.activities_by_id.get(tid)
            if act is None or act.proj_id not in proj_ids:
                continue
            for c in codes:
                rows.append({"task_code": act.code, "task_name": act.name, **c})
        return sorted(rows, key=lambda d: (str(d["task_code"]), str(d["code_type"])))
    if dataset == "udfs":
        rows = []
        for (table, fk), udfs in sch.udfs_by_entity.items():
            for u in udfs:
                entity_ref: str | int = fk
                if table == "TASK" and fk in sch.activities_by_id:
                    act = sch.activities_by_id[fk]
                    if act.proj_id not in proj_ids:
                        continue
                    entity_ref = act.code
                rows.append({"entity_table": table, "entity": entity_ref, **u})
        return sorted(
            rows, key=lambda d: (str(d["entity_table"]), str(d["entity"]), str(d.get("name")))
        )
    if dataset == "expenses":
        rows = []
        for tid, expenses in sch.expenses_by_task.items():
            act = sch.activities_by_id.get(tid)
            if act is None or act.proj_id not in proj_ids:
                continue
            for e in expenses:
                rows.append(
                    iso(
                        {
                            "task_code": act.code,
                            "task_name": act.name,
                            "cost_name": e.get("cost_name"),
                            "cost_type": e.get("cost_type"),
                            "vendor": e.get("vendor_name"),
                            "po_number": e.get("po_number"),
                            "budgeted_cost": e.get("target_cost"),
                            "actual_cost": e.get("act_cost"),
                            "remaining_cost": e.get("remain_cost"),
                        }
                    )
                )
        return sorted(rows, key=lambda d: (str(d["task_code"]), str(d["cost_name"])))
    if dataset == "projects":
        from p6_mcp.services.query.serialize import project_to_dict

        return [project_to_dict(sch, p, verbosity) for p in sch.projects]
    if dataset == "raw_table":
        if not table_name:
            raise InvalidArgumentError(
                "dataset='raw_table' requires table_name",
                hint="Call get_table_inventory to list available tables.",
            )
        t = sch.doc.table(table_name)
        if t is None:
            raise NotFoundError(
                f"No table {table_name!r} in this file",
                hint="Call get_table_inventory to list available tables.",
            )
        return [iso(t.row_dict(row)) for row in t.rows]
    raise InvalidArgumentError(f"Unknown dataset {dataset!r}", hint=f"Use one of {DATASETS}")
