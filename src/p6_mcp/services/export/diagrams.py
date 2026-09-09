"""Diagram and calendar exports: Mermaid Gantt, Graphviz DOT, iCalendar."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.services.query.activities import ActivityFilter, filter_activities

_SAFE = re.compile(r"[^A-Za-z0-9_]")


def _ident(code: str) -> str:
    return "n_" + _SAFE.sub("_", code)


def gantt_mermaid(
    sch: Schedule,
    projects: list[Project],
    flt: ActivityFilter | None = None,
    max_rows: int = 60,
    group_by_wbs: bool = True,
) -> str:
    """A Mermaid `gantt` block; critical activities get the `crit` tag."""
    acts = sch.activities_of(projects)
    if flt is not None:
        acts = filter_activities(sch, acts, flt)
    acts = [a for a in acts if a.start and a.finish and not a.is_wbs_summary]
    acts.sort(key=lambda a: (a.start or datetime.max, a.code))
    truncated = len(acts) > max_rows
    acts = acts[:max_rows]
    title = projects[0].short_name if projects else "Schedule"
    lines = [
        "gantt",
        f"    title {title} schedule",
        "    dateFormat YYYY-MM-DD",
        "    axisFormat %Y-%m",
    ]
    groups: dict[str, list] = {}
    for a in acts:
        key = sch.wbs_path(a.wbs_id) if group_by_wbs else "Activities"
        groups.setdefault(key or "(no WBS)", []).append(a)
    for section, members in groups.items():
        lines.append(f"    section {section}")
        for a in members:
            tags = []
            if a.is_completed:
                tags.append("done")
            elif a.is_in_progress:
                tags.append("active")
            if not a.is_completed and (a.total_float_hours or 1) <= 0:
                tags.append("crit")
            if a.is_milestone:
                tags.append("milestone")
            tag = ", ".join(tags)
            prefix = f"{tag}, " if tag else ""
            name = a.name.replace(":", " -").replace("\n", " ")
            start = (a.start or datetime.min).strftime("%Y-%m-%d")
            end = (a.finish or a.start or datetime.min) + timedelta(days=1)
            lines.append(f"    {name} :{prefix}{_ident(a.code)}, {start}, {end:%Y-%m-%d}")
    if truncated:
        lines.append(f"    %% truncated to {max_rows} activities")
    return "\n".join(lines)


def network_dot(
    sch: Schedule,
    projects: list[Project],
    flt: ActivityFilter | None = None,
    max_nodes: int = 200,
) -> str:
    """A Graphviz DOT digraph of the activity network."""
    acts = sch.activities_of(projects)
    if flt is not None:
        acts = filter_activities(sch, acts, flt)
    acts.sort(key=lambda a: (a.start or datetime.max, a.code))
    acts = acts[:max_nodes]
    keep = {a.task_id for a in acts}
    lines = [
        "digraph schedule {",
        "  rankdir=LR;",
        '  node [shape=box, style="rounded,filled", fontname="Helvetica"];',
    ]
    for a in acts:
        critical = not a.is_completed and (a.total_float_hours or 1) <= 0
        fill = (
            "#d9d9d9"
            if a.is_completed
            else "#ffcccc"
            if critical
            else "#cce5ff"
            if a.is_in_progress
            else "#ffffff"
        )
        shape = ", shape=diamond" if a.is_milestone else ""
        label = f"{a.code}\\n{a.name}".replace('"', "'")
        lines.append(f'  {_ident(a.code)} [label="{label}", fillcolor="{fill}"{shape}];')
    for r in sch.relationships:
        if r.pred_task_id not in keep or r.task_id not in keep:
            continue
        pred = sch.activities_by_id[r.pred_task_id]
        succ = sch.activities_by_id[r.task_id]
        label_parts = [r.short_type]
        if r.lag_hours:
            cal = sch.calendar_for(succ)
            lag_days = cal.hours_to_days(r.lag_hours) if cal else r.lag_hours / 8
            label_parts.append(f"{lag_days:+.0f}d")
        style = ' style="dashed"' if r.pred_type != "PR_FS" else ""
        lines.append(
            f"  {_ident(pred.code)} -> {_ident(succ.code)} "
            f'[label="{" ".join(label_parts)}"{style}];'
        )
    lines.append("}")
    return "\n".join(lines)


def milestones_ics(sch: Schedule, projects: list[Project]) -> str:
    """Milestones as an RFC 5545 iCalendar feed (all-day VEVENTs)."""
    stamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//p6-mcp//Primavera P6 milestones//EN",
        "CALSCALE:GREGORIAN",
    ]
    for a in sch.activities_of(projects):
        if not a.is_milestone:
            continue
        when = a.finish if a.task_type == "TT_FinMile" else a.start
        if when is None:
            continue
        proj = sch.projects_by_id.get(a.proj_id)
        lines += [
            "BEGIN:VEVENT",
            f"UID:{a.task_id}-{a.code}@p6-mcp",
            f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{when:%Y%m%d}",
            f"DTEND;VALUE=DATE:{when + timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{a.code} {a.name}",
            f"DESCRIPTION:Project {proj.short_name if proj else a.proj_id} — "
            f"{a.type_label}; status {a.status_label}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
