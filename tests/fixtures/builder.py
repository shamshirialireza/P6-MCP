"""Deterministic XER fixture builder used by tests and scripts.

Intentionally independent of ``p6_mcp`` internals (its own working-day math),
so fixtures cross-validate the product's parser and CPM engine.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

HOLIDAYS = {date(2024, 1, 1), date(2024, 12, 25)}
DATA_DATE = datetime(2024, 2, 5, 8, 0)
DAY_HOURS = 8.0

CLNDR_DATA_5D = (
    "(0||CalendarData()((0||DaysOfWeek()("
    "(0||1()())"
    + "".join(f"(0||{d}()((0||0(s|08:00|f|16:00)())))" for d in range(2, 7))
    + "(0||7()())"
    "))(0||Exceptions()((0||0(d|45292)())(0||1(d|45651)())))))"
)  # 45292 = 2024-01-01, 45651 = 2024-12-25
CLNDR_DATA_7D = (
    "(0||CalendarData()((0||DaysOfWeek()("
    + "".join(f"(0||{d}()((0||0(s|08:00|f|16:00)())))" for d in range(1, 8))
    + "))(0||Exceptions()())))"
)


def is_workday(d: date) -> bool:
    return d.weekday() < 5 and d not in HOLIDAYS


def next_workday(d: date) -> date:
    while not is_workday(d):
        d += timedelta(days=1)
    return d


def add_workdays(start: date, days: int) -> date:
    """Date reached after consuming ``days`` full working days starting at ``start``."""
    d = next_workday(start)
    remaining = days
    while remaining > 1:
        d = next_workday(d + timedelta(days=1))
        remaining -= 1
    return d


def span(start_day: date, dur_days: int) -> tuple[datetime, datetime]:
    """(start 08:00, finish 16:00) of a ``dur_days`` activity beginning start_day."""
    s = next_workday(start_day)
    f = add_workdays(s, dur_days)
    return datetime.combine(s, time(8)), datetime.combine(f, time(16))


def after(finish: datetime, lag_days: int = 0) -> date:
    """First candidate start date for an FS successor of an activity finishing ``finish``."""
    d = finish.date() + timedelta(days=1)
    d = next_workday(d)
    for _ in range(lag_days):
        d = next_workday(d + timedelta(days=1))
    return d


def fmt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def _dt(m: int, d: int, h: int = 8) -> datetime:
    return datetime(2024, m, d, h)


#: Hand-verified CPM truth for incomplete DEMO activities:
#: code -> (early_start, early_finish, late_start, late_finish, total_float_hours)
EXPECTED_CPM: dict[str, tuple[datetime, datetime, datetime, datetime, float]] = {
    "A1030": (_dt(2, 5), _dt(2, 14, 16), _dt(2, 5), _dt(2, 14, 16), 0.0),
    "A1040": (_dt(2, 15), _dt(2, 21, 16), _dt(2, 15), _dt(2, 21, 16), 0.0),
    "A1050": (_dt(2, 5), _dt(4, 8, 16), _dt(2, 27), _dt(4, 8, 16), 128.0),
    "A2010": (_dt(2, 5), _dt(2, 6, 16), _dt(2, 19), _dt(2, 20, 16), 80.0),
    "A2020": (_dt(2, 7), _dt(2, 8, 16), _dt(2, 21), _dt(2, 22, 16), 80.0),
    "A2030": (_dt(2, 9), _dt(2, 29, 16), _dt(2, 23), _dt(3, 14, 16), 80.0),
    "A3000": (_dt(2, 22), _dt(2, 28, 16), _dt(2, 22), _dt(2, 28, 16), 0.0),
    "A3010": (_dt(2, 29), _dt(3, 13, 16), _dt(2, 29), _dt(3, 13, 16), 0.0),
    "A3020": (_dt(3, 14), _dt(3, 25, 16), _dt(3, 14), _dt(3, 25, 16), 0.0),
    "A3030": (_dt(2, 29), _dt(3, 11, 16), _dt(3, 14), _dt(3, 25, 16), 80.0),
    "A3040": (_dt(3, 26), _dt(4, 1, 16), _dt(3, 26), _dt(4, 1, 16), 0.0),
    "A3050": (_dt(4, 4), _dt(4, 8, 16), _dt(4, 4), _dt(4, 8, 16), 0.0),
    "A3060": (_dt(2, 22), _dt(3, 27, 16), _dt(3, 5), _dt(4, 8, 16), 64.0),
    "A9000": (_dt(4, 8, 16), _dt(4, 8, 16), _dt(4, 8, 16), _dt(4, 8, 16), 0.0),
}

#: Project-level truth for golden tests.
EXPECTED_PROJECT_FINISH = _dt(4, 8, 16)


class XerBuilder:
    """Accumulates tables/rows and renders XER text."""

    def __init__(self, version: str = "19.12", currency: str = "USD") -> None:
        self.header = [
            version, "2024-02-05", "Project", "admin", "Fixture User",
            "fixturedb", "Project Management", currency,
        ]
        self._tables: dict[str, tuple[list[str], list[dict[str, str]]]] = {}

    def add(self, table: str, fields: list[str], *rows: dict[str, object]) -> None:
        if table not in self._tables:
            self._tables[table] = (fields, [])
        for row in rows:
            self._tables[table][1].append({k: self._s(v) for k, v in row.items()})

    @staticmethod
    def _s(v: object) -> str:
        if v is None:
            return ""
        if isinstance(v, bool):
            return "Y" if v else "N"
        if isinstance(v, datetime):
            return fmt(v)
        if isinstance(v, float) and v.is_integer():
            return str(int(v))
        return str(v)

    def render(self, line_ending: str = "\r\n") -> str:
        lines = ["ERMHDR\t" + "\t".join(self.header)]
        for name, (fields, rows) in self._tables.items():
            lines.append("%T\t" + name)
            lines.append("%F\t" + "\t".join(fields))
            for row in rows:
                lines.append("%R\t" + "\t".join(row.get(f, "") for f in fields))
        lines.append("%E")
        return line_ending.join(lines) + line_ending


TASK_FIELDS = [
    "task_id", "proj_id", "wbs_id", "clndr_id", "phys_complete_pct", "rev_fdbk_flag",
    "est_wt", "lock_plan_flag", "auto_compute_act_flag", "complete_pct_type",
    "task_type", "duration_type", "status_code", "task_code", "task_name", "rsrc_id",
    "total_float_hr_cnt", "free_float_hr_cnt", "remain_drtn_hr_cnt", "act_work_qty",
    "remain_work_qty", "target_work_qty", "target_drtn_hr_cnt", "target_equip_qty",
    "act_equip_qty", "remain_equip_qty", "cstr_date", "act_start_date", "act_end_date",
    "late_start_date", "late_end_date", "expect_end_date", "early_start_date",
    "early_end_date", "restart_date", "reend_date", "target_start_date",
    "target_end_date", "rem_late_start_date", "rem_late_end_date", "cstr_type",
    "priority_type", "suspend_date", "resume_date", "float_path", "float_path_order",
    "guid", "tmpl_guid", "cstr_date2", "cstr_type2", "driving_path_flag",
    "act_this_per_work_qty", "act_this_per_equip_qty", "external_early_start_date",
    "external_late_end_date", "create_date", "update_date", "create_user",
    "update_user", "location_id", "control_updates_flag",
]

PROJECT_FIELDS = [
    "proj_id", "fy_start_month_num", "rsrc_self_add_flag", "allow_complete_flag",
    "rsrc_multi_assign_flag", "checkout_flag", "project_flag", "chng_eff_cmp_pct_flag",
    "batch_sum_flag", "name_sep_char", "def_complete_pct_type", "proj_short_name",
    "acct_id", "orig_proj_id", "source_proj_id", "base_type_id", "clndr_id",
    "sum_base_proj_id", "task_code_base", "task_code_step", "priority_num",
    "wbs_max_sum_level", "strgy_priority_num", "last_checksum", "critical_drtn_hr_cnt",
    "def_cost_per_qty", "last_recalc_date", "plan_start_date", "plan_end_date",
    "scd_end_date", "add_date", "fcst_start_date", "def_duration_type",
    "task_code_prefix", "guid", "def_qty_type", "add_by_name", "web_local_root_path",
    "proj_url", "def_rate_type", "add_act_remain_flag", "act_this_per_link_flag",
    "def_task_type", "act_pct_link_flag", "critical_path_type", "task_code_prefix_flag",
    "def_rollup_dates_flag", "use_project_baseline_flag", "rem_target_link_flag",
    "reset_planned_flag", "allow_neg_act_flag", "sum_assign_level",
    "last_baseline_update_date", "apply_actuals_date", "location_id", "next_data_date",
]

PROJWBS_FIELDS = [
    "wbs_id", "proj_id", "obs_id", "seq_num", "est_wt", "proj_node_flag",
    "sum_data_flag", "status_code", "wbs_short_name", "wbs_name", "phase_id",
    "parent_wbs_id", "ev_user_pct", "ev_etc_user_value", "orig_cost",
    "indep_remain_total_cost", "ann_dscnt_rate_pct", "dscnt_period_type",
    "indep_remain_work_qty", "anticip_start_date", "anticip_end_date",
    "ev_compute_type", "ev_etc_compute_type", "guid", "plan_open_state",
]

CALENDAR_FIELDS = [
    "clndr_id", "default_flag", "clndr_name", "proj_id", "base_clndr_id",
    "last_chng_date", "clndr_type", "day_hr_cnt", "week_hr_cnt", "month_hr_cnt",
    "year_hr_cnt", "rsrc_private", "clndr_data",
]

RSRC_FIELDS = [
    "rsrc_id", "parent_rsrc_id", "clndr_id", "role_id", "shift_id", "user_id",
    "pobs_id", "guid", "rsrc_seq_num", "email_addr", "employee_code", "office_phone",
    "other_phone", "rsrc_name", "rsrc_short_name", "rsrc_title_name", "def_qty_per_hr",
    "cost_qty_type", "ot_factor", "active_flag", "auto_compute_act_flag",
    "def_cost_qty_link_flag", "ot_flag", "curr_id", "unit_id", "rsrc_type",
    "location_id", "rsrc_notes", "load_tasks_flag", "level_flag",
]

TASKRSRC_FIELDS = [
    "taskrsrc_id", "task_id", "proj_id", "cost_qty_link_flag", "role_id", "acct_id",
    "rsrc_id", "pobs_id", "skill_level", "remain_qty", "target_qty",
    "remain_qty_per_hr", "target_lag_drtn_hr_cnt", "target_qty_per_hr", "act_ot_qty",
    "act_reg_qty", "relag_drtn_hr_cnt", "ot_factor", "cost_per_qty", "target_cost",
    "act_reg_cost", "act_ot_cost", "remain_cost", "act_start_date", "act_end_date",
    "restart_date", "reend_date", "target_start_date", "target_end_date",
    "rem_late_start_date", "rem_late_end_date", "rollup_dates_flag", "target_crv",
    "remain_crv", "actual_crv", "ts_pend_act_end_flag", "guid", "rate_type",
    "act_this_per_cost", "act_this_per_qty", "curv_id", "rsrc_type",
    "cost_per_qty_source_type", "cpq_link_type", "cbs_id", "has_rsrchours",
    "taskrsrc_sum_id",
]

TASKPRED_FIELDS = [
    "task_pred_id", "task_id", "pred_task_id", "proj_id", "pred_proj_id", "pred_type",
    "lag_hr_cnt", "float_path", "aref", "arls", "comments",
]


class DemoSchedule:
    """Builds the canonical small demo fixture and records expected values."""

    def __init__(self) -> None:
        self.b = XerBuilder()
        self.next_task_id = 1000
        self.next_pred_id = 5000
        self.next_rsrc_assign_id = 7000
        self.tasks: dict[str, dict[str, object]] = {}  # task_code -> row
        self.expected: dict[str, object] = {"data_date": DATA_DATE}

    def task_id_of(self, code: str) -> int:
        return int(str(self.tasks[code]["task_id"]))

    def add_task(self, code: str, name: str, wbs_id: int, dur_days: int, *,
                 status: str, start_day: date, task_type: str = "TT_Task",
                 float_hours: float = 0.0, cstr_type: str | None = None,
                 cstr_date: datetime | None = None, proj_id: int = 1,
                 clndr_id: int = 10, driving: bool = False,
                 remain_days: int | None = None) -> dict[str, object]:
        tid = self.next_task_id
        self.next_task_id += 1
        es, ef = span(start_day, max(dur_days, 1) if dur_days else 1)
        if task_type in ("TT_Mile", "TT_FinMile"):
            dur_days = 0
            es = datetime.combine(next_workday(start_day), time(8))
            ef = es if task_type == "TT_Mile" else datetime.combine(
                next_workday(start_day), time(16))
        dur_hr = dur_days * DAY_HOURS
        remain_hr = (remain_days * DAY_HOURS if remain_days is not None
                     else (0.0 if status == "TK_Complete" else dur_hr))
        lf = ef if float_hours == 0 else datetime.combine(
            add_workdays(ef.date(), int(float_hours / DAY_HOURS)), time(16))
        ls = es if float_hours == 0 else datetime.combine(
            add_workdays(es.date(), int(float_hours / DAY_HOURS)), time(8))
        row: dict[str, object] = {
            "task_id": tid, "proj_id": proj_id, "wbs_id": wbs_id, "clndr_id": clndr_id,
            "phys_complete_pct": 100 if status == "TK_Complete" else (
                50 if status == "TK_Active" else 0),
            "rev_fdbk_flag": False, "lock_plan_flag": False,
            "auto_compute_act_flag": True, "complete_pct_type": "CP_Drtn",
            "task_type": task_type, "duration_type": "DT_FixedDrtn",
            "status_code": status, "task_code": code, "task_name": name,
            "total_float_hr_cnt": "" if status == "TK_Complete" else float_hours,
            "free_float_hr_cnt": "" if status == "TK_Complete" else 0,
            "remain_drtn_hr_cnt": remain_hr, "target_drtn_hr_cnt": dur_hr,
            "act_work_qty": 0, "remain_work_qty": 0, "target_work_qty": 0,
            "target_start_date": es, "target_end_date": ef,
            "create_user": "admin", "update_user": "admin",
            "create_date": datetime(2024, 1, 1, 9), "update_date": DATA_DATE,
            "driving_path_flag": driving,
        }
        if status == "TK_Complete":
            row.update({"act_start_date": es, "act_end_date": ef})
        elif status == "TK_Active":
            row.update({"act_start_date": es, "early_start_date": DATA_DATE,
                        "early_end_date": ef, "late_start_date": DATA_DATE,
                        "late_end_date": lf})
        else:
            row.update({"early_start_date": es, "early_end_date": ef,
                        "late_start_date": ls, "late_end_date": lf})
        if cstr_type:
            row.update({"cstr_type": cstr_type, "cstr_date": cstr_date})
        self.tasks[code] = row
        return row

    def link(self, pred_code: str, succ_code: str, pred_type: str = "PR_FS",
             lag_hr: float = 0.0) -> None:
        pid = self.next_pred_id
        self.next_pred_id += 1
        self.b.add("TASKPRED", TASKPRED_FIELDS, {
            "task_pred_id": pid, "task_id": self.task_id_of(succ_code),
            "pred_task_id": self.task_id_of(pred_code), "proj_id": 1,
            "pred_proj_id": 1, "pred_type": pred_type, "lag_hr_cnt": lag_hr,
        })

    def assign(self, code: str, rsrc_id: int, qty_hr: float, rate: float,
               rsrc_type: str = "RT_Labor", role_id: int | None = None) -> None:
        aid = self.next_rsrc_assign_id
        self.next_rsrc_assign_id += 1
        t = self.tasks[code]
        status = t["status_code"]
        act_qty = qty_hr if status == "TK_Complete" else (
            qty_hr / 2 if status == "TK_Active" else 0.0)
        rem_qty = qty_hr - act_qty
        self.b.add("TASKRSRC", TASKRSRC_FIELDS, {
            "taskrsrc_id": aid, "task_id": t["task_id"], "proj_id": 1,
            "cost_qty_link_flag": True, "rsrc_id": rsrc_id, "role_id": role_id,
            "remain_qty": rem_qty, "target_qty": qty_hr,
            "target_qty_per_hr": qty_hr / float(str(t["target_drtn_hr_cnt"]) or 1)
            if t["target_drtn_hr_cnt"] else 0,
            "act_reg_qty": act_qty, "act_ot_qty": 0, "ot_factor": 1.5,
            "cost_per_qty": rate, "target_cost": qty_hr * rate,
            "act_reg_cost": act_qty * rate, "act_ot_cost": 0,
            "remain_cost": rem_qty * rate,
            "target_start_date": t["target_start_date"],
            "target_end_date": t["target_end_date"],
            "act_start_date": t.get("act_start_date"),
            "act_end_date": t.get("act_end_date"),
            "rollup_dates_flag": True, "rate_type": "COST_PER_QTY",
            "rsrc_type": rsrc_type, "cost_per_qty_source_type": "ST_Rsrc",
        })

    def _projects(self) -> None:
        self.b.add("PROJECT", PROJECT_FIELDS, {
            "proj_id": 1, "fy_start_month_num": 1, "project_flag": True,
            "proj_short_name": "DEMO", "clndr_id": 10, "sum_base_proj_id": 2,
            "task_code_base": 1000, "task_code_step": 10, "priority_num": 10,
            "wbs_max_sum_level": 2, "critical_drtn_hr_cnt": 0,
            "def_cost_per_qty": 0, "last_recalc_date": DATA_DATE,
            "plan_start_date": datetime(2024, 1, 2, 8),
            "plan_end_date": datetime(2024, 3, 29, 16),
            "scd_end_date": datetime(2024, 3, 26, 16),
            "add_date": datetime(2023, 12, 1, 9),
            "def_duration_type": "DT_FixedDrtn", "task_code_prefix": "A",
            "def_qty_type": "QT_Hour", "add_by_name": "admin",
            "def_rate_type": "COST_PER_QTY", "def_task_type": "TT_Task",
            "critical_path_type": "CT_TotFloat", "allow_neg_act_flag": False,
            "use_project_baseline_flag": True, "def_complete_pct_type": "CP_Drtn",
            "name_sep_char": ".", "sum_assign_level": "SL_Taskrsrc",
            "next_data_date": datetime(2024, 3, 4, 8),
        }, {
            "proj_id": 2, "fy_start_month_num": 1, "project_flag": False,
            "proj_short_name": "DEMO-BL1", "clndr_id": 10, "orig_proj_id": 1,
            "task_code_base": 1000, "task_code_step": 10,
            "last_recalc_date": datetime(2024, 1, 2, 8),
            "plan_start_date": datetime(2024, 1, 2, 8),
            "plan_end_date": datetime(2024, 3, 27, 16),
            "scd_end_date": datetime(2024, 3, 22, 16),
            "add_date": datetime(2024, 1, 2, 9), "def_duration_type": "DT_FixedDrtn",
            "task_code_prefix": "A", "def_complete_pct_type": "CP_Drtn",
            "critical_path_type": "CT_TotFloat", "name_sep_char": ".",
        })

    def _wbs(self) -> None:
        rows = [
            (100, 1, None, "DEMO", "Demo Plant Project", True),
            (101, 1, 100, "ENG", "Engineering", False),
            (102, 1, 100, "PRC", "Procurement", False),
            (103, 1, 100, "CON", "Construction", False),
            (200, 2, None, "DEMO", "Demo Plant Project", True),
            (203, 2, 200, "CON", "Construction", False),
        ]
        for wbs_id, proj, parent, short, name, is_node in rows:
            self.b.add("PROJWBS", PROJWBS_FIELDS, {
                "wbs_id": wbs_id, "proj_id": proj, "obs_id": 101,
                "seq_num": wbs_id, "proj_node_flag": is_node,
                "sum_data_flag": False, "status_code": "WS_Open",
                "wbs_short_name": short, "wbs_name": name,
                "parent_wbs_id": parent, "ev_compute_type": "EC_Cmp_pct",
                "ev_etc_compute_type": "EE_Rem_hr",
            })

    def _activities(self) -> None:
        add, link = self.add_task, None
        # Engineering — complete / in progress around DATA_DATE (Mon 2024-02-05)
        add("A1000", "Notice to Proceed", 101, 0, status="TK_Complete",
            start_day=date(2024, 1, 2), task_type="TT_Mile")
        add("A1010", "Design Criteria", 101, 5, status="TK_Complete",
            start_day=date(2024, 1, 2))
        add("A1020", "Preliminary Design", 101, 10, status="TK_Complete",
            start_day=date(2024, 1, 9))
        add("A1030", "Detailed Design", 101, 15, status="TK_Active",
            start_day=date(2024, 1, 23), remain_days=8)
        add("A1040", "Design Review", 101, 5, status="TK_NotStart",
            start_day=date(2024, 2, 15), float_hours=0)
        add("A1050", "Engineering Management", 101, 45, status="TK_Active",
            start_day=date(2024, 1, 2), task_type="TT_LOE", remain_days=30)
        # Procurement — mixed, with float
        add("A2000", "Issue RFQ", 102, 3, status="TK_Complete",
            start_day=date(2024, 1, 23))
        add("A2010", "Evaluate Bids", 102, 5, status="TK_Active",
            start_day=date(2024, 1, 26), remain_days=2)
        add("A2020", "Award PO", 102, 2, status="TK_NotStart",
            start_day=date(2024, 2, 7), float_hours=40)
        add("A2030", "Fabrication & Delivery", 102, 15, status="TK_NotStart",
            start_day=date(2024, 2, 9), float_hours=40)
        # Construction — not started, critical chain from data date
        add("A3000", "Mobilize", 103, 5, status="TK_NotStart",
            start_day=date(2024, 2, 22), driving=True,
            cstr_type="CS_MSO", cstr_date=datetime(2024, 2, 22, 8))
        add("A3010", "Foundations", 103, 10, status="TK_NotStart",
            start_day=date(2024, 2, 29), driving=True)
        add("A3020", "Structural Steel", 103, 8, status="TK_NotStart",
            start_day=date(2024, 3, 14), driving=True)
        add("A3030", "Site Works", 103, 8, status="TK_NotStart",
            start_day=date(2024, 2, 29), float_hours=64)
        add("A3040", "Finishes", 103, 5, status="TK_NotStart",
            start_day=date(2024, 3, 26), driving=True)
        add("A3050", "Punchlist", 103, 3, status="TK_NotStart",
            start_day=date(2024, 4, 4), driving=True)  # 2d lag after A3040
        add("A3060", "Long Duration Buffer", 103, 25, status="TK_NotStart",
            start_day=date(2024, 2, 22), float_hours=64)
        add("A9000", "Project Complete", 103, 0, status="TK_NotStart",
            start_day=date(2024, 4, 8), task_type="TT_FinMile", driving=True)
        self._apply_cpm_expected()

    def _apply_cpm_expected(self) -> None:
        """Overwrite stored dates/float with hand-verified CPM truth so golden
        tests can assert exact agreement between stored and recomputed values."""
        for code, (es, ef, ls, lf, tf) in EXPECTED_CPM.items():
            row = self.tasks[code]
            row["total_float_hr_cnt"] = tf
            row["late_start_date"] = ls
            row["late_end_date"] = lf
            if row["status_code"] == "TK_Active":
                row["early_start_date"] = es
                row["early_end_date"] = ef
            elif row["status_code"] == "TK_NotStart":
                row["early_start_date"] = es
                row["early_end_date"] = ef
                row["target_start_date"] = es
                row["target_end_date"] = ef

    def _logic(self) -> None:
        for pred, succ, typ, lag in [
            ("A1000", "A1010", "PR_FS", 0), ("A1010", "A1020", "PR_FS", 0),
            ("A1020", "A1030", "PR_FS", 0), ("A1030", "A1040", "PR_FS", 0),
            ("A1000", "A1050", "PR_SS", 0), ("A9000", "A1050", "PR_FF", 0),
            ("A1020", "A2000", "PR_FS", 0), ("A2000", "A2010", "PR_FS", 0),
            ("A2010", "A2020", "PR_FS", 0), ("A2020", "A2030", "PR_FS", 0),
            ("A2030", "A3020", "PR_FS", -8),  # lead on a non-driving link (DCMA #2)
            ("A1040", "A3000", "PR_FS", 0), ("A3000", "A3010", "PR_FS", 0),
            ("A3010", "A3020", "PR_FS", 0), ("A3000", "A3030", "PR_FS", 0),
            ("A3020", "A3040", "PR_FS", 0), ("A3030", "A3040", "PR_FS", 0),
            ("A3040", "A3050", "PR_FS", 16), ("A3050", "A9000", "PR_FS", 0),
            ("A3000", "A3060", "PR_SS", 0),
        ]:
            self.link(pred, succ, typ, lag)

    def _resources(self) -> None:
        self.b.add("ROLES", ["role_id", "parent_role_id", "seq_num", "role_name",
                             "role_short_name", "def_cost_qty_link_flag",
                             "cost_qty_type"],
                   {"role_id": 50, "seq_num": 1, "role_name": "Engineer",
                    "role_short_name": "ENG", "def_cost_qty_link_flag": True,
                    "cost_qty_type": "QT_Hour"})
        rows = [
            (301, "Lead Engineer", "LE", "RT_Labor", 10, 1.0),
            (302, "Construction Crew", "CREW", "RT_Labor", 10, 4.0),
            (303, "Crane", "CRANE", "RT_Equip", 11, 1.0),
            (304, "Concrete", "CONC", "RT_Mat", 10, 0.0),
        ]
        for rid, name, short, typ, cal, qph in rows:
            self.b.add("RSRC", RSRC_FIELDS, {
                "rsrc_id": rid, "clndr_id": cal, "rsrc_seq_num": rid,
                "rsrc_name": name, "rsrc_short_name": short,
                "def_qty_per_hr": qph, "cost_qty_type": "QT_Hour", "ot_factor": 1.5,
                "active_flag": True, "auto_compute_act_flag": True,
                "def_cost_qty_link_flag": True, "ot_flag": False, "curr_id": 1,
                "unit_id": 1 if typ != "RT_Mat" else 2, "rsrc_type": typ,
                "load_tasks_flag": True, "level_flag": False,
                "role_id": 50 if typ == "RT_Labor" else None,
            })
        self.b.add("RSRCRATE",
                   ["rsrc_rate_id", "rsrc_id", "max_qty_per_hr", "cost_per_qty",
                    "start_date", "shift_period_id", "cost_per_qty2", "cost_per_qty3",
                    "cost_per_qty4", "cost_per_qty5"],
                   {"rsrc_rate_id": 401, "rsrc_id": 301, "max_qty_per_hr": 1,
                    "cost_per_qty": 120, "start_date": datetime(2024, 1, 1)},
                   {"rsrc_rate_id": 402, "rsrc_id": 302, "max_qty_per_hr": 4,
                    "cost_per_qty": 65, "start_date": datetime(2024, 1, 1)},
                   {"rsrc_rate_id": 403, "rsrc_id": 303, "max_qty_per_hr": 1,
                    "cost_per_qty": 250, "start_date": datetime(2024, 1, 1)},
                   {"rsrc_rate_id": 404, "rsrc_id": 304, "max_qty_per_hr": 0,
                    "cost_per_qty": 150, "start_date": datetime(2024, 1, 1)})
        for code, rid, qty, rate, typ in [
            ("A1010", 301, 40, 120, "RT_Labor"), ("A1020", 301, 80, 120, "RT_Labor"),
            ("A1030", 301, 120, 120, "RT_Labor"), ("A1040", 301, 40, 120, "RT_Labor"),
            ("A3000", 302, 160, 65, "RT_Labor"), ("A3010", 302, 320, 65, "RT_Labor"),
            ("A3020", 302, 256, 65, "RT_Labor"), ("A3020", 303, 64, 250, "RT_Equip"),
            ("A3030", 302, 256, 65, "RT_Labor"), ("A3040", 302, 160, 65, "RT_Labor"),
            ("A3050", 302, 96, 65, "RT_Labor"),
            ("A3010", 304, 500, 150, "RT_Mat"),
        ]:
            self.assign(code, rid, qty, rate, typ,
                        role_id=50 if typ == "RT_Labor" else None)

    def _codes_udfs(self) -> None:
        self.b.add("ACTVTYPE",
                   ["actv_code_type_id", "actv_short_len", "seq_num",
                    "actv_code_type", "proj_id", "wbs_id", "actv_code_type_scope"],
                   {"actv_code_type_id": 601, "actv_short_len": 10, "seq_num": 1,
                    "actv_code_type": "Phase", "actv_code_type_scope": "AS_Global"},
                   {"actv_code_type_id": 602, "actv_short_len": 10, "seq_num": 2,
                    "actv_code_type": "Responsibility", "proj_id": 1,
                    "actv_code_type_scope": "AS_Project"})
        self.b.add("ACTVCODE",
                   ["actv_code_id", "parent_actv_code_id", "actv_code_type_id",
                    "actv_code_name", "short_name", "seq_num", "color", "total_assignments"],
                   {"actv_code_id": 611, "actv_code_type_id": 601,
                    "actv_code_name": "Engineering", "short_name": "ENG", "seq_num": 1},
                   {"actv_code_id": 612, "actv_code_type_id": 601,
                    "actv_code_name": "Construction", "short_name": "CON", "seq_num": 2},
                   {"actv_code_id": 621, "actv_code_type_id": 602,
                    "actv_code_name": "Alice", "short_name": "AL", "seq_num": 1},
                   {"actv_code_id": 622, "actv_code_type_id": 602,
                    "actv_code_name": "Bob", "short_name": "BO", "seq_num": 2})
        taskactv = []
        for code, actv in [("A1010", 611), ("A1020", 611), ("A1030", 611),
                           ("A1040", 611), ("A3000", 612), ("A3010", 612),
                           ("A3020", 612), ("A3040", 612), ("A1030", 621),
                           ("A3010", 622)]:
            taskactv.append({"task_id": self.task_id_of(code),
                             "actv_code_type_id": 601 if actv < 620 else 602,
                             "actv_code_id": actv, "proj_id": 1})
        self.b.add("TASKACTV",
                   ["task_id", "actv_code_type_id", "actv_code_id", "proj_id"],
                   *taskactv)
        self.b.add("UDFTYPE",
                   ["udf_type_id", "table_name", "udf_type_name", "udf_type_label",
                    "logical_data_type", "super_flag"],
                   {"udf_type_id": 701, "table_name": "TASK",
                    "udf_type_name": "bid_package", "udf_type_label": "Bid Package",
                    "logical_data_type": "FT_TEXT", "super_flag": False},
                   {"udf_type_id": 702, "table_name": "TASK",
                    "udf_type_name": "risk_score", "udf_type_label": "Risk Score",
                    "logical_data_type": "FT_FLOAT", "super_flag": False})
        self.b.add("UDFVALUE",
                   ["udf_type_id", "fk_id", "proj_id", "udf_date", "udf_number",
                    "udf_text", "udf_code_id"],
                   {"udf_type_id": 701, "fk_id": self.task_id_of("A3010"),
                    "proj_id": 1, "udf_text": "BP-CIVIL-01"},
                   {"udf_type_id": 702, "fk_id": self.task_id_of("A3020"),
                    "proj_id": 1, "udf_number": 7.5})

    def _misc(self) -> None:
        self.b.add("SCHEDOPTIONS",
                   ["schedoptions_id", "proj_id", "sched_outer_depend_type",
                    "sched_open_critical_flag", "sched_lag_early_start_flag",
                    "sched_retained_logic", "sched_setplantoforecast",
                    "sched_float_type", "sched_calendar_on_relationship_lag",
                    "sched_use_expect_end_flag", "sched_progress_override",
                    "level_float_thrs_cnt", "level_outer_assign_flag",
                    "sched_use_project_end_date_for_float"],
                   {"schedoptions_id": 801, "proj_id": 1,
                    "sched_outer_depend_type": "SD_Both",
                    "sched_open_critical_flag": False,
                    "sched_lag_early_start_flag": True,
                    "sched_retained_logic": "Y", "sched_setplantoforecast": "N",
                    "sched_float_type": "FT_Fin_Dt",
                    "sched_calendar_on_relationship_lag": "rcal_Predecessor",
                    "sched_use_expect_end_flag": True,
                    "sched_progress_override": "N", "level_float_thrs_cnt": 8,
                    "level_outer_assign_flag": False,
                    "sched_use_project_end_date_for_float": True})
        self.b.add("ACCOUNT",
                   ["acct_id", "parent_acct_id", "acct_seq_num", "acct_name",
                    "acct_short_name", "acct_descr"],
                   {"acct_id": 901, "acct_seq_num": 1, "acct_name": "Direct Labor",
                    "acct_short_name": "DL"},
                   {"acct_id": 902, "acct_seq_num": 2, "acct_name": "Materials",
                    "acct_short_name": "MAT"})
        self.b.add("PROJCOST",
                   ["cost_item_id", "acct_id", "proj_id", "task_id", "cost_type_id",
                    "cost_per_qty", "cost_qty", "cost_load_type", "target_cost",
                    "act_cost", "remain_cost", "cost_name", "cost_descr",
                    "target_start_date", "target_end_date", "vendor_name",
                    "po_number", "auto_compute_act_flag", "cost_type"],
                   {"cost_item_id": 951, "acct_id": 902, "proj_id": 1,
                    "task_id": self.task_id_of("A3010"), "cost_per_qty": 1,
                    "cost_qty": 25000, "cost_load_type": "CL_Uniform",
                    "target_cost": 25000, "act_cost": 0, "remain_cost": 25000,
                    "cost_name": "Rebar Package", "auto_compute_act_flag": True,
                    "cost_type": "Materials"},
                   {"cost_item_id": 952, "acct_id": 901, "proj_id": 1,
                    "task_id": self.task_id_of("A1030"), "cost_per_qty": 1,
                    "cost_qty": 5000, "cost_load_type": "CL_Uniform",
                    "target_cost": 5000, "act_cost": 2500, "remain_cost": 2500,
                    "cost_name": "Design Software", "auto_compute_act_flag": True,
                    "cost_type": "Expenses"})
        self.b.add("MEMOTYPE",
                   ["memo_type_id", "seq_num", "memo_type"],
                   {"memo_type_id": 971, "seq_num": 1, "memo_type": "General"})
        self.b.add("TASKMEMO",
                   ["memo_id", "task_id", "memo_type_id", "proj_id", "task_memo"],
                   {"memo_id": 981, "task_id": self.task_id_of("A3010"),
                    "memo_type_id": 971, "proj_id": 1,
                    "task_memo": "Pour sequence per drawing C-101."})
        self.b.add("WBSSTEP",
                   ["wbs_step_id", "proj_id", "wbs_id", "seq_num", "step_name",
                    "step_wt", "complete_flag"],
                   {"wbs_step_id": 991, "proj_id": 1, "wbs_id": 103, "seq_num": 1,
                    "step_name": "Permits Approved", "step_wt": 1,
                    "complete_flag": False})
        self.b.add("TASKPROC",
                   ["proc_id", "task_id", "proj_id", "seq_num", "proc_name",
                    "complete_flag", "proc_wt", "complete_pct", "proc_descr"],
                   {"proc_id": 992, "task_id": self.task_id_of("A3010"),
                    "proj_id": 1, "seq_num": 1, "proc_name": "Excavate",
                    "complete_flag": False, "proc_wt": 1, "complete_pct": 0,
                    "proc_descr": "Excavate to formation level"})
        self.b.add("FINDATES",
                   ["fin_dates_id", "fin_dates_name", "start_date", "end_date"],
                   *[{"fin_dates_id": 1000 + m, "fin_dates_name": f"2024-{m:02d}",
                      "start_date": datetime(2024, m, 1),
                      "end_date": datetime(2024, m, 28)} for m in range(1, 5)])
        self.b.add("NONWORK",
                   ["nonwork_type_id", "seq_num", "nonwork_code", "nonwork_type"],
                   {"nonwork_type_id": 1101, "seq_num": 1, "nonwork_code": "HOL",
                    "nonwork_type": "Holiday"})
        self.b.add("PHASE", ["phase_id", "seq_num", "phase_name"],
                   {"phase_id": 1201, "seq_num": 1, "phase_name": "Execution"})

    def _baseline(self) -> None:
        # Baseline (proj 2) mirrors the construction chain, two days earlier.
        for code, name, dur, start in [
            ("A1000", "Notice to Proceed", 0, date(2024, 1, 2)),
            ("A1010", "Design Criteria", 5, date(2024, 1, 2)),
            ("A1020", "Preliminary Design", 10, date(2024, 1, 9)),
            ("A1030", "Detailed Design", 15, date(2024, 1, 23)),
            ("A1040", "Design Review", 5, date(2024, 2, 13)),
            ("A3000", "Mobilize", 5, date(2024, 2, 20)),
            ("A3010", "Foundations", 10, date(2024, 2, 27)),
            ("A3020", "Structural Steel", 8, date(2024, 3, 12)),
            ("A3040", "Finishes", 5, date(2024, 3, 22)),
            ("A9000", "Project Complete", 0, date(2024, 4, 3)),
        ]:
            tid = self.next_task_id
            self.next_task_id += 1
            es, ef = span(start, max(dur, 1))
            ttype = {"A9000": "TT_FinMile", "A1000": "TT_Mile"}.get(code, "TT_Task")
            if ttype == "TT_FinMile":
                es = ef = datetime.combine(next_workday(start), time(16))
            elif ttype == "TT_Mile":
                es = ef = datetime.combine(next_workday(start), time(8))
            self.b.add("TASK", TASK_FIELDS, {
                "task_id": tid, "proj_id": 2, "wbs_id": 203, "clndr_id": 10,
                "phys_complete_pct": 0, "complete_pct_type": "CP_Drtn",
                "task_type": ttype, "duration_type": "DT_FixedDrtn",
                "status_code": "TK_NotStart", "task_code": code,
                "task_name": name, "total_float_hr_cnt": 0,
                "remain_drtn_hr_cnt": dur * DAY_HOURS,
                "target_drtn_hr_cnt": dur * DAY_HOURS,
                "early_start_date": es, "early_end_date": ef,
                "late_start_date": es, "late_end_date": ef,
                "target_start_date": es, "target_end_date": ef,
                "driving_path_flag": True,
            })

def build_demo_xer() -> str:
    """The canonical small demo fixture."""
    return _assemble(DemoSchedule())


def _assemble(d: DemoSchedule) -> str:
    d._activities()
    # flush TASK before dependent tables so table order is realistic
    d.b.add("TASK", TASK_FIELDS, *d.tasks.values())
    d.b.add("CURRTYPE",
            ["curr_id", "decimal_digit_cnt", "curr_symbol", "curr_type",
             "curr_short_name", "group_digit_sym", "decimal_sym"],
            {"curr_id": 1, "decimal_digit_cnt": 2, "curr_symbol": "$",
             "curr_type": "US Dollar", "curr_short_name": "USD",
             "group_digit_sym": ",", "decimal_sym": "."})
    d.b.add("OBS", ["obs_id", "parent_obs_id", "guid", "seq_num", "obs_name",
                    "obs_descr"],
            {"obs_id": 100, "seq_num": 1, "obs_name": "Enterprise"},
            {"obs_id": 101, "parent_obs_id": 100, "seq_num": 2,
             "obs_name": "Capital Projects"})
    d.b.add("UMEASURE", ["unit_id", "unit_abbrev", "unit_name", "seq_num"],
            {"unit_id": 1, "unit_abbrev": "h", "unit_name": "Hours", "seq_num": 1},
            {"unit_id": 2, "unit_abbrev": "ea", "unit_name": "Each", "seq_num": 2})
    d.b.add("CALENDAR", CALENDAR_FIELDS,
            {"clndr_id": 10, "default_flag": True, "clndr_name": "Standard 5-Day",
             "clndr_type": "CA_Base", "day_hr_cnt": 8, "week_hr_cnt": 40,
             "month_hr_cnt": 172, "year_hr_cnt": 2000, "rsrc_private": False,
             "last_chng_date": datetime(2024, 1, 1, 9), "clndr_data": CLNDR_DATA_5D},
            {"clndr_id": 11, "default_flag": False, "clndr_name": "7-Day Calendar",
             "clndr_type": "CA_Base", "day_hr_cnt": 8, "week_hr_cnt": 56,
             "month_hr_cnt": 240, "year_hr_cnt": 2920, "rsrc_private": False,
             "last_chng_date": datetime(2024, 1, 1, 9), "clndr_data": CLNDR_DATA_7D})
    d._projects()
    d._wbs()
    d._logic()
    d._resources()
    d._codes_udfs()
    d._misc()
    d._baseline()
    return d.b.render()


def build_large_xer(n_activities: int) -> str:
    """A synthetic large schedule: parallel FS chains of 20 activities each."""
    b = XerBuilder()
    b.add("CALENDAR", CALENDAR_FIELDS,
          {"clndr_id": 10, "default_flag": True, "clndr_name": "Standard",
           "clndr_type": "CA_Base", "day_hr_cnt": 8, "week_hr_cnt": 40,
           "month_hr_cnt": 172, "year_hr_cnt": 2000, "clndr_data": CLNDR_DATA_5D})
    b.add("PROJECT", PROJECT_FIELDS, {
        "proj_id": 1, "project_flag": True, "proj_short_name": "BIG",
        "clndr_id": 10, "last_recalc_date": DATA_DATE,
        "plan_start_date": datetime(2024, 1, 2, 8),
        "critical_path_type": "CT_TotFloat", "def_complete_pct_type": "CP_Drtn",
        "name_sep_char": ".",
    })
    b.add("PROJWBS", PROJWBS_FIELDS, {
        "wbs_id": 100, "proj_id": 1, "proj_node_flag": True, "seq_num": 1,
        "status_code": "WS_Open", "wbs_short_name": "BIG", "wbs_name": "Big Project",
    })
    task_rows: list[dict[str, object]] = []
    pred_rows: list[dict[str, object]] = []
    chain_len = 20
    tid, pid = 1000, 50000
    for i in range(n_activities):
        chain, pos = divmod(i, chain_len)
        start = date(2024, 2, 5) + timedelta(days=7 * pos)
        es, ef = span(start, 5)
        task_rows.append({
            "task_id": tid + i, "proj_id": 1, "wbs_id": 100, "clndr_id": 10,
            "status_code": "TK_NotStart", "task_type": "TT_Task",
            "duration_type": "DT_FixedDrtn", "complete_pct_type": "CP_Drtn",
            "task_code": f"T{i:06d}", "task_name": f"Task {i} chain {chain}",
            "total_float_hr_cnt": 0 if chain == 0 else 40,
            "remain_drtn_hr_cnt": 40, "target_drtn_hr_cnt": 40,
            "early_start_date": es, "early_end_date": ef,
            "late_start_date": es, "late_end_date": ef,
            "target_start_date": es, "target_end_date": ef,
            "phys_complete_pct": 0,
        })
        if pos > 0:
            pred_rows.append({
                "task_pred_id": pid + i, "task_id": tid + i,
                "pred_task_id": tid + i - 1, "proj_id": 1, "pred_proj_id": 1,
                "pred_type": "PR_FS", "lag_hr_cnt": 0,
            })
    b.add("TASK", TASK_FIELDS, *task_rows)
    b.add("TASKPRED", TASKPRED_FIELDS, *pred_rows)
    return b.render()
