"""Decision actions and implementation verification over the API (D-41; Batch 3.4).

The acceptance flow (GOVERNANCE_MEASUREMENT_MODEL.md §6, as D-41 approved it):
an ADR is signed with a deadline, gets two actions, both are completed with
evidence, the implementation is submitted and independently verified before
the deadline — and only then does GOV-05 count it as implemented on time. A
verification by someone who executed it is refused; a decision with no linked
card is verifiable through recorded references; decision actions cannot be
changed through the generic todo routes.
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
from app.models.decision_implementation import DecisionImplementation
from app.models.document import Document
from app.models.governance_transition import GovernanceTransition
from app.services.card_read_scope import CardReadScope
from app.services.executive import governance as gov
from app.services.executive.periods import Period
from app.services.permission_service import PermissionService
from tests.conftest import (
    auth_headers,
    create_card,
    create_card_type,
    create_role,
    create_user,
)

API = "/api/v1"


@pytest.fixture
async def env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    await create_role(
        db,
        key="verifier",
        label="EA Governance Office",
        permissions={**MEMBER_PERMISSIONS, "governance.verify_implementation": True},
        is_system=False,
    )
    await create_card_type(db, key="Application", label="Application")
    await create_card_type(db, key="Secret", label="Secret")
    admin = await create_user(db, email="admin@test.com", role="admin")
    owner = await create_user(db, email="owner@test.com", role="member")
    verifier = await create_user(db, email="verifier@test.com", role="verifier")
    app = await create_card(db, card_type="Application", name="Billing", user_id=admin.id)
    secret = await create_card(db, card_type="Secret", name="Zephyr", user_id=admin.id)
    ct = (await db.execute(select(CardType).where(CardType.key == "Secret"))).scalar_one()
    ct.role_permissions = {"member": {"inventory.view": False}}
    await db.flush()
    PermissionService.invalidate_type_permission_cache()
    return {"admin": admin, "owner": owner, "verifier": verifier, "app": app, "secret": secret}


async def _signed_adr(db, author) -> ArchitectureDecision:
    adr = ArchitectureDecision(
        reference_number=f"ADR-{uuid.uuid4().hex[:6]}",
        title="Move billing to the platform",
        status="signed",
        created_by=author.id,
        signed_at=datetime.now(timezone.utc),
        signatories=[],
    )
    db.add(adr)
    await db.flush()
    return adr


async def _action(client, kind, did, admin, owner, due="2026-12-01"):
    r = await client.post(
        f"{API}/{kind}/{did}/actions",
        json={"description": "Cut over", "assigned_to": str(owner.id), "due_date": due},
        headers=auth_headers(admin),
    )
    assert r.status_code == 201, r.text
    return r.json()["actions"][-1]["id"]


async def _complete(client, kind, did, aid, user, evidence):
    return await client.post(
        f"{API}/{kind}/{did}/actions/{aid}/complete",
        json={"note": "Done", "evidence": evidence},
        headers=auth_headers(user),
    )


async def test_adr_end_to_end_verified_on_time_counts_in_gov05(client, db, env):
    admin, owner, verifier = env["admin"], env["owner"], env["verifier"]
    # The deadline is proposed on the draft and approved when signed (D-41.3).
    r = await client.post(
        f"{API}/adr", json={"title": "Platform move"}, headers=auth_headers(admin)
    )
    adr_id = r.json()["id"]
    due = (date.today() + timedelta(days=30)).isoformat()
    r = await client.put(
        f"{API}/adr/{adr_id}/implementation/due-date",
        json={"due_date": due},
        headers=auth_headers(admin),
    )
    assert r.status_code == 200 and r.json()["implementation"]["due_date"] == due
    assert r.json()["implementation"]["original_due_date"] is None
    r = await client.post(
        f"{API}/adr/{adr_id}/request-signatures",
        json={"user_ids": [str(admin.id)]},
        headers=auth_headers(admin),
    )
    assert r.status_code == 200, r.text
    r = await client.post(f"{API}/adr/{adr_id}/sign", json={}, headers=auth_headers(admin))
    assert r.status_code == 200, r.text
    body = (
        await client.get(f"{API}/adr/{adr_id}/implementation", headers=auth_headers(admin))
    ).json()
    assert body["implementation"]["original_due_date"] == due
    assert body["implementation"]["due_date_basis"] == "with_decision"
    assert body["state"] == "no_plan"

    a1 = await _action(client, "adr", adr_id, admin, owner)
    a2 = await _action(client, "adr", adr_id, admin, owner)
    ref = [{"kind": "reference", "text": "CHG-1001"}]
    for aid in (a1, a2):
        r = await _complete(client, "adr", adr_id, aid, owner, ref)
        assert r.status_code == 200, r.text
    body = r.json()
    # Completed actions alone are not implementation (D-32).
    assert body["state"] == "in_progress"

    r = await client.post(
        f"{API}/adr/{adr_id}/implementation/submit", json={}, headers=auth_headers(owner)
    )
    assert r.json()["state"] == "awaiting_verification"

    # The owner who executed it cannot verify it even with the permission.
    attestation = {"examined": "CHG-1001 record", "demonstrates": "deployed", "confirmed": True}
    r = await client.post(
        f"{API}/adr/{adr_id}/implementation/verify",
        json={"outcome": "verified", "attestation": attestation},
        headers=auth_headers(owner),
    )
    assert r.status_code == 403
    r = await client.post(
        f"{API}/adr/{adr_id}/implementation/verify",
        json={"outcome": "verified", "attestation": attestation},
        headers=auth_headers(verifier),
    )
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "implemented"

    # Counted in the period its original deadline falls in, once it has passed.
    due_day = date.fromisoformat(due)
    period = Period(
        fy=2027,
        quarter=None,
        start=due_day,
        end=due_day + timedelta(days=1),
        as_of=due_day,
        is_current=False,
    )
    result = await gov.decision_implementation(db, await CardReadScope.load(db, admin), period)
    assert result["status"] == "ok"
    assert result["outcomes"]["verified_on_time"] == 1
    assert result["value"] == 100.0


async def test_self_verification_by_the_submitter_is_refused(client, db, env):
    adr = await _signed_adr(db, env["admin"])
    aid = await _action(client, "adr", adr.id, env["admin"], env["owner"])
    await _complete(client, "adr", adr.id, aid, env["owner"], [{"kind": "reference", "text": "R"}])
    # The verifier submits, so they may no longer verify.
    r = await client.post(
        f"{API}/adr/{adr.id}/implementation/submit", json={}, headers=auth_headers(env["admin"])
    )
    assert r.status_code == 200
    r = await client.post(
        f"{API}/adr/{adr.id}/implementation/verify",
        json={
            "outcome": "verified",
            "attestation": {"examined": "a", "demonstrates": "b", "confirmed": True},
        },
        headers=auth_headers(env["admin"]),
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "self_verification"


async def test_verify_needs_the_permission(client, db, env):
    adr = await _signed_adr(db, env["admin"])
    r = await client.post(
        f"{API}/adr/{adr.id}/implementation/verify",
        json={"outcome": "returned", "note": "x"},
        headers=auth_headers(env["owner"]),
    )
    assert r.status_code == 403


async def test_actions_need_manage_owner_and_due_date(client, db, env):
    adr = await _signed_adr(db, env["admin"])
    # A role with adr.view but not adr.manage is refused.
    viewer_role = await create_role(
        db, key="adrview", label="ADR view", permissions={"adr.view": True}, is_system=False
    )
    viewer = await create_user(db, email="v@test.com", role=viewer_role.key)
    r = await client.post(
        f"{API}/adr/{adr.id}/actions",
        json={"description": "x", "assigned_to": str(env["owner"].id), "due_date": "2026-12-01"},
        headers=auth_headers(viewer),
    )
    assert r.status_code == 403
    r = await client.post(
        f"{API}/adr/{adr.id}/actions",
        json={"description": "x", "due_date": "2026-12-01"},
        headers=auth_headers(env["admin"]),
    )
    assert r.status_code == 422 and r.json()["detail"]["code"] == "owner_required"
    r = await client.post(
        f"{API}/adr/{adr.id}/actions",
        json={"description": "x", "assigned_to": str(env["owner"].id)},
        headers=auth_headers(env["admin"]),
    )
    assert r.status_code == 422 and r.json()["detail"]["code"] == "due_date_required"


async def test_actions_wait_for_the_decision(client, db, env):
    r = await client.post(f"{API}/adr", json={"title": "Draft"}, headers=auth_headers(env["admin"]))
    r = await client.post(
        f"{API}/adr/{r.json()['id']}/actions",
        json={"description": "x", "assigned_to": str(env["owner"].id), "due_date": "2026-12-01"},
        headers=auth_headers(env["admin"]),
    )
    assert r.status_code == 409 and r.json()["detail"]["code"] == "decision_not_approved"


async def test_completion_needs_evidence(client, db, env):
    adr = await _signed_adr(db, env["admin"])
    aid = await _action(client, "adr", adr.id, env["admin"], env["owner"])
    r = await _complete(client, "adr", adr.id, aid, env["owner"], [])
    assert r.status_code == 422 and r.json()["detail"]["code"] == "evidence_required"


async def test_card_evidence_must_be_on_a_linked_card(client, db, env):
    adr = await _signed_adr(db, env["admin"])
    doc = Document(card_id=env["app"].id, name="Runbook", url="https://example.com/rb")
    db.add(doc)
    await db.flush()
    aid = await _action(client, "adr", adr.id, env["admin"], env["owner"])
    r = await _complete(
        client, "adr", adr.id, aid, env["owner"], [{"kind": "document", "id": str(doc.id)}]
    )
    assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_evidence_ref"


async def test_generic_todo_routes_refuse_a_decision_action(client, db, env):
    adr = await _signed_adr(db, env["admin"])
    aid = await _action(client, "adr", adr.id, env["admin"], env["owner"])
    r = await client.patch(
        f"{API}/todos/{aid}", json={"status": "done"}, headers=auth_headers(env["owner"])
    )
    assert r.status_code == 409
    r = await client.delete(f"{API}/todos/{aid}", headers=auth_headers(env["owner"]))
    assert r.status_code == 409


async def test_arb_approval_carries_the_deadline_and_revision_keeps_the_original(client, db, env):
    h = auth_headers(env["admin"])
    rid = (
        await client.post(
            f"{API}/arb", json={"title": "Review", "subject_card_id": str(env["app"].id)}, headers=h
        )
    ).json()["id"]
    r = await client.patch(
        f"{API}/arb/{rid}",
        json={"status": "deferred", "implementation_due_date": "2027-01-31"},
        headers=h,
    )
    assert r.status_code == 422
    r = await client.patch(
        f"{API}/arb/{rid}",
        json={"status": "approved", "implementation_due_date": "2027-01-31"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    r = await client.put(
        f"{API}/arb/{rid}/implementation/due-date", json={"due_date": "2027-03-31"}, headers=h
    )
    assert r.status_code == 422 and r.json()["detail"]["code"] == "due_date_reason_required"
    r = await client.put(
        f"{API}/arb/{rid}/implementation/due-date",
        json={"due_date": "2027-03-31", "reason": "vendor delay"},
        headers=h,
    )
    impl = r.json()["implementation"]
    assert (impl["original_due_date"], impl["due_date"], impl["revised"]) == (
        "2027-01-31",
        "2027-03-31",
        True,
    )
    rows = (
        await db.execute(
            select(GovernanceTransition)
            .where(GovernanceTransition.record_id == uuid.UUID(rid))
            .order_by(GovernanceTransition.occurred_at)
        )
    ).scalars()
    kinds = [t.event_kind for t in rows if t.instrument == "arb_impl"]
    assert kinds == ["due_date_set", "due_date_changed"]


async def test_arb_review_of_a_hidden_card_is_404(client, db, env):
    review = ArbReview(title="Secret review", subject_card_id=env["secret"].id, status="approved")
    db.add(review)
    await db.flush()
    r = await client.get(
        f"{API}/arb/{review.id}/implementation", headers=auth_headers(env["owner"])
    )
    assert r.status_code == 404


async def test_gov05_discloses_decisions_without_a_deadline(db, env):
    await _signed_adr(db, env["admin"])
    with_deadline = await _signed_adr(db, env["admin"])
    db.add(
        DecisionImplementation(
            decision_kind="adr",
            decision_id=with_deadline.id,
            status="open",
            due_date=date(2026, 8, 15),
            original_due_date=date(2026, 8, 15),
            due_date_basis="with_decision",
        )
    )
    await db.flush()
    period = Period(
        fy=2027,
        quarter=None,
        start=date(2026, 7, 1),
        end=date(2026, 10, 1),
        as_of=date(2026, 9, 30),
        is_current=False,
    )
    result = await gov.decision_implementation(
        db, await CardReadScope.load(db, env["admin"]), period
    )
    # One due decision, not verified: 0 %, never inflated by dropping the other.
    assert result["status"] == "ok" and result["value"] == 0.0
    assert result["eligible"] == 1 and result["outcomes"]["no_plan"] == 1
    assert result["excluded"]["no_deadline"] == 1
    assert result["planning_coverage"]["approved_decisions"] == 2
    assert result["planning_coverage"]["planned"] == 0
