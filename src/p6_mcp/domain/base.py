"""Entity base class and P6 enum vocabulary with human-readable labels.

Enum values are the exact strings P6 writes to XER. ``label_of`` never raises:
unknown values are surfaced verbatim so future P6 versions degrade gracefully.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from p6_mcp.parser.reader import Table

# ---------------------------------------------------------------------------
# Enum vocabularies (P6 code -> human label)
# ---------------------------------------------------------------------------

TASK_TYPE = {
    "TT_Task": "Task Dependent",
    "TT_Rsrc": "Resource Dependent",
    "TT_Mile": "Start Milestone",
    "TT_FinMile": "Finish Milestone",
    "TT_LOE": "Level of Effort",
    "TT_WBS": "WBS Summary",
}
STATUS_CODE = {
    "TK_NotStart": "Not Started",
    "TK_Active": "In Progress",
    "TK_Complete": "Completed",
}
CSTR_TYPE = {
    "CS_ALAP": "As Late As Possible",
    "CS_MEO": "Finish On",
    "CS_MEOA": "Finish On or After",
    "CS_MEOB": "Finish On or Before",
    "CS_MANDFIN": "Mandatory Finish",
    "CS_MANDSTART": "Mandatory Start",
    "CS_MSO": "Start On",
    "CS_MSOA": "Start On or After",
    "CS_MSOB": "Start On or Before",
}
#: Constraints DCMA treats as "hard" (two-sided: pin the date in both directions).
HARD_CONSTRAINTS = frozenset({"CS_MANDFIN", "CS_MANDSTART", "CS_MEO", "CS_MSO"})
PRED_TYPE = {
    "PR_FS": "Finish to Start",
    "PR_SS": "Start to Start",
    "PR_FF": "Finish to Finish",
    "PR_SF": "Start to Finish",
}
RSRC_TYPE = {
    "RT_Labor": "Labor",
    "RT_Mat": "Material",
    "RT_Equip": "Nonlabor (Equipment)",
}
DURATION_TYPE = {
    "DT_FixedDrtn": "Fixed Duration & Units/Time",
    "DT_FixedQty": "Fixed Units",
    "DT_FixedDUR2": "Fixed Duration & Units",
    "DT_FixedRate": "Fixed Units/Time",
}
COMPLETE_PCT_TYPE = {
    "CP_Phys": "Physical",
    "CP_Drtn": "Duration",
    "CP_Units": "Units",
}
CRITICAL_PATH_TYPE = {
    "CT_TotFloat": "Total Float",
    "CT_DrivPath": "Longest Path",
}
CLNDR_TYPE = {
    "CA_Base": "Global",
    "CA_Project": "Project",
    "CA_Rsrc": "Resource",
}
WBS_STATUS = {
    "WS_Open": "Active",
    "WS_Closed": "Inactive",
    "WS_Planned": "Planned",
    "WS_NotStarted": "What-If",
}
EV_COMPUTE_TYPE = {
    "EC_Cmp_pct": "Activity Percent Complete",
    "EC_Milestone_pct": "WBS Milestones Percent Complete",
    "EC_Zero_pct": "0/100 Percent Complete",
    "EC_Fifty_pct": "50/50 Percent Complete",
    "EC_Custom_pct": "Custom Percent Complete",
    "EC_Eff": "Planned Value with Planned Dates",
}
UDF_DATA_TYPE = {
    "FT_TEXT": "Text",
    "FT_FLOAT": "Number",
    "FT_INT": "Integer",
    "FT_MONEY": "Cost",
    "FT_START_DATE": "Start Date",
    "FT_END_DATE": "Finish Date",
    "FT_STATICTYPE": "Indicator",
    "FT_FLOAT_2_DECIMALS": "Number (2 decimals)",
}

ENUMS: dict[str, dict[str, str]] = {
    "task_type": TASK_TYPE,
    "status_code": STATUS_CODE,
    "cstr_type": CSTR_TYPE,
    "pred_type": PRED_TYPE,
    "rsrc_type": RSRC_TYPE,
    "duration_type": DURATION_TYPE,
    "complete_pct_type": COMPLETE_PCT_TYPE,
    "critical_path_type": CRITICAL_PATH_TYPE,
    "clndr_type": CLNDR_TYPE,
    "wbs_status": WBS_STATUS,
    "ev_compute_type": EV_COMPUTE_TYPE,
    "udf_data_type": UDF_DATA_TYPE,
}


def label_of(vocab: dict[str, str], code: str | None) -> str | None:
    """Human label for a P6 code; unknown codes pass through verbatim."""
    if code is None:
        return None
    return vocab.get(code, code)


# ---------------------------------------------------------------------------
# Entity base
# ---------------------------------------------------------------------------


class Entity:
    """A typed view over one raw table row (raw strings stay authoritative)."""

    __slots__ = ("_table", "row")

    def __init__(self, table: Table, row: list[str]) -> None:
        self._table = table
        self.row = row

    def f(self, name: str) -> Any:
        """Typed field value (None when blank/absent)."""
        return self._table.value(self.row, name)

    def raw(self, name: str) -> str:
        """Raw string value ('' when blank/absent)."""
        return self._table.raw(self.row, name)

    def set(self, name: str, value: Any) -> None:
        """Write a value back into raw storage (used by the mutation layer)."""
        self._table.set(self.row, name, value)

    def date(self, name: str) -> datetime | None:
        v = self.f(name)
        return v if isinstance(v, datetime) else None

    def num(self, name: str, default: float = 0.0) -> float:
        v = self.f(name)
        return float(v) if isinstance(v, (int, float)) else default

    def to_dict(self, fields: list[str] | None = None) -> dict[str, Any]:
        """Serialize (all or selected) fields with typed values."""
        names = fields if fields is not None else self._table.fields
        return {n: self.f(n) for n in names if self._table.has_field(n)}
