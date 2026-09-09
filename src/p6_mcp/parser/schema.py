"""Registry of known XER tables and field typing rules.

Typing is resolved as: explicit override → suffix heuristic → string. The
heuristics mirror Oracle's P6 column naming conventions, so even unknown or
future tables get sensible types while remaining lossless (raw strings are
always kept).
"""

from __future__ import annotations

from enum import StrEnum


class FieldType(StrEnum):
    """Coercion category for an XER column."""

    STR = "str"
    INT = "int"
    FLOAT = "float"
    DATE = "date"
    BOOL = "bool"


#: Every table name p6-mcp types explicitly. Unknown tables still parse
#: generically; this set drives the domain binding and documentation.
KNOWN_TABLES: frozenset[str] = frozenset(
    {
        "ACCOUNT",
        "ACTVCODE",
        "ACTVTYPE",
        "APPLYACTOPTIONS",
        "CALENDAR",
        "CURRTYPE",
        "DOCUMENT",
        "FINDATES",
        "FINTMPL",
        "FUNDSRC",
        "MEMOTYPE",
        "NONWORK",
        "OBS",
        "PCATTYPE",
        "PCATVAL",
        "PHASE",
        "POBS",
        "PROJCOST",
        "PROJECT",
        "PROJEST",
        "PROJFUND",
        "PROJISSU",
        "PROJPCAT",
        "PROJTHRS",
        "PROJWBS",
        "RCATTYPE",
        "RCATVAL",
        "RISKTYPE",
        "ROLECATTYPE",
        "ROLECATVAL",
        "ROLELIMIT",
        "ROLERATE",
        "ROLERCAT",
        "ROLES",
        "RSRC",
        "RSRCCURVDATA",
        "RSRCLEVELLIST",
        "RSRCRATE",
        "RSRCRCAT",
        "RSRCROLE",
        "SCHEDOPTIONS",
        "SHIFT",
        "SHIFTPER",
        "TASK",
        "TASKACTV",
        "TASKDOC",
        "TASKFDBK",
        "TASKFIN",
        "TASKMEMO",
        "TASKNOTE",
        "TASKPRED",
        "TASKPROC",
        "TASKRSRC",
        "TASKUSER",
        "THRSPARM",
        "TRSRCFIN",
        "UDFTYPE",
        "UDFVALUE",
        "UMEASURE",
        "WBSBUDG",
        "WBSMEMO",
        "WBSRSRC_QTY",
        "WBSSTEP",
    }
)

#: Fields whose type the suffix heuristic would get wrong.
_OVERRIDES: dict[str, FieldType] = {
    # GUIDs and free text that end in suspicious suffixes
    "guid": FieldType.STR,
    "tmpl_guid": FieldType.STR,
    "clndr_data": FieldType.STR,
    "curr_symbol": FieldType.STR,
    "task_code": FieldType.STR,
    "wbs_short_name": FieldType.STR,
    "rsrc_short_name": FieldType.STR,
    "proj_short_name": FieldType.STR,
    "employee_code": FieldType.STR,
    "task_code_prefix": FieldType.STR,
    "task_code_base": FieldType.INT,
    "task_code_step": FieldType.INT,
    "fy_start_month_num": FieldType.INT,
    "day_hr_cnt": FieldType.FLOAT,
    "week_hr_cnt": FieldType.FLOAT,
    "month_hr_cnt": FieldType.FLOAT,
    "year_hr_cnt": FieldType.FLOAT,
    "udf_type": FieldType.STR,
    "logical_data_type": FieldType.STR,
    "udf_number": FieldType.FLOAT,
    "udf_text": FieldType.STR,
    "udf_date": FieldType.DATE,
    "udf_code_id": FieldType.INT,
    "seq_num": FieldType.INT,
    "wbs_max_sum_level": FieldType.INT,
    "sum_assign_level": FieldType.INT,
    "float_path": FieldType.INT,
    "float_path_order": FieldType.INT,
    "priority_num": FieldType.INT,
    "strgy_priority_num": FieldType.INT,
    "skill_level": FieldType.INT,
    "shift_period_id": FieldType.INT,
    "aref": FieldType.DATE,
    "arls": FieldType.DATE,
}

_INT_ID_EXCEPTIONS: frozenset[str] = frozenset({"cbs_id"})  # numeric anyway; kept for clarity

_DATE_SUFFIXES = ("_date",)
_BOOL_SUFFIXES = ("_flag",)
_INT_SUFFIXES = ("_id", "_num", "_level", "_type_id")
_FLOAT_SUFFIXES = (
    "_cnt",
    "_qty",
    "_cost",
    "_pct",
    "_factor",
    "_rate",
    "_wt",
    "_value",
    "_qty_per_hr",
    "_per_qty",
    "_amount",
)


def field_type(field: str) -> FieldType:
    """Resolve the coercion type for a column name."""
    ft = _OVERRIDES.get(field)
    if ft is not None:
        return ft
    for suf in _DATE_SUFFIXES:
        if field.endswith(suf):
            return FieldType.DATE
    for suf in _BOOL_SUFFIXES:
        if field.endswith(suf):
            return FieldType.BOOL
    for suf in _FLOAT_SUFFIXES:
        if field.endswith(suf):
            return FieldType.FLOAT
    for suf in _INT_SUFFIXES:
        if field.endswith(suf):
            return FieldType.INT
    return FieldType.STR
