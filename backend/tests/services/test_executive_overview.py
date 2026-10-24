"""Executive Phase 2 builders (pure): periods, the D-04 escalation rule and the
CEO KPI contract. No database."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.executive import decisions as dec
from app.services.executive import kpis, periods
from app.services.fiscal_year import fiscal_quarter_bounds

TODAY = date(2026, 10, 24)


# ── Periods ──────────────────────────────────────────────────────────────


def test_quarter_bounds_follow_the_fiscal_start_month():
    assert fiscal_quarter_bounds(2027, 1, 10) == (date(2026, 10, 1), date(2027, 1, 1))
    assert fiscal_quarter_bounds(2027, 4, 10) == (date(2027, 7, 1), date(2027, 10, 1))
    assert fiscal_quarter_bounds(2026, 2, 1) == (date(2026, 4, 1), date(2026, 7, 1))
    with pytest.raises(ValueError):
        fiscal_quarter_bounds(2026, 5, 1)


def test_default_period_is_the_current_quarter_measured_as_of_today():
    p = periods.parse(None, 1, TODAY)
    assert p.key == "FY2026-Q4"
    assert p.as_of == TODAY  # an unfinished period never claims future data


def test_finished_period_is_measured_at_its_last_day():
    p = periods.parse("FY2026-Q1", 1, TODAY)
    assert p.as_of == date(2026, 3, 31)
    assert p.to_dict()["end"] == "2026-03-31"


@pytest.mark.parametrize("bad", ["2026", "FY26", "FY2026-Q5", "FY2026Q1", "FY2030"])
def test_malformed_or_future_period_is_refused(bad):
    with pytest.raises(ValueError):
        periods.parse(bad, 1, TODAY)


def test_previous_period():
    assert periods.previous(periods.parse("FY2026-Q1", 1, TODAY), 1, TODAY).key == "FY2025-Q4"
    assert periods.previous(periods.parse("FY2026-Q3", 1, TODAY), 1, TODAY).key == "FY2026-Q2"
    assert periods.previous(periods.parse("FY2026", 1, TODAY), 1, TODAY).key == "FY2025"


def test_available_periods_never_list_a_future_quarter():
    keys = periods.available(TODAY, 1)
    assert keys[:5] == ["FY2026", "FY2026-Q4", "FY2026-Q3", "FY2026-Q2", "FY2026-Q1"]
    assert "FY2023" in keys and "FY2022" not in keys
    # With an October start, FY2027 has just begun: only its first quarter.
    oct_keys = periods.available(TODAY, 10)
    assert oct_keys[:3] == ["FY2027", "FY2027-Q1", "FY2026"]


# ── D-04 escalation ──────────────────────────────────────────────────────


def _risk(status="identified", level="medium", residual=None, due=None, category="operational"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        reference="R-1",
        title="t",
        status=status,
        initial_level=level,
        residual_level=residual,
        target_resolution_date=due,
        category=category,
        owner_id=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_critical_open_risk_is_escalated():
    assert dec.is_escalated(_risk(level="critical"), TODAY)


def test_residual_level_wins_over_initial():
    assert not dec.is_escalated(_risk(level="critical", residual="medium"), TODAY)
    assert dec.is_escalated(_risk(level="low", residual="critical"), TODAY)


def test_high_risk_escalates_only_when_overdue_and_not_mitigated():
    past, future = TODAY - timedelta(days=1), TODAY + timedelta(days=1)
    assert dec.is_escalated(_risk(level="high", due=past), TODAY)
    assert not dec.is_escalated(_risk(level="high", due=future), TODAY)
    assert not dec.is_escalated(_risk(level="high"), TODAY)
    assert not dec.is_escalated(_risk(status="mitigated", level="high", due=past), TODAY)


def test_closed_or_accepted_risks_never_escalate():
    for status in ("closed", "accepted"):
        assert not dec.is_escalated(_risk(status=status, level="critical"), TODAY)


def test_strategic_category_is_not_an_escalation_signal():
    assert not dec.is_escalated(_risk(level="medium", category="strategic"), TODAY)


def test_open_mitigated_and_escalated_are_counted_separately():
    risks = [
        _risk(level="critical"),
        _risk(status="mitigated", level="critical"),
        _risk(status="mitigated"),
        _risk(status="closed", level="critical"),
        _risk(),
    ]
    picture = dec.classify_risks(risks, TODAY)
    assert picture.open == 4
    assert picture.mitigated == 2
    # A mitigated risk whose level is still critical stays escalated.
    assert len(picture.escalated) == 2


def test_decision_section_lists_records_only_with_permission():
    assert dec.section(3, [{"id": "x"}], can_list=True) == {
        "status": "ok",
        "count": 3,
        "items": [{"id": "x"}],
    }
    assert dec.section(3, [{"id": "x"}], can_list=False) == {
        "status": "restricted",
        "count": 3,
        "items": None,
    }
    assert dec.section(0, [], can_list=True, enabled=False) == {"status": "disabled"}


# ── KPI contract ─────────────────────────────────────────────────────────

PERIOD = periods.parse("FY2026-Q3", 1, TODAY)
PRIOR = periods.previous(PERIOD, 1, TODAY)


def _delivery(on_track, reported, in_flight, latest="2026-09-01"):
    return {
        "source": "ppm_reports",
        "staleness_days": None,
        "states": {"onTrack": on_track, "atRisk": 0, "offTrack": 0, "notReported": 0},
        "excluded": {"completed": 0, "onHold": 0},
        "on_track_pct": round(on_track / reported * 100, 1) if reported else None,
        "coverage": {
            "reported": reported,
            "in_flight": in_flight,
            "percentage": round(reported / in_flight * 100, 1) if in_flight else None,
            "stale_reports": 0,
            "latest_report_date": latest if reported else None,
        },
    }


def test_every_tile_shows_target_and_owner_as_not_linked():
    tiles = [
        kpis.strategy_execution(PERIOD),
        kpis.governance_effectiveness(PERIOD),
        kpis.services_and_automation(PERIOD),
        kpis.initiative_delivery(PERIOD, _delivery(3, 4, 5), None, PRIOR),
    ]
    for tile in tiles:
        assert tile["target"] == {"status": "not_linked", "decision": "D-26"}
        assert tile["owner"]["status"] == "not_linked"


def test_blocked_kpis_are_not_available_with_reason_never_zero():
    for tile, decision in (
        (kpis.strategy_execution(PERIOD), "D-21"),
        (kpis.governance_effectiveness(PERIOD), "D-13"),
        (kpis.services_and_automation(PERIOD), "D-08"),
    ):
        assert tile["status"] == "not_available"
        assert tile["value"] is None and tile["confidence"] is None
        assert decision in tile["reason"]["decisions"]


def test_delivery_tile_value_previous_and_confidence():
    tile = kpis.initiative_delivery(PERIOD, _delivery(3, 4, 5), _delivery(1, 2, 5), PRIOR)
    assert tile["status"] == "ok" and tile["value"] == 75.0
    assert tile["previous"] == {
        "status": "ok",
        "value": 50.0,
        "period": "FY2026-Q2",
        "coverage_percentage": 40.0,
    }
    assert tile["completeness"]["percentage"] == 80.0
    assert tile["confidence"] == "medium"  # self-reported, 80% coverage
    assert tile["freshness"] == "2026-09-01"
    assert tile["as_of"] == "2026-09-30"


def test_delivery_with_low_coverage_is_low_confidence():
    tile = kpis.initiative_delivery(PERIOD, _delivery(1, 1, 5), None, PRIOR)
    assert tile["confidence"] == "low"
    assert tile["previous"]["status"] == "not_available"  # no history (D-19)


def test_delivery_with_nobody_reporting_is_not_reported_not_zero():
    tile = kpis.initiative_delivery(PERIOD, _delivery(0, 0, 5), None, PRIOR)
    assert tile["status"] == "not_available"
    assert tile["reason"]["code"] == "not_reported"
    assert tile["value"] is None


def test_business_value_never_uses_the_forecast_as_value():
    forecast = {"status": "ok", "total": 1000.0, "provenance": "forecast"}
    tile = kpis.business_value(PERIOD, forecast)
    assert tile["status"] == "not_available" and tile["value"] is None
    assert tile["details"]["forecast"] is forecast


def test_decisions_tile_counts_escalated_and_shows_open_and_mitigated_apart():
    picture = dec.RiskPicture(open=7, mitigated=2, escalated=[object(), object()])
    tile = kpis.decisions_and_escalations(PERIOD, picture, {"adrs": 1, "arb": 0, "exceptions": 0})
    assert tile["value"] == 2
    assert tile["details"]["open_risks"] == 7 and tile["details"]["mitigated_risks"] == 2
    assert tile["confidence"] == "high"
    disabled = kpis.decisions_and_escalations(PERIOD, None, {"adrs": 1, "arb": 0, "exceptions": 0})
    assert disabled["status"] == "not_available"
    assert disabled["details"]["pending"]["adrs"] == 1
