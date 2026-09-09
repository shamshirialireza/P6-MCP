"""Write a valid subset XER: keep selected projects/activities and every row
that references them, dropping rows whose owner is gone.

The output is a real XER (same header, table order, and field order as the
source) that P6 can import, not a partial dump.
"""

from __future__ import annotations

from typing import Any

from p6_mcp.domain.schedule import Schedule
from p6_mcp.parser.reader import Table, XerDocument

#: Tables filtered by proj_id (rows belonging to dropped projects are removed).
_PROJECT_SCOPED = {
    "PROJECT": "proj_id",
    "PROJWBS": "proj_id",
    "TASK": "proj_id",
    "TASKPRED": "proj_id",
    "TASKRSRC": "proj_id",
    "PROJCOST": "proj_id",
    "TASKMEMO": "proj_id",
    "TASKACTV": "proj_id",
    "TASKPROC": "proj_id",
    "TASKFIN": "proj_id",
    "TRSRCFIN": "proj_id",
    "SCHEDOPTIONS": "proj_id",
    "PROJPCAT": "proj_id",
    "PROJFUND": "proj_id",
    "PROJISSU": "proj_id",
    "PROJTHRS": "proj_id",
    "PROJEST": "proj_id",
    "WBSBUDG": "proj_id",
    "WBSMEMO": "proj_id",
    "WBSSTEP": "proj_id",
    "TASKDOC": "proj_id",
    "TASKFDBK": "proj_id",
    "TASKUSER": "proj_id",
}
#: Tables filtered by task_id.
_TASK_SCOPED = (
    "TASKPRED",
    "TASKRSRC",
    "PROJCOST",
    "TASKMEMO",
    "TASKACTV",
    "TASKPROC",
    "TASKFIN",
    "TASKDOC",
    "TASKFDBK",
    "TASKUSER",
)


def _keep_rows(table: Table, field: str, allowed: set[int]) -> list[list[str]]:
    if not table.has_field(field):
        return table.rows
    out = []
    for row in table.rows:
        v = table.value(row, field)
        if v is None or int(v) in allowed:
            out.append(row)
    return out


def build_subset(
    sch: Schedule,
    project_ids: set[int],
    task_ids: set[int] | None = None,
) -> tuple[XerDocument, dict[str, Any]]:
    """Return a new XerDocument limited to the given projects/activities.

    ``task_ids`` of None keeps every activity in the selected projects.
    Relationships are kept only when *both* endpoints survive, so the written
    file never dangles.
    """
    src = sch.doc
    out = XerDocument(
        header=src.header,
        tables={},
        encoding=src.encoding,
        line_ending=src.line_ending,
        ends_with_newline=src.ends_with_newline,
    )
    kept_tasks: set[int] = set()
    for a in sch.activities:
        if a.proj_id in project_ids and (task_ids is None or a.task_id in task_ids):
            kept_tasks.add(a.task_id)
    kept_wbs = {w.wbs_id for w in sch.wbs_nodes if w.proj_id in project_ids}

    stats: dict[str, Any] = {
        "tables": {},
        "projects": sorted(project_ids),
        "activities": len(kept_tasks),
    }
    for name, table in src.tables.items():
        new = Table(name, list(table.fields))
        rows = table.rows
        proj_field = _PROJECT_SCOPED.get(name)
        if proj_field:
            rows = _keep_rows(table, proj_field, project_ids)
        if name in _TASK_SCOPED:
            rows = [
                r for r in rows if (v := table.value(r, "task_id")) is None or int(v) in kept_tasks
            ]
        if name == "TASK":
            rows = [
                r
                for r in rows
                if (v := table.value(r, "task_id")) is not None and int(v) in kept_tasks
            ]
        if name == "TASKPRED":
            rows = [
                r
                for r in rows
                if (p := table.value(r, "pred_task_id")) is not None and int(p) in kept_tasks
            ]
        if name == "PROJWBS":
            rows = [
                r
                for r in rows
                if (v := table.value(r, "wbs_id")) is not None and int(v) in kept_wbs
            ]
        new.rows = list(rows)
        out.tables[name] = new
        if len(new.rows) != len(table.rows):
            stats["tables"][name] = {"kept": len(new.rows), "original": len(table.rows)}
    return out, stats
