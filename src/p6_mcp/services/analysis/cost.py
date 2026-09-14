"""Cost summaries and time-phased cash flow."""

from __future__ import annotations

from typing import Any

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import InvalidArgumentError
from p6_mcp.services.analysis.time_phasing import merge_series, series_to_rows, spread

GROUP_BYS = ("wbs", "resource", "role", "account", "activity_code", "expense_category", "activity")


def activity_costs(sch: Schedule, a: Activity) -> dict[str, float]:
    """budgeted/actual/remaining cost of one activity (assignments + expenses),
    with labor/nonlabor/material/expense split of the budget."""
    out = {
        "budgeted": 0.0,
        "actual": 0.0,
        "remaining": 0.0,
        "labor": 0.0,
        "nonlabor": 0.0,
        "material": 0.0,
        "expense": 0.0,
    }
    for x in sch.assignments_by_task.get(a.task_id, []):
        out["budgeted"] += x.budgeted_cost
        out["actual"] += x.actual_cost
        out["remaining"] += x.remaining_cost
        key = {"RT_Labor": "labor", "RT_Equip": "nonlabor", "RT_Mat": "material"}.get(
            x.rsrc_type, "nonlabor"
        )
        out[key] += x.budgeted_cost
    for e in sch.expenses_by_task.get(a.task_id, []):
        out["budgeted"] += float(e.get("target_cost") or 0)
        out["actual"] += float(e.get("act_cost") or 0)
        out["remaining"] += float(e.get("remain_cost") or 0)
        out["expense"] += float(e.get("target_cost") or 0)
    out["at_completion"] = out["actual"] + out["remaining"]
    return out


def _group_keys(sch: Schedule, a: Activity, group_by: str, code_type: str | None) -> list[str]:
    if group_by == "activity":
        return [a.code]
    if group_by == "wbs":
        return [sch.wbs_path(a.wbs_id) or "(no WBS)"]
    if group_by == "resource":
        names = {
            sch.resources_by_id[x.rsrc_id].name
            for x in sch.assignments_by_task.get(a.task_id, [])
            if x.rsrc_id in sch.resources_by_id
        }
        return sorted(names) or ["(no resource)"]
    if group_by == "role":
        t = sch.table("ROLES")
        roles_by_id = {
            int(d["role_id"]): str(d.get("role_name") or "")
            for d in t.iter_dicts()
            if d.get("role_id") is not None
        }
        names = {
            roles_by_id.get(x.role_id, f"role {x.role_id}")
            for x in sch.assignments_by_task.get(a.task_id, [])
            if x.role_id is not None
        }
        return sorted(names) or ["(no role)"]
    if group_by == "account":
        accts = {
            int(d["acct_id"]): str(d.get("acct_name") or "")
            for d in sch.table("ACCOUNT").iter_dicts()
            if d.get("acct_id") is not None
        }
        keys: set[str] = set()
        for x in sch.assignments_by_task.get(a.task_id, []):
            acct = x.f("acct_id")
            if acct is not None:
                keys.add(accts.get(int(acct), f"account {acct}"))
        for e in sch.expenses_by_task.get(a.task_id, []):
            acct = e.get("acct_id")
            if acct is not None:
                keys.add(accts.get(int(acct), f"account {acct}"))
        return sorted(keys) or ["(no cost account)"]
    if group_by == "expense_category":
        cats = {
            str(e.get("cost_type") or "(uncategorized)")
            for e in sch.expenses_by_task.get(a.task_id, [])
        }
        return sorted(cats) or ["(no expenses)"]
    if group_by == "activity_code":
        codes = sch.codes_by_task.get(a.task_id, [])
        if code_type:
            codes = [c for c in codes if str(c.get("code_type") or "").lower() == code_type.lower()]
        return sorted({f"{c.get('code_type')}: {c.get('code_value')}" for c in codes}) or [
            "(unassigned)"
        ]
    raise InvalidArgumentError(f"Unknown group_by {group_by!r}", hint=f"Use one of {GROUP_BYS}")


def cost_summary(
    sch: Schedule,
    projects: list[Project],
    group_by: str = "wbs",
    code_type: str | None = None,
) -> dict[str, Any]:
    """Budget/actual/remaining/at-completion grouped by the requested dimension.

    Note: grouping by resource/role/account attributes the activity's whole
    cost to each matching key, so multi-keyed activities appear under each.
    """
    groups: dict[str, dict[str, float]] = {}
    totals = {
        "budgeted": 0.0,
        "actual": 0.0,
        "remaining": 0.0,
        "at_completion": 0.0,
        "labor": 0.0,
        "nonlabor": 0.0,
        "material": 0.0,
        "expense": 0.0,
    }
    for a in sch.activities_of(projects):
        costs = activity_costs(sch, a)
        for k in totals:
            totals[k] += costs.get(k, 0.0)
        for key in _group_keys(sch, a, group_by, code_type):
            g = groups.setdefault(
                key,
                {
                    "budgeted": 0.0,
                    "actual": 0.0,
                    "remaining": 0.0,
                    "at_completion": 0.0,
                    "activity_count": 0.0,
                },
            )
            for k in ("budgeted", "actual", "remaining", "at_completion"):
                g[k] += costs[k]
            g["activity_count"] += 1
    return {
        "group_by": group_by,
        "totals": {k: round(v, 2) for k, v in totals.items()},
        "groups": [
            {"key": k, **{m: round(v, 2) for m, v in g.items()}} for k, g in sorted(groups.items())
        ],
    }


def cash_flow(
    sch: Schedule,
    projects: list[Project],
    period: str = "month",
    include_expenses: bool = True,
) -> dict[str, Any]:
    """Time-phased planned/actual/remaining cost with cumulative columns."""
    dd = sch.data_date(projects[0] if projects else None)
    series: dict[str, dict[str, float]] = {
        "planned_cost": {},
        "actual_cost": {},
        "remaining_cost": {},
    }
    proj_ids = {p.proj_id for p in projects}
    for x in sch.assignments:
        if x.proj_id not in proj_ids:
            continue
        act = sch.activities_by_id.get(x.task_id)
        if act is None:
            continue
        cal = sch.calendar_for(act)
        if cal is None:
            continue
        if x.planned_start and x.planned_finish:
            merge_series(
                series["planned_cost"],
                spread(cal, x.planned_start, x.planned_finish, x.budgeted_cost, period),
            )
        a_start, a_end = x.f("act_start_date"), x.f("act_end_date") or dd
        if a_start and a_end and x.actual_cost:
            merge_series(series["actual_cost"], spread(cal, a_start, a_end, x.actual_cost, period))
        r_start = x.f("restart_date") or (dd if a_start else x.planned_start)
        r_finish = x.f("reend_date") or x.finish
        if r_start and r_finish and x.remaining_cost:
            merge_series(
                series["remaining_cost"], spread(cal, r_start, r_finish, x.remaining_cost, period)
            )
    if include_expenses:
        for a in sch.activities_of(projects):
            cal = sch.calendar_for(a)
            if cal is None:
                continue
            for e in sch.expenses_by_task.get(a.task_id, []):
                ps = e.get("target_start_date") or a.planned_start or a.start
                pf = e.get("target_end_date") or a.planned_finish or a.finish
                if ps and pf:
                    merge_series(
                        series["planned_cost"],
                        spread(cal, ps, pf, float(e.get("target_cost") or 0), period),
                    )
                    merge_series(
                        series["remaining_cost"],
                        spread(cal, ps, pf, float(e.get("remain_cost") or 0), period),
                    )
                if a.act_start and float(e.get("act_cost") or 0):
                    merge_series(
                        series["actual_cost"],
                        spread(
                            cal,
                            a.act_start,
                            a.act_finish or dd or a.act_start,
                            float(e.get("act_cost") or 0),
                            period,
                        ),
                    )
    rows = series_to_rows(series, cumulative_keys=tuple(series))
    return {
        "period": period,
        "include_expenses": include_expenses,
        "data_date": dd.isoformat(sep=" ") if dd else None,
        "periods": rows,
        "totals": {k: round(sum(v.values()), 2) for k, v in series.items()},
    }


def cost_by_account(
    sch: Schedule,
    projects: list[Project],
) -> dict[str, Any]:
    """Cost grouped by cost account (PROJCOST)."""
    return cost_summary(sch, projects, group_by="account")
