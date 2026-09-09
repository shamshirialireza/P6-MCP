"""Prompt templates (§7).

Every prompt names the exact tools to call, in order, with suggested arguments
and a required output structure — so a model with no P6 background still runs a
professional analysis instead of guessing.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from p6_mcp.mcp.context import AppContext

_ANALYSIS_PLANS: dict[str, list[str]] = {
    "general": [
        "parse_xer_file(file_path) — establish what is in the file",
        "get_schedule_summary(file_path) — counts, dates, health score",
        "get_critical_path(file_path, method='both')",
        "get_progress_summary(file_path)",
    ],
    "schedule": [
        "get_schedule_summary(file_path)",
        "get_critical_path(file_path, method='both')",
        "get_near_critical(file_path, threshold_days=10)",
        "get_float_distribution(file_path)",
        "get_constraints(file_path)",
    ],
    "resources": [
        "get_resources(file_path)",
        "analyze_resource_utilization(file_path, period='month')",
        "get_resource_leveling_report(file_path)",
        "get_cost_summary(file_path, group_by='resource')",
    ],
    "progress": [
        "get_progress_summary(file_path)",
        "get_status_update_check(file_path)",
        "get_behind_schedule_activities(file_path)",
        "get_lookahead(file_path, window_days=28)",
    ],
    "quality": [
        "run_dcma_assessment(file_path)",
        "analyze_logic_health(file_path)",
        "get_schedule_health_score(file_path)",
        "get_invalid_dates(file_path)",
    ],
    "cost": [
        "get_cost_summary(file_path, group_by='wbs')",
        "get_earned_value(file_path)",
        "get_cash_flow(file_path, period='month')",
        "get_expenses(file_path)",
    ],
    "risk": [
        "get_critical_path(file_path, method='longest_path')",
        "get_near_critical(file_path, threshold_days=10)",
        "get_negative_float(file_path)",
        "get_constraints(file_path)",
        "run_dcma_assessment(file_path)",
    ],
    "logic": [
        "analyze_logic_health(file_path)",
        "get_relationship_type_summary(file_path)",
        "get_out_of_sequence(file_path)",
        "recompute_cpm(file_path)",
    ],
}

_REPORT_PLANS: dict[str, str] = {
    "executive": "generate_report(file_path, report_type='executive')",
    "detailed": "generate_report(file_path, report_type='detailed')",
    "critical_path": "generate_report(file_path, report_type='critical_path')",
    "resource": "generate_report(file_path, report_type='resource')",
    "milestone": "generate_report(file_path, report_type='milestone')",
    "cost": "generate_report(file_path, report_type='cost')",
    "dcma": "generate_report(file_path, report_type='dcma')",
    "lookahead": "generate_report(file_path, report_type='lookahead')",
}

_CONCEPTS: dict[str, str] = {
    "critical path": (
        "The longest chain of dependent work determining the project finish. P6 "
        "reports it two ways: activities with total float at or below a threshold, "
        "and activities flagged driving_path_flag (the longest path). They differ "
        "when calendars differ across the network."
    ),
    "total float": (
        "How long an activity can slip before the project finish moves. Late "
        "start minus early start, measured in that activity's calendar working "
        "time — which is why float in days depends on the calendar."
    ),
    "free float": (
        "How long an activity can slip before ANY successor moves. Always less "
        "than or equal to total float."
    ),
    "data date": (
        "The 'as of' moment of a schedule update (last_recalc_date). Everything "
        "before it should be actuals; everything after it is forecast. Actuals "
        "after the data date or forecasts before it are data errors."
    ),
    "earned value": (
        "Comparing budgeted cost of work performed (EV) against work scheduled "
        "(PV) and money spent (AC). SPI = EV/PV measures schedule efficiency, "
        "CPI = EV/AC cost efficiency. PV must be time-phased to the data date."
    ),
    "dcma 14 point": (
        "A US Defense Contract Management Agency checklist for schedule quality: "
        "logic completeness, leads, lags, relationship types, hard constraints, "
        "high float, negative float, high duration, invalid dates, resources, "
        "missed tasks, a critical path test, CPLI, and BEI."
    ),
    "retained logic": (
        "When work starts out of sequence, retained logic keeps the remaining "
        "portion behind its predecessors; progress override lets it continue "
        "immediately. The choice materially changes the forecast."
    ),
    "level of effort": (
        "An LOE activity (TT_LOE) spans the work it supports rather than driving "
        "it — supervision, site management. It should be excluded from critical "
        "path and DCMA duration checks."
    ),
    "loe": "See 'level of effort'.",
    "constraint": (
        "A date imposed on an activity. Soft constraints (Start On or After) "
        "only push one direction; hard ones (Mandatory Start/Finish) override "
        "logic entirely and can hide real delays. DCMA limits hard constraints "
        "to 5% of activities."
    ),
    "lag": (
        "A delay applied to a relationship. Positive lag waits; negative lag (a "
        "lead) overlaps. DCMA wants zero leads and lags on under 5% of links, "
        "because both hide real logic."
    ),
    "wbs": (
        "The work breakdown structure — the hierarchical decomposition of scope "
        "that activities hang from and that costs roll up through."
    ),
    "baseline": (
        "A frozen copy of the schedule kept for comparison. In an XER it appears "
        "as a project row with project_flag='N' linked via orig_proj_id."
    ),
}


def register_prompts(mcp: MCPServer, ctx: AppContext) -> None:
    """Register every prompt template."""
    _ = ctx

    @mcp.prompt(title="Analyze a P6 project")
    def analyze_xer_project(file_path: str, analysis_type: str = "general") -> str:
        """Guided analysis of an XER file. analysis_type: general, schedule,
        resources, progress, quality, cost, risk, or logic."""
        plan = _ANALYSIS_PLANS.get(analysis_type)
        if plan is None:
            plan = _ANALYSIS_PLANS["general"]
            note = (
                f"\n(Unknown analysis_type '{analysis_type}' — falling back to a general analysis.)"
            )
        else:
            note = ""
        steps = "\n".join(f"{i}. {s}" for i, s in enumerate(plan, 1))
        return f"""Analyze the Primavera P6 schedule at `{file_path}`.
Analysis type: **{analysis_type}**.{note}

Call these tools in order, passing `file_path="{file_path}"`:

{steps}

If the file holds several projects, call `get_projects` first and scope every
later call with `project_id`.

Then write up your findings as:

## Summary
Two or three sentences a project director can act on.

## Key Findings
Bullets. Each one must cite the number it came from and the tool that produced
it. Report durations and float in days, and say which calendar they came from
when it matters.

## Risks and Concerns
Ranked by impact on the finish date.

## Recommended Actions
Specific and assignable — name the activity codes involved.

Do not speculate beyond the returned data. If a tool reports that a baseline was
missing and planned dates were used as a proxy, say so explicitly."""

    @mcp.prompt(title="P6 report request")
    def xer_reporting_prompt(file_path: str, report_type: str = "executive") -> str:
        """Produce a specific schedule report. report_type: executive, detailed,
        critical_path, resource, milestone, cost, dcma, or lookahead."""
        call = _REPORT_PLANS.get(
            report_type, f"generate_report(file_path, report_type='{report_type}')"
        )
        return f"""Produce a **{report_type}** report for the P6 schedule at `{file_path}`.

1. `{call}` with `file_path="{file_path}"` and `output_format="markdown"`.
2. If any figure needs backing detail, call the matching specific tool
   (`get_critical_path`, `get_earned_value`, `run_dcma_assessment`, ...).

Present the report as returned, then add a short **Analyst Commentary** section
explaining what the numbers mean and what should happen next. Keep every figure
traceable to a tool result — do not re-compute anything yourself."""

    @mcp.prompt(title="DCMA assessment walkthrough")
    def dcma_assessment_walkthrough(file_path: str, project_short_name: str = "") -> str:
        """Run the DCMA 14-point assessment and explain every failure."""
        scope = f', project_short_name="{project_short_name}"' if project_short_name else ""
        return f"""Run a DCMA 14-point assessment on `{file_path}`.

1. `run_dcma_assessment(file_path="{file_path}"{scope})`
2. For each FAILED check, pull the supporting detail:
   - Check 1 Logic → `analyze_logic_health`
   - Checks 2-4 Leads/Lags/Types → `get_relationships(only_leads=true)` and
     `get_relationship_type_summary`
   - Check 5 Hard Constraints → `get_constraints`
   - Checks 6-7 Float → `get_float_distribution`, `get_negative_float`
   - Check 8 High Duration → `get_activities(remaining_duration_min_days=44)`
   - Check 9 Invalid Dates → `get_invalid_dates`
   - Check 10 Resources → `get_activities(has_actuals=false)` cross-checked with
     `get_resource_assignments`
   - Checks 11/14 Missed Tasks & BEI → `compare_to_baseline`
   - Check 12 Critical Path Test → already run inside the assessment
   - Check 13 CPLI → `get_progress_summary`

Output a table of all 14 checks (number, name, PASS/FAIL, metric, threshold),
then a section per failure containing: what the check means in plain language,
which activities caused it (by code), why it matters for this schedule, and the
specific fix.

Note where a check was measured against planned dates because no baseline was
present — that weakens checks 11 and 14 and the reader must know."""

    @mcp.prompt(title="Schedule update review")
    def schedule_update_review(current_file: str, previous_file: str) -> str:
        """Compare this period's update against the last one."""
        return f"""Review a schedule update: `{current_file}` (current) against
`{previous_file}` (previous).

1. `diff_schedules(current_file_path="{current_file}",
   previous_file_path="{previous_file}")`
2. `get_status_update_check(file_path="{current_file}")` — is the update clean?
3. `get_progress_summary` on both files to compare percent complete.
4. `get_critical_path(file_path="{current_file}", method='both')`
5. `get_behind_schedule_activities(file_path="{current_file}")`

Report:

## What Changed
Activities added, deleted, re-dated, and progressed; logic and cost changes.

## Schedule Movement
Did the forecast finish move, and which activities drove that movement?

## Update Quality
Out-of-sequence progress, actuals past the data date, activities that should
have started but didn't. An update with these defects cannot be trusted.

## Watch List
What to interrogate before accepting the update."""

    @mcp.prompt(title="Baseline variance narrative")
    def baseline_variance_narrative(file_path: str, project_short_name: str = "") -> str:
        """Explain baseline variance in prose for a status report."""
        scope = f', project_short_name="{project_short_name}"' if project_short_name else ""
        return f"""Explain how `{file_path}` is performing against its baseline.

1. `get_baselines(file_path="{file_path}")` — confirm a baseline exists.
2. `compare_to_baseline(file_path="{file_path}"{scope})`
3. `get_activity_variances(file_path="{file_path}"{scope})`
4. `get_earned_value(file_path="{file_path}"{scope})`

Write a narrative (not a data dump) covering: overall slip or gain in working
days, which specific chains of work caused it, milestone impact, whether the
critical path has moved to different work, and what cost performance says about
whether the remaining plan is credible.

If no baseline project exists in the file, say so plainly and explain that the
comparison fell back to planned dates, which understates true variance."""

    @mcp.prompt(title="Resource leveling advice")
    def resource_leveling_advice(file_path: str, project_short_name: str = "") -> str:
        """Diagnose over-allocation and propose a levelling approach."""
        scope = f', project_short_name="{project_short_name}"' if project_short_name else ""
        return f"""Diagnose resource loading in `{file_path}` and advise on levelling.

1. `analyze_resource_utilization(file_path="{file_path}"{scope}, period='week')`
2. `get_resource_leveling_report(file_path="{file_path}"{scope})`
3. For each over-allocated resource, `get_activities(resource_name=...)` to see
   the competing work.
4. `get_activities(float_min_days=1)` to find work with float that could absorb
   a shift.

Report: which resources exceed availability and in which periods; which
activities collide; which of those have float (move these first) versus sit on
the critical path (moving these slips the finish); and a concrete levelling
sequence. Quantify the finish-date cost of any move that touches critical work."""

    @mcp.prompt(title="Earned value briefing")
    def earned_value_briefing(file_path: str, project_short_name: str = "") -> str:
        """Prepare an EVM briefing with forecasts."""
        scope = f', project_short_name="{project_short_name}"' if project_short_name else ""
        return f"""Prepare an earned-value briefing for `{file_path}`.

1. `get_earned_value(file_path="{file_path}"{scope})`
2. `get_earned_value_curve(file_path="{file_path}"{scope}, period='month')`
3. `get_cash_flow(file_path="{file_path}"{scope}, period='month')`
4. `get_progress_summary(file_path="{file_path}"{scope})`

Report BAC, PV, EV, AC, then CV/SV, then CPI/SPI, then the EAC range across all
four forecast methods, VAC, and TCPI.

Interpret, don't just tabulate: say what CPI and SPI mean for delivery, which
EAC method is most defensible for this project and why, and whether TCPI implies
a level of future efficiency the team has never actually achieved.

State the note the tool returns about how PV was derived — if planned dates
stood in for a missing baseline, every schedule variance figure is soft."""

    @mcp.prompt(title="Lookahead meeting agenda")
    def lookahead_meeting_agenda(
        file_path: str, weeks: int = 4, project_short_name: str = ""
    ) -> str:
        """Build an agenda for a lookahead coordination meeting."""
        scope = f', project_short_name="{project_short_name}"' if project_short_name else ""
        days = weeks * 7
        return f"""Build a {weeks}-week lookahead agenda from `{file_path}`.

1. `get_lookahead(file_path="{file_path}"{scope}, window_days={days},
   group_by='wbs')`
2. `get_critical_path(file_path="{file_path}"{scope})` — flag which lookahead
   items are critical.
3. `get_constraints(file_path="{file_path}"{scope})` — constraints landing in
   the window.
4. `get_resource_histogram` for any resource peaking in the window.

Produce a meeting agenda grouped by area: work starting, work finishing, work
continuing. Mark critical items clearly. For each item note the responsible
party if an activity code or UDF carries it. End with a **Decisions Needed**
list — the specific blockers that must be resolved in the meeting."""

    @mcp.prompt(title="Logic repair plan")
    def logic_repair_plan(file_path: str, project_short_name: str = "") -> str:
        """Produce a prioritized plan to fix network logic defects."""
        scope = f', project_short_name="{project_short_name}"' if project_short_name else ""
        return f"""Produce a logic repair plan for `{file_path}`.

1. `analyze_logic_health(file_path="{file_path}"{scope})`
2. `check_schedule_quality(file_path="{file_path}"{scope})`
3. `run_dcma_assessment(file_path="{file_path}"{scope})`
4. `recompute_cpm(file_path="{file_path}"{scope})` — do the stored dates match
   an independent CPM pass? Large deviations mean the file was not rescheduled
   after its last edit.

Produce a prioritized fix list. For each defect: the activity codes involved,
why it distorts the forecast, the specific repair, and the risk of making it.

Order by impact on forecast reliability: open ends and circular logic first,
then out-of-sequence progress, then leads, then hard constraints, then
redundant links. Note which repairs will move the finish date — those need
approval before anyone edits the file."""

    @mcp.prompt(title="Explain a P6 concept")
    def explain_p6_concept(concept: str) -> str:
        """Explain a Primavera P6 or planning concept in plain language."""
        key = concept.lower().strip()
        known = _CONCEPTS.get(key)
        if known:
            return f"""Explain the P6 concept **{concept}** to someone who reads
schedules but is not a scheduler.

Reference definition:
> {known}

Expand on it: what it means in practice, how P6 stores or computes it, one
worked example with real numbers, the most common way people misread it, and
which p6-mcp tools expose it. Use `explain_field` or `get_enum_values` if you
need the exact field names and codes."""
        return f"""Explain the Primavera P6 concept **{concept}**.

Start by calling `get_data_dictionary` (and `explain_field` / `get_enum_values`
if a specific column or code is involved) so your explanation matches how the
data is actually stored.

Cover: a plain-language definition, how P6 represents it, a worked example, the
common misconception, and which p6-mcp tools surface it. If the concept is not a
P6 concept at all, say so rather than inventing one."""

    _ = (
        analyze_xer_project,
        xer_reporting_prompt,
        dcma_assessment_walkthrough,
        schedule_update_review,
        baseline_variance_narrative,
        resource_leveling_advice,
        earned_value_briefing,
        lookahead_meeting_agenda,
        logic_repair_plan,
        explain_p6_concept,
    )
