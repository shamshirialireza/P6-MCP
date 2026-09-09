"""Report composition: every report returns a typed result exposing both
``to_dict()`` and ``to_markdown()``.

Reports are assembled from the analysis services only — no data access or
formatting logic is duplicated here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import InvalidArgumentError
from p6_mcp.services.analysis import logic_health
from p6_mcp.services.analysis.baseline_compare import compare_to_baseline
from p6_mcp.services.analysis.constraints import constraints
from p6_mcp.services.analysis.cost import cash_flow, cost_summary
from p6_mcp.services.analysis.critical_path import get_critical_path, get_near_critical
from p6_mcp.services.analysis.dcma import run_dcma_assessment
from p6_mcp.services.analysis.earned_value import earned_value
from p6_mcp.services.analysis.health_score import health_score
from p6_mcp.services.analysis.lookahead import lookahead
from p6_mcp.services.analysis.milestones import milestones
from p6_mcp.services.analysis.progress import behind_schedule, progress_summary
from p6_mcp.services.analysis.resources import utilization
from p6_mcp.services.export.tabular import to_markdown
from p6_mcp.services.query.serialize import activity_to_dict, iso

REPORT_TYPES = (
    "executive",
    "detailed",
    "critical_path",
    "milestone",
    "resource",
    "cost",
    "dcma",
    "progress",
    "baseline_variance",
    "lookahead",
    "logic_health",
)


@dataclass(slots=True)
class Report:
    """A rendered report: structured sections plus a Markdown view."""

    title: str
    report_type: str
    sections: dict[str, Any] = field(default_factory=dict)
    _markdown: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return iso(
            {"title": self.title, "report_type": self.report_type, "sections": self.sections}
        )

    def to_markdown(self) -> str:
        return "\n".join([f"# {self.title}", "", *self._markdown]).strip() + "\n"

    def add(self, heading: str, body: str, data: Any = None) -> None:
        """Append a section to both the structured and Markdown views."""
        if data is not None:
            self.sections[heading.lower().replace(" ", "_")] = data
        self._markdown += [f"## {heading}", "", body, ""]


def _kv(pairs: dict[str, Any]) -> str:
    return "\n".join(
        f"- **{k.replace('_', ' ')}**: {'' if v is None else v}" for k, v in iso(pairs).items()
    )


def _executive(sch: Schedule, projects: list[Project], rep: Report) -> None:
    prog = progress_summary(sch, projects)
    ev = earned_value(sch, projects, time_phased=False)
    hs = health_score(sch, projects)
    cp = get_critical_path(sch, projects, method="total_float")
    ms = milestones(sch, projects)
    rep.add(
        "Status at a Glance",
        _kv(
            {
                "data_date": prog["data_date"],
                "forecast_finish": prog["forecast_finish"],
                "working_days_to_finish": prog["working_days_to_finish"],
                "percent_complete_duration": f"{prog['percent_complete']['by_duration']}%",
                "activities": prog["activity_counts"]["total"],
                "completed": prog["activity_counts"]["completed"],
                "in_progress": prog["activity_counts"]["in_progress"],
                "critical_activities": len(cp["total_float_critical"]),
                "health_score": f"{hs['score']} ({hs['grade']})",
            }
        ),
        {"progress": prog, "health": hs},
    )
    rep.add("Cost and Earned Value", _kv(ev["metrics"]), ev)
    if ms:
        rows = [
            {
                "milestone": m["task_code"],
                "name": m["task_name"],
                "date": m["date"],
                "variance_days": m["variance_days"],
                "status": m["status"],
            }
            for m in ms
        ]
        rep.add("Key Milestones", to_markdown(iso(rows)), rows)
    if hs["recommendations"]:
        rep.add(
            "Recommendations",
            "\n".join(f"- {r}" for r in hs["recommendations"]),
            hs["recommendations"],
        )


def _critical_path(sch: Schedule, projects: list[Project], rep: Report) -> None:
    cp = get_critical_path(sch, projects, method="both")
    rows = [activity_to_dict(sch, a, "compact") for a in cp["total_float_critical"]]
    rep.add("Critical Activities (Total Float)", to_markdown(rows), rows)
    lp = [activity_to_dict(sch, a, "compact") for a in cp.get("longest_path", [])]
    rep.add(f"Longest Path ({cp.get('longest_path_note', 'n/a')})", to_markdown(lp), lp)
    near = [
        {**activity_to_dict(sch, a, "compact"), "float_days": round(d, 1)}
        for a, d in get_near_critical(sch, projects, 5.0)
    ]
    rep.add("Near-Critical (<= 5 days float)", to_markdown(near), near)


def _milestone(sch: Schedule, projects: list[Project], rep: Report) -> None:
    ms = milestones(sch, projects)
    rep.add("Milestones", to_markdown(iso(ms)), ms)


def _resource(sch: Schedule, projects: list[Project], rep: Report) -> None:
    util = utilization(sch, projects, period="month")
    summary = [
        {
            "resource": r["resource"],
            "type": r["rsrc_type"],
            **r["totals"],
            "overallocated_periods": r["overallocated_periods"],
        }
        for r in util["resources"]
    ]
    rep.add("Resource Totals (by month)", to_markdown(summary), util)
    over = [
        {
            "resource": r["resource"],
            "period": p["period"],
            "demand": round(p["remaining_qty"] + p["actual_qty"], 2),
            "limit": p["limit_qty"],
        }
        for r in util["resources"]
        for p in r["periods"]
        if p["overallocated"]
    ]
    rep.add("Over-allocated Periods", to_markdown(over) if over else "_None._", over)


def _cost(sch: Schedule, projects: list[Project], rep: Report) -> None:
    cs = cost_summary(sch, projects, group_by="wbs")
    rep.add("Cost Totals", _kv(cs["totals"]), cs["totals"])
    rep.add("Cost by WBS", to_markdown(cs["groups"]), cs["groups"])
    cf = cash_flow(sch, projects, period="month")
    rep.add("Cash Flow (monthly)", to_markdown(cf["periods"]), cf)


def _dcma(sch: Schedule, projects: list[Project], rep: Report) -> None:
    res = run_dcma_assessment(sch, projects)
    rows = [
        {
            "#": c["check"],
            "name": c["name"],
            "result": "PASS" if c["passed"] else "FAIL",
            "metric": c["metric"],
            "threshold": c["threshold"],
            "count": f"{c['count']}/{c['eligible']}",
        }
        for c in res["checks"]
    ]
    rep.add(
        "DCMA 14-Point Summary",
        f"**{res['summary']['passed']}/14 checks passed** "
        f"({res['summary']['score_pct']}%)\n\n" + to_markdown(rows),
        res,
    )
    failed = [c for c in res["checks"] if not c["passed"]]
    if failed:
        detail = "\n\n".join(
            f"### {c['check']}. {c['name']}\n{c['description']}\n\n"
            f"- metric: {c['metric']} (threshold {c['threshold']})\n"
            f"- offenders: {', '.join(map(str, c['offenders'])) or 'n/a'}"
            + (f"\n- note: {c['note']}" if c.get("note") else "")
            for c in failed
        )
        rep.add("Failed Checks in Detail", detail, failed)


def _progress(sch: Schedule, projects: list[Project], rep: Report) -> None:
    prog = progress_summary(sch, projects)
    rep.add("Progress", _kv(prog["percent_complete"]), prog)
    late = behind_schedule(sch, projects)
    rep.add(
        "Behind Schedule", to_markdown(iso(late)) if late else "_Nothing behind schedule._", late
    )


def _baseline_variance(sch: Schedule, projects: list[Project], rep: Report) -> None:
    cmp_ = compare_to_baseline(sch, projects)
    rep.add("Baseline Comparison Summary", _kv(cmp_["summary"]), cmp_["summary"])
    rep.add("Activity Variances", to_markdown(iso(cmp_["variances"])), cmp_["variances"])
    if cmp_["milestone_variances"]:
        rep.add(
            "Milestone Variances",
            to_markdown(iso(cmp_["milestone_variances"])),
            cmp_["milestone_variances"],
        )


def _lookahead(sch: Schedule, projects: list[Project], rep: Report) -> None:
    la = lookahead(sch, projects, window_days=28)
    for label, key in (
        ("Starting", "starting"),
        ("Finishing", "finishing"),
        ("Continuing", "continuing_in_progress"),
    ):
        rows = [r for group in la[key].values() for r in group]
        rep.add(f"{label} in the next 28 days", to_markdown(iso(rows)) if rows else "_None._", rows)


def _logic_health(sch: Schedule, projects: list[Project], rep: Report) -> None:
    lh = logic_health.analyze_logic_health(sch, projects)
    mix = lh["relationship_mix"]
    rep.add(
        "Relationship Mix", _kv({**mix["counts"], "leads": mix["leads"], "lags": mix["lags"]}), mix
    )
    rep.add(
        "Open Ends",
        _kv(
            {
                "no_predecessors": ", ".join(a.code for a in lh["open_ends"]["no_predecessors"])
                or "none",
                "no_successors": ", ".join(a.code for a in lh["open_ends"]["no_successors"])
                or "none",
            }
        ),
        {k: [a.code for a in v] for k, v in lh["open_ends"].items()},
    )
    rep.add(
        "Out of Sequence",
        to_markdown(lh["out_of_sequence"]) if lh["out_of_sequence"] else "_None._",
        lh["out_of_sequence"],
    )
    rep.add(
        "Redundant Relationships",
        to_markdown(lh["redundant"]) if lh["redundant"] else "_None._",
        lh["redundant"],
    )
    if lh["circular"]:
        rep.add("Circular Logic", "\n".join(" → ".join(c) for c in lh["circular"]), lh["circular"])


def _detailed(sch: Schedule, projects: list[Project], rep: Report) -> None:
    _executive(sch, projects, rep)
    _critical_path(sch, projects, rep)
    _progress(sch, projects, rep)
    _logic_health(sch, projects, rep)
    _cost(sch, projects, rep)
    cons = constraints(sch, projects)
    rep.add("Constraints", to_markdown(iso(cons["constraints"])), cons)


_BUILDERS: dict[str, Callable[[Schedule, list[Project], Report], None]] = {
    "executive": _executive,
    "detailed": _detailed,
    "critical_path": _critical_path,
    "milestone": _milestone,
    "resource": _resource,
    "cost": _cost,
    "dcma": _dcma,
    "progress": _progress,
    "baseline_variance": _baseline_variance,
    "lookahead": _lookahead,
    "logic_health": _logic_health,
}


def build_report(
    sch: Schedule,
    projects: list[Project],
    report_type: str = "executive",
    sections: list[str] | None = None,
) -> Report:
    """Build one of the §5.13 report types."""
    builder = _BUILDERS.get(report_type)
    if builder is None:
        raise InvalidArgumentError(
            f"Unknown report_type {report_type!r}",
            hint=f"Use one of {REPORT_TYPES}",
        )
    name = projects[0].short_name if projects else "All Projects"
    rep = Report(
        title=f"{report_type.replace('_', ' ').title()} Report — {name}",
        report_type=report_type,
    )
    builder(sch, projects, rep)
    if sections:
        wanted = {s.lower().replace(" ", "_") for s in sections}
        rep.sections = {k: v for k, v in rep.sections.items() if k in wanted}
    return rep
