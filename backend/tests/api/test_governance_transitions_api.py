"""Governance transition history over the API (D-35, D-34; Batch 3.2).

Each status change of an ARB review, a standard exception and an ADR leaves one
row, readable under the instrument's own view permission; a record about a
hidden card is 404; a record decided before the history existed reads
``recorded: false`` instead of a reconstructed past.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.permissions import MEMBER_PERMISSIONS
from app.models.arb_review import ArbReview
from app.models.card_type import CardType
from app.models.governance_transition import GovernanceTransition
from app.models.tech_standard import StandardException, TechStandard
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
        key="nogov",
        label="No governance",
        permissions={"inventory.view": True},
        is_system=False,
    )
    await create_card_type(db, key="Application", label="Application")
    await create_card_type(db, key="Secret", label="Secret")
    admin = await create_user(db, email="admin@test.com", role="admin")
    member = await create_user(db, email="member@test.com", role="member")
    nogov = await create_user(db, email="nogov@test.com", role="nogov")
    app = await create_card(db, card_type="Application", name="Billing", user_id=admin.id)
    secret = await create_card(db, card_type="Secret", name="Zephyr", user_id=admin.id)
    ct = (await db.execute(select(CardType).where(CardType.key == "Secret"))).scalar_one()
    ct.role_permissions = {"member": {"inventory.view": False}}
    await db.flush()
    PermissionService.invalidate_type_permission_cache()
    return {"admin": admin, "member": member, "nogov": nogov, "app": app, "secret": secret}


async def _rows(db, instrument, record_id):
    res = await db.execute(
        select(GovernanceTransition)
        .where(
            GovernanceTransition.instrument == instrument,
            GovernanceTransition.record_id == uuid.UUID(record_id),
        )
        .order_by(GovernanceTransition.occurred_at, GovernanceTransition.created_at)
    )
    return [(t.from_status, t.to_status) for t in res.scalars().all()]


# --------------------------------------------------------------------------- #
# ARB                                                                          #
# --------------------------------------------------------------------------- #
async def test_arb_lifecycle_is_recorded_and_deferral_is_its_own_step(client, db, env):
    h = auth_headers(env["admin"])
    rid = (
        await client.post(
            f"{API}/arb", json={"title": "R", "subject_card_id": str(env["app"].id)}, headers=h
        )
    ).json()["id"]
    for status in ("deferred", "approved"):
        resp = await client.patch(f"{API}/arb/{rid}", json={"status": status}, headers=h)
        assert resp.status_code == 200
        assert resp.json()["status"] == status
    # A same-status save is not a transition.
    await client.patch(f"{API}/arb/{rid}", json={"status": "approved"}, headers=h)
    # A non-status edit is not one either.
    await client.patch(f"{API}/arb/{rid}", json={"decision_notes": "ok"}, headers=h)

    assert await _rows(db, "arb", rid) == [
        (None, "scheduled"),
        ("scheduled", "deferred"),
        ("deferred", "approved"),
    ]
    body = (await client.get(f"{API}/arb/{rid}/transitions", headers=h)).json()
    assert body["recorded"] is True
    assert [t["to_status"] for t in body["transitions"]] == ["scheduled", "deferred", "approved"]
    actor = body["transitions"][-1]["actor"]
    assert actor == {"id": str(env["admin"].id), "display_name": env["admin"].display_name}


async def test_arb_invalid_status_records_nothing(client, db, env):
    h = auth_headers(env["admin"])
    rid = (await client.post(f"{API}/arb", json={"title": "R"}, headers=h)).json()["id"]
    resp = await client.patch(f"{API}/arb/{rid}", json={"status": "withdrawn"}, headers=h)
    assert resp.status_code == 400
    assert await _rows(db, "arb", rid) == [(None, "scheduled")]


async def test_arb_history_needs_arb_view_and_hides_a_hidden_subject(client, db, env):
    review = ArbReview(title="Secret review", subject_card_id=env["secret"].id)
    db.add(review)
    await db.flush()
    path = f"{API}/arb/{review.id}/transitions"
    assert (await client.get(path, headers=auth_headers(env["nogov"]))).status_code == 403
    assert (await client.get(path, headers=auth_headers(env["member"]))).status_code == 404
    # Created before the history existed: nothing is reconstructed.
    body = (await client.get(path, headers=auth_headers(env["admin"]))).json()
    assert body == {"recorded": False, "transitions": []}


async def test_arb_history_rejects_a_malformed_id(client, env):
    resp = await client.get(f"{API}/arb/not-a-uuid/transitions", headers=auth_headers(env["admin"]))
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# Standard exceptions                                                          #
# --------------------------------------------------------------------------- #
async def _exception(client, user, card_id):
    h = auth_headers(user)
    sid = (
        await client.post(
            f"{API}/tech-standards",
            json={"name": "Legacy SOAP", "category": "integration", "status": "prohibited"},
            headers=h,
        )
    ).json()["id"]
    resp = await client.post(
        f"{API}/tech-standards/{sid}/exceptions", json={"card_id": str(card_id)}, headers=h
    )
    assert resp.status_code == 201
    return resp.json()


async def test_exception_decision_is_dated_and_recorded(client, db, env):
    h = auth_headers(env["admin"])
    exc = await _exception(client, env["admin"], env["app"].id)
    assert exc["decided_at"] is None
    eid = exc["id"]
    resp = await client.post(
        f"{API}/tech-standards/exceptions/{eid}/decision?action=approve", headers=h
    )
    assert resp.status_code == 200
    assert resp.json()["decided_at"] is not None
    await client.post(f"{API}/tech-standards/exceptions/{eid}/decision?action=reject", headers=h)
    assert await _rows(db, "exception", eid) == [
        (None, "requested"),
        ("requested", "approved"),
        ("approved", "rejected"),
    ]
    body = (
        await client.get(f"{API}/tech-standards/exceptions/{eid}/transitions", headers=h)
    ).json()
    assert body["recorded"] is True
    assert [t["to_status"] for t in body["transitions"]] == ["requested", "approved", "rejected"]


async def test_exception_invalid_action_records_nothing(client, db, env):
    h = auth_headers(env["admin"])
    eid = (await _exception(client, env["admin"], env["app"].id))["id"]
    resp = await client.post(
        f"{API}/tech-standards/exceptions/{eid}/decision?action=withdraw", headers=h
    )
    assert resp.status_code == 422
    assert await _rows(db, "exception", eid) == [(None, "requested")]


async def test_exception_history_needs_view_and_hides_a_hidden_card(client, env):
    eid = (await _exception(client, env["admin"], env["secret"].id))["id"]
    path = f"{API}/tech-standards/exceptions/{eid}/transitions"
    assert (await client.get(path, headers=auth_headers(env["nogov"]))).status_code == 403
    assert (await client.get(path, headers=auth_headers(env["member"]))).status_code == 404
    assert (await client.get(path, headers=auth_headers(env["admin"]))).status_code == 200


# --------------------------------------------------------------------------- #
# ADR                                                                          #
# --------------------------------------------------------------------------- #
async def test_adr_lifecycle_draft_review_recall_review_signed(client, db, env):
    admin = env["admin"]
    h = auth_headers(admin)
    aid = (await client.post(f"{API}/adr", json={"title": "Use Kafka"}, headers=h)).json()["id"]
    sig = {"user_ids": [str(admin.id)]}
    assert (
        await client.post(f"{API}/adr/{aid}/request-signatures", json=sig, headers=h)
    ).status_code == 200
    # Re-requesting while in review is the same status: no row.
    await client.post(f"{API}/adr/{aid}/request-signatures", json=sig, headers=h)
    assert (await client.post(f"{API}/adr/{aid}/recall-signatures", headers=h)).status_code == 200
    await client.post(f"{API}/adr/{aid}/request-signatures", json=sig, headers=h)
    resp = await client.post(f"{API}/adr/{aid}/sign", json={}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "signed"

    assert await _rows(db, "adr", aid) == [
        (None, "draft"),
        ("draft", "in_review"),
        ("in_review", "draft"),
        ("draft", "in_review"),
        ("in_review", "signed"),
    ]
    # A revision starts its own history as a new draft.
    rev = (await client.post(f"{API}/adr/{aid}/revise", headers=h)).json()["id"]
    assert await _rows(db, "adr", rev) == [(None, "draft")]
    body = (await client.get(f"{API}/adr/{aid}/transitions", headers=h)).json()
    assert body["transitions"][-1]["to_status"] == "signed"


async def test_adr_rejection_returns_to_draft_with_a_row(client, db, env):
    admin = env["admin"]
    h = auth_headers(admin)
    aid = (await client.post(f"{API}/adr", json={"title": "T"}, headers=h)).json()["id"]
    await client.post(
        f"{API}/adr/{aid}/request-signatures", json={"user_ids": [str(admin.id)]}, headers=h
    )
    resp = await client.post(f"{API}/adr/{aid}/reject", json={"comment": "no"}, headers=h)
    assert resp.status_code == 200
    assert (await _rows(db, "adr", aid))[-1] == ("in_review", "draft")


async def test_adr_duplicate_starts_a_fresh_history(client, db, env):
    h = auth_headers(env["admin"])
    aid = (await client.post(f"{API}/adr", json={"title": "T"}, headers=h)).json()["id"]
    dup = (await client.post(f"{API}/adr/{aid}/duplicate", headers=h)).json()["id"]
    assert await _rows(db, "adr", dup) == [(None, "draft")]


async def test_adr_history_needs_adr_view(client, env):
    h = auth_headers(env["admin"])
    aid = (await client.post(f"{API}/adr", json={"title": "T"}, headers=h)).json()["id"]
    path = f"{API}/adr/{aid}/transitions"
    assert (await client.get(path, headers=auth_headers(env["nogov"]))).status_code == 403
    assert (await client.get(path, headers=auth_headers(env["member"]))).status_code == 200


# --------------------------------------------------------------------------- #
# D-40: remediation, verification, withdrawal, deletion                        #
# --------------------------------------------------------------------------- #
@pytest.fixture
async def lifecycle(db, env):
    await create_role(
        db,
        key="stdview",
        label="Standards viewer",
        permissions={"tech_standards.view": True, "inventory.view": True},
        is_system=False,
    )
    second = await create_user(db, email="member2@test.com", role="member")
    requester = await create_user(db, email="req@test.com", role="stdview")
    stranger = await create_user(db, email="other@test.com", role="stdview")
    return {**env, "member2": second, "requester": requester, "stranger": stranger}


async def _approved(client, env):
    """An exception requested by the admin and approved by the admin."""
    exc = await _exception(client, env["admin"], env["app"].id)
    resp = await client.post(
        f"{API}/tech-standards/exceptions/{exc['id']}/decision?action=approve",
        headers=auth_headers(env["admin"]),
    )
    assert resp.status_code == 200
    return exc["id"]


async def test_remediation_needs_an_independent_verifier(client, db, lifecycle):
    eid = await _approved(client, lifecycle)
    base = f"{API}/tech-standards/exceptions/{eid}"
    member = auth_headers(lifecycle["member"])
    resp = await client.post(
        f"{base}/remediation", json={"evidence": "Moved to REST"}, headers=member
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "remediation_submitted"
    assert body["remediation_evidence"] == "Moved to REST"
    assert body["remediation_submitted_by"] == str(lifecycle["member"].id)

    verify = {"outcome": "verified"}
    # The submitter and the requester may not verify their own case.
    for who in ("member", "admin"):
        resp = await client.post(
            f"{base}/remediation/verify", json=verify, headers=auth_headers(lifecycle[who])
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "self_verification"
    resp = await client.post(
        f"{base}/remediation/verify", json=verify, headers=auth_headers(lifecycle["member2"])
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "remediated"
    assert resp.json()["remediation_verified_by"] == str(lifecycle["member2"].id)
    assert (await _rows(db, "exception", eid))[-2:] == [
        ("approved", "remediation_submitted"),
        ("remediation_submitted", "remediated"),
    ]


async def test_returned_remediation_goes_back_to_approved_with_a_note(client, db, lifecycle):
    eid = await _approved(client, lifecycle)
    base = f"{API}/tech-standards/exceptions/{eid}"
    await client.post(
        f"{base}/remediation", json={"evidence": "e"}, headers=auth_headers(lifecycle["member"])
    )
    other = auth_headers(lifecycle["member2"])
    resp = await client.post(
        f"{base}/remediation/verify", json={"outcome": "returned"}, headers=other
    )
    assert resp.status_code == 422
    resp = await client.post(
        f"{base}/remediation/verify",
        json={"outcome": "returned", "note": "Still on SOAP"},
        headers=other,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


async def test_remediation_input_and_permission_are_checked(client, lifecycle):
    eid = await _approved(client, lifecycle)
    base = f"{API}/tech-standards/exceptions/{eid}"
    resp = await client.post(
        f"{base}/remediation", json={"evidence": ""}, headers=auth_headers(lifecycle["member"])
    )
    assert resp.status_code == 422
    resp = await client.post(
        f"{base}/remediation", json={"evidence": "e"}, headers=auth_headers(lifecycle["requester"])
    )
    assert resp.status_code == 403  # needs tech_standards.manage
    resp = await client.post(
        f"{base}/remediation/verify",
        json={"outcome": "verified"},
        headers=auth_headers(lifecycle["member2"]),
    )
    assert resp.status_code == 409  # nothing submitted yet
    assert resp.json()["detail"]["code"] == "invalid_state"


async def test_remediation_of_a_hidden_cards_exception_is_404(client, lifecycle):
    exc = await _exception(client, lifecycle["admin"], lifecycle["secret"].id)
    resp = await client.post(
        f"{API}/tech-standards/exceptions/{exc['id']}/remediation",
        json={"evidence": "e"},
        headers=auth_headers(lifecycle["member"]),
    )
    assert resp.status_code == 404


async def test_withdrawal_by_the_requester_or_a_manager_only(client, db, lifecycle):
    std = TechStandard(name="Old FTP", status="prohibited")
    db.add(std)
    await db.flush()
    exc = StandardException(
        standard_id=std.id,
        card_id=lifecycle["app"].id,
        status="requested",
        created_by=lifecycle["requester"].id,
    )
    db.add(exc)
    await db.flush()
    path = f"{API}/tech-standards/exceptions/{exc.id}/withdraw"
    body = {"reason": "Project cancelled"}
    resp = await client.post(path, json=body, headers=auth_headers(lifecycle["stranger"]))
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "not_requester"
    assert (
        await client.post(path, json=body, headers=auth_headers(lifecycle["nogov"]))
    ).status_code == 403
    assert (
        await client.post(path, json={"reason": ""}, headers=auth_headers(lifecycle["requester"]))
    ).status_code == 422
    resp = await client.post(path, json=body, headers=auth_headers(lifecycle["requester"]))
    assert resp.status_code == 200
    assert resp.json()["status"] == "withdrawn"
    assert resp.json()["withdrawal_reason"] == "Project cancelled"
    # Withdrawn is final: a second withdrawal is a state error.
    resp = await client.post(path, json=body, headers=auth_headers(lifecycle["member"]))
    assert resp.status_code == 409


async def test_a_manager_may_withdraw_an_approved_exception(client, lifecycle):
    eid = await _approved(client, lifecycle)
    resp = await client.post(
        f"{API}/tech-standards/exceptions/{eid}/withdraw",
        json={"reason": "Replaced by a broader waiver"},
        headers=auth_headers(lifecycle["member"]),
    )
    assert resp.status_code == 200


async def _audit(db):
    from app.models.audit_log import AuditLogEntry

    await db.rollback()
    res = await db.execute(
        select(AuditLogEntry).where(AuditLogEntry.action == "admin.tech_standard_exception.deleted")
    )
    return list(res.scalars().all())


async def test_hard_delete_is_an_audited_admin_correction(client, db, lifecycle):
    eid = await _approved(client, lifecycle)
    path = f"{API}/tech-standards/exceptions/{eid}"
    # A routine manager can no longer delete; withdrawal is the way to close.
    assert (await client.delete(path, headers=auth_headers(lifecycle["member"]))).status_code == 403
    admin = auth_headers(lifecycle["admin"])
    resp = await client.delete(path, headers=admin)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "reason_required"
    resp = await client.delete(
        f"{path}?reason=Raised%20against%20the%20wrong%20card", headers=admin
    )
    assert resp.status_code == 204
    assert (await client.get(f"{path}/transitions", headers=admin)).status_code == 404
    entries = await _audit(db)
    assert len(entries) == 1
    assert entries[0].details["context"]["deletion_reason"] == "Raised against the wrong card"
    assert entries[0].details["context"]["status"] == "approved"
    # The history outlives the record, ending in a "deleted" row.
    assert (await _rows(db, "exception", eid))[-1] == ("approved", "deleted")


async def test_a_standard_with_decided_exceptions_cannot_be_deleted(client, lifecycle):
    eid = await _approved(client, lifecycle)
    admin = auth_headers(lifecycle["admin"])
    sid = (await client.get(f"{API}/tech-standards/exceptions", headers=admin)).json()
    sid = next(e["standard_id"] for e in sid if e["id"] == eid)
    resp = await client.delete(f"{API}/tech-standards/{sid}", headers=admin)
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "exceptions_have_lifecycle"


# --------------------------------------------------------------------------- #
# D-39: delay attribution on ARB deferral and ADR drafts                       #
# --------------------------------------------------------------------------- #
async def _rows_full(db, instrument, record_id):
    res = await db.execute(
        select(GovernanceTransition)
        .where(
            GovernanceTransition.instrument == instrument,
            GovernanceTransition.record_id == uuid.UUID(record_id),
        )
        .order_by(GovernanceTransition.occurred_at, GovernanceTransition.created_at)
    )
    return list(res.scalars().all())


async def test_arb_deferral_records_who_the_delay_is_due_to(client, db, env):
    h = auth_headers(env["admin"])
    rid = (await client.post(f"{API}/arb", json={"title": "R"}, headers=h)).json()["id"]
    path = f"{API}/arb/{rid}"
    resp = await client.patch(
        path, json={"status": "deferred", "delay_attribution": "requester"}, headers=h
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "delay_reason_required"
    resp = await client.patch(
        path, json={"status": "approved", "delay_attribution": "governance"}, headers=h
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "delay_only_on_deferral"
    resp = await client.patch(
        path,
        json={"status": "deferred", "delay_attribution": "external", "delay_reason": "Vendor SLA"},
        headers=h,
    )
    assert resp.status_code == 200
    last = (await _rows_full(db, "arb", rid))[-1]
    assert (last.to_status, last.delay_attribution, last.reason) == (
        "deferred",
        "external",
        "Vendor SLA",
    )
    body = (await client.get(f"{path}/transitions", headers=h)).json()
    assert body["transitions"][-1]["delay_attribution"] == "external"


async def test_adr_draft_moves_carry_an_optional_attribution(client, db, env):
    admin = env["admin"]
    h = auth_headers(admin)
    resp = await client.post(
        f"{API}/adr",
        json={"title": "T", "delay_attribution": "requester", "delay_reason": "Author drafting"},
        headers=h,
    )
    assert resp.status_code == 201
    aid = resp.json()["id"]
    assert (await _rows_full(db, "adr", aid))[0].delay_attribution == "requester"
    bad = await client.post(
        f"{API}/adr", json={"title": "T", "delay_attribution": "external"}, headers=h
    )
    assert bad.status_code == 422
    await client.post(
        f"{API}/adr/{aid}/request-signatures", json={"user_ids": [str(admin.id)]}, headers=h
    )
    resp = await client.post(
        f"{API}/adr/{aid}/recall-signatures",
        json={"delay_attribution": "governance"},
        headers=h,
    )
    assert resp.status_code == 200
    last = (await _rows_full(db, "adr", aid))[-1]
    assert (last.to_status, last.delay_attribution) == ("draft", "governance")
