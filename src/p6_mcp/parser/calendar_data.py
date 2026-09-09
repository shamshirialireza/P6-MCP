"""Parser for the CALENDAR.clndr_data blob.

The blob is a nested parenthesized structure P6 uses for calendar definitions::

    (0||CalendarData()(
      (0||DaysOfWeek()(
        (0||1()())                                    <- Sunday, non-working
        (0||2()((0||0(s|08:00|f|17:00)()))            <- Monday, 08:00-17:00
        ...
      ))
      (0||Exceptions()(
        (0||0(d|41640)())                             <- holiday (Excel serial date)
        (0||1(d|41650)((0||0(s|08:00|f|12:00)()))     <- working exception, half day
      ))
    ))

Grammar per node: ``( prefix ( data )( children ) )`` where *data* is a
``key|value|key|value`` list and *children* are nodes. Weekday keys are 1..7
with 1 = Sunday. Exception dates are days since 1899-12-30 (Excel serial).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time, timedelta

_EXCEL_EPOCH = date(1899, 12, 30)


@dataclass(slots=True)
class CalendarNode:
    """One node of the clndr_data tree."""

    name: str
    data: dict[str, str] = field(default_factory=dict)
    children: list[CalendarNode] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class WorkShift:
    """A start/finish working period within a day."""

    start: time
    finish: time

    @property
    def hours(self) -> float:
        s = self.start.hour * 60 + self.start.minute
        f = self.finish.hour * 60 + self.finish.minute
        if f == 0 and s > 0:  # 24:00 encoded as 00:00
            f = 24 * 60
        return max(f - s, 0) / 60.0


@dataclass(slots=True)
class ParsedCalendar:
    """Workweek + exceptions extracted from clndr_data."""

    #: weekday (1=Sunday .. 7=Saturday) → shifts; empty list = non-working day.
    workweek: dict[int, list[WorkShift]] = field(default_factory=dict)
    #: exception date → shifts; empty list = full-day holiday.
    exceptions: dict[date, list[WorkShift]] = field(default_factory=dict)

    def day_hours(self, weekday_p6: int) -> float:
        """Working hours for a P6 weekday number (1=Sunday)."""
        return sum(s.hours for s in self.workweek.get(weekday_p6, []))

    def week_hours(self) -> float:
        return sum(self.day_hours(d) for d in range(1, 8))


def _parse_time(raw: str) -> time | None:
    parts = raw.split(":")
    try:
        h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        return None
    if h == 24:
        h = 0
    if 0 <= h <= 23 and 0 <= m <= 59:
        return time(h, m)
    return None


def _parse_node(blob: str, i: int) -> tuple[CalendarNode | None, int]:
    """Parse one ``( prefix ( data )( children ) )`` node starting at ``blob[i]``.

    Returns (node, next_index). A node owns three paren groups — its own, its
    data list, and its children list — and every one must be consumed, or
    sibling nodes leak up into the parent.
    """
    n = len(blob)
    i += 1  # consume the node's opening '('
    j = blob.find("(", i)
    if j == -1:
        return None, n
    prefix = blob[i:j].strip()
    node = CalendarNode(name=prefix.split("|")[-1].strip() if prefix else "")
    k = blob.find(")", j + 1)
    if k == -1:
        return node, n
    data_raw = blob[j + 1 : k]
    if data_raw:
        toks = data_raw.split("|")
        for a in range(0, len(toks) - 1, 2):
            node.data[toks[a].strip()] = toks[a + 1]
    i = k + 1
    if i < n and blob[i] == "(":  # children list
        i += 1
        while i < n and blob[i] != ")":
            if blob[i] == "(":
                child, i = _parse_node(blob, i)
                if child is not None:
                    node.children.append(child)
            else:
                i += 1
        i += 1  # consume the children list's ')'
    if i < n and blob[i] == ")":
        i += 1  # consume the node's own closing ')'
    return node, i


def parse_tree(blob: str) -> CalendarNode:
    """Parse the raw blob into a node tree (tolerant of malformed input)."""
    root = CalendarNode(name="<root>")
    i, n = 0, len(blob)
    while i < n:
        if blob[i] == "(":
            node, i = _parse_node(blob, i)
            if node is not None:
                root.children.append(node)
        else:
            i += 1
    return root


def _shifts_from(node: CalendarNode) -> list[WorkShift]:
    shifts: list[WorkShift] = []
    for child in node.children:
        s, f = child.data.get("s"), child.data.get("f")
        if s is None or f is None:
            continue
        st, ft = _parse_time(s), _parse_time(f)
        if st is not None and ft is not None:
            shifts.append(WorkShift(st, ft))
    shifts.sort(key=lambda w: (w.start, w.finish))
    return shifts


def _walk(node: CalendarNode, name: str) -> CalendarNode | None:
    if node.name == name:
        return node
    for child in node.children:
        found = _walk(child, name)
        if found is not None:
            return found
    return None


def parse_calendar_data(blob: str | None) -> ParsedCalendar:
    """Parse clndr_data into workweek + exceptions; empty result for blank input."""
    result = ParsedCalendar()
    if not blob:
        return result
    tree = parse_tree(blob)
    days = _walk(tree, "DaysOfWeek")
    if days is not None:
        for day_node in days.children:
            try:
                weekday = int(day_node.name)
            except ValueError:
                continue
            if 1 <= weekday <= 7:
                result.workweek[weekday] = _shifts_from(day_node)
    exceptions = _walk(tree, "Exceptions")
    if exceptions is not None:
        for exc_node in exceptions.children:
            serial_raw = exc_node.data.get("d")
            if serial_raw is None:
                continue
            try:
                serial = int(float(serial_raw))
            except ValueError:
                continue
            exc_date = _EXCEL_EPOCH + timedelta(days=serial)
            result.exceptions[exc_date] = _shifts_from(exc_node)
    return result


def serialize_calendar_data(cal: ParsedCalendar) -> str:
    """Serialize a ParsedCalendar back into a clndr_data blob (canonical form)."""

    def shift_children(shifts: list[WorkShift]) -> str:
        return "".join(
            f"(0||{i}(s|{s.start.strftime('%H:%M')}|f|{s.finish.strftime('%H:%M')})())"
            for i, s in enumerate(shifts)
        )

    days = "".join(f"(0||{d}()({shift_children(cal.workweek.get(d, []))}))" for d in range(1, 8))
    excs = "".join(
        f"(0||{i}(d|{(dt - _EXCEL_EPOCH).days})({shift_children(shifts)}))"
        for i, (dt, shifts) in enumerate(sorted(cal.exceptions.items()))
    )
    return f"(0||CalendarData()((0||DaysOfWeek()({days}))(0||Exceptions()({excs}))))"
