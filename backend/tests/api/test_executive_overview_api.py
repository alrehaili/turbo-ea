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


async def test_previous_period_comes_from_dated_reports(client, db, env):
    # The only report is today's, so the previous quarter had nobody reporting.
    body = (await _get(client, env["admin"], "/overview")).json()
    delivery = next(t for t in body["kpis"] if t["slot"] == "delivery")
    assert delivery["previous"]["status"] == "not_available"
    assert delivery["previous"]["period"] == body["previous_period"]["key"]


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
        "count": 2,
        "items": None,
        "open": 3,
        "mitigated": 0,
    }
    assert limited["arb"]["status"] == "restricted" and limited["arb"]["count"] == 1
    assert "Data centre outage" not in str(limited) and "Review CRM" not in str(limited)

    overview = (await _get(client, env["exec"], "/overview")).json()
    assert overview["decisions_panel"] == []
    escalation = next(t for t in overview["kpis"] if t["slot"] == "decisions")
    assert escalation["value"] == 2 and escalation["details"]["open_risks"] == 3


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
