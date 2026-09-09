"""ScheduleEditor: safe, auditable edits to a parsed XER document.

Design (ADR-0004): the editor never mutates the cached Schedule. It deep-copies
the document, applies changes to the copy, and records a change summary. The
caller decides where to write. Field writes go through ``Table.set`` so values
are re-serialized in P6's own format.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import MutationError, NotFoundError
from p6_mcp.parser.coercion import parse_date
from p6_mcp.parser.reader import Table, XerDocument
from p6_mcp.services.query.serialize import iso

#: Friendly aliases → real TASK column names.
ACTIVITY_FIELD_ALIASES = {
    "name": "task_name",
    "task_name": "task_name",
    "status": "status_code",
    "status_code": "status_code",
    "task_type": "task_type",
    "type": "task_type",
    "wbs_id": "wbs_id",
    "calendar_id": "clndr_id",
    "clndr_id": "clndr_id",
    "duration_hours": "target_drtn_hr_cnt",
    "original_duration_hours": "target_drtn_hr_cnt",
    "remaining_duration_hours": "remain_drtn_hr_cnt",
    "actual_start": "act_start_date",
    "act_start_date": "act_start_date",
    "actual_finish": "act_end_date",
    "act_end_date": "act_end_date",
    "early_start": "early_start_date",
    "early_finish": "early_end_date",
    "planned_start": "target_start_date",
    "planned_finish": "target_end_date",
    "constraint_type": "cstr_type",
    "cstr_type": "cstr_type",
    "constraint_date": "cstr_date",
    "cstr_date": "cstr_date",
    "physical_percent": "phys_complete_pct",
    "phys_complete_pct": "phys_complete_pct",
    "percent_complete_type": "complete_pct_type",
    "total_float_hours": "total_float_hr_cnt",
}

_STATUS_VALUES = {"TK_NotStart", "TK_Active", "TK_Complete"}
_TASK_TYPES = {"TT_Task", "TT_Rsrc", "TT_Mile", "TT_FinMile", "TT_LOE", "TT_WBS"}
_DATE_FIELDS = {
    "act_start_date",
    "act_end_date",
    "early_start_date",
    "early_end_date",
    "late_start_date",
    "late_end_date",
    "target_start_date",
    "target_end_date",
    "cstr_date",
    "cstr_date2",
    "restart_date",
    "reend_date",
}


@dataclass(slots=True)
class ChangeSummary:
    """An audit trail of everything an editor session changed."""

    changes: list[dict[str, Any]] = field(default_factory=list)

    def record(self, action: str, target: str, detail: dict[str, Any]) -> None:
        self.changes.append({"action": action, "target": target, **iso(detail)})

    @property
    def count(self) -> int:
        return len(self.changes)

    def to_dict(self) -> dict[str, Any]:
        return {"change_count": self.count, "changes": self.changes}


class ScheduleEditor:
    """Applies edits to a private copy of a schedule's document."""

    def __init__(self, schedule: Schedule) -> None:
        self.doc: XerDocument = copy.deepcopy(schedule.doc)
        self.schedule = Schedule(self.doc, schedule.schedule_id)
        self.summary = ChangeSummary()

    # -- helpers -----------------------------------------------------------

    def _table(self, name: str) -> Table:
        t = self.doc.table(name)
        if t is None:
            raise MutationError(
                f"This file has no {name} table",
                hint="The XER must already contain the table being edited.",
            )
        return t

    def _next_id(self, table: Table, field_name: str) -> int:
        existing = [int(v) for row in table.rows if (v := table.value(row, field_name)) is not None]
        return (max(existing) + 1) if existing else 1

    @staticmethod
    def _coerce(field_name: str, value: Any) -> Any:
        if field_name in _DATE_FIELDS and isinstance(value, str):
            parsed = parse_date(value)
            if parsed is None and value.strip():
                raise MutationError(
                    f"Cannot parse {value!r} as a date for {field_name}",
                    hint="Use 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'.",
                )
            return parsed
        return value

    @staticmethod
    def _validate(field_name: str, value: Any) -> None:
        if field_name == "status_code" and value not in _STATUS_VALUES:
            raise MutationError(
                f"Invalid status_code {value!r}",
                hint=f"Use one of {sorted(_STATUS_VALUES)}",
            )
        if field_name == "task_type" and value not in _TASK_TYPES:
            raise MutationError(
                f"Invalid task_type {value!r}", hint=f"Use one of {sorted(_TASK_TYPES)}"
            )
        if field_name in ("target_drtn_hr_cnt", "remain_drtn_hr_cnt") and (
            not isinstance(value, (int, float)) or value < 0
        ):
            raise MutationError(f"{field_name} must be a non-negative number, got {value!r}")

    # -- activities --------------------------------------------------------

    def update_activity(self, task_ref: str, changes: dict[str, Any]) -> dict[str, Any]:
        """Apply field changes to one activity; returns before/after values."""
        act = self.schedule.resolve_activity(task_ref)
        table = self._table("TASK")
        before: dict[str, Any] = {}
        after: dict[str, Any] = {}
        for key, raw_value in changes.items():
            fname = ACTIVITY_FIELD_ALIASES.get(key, key)
            if not table.has_field(fname):
                raise MutationError(
                    f"TASK has no field {fname!r} (from {key!r})",
                    hint=f"Known aliases: {sorted(ACTIVITY_FIELD_ALIASES)}",
                )
            value = self._coerce(fname, raw_value)
            self._validate(fname, value)
            before[fname] = act.f(fname)
            act.set(fname, value)
            after[fname] = act.f(fname)
        self.summary.record("update_activity", act.code, {"before": before, "after": after})
        return iso({"task_code": act.code, "before": before, "after": after})

    def add_activity(
        self,
        proj_id: int,
        wbs_id: int,
        task_code: str,
        task_name: str,
        duration_hours: float = 0.0,
        task_type: str = "TT_Task",
        clndr_id: int | None = None,
    ) -> dict[str, Any]:
        """Append a new TASK row with sensible defaults for required fields."""
        table = self._table("TASK")
        if self.schedule.activities_by_code.get(task_code):
            raise MutationError(
                f"Activity code {task_code!r} already exists",
                hint="Activity codes must be unique within the file.",
            )
        if wbs_id not in self.schedule.wbs_by_id:
            raise NotFoundError(f"No WBS node with wbs_id={wbs_id}")
        task_id = self._next_id(table, "task_id")
        proj = self.schedule.projects_by_id.get(proj_id)
        row = [""] * len(table.fields)
        defaults: dict[str, Any] = {
            "task_id": task_id,
            "proj_id": proj_id,
            "wbs_id": wbs_id,
            "clndr_id": clndr_id or (proj.clndr_id if proj else None),
            "task_code": task_code,
            "task_name": task_name,
            "task_type": task_type,
            "status_code": "TK_NotStart",
            "duration_type": "DT_FixedDrtn",
            "complete_pct_type": "CP_Drtn",
            "target_drtn_hr_cnt": duration_hours,
            "remain_drtn_hr_cnt": duration_hours,
            "phys_complete_pct": 0,
            "total_float_hr_cnt": 0,
            "create_date": datetime.now().replace(microsecond=0),
            "create_user": "p6-mcp",
        }
        for fname, value in defaults.items():
            if table.has_field(fname):
                table.set(row, fname, value)
        table.rows.append(row)
        self._invalidate()
        self.summary.record(
            "add_activity", task_code, {"task_id": task_id, "proj_id": proj_id, "wbs_id": wbs_id}
        )
        return {"task_code": task_code, "task_id": task_id}

    def delete_activity(self, task_ref: str, cascade: bool = True) -> dict[str, Any]:
        """Remove an activity and (optionally) every row that references it."""
        act = self.schedule.resolve_activity(task_ref)
        tid = act.task_id
        removed: dict[str, int] = {}
        rels = len(self.schedule.predecessors_of.get(tid, [])) + len(
            self.schedule.successors_of.get(tid, [])
        )
        if rels and not cascade:
            raise MutationError(
                f"{act.code} still has {rels} relationships",
                hint="Pass cascade=True to remove dependent rows too.",
            )
        task_table = self._table("TASK")
        task_table.rows = [r for r in task_table.rows if r is not act.row]
        removed["TASK"] = 1
        if cascade:
            for name, fields in (
                ("TASKPRED", ("task_id", "pred_task_id")),
                ("TASKRSRC", ("task_id",)),
                ("PROJCOST", ("task_id",)),
                ("TASKACTV", ("task_id",)),
                ("TASKMEMO", ("task_id",)),
                ("TASKPROC", ("task_id",)),
            ):
                t = self.doc.table(name)
                if t is None:
                    continue
                before = len(t.rows)
                t.rows = [
                    r
                    for r in t.rows
                    if not any(
                        t.has_field(f) and (v := t.value(r, f)) is not None and int(v) == tid
                        for f in fields
                    )
                ]
                if before != len(t.rows):
                    removed[name] = before - len(t.rows)
        self._invalidate()
        self.summary.record("delete_activity", act.code, {"removed_rows": removed})
        return {"task_code": act.code, "removed_rows": removed}

    # -- relationships -----------------------------------------------------

    def add_relationship(
        self,
        pred_ref: str,
        succ_ref: str,
        pred_type: str = "PR_FS",
        lag_hours: float = 0.0,
    ) -> dict[str, Any]:
        pred = self.schedule.resolve_activity(pred_ref)
        succ = self.schedule.resolve_activity(succ_ref)
        if pred.task_id == succ.task_id:
            raise MutationError("An activity cannot be its own predecessor")
        if pred_type not in ("PR_FS", "PR_SS", "PR_FF", "PR_SF"):
            raise MutationError(
                f"Invalid pred_type {pred_type!r}",
                hint="Use PR_FS, PR_SS, PR_FF, or PR_SF.",
            )
        table = self._table("TASKPRED")
        for r in self.schedule.predecessors_of.get(succ.task_id, []):
            if r.pred_task_id == pred.task_id and r.pred_type == pred_type:
                raise MutationError(
                    f"{pred.code} -> {succ.code} ({pred_type.removeprefix('PR_')}) already exists",
                    hint="Use update_relationship to change its lag.",
                )
        rel_id = self._next_id(table, "task_pred_id")
        row = [""] * len(table.fields)
        for fname, value in {
            "task_pred_id": rel_id,
            "task_id": succ.task_id,
            "pred_task_id": pred.task_id,
            "proj_id": succ.proj_id,
            "pred_proj_id": pred.proj_id,
            "pred_type": pred_type,
            "lag_hr_cnt": lag_hours,
        }.items():
            if table.has_field(fname):
                table.set(row, fname, value)
        table.rows.append(row)
        self._invalidate()
        self.summary.record(
            "add_relationship",
            f"{pred.code}->{succ.code}",
            {"type": pred_type, "lag_hours": lag_hours},
        )
        return {
            "predecessor": pred.code,
            "successor": succ.code,
            "type": pred_type,
            "lag_hours": lag_hours,
        }

    def _find_relationship(self, pred_ref: str, succ_ref: str) -> Any:
        pred = self.schedule.resolve_activity(pred_ref)
        succ = self.schedule.resolve_activity(succ_ref)
        for r in self.schedule.predecessors_of.get(succ.task_id, []):
            if r.pred_task_id == pred.task_id:
                return pred, succ, r
        raise NotFoundError(
            f"No relationship {pred.code} -> {succ.code}",
            hint="Call get_relationships to list existing links.",
        )

    def remove_relationship(self, pred_ref: str, succ_ref: str) -> dict[str, Any]:
        pred, succ, rel = self._find_relationship(pred_ref, succ_ref)
        table = self._table("TASKPRED")
        table.rows = [r for r in table.rows if r is not rel.row]
        self._invalidate()
        self.summary.record(
            "remove_relationship", f"{pred.code}->{succ.code}", {"type": rel.pred_type}
        )
        return {"predecessor": pred.code, "successor": succ.code, "removed": True}

    def update_relationship(
        self,
        pred_ref: str,
        succ_ref: str,
        pred_type: str | None = None,
        lag_hours: float | None = None,
    ) -> dict[str, Any]:
        pred, succ, rel = self._find_relationship(pred_ref, succ_ref)
        before = {"type": rel.pred_type, "lag_hours": rel.lag_hours}
        if pred_type is not None:
            if pred_type not in ("PR_FS", "PR_SS", "PR_FF", "PR_SF"):
                raise MutationError(f"Invalid pred_type {pred_type!r}")
            rel.set("pred_type", pred_type)
        if lag_hours is not None:
            rel.set("lag_hr_cnt", lag_hours)
        after = {"type": rel.pred_type, "lag_hours": rel.lag_hours}
        self.summary.record(
            "update_relationship", f"{pred.code}->{succ.code}", {"before": before, "after": after}
        )
        return {"predecessor": pred.code, "successor": succ.code, "before": before, "after": after}

    # -- assignments -------------------------------------------------------

    def assign_resource(
        self,
        task_ref: str,
        rsrc_ref: str | int,
        budgeted_qty: float,
        cost_per_qty: float | None = None,
    ) -> dict[str, Any]:
        act = self.schedule.resolve_activity(task_ref)
        rsrc = self.schedule.resolve_resource(rsrc_ref)
        table = self._table("TASKRSRC")
        rate = cost_per_qty
        if rate is None:
            rates = self.schedule.rates_by_rsrc.get(rsrc.rsrc_id, [])
            rate = float(rates[-1].get("cost_per_qty") or 0) if rates else 0.0
        aid = self._next_id(table, "taskrsrc_id")
        row = [""] * len(table.fields)
        for fname, value in {
            "taskrsrc_id": aid,
            "task_id": act.task_id,
            "proj_id": act.proj_id,
            "rsrc_id": rsrc.rsrc_id,
            "role_id": rsrc.f("role_id"),
            "rsrc_type": rsrc.rsrc_type,
            "target_qty": budgeted_qty,
            "remain_qty": budgeted_qty,
            "act_reg_qty": 0,
            "act_ot_qty": 0,
            "cost_per_qty": rate,
            "target_cost": budgeted_qty * rate,
            "remain_cost": budgeted_qty * rate,
            "act_reg_cost": 0,
            "act_ot_cost": 0,
            "target_start_date": act.planned_start or act.start,
            "target_end_date": act.planned_finish or act.finish,
            "cost_qty_link_flag": True,
            "rate_type": "COST_PER_QTY",
        }.items():
            if table.has_field(fname):
                table.set(row, fname, value)
        table.rows.append(row)
        self._invalidate()
        self.summary.record(
            "assign_resource",
            act.code,
            {"resource": rsrc.name, "qty": budgeted_qty, "cost": budgeted_qty * rate},
        )
        return {
            "task_code": act.code,
            "resource": rsrc.name,
            "budgeted_qty": budgeted_qty,
            "budgeted_cost": budgeted_qty * rate,
        }

    def remove_assignment(self, task_ref: str, rsrc_ref: str | int) -> dict[str, Any]:
        act = self.schedule.resolve_activity(task_ref)
        rsrc = self.schedule.resolve_resource(rsrc_ref)
        table = self._table("TASKRSRC")
        targets = [
            x.row
            for x in self.schedule.assignments_by_task.get(act.task_id, [])
            if x.rsrc_id == rsrc.rsrc_id
        ]
        if not targets:
            raise NotFoundError(f"{rsrc.name} is not assigned to {act.code}")
        table.rows = [r for r in table.rows if r not in targets]
        self._invalidate()
        self.summary.record("remove_assignment", act.code, {"resource": rsrc.name})
        return {"task_code": act.code, "resource": rsrc.name, "removed": len(targets)}

    def update_assignment(
        self, task_ref: str, rsrc_ref: str | int, changes: dict[str, Any]
    ) -> dict[str, Any]:
        act = self.schedule.resolve_activity(task_ref)
        rsrc = self.schedule.resolve_resource(rsrc_ref)
        matches = [
            x
            for x in self.schedule.assignments_by_task.get(act.task_id, [])
            if x.rsrc_id == rsrc.rsrc_id
        ]
        if not matches:
            raise NotFoundError(f"{rsrc.name} is not assigned to {act.code}")
        asg = matches[0]
        aliases = {
            "budgeted_qty": "target_qty",
            "remaining_qty": "remain_qty",
            "budgeted_cost": "target_cost",
            "remaining_cost": "remain_cost",
            "cost_per_qty": "cost_per_qty",
            "actual_qty": "act_reg_qty",
            "actual_cost": "act_reg_cost",
        }
        before, after = {}, {}
        for key, value in changes.items():
            fname = aliases.get(key, key)
            before[fname] = asg.f(fname)
            asg.set(fname, self._coerce(fname, value))
            after[fname] = asg.f(fname)
        self.summary.record(
            "update_assignment", act.code, {"resource": rsrc.name, "before": before, "after": after}
        )
        return iso({"task_code": act.code, "resource": rsrc.name, "before": before, "after": after})

    # -- project & progress ------------------------------------------------

    def update_project(self, proj_id: int, changes: dict[str, Any]) -> dict[str, Any]:
        proj = self.schedule.projects_by_id.get(proj_id)
        if proj is None:
            raise NotFoundError(f"No project with proj_id={proj_id}")
        table = self._table("PROJECT")
        aliases = {"data_date": "last_recalc_date", "name": "proj_short_name"}
        before, after = {}, {}
        for key, value in changes.items():
            fname = aliases.get(key, key)
            if not table.has_field(fname):
                raise MutationError(f"PROJECT has no field {fname!r}")
            before[fname] = proj.f(fname)
            coerced = value
            if fname.endswith("_date") and isinstance(value, str):
                coerced = self._coerce("cstr_date", value)
            proj.set(fname, coerced)
            after[fname] = proj.f(fname)
        self.summary.record("update_project", proj.short_name, {"before": before, "after": after})
        return iso({"proj_id": proj_id, "before": before, "after": after})

    def apply_progress(
        self,
        updates: list[dict[str, Any]],
        new_data_date: str | datetime | None = None,
        proj_id: int | None = None,
    ) -> dict[str, Any]:
        """Status a batch of activities and optionally advance the data date."""
        applied: list[dict[str, Any]] = []
        for upd in updates:
            code = upd.get("task_code")
            if not code:
                raise MutationError("Each progress update needs a task_code")
            changes: dict[str, Any] = {}
            if (v := upd.get("actual_start")) is not None:
                changes["act_start_date"] = v
            if (v := upd.get("actual_finish")) is not None:
                changes["act_end_date"] = v
            if (v := upd.get("remaining_duration")) is not None:
                changes["remain_drtn_hr_cnt"] = v
            if (v := upd.get("pct")) is not None:
                changes["phys_complete_pct"] = v
            act = self.schedule.resolve_activity(str(code))
            if upd.get("actual_finish"):
                changes["status_code"] = "TK_Complete"
                changes.setdefault("remain_drtn_hr_cnt", 0)
            elif upd.get("actual_start") and act.is_not_started:
                changes["status_code"] = "TK_Active"
            applied.append(self.update_activity(str(code), changes))
        if new_data_date is not None:
            targets = (
                [proj_id]
                if proj_id is not None
                else [p.proj_id for p in self.schedule.active_projects]
            )
            for pid in targets:
                self.update_project(pid, {"last_recalc_date": new_data_date})
        return {"applied": len(applied), "activities": applied, "new_data_date": iso(new_data_date)}

    # -- codes & UDFs ------------------------------------------------------

    def set_activity_code(self, task_ref: str, code_type: str, code_value: str) -> dict[str, Any]:
        act = self.schedule.resolve_activity(task_ref)
        type_id = next(
            (
                tid
                for tid, d in self.schedule.code_types_by_id.items()
                if str(d.get("actv_code_type") or "").lower() == code_type.lower()
            ),
            None,
        )
        if type_id is None:
            raise NotFoundError(
                f"No activity code type {code_type!r}",
                hint="Call get_activity_codes to list code types.",
            )
        value_id = next(
            (
                vid
                for vid, d in self.schedule.code_values_by_id.items()
                if int(d.get("actv_code_type_id") or 0) == type_id
                and code_value.lower()
                in (
                    str(d.get("actv_code_name") or "").lower(),
                    str(d.get("short_name") or "").lower(),
                )
            ),
            None,
        )
        if value_id is None:
            raise NotFoundError(f"No value {code_value!r} in code type {code_type!r}")
        table = self._table("TASKACTV")
        table.rows = [
            r
            for r in table.rows
            if not (
                (t := table.value(r, "task_id")) is not None
                and int(t) == act.task_id
                and (ct := table.value(r, "actv_code_type_id")) is not None
                and int(ct) == type_id
            )
        ]
        row = [""] * len(table.fields)
        for fname, value in {
            "task_id": act.task_id,
            "actv_code_type_id": type_id,
            "actv_code_id": value_id,
            "proj_id": act.proj_id,
        }.items():
            if table.has_field(fname):
                table.set(row, fname, value)
        table.rows.append(row)
        self._invalidate()
        self.summary.record(
            "set_activity_code", act.code, {"code_type": code_type, "value": code_value}
        )
        return {"task_code": act.code, "code_type": code_type, "value": code_value}

    def set_udf_value(
        self, entity_table: str, entity_ref: str | int, udf_name: str, value: Any
    ) -> dict[str, Any]:
        types = {
            tid: d
            for tid, d in self.schedule.udf_types_by_id.items()
            if str(d.get("table_name") or "").upper() == entity_table.upper()
        }
        match = next(
            (
                (tid, d)
                for tid, d in types.items()
                if udf_name.lower()
                in (
                    str(d.get("udf_type_name") or "").lower(),
                    str(d.get("udf_type_label") or "").lower(),
                )
            ),
            None,
        )
        if match is None:
            raise NotFoundError(
                f"No UDF {udf_name!r} on {entity_table}",
                hint="Call get_udfs to list user-defined fields.",
            )
        type_id, tdef = match
        if entity_table.upper() == "TASK":
            entity = self.schedule.resolve_activity(str(entity_ref))
            fk, proj_id = entity.task_id, entity.proj_id
        else:
            fk, proj_id = int(entity_ref), None
        column = {
            "FT_TEXT": "udf_text",
            "FT_FLOAT": "udf_number",
            "FT_INT": "udf_number",
            "FT_MONEY": "udf_number",
            "FT_FLOAT_2_DECIMALS": "udf_number",
            "FT_START_DATE": "udf_date",
            "FT_END_DATE": "udf_date",
            "FT_STATICTYPE": "udf_code_id",
        }.get(str(tdef.get("logical_data_type")), "udf_text")
        table = self._table("UDFVALUE")
        table.rows = [
            r
            for r in table.rows
            if not (
                (t := table.value(r, "udf_type_id")) is not None
                and int(t) == type_id
                and (f := table.value(r, "fk_id")) is not None
                and int(f) == fk
            )
        ]
        row = [""] * len(table.fields)
        for fname, val in {
            "udf_type_id": type_id,
            "fk_id": fk,
            "proj_id": proj_id,
            column: self._coerce("cstr_date" if column == "udf_date" else column, value),
        }.items():
            if table.has_field(fname):
                table.set(row, fname, val)
        table.rows.append(row)
        self._invalidate()
        self.summary.record("set_udf_value", str(entity_ref), {"udf": udf_name, "value": value})
        return {"entity": entity_ref, "udf": udf_name, "value": value}

    # -- internals ---------------------------------------------------------

    def _invalidate(self) -> None:
        """Rebuild the Schedule view after row-count-changing edits."""
        self.schedule = Schedule(self.doc, self.schedule.schedule_id)
