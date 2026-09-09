"""Time-phasing: spread quantities/costs across calendar working periods.

Distribution is proportional to *working hours* per the governing calendar
(linear), optionally shaped by a resource curve (RSRCCURVDATA's 21-point
cumulative profile). Buckets are week / month / quarter boundaries.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterator

from p6_mcp.domain.calendar import Calendar
from p6_mcp.exceptions import InvalidArgumentError

PERIODS = ("day", "week", "month", "quarter", "year")


def period_start(d: date, period: str) -> date:
    if period == "day":
        return d
    if period == "week":  # ISO weeks, Monday start
        return d - timedelta(days=d.weekday())
    if period == "month":
        return d.replace(day=1)
    if period == "quarter":
        return d.replace(month=((d.month - 1) // 3) * 3 + 1, day=1)
    if period == "year":
        return d.replace(month=1, day=1)
    raise InvalidArgumentError(f"Unknown period {period!r}", hint=f"Use one of {PERIODS}")


def next_period(d: date, period: str) -> date:
    if period == "day":
        return d + timedelta(days=1)
    if period == "week":
        return d + timedelta(days=7)
    if period == "month":
        return (d.replace(day=28) + timedelta(days=7)).replace(day=1)
    if period == "quarter":
        for _ in range(3):
            d = (d.replace(day=28) + timedelta(days=7)).replace(day=1)
        return d
    return d.replace(year=d.year + 1)


def iter_periods(start: date, end: date, period: str) -> Iterator[tuple[date, date]]:
    """(period_start, period_end_exclusive) buckets covering [start, end]."""
    cur = period_start(start, period)
    while cur <= end:
        nxt = next_period(cur, period)
        yield cur, nxt
        cur = nxt


def period_label(d: date, period: str) -> str:
    if period == "week":
        iso = d.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if period == "month":
        return d.strftime("%Y-%m")
    if period == "quarter":
        return f"{d.year}-Q{(d.month - 1) // 3 + 1}"
    if period == "year":
        return str(d.year)
    return d.isoformat()


def parse_curve(curve_blob: str | None) -> list[float] | None:
    """Parse RSRCCURVDATA pct_usage values (21 points, 0..100 each) into
    normalized incremental weights; None means linear."""
    if not curve_blob:
        return None
    vals: list[float] = []
    for tok in curve_blob.replace("(", " ").replace(")", " ").split():
        try:
            vals.append(float(tok))
        except ValueError:
            continue
    if len(vals) < 2:
        return None
    total = sum(vals)
    if total <= 0:
        return None
    return [v / total for v in vals]


def spread(
    cal: Calendar,
    start: datetime,
    finish: datetime,
    total: float,
    period: str = "month",
    curve: list[float] | None = None,
) -> dict[str, float]:
    """Distribute ``total`` across period buckets between start and finish.

    Returns {period_label: amount}. Instantaneous spans put everything in the
    start bucket.
    """
    out: dict[str, float] = {}
    if total == 0:
        return out
    if finish <= start:
        out[period_label(period_start(start.date(), period), period)] = total
        return out
    total_hours = cal.work_hours_between(start, finish)
    if total_hours <= 0:
        out[period_label(period_start(start.date(), period), period)] = total
        return out
    consumed_hours = 0.0
    for p_start, p_end in iter_periods(start.date(), finish.date(), period):
        lo = max(start, datetime.combine(p_start, datetime.min.time()))
        hi = min(finish, datetime.combine(p_end, datetime.min.time()))
        if hi <= lo:
            continue
        h = cal.work_hours_between(lo, hi)
        if h <= 0:
            continue
        if curve:
            frac = _curve_fraction(curve, consumed_hours / total_hours,
                                   (consumed_hours + h) / total_hours)
            amount = total * frac
        else:
            amount = total * h / total_hours
        consumed_hours += h
        label = period_label(p_start, period)
        out[label] = out.get(label, 0.0) + amount
    return out


def _curve_fraction(curve: list[float], lo_frac: float, hi_frac: float) -> float:
    """Fraction of total falling between two progress fractions per the curve."""
    n = len(curve)
    seg = 1.0 / n
    total = 0.0
    for i, w in enumerate(curve):
        s, e = i * seg, (i + 1) * seg
        overlap = max(0.0, min(e, hi_frac) - max(s, lo_frac))
        if overlap > 0:
            total += w * (overlap / seg)
    return total


def merge_series(target: dict[str, float], addition: dict[str, float]) -> None:
    for k, v in addition.items():
        target[k] = target.get(k, 0.0) + v


def series_to_rows(
    series: dict[str, dict[str, float]], cumulative_keys: tuple[str, ...] = ()
) -> list[dict[str, Any]]:
    """{metric: {label: value}} → sorted rows with optional cumulative columns."""
    labels = sorted({label for m in series.values() for label in m})
    rows: list[dict[str, Any]] = []
    running = dict.fromkeys(cumulative_keys, 0.0)
    for label in labels:
        row: dict[str, Any] = {"period": label}
        for metric, values in series.items():
            v = round(values.get(label, 0.0), 2)
            row[metric] = v
            if metric in running:
                running[metric] += v
                row[f"cumulative_{metric}"] = round(running[metric], 2)
        rows.append(row)
    return rows
