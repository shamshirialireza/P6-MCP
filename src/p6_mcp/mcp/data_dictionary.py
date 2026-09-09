"""A plain-language dictionary of P6 tables, fields, and enum values.

Kept in code (not markdown) so ``explain_field`` and the generated docs page
can never drift apart. Field entries fall back to the schema registry's type
heuristic when a column is not described here explicitly.
"""

from __future__ import annotations

from typing import Any

from p6_mcp.domain.base import ENUMS
from p6_mcp.parser.schema import field_type

TABLES: dict[str, str] = {
    "PROJECT": "One row per project (and per baseline; baselines have project_flag='N').",
    "PROJWBS": "Work breakdown structure nodes. The project node has proj_node_flag='Y'.",
    "TASK": "Activities — the core schedule records.",
    "TASKPRED": "Relationships (predecessor links) with type and lag.",
    "TASKRSRC": "Resource and role assignments with quantities and costs.",
    "RSRC": "The resource pool (labor, material, nonlabor).",
    "RSRCRATE": "Resource price and availability by effective date.",
    "ROLES": "Role dictionary used for role-based planning.",
    "CALENDAR": "Calendars; clndr_data holds the work week and holidays.",
    "ACTVTYPE": "Activity code type definitions.",
    "ACTVCODE": "Activity code values.",
    "TASKACTV": "Which activity code values are assigned to which activities.",
    "UDFTYPE": "User-defined field definitions.",
    "UDFVALUE": "User-defined field values per entity.",
    "PROJCOST": "Project expenses (non-resource costs).",
    "ACCOUNT": "Cost account breakdown structure.",
    "SCHEDOPTIONS": "Per-project scheduling settings used by the P6 engine.",
    "MEMOTYPE": "Notebook topic definitions.",
    "TASKMEMO": "Notebook entries on activities.",
    "TASKPROC": "Activity steps with weights.",
    "FINDATES": "Financial period calendar.",
    "TASKFIN": "Stored past-period actuals at activity level.",
    "TRSRCFIN": "Stored past-period actuals at assignment level.",
    "OBS": "Organizational breakdown structure.",
    "CURRTYPE": "Currency definitions.",
    "UMEASURE": "Units of measure for material resources.",
    "RSRCCURVDATA": "Resource distribution curves for non-linear spreading.",
    "WBSSTEP": "WBS milestones used for weighted percent complete.",
    "DOCUMENT": "Work products and documents.",
}

FIELDS: dict[str, str] = {
    # Identity
    "task_code": "Activity ID as shown in P6 (unique within a project).",
    "task_name": "Activity description.",
    "proj_short_name": "Project ID as shown in P6.",
    "wbs_short_name": "WBS code segment; the full path joins segments with '.'.",
    "guid": "Globally unique identifier, stable across exports.",
    # Status and type
    "status_code": "Activity status: TK_NotStart, TK_Active, TK_Complete.",
    "task_type": "Activity type: task/resource dependent, milestone, LOE, WBS summary.",
    "duration_type": "How P6 rebalances duration, units, and units/time when one changes.",
    "complete_pct_type": "Which percent complete drives the activity: duration, units, or physical.",
    "phys_complete_pct": "Physical percent complete, entered manually by the planner.",
    # Durations (all in hours)
    "target_drtn_hr_cnt": "Original (planned/at-completion) duration in hours.",
    "remain_drtn_hr_cnt": "Remaining duration in hours; drives the forecast finish.",
    "total_float_hr_cnt": "Total float in hours — delay available before the project finish slips.",
    "free_float_hr_cnt": "Free float in hours — delay available before any successor moves.",
    # Dates
    "act_start_date": "Actual start. Present once work has begun.",
    "act_end_date": "Actual finish. Present only when the activity is complete.",
    "early_start_date": "Earliest the activity can start per the forward pass.",
    "early_end_date": "Earliest the activity can finish per the forward pass.",
    "late_start_date": "Latest start that keeps the project finish; ES + total float.",
    "late_end_date": "Latest finish that keeps the project finish.",
    "target_start_date": "Planned start (the 'plan' baseline inside the project).",
    "target_end_date": "Planned finish.",
    "expect_end_date": "Expected finish entered by a resource; overrides remaining duration.",
    "suspend_date": "When work was suspended.",
    "resume_date": "When suspended work resumed.",
    "restart_date": "Remaining-work start for an in-progress activity.",
    "reend_date": "Remaining-work finish for an in-progress activity.",
    "last_recalc_date": "The project DATA DATE — the 'as of' moment of the schedule.",
    "next_data_date": "The planned data date of the next update.",
    "plan_start_date": "Project planned start.",
    "plan_end_date": "Project planned finish.",
    "scd_end_date": "Must-finish-by date constraining the whole project.",
    "anticip_start_date": "Anticipated start on a WBS node before activities exist.",
    # Constraints
    "cstr_type": "Primary constraint type (see the cstr_type enum).",
    "cstr_date": "Date the primary constraint applies to.",
    "cstr_type2": "Secondary constraint type.",
    "cstr_date2": "Date the secondary constraint applies to.",
    # Critical path
    "driving_path_flag": "Y when P6's last schedule run put the activity on the longest path.",
    "float_path": "Float path number when multiple float paths were calculated.",
    "float_path_order": "Position within its float path.",
    "critical_drtn_hr_cnt": "Float at or below which P6 calls an activity critical.",
    "critical_path_type": "Whether criticality means total float or longest path.",
    # Relationships
    "pred_type": "Relationship type: PR_FS, PR_SS, PR_FF, PR_SF.",
    "lag_hr_cnt": "Lag in hours; negative values are leads.",
    "pred_task_id": "task_id of the predecessor.",
    "aref": "Actual relationship early finish, stored by the scheduler.",
    "arls": "Actual relationship late start, stored by the scheduler.",
    # Resources and cost
    "rsrc_type": "Resource type: RT_Labor, RT_Mat (material), RT_Equip (nonlabor).",
    "target_qty": "Budgeted units on the assignment.",
    "remain_qty": "Remaining units.",
    "act_reg_qty": "Actual regular (non-overtime) units.",
    "act_ot_qty": "Actual overtime units.",
    "target_cost": "Budgeted cost.",
    "act_reg_cost": "Actual regular cost.",
    "remain_cost": "Remaining cost.",
    "cost_per_qty": "Price per unit used for this assignment.",
    "max_qty_per_hr": "Resource availability — max units per hour; drives over-allocation.",
    "curv_id": "Resource curve shaping how units spread over the activity.",
    "target_qty_per_hr": "Budgeted units per hour (the assignment's 'units/time').",
    # Calendars
    "clndr_data": "Encoded work week, shifts, and holiday exceptions.",
    "day_hr_cnt": "Hours per working day — the divisor for hours-to-days conversion.",
    "week_hr_cnt": "Hours per working week.",
    "clndr_type": "Calendar scope: global (CA_Base), project, or resource.",
    "base_clndr_id": "Calendar this one inherits from.",
    # Project / WBS
    "project_flag": "Y for a live project, N for a baseline copy.",
    "orig_proj_id": "For a baseline, the project it was copied from.",
    "sum_base_proj_id": "For a live project, the baseline it is compared against.",
    "ev_compute_type": "How earned value percent complete is derived for the WBS node.",
    "ev_etc_compute_type": "How the estimate-to-complete is derived for the WBS node.",
    "proj_node_flag": "Y when the WBS row is the project's root node.",
    "parent_wbs_id": "Parent WBS node; null at the root.",
}


def explain_field(table: str, field: str) -> dict[str, Any]:
    """Human explanation of a P6 column, with its enum values when relevant."""
    table_u, field_l = table.upper(), field.lower()
    out: dict[str, Any] = {
        "table": table_u,
        "field": field_l,
        "table_description": TABLES.get(table_u, "Not one of the tables p6-mcp describes."),
        "description": FIELDS.get(field_l),
        "parsed_as": field_type(field_l).value,
    }
    if out["description"] is None:
        out["description"] = _infer(field_l, out["parsed_as"])
        out["inferred"] = True
    enum_key = {
        "status_code": "status_code",
        "task_type": "task_type",
        "cstr_type": "cstr_type",
        "cstr_type2": "cstr_type",
        "pred_type": "pred_type",
        "rsrc_type": "rsrc_type",
        "duration_type": "duration_type",
        "complete_pct_type": "complete_pct_type",
        "critical_path_type": "critical_path_type",
        "clndr_type": "clndr_type",
        "ev_compute_type": "ev_compute_type",
        "logical_data_type": "udf_data_type",
    }.get(field_l)
    if enum_key:
        out["values"] = ENUMS[enum_key]
    if field_l.endswith("_hr_cnt"):
        out["units"] = "hours (convert with the owning activity's calendar day_hr_cnt)"
    elif field_l.endswith("_cost"):
        out["units"] = "project currency"
    elif field_l.endswith("_qty"):
        out["units"] = "hours for labor/nonlabor, material units for RT_Mat"
    elif field_l.endswith("_pct"):
        out["units"] = "percent (0-100)"
    return out


def _infer(field: str, parsed_as: str) -> str:
    """A best-effort description from P6's naming conventions."""
    hints = {
        "date": "A date value.",
        "bool": "A Y/N flag.",
        "int": "An identifier or whole number.",
        "float": "A numeric quantity.",
        "str": "A text value.",
    }
    base = hints.get(parsed_as, "A field value.")
    if field.endswith("_id"):
        base = "A foreign key or identifier."
    return f"{base} No curated description for this column yet."


def dictionary() -> dict[str, Any]:
    """The full dictionary, used by the data-dictionary resource and docs."""
    return {
        "tables": TABLES,
        "fields": FIELDS,
        "enums": ENUMS,
        "conventions": {
            "_hr_cnt": "duration or float in hours",
            "_qty": "units (hours for labor, material units otherwise)",
            "_cost": "money in the project currency",
            "_flag": "Y/N boolean",
            "_date": "timezone-naive datetime, 'YYYY-MM-DD HH:MM'",
            "_id": "identifier / foreign key",
            "_pct": "percentage 0-100",
        },
    }
