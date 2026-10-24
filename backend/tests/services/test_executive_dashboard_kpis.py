"""Executive dashboard Phase 1 KPI rules (pure builders, no database).

Pins the approved decisions: four-state delivery health with reporting
coverage kept separate and no invented staleness default (D-02); one fiscal
year per budget figure (D-06); planned savings counted once per application,
with conflicting estimates excluded rather than resolved (D-24); every money
block naming its currency (D-05).
"""

from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace

from app.services import executive_dashboard as exe
from app.services.fiscal_year import fiscal_year_bounds, fiscal_year_for

TODAY = date(2026, 10, 24)


def _card(status: str | None = None):
    attrs = {"initiativeStatus": status} if status else {}
    return SimpleNamespace(id=uuid.uuid4(), attributes=attrs)


def _report(days_old: int, schedule="onTrack", cost="onTrack", scope="onTrack"):
    return SimpleNamespace(
        report_date=date.fromordinal(TODAY.toordinal() - days_old),
        schedule_health=schedule,
        cost_health=cost,
        scope_health=scope,
    )


# ── Delivery state ───────────────────────────────────────────────────────


def test_missing_report_is_not_reported_never_healthy_or_at_risk():
    assert exe.report_state(None, today=TODAY, stale=None) == "notReported"


def test_worst_dimension_decides():
    assert exe.report_state(_report(1, cost="atRisk"), today=TODAY, stale=None) == "atRisk"
    report = _report(1, schedule="atRisk", scope="offTrack")
    assert exe.report_state(report, today=TODAY, stale=None) == "offTrack"
    assert exe.report_state(_report(1), today=TODAY, stale=None) == "onTrack"


def test_unrecognised_health_value_is_unknown():
    assert exe.report_state(_report(1, cost="green"), today=TODAY, stale=None) == "notReported"


def test_no_staleness_configured_means_no_report_is_stale():
    assert exe.report_state(_report(3000), today=TODAY, stale=None) == "onTrack"


def test_report_older_than_threshold_is_not_reported():
    assert exe.report_state(_report(31), today=TODAY, stale=30) == "notReported"
    assert exe.report_state(_report(30), today=TODAY, stale=30) == "onTrack"


def test_staleness_setting_has_no_default_and_rejects_bad_values():
    assert exe.staleness_days({}) is None
    assert exe.staleness_days({exe.STALENESS_SETTING: 45}) == 45
    for bad in (0, -1, 3651, "30", 2.5, True, None):
        assert exe.staleness_days({exe.STALENESS_SETTING: bad}) is None


def test_health_summary_keeps_coverage_separate_and_reconciles():
    on, risk, none, stale = _card(), _card(), _card(), _card()
    done, held = _card("completed"), _card("onHold")
    latest = {
        on.id: _report(5),
        risk.id: _report(5, schedule="atRisk"),
        stale.id: _report(90, schedule="offTrack"),
        done.id: _report(5, schedule="offTrack"),
    }
    out = exe.summarize_delivery_health(
        [on, risk, none, stale, done, held], latest, today=TODAY, stale=30
    )
    assert out["states"] == {"onTrack": 1, "atRisk": 1, "offTrack": 0, "notReported": 2}
    assert out["excluded"] == {"completed": 1, "onHold": 1}
    # The four states plus the excluded initiatives equal the population.
    assert sum(out["states"].values()) + sum(out["excluded"].values()) == 6
    assert out["coverage"]["reported"] == 2 and out["coverage"]["in_flight"] == 4
    assert out["coverage"]["percentage"] == 50.0
    assert out["coverage"]["stale_reports"] == 1
    # Headline is over the reporting initiatives only.
    assert out["on_track_pct"] == 50.0
    assert out["dimensions"]["schedule"]["noReport"] == 2
    assert out["source"] == exe.SOURCE_PPM_REPORTS


def test_health_summary_with_nobody_reporting_has_no_headline():
    out = exe.summarize_delivery_health([_card(), _card()], {}, today=TODAY, stale=None)
    assert out["on_track_pct"] is None
    assert out["coverage"]["percentage"] == 0.0
    assert out["states"]["notReported"] == 2


def test_without_ppm_the_initiative_status_is_the_source():
    cards = [_card("onTrack"), _card("offTrack"), _card(), _card("completed")]
    out = exe.summarize_delivery_health(cards, None, today=TODAY, stale=None)
    assert out["source"] == exe.SOURCE_INITIATIVE_STATUS
    assert out["states"] == {"onTrack": 1, "atRisk": 0, "offTrack": 1, "notReported": 1}
    assert out["dimensions"] is None


# ── Fiscal period ────────────────────────────────────────────────────────


def test_fiscal_year_bounds_invert_fiscal_year_for():
    for start in range(1, 13):
        lo, hi = fiscal_year_bounds(2026, start)
        assert fiscal_year_for(lo, start) == 2026
        assert fiscal_year_for(date.fromordinal(hi.toordinal() - 1), start) == 2026
        assert fiscal_year_for(hi, start) == 2027
    assert fiscal_year_bounds(2026, 10) == (date(2025, 10, 1), date(2026, 10, 1))
    assert fiscal_year_bounds(2026, 1) == (date(2026, 1, 1), date(2027, 1, 1))


def _budget(**kw):
    defaults = dict(fy=2026, start_month=1, current_fy=2026, currency="SAR", can_view_costs=True)
    return exe.summarize_budget(**{**defaults, **kw})


def test_budget_names_period_currency_and_execution():
    money = exe.FiscalMoney(budget=1000, actual=250, undated_cost_lines=3, years=(2024, 2026))
    out = _budget(money=money, enabled=True)
    assert out["status"] == "ok" and out["currency"] == "SAR"
    assert out["execution_pct"] == 25.0
    assert out["available_years"] == [2024, 2026]
    assert out["undated_cost_lines"] == 3


def test_budget_without_a_budget_has_no_execution_rate():
    out = _budget(money=exe.FiscalMoney(0, 50, 0, ()), enabled=True)
    assert out["execution_pct"] is None


def test_budget_restricted_keeps_the_period_but_no_amounts():
    out = _budget(money=None, enabled=True, can_view_costs=False)
    assert out["status"] == "restricted"
    assert out["fiscal_year"] == 2026
    assert "budget" not in out and "actual" not in out and "currency" not in out


def test_budget_disabled_without_ppm():
    assert _budget(money=None, enabled=False)["status"] == "disabled"


# ── Planned savings ──────────────────────────────────────────────────────


def _row(card_id, amount, assessment="A", decision="eliminate", name="App"):
    return exe.DecisionRow(
        card_id=card_id,
        card_name=name,
        assessment_id=uuid.uuid4(),
        assessment_name=assessment,
        time_decision=decision,
        planned_savings=amount,
    )


def test_agreeing_estimates_count_once():
    app = uuid.uuid4()
    out = exe.summarize_planned_savings([_row(app, 100.0, "A"), _row(app, 100.0, "B")])
    assert out["total"] == 100.0
    assert out["applications_counted"] == 1
    assert out["duplicates_merged"] == 1
    assert out["conflicts"] == []


def test_conflicting_estimates_are_excluded_and_listed_with_every_candidate():
    app, other = uuid.uuid4(), uuid.uuid4()
    rows = [_row(app, 100.0, "A", name="CRM"), _row(app, 80.0, "B", name="CRM"), _row(other, 30.0)]
    out = exe.summarize_planned_savings(rows)
    # Neither 100 (latest?) nor 80 (lowest) is chosen: the conflict adds nothing.
    assert out["total"] == 30.0
    assert out["applications_counted"] == 1
    assert len(out["conflicts"]) == 1
    conflict = out["conflicts"][0]
    assert conflict["card_name"] == "CRM"
    assert [c["amount"] for c in conflict["candidates"]] == [80.0, 100.0]
    assert out["excluded_range"] == [80.0, 100.0]


def test_decision_without_an_estimate_is_not_a_candidate():
    app = uuid.uuid4()
    out = exe.summarize_planned_savings([_row(app, None), _row(app, 40.0)])
    assert out["total"] == 40.0 and out["conflicts"] == []


def test_savings_period_is_marked_blocked_on_d31():
    assert exe.summarize_planned_savings([])["period"] == {"status": "blocked", "decision": "D-31"}


def test_rationalization_keeps_forecast_and_realised_apart():
    app = uuid.uuid4()
    rows = [_row(app, 10.0, "A"), _row(app, 10.0, "B", decision="migrate")]
    out = exe.summarize_rationalization(
        rows, can_view_costs=True, can_view_rationalization=True, currency="SAR"
    )
    assert out["decisions"] == 2 and out["applications"] == 1
    assert out["planned_savings"]["provenance"] == "forecast"
    assert out["planned_savings"]["currency"] == "SAR"
    assert out["realized_savings"] == {"status": exe.NOT_AVAILABLE}

    restricted = exe.summarize_rationalization(
        rows, can_view_costs=False, can_view_rationalization=True, currency="SAR"
    )
    assert restricted["planned_savings"] == {"status": "restricted", "provenance": "forecast"}


def test_conflict_detail_needs_rationalization_view():
    app, other = uuid.uuid4(), uuid.uuid4()
    rows = [_row(app, 100.0, "A", name="CRM"), _row(app, 80.0, "B", name="CRM"), _row(other, 30.0)]

    full = exe.summarize_rationalization(
        rows, can_view_costs=True, can_view_rationalization=True, currency="SAR"
    )["planned_savings"]
    assert full["conflict_detail"] == "ok"
    assert full["conflict_count"] == 1
    assert [c["card_name"] for c in full["conflicts"]] == ["CRM"]
    assert full["excluded_range"] == [80.0, 100.0]

    # costs.view without rationalization.view: the total and the count stay, but
    # nothing names the application or the assessments, and no estimate leaks
    # through the range.
    count_only = exe.summarize_rationalization(
        rows, can_view_costs=True, can_view_rationalization=False, currency="SAR"
    )["planned_savings"]
    assert count_only["conflict_detail"] == "restricted"
    assert count_only["conflict_count"] == 1
    assert count_only["conflicts"] is None
    assert count_only["excluded_range"] is None
    assert count_only["total"] == full["total"] == 30.0
    assert "CRM" not in str(count_only) and "100.0" not in str(count_only)
