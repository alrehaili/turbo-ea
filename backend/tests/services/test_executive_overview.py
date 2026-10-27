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
    group = dec.OPERATIONAL_PIPELINE
    assert dec.section(3, [{"id": "x"}], can_list=True, group=group) == {
        "status": "ok",
        "group": group,
        "count": 3,
        "items": [{"id": "x"}],
    }
    assert dec.section(3, [{"id": "x"}], can_list=False, group=group) == {
        "status": "restricted",
        "group": group,
        "count": 3,
        "items": None,
    }
    assert dec.section(0, [], can_list=True, group=group, enabled=False) == {
        "status": "disabled",
        "group": group,
    }


def test_current_and_finished_periods():
    assert periods.parse(None, 1, TODAY).is_current is True
    assert periods.parse("FY2026", 1, TODAY).is_current is True  # the year is still running
    assert periods.parse("FY2026-Q3", 1, TODAY).is_current is False
    assert periods.parse("FY2026-Q3", 1, TODAY).to_dict()["is_current"] is False
    # A period whose last day is today has not ended yet.
    assert periods.parse("FY2026-Q3", 1, date(2026, 9, 30)).is_current is True


# ── KPI contract ─────────────────────────────────────────────────────────

PERIOD = periods.parse("FY2026-Q4", 1, TODAY)  # the current quarter
PRIOR = periods.previous(PERIOD, 1, TODAY)
FINISHED = periods.parse("FY2026-Q2", 1, TODAY)


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
            "oldest_report_date": latest if reported else None,
        },
    }


def _implementation(status="not_available", value=None, planned=0, total=0, eligible=0):
    """A ``governance.decision_implementation`` result, as the overview takes it."""
    out = {
        "status": status,
        "eligible": eligible,
        "outcomes": {},
        "excluded": {"no_deadline": total - planned},
        "planning_coverage": {
            "approved_decisions": total,
            "planned": planned,
            "percentage": round(100 * planned / total, 1) if total else None,
        },
    }
    if status == "ok":
        out |= {"value": value, "unit": "percent"}
    else:
        out["reason"] = {"code": "no_eligible_decisions"}
    return out


def test_every_tile_shows_target_and_owner_as_not_linked():
    tiles = [
        kpis.strategy_execution(PERIOD, None),
        kpis.governance_effectiveness(PERIOD, _implementation()),
        kpis.services_and_automation(PERIOD),
        kpis.initiative_delivery(PERIOD, _delivery(3, 4, 5), PRIOR),
    ]
    for tile in tiles:
        assert tile["target"] == {"status": "not_linked", "decision": "D-26"}
        assert tile["owner"]["status"] == "not_linked"


def test_blocked_kpis_are_not_available_with_reason_never_zero():
    tile = kpis.services_and_automation(PERIOD)
    assert tile["status"] == "not_available"
    assert tile["value"] is None and tile["confidence"] is None
    assert "D-08" in tile["reason"]["decisions"]


def test_gov05_tile_is_the_verified_rate_with_planning_coverage():
    tile = kpis.governance_effectiveness(
        PERIOD, _implementation("ok", value=50.0, planned=3, total=4, eligible=2)
    )
    assert (tile["key"], tile["calculation_version"]) == ("GOV-05", "GOV-05@1")
    assert tile["status"] == "ok" and tile["value"] == 50.0
    assert tile["completeness"] == {"numerator": 3, "denominator": 4, "percentage": 75.0}
    # Decisions without a deadline are disclosed, never dropped.
    assert tile["details"]["excluded"] == {"no_deadline": 1}
    # Verification is a person's attestation: never "high" confidence.
    assert tile["confidence"] == "medium"
    assert tile["drilldown"] == {"path": kpis.GOVERNANCE_PAGE}


def test_gov05_tile_without_due_decisions_is_not_available_never_zero():
    tile = kpis.governance_effectiveness(PERIOD, _implementation(planned=1, total=2))
    assert tile["status"] == "not_available" and tile["value"] is None
    assert tile["reason"] == {"code": "no_eligible_decisions"}
    assert tile["completeness"]["denominator"] == 2


def test_delivery_tile_value_and_confidence_for_the_current_period():
    tile = kpis.initiative_delivery(PERIOD, _delivery(3, 4, 5), PRIOR)
    assert tile["status"] == "ok" and tile["value"] == 75.0
    assert tile["temporal"] == "period" and tile["period"] == "FY2026-Q4"
    assert tile["completeness"]["percentage"] == 80.0
    assert tile["confidence"] == "medium"  # self-reported, 80% coverage
    assert tile["freshness"] == "2026-09-01"
    assert tile["as_of"] == "2026-10-24"
    assert tile["details"]["oldest_report_date"] == "2026-09-01"
    assert tile["drilldown"] == {"api": "TR-03", "path": "/ppm"}


def test_previous_delivery_is_never_recounted_over_todays_population():
    # The previous period has ended and its in-flight population is not on record.
    tile = kpis.initiative_delivery(PERIOD, _delivery(3, 4, 5), PRIOR)
    assert tile["previous"] == {
        "status": "not_available",
        "reason": "historical_unavailable",
        "period": "FY2026-Q3",
    }


def test_finished_period_delivery_is_historical_unavailable_not_a_value():
    tile = kpis.initiative_delivery(FINISHED, None, periods.previous(FINISHED, 1, TODAY))
    assert tile["status"] == "not_available" and tile["value"] is None
    assert tile["reason"] == {"code": "historical_unavailable"}
    assert tile["previous"]["reason"] == "historical_unavailable"
    assert tile["completeness"] is None and tile["drilldown"] is None


def test_delivery_from_card_status_offers_no_ppm_link():
    current = _delivery(3, 4, 5) | {"source": "initiative_status"}
    assert kpis.initiative_delivery(PERIOD, current, PRIOR)["drilldown"] is None


def test_delivery_with_low_coverage_is_low_confidence():
    tile = kpis.initiative_delivery(PERIOD, _delivery(1, 1, 5), PRIOR)
    assert tile["confidence"] == "low"


def test_delivery_with_nobody_reporting_is_not_reported_not_zero():
    tile = kpis.initiative_delivery(PERIOD, _delivery(0, 0, 5), PRIOR)
    assert tile["status"] == "not_available"
    assert tile["reason"]["code"] == "not_reported"
    assert tile["value"] is None


def test_business_value_never_uses_the_forecast_as_value():
    forecast = {"status": "ok", "total": 1000.0, "provenance": "forecast"}
    tile = kpis.business_value(PERIOD, forecast)
    assert tile["status"] == "not_available" and tile["value"] is None
    # Undated estimates (D-31): a current-state forecast, never a period result.
    assert tile["details"]["forecast"] == {**forecast, "temporal": "current_state"}


def test_decisions_tile_counts_escalated_and_shows_open_and_mitigated_apart():
    picture = dec.RiskPicture(open=7, mitigated=2, escalated=[object(), object()])
    pipeline = {"adrs": 1, "arb": 0, "exceptions": 0}
    tile = kpis.decisions_and_escalations(PERIOD, picture, pipeline, TODAY)
    assert tile["value"] == 2
    assert tile["details"]["open_risks"] == 7 and tile["details"]["mitigated_risks"] == 2
    assert tile["details"]["operational_pipeline"] == pipeline
    assert tile["confidence"] == "high"
    disabled = kpis.decisions_and_escalations(PERIOD, None, pipeline, TODAY)
    assert disabled["status"] == "not_available"
    assert disabled["details"]["operational_pipeline"]["adrs"] == 1


def test_decisions_tile_is_current_state_whatever_period_is_selected():
    picture = dec.RiskPicture(open=1, mitigated=0, escalated=[object()])
    for selected in (PERIOD, FINISHED):
        for risks in (picture, None):
            tile = kpis.decisions_and_escalations(selected, risks, {}, TODAY)
            assert tile["temporal"] == "current_state"
            assert tile["period"] is None
            assert tile["as_of"] == TODAY.isoformat()


# ── Strategy achievement (TR-01, D-21) and the on-target rule ─────────────

from app.services.executive import linkage, strategy  # noqa: E402

RATIFIED = {"status": "ratified", "value": 80.0, "baseline": 40.0, "direction": "higherIsBetter"}


def _totals(linked, measured, on_target):
    return {
        "totals": {"linked": linked, "measured": measured, "on_target": on_target},
        "execution": {},
    }


def test_strategy_tile_counts_on_target_among_measured_with_coverage():
    tile = kpis.strategy_execution(PERIOD, _totals(linked=5, measured=4, on_target=3))
    assert tile["status"] == "ok" and tile["value"] == 3 and tile["unit"] == "count_of"
    assert tile["completeness"] == {"numerator": 4, "denominator": 5, "percentage": 80.0}
    assert tile["drilldown"]["path"] == kpis.STRATEGY_PAGE


def test_strategy_tile_is_never_zero_without_evidence():
    none_linked = kpis.strategy_execution(PERIOD, _totals(0, 0, 0))
    assert none_linked["status"] == "not_available" and none_linked["value"] is None
    assert none_linked["reason"] == {"code": "no_strategic_kpis"}
    unmeasured = kpis.strategy_execution(PERIOD, _totals(3, 0, 0))
    assert unmeasured["reason"] == {"code": "no_verified_measurements"}
    assert unmeasured["completeness"]["percentage"] == 0.0
    past = kpis.strategy_execution(FINISHED, None)
    assert past["reason"] == {"code": "historical_unavailable"}


def test_assess_needs_a_ratified_target_and_a_direction():
    assert linkage.assess(85, RATIFIED) == {"achieved": True, "attainment": 100.0}
    assert linkage.assess(60, RATIFIED) == {"achieved": False, "attainment": 50.0}
    assert linkage.assess(30, RATIFIED)["attainment"] == 0.0
    lower = {**RATIFIED, "direction": "lowerIsBetter", "value": 10.0, "baseline": 30.0}
    assert linkage.assess(9, lower) == {"achieved": True, "attainment": 100.0}
    for target in ({**RATIFIED, "status": "unratified"}, {**RATIFIED, "direction": None}):
        assert linkage.assess(85, target) == {"achieved": None, "attainment": None}
    assert linkage.assess(None, RATIFIED)["achieved"] is None


def test_kpi_state_follows_the_evidence_order():
    approved = SimpleNamespace(approval_status="APPROVED")
    draft = SimpleNamespace(approval_status="DRAFT")
    assert strategy.kpi_state(draft, RATIFIED, 90)[0] == strategy.NOT_APPROVED
    assert (
        strategy.kpi_state(approved, {**RATIFIED, "status": "unratified"}, 90)[0]
        == strategy.NO_TARGET
    )
    assert (
        strategy.kpi_state(approved, {**RATIFIED, "direction": "x"}, 90)[0] == strategy.NO_DIRECTION
    )
    assert strategy.kpi_state(approved, RATIFIED, None)[0] == strategy.NOT_MEASURED
    assert strategy.kpi_state(approved, RATIFIED, 90)[0] == strategy.ON_TARGET
    assert strategy.kpi_state(approved, RATIFIED, 50)[0] == strategy.OFF_TARGET


def test_linked_tile_shows_target_owner_and_judges_only_when_ratified():
    tile = kpis.initiative_delivery(PERIOD, _delivery(3, 4, 5), PRIOR)  # 75 %
    link = {"card_id": "k1", "name": "Delivery KPI", "target": RATIFIED, "owners": ["Sara"]}
    out = linkage.apply_link(dict(tile), link)
    assert out["target"]["status"] == "ratified" and out["target"]["achieved"] is False
    assert out["owner"] == {"status": "ok", "name": "Sara"}
    unratified = linkage.apply_link(
        dict(tile), {**link, "target": {**RATIFIED, "status": "unratified"}, "owners": []}
    )
    assert unratified["target"]["achieved"] is None
    assert unratified["owner"] == {"status": "unassigned"}
    assert linkage.apply_link(dict(tile), None)["target"]["status"] == "not_linked"


def test_previous_and_finished_period_come_only_from_verified_history():
    verified = SimpleNamespace(
        value=70.0,
        status="verified",
        observed_on=date(2026, 6, 30),
        verified_at=None,
        calculation_version="TR-03@3",
    )
    assert kpis.previous_from_history(PRIOR, verified)["value"] == 70.0
    assert kpis.previous_from_history(PRIOR, None)["reason"] == "historical_unavailable"
    past = kpis.recorded_delivery(FINISHED, verified, kpis.historical_previous(PRIOR))
    assert past["status"] == "ok" and past["value"] == 70.0 and past["freshness"] == "2026-06-30"
    submitted = SimpleNamespace(**{**verified.__dict__, "status": "submitted"})
    waiting = kpis.recorded_delivery(FINISHED, submitted, kpis.historical_previous(PRIOR))
    assert waiting["status"] == "not_available"
    assert waiting["reason"] == {"code": "awaiting_verification"}


def test_gov05_tile_carries_the_verified_previous_period():
    previous = {"status": "ok", "value": 60.0, "period": "FY2026-Q3", "verified": True}
    tile = kpis.governance_effectiveness(
        PERIOD, _implementation("ok", value=50.0, planned=1, total=1, eligible=1), previous
    )
    assert tile["previous"] == previous
    unavailable = kpis.governance_effectiveness(PERIOD, _implementation(), previous)
    assert unavailable["previous"] == previous


def test_rsk01_tile_is_a_current_state_count_with_the_verified_previous():
    from datetime import date

    figures = {
        "status": "ok",
        "temporal": "current_state",
        "total": 4,
        "open": 3,
        "escalated": 1,
        "mitigated": 1,
        "verified_reduction": {"status": "not_available"},
    }
    previous = {"status": "ok", "value": 5, "period": "FY2026-Q3", "verified": True}
    tile = kpis.architecture_risk_tile(PERIOD, figures, date(2026, 10, 27), previous)
    assert (tile["key"], tile["calculation_version"]) == ("RSK-01", "RSK-01@1")
    assert (tile["value"], tile["unit"], tile["temporal"]) == (3, "count", "current_state")
    assert tile["period"] is None and tile["previous"] == previous
    assert tile["details"]["verified_reduction"]["status"] == "not_available"
    none = kpis.architecture_risk_tile(
        PERIOD,
        {"status": "not_available", "reason": {"code": "no_linked_risks"}},
        date(2026, 10, 27),
    )
    assert none["status"] == "not_available" and none["value"] is None
    assert none["temporal"] == "current_state"


def test_gov01_tile_is_current_state_with_assessment_coverage():
    from datetime import date

    figures = {
        "status": "ok",
        "value": 75.0,
        "unit": "percent",
        "temporal": "current_state",
        "population": 10,
        "requiring_review": 4,
        "review_completed": 3,
        "awaiting_review": 1,
        "review_in_progress": 0,
        "exempt": 2,
        "undetermined": 4,
        "assessment_coverage": {"assessed": 6, "population": 10, "percentage": 60.0},
        "basis": "approved_subject_review",
    }
    tile = kpis.review_coverage_tile(PERIOD, figures, date(2026, 10, 27))
    assert (tile["key"], tile["value"], tile["temporal"]) == ("GOV-01", 75.0, "current_state")
    assert tile["completeness"] == {"numerator": 6, "denominator": 10, "percentage": 60.0}
    assert tile["details"]["undetermined"] == 4
    # Never "high": below 70 % assessment coverage the confidence is "low".
    assert tile["confidence"] == "low"
    assert tile["previous"]["status"] == "not_available"
    none = kpis.review_coverage_tile(
        PERIOD,
        {**figures, "status": "not_available", "reason": {"code": "no_required_reviews"}},
        date(2026, 10, 27),
    )
    assert none["status"] == "not_available" and none["value"] is None
