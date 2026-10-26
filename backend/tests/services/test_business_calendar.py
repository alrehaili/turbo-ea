"""Business calendar rules and working-day arithmetic (D-28, D-38). No database.

Sunday–Thursday by default; holidays per fiscal year inside that year; a
duration is computable only when every fiscal year it spans is confirmed; a
change to a confirmed year withdraws its confirmation (I-38).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.models.business_calendar import DEFAULT_WORKING_WEEKDAYS, BusinessCalendarYear
from app.services import business_calendar as bc


def _year(fy, *, confirmed=True, holidays=(), week=None):
    return BusinessCalendarYear(
        fiscal_year=fy,
        working_weekdays=list(week or DEFAULT_WORKING_WEEKDAYS),
        holidays=[{"date": d, "name": "H"} for d in holidays],
        confirmed=confirmed,
    )


def test_the_default_week_is_sunday_to_thursday():
    assert bc.validate_working_weekdays(None) == [7, 1, 2, 3, 4]


@pytest.mark.parametrize("days", [[], [0], [8], [1, 1], ["1"], [True]])
def test_an_invalid_working_week_is_refused(days):
    with pytest.raises(bc.CalendarError) as err:
        bc.validate_working_weekdays(days)
    assert err.value.code == "invalid_working_week"


def test_a_working_week_is_kept_sunday_first():
    assert bc.validate_working_weekdays([1, 7, 3]) == [7, 1, 3]


def test_holidays_are_sorted_named_and_inside_the_fiscal_year():
    out = bc.validate_holidays(
        2026,
        1,
        [
            {"date": "2026-09-23", "name": " National Day "},
            {"date": "2026-02-22", "name": "Founding"},
        ],
    )
    assert out == [
        {"date": "2026-02-22", "name": "Founding"},
        {"date": "2026-09-23", "name": "National Day"},
    ]


@pytest.mark.parametrize(
    ("holidays", "code"),
    [
        ([{"date": "2025-12-31", "name": "x"}], "holiday_outside_year"),
        ([{"date": "2026-13-01", "name": "x"}], "invalid_holiday"),
        ([{"date": "2026-02-22", "name": "  "}], "invalid_holiday"),
        (
            [{"date": "2026-02-22", "name": "a"}, {"date": "2026-02-22", "name": "b"}],
            "duplicate_holiday",
        ),
    ],
)
def test_bad_holidays_are_refused(holidays, code):
    with pytest.raises(bc.CalendarError) as err:
        bc.validate_holidays(2026, 1, holidays)
    assert err.value.code == code


def test_a_fiscal_year_outside_the_range_is_refused():
    with pytest.raises(bc.CalendarError):
        bc.validate_fiscal_year(1999)
    assert bc.validate_fiscal_year(2027) == 2027


def test_editing_a_confirmed_year_withdraws_the_confirmation():
    row = _year(2026, confirmed=True)
    row.confirmed_at = datetime.now(timezone.utc)
    changes = bc.apply_edit(row, [7, 1, 2, 3, 4], [{"date": "2026-02-22", "name": "Founding"}])
    assert row.confirmed is False and row.confirmed_at is None
    assert changes["confirmed"] == {"old": True, "new": False}
    assert changes["holiday_count"] == {"old": 0, "new": 1}


def test_an_unchanged_save_keeps_the_confirmation():
    row = _year(2026, confirmed=True)
    assert bc.apply_edit(row, [7, 1, 2, 3, 4], []) == {}
    assert row.confirmed is True


def _calendar(*rows, start_month=1):
    return bc.build_calendar(list(rows), start_month)


def test_working_days_skip_weekends_and_holidays():
    cal = _calendar(_year(2026, holidays=["2026-09-23"]))
    # Sun 2026-09-20 → Sun 2026-09-27: Sun, Mon, Tue, (Wed holiday), Thu = 4.
    assert cal.working_days(date(2026, 9, 20), date(2026, 9, 27)) == 4
    assert cal.working_days(date(2026, 9, 20), date(2026, 9, 20)) == 0
    # A Thursday to the next Sunday crosses only the weekend.
    assert cal.working_days(date(2026, 9, 24), date(2026, 9, 27)) == 1


def test_a_span_into_an_unconfirmed_or_missing_year_has_no_working_days():
    cal = _calendar(_year(2026), _year(2025, confirmed=False))
    assert cal.working_days(date(2025, 12, 28), date(2026, 1, 4)) is None
    assert cal.working_days(date(2026, 12, 28), date(2027, 1, 4)) is None  # 2027 missing
    assert cal.working_days(date(2026, 3, 1), date(2026, 2, 1)) is None  # impossible order


def test_each_fiscal_year_uses_its_own_working_week():
    cal = _calendar(_year(2026), _year(2027, week=[1, 2, 3, 4, 5]))
    # Thu 2026-12-31 counts (Sun–Thu); Fri 2027-01-01 counts in 2027's Mon–Fri week.
    assert cal.working_days(date(2026, 12, 31), date(2027, 1, 2)) == 2


def test_fiscal_years_follow_the_start_month():
    cal = _calendar(_year(2027), start_month=10)
    # FY2027 runs 2026-10-01 .. 2027-09-30 with an October start.
    assert cal.fiscal_years(date(2026, 10, 1), date(2027, 9, 30)) == [2027]
    assert cal.unconfirmed([2026, 2027]) == [2026]


def test_serialize_names_the_years_bounds():
    out = bc.serialize(_year(2027), 10)
    assert (out["starts"], out["ends"]) == ("2026-10-01", "2027-09-30")
    assert out["working_weekdays"] == [7, 1, 2, 3, 4]
