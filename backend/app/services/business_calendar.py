"""Business calendar and working-day arithmetic (D-28, D-38; Batch 3.3).

The approved rules (DECISION_LOG D-38):

* The EA Governance Office owns the calendar; holders of
  ``admin.business_calendar`` maintain the official Saudi holidays per fiscal
  year (``business_calendar_years``).
* Sunday–Thursday is the default working week (D-28); each fiscal year keeps
  its own working week.
* A reporting period is valid for working-day figures only when **every**
  fiscal year it touches has a confirmed calendar; one working-day duration is
  computable only when every fiscal year it spans is confirmed.
* Otherwise the working-day figure is Not Available — never estimated with
  the default week alone.

The pure helpers carry the rules; the routes only gate, load and audit.
Helpers never commit (the caller owns the session).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_calendar import DEFAULT_WORKING_WEEKDAYS, BusinessCalendarYear
from app.services.fiscal_year import fiscal_year_bounds, fiscal_year_for

#: The fiscal years an administrator may maintain.
MIN_FISCAL_YEAR, MAX_FISCAL_YEAR = 2000, 2100
MAX_HOLIDAYS = 120


class CalendarError(Exception):
    """A calendar edit the rules refuse; ``code`` is the machine-readable reason."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def validate_fiscal_year(fy: int) -> int:
    if not MIN_FISCAL_YEAR <= fy <= MAX_FISCAL_YEAR:
        raise CalendarError("invalid_fiscal_year", f"Fiscal year must be {MIN_FISCAL_YEAR}-2100")
    return fy


def validate_working_weekdays(days: list | None) -> list[int]:
    """ISO weekdays (1-7), at least one, each once; returned sorted Sunday first."""
    if days is None:
        return list(DEFAULT_WORKING_WEEKDAYS)
    if (
        not days
        or any(not isinstance(d, int) or isinstance(d, bool) or not 1 <= d <= 7 for d in days)
        or len(set(days)) != len(days)
    ):
        raise CalendarError("invalid_working_week", "Working days are ISO weekdays 1-7, each once")
    return sorted(days, key=lambda d: d % 7)


def validate_holidays(fy: int, start_month: int, holidays: list | None) -> list[dict]:
    """Each holiday inside the fiscal year, dated once, with a name; sorted by date."""
    start, end = fiscal_year_bounds(fy, start_month)
    out: dict[date, dict] = {}
    for h in holidays or []:
        try:
            day = date.fromisoformat(str(h.get("date")))
        except (ValueError, AttributeError) as err:
            raise CalendarError("invalid_holiday", "A holiday needs a date (YYYY-MM-DD)") from err
        name = str(h.get("name") or "").strip()
        if not name:
            raise CalendarError("invalid_holiday", "A holiday needs a name")
        if not start <= day < end:
            raise CalendarError("holiday_outside_year", f"{day.isoformat()} is not in FY{fy}")
        if day in out:
            raise CalendarError("duplicate_holiday", f"{day.isoformat()} is listed twice")
        out[day] = {"date": day.isoformat(), "name": name[:200]}
    if len(out) > MAX_HOLIDAYS:
        raise CalendarError("too_many_holidays", f"At most {MAX_HOLIDAYS} holidays per year")
    return [out[d] for d in sorted(out)]


def apply_edit(
    row: BusinessCalendarYear, working_weekdays: list[int], holidays: list[dict]
) -> dict:
    """Set a year's week and holidays; return what changed (labels, for the audit).

    A confirmation covers the calendar as it was confirmed: any change to a
    confirmed year withdraws the confirmation, so the year must be confirmed
    again before it counts (I-38)."""
    changes: dict = {}
    if list(row.working_weekdays or []) != working_weekdays:
        changes["working_days"] = {
            "old": weekday_labels(row.working_weekdays or []),
            "new": weekday_labels(working_weekdays),
        }
        row.working_weekdays = working_weekdays
    if list(row.holidays or []) != holidays:
        changes["holiday_count"] = {"old": len(row.holidays or []), "new": len(holidays)}
        row.holidays = holidays
    if changes and row.confirmed:
        changes["confirmed"] = {"old": True, "new": False}
        row.confirmed = False
        row.confirmed_by = None
        row.confirmed_at = None
    return changes


_WEEKDAY_NAMES = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}


def weekday_labels(days: list[int]) -> str:
    return ", ".join(_WEEKDAY_NAMES[d] for d in sorted(days, key=lambda d: d % 7))


@dataclass(frozen=True)
class YearCalendar:
    working_weekdays: frozenset[int]
    holidays: frozenset[date]
    confirmed: bool


@dataclass(frozen=True)
class BusinessCalendar:
    """The calendar as loaded once per request: fiscal year → that year's calendar."""

    start_month: int
    years: dict[int, YearCalendar]

    def fiscal_years(self, start: date, end: date) -> list[int]:
        """Every fiscal year the days ``start``..``end`` (inclusive) touch."""
        first = fiscal_year_for(start, self.start_month)
        last = fiscal_year_for(end, self.start_month)
        return list(range(first, last + 1))

    def unconfirmed(self, fiscal_years: list[int]) -> list[int]:
        return [fy for fy in fiscal_years if not (fy in self.years and self.years[fy].confirmed)]

    def working_days(self, start: datetime | date, end: datetime | date) -> int | None:
        """Working days from ``start`` to ``end``: the working days in
        ``[start date, end date)``, so a same-day decision is 0 and one taken on
        the next working day is 1. ``None`` when the order is impossible or any
        fiscal year the span touches is not confirmed — never an estimate."""
        s = start.date() if isinstance(start, datetime) else start
        e = end.date() if isinstance(end, datetime) else end
        if e < s or self.unconfirmed(self.fiscal_years(s, e)):
            return None
        count = 0
        day = s
        while day < e:
            year = self.years[fiscal_year_for(day, self.start_month)]
            if day.isoweekday() in year.working_weekdays and day not in year.holidays:
                count += 1
            day += timedelta(days=1)
        return count


def build_calendar(rows: list[BusinessCalendarYear], start_month: int) -> BusinessCalendar:
    years = {
        r.fiscal_year: YearCalendar(
            working_weekdays=frozenset(r.working_weekdays or DEFAULT_WORKING_WEEKDAYS),
            holidays=frozenset(date.fromisoformat(h["date"]) for h in r.holidays or []),
            confirmed=bool(r.confirmed),
        )
        for r in rows
    }
    return BusinessCalendar(start_month=start_month, years=years)


async def load_calendar(db: AsyncSession, start_month: int) -> BusinessCalendar:
    rows = (await db.execute(select(BusinessCalendarYear))).scalars().all()
    return build_calendar(list(rows), start_month)


def serialize(row: BusinessCalendarYear, start_month: int) -> dict:
    start, end = fiscal_year_bounds(row.fiscal_year, start_month)
    return {
        "fiscal_year": row.fiscal_year,
        "starts": start.isoformat(),
        "ends": (end - timedelta(days=1)).isoformat(),
        "working_weekdays": list(row.working_weekdays or []),
        "holidays": list(row.holidays or []),
        "confirmed": bool(row.confirmed),
        "confirmed_at": row.confirmed_at.isoformat() if row.confirmed_at else None,
    }
