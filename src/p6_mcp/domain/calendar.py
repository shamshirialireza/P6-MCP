"""Calendar entity with working-time arithmetic.

All schedule math (CPM, time-phasing, variance in days) flows through this
class, so durations are always calendar-aware — never a hard-coded 8 h/day.
P6 weekday numbering is 1=Sunday .. 7=Saturday.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from p6_mcp.domain.base import CLNDR_TYPE, Entity, label_of
from p6_mcp.parser.calendar_data import ParsedCalendar, WorkShift, parse_calendar_data

_MAX_SCAN_DAYS = 40_000  # ~110 years safety bound for empty/pathological calendars
_FALLBACK_SHIFTS = [WorkShift(time(8, 0), time(16, 0))]


def _p6_weekday(d: date) -> int:
    """Python date -> P6 weekday (1=Sunday..7=Saturday)."""
    return (d.weekday() + 1) % 7 + 1


class Calendar(Entity):
    """One CALENDAR row plus parsed workweek/exception data and math helpers."""

    __slots__ = ("_parsed", "_empty_workweek")

    def __init__(self, table: object, row: list[str]) -> None:  # type: ignore[override]
        super().__init__(table, row)  # type: ignore[arg-type]
        self._parsed: ParsedCalendar | None = None
        self._empty_workweek = False

    # -- identity ----------------------------------------------------------

    @property
    def clndr_id(self) -> int:
        return int(self.num("clndr_id"))

    @property
    def name(self) -> str:
        return self.raw("clndr_name")

    @property
    def clndr_type(self) -> str | None:
        return self.f("clndr_type")

    @property
    def type_label(self) -> str | None:
        return label_of(CLNDR_TYPE, self.clndr_type)

    @property
    def base_clndr_id(self) -> int | None:
        v = self.f("base_clndr_id")
        return int(v) if v is not None else None

    @property
    def parsed(self) -> ParsedCalendar:
        """Lazily parsed clndr_data. Falls back to Mon-Fri 08-16 when empty."""
        if self._parsed is None:
            p = parse_calendar_data(self.raw("clndr_data"))
            if not any(p.workweek.get(d) for d in range(1, 8)):
                self._empty_workweek = True
                for d in range(2, 7):  # Monday..Friday
                    p.workweek[d] = list(_FALLBACK_SHIFTS)
            self._parsed = p
        return self._parsed

    @property
    def used_fallback_workweek(self) -> bool:
        _ = self.parsed
        return self._empty_workweek

    @property
    def day_hours(self) -> float:
        """Nominal hours/day for hour<->day conversion (day_hr_cnt, else derived)."""
        v = self.num("day_hr_cnt")
        if v > 0:
            return v
        week = self.parsed.week_hours()
        working_days = sum(1 for d in range(1, 8) if self.parsed.workweek.get(d))
        if week > 0 and working_days > 0:
            return week / working_days
        return 8.0

    @property
    def week_hours(self) -> float:
        v = self.num("week_hr_cnt")
        return v if v > 0 else self.parsed.week_hours()

    # -- day-level ---------------------------------------------------------

    def shifts_on(self, d: date) -> list[WorkShift]:
        """Working shifts on a calendar date (exceptions override the workweek)."""
        p = self.parsed
        if d in p.exceptions:
            return p.exceptions[d]
        return p.workweek.get(_p6_weekday(d), [])

    def is_working_day(self, d: date) -> bool:
        return bool(self.shifts_on(d))

    def work_hours_on(self, d: date) -> float:
        return sum(s.hours for s in self.shifts_on(d))

    def next_working_day(self, d: date) -> date:
        for _ in range(_MAX_SCAN_DAYS):
            if self.is_working_day(d):
                return d
            d += timedelta(days=1)
        return d

    def add_working_days(self, start: date, days: int) -> date:
        """Date after consuming ``days`` full working days (0 -> next working day)."""
        d = self.next_working_day(start)
        step = 1 if days >= 0 else -1
        remaining = abs(days)
        while remaining > 1:
            d += timedelta(days=step)
            for _ in range(_MAX_SCAN_DAYS):
                if self.is_working_day(d):
                    break
                d += timedelta(days=step)
            remaining -= 1
        return d

    def working_days_between(self, start: date, end: date) -> int:
        """Count of working days in [start, end] inclusive (negative if reversed)."""
        if end < start:
            return -self.working_days_between(end, start)
        count, d = 0, start
        while d <= end:
            if self.is_working_day(d):
                count += 1
            d += timedelta(days=1)
        return count

    # -- hour-level --------------------------------------------------------

    def _day_worked_minutes(self, d: date, lo: datetime, hi: datetime) -> float:
        total = 0.0
        for s in self.shifts_on(d):
            s_start = datetime.combine(d, s.start)
            finish = s.finish
            s_end = (
                datetime.combine(d + timedelta(days=1), time(0))
                if finish == time(0) and s.start != time(0)
                else datetime.combine(d, finish)
            )
            a, b = max(s_start, lo), min(s_end, hi)
            if b > a:
                total += (b - a).total_seconds() / 60.0
        return total

    def work_hours_between(self, start: datetime, end: datetime) -> float:
        """Working hours in [start, end); negative when end < start."""
        if end < start:
            return -self.work_hours_between(end, start)
        minutes, d = 0.0, start.date()
        while d <= end.date():
            minutes += self._day_worked_minutes(d, start, end)
            d += timedelta(days=1)
        return minutes / 60.0

    def next_work_time(self, dt: datetime) -> datetime:
        """Earliest working instant at or after ``dt``."""
        d = dt.date()
        for _ in range(_MAX_SCAN_DAYS):
            for s in self.shifts_on(d):
                s_start = datetime.combine(d, s.start)
                s_end = datetime.combine(d, s.finish)
                if s.finish == time(0) and s.start != time(0):
                    s_end = datetime.combine(d + timedelta(days=1), time(0))
                if dt < s_end:
                    return max(dt, s_start)
            d += timedelta(days=1)
            dt = datetime.combine(d, time(0))
        return dt

    def prev_work_time(self, dt: datetime) -> datetime:
        """Latest working instant at or before ``dt``."""
        d = dt.date()
        for _ in range(_MAX_SCAN_DAYS):
            for s in reversed(self.shifts_on(d)):
                s_start = datetime.combine(d, s.start)
                s_end = datetime.combine(d, s.finish)
                if s.finish == time(0) and s.start != time(0):
                    s_end = datetime.combine(d + timedelta(days=1), time(0))
                if dt > s_start:
                    return min(dt, s_end)
            d -= timedelta(days=1)
            dt = datetime.combine(d, time(23, 59, 59))
        return dt

    def add_work_hours(self, start: datetime, hours: float) -> datetime:
        """Instant reached after consuming ``hours`` working hours from ``start``.

        Positive moves forward, negative moves backward; 0 returns ``start``.
        """
        if hours == 0:
            return start
        if hours < 0:
            return self._sub_work_hours(start, -hours)
        remaining = hours * 60.0
        dt = self.next_work_time(start)
        d = dt.date()
        for _ in range(_MAX_SCAN_DAYS):
            for s in self.shifts_on(d):
                s_start = datetime.combine(d, s.start)
                s_end = datetime.combine(d, s.finish)
                if s.finish == time(0) and s.start != time(0):
                    s_end = datetime.combine(d + timedelta(days=1), time(0))
                lo = max(dt, s_start)
                if lo >= s_end:
                    continue
                avail = (s_end - lo).total_seconds() / 60.0
                if remaining <= avail + 1e-9:
                    return lo + timedelta(minutes=remaining)
                remaining -= avail
            d += timedelta(days=1)
            dt = datetime.combine(d, time(0))
        return dt

    def _sub_work_hours(self, end: datetime, hours: float) -> datetime:
        remaining = hours * 60.0
        dt = self.prev_work_time(end)
        d = dt.date()
        for _ in range(_MAX_SCAN_DAYS):
            for s in reversed(self.shifts_on(d)):
                s_start = datetime.combine(d, s.start)
                s_end = datetime.combine(d, s.finish)
                if s.finish == time(0) and s.start != time(0):
                    s_end = datetime.combine(d + timedelta(days=1), time(0))
                hi = min(dt, s_end)
                if hi <= s_start:
                    continue
                avail = (hi - s_start).total_seconds() / 60.0
                if remaining <= avail + 1e-9:
                    return hi - timedelta(minutes=remaining)
                remaining -= avail
            d -= timedelta(days=1)
            dt = datetime.combine(d, time(23, 59, 59))
        return dt

    def hours_to_days(self, hours: float | None) -> float | None:
        """Convert an hour count to calendar days using this calendar's day length."""
        if hours is None:
            return None
        dh = self.day_hours
        return hours / dh if dh else None

    def exceptions_list(self) -> list[dict[str, object]]:
        """Exceptions as serializable dicts (date, working flag, hours, shifts)."""
        out: list[dict[str, object]] = []
        for d, shifts in sorted(self.parsed.exceptions.items()):
            out.append(
                {
                    "date": d.isoformat(),
                    "working": bool(shifts),
                    "hours": sum(s.hours for s in shifts),
                    "shifts": [
                        {"start": s.start.strftime("%H:%M"), "finish": s.finish.strftime("%H:%M")}
                        for s in shifts
                    ],
                }
            )
        return out

    def workweek_dict(self) -> dict[str, list[dict[str, str]]]:
        """Standard week as day-name → shift list."""
        names = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
        return {
            names[d - 1]: [
                {"start": s.start.strftime("%H:%M"), "finish": s.finish.strftime("%H:%M")}
                for s in self.parsed.workweek.get(d, [])
            ]
            for d in range(1, 8)
        }
