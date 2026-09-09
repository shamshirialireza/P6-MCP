"""§5.10 Cost and earned-value tools."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.parser.coercion import parse_date
from p6_mcp.services.analysis.cost import cash_flow, cost_summary
from p6_mcp.services.analysis.earned_value import earned_value
from p6_mcp.services.query.serialize import iso


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register cost and EVM tools."""

    @mcp.tool(title="Get cost summary", annotations=READ_ONLY)
    @tool_errors
    def get_cost_summary(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        group_by: str = "wbs",
        code_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Budgeted, actual, remaining, and at-completion cost grouped by wbs,
        resource, role, account, activity_code, expense_category, or activity.

        Totals also split the budget into labor / nonlabor / material / expense.
        Note: grouping by resource, role, or account attributes an activity's
        whole cost to each matching key, so those groups can sum above the total.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        res = cost_summary(sch, projects, group_by, code_type)
        groups = res.pop("groups")
        return ctx.page(iso(groups), limit, offset, extra=iso(res))

    @mcp.tool(title="Get cash flow", annotations=READ_ONLY)
    @tool_errors
    def get_cash_flow(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        period: str = "month",
        include_expenses: bool = True,
    ) -> dict[str, Any]:
        """Time-phased planned, actual, and remaining cost per period with
        cumulative columns — the S-curve data.

        Cost is spread across calendar working hours, not evenly across
        calendar days, so holidays and non-working weeks show up correctly.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        return ctx.guard(cash_flow(sch, projects, period, include_expenses))

    @mcp.tool(title="Get earned value", annotations=READ_ONLY)
    @tool_errors
    def get_earned_value(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        as_of: str | None = None,
        ev_method: str = "from_p6_settings",
        eac_method: str = "cpi",
        time_phased: bool = True,
        period: str = "month",
    ) -> dict[str, Any]:
        """Full earned-value analysis: BAC, PV, EV, AC, CV, SV, CPI, SPI, EAC,
        ETC, VAC, TCPI, percent complete and percent spent, plus a per-WBS
        breakdown.

        PV is time-phased to the data date — the budgeted cost of work that
        *should* be done by now — not the total budget. Baseline dates drive PV
        when a baseline project exists in the file; otherwise planned dates are
        used and the result carries a `note` saying so.

        ev_method: from_p6_settings (honors each activity's complete_pct_type),
        physical, duration, units, or activity_pct.
        eac_method: cpi, spi_cpi, remaining, or bac_ac_plus_etc. All four are
        also returned under `eac_all_methods` for comparison.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        return ctx.guard(
            earned_value(
                sch,
                projects,
                parse_date(as_of) if as_of else None,
                ev_method,
                eac_method,
                time_phased,
                period,
            )
        )

    @mcp.tool(title="Get earned value curve", annotations=READ_ONLY)
    @tool_errors
    def get_earned_value_curve(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        period: str = "month",
    ) -> dict[str, Any]:
        """Cumulative PV, EV, and AC series for plotting the three EVM curves."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        ev = earned_value(sch, projects, time_phased=True, period=period)
        flow = cash_flow(sch, projects, period)
        pv_rows = {r["period"]: r for r in ev.get("pv_curve", [])}
        rows = []
        cum_ac = 0.0
        for r in flow["periods"]:
            label = r["period"]
            cum_ac += float(r.get("actual_cost") or 0)
            pv_row = pv_rows.get(label, {})
            rows.append(
                {
                    "period": label,
                    "pv": pv_row.get("pv", 0.0),
                    "cumulative_pv": pv_row.get("cumulative_pv"),
                    "ac": r.get("actual_cost", 0.0),
                    "cumulative_ac": round(cum_ac, 2),
                }
            )
        return ctx.guard(
            {
                "period": period,
                "metrics": ev["metrics"],
                "curve": rows,
                "note": ev.get("note"),
            }
        )

    @mcp.tool(title="Get financial periods", annotations=READ_ONLY)
    @tool_errors
    def get_financial_periods(file_path: str) -> dict[str, Any]:
        """Financial period calendar (FINDATES) used for past-period actuals."""
        sch = ctx.schedule(file_path)
        rows = sorted(
            sch.table("FINDATES").iter_dicts(),
            key=lambda d: str(d.get("start_date") or ""),
        )
        return ctx.guard({"total": len(rows), "items": iso(rows)})

    @mcp.tool(title="Get past period actuals", annotations=READ_ONLY)
    @tool_errors
    def get_past_period_actuals(
        file_path: str,
        task_code: str | None = None,
        resource: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Stored period actuals by financial period: TASKFIN (activity level)
        and TRSRCFIN (assignment level).

        This is how P6 preserves what was earned in each past period, which
        matters when actuals have been re-baselined since.
        """
        sch = ctx.schedule(file_path)
        periods = {
            int(d["fin_dates_id"]): d.get("fin_dates_name")
            for d in sch.table("FINDATES").iter_dicts()
            if d.get("fin_dates_id") is not None
        }
        rows: list[dict[str, Any]] = []
        for source, table in (
            ("TASKFIN", sch.table("TASKFIN")),
            ("TRSRCFIN", sch.table("TRSRCFIN")),
        ):
            for d in table.iter_dicts():
                tid = d.get("task_id")
                act = sch.activities_by_id.get(int(tid)) if tid is not None else None
                if task_code and (act is None or act.code != task_code):
                    continue
                if resource:
                    r = sch.resolve_resource(resource)
                    if d.get("rsrc_id") != r.rsrc_id:
                        continue
                rows.append(
                    {
                        "source": source,
                        "task_code": act.code if act else tid,
                        "financial_period": periods.get(int(d.get("fin_dates_id") or 0)),
                        **d,
                    }
                )
        return ctx.page(iso(rows), limit, offset)

    _ = (
        get_cost_summary,
        get_cash_flow,
        get_earned_value,
        get_earned_value_curve,
        get_financial_periods,
        get_past_period_actuals,
    )
