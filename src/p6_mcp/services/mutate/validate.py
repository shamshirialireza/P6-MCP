"""Structural validation of a parsed XER document.

Never raises on bad content: everything is collected as a warning/error entry
so a damaged file can still be inspected. Run after every mutation.
"""

from __future__ import annotations

from typing import Any

from p6_mcp.domain.schedule import Schedule

#: (table, field) → referenced (table, key) for orphan detection.
_FOREIGN_KEYS: list[tuple[str, str, str, str]] = [
    ("TASK", "proj_id", "PROJECT", "proj_id"),
    ("TASK", "wbs_id", "PROJWBS", "wbs_id"),
    ("TASK", "clndr_id", "CALENDAR", "clndr_id"),
    ("PROJWBS", "proj_id", "PROJECT", "proj_id"),
    ("TASKPRED", "task_id", "TASK", "task_id"),
    ("TASKPRED", "pred_task_id", "TASK", "task_id"),
    ("TASKRSRC", "task_id", "TASK", "task_id"),
    ("TASKRSRC", "rsrc_id", "RSRC", "rsrc_id"),
    ("TASKRSRC", "role_id", "ROLES", "role_id"),
    ("PROJCOST", "task_id", "TASK", "task_id"),
    ("PROJCOST", "acct_id", "ACCOUNT", "acct_id"),
    ("TASKACTV", "task_id", "TASK", "task_id"),
    ("TASKACTV", "actv_code_id", "ACTVCODE", "actv_code_id"),
    ("ACTVCODE", "actv_code_type_id", "ACTVTYPE", "actv_code_type_id"),
    ("UDFVALUE", "udf_type_id", "UDFTYPE", "udf_type_id"),
    ("RSRC", "clndr_id", "CALENDAR", "clndr_id"),
    ("RSRCRATE", "rsrc_id", "RSRC", "rsrc_id"),
]
_UNIQUE_KEYS = [
    ("PROJECT", "proj_id"),
    ("TASK", "task_id"),
    ("PROJWBS", "wbs_id"),
    ("RSRC", "rsrc_id"),
    ("CALENDAR", "clndr_id"),
    ("TASKPRED", "task_pred_id"),
    ("TASKRSRC", "taskrsrc_id"),
]
_ISSUE_CAP = 50


def validate(sch: Schedule) -> dict[str, Any]:
    """Full structural report: parse warnings, orphans, duplicates, integrity."""
    doc = sch.doc
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    def add(bucket: list[dict[str, Any]], kind: str, message: str, detail: Any = None) -> None:
        if len(bucket) < _ISSUE_CAP:
            entry: dict[str, Any] = {"kind": kind, "message": message}
            if detail is not None:
                entry["detail"] = detail
            bucket.append(entry)

    for w in doc.warnings:
        add(warnings, "parse", w)

    # Required tables
    for required in ("PROJECT", "TASK"):
        if doc.table(required) is None:
            add(errors, "missing_table", f"required table {required} is absent")

    # Duplicate primary keys
    for table_name, key in _UNIQUE_KEYS:
        t = doc.table(table_name)
        if t is None or not t.has_field(key):
            continue
        seen: set[int] = set()
        dupes: set[int] = set()
        for row in t.rows:
            v = t.value(row, key)
            if v is None:
                continue
            iv = int(v)
            if iv in seen:
                dupes.add(iv)
            seen.add(iv)
        if dupes:
            add(
                errors,
                "duplicate_key",
                f"{table_name}.{key} has {len(dupes)} duplicate value(s)",
                sorted(dupes)[:10],
            )

    # Orphan foreign keys
    for table_name, field, ref_table, ref_key in _FOREIGN_KEYS:
        t, rt = doc.table(table_name), doc.table(ref_table)
        if t is None or rt is None or not t.has_field(field) or not rt.has_field(ref_key):
            continue
        valid = {int(v) for row in rt.rows if (v := rt.value(row, ref_key)) is not None}
        orphans: set[int] = set()
        for row in t.rows:
            v = t.value(row, field)
            if v is not None and int(v) not in valid:
                orphans.add(int(v))
        if orphans:
            add(
                warnings,
                "orphan_reference",
                f"{table_name}.{field} references {len(orphans)} missing "
                f"{ref_table}.{ref_key} value(s)",
                sorted(orphans)[:10],
            )

    # Schedule-semantics checks
    for a in sch.activities:
        if a.is_completed and a.act_finish is None:
            add(warnings, "data_integrity", f"{a.code} is Completed but has no actual finish")
        if a.is_not_started and a.act_start is not None:
            add(warnings, "data_integrity", f"{a.code} is Not Started but has an actual start")
        if a.start and a.finish and a.finish < a.start:
            add(errors, "data_integrity", f"{a.code} finishes before it starts")
    for r in sch.relationships:
        if r.pred_task_id == r.task_id:
            act = sch.activities_by_id.get(r.task_id)
            add(
                errors, "data_integrity", f"{act.code if act else r.task_id} is its own predecessor"
            )
    for c in sch.calendars:
        if c.used_fallback_workweek:
            add(
                warnings,
                "calendar",
                f"calendar {c.name!r} has no parsable workweek; "
                "a Mon-Fri 08:00-16:00 fallback is being used",
            )

    return {
        "valid": not errors,
        "encoding": doc.encoding,
        "table_count": len(doc.tables),
        "row_count": sum(len(t.rows) for t in doc.tables.values()),
        "unknown_tables": sorted(t.name for t in doc.tables.values() if not t.is_known),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }
