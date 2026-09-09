"""File-level operations: merge, split, and baseline copy."""

from __future__ import annotations

import copy
from typing import Any

from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import MutationError, NotFoundError
from p6_mcp.parser.reader import Table, XerDocument
from p6_mcp.services.export.xer_subset import build_subset

#: Primary-key column per table, used to detect collisions when merging.
_PRIMARY_KEYS = {
    "PROJECT": "proj_id",
    "PROJWBS": "wbs_id",
    "TASK": "task_id",
    "TASKPRED": "task_pred_id",
    "TASKRSRC": "taskrsrc_id",
    "RSRC": "rsrc_id",
    "CALENDAR": "clndr_id",
    "ROLES": "role_id",
    "ACCOUNT": "acct_id",
    "ACTVTYPE": "actv_code_type_id",
    "ACTVCODE": "actv_code_id",
    "UDFTYPE": "udf_type_id",
    "PROJCOST": "cost_item_id",
    "OBS": "obs_id",
    "CURRTYPE": "curr_id",
    "UMEASURE": "unit_id",
    "MEMOTYPE": "memo_type_id",
}


def merge_documents(schedules: list[Schedule]) -> tuple[XerDocument, dict[str, Any]]:
    """Merge several XER files into one document.

    Rows whose primary key already exists are skipped (first file wins), and
    the skip is reported — p6-mcp never silently renumbers IDs, because doing
    so would break every cross-table reference in the incoming file.
    """
    if not schedules:
        raise MutationError("merge requires at least one file")
    base = schedules[0]
    out = XerDocument(
        header=base.doc.header,
        tables={},
        encoding=base.doc.encoding,
        line_ending=base.doc.line_ending,
        ends_with_newline=base.doc.ends_with_newline,
    )
    for name, table in base.doc.tables.items():
        new = Table(name, list(table.fields))
        new.rows = [list(r) for r in table.rows]
        out.tables[name] = new

    stats: dict[str, Any] = {
        "files_merged": len(schedules),
        "rows_added": {},
        "rows_skipped": {},
        "conflicts": [],
    }
    for sch in schedules[1:]:
        for name, table in sch.doc.tables.items():
            target = out.tables.get(name)
            if target is None:
                target = Table(name, list(table.fields))
                out.tables[name] = target
            if target.fields != table.fields:
                # Different field sets: map by name so nothing lands in the
                # wrong column.
                pass
            pk = _PRIMARY_KEYS.get(name)
            existing_keys: set[int] = set()
            if pk and target.has_field(pk):
                existing_keys = {
                    int(v) for r in target.rows if (v := target.value(r, pk)) is not None
                }
            # Tables with no primary key (TASKACTV, UDFVALUE, RSRCRATE...) are
            # deduplicated on the whole row, so re-merging the same file is a
            # no-op instead of doubling every association row.
            existing_rows: set[tuple[str, ...]] = set() if pk else {tuple(r) for r in target.rows}
            added = skipped = 0
            for row in table.rows:
                if pk and table.has_field(pk):
                    v = table.value(row, pk)
                    if v is not None and int(v) in existing_keys:
                        skipped += 1
                        if name == "PROJECT":
                            stats["conflicts"].append(
                                f"PROJECT proj_id={int(v)} already present; "
                                "row from later file skipped"
                            )
                        continue
                    if v is not None:
                        existing_keys.add(int(v))
                new_row = [""] * len(target.fields)
                for i, fname in enumerate(target.fields):
                    if table.has_field(fname):
                        new_row[i] = table.raw(row, fname)
                if not pk:
                    key = tuple(new_row)
                    if key in existing_rows:
                        skipped += 1
                        continue
                    existing_rows.add(key)
                target.rows.append(new_row)
                added += 1
            if added:
                stats["rows_added"][name] = stats["rows_added"].get(name, 0) + added
            if skipped:
                stats["rows_skipped"][name] = stats["rows_skipped"].get(name, 0) + skipped
    return out, stats


def split_by_project(sch: Schedule) -> list[tuple[str, XerDocument, dict[str, Any]]]:
    """One document per non-baseline project (baselines travel with their parent)."""
    out: list[tuple[str, XerDocument, dict[str, Any]]] = []
    for proj in sch.active_projects or sch.projects:
        ids = {proj.proj_id}
        for bp in sch.baseline_projects:
            if bp.orig_proj_id == proj.proj_id or proj.sum_base_proj_id == bp.proj_id:
                ids.add(bp.proj_id)
        doc, stats = build_subset(sch, ids)
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in proj.short_name)
        out.append((f"{safe or proj.proj_id}.xer", doc, stats))
    return out


def create_baseline_copy(sch: Schedule, proj_id: int) -> tuple[XerDocument, dict[str, Any]]:
    """Duplicate a project as a baseline (project_flag='N', linked via orig_proj_id).

    All IDs in the copy are offset so the baseline coexists with its source in
    one file, exactly as a P6 "save as baseline" export would.
    """
    proj = sch.projects_by_id.get(proj_id)
    if proj is None:
        raise NotFoundError(f"No project with proj_id={proj_id}")
    doc = copy.deepcopy(sch.doc)
    offset = _id_offset(doc)
    scoped = {
        "PROJECT": ("proj_id",),
        "PROJWBS": ("wbs_id", "proj_id", "parent_wbs_id"),
        "TASK": ("task_id", "proj_id", "wbs_id"),
        "TASKPRED": ("task_pred_id", "task_id", "pred_task_id", "proj_id", "pred_proj_id"),
        "TASKRSRC": ("taskrsrc_id", "task_id", "proj_id"),
        "PROJCOST": ("cost_item_id", "task_id", "proj_id"),
        "TASKACTV": ("task_id", "proj_id"),
        "TASKMEMO": ("memo_id", "task_id", "proj_id"),
        "TASKPROC": ("proc_id", "task_id", "proj_id"),
        "SCHEDOPTIONS": ("schedoptions_id", "proj_id"),
    }
    counts: dict[str, int] = {}
    for name, fields in scoped.items():
        table = doc.table(name)
        if table is None or not table.has_field("proj_id"):
            continue
        clones = []
        for row in list(table.rows):
            v = table.value(row, "proj_id")
            if v is None or int(v) != proj_id:
                continue
            clone = list(row)
            for fname in fields:
                if not table.has_field(fname):
                    continue
                old = table.value(clone, fname)
                if old is not None:
                    table.set(clone, fname, int(old) + offset)
            if name == "PROJECT":
                table.set(clone, "project_flag", False)
                if table.has_field("orig_proj_id"):
                    table.set(clone, "orig_proj_id", proj_id)
                if table.has_field("proj_short_name"):
                    base = table.raw(clone, "proj_short_name")
                    table.set(clone, "proj_short_name", f"{base}-BL"[:40])
                if table.has_field("sum_base_proj_id"):
                    table.set(clone, "sum_base_proj_id", None)
            clones.append(clone)
        table.rows.extend(clones)
        if clones:
            counts[name] = len(clones)
    # Point the source project at its new baseline.
    proj_table = doc.table("PROJECT")
    if proj_table is not None and proj_table.has_field("sum_base_proj_id"):
        for row in proj_table.rows:
            v = proj_table.value(row, "proj_id")
            if v is not None and int(v) == proj_id:
                proj_table.set(row, "sum_base_proj_id", proj_id + offset)
                break
    return doc, {
        "source_proj_id": proj_id,
        "baseline_proj_id": proj_id + offset,
        "id_offset": offset,
        "rows_copied": counts,
    }


def _id_offset(doc: XerDocument) -> int:
    """An offset larger than every ID in the file, rounded for readability."""
    biggest = 0
    for table in doc.tables.values():
        for fname in table.fields:
            if not fname.endswith("_id"):
                continue
            for row in table.rows:
                v = table.value(row, fname)
                if isinstance(v, (int, float)) and v > biggest:
                    biggest = int(v)
    return max(10 ** (len(str(biggest))), 1000)
