"""Schedule aggregate root: typed collections + cross-reference indexes.

Wraps an :class:`~p6_mcp.parser.reader.XerDocument`. All indexes are built
lazily on first access and invalidated never (documents are immutable in the
cache; mutation flows produce new documents).
"""

from __future__ import annotations

from datetime import datetime
from functools import cached_property
from typing import Any

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.calendar import Calendar
from p6_mcp.domain.project import Project, Wbs
from p6_mcp.domain.relationship import Relationship
from p6_mcp.domain.resource import Assignment, Resource
from p6_mcp.exceptions import AmbiguousMatchError, NotFoundError
from p6_mcp.parser.reader import Table, XerDocument


class Schedule:
    """Typed, indexed view over one parsed XER document."""

    def __init__(self, doc: XerDocument, schedule_id: str | None = None) -> None:
        self.doc = doc
        self.schedule_id = schedule_id or ""

    # -- raw table helpers ---------------------------------------------------

    def table(self, name: str) -> Table:
        return self.doc.table_or_empty(name)

    def _entities(self, table: str, cls: type[Any]) -> list[Any]:
        t = self.doc.table(table)
        if t is None:
            return []
        return [cls(t, row) for row in t.rows]

    # -- projects ------------------------------------------------------------

    @cached_property
    def projects(self) -> list[Project]:
        return self._entities("PROJECT", Project)

    @cached_property
    def projects_by_id(self) -> dict[int, Project]:
        return {p.proj_id: p for p in self.projects}

    @cached_property
    def active_projects(self) -> list[Project]:
        return [p for p in self.projects if not p.is_baseline]

    @cached_property
    def baseline_projects(self) -> list[Project]:
        return [p for p in self.projects if p.is_baseline]

    def resolve_projects(
        self, project_id: int | None = None, project_short_name: str | None = None
    ) -> list[Project]:
        """Projects matching the selector; all non-baseline projects by default."""
        if project_id is not None:
            p = self.projects_by_id.get(project_id)
            if p is None:
                raise NotFoundError(
                    f"No project with proj_id={project_id}",
                    hint=f"Known ids: {sorted(self.projects_by_id)}",
                )
            return [p]
        if project_short_name:
            matches = [
                p for p in self.projects if p.short_name.lower() == project_short_name.lower()
            ]
            if not matches:
                raise NotFoundError(
                    f"No project named {project_short_name!r}",
                    hint=f"Known: {[p.short_name for p in self.projects]}",
                )
            non_bl = [p for p in matches if not p.is_baseline]
            return non_bl or matches
        return self.active_projects or self.projects

    def data_date(self, project: Project | None = None) -> datetime | None:
        """The project's data date (earliest across projects when unspecified)."""
        if project is not None:
            return project.data_date
        dates = [p.data_date for p in self.active_projects if p.data_date]
        return min(dates) if dates else None

    # -- activities ----------------------------------------------------------

    @cached_property
    def activities(self) -> list[Activity]:
        return self._entities("TASK", Activity)

    @cached_property
    def activities_by_id(self) -> dict[int, Activity]:
        return {a.task_id: a for a in self.activities}

    @cached_property
    def activities_by_code(self) -> dict[str, list[Activity]]:
        out: dict[str, list[Activity]] = {}
        for a in self.activities:
            out.setdefault(a.code, []).append(a)
        return out

    def activities_of(self, projects: list[Project]) -> list[Activity]:
        ids = {p.proj_id for p in projects}
        return [a for a in self.activities if a.proj_id in ids]

    def resolve_activity(self, ref: str | int, project_ids: set[int] | None = None) -> Activity:
        """Find one activity by task_code or numeric task_id."""
        if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
            a = self.activities_by_id.get(int(ref))
            if a is not None:
                return a
        matches = self.activities_by_code.get(str(ref), [])
        if project_ids is not None:
            scoped = [a for a in matches if a.proj_id in project_ids]
            matches = scoped or matches
        if not matches:
            raise NotFoundError(
                f"No activity with code or id {ref!r}",
                hint="Use get_activities/search_activities to list valid codes.",
            )
        non_bl = [a for a in matches if a.proj_id in {p.proj_id for p in self.active_projects}]
        matches = non_bl or matches
        if len(matches) > 1:
            raise AmbiguousMatchError(
                f"Activity code {ref!r} matches {len(matches)} activities across projects",
                hint="Pass project_id or the numeric task_id.",
            )
        return matches[0]

    # -- WBS -----------------------------------------------------------------

    @cached_property
    def wbs_nodes(self) -> list[Wbs]:
        return self._entities("PROJWBS", Wbs)

    @cached_property
    def wbs_by_id(self) -> dict[int, Wbs]:
        return {w.wbs_id: w for w in self.wbs_nodes}

    @cached_property
    def wbs_children(self) -> dict[int | None, list[Wbs]]:
        out: dict[int | None, list[Wbs]] = {}
        for w in sorted(self.wbs_nodes, key=lambda x: (x.num("seq_num"), x.wbs_id)):
            parent = w.parent_wbs_id if w.parent_wbs_id in self.wbs_by_id else None
            out.setdefault(parent, []).append(w)
        return out

    def wbs_path(self, wbs_id: int | None) -> str:
        """Dotted short-name path from the project node down."""
        parts: list[str] = []
        seen: set[int] = set()
        while wbs_id is not None and wbs_id in self.wbs_by_id and wbs_id not in seen:
            seen.add(wbs_id)
            node = self.wbs_by_id[wbs_id]
            parts.append(node.short_name or node.name)
            wbs_id = node.parent_wbs_id
        return ".".join(reversed(parts))

    def wbs_level(self, wbs_id: int | None) -> int:
        level, seen = 0, set()
        while wbs_id is not None and wbs_id in self.wbs_by_id and wbs_id not in seen:
            seen.add(wbs_id)
            level += 1
            wbs_id = self.wbs_by_id[wbs_id].parent_wbs_id
        return level

    @cached_property
    def activities_by_wbs(self) -> dict[int, list[Activity]]:
        out: dict[int, list[Activity]] = {}
        for a in self.activities:
            if a.wbs_id is not None:
                out.setdefault(a.wbs_id, []).append(a)
        return out

    def wbs_descendant_ids(self, wbs_id: int) -> set[int]:
        """wbs_id plus all descendants."""
        out = {wbs_id}
        stack = [wbs_id]
        while stack:
            for child in self.wbs_children.get(stack.pop(), []):
                if child.wbs_id not in out:
                    out.add(child.wbs_id)
                    stack.append(child.wbs_id)
        return out

    # -- calendars -----------------------------------------------------------

    @cached_property
    def calendars(self) -> list[Calendar]:
        return self._entities("CALENDAR", Calendar)

    @cached_property
    def calendars_by_id(self) -> dict[int, Calendar]:
        return {c.clndr_id: c for c in self.calendars}

    @cached_property
    def default_calendar(self) -> Calendar | None:
        for c in self.calendars:
            if c.f("default_flag"):
                return c
        return self.calendars[0] if self.calendars else None

    def calendar_for(self, activity: Activity) -> Calendar | None:
        """The activity's calendar, falling back to project default then global."""
        if activity.clndr_id is not None:
            cal = self.calendars_by_id.get(activity.clndr_id)
            if cal is not None:
                return cal
        proj = self.projects_by_id.get(activity.proj_id)
        if proj is not None and proj.clndr_id is not None:
            cal = self.calendars_by_id.get(proj.clndr_id)
            if cal is not None:
                return cal
        return self.default_calendar

    def hours_to_days(self, activity: Activity, hours: float | None) -> float | None:
        cal = self.calendar_for(activity)
        if hours is None:
            return None
        return cal.hours_to_days(hours) if cal else hours / 8.0

    # -- relationships -------------------------------------------------------

    @cached_property
    def relationships(self) -> list[Relationship]:
        return self._entities("TASKPRED", Relationship)

    @cached_property
    def predecessors_of(self) -> dict[int, list[Relationship]]:
        out: dict[int, list[Relationship]] = {}
        for r in self.relationships:
            out.setdefault(r.task_id, []).append(r)
        return out

    @cached_property
    def successors_of(self) -> dict[int, list[Relationship]]:
        out: dict[int, list[Relationship]] = {}
        for r in self.relationships:
            out.setdefault(r.pred_task_id, []).append(r)
        return out

    # -- resources & assignments --------------------------------------------

    @cached_property
    def resources(self) -> list[Resource]:
        return self._entities("RSRC", Resource)

    @cached_property
    def resources_by_id(self) -> dict[int, Resource]:
        return {r.rsrc_id: r for r in self.resources}

    def resolve_resource(self, ref: str | int) -> Resource:
        """Find a resource by rsrc_id, short name, or name (case-insensitive)."""
        if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
            r = self.resources_by_id.get(int(ref))
            if r is not None:
                return r
        needle = str(ref).lower()
        matches = [
            r for r in self.resources if r.short_name.lower() == needle or r.name.lower() == needle
        ]
        if not matches:
            raise NotFoundError(
                f"No resource matching {ref!r}",
                hint="Use get_resources to list resources.",
            )
        if len(matches) > 1:
            raise AmbiguousMatchError(
                f"Resource {ref!r} matches {len(matches)} resources",
                hint="Pass the numeric rsrc_id.",
            )
        return matches[0]

    @cached_property
    def assignments(self) -> list[Assignment]:
        return self._entities("TASKRSRC", Assignment)

    @cached_property
    def assignments_by_task(self) -> dict[int, list[Assignment]]:
        out: dict[int, list[Assignment]] = {}
        for a in self.assignments:
            out.setdefault(a.task_id, []).append(a)
        return out

    @cached_property
    def assignments_by_rsrc(self) -> dict[int, list[Assignment]]:
        out: dict[int, list[Assignment]] = {}
        for a in self.assignments:
            if a.rsrc_id is not None:
                out.setdefault(a.rsrc_id, []).append(a)
        return out

    @cached_property
    def rates_by_rsrc(self) -> dict[int, list[dict[str, Any]]]:
        out: dict[int, list[dict[str, Any]]] = {}
        t = self.doc.table("RSRCRATE")
        if t is None:
            return out
        for d in t.iter_dicts():
            rid = d.get("rsrc_id")
            if rid is not None:
                out.setdefault(int(rid), []).append(d)
        for rows in out.values():
            rows.sort(key=lambda r: r.get("start_date") or datetime.min)
        return out

    # -- activity codes ------------------------------------------------------

    @cached_property
    def code_types_by_id(self) -> dict[int, dict[str, Any]]:
        t = self.doc.table("ACTVTYPE")
        if t is None:
            return {}
        return {
            int(d["actv_code_type_id"]): d
            for d in t.iter_dicts()
            if d.get("actv_code_type_id") is not None
        }

    @cached_property
    def code_values_by_id(self) -> dict[int, dict[str, Any]]:
        t = self.doc.table("ACTVCODE")
        if t is None:
            return {}
        return {
            int(d["actv_code_id"]): d for d in t.iter_dicts() if d.get("actv_code_id") is not None
        }

    @cached_property
    def codes_by_task(self) -> dict[int, list[dict[str, Any]]]:
        """task_id → [{code_type, code_value, short_name}]."""
        out: dict[int, list[dict[str, Any]]] = {}
        t = self.doc.table("TASKACTV")
        if t is None:
            return out
        for d in t.iter_dicts():
            tid, cid = d.get("task_id"), d.get("actv_code_id")
            if tid is None or cid is None:
                continue
            val = self.code_values_by_id.get(int(cid), {})
            typ = self.code_types_by_id.get(
                int(val.get("actv_code_type_id") or d.get("actv_code_type_id") or 0), {}
            )
            out.setdefault(int(tid), []).append(
                {
                    "code_type": typ.get("actv_code_type"),
                    "code_value": val.get("actv_code_name"),
                    "short_name": val.get("short_name"),
                    "actv_code_id": int(cid),
                }
            )
        return out

    @cached_property
    def tasks_by_code_value(self) -> dict[int, list[int]]:
        """actv_code_id → [task_id]."""
        out: dict[int, list[int]] = {}
        for tid, codes in self.codes_by_task.items():
            for c in codes:
                out.setdefault(int(c["actv_code_id"]), []).append(tid)
        return out

    # -- UDFs ----------------------------------------------------------------

    @cached_property
    def udf_types_by_id(self) -> dict[int, dict[str, Any]]:
        t = self.doc.table("UDFTYPE")
        if t is None:
            return {}
        return {
            int(d["udf_type_id"]): d for d in t.iter_dicts() if d.get("udf_type_id") is not None
        }

    @cached_property
    def udfs_by_entity(self) -> dict[tuple[str, int], list[dict[str, Any]]]:
        """(table_name, fk_id) → [{name, label, type, value}]."""
        out: dict[tuple[str, int], list[dict[str, Any]]] = {}
        t = self.doc.table("UDFVALUE")
        if t is None:
            return out
        for d in t.iter_dicts():
            type_id, fk = d.get("udf_type_id"), d.get("fk_id")
            if type_id is None or fk is None:
                continue
            typ = self.udf_types_by_id.get(int(type_id), {})
            value: Any = d.get("udf_text")
            if value is None:
                value = d.get("udf_number")
            if value is None:
                value = d.get("udf_date")
            if value is None:
                value = d.get("udf_code_id")
            out.setdefault((str(typ.get("table_name") or ""), int(fk)), []).append(
                {
                    "udf_type_id": int(type_id),
                    "name": typ.get("udf_type_name"),
                    "label": typ.get("udf_type_label"),
                    "data_type": typ.get("logical_data_type"),
                    "value": value,
                }
            )
        return out

    def task_udfs(self, task_id: int) -> list[dict[str, Any]]:
        return self.udfs_by_entity.get(("TASK", task_id), [])

    # -- expenses, notes, steps ---------------------------------------------

    @cached_property
    def expenses_by_task(self) -> dict[int, list[dict[str, Any]]]:
        out: dict[int, list[dict[str, Any]]] = {}
        t = self.doc.table("PROJCOST")
        if t is None:
            return out
        for d in t.iter_dicts():
            tid = d.get("task_id")
            if tid is not None:
                out.setdefault(int(tid), []).append(d)
        return out

    @cached_property
    def memos_by_task(self) -> dict[int, list[dict[str, Any]]]:
        out: dict[int, list[dict[str, Any]]] = {}
        t = self.doc.table("TASKMEMO")
        memo_types = {
            int(d["memo_type_id"]): d.get("memo_type")
            for d in self.table("MEMOTYPE").iter_dicts()
            if d.get("memo_type_id") is not None
        }
        if t is None:
            return out
        for d in t.iter_dicts():
            tid = d.get("task_id")
            if tid is None:
                continue
            mt = d.get("memo_type_id")
            out.setdefault(int(tid), []).append(
                {
                    "notebook_topic": memo_types.get(int(mt)) if mt is not None else None,
                    "memo": d.get("task_memo"),
                }
            )
        return out

    @cached_property
    def steps_by_task(self) -> dict[int, list[dict[str, Any]]]:
        out: dict[int, list[dict[str, Any]]] = {}
        t = self.doc.table("TASKPROC")
        if t is None:
            return out
        for d in t.iter_dicts():
            tid = d.get("task_id")
            if tid is not None:
                out.setdefault(int(tid), []).append(d)
        return out

    # -- schedule options ----------------------------------------------------

    @cached_property
    def schedoptions_by_proj(self) -> dict[int, dict[str, Any]]:
        t = self.doc.table("SCHEDOPTIONS")
        if t is None:
            return {}
        return {int(d["proj_id"]): d for d in t.iter_dicts() if d.get("proj_id") is not None}
