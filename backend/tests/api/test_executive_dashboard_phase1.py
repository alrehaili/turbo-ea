"""``GET /reports/executive`` — Phase 1 KPI correctness end to end.

The pure rules are pinned in ``tests/services/test_executive_dashboard_kpis.py``;
this covers what only the route does: reading the staleness and fiscal-year
settings, scoping the money to one fiscal year, naming the currency, and the
admin-only staleness setting. Scope / hidden-type / cost gating is covered by
``test_disclosure_phase1_prep.py::test_executive_applies_scope_hidden_types_and_cost_rules``.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.app_settings import AppSettings
from app.models.rationalization import AssessmentDecision, RationalizationAssessment
from tests.conftest import (
    auth_headers,
    create_budget_line,
    create_card,
    create_card_type,
    create_cost_line,
    create_role,
    create_status_report,
    create_user,
)

URL = "/api/v1/reports/executive"


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
    # Costs but not the rationalization module: sees savings totals, not records.
    await create_role(
        db,
        key="finance",
        label="Finance",
        permissions={
            "reports.executive_dashboard": True,
            "inventory.view": True,
            "costs.view": True,
        },
        is_system=False,
    )
    admin = await create_user(db, email="admin@test.com", role="admin")
    finance = await create_user(db, email="finance@test.com", role="finance")
    nocost = await create_user(db, email="exec@test.com", role="exec")
    await create_card_type(db, key="Initiative", label="Initiative")
    await create_card_type(db, key="Application", label="Application")
    await _settings(db, ppmEnabled=True, currency="SAR", fiscalYearStart=1)

    today = date.today()
    fresh = await create_card(db, card_type="Initiative", name="Fresh")
    old = await create_card(db, card_type="Initiative", name="Old")
    await create_card(db, card_type="Initiative", name="Silent")
    await create_card(
        db, card_type="Initiative", name="Done", attributes={"initiativeStatus": "completed"}
    )
    await create_status_report(db, initiative_id=fresh.id, report_date=today, cost_health="atRisk")
    await create_status_report(db, initiative_id=old.id, report_date=today - timedelta(days=200))

    await create_budget_line(db, initiative_id=fresh.id, fiscal_year=2025, amount=1000)
    await create_budget_line(db, initiative_id=fresh.id, fiscal_year=2026, amount=4000)
    await create_cost_line(db, initiative_id=fresh.id, actual=300, date=date(2025, 6, 1))
    await create_cost_line(db, initiative_id=fresh.id, actual=700, date=date(2026, 3, 1))
    await create_cost_line(db, initiative_id=fresh.id, actual=50, date=None)
    return {"admin": admin, "nocost": nocost, "finance": finance}


async def test_delivery_is_four_states_with_coverage_separate(client, db, env):
    body = (await client.get(URL, headers=auth_headers(env["admin"]))).json()
    d = body["delivery"]
    # No staleness configured: the 200-day-old report still counts.
    assert d["staleness_days"] is None
    assert d["states"] == {"onTrack": 1, "atRisk": 1, "offTrack": 0, "notReported": 1}
    assert d["excluded"]["completed"] == 1
    assert d["coverage"]["reported"] == 2 and d["coverage"]["in_flight"] == 3

    await _settings(db, initiativeReportStalenessDays=30)
    body = (await client.get(URL, headers=auth_headers(env["admin"]))).json()
    d = body["delivery"]
    assert d["staleness_days"] == 30
    assert d["states"]["notReported"] == 2
    assert d["coverage"]["stale_reports"] == 1
    assert d["on_track_pct"] == 0.0  # the only reporter is at risk


async def test_budget_is_one_fiscal_year_in_the_named_currency(client, env):
    body = (await client.get(f"{URL}?fiscal_year=2026", headers=auth_headers(env["admin"]))).json()
    b = body["delivery"]["budget"]
    assert b["status"] == "ok" and b["currency"] == "SAR" and body["currency"] == "SAR"
    assert (b["fiscal_year"], b["budget"], b["actual"]) == (2026, 4000, 700)
    assert b["undated_cost_lines"] == 1
    assert {2025, 2026} <= set(b["available_years"])

    b = (await client.get(f"{URL}?fiscal_year=2025", headers=auth_headers(env["admin"]))).json()[
        "delivery"
    ]["budget"]
    assert (b["budget"], b["actual"], b["execution_pct"]) == (1000, 300, 30.0)


async def test_fiscal_year_follows_the_start_month_setting(client, db, env):
    await _settings(db, fiscalYearStart=4)
    b = (await client.get(f"{URL}?fiscal_year=2026", headers=auth_headers(env["admin"]))).json()[
        "delivery"
    ]["budget"]
    # FY2026 with an April start = 2025-04-01 .. 2026-04-01: both dated lines.
    assert b["actual"] == 1000 and b["fiscal_year_start"] == 4


async def test_budget_restricted_without_costs_view(client, env):
    body = (await client.get(URL, headers=auth_headers(env["nocost"]))).json()
    b = body["delivery"]["budget"]
    assert b["status"] == "restricted"
    assert "budget" not in b and "actual" not in b
    # Non-financial indicators stay visible.
    assert body["delivery"]["coverage"]["in_flight"] == 3


async def test_rejects_out_of_range_fiscal_year(client, env):
    resp = await client.get(f"{URL}?fiscal_year=99", headers=auth_headers(env["admin"]))
    assert resp.status_code == 422


async def test_planned_savings_conflicts_are_excluded(client, db, env):
    app = await create_card(db, card_type="Application", name="CRM")
    other = await create_card(db, card_type="Application", name="ERP")
    for name, amounts in (("A", (100.0, 10.0)), ("B", (80.0, 10.0))):
        assessment = RationalizationAssessment(name=name, status="active")
        db.add(assessment)
        await db.flush()
        db.add(
            AssessmentDecision(
                assessment_id=assessment.id, card_id=app.id, planned_savings=amounts[0]
            )
        )
        db.add(
            AssessmentDecision(
                assessment_id=assessment.id, card_id=other.id, planned_savings=amounts[1]
            )
        )
    await db.flush()

    savings = (await client.get(URL, headers=auth_headers(env["admin"]))).json()["rationalization"][
        "planned_savings"
    ]
    assert savings["total"] == 10.0  # ERP once; CRM excluded
    assert savings["duplicates_merged"] == 1
    assert [c["card_name"] for c in savings["conflicts"]] == ["CRM"]
    assert savings["currency"] == "SAR" and savings["provenance"] == "forecast"
    assert savings["conflict_detail"] == "ok" and savings["conflict_count"] == 1

    # H1: without rationalization.view the conflict is counted, never described.
    finance = (await client.get(URL, headers=auth_headers(env["finance"]))).json()
    savings = finance["rationalization"]["planned_savings"]
    assert savings["status"] == "ok" and savings["total"] == 10.0
    assert savings["conflict_detail"] == "restricted" and savings["conflict_count"] == 1
    assert savings["conflicts"] is None and savings["excluded_range"] is None
    assert "CRM" not in str(finance)
    assert "candidates" not in str(savings) and "assessment" not in str(savings)


async def test_staleness_setting_is_admin_only_and_clearable(client, env):
    path = "/api/v1/settings/initiative-report-staleness"
    assert (await client.get(path, headers=auth_headers(env["nocost"]))).status_code == 403
    assert (
        await client.patch(path, json={"days": 30}, headers=auth_headers(env["nocost"]))
    ).status_code == 403
    assert (await client.get(path, headers=auth_headers(env["admin"]))).json() == {"days": None}
    assert (
        await client.patch(path, json={"days": 0}, headers=auth_headers(env["admin"]))
    ).status_code == 422
    resp = await client.patch(path, json={"days": 30}, headers=auth_headers(env["admin"]))
    assert resp.json() == {"days": 30}
    assert (await client.get(path, headers=auth_headers(env["admin"]))).json() == {"days": 30}
    resp = await client.patch(path, json={"days": None}, headers=auth_headers(env["admin"]))
    assert (await client.get(path, headers=auth_headers(env["admin"]))).json() == {"days": None}
