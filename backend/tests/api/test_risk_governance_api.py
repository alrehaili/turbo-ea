"""Risk ↔ EA governance-record links and architecture-risk figures (D-42; Batch 3.5).

A risk is architecture-related only through an explicit link; linking needs
``risks.manage`` and visibility of the record; a record the caller cannot see
does not exist for them — not in lists, counts, names or drill-downs — and
removing a visible link never touches a hidden one. Each risk counts once in
the totals; the record-type breakdown overlaps and says so; verified reduction
is Not Available.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.permissions import MEMBER_PERMISSIONS
from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.card_type import CardType
from app.models.event import Event
from app.models.risk_governance_link import RiskGovernanceLink
from app.models.tech_standard import StandardException, TechStandard
from app.services import risk_governance as rg
from app.services.card_read_scope import CardReadScope
from app.services.permission_service import PermissionService
from tests.conftest import (
    auth_headers,
    create_card,
    create_card_type,
    create_risk,
    create_role,
    create_user,
)

API = "/api/v1"
TODAY = date.today()


@pytest.fixture
async def env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    await create_role(
        db,
        key="riskonly",
        label="Risks only",
        permissions={"risks.view": True, "risks.manage": True, "inventory.view": True},
        is_system=False,
    )
    await create_card_type(db, key="Application", label="Application")
    await create_card_type(db, key="Secret", label="Secret")
    admin = await create_user(db, email="admin@test.com", role="admin")
    member = await create_user(db, email="member@test.com", role="member")
    riskonly = await create_user(db, email="riskonly@test.com", role="riskonly")
    app = await create_card(db, card_type="Application", name="Billing", user_id=admin.id)
    secret = await create_card(db, card_type="Secret", name="Zephyr", user_id=admin.id)
    ct = (await db.execute(select(CardType).where(CardType.key == "Secret"))).scalar_one()
    ct.role_permissions = {"member": {"inventory.view": False}}
    adr = ArchitectureDecision(
        reference_number=f"ADR-{uuid.uuid4().hex[:6]}",
        title="Event bus",
        status="signed",
        created_by=admin.id,
        signed_at=datetime.now(timezone.utc),
        signatories=[],
    )
    visible_review = ArbReview(title="Billing review", subject_card_id=app.id, status="approved")
    hidden_review = ArbReview(title="Zephyr review", subject_card_id=secret.id, status="approved")
    db.add_all([adr, visible_review, hidden_review])
    await db.flush()
    PermissionService.invalidate_type_permission_cache()
    return {
        "admin": admin,
        "member": member,
        "riskonly": riskonly,
        "app": app,
        "secret": secret,
        "adr": adr,
        "review": visible_review,
        "hidden_review": hidden_review,
    }


async def _link(client, user, risk, instrument, record_id):
    return await client.post(
        f"{API}/risks/{risk.id}/governance-links",
        json={"instrument": instrument, "record_id": str(record_id)},
        headers=auth_headers(user),
    )


async def test_link_is_recorded_once_and_audited(client, db, env):
    risk = await create_risk(db, title="Vendor lock-in")
    r = await _link(client, env["member"], risk, "adr", env["adr"].id)
    assert r.status_code == 201, r.text
    assert [link["instrument"] for link in r.json()["links"]] == ["adr"]
    r = await _link(client, env["member"], risk, "adr", env["adr"].id)
    assert r.status_code == 201 and len(r.json()["links"]) == 1
    rows = (await db.execute(select(RiskGovernanceLink))).scalars().all()
    assert len(rows) == 1 and rows[0].created_by == env["member"].id
    events = (
        (await db.execute(select(Event).where(Event.event_type == "risk.governance_linked")))
        .scalars()
        .all()
    )
    assert len(events) == 1 and events[0].user_id == env["member"].id


async def test_linking_needs_risks_manage(client, db, env):
    viewer_role = await create_role(
        db,
        key="rv",
        label="Risk viewer",
        permissions={"risks.view": True, "adr.view": True},
        is_system=False,
    )
    viewer = await create_user(db, email="rv@test.com", role=viewer_role.key)
    risk = await create_risk(db)
    r = await _link(client, viewer, risk, "adr", env["adr"].id)
    assert r.status_code == 403


async def test_linking_needs_the_record_module_permission(client, db, env):
    risk = await create_risk(db)
    # risks.manage alone does not open decision records.
    r = await _link(client, env["riskonly"], risk, "adr", env["adr"].id)
    assert r.status_code == 404


async def test_a_review_of_a_hidden_card_cannot_be_linked_or_seen(client, db, env):
    risk = await create_risk(db)
    r = await _link(client, env["member"], risk, "arb", env["hidden_review"].id)
    assert r.status_code == 404
    # Linked by someone who can see it: the member still sees nothing of it.
    assert (
        await _link(client, env["admin"], risk, "arb", env["hidden_review"].id)
    ).status_code == 201
    r = await client.get(
        f"{API}/risks/{risk.id}/governance-links", headers=auth_headers(env["member"])
    )
    assert r.json()["links"] == []
    assert "Zephyr" not in r.text


async def test_removing_a_visible_link_keeps_the_hidden_one(client, db, env):
    risk = await create_risk(db)
    for instrument, rec in (("arb", env["review"]), ("arb", env["hidden_review"])):
        assert (await _link(client, env["admin"], risk, instrument, rec.id)).status_code == 201
    r = await client.delete(
        f"{API}/risks/{risk.id}/governance-links/arb/{env['review'].id}",
        headers=auth_headers(env["member"]),
    )
    assert r.status_code == 200
    left = (await db.execute(select(RiskGovernanceLink))).scalars().all()
    assert [link.record_id for link in left] == [env["hidden_review"].id]
    # The hidden link cannot be removed by someone who cannot see its record.
    r = await client.delete(
        f"{API}/risks/{risk.id}/governance-links/arb/{env['hidden_review'].id}",
        headers=auth_headers(env["member"]),
    )
    assert r.status_code == 404


async def test_linked_risks_on_adr_need_risks_view(client, db, env):
    risk = await create_risk(db, title="Throughput")
    await _link(client, env["admin"], risk, "adr", env["adr"].id)
    r = await client.get(f"{API}/adr/{env['adr'].id}/risks", headers=auth_headers(env["member"]))
    assert r.status_code == 200 and r.json()["risks"][0]["title"] == "Throughput"
    no_risks = await create_role(
        db, key="adronly", label="ADR only", permissions={"adr.view": True}, is_system=False
    )
    u = await create_user(db, email="adronly@test.com", role=no_risks.key)
    r = await client.get(f"{API}/adr/{env['adr'].id}/risks", headers=auth_headers(u))
    assert r.status_code == 403


async def test_linked_risks_on_a_hidden_review_are_404(client, db, env):
    r = await client.get(
        f"{API}/arb/{env['hidden_review'].id}/risks", headers=auth_headers(env["member"])
    )
    assert r.status_code == 404


async def test_invalid_instrument_is_refused(client, db, env):
    risk = await create_risk(db)
    r = await _link(client, env["admin"], risk, "card", env["app"].id)
    assert r.status_code == 422


async def test_deleting_a_review_removes_its_links_and_records_it(client, db, env):
    risk = await create_risk(db)
    await _link(client, env["admin"], risk, "arb", env["review"].id)
    r = await client.delete(f"{API}/arb/{env['review'].id}", headers=auth_headers(env["admin"]))
    assert r.status_code == 204
    assert (await db.execute(select(RiskGovernanceLink))).scalars().all() == []
    events = (
        (await db.execute(select(Event).where(Event.event_type == "risk.governance_unlinked")))
        .scalars()
        .all()
    )
    assert any(e.data.get("reason") == "record_deleted" for e in events)


# ── Figures (I-53) ───────────────────────────────────────────────────────


async def test_each_risk_counts_once_and_the_type_breakdown_overlaps(db, env):
    both = await create_risk(db, title="Linked twice", status="mitigated")
    escalated = await create_risk(
        db, title="Critical", initial_probability="very_high", initial_impact="critical"
    )
    closed = await create_risk(db, title="Done", status="closed")
    await create_risk(db, title="Unlinked technology risk", category="technology")
    standard = TechStandard(name="Legacy SOAP", status="sunset")
    db.add(standard)
    await db.flush()
    waiver = StandardException(
        standard_id=standard.id,
        card_id=env["app"].id,
        status="approved",
        expiry_date=TODAY + timedelta(days=30),
    )
    db.add(waiver)
    await db.flush()
    for risk, kind, rid in (
        (both, "adr", env["adr"].id),
        (both, "exception", waiver.id),
        (escalated, "arb", env["review"].id),
        (closed, "adr", env["adr"].id),
    ):
        info = (await rg.describe(db, {(kind, rid)}))[(kind, rid)]
        await rg.link(db, risk, info, env["admin"].id)

    figures = await rg.architecture_risk_figures(db, CardReadScope.everything(), TODAY)
    assert figures["status"] == "ok"
    # The unlinked technology risk is never architecture-related (D-42.2).
    assert figures["total"] == 3
    assert figures["open"] == 2
    assert figures["mitigated"] == 1
    assert figures["escalated"] == 1
    assert figures["by_record_type"] == {"adr": 2, "arb": 1, "exception": 1, "additive": False}
    assert figures["linked_to_approved"] == {"count": 3, "additive": False}
    assert figures["verified_reduction"]["status"] == "not_available"


async def test_hidden_records_change_no_count(db, env):
    risk = await create_risk(db, title="Zephyr outage")
    info = (await rg.describe(db, {("arb", env["hidden_review"].id)}))[
        ("arb", env["hidden_review"].id)
    ]
    await rg.link(db, risk, info, env["admin"].id)
    member_scope = await CardReadScope.load(db, env["member"])
    figures = await rg.architecture_risk_figures(db, member_scope, TODAY)
    assert figures["status"] == "not_available"
    assert figures["reason"] == {"code": "no_linked_risks"}
    assert await rg.architecture_risk_rows(db, env["member"], member_scope, TODAY) == []


async def test_drilldown_withholds_records_the_reader_cannot_open(db, env):
    risk = await create_risk(db, title="Coupling")
    info = (await rg.describe(db, {("adr", env["adr"].id)}))[("adr", env["adr"].id)]
    await rg.link(db, risk, info, env["admin"].id)
    scope = await CardReadScope.load(db, env["riskonly"])
    rows = await rg.architecture_risk_rows(db, env["riskonly"], scope, TODAY)
    assert rows[0]["records"] == [] and rows[0]["records_withheld"] == 1


async def test_rsk01_drilldown_needs_risks_view(client, db, env):
    role = await create_role(
        db,
        key="exec",
        label="Executive",
        permissions={"reports.executive_dashboard": True},
        is_system=False,
    )
    exec_user = await create_user(db, email="exec@test.com", role=role.key)
    r = await client.get(
        f"{API}/reports/executive/kpi/RSK-01/drilldown", headers=auth_headers(exec_user)
    )
    assert r.status_code == 403


async def test_governance_page_carries_the_rsk01_tile(client, db, env):
    risk = await create_risk(db, title="Coupling")
    await _link(client, env["admin"], risk, "adr", env["adr"].id)
    r = await client.get(f"{API}/reports/executive/governance", headers=auth_headers(env["admin"]))
    assert r.status_code == 200, r.text
    impact = r.json()["impact"]
    assert impact["architecture_risks"]["total"] == 1
    tile = impact["architecture_risk_tile"]
    assert (tile["key"], tile["value"], tile["temporal"]) == ("RSK-01", 1, "current_state")
