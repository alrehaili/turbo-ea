"""``/reports/executive/{overview,decisions,kpi/*/drilldown}`` — Phase 2.

The executive permission grants aggregates only (D-03): counts are visible,
records need their module's own view permission, and every population is the
caller's read scope with hidden types left out before counting.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.app_settings import AppSettings
from app.models.arb_review import ArbReview
from app.models.card_type import CardType
from tests.conftest import (
    auth_headers,
    create_card,
    create_card_type,
    create_risk,
    create_role,
    create_status_report,
    create_user,
)

BASE = "/api/v1/reports/executive"


async def _settings(db, **general):
    row = (
        await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    ).scalar_one_or_none()
    if row is None:
        db.add(AppSettings(id="default", general_settings=general))
    else:
        row.general_settings = {**(row.general_settings or {}), **general}
    await db.flush()


@pytest.fixture
async def env(db):
    await create_role(db, key="admin", permissions={"*": True})
    await create_role(
        db,
        key="exec",
        label="Exec",
        permissions={"reports.executive_dashboard": True, "inventory.view": True},
        is_system=False,
    )
    await create_role(
        db, key="plain", label="Plain", permissions={"inventory.view": True}, is_system=False
    )
    admin = await create_user(db, email="admin@test.com", role="admin")
    executive = await create_user(db, email="exec@test.com", role="exec")
    plain = await create_user(db, email="plain@test.com", role="plain")
    await create_card_type(db, key="Initiative", label="Initiative")
    await create_card_type(db, key="Application", label="Application")
    await _settings(db, ppmEnabled=True, grcEnabled=True, fiscalYearStart=1)

    today = date.today()
    on = await create_card(db, card_type="Initiative", name="On")
    await create_card(db, card_type="Initiative", name="Silent")
    await create_status_report(db, initiative_id=on.id, report_date=today)
    return {"admin": admin, "exec": executive, "plain": plain, "today": today}


async def _get(client, user, path):
    return await client.get(f"{BASE}{path}", headers=auth_headers(user))


async def test_needs_the_executive_permission(client, env):
    for path in ("/overview", "/decisions", "/kpi/TR-03/drilldown"):
        assert (await _get(client, env["plain"], path)).status_code == 403


async def test_overview_has_six_tiles_and_never_fabricates(client, env):
    body = (await _get(client, env["admin"], "/overview")).json()
    tiles = {t["slot"]: t for t in body["kpis"]}
    assert list(tiles) == ["strategy", "governance", "delivery", "services", "value", "decisions"]
    for slot in ("strategy", "governance", "services", "value"):
        assert tiles[slot]["status"] == "not_available" and tiles[slot]["value"] is None
    assert tiles["delivery"]["value"] == 100.0
    assert tiles["delivery"]["completeness"] == {
        "numerator": 1,
        "denominator": 2,
        "percentage": 50.0,
    }
    assert all(t["target"]["status"] == "not_linked" for t in body["kpis"])
    assert body["period"]["key"] in body["available_periods"]


async def test_previous_period_is_never_recounted_over_todays_initiatives(client, db, env):
    # A report dated inside the previous quarter exists, but who was in flight
    # then is not on record: no comparison is fabricated from today's cards.
    body = (await _get(client, env["admin"], "/overview")).json()
    delivery = next(t for t in body["kpis"] if t["slot"] == "delivery")
    assert delivery["previous"] == {
        "status": "not_available",
        "reason": "historical_unavailable",
        "period": body["previous_period"]["key"],
    }


async def _finished_period(client, admin) -> str:
    keys = (await _get(client, admin, "/overview")).json()["available_periods"]
    return next(k for k in keys if "-Q" in k and k != keys[1])


async def test_finished_period_shows_historical_unavailable_and_current_state_apart(client, env):
    past = await _finished_period(client, env["admin"])
    body = (await _get(client, env["admin"], f"/overview?period={past}")).json()
    assert body["period"]["is_current"] is False
    tiles = {t["slot"]: t for t in body["kpis"]}
    assert tiles["delivery"]["status"] == "not_available"
    assert tiles["delivery"]["reason"] == {"code": "historical_unavailable"}
    assert tiles["delivery"]["value"] is None and tiles["delivery"]["completeness"] is None
    # Escalations are today's register, labelled so — never a result for the past period.
    assert tiles["decisions"]["temporal"] == "current_state"
    assert tiles["decisions"]["period"] is None
    assert tiles["decisions"]["as_of"] == env["today"].isoformat()
    assert tiles["value"]["details"]["forecast"]["temporal"] == "current_state"

    current = (await _get(client, env["admin"], "/overview")).json()
    assert current["period"]["is_current"] is True
    assert next(t for t in current["kpis"] if t["slot"] == "delivery")["status"] == "ok"


async def test_finished_period_drilldown_lists_no_rows(client, env):
    past = await _finished_period(client, env["admin"])
    body = (await _get(client, env["admin"], f"/kpi/TR-03/drilldown?period={past}")).json()
    assert body["status"] == "not_available" and body["rows"] == []
    assert body["reason"] == {"code": "historical_unavailable"}


async def test_period_is_validated(client, env):
    assert (await _get(client, env["admin"], "/overview?period=FY20")).status_code == 422
    assert (await _get(client, env["admin"], "/overview?period=FY2999")).status_code == 422


async def test_hidden_initiative_type_leaves_every_delivery_figure(client, db, env):
    initiative = (
        await db.execute(select(CardType).where(CardType.key == "Initiative"))
    ).scalar_one()
    initiative.is_hidden = True
    await db.flush()
    body = (await _get(client, env["admin"], "/overview")).json()
    delivery = next(t for t in body["kpis"] if t["slot"] == "delivery")
    assert delivery["status"] == "not_available"
    assert delivery["completeness"]["denominator"] == 0


async def test_decisions_counts_for_everyone_records_only_with_module_permission(client, db, env):
    app = await create_card(db, card_type="Application", name="CRM")
    # Level = probability x impact (risk_service.derive_level).
    await create_risk(
        db, title="Data centre outage", initial_probability="very_high", initial_impact="high"
    )
    await create_risk(
        db,
        title="Late migration",
        initial_probability="high",
        initial_impact="high",
        target_resolution_date=env["today"] - timedelta(days=3),
    )
    await create_risk(db, title="Fine")
    db.add(ArbReview(title="Review CRM", subject_card_id=app.id, status="scheduled"))
    await db.flush()

    full = (await _get(client, env["admin"], "/decisions")).json()
    assert full["risks"]["status"] == "ok" and full["risks"]["count"] == 2
    assert full["risks"]["open"] == 3
    assert {i["title"] for i in full["risks"]["items"]} == {"Data centre outage", "Late migration"}
    assert full["arb"]["count"] == 1 and full["arb"]["items"][0]["title"] == "Review CRM"

    limited = (await _get(client, env["exec"], "/decisions")).json()
    assert limited["risks"] == {
        "status": "restricted",
        "group": "executive_escalation",
        "count": 2,
        "items": None,
        "open": 3,
        "mitigated": 0,
    }
    assert limited["arb"]["status"] == "restricted" and limited["arb"]["count"] == 1
    assert "Data centre outage" not in str(limited) and "Review CRM" not in str(limited)

    # A restricted reader is told how many, not shown an empty "nothing to do".
    overview = (await _get(client, env["exec"], "/overview")).json()
    assert overview["escalations_panel"] == {
        "status": "restricted",
        "count": 2,
        "items": [],
        "more": 0,
    }
    escalation = next(t for t in overview["kpis"] if t["slot"] == "decisions")
    assert escalation["value"] == 2 and escalation["details"]["open_risks"] == 3
    assert escalation["details"]["operational_pipeline"]["arb"] == 1


async def test_attention_panel_holds_escalations_only(client, db, env):
    app = await create_card(db, card_type="Application", name="CRM")
    await create_risk(
        db, title="Data centre outage", initial_probability="very_high", initial_impact="high"
    )
    db.add(ArbReview(title="Review CRM", subject_card_id=app.id, status="scheduled"))
    await db.flush()

    full = (await _get(client, env["admin"], "/decisions")).json()
    assert full["risks"]["group"] == "executive_escalation"
    assert {full[k]["group"] for k in ("adrs", "arb", "exceptions")} == {"operational_pipeline"}

    panel = (await _get(client, env["admin"], "/overview")).json()["escalations_panel"]
    assert panel["status"] == "ok" and panel["count"] == 1
    assert [i["kind"] for i in panel["items"]] == ["risk"]
    assert "Review CRM" not in str(panel)


async def test_drilldown_rows_need_the_module_permission(client, env):
    assert (await _get(client, env["exec"], "/kpi/TR-03/drilldown")).status_code == 403
    assert (await _get(client, env["exec"], "/kpi/DEC-01/drilldown")).status_code == 403
    assert (await _get(client, env["admin"], "/kpi/NOPE/drilldown")).status_code == 404

    rows = (await _get(client, env["admin"], "/kpi/TR-03/drilldown")).json()["rows"]
    # The rows add up to the tile: one in-flight row per initiative, same states.
    assert [(r["name"], r["state"]) for r in rows] == [
        ("Silent", "notReported"),
        ("On", "onTrack"),
    ]
    assert rows[1]["path"].startswith("/ppm/")


# ── /strategy (D-21) ─────────────────────────────────────────────────────


async def _strategic_kpis(db, today):
    """A strategic objective with a measured, a ratified-but-unmeasured and an
    unratified KPI, plus a non-strategic objective whose KPI must not count."""
    from app.models.kpi_measurement import KpiMeasurement, KpiTargetRatification
    from app.services.executive import periods
    from tests.conftest import create_relation, create_relation_type

    await create_card_type(db, key="Objective", label="Objective")
    await create_card_type(db, key="KPI", label="KPI")
    await create_relation_type(
        db, key="relObjectiveToKPI", source_type_key="Objective", target_type_key="KPI"
    )
    target = {
        "targetValue": 80,
        "baselineValue": 50,
        "unit": "%",
        "direction": "higherIsBetter",
    }
    strategic = await create_card(
        db, card_type="Objective", name="Grow", attributes={"objectiveType": "strategic"}
    )
    other = await create_card(
        db, card_type="Objective", name="Tidy", attributes={"objectiveType": "operational"}
    )
    measured = await create_card(
        db, card_type="KPI", name="Measured", approval_status="APPROVED", attributes=target
    )
    unratified = await create_card(
        db, card_type="KPI", name="Unratified", approval_status="APPROVED", attributes=target
    )
    outside = await create_card(
        db, card_type="KPI", name="Outside", approval_status="APPROVED", attributes=target
    )
    for o, k in ((strategic, measured), (strategic, unratified), (other, outside)):
        await create_relation(db, type_key="relObjectiveToKPI", source_id=o.id, target_id=k.id)

    db.add(
        KpiTargetRatification(
            kpi_card_id=measured.id,
            target_value=80.0,
            baseline_value=50.0,
            unit="%",
            direction="higherIsBetter",
        )
    )
    period = periods.parse(None, 1, today)
    db.add(
        KpiMeasurement(
            kind="period",
            kpi_card_id=measured.id,
            period_type="quarter" if period.quarter else "fiscal_year",
            period_key=period.key,
            period_start=period.start,
            period_end=period.end - timedelta(days=1),
            value=90.0,
            source="manual",
            status="verified",
        )
    )
    await db.flush()


async def test_strategy_needs_the_executive_permission(client, env):
    assert (await _get(client, env["plain"], "/strategy")).status_code == 403


async def test_strategy_counts_verified_values_against_ratified_targets(client, db, env):
    await _strategic_kpis(db, env["today"])
    body = (await _get(client, env["admin"], "/strategy")).json()

    totals = body["totals"]
    assert totals["strategic_objectives"] == 1
    assert (totals["linked"], totals["measured"], totals["on_target"]) == (2, 1, 1)
    states = {k["name"]: k for o in body["objectives"] for k in o["kpis"]}
    assert set(states) == {"Measured", "Unratified"}
    assert states["Measured"]["state"] == "on_target"
    assert states["Measured"]["attainment"] == 100.0
    assert states["Unratified"]["state"] == "no_ratified_target"
    assert states["Unratified"]["value"] is None


async def test_strategy_leaves_out_a_hidden_kpi_type(client, db, env):
    await _strategic_kpis(db, env["today"])
    kpi_type = (await db.execute(select(CardType).where(CardType.key == "KPI"))).scalar_one()
    kpi_type.is_hidden = True
    await db.flush()

    body = (await _get(client, env["admin"], "/strategy")).json()
    assert body["totals"]["linked"] == 0
    assert all(o["kpis"] == [] for o in body["objectives"])
