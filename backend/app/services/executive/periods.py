"""Reporting periods for the executive overview: a fiscal year or one of its quarters.

A period key is ``FY2027`` or ``FY2027-Q2``; fiscal years follow the workspace's
``fiscalYearStart`` and are named after the calendar year they end in
(``app.services.fiscal_year``). A figure is measured *as of* the period's last
day, or today when the period has not ended yet, so the current period never
claims data from the future.

A period is *current* when it has not ended (``as_of`` is today). Only a
current period can be measured from data that carries no history — a card's
present status, today's risk register. A finished period is measured only from
dated records, and a figure with no dated evidence is unavailable for it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from app.services.fiscal_year import fiscal_quarter_bounds, fiscal_year_bounds, fiscal_year_for

_KEY = re.compile(r"^FY(\d{4})(?:-Q([1-4]))?$")
#: Fiscal years offered in the selector: the current one and three before it.
PRIOR_YEARS = 3


@dataclass(frozen=True)
class Period:
    fy: int
    quarter: int | None
    start: date
    end: date  # exclusive
    as_of: date
    #: The period has not ended: today falls inside it.
    is_current: bool

    @property
    def key(self) -> str:
        return f"FY{self.fy}" + (f"-Q{self.quarter}" if self.quarter else "")

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "fiscal_year": self.fy,
            "quarter": self.quarter,
            "start": self.start.isoformat(),
            "end": (self.end - timedelta(days=1)).isoformat(),
            "as_of": self.as_of.isoformat(),
            "is_current": self.is_current,
        }


def build(fy: int, quarter: int | None, start_month: int, today: date) -> Period:
    if quarter is None:
        start, end = fiscal_year_bounds(fy, start_month)
    else:
        start, end = fiscal_quarter_bounds(fy, quarter, start_month)
    last_day = end - timedelta(days=1)
    return Period(fy, quarter, start, end, min(last_day, today), last_day >= today)


def current_quarter(today: date, start_month: int) -> tuple[int, int]:
    fy = fiscal_year_for(today, start_month)
    for q in range(1, 5):
        start, end = fiscal_quarter_bounds(fy, q, start_month)
        if start <= today < end:
            return fy, q
    raise AssertionError("a date always falls in one quarter of its fiscal year")


def parse(key: str | None, start_month: int, today: date) -> Period:
    """The period named by ``key``; the current quarter when ``key`` is empty.

    Raises ``ValueError`` for a malformed key or a period that starts after today.
    """
    if not key:
        fy, q = current_quarter(today, start_month)
        return build(fy, q, start_month, today)
    m = _KEY.match(key)
    if not m:
        raise ValueError("period must look like FY2027 or FY2027-Q2")
    period = build(int(m.group(1)), int(m.group(2)) if m.group(2) else None, start_month, today)
    if period.start > today:
        raise ValueError("period has not started yet")
    return period


def previous(period: Period, start_month: int, today: date) -> Period:
    """The period immediately before: the prior quarter, or the prior fiscal year."""
    if period.quarter is None:
        return build(period.fy - 1, None, start_month, today)
    if period.quarter == 1:
        return build(period.fy - 1, 4, start_month, today)
    return build(period.fy, period.quarter - 1, start_month, today)


def available(today: date, start_month: int) -> list[str]:
    """Selectable keys, newest first: each fiscal year then its started quarters."""
    current_fy = fiscal_year_for(today, start_month)
    keys: list[str] = []
    for fy in range(current_fy, current_fy - PRIOR_YEARS - 1, -1):
        keys.append(f"FY{fy}")
        for q in range(4, 0, -1):
            start, _ = fiscal_quarter_bounds(fy, q, start_month)
            if start <= today:
                keys.append(f"FY{fy}-Q{q}")
    return keys
