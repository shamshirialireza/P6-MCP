"""§5.11 Calendar tools."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.exceptions import InvalidArgumentError, NotFoundError
from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.parser.coercion import parse_date
from p6_mcp.services.query.serialize import calendar_to_dict, iso


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register calendar tools."""

    def _calendar(sch: Any, ref: str | int) -> Any:
        if isinstance(ref, int) or str(ref).isdigit():
            cal = sch.calendars_by_id.get(int(ref))
            if cal is not None:
                return cal
        needle = str(ref).lower()
        matches = [c for c in sch.calendars if c.name.lower() == needle]
        if not matches:
            raise NotFoundError(
                f"No calendar matching {ref!r}",
                hint="Call get_calendars to list calendars with their ids.",
            )
        return matches[0]

    @mcp.tool(title="Get calendars", annotations=READ_ONLY)
    @tool_errors
    def get_calendars(
        file_path: str, include_workweek: bool = True, include_exceptions: bool = True
    ) -> dict[str, Any]:
        """Every calendar with its type, hours per day/week, standard work week,
        and holiday/exception list parsed out of the clndr_data blob.

        Calendars are the reason a "5 day" duration is not always 5 calendar
        days; every duration and float figure in this server is converted using
        the owning activity's calendar.
        """
        sch = ctx.schedule(file_path)
        return ctx.guard(
            {
                "total": len(sch.calendars),
                "items": [
                    calendar_to_dict(sch, c, include_workweek, include_exceptions)
                    for c in sch.calendars
                ],
            }
        )

    @mcp.tool(title="Get calendar detail", annotations=READ_ONLY)
    @tool_errors
    def get_calendar_detail(file_path: str, calendar: str) -> dict[str, Any]:
        """One calendar in full, including all raw CALENDAR fields.

        `calendar` accepts a clndr_id or a calendar name.
        """
        sch = ctx.schedule(file_path)
        c = _calendar(sch, calendar)
        return ctx.guard(
            {
                **calendar_to_dict(sch, c, True, True),
                "hours_per_period": {
                    "day": c.f("day_hr_cnt"),
                    "week": c.f("week_hr_cnt"),
                    "month": c.f("month_hr_cnt"),
                    "year": c.f("year_hr_cnt"),
                },
                "all_fields": {k: v for k, v in c.to_dict().items() if k != "clndr_data"},
            }
        )

    @mcp.tool(title="Get calendar usage", annotations=READ_ONLY)
    @tool_errors
    def get_calendar_usage(file_path: str) -> dict[str, Any]:
        """How many activities and resources use each calendar.

        A calendar with zero users is dead weight; one used by a handful of
        activities is often where surprising float values come from.
        """
        sch = ctx.schedule(file_path)
        rows = []
        for c in sch.calendars:
            acts = [a for a in sch.activities if a.clndr_id == c.clndr_id]
            rsrcs = [r for r in sch.resources if r.clndr_id == c.clndr_id]
            rows.append(
                {
                    "clndr_id": c.clndr_id,
                    "name": c.name,
                    "type": c.type_label,
                    "activity_count": len(acts),
                    "resource_count": len(rsrcs),
                    "day_hours": c.day_hours,
                    "week_hours": c.week_hours,
                    "sample_activities": sorted(a.code for a in acts)[:5],
                }
            )
        return ctx.guard({"items": iso(rows)})

    @mcp.tool(title="Calendar working days between", annotations=READ_ONLY)
    @tool_errors
    def calendar_working_days_between(
        file_path: str, calendar: str, start: str, end: str
    ) -> dict[str, Any]:
        """Count working days (and hours) between two dates on a given calendar,
        inclusive of both endpoints. Honors holidays and exceptions."""
        sch = ctx.schedule(file_path)
        c = _calendar(sch, calendar)
        s, e = parse_date(start), parse_date(end)
        if s is None or e is None:
            raise InvalidArgumentError(
                "start and end must be dates",
                hint="Use 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM'.",
            )
        days = c.working_days_between(s.date(), e.date())
        return ctx.guard(
            {
                "calendar": c.name,
                "start": s,
                "end": e,
                "working_days": days,
                "working_hours": round(c.work_hours_between(s, e), 2),
                "calendar_days": (e.date() - s.date()).days + 1,
                "non_working_days": ((e.date() - s.date()).days + 1) - days,
            }
        )

    @mcp.tool(title="Calendar add working days", annotations=READ_ONLY)
    @tool_errors
    def calendar_add_working_days(
        file_path: str, calendar: str, start: str, days: int
    ) -> dict[str, Any]:
        """The date reached after consuming N working days from a start date.

        days=1 means the start day itself (a one-day activity starting Monday
        finishes Monday), matching how P6 counts durations.
        """
        sch = ctx.schedule(file_path)
        c = _calendar(sch, calendar)
        s = parse_date(start)
        if s is None:
            raise InvalidArgumentError("start must be a date")
        result = c.add_working_days(s.date(), days)
        return ctx.guard(
            {
                "calendar": c.name,
                "start": s.date(),
                "working_days_added": days,
                "result_date": result,
                "calendar_days_elapsed": (result - s.date()).days,
            }
        )

    @mcp.tool(title="Is working day", annotations=READ_ONLY)
    @tool_errors
    def is_working_day(file_path: str, calendar: str, date: str) -> dict[str, Any]:
        """Whether a date is a working day on a calendar, with its shift hours
        and the reason when it is not."""
        sch = ctx.schedule(file_path)
        c = _calendar(sch, calendar)
        d = parse_date(date)
        if d is None:
            raise InvalidArgumentError("date must be a date")
        day = d.date()
        shifts = c.shifts_on(day)
        is_exception = day in c.parsed.exceptions
        reason = None
        if not shifts:
            reason = "calendar exception (holiday)" if is_exception else "non-working weekday"
        return ctx.guard(
            {
                "calendar": c.name,
                "date": day,
                "is_working_day": bool(shifts),
                "hours": round(c.work_hours_on(day), 2),
                "is_exception": is_exception,
                "reason": reason,
                "shifts": [
                    {"start": s.start.strftime("%H:%M"), "finish": s.finish.strftime("%H:%M")}
                    for s in shifts
                ],
            }
        )

    @mcp.tool(title="Compare calendars", annotations=READ_ONLY)
    @tool_errors
    def compare_calendars(file_path: str, calendar_a: str, calendar_b: str) -> dict[str, Any]:
        """Diff two calendars: hours per day/week, work-week differences, and
        exceptions unique to each.

        Differing calendars across a network are a common cause of float that
        looks wrong but is arithmetically correct.
        """
        sch = ctx.schedule(file_path)
        a, b = _calendar(sch, calendar_a), _calendar(sch, calendar_b)
        week_diff = {}
        for day, label in zip(
            range(1, 8),
            ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
        ):
            ha, hb = a.parsed.day_hours(day), b.parsed.day_hours(day)
            if abs(ha - hb) > 1e-6:
                week_diff[label] = {"a_hours": ha, "b_hours": hb}
        exc_a, exc_b = set(a.parsed.exceptions), set(b.parsed.exceptions)
        return ctx.guard(
            {
                "calendar_a": {
                    "name": a.name,
                    "day_hours": a.day_hours,
                    "week_hours": a.week_hours,
                    "exception_count": len(exc_a),
                },
                "calendar_b": {
                    "name": b.name,
                    "day_hours": b.day_hours,
                    "week_hours": b.week_hours,
                    "exception_count": len(exc_b),
                },
                "workweek_differences": week_diff,
                "exceptions_only_in_a": sorted(d.isoformat() for d in exc_a - exc_b),
                "exceptions_only_in_b": sorted(d.isoformat() for d in exc_b - exc_a),
                "shared_exceptions": len(exc_a & exc_b),
                "identical": not week_diff and exc_a == exc_b,
            }
        )

    _ = (
        get_calendars,
        get_calendar_detail,
        get_calendar_usage,
        calendar_working_days_between,
        calendar_add_working_days,
        is_working_day,
        compare_calendars,
    )
