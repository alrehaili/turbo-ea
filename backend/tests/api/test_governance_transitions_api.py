"""Governance transition history over the API (D-35, D-34; Batch 3.2).

Each status change of an ARB review, a standard exception and an ADR leaves one
row, readable under the instrument's own view permission; a record about a
hidden card is 404; a record decided before the history existed reads
``recorded: false`` instead of a reconstructed past.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.core.permissions import MEMBER_PERMISSIONS
from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.card_type import CardType
from app.models.document import Document
from app.models.file_attachment import FileAttachment
from app.models.governance_transition import GovernanceTransition
from app.models.tech_standard import StandardException, TechStandard
from app.services.permission_service import PermissionService
from tests.conftest import (
    auth_headers,
    create_card,
    create_card_type,
    create_relation,
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


async def _document(db, card_id, name="Cutover report"):
    doc = Document(card_id=card_id, name=name, url="https://evidence.example/cutover")
    db.add(doc)
    await db.flush()
    return doc


async def _file(db, card_id, name="config-export.json", data=b'{"mq": false}'):
    f = FileAttachment(
        card_id=card_id, name=name, mime_type="application/json", size=len(data), data=data
    )
    db.add(f)
    await db.flush()
    return f


ATTEST = {
    "examined": "The production config export attached to the card",
    "demonstrates": "It lists no MQ endpoint, so nothing uses the standard",
    "confirmed": True,
}


async def test_remediation_needs_an_independent_verifier(client, db, lifecycle):
    eid = await _approved(client, lifecycle)
    base = f"{API}/tech-standards/exceptions/{eid}"
    member = auth_headers(lifecycle["member"])
    doc = await _document(db, lifecycle["app"].id)
    f = await _file(db, lifecycle["app"].id)
    resp = await client.post(
        f"{base}/remediation",
        json={
            "evidence": "Moved to REST",
            "evidence_refs": [
                {"kind": "document", "id": str(doc.id)},
                {"kind": "attachment", "id": str(f.id)},
            ],
        },
        headers=member,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "remediation_submitted"
    assert body["remediation_evidence"] == "Moved to REST"
    refs = body["remediation_evidence_refs"]
    assert [(r["kind"], r["id"], r["name"], r["fingerprint_of"]) for r in refs] == [
        ("document", str(doc.id), "Cutover report", "link"),
        ("attachment", str(f.id), "config-export.json", "content"),
    ]
    assert refs[1]["size"] == f.size and len(refs[1]["sha256"]) == 64
    assert body["remediation_submitted_by"] == str(lifecycle["member"].id)

    # The standard governs no category, so the scan cannot check the pair: the
    # cited evidence is unchanged, includes a file, and the verifier attests
    # (I-32, I-36).
    verify = {"outcome": "verified", "attestation": ATTEST}
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
    assert resp.json()["remediation_verification_basis"] == "attested"
    att = resp.json()["remediation_attestation"]
    assert att["examined"] == ATTEST["examined"] and att["confirmed"] is True
    assert [r["id"] for r in att["evidence"]] == [str(doc.id), str(f.id)]
    assert (await _rows(db, "exception", eid))[-2:] == [
        ("approved", "remediation_submitted"),
        ("remediation_submitted", "remediated"),
    ]


async def _submitted(client, lifecycle, refs):
    eid = await _approved(client, lifecycle)
    base = f"{API}/tech-standards/exceptions/{eid}"
    resp = await client.post(
        f"{base}/remediation",
        json={"evidence": "e", "evidence_refs": refs},
        headers=auth_headers(lifecycle["member"]),
    )
    assert resp.status_code == 200
    return eid, base


async def test_an_unassessable_verification_needs_intact_file_evidence(client, db, lifecycle):
    """I-32 / I-36: the existence of a document is not proof. Without cited
    evidence, with only a link, or with a file changed since submission, the
    verification is refused, whatever the verifier writes."""
    verifier = auth_headers(lifecycle["member2"])
    verify = {"outcome": "verified", "attestation": ATTEST}

    eid, base = await _submitted(client, lifecycle, [])
    resp = await client.post(f"{base}/remediation/verify", json=verify, headers=verifier)
    assert resp.json()["detail"]["code"] == "verifiable_evidence_required"

    doc = await _document(db, lifecycle["app"].id)
    eid, base = await _submitted(client, lifecycle, [{"kind": "document", "id": str(doc.id)}])
    resp = await client.post(f"{base}/remediation/verify", json=verify, headers=verifier)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "evidence_integrity_unavailable"

    f = await _file(db, lifecycle["app"].id)
    eid, base = await _submitted(client, lifecycle, [{"kind": "attachment", "id": str(f.id)}])
    f.data = b'{"mq": true}'  # replaced after submission, same size
    await db.flush()
    resp = await client.post(f"{base}/remediation/verify", json=verify, headers=verifier)
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "evidence_changed"
    assert (await _rows(db, "exception", eid))[-1] == ("approved", "remediation_submitted")


async def test_an_unassessable_verification_needs_the_verifier_s_attestation(client, db, lifecycle):
    f = await _file(db, lifecycle["app"].id)
    eid, base = await _submitted(client, lifecycle, [{"kind": "attachment", "id": str(f.id)}])
    verifier = auth_headers(lifecycle["member2"])
    for body in (
        {"outcome": "verified"},
        {"outcome": "verified", "note": "Looks fine"},
        {"outcome": "verified", "attestation": {**ATTEST, "confirmed": False}},
    ):
        resp = await client.post(f"{base}/remediation/verify", json=body, headers=verifier)
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "attestation_required"
    # Older evidence is never refused for predating the approval.
    resp = await client.post(
        f"{base}/remediation/verify",
        json={"outcome": "verified", "attestation": ATTEST},
        headers=verifier,
    )
    assert resp.status_code == 200


async def test_changing_an_approved_expiry_is_recorded_with_a_reason(client, db, lifecycle):
    """Decision B / I-35: the previous and new expiry, actor, time and reason."""
    eid = await _approved(client, lifecycle)
    path = f"{API}/tech-standards/exceptions/{eid}"
    admin = auth_headers(lifecycle["admin"])
    resp = await client.patch(path, json={"expiry_date": "2027-06-30"}, headers=admin)
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "expiry_reason_required"
    resp = await client.patch(
        path, json={"expiry_date": "2027-06-30", "expiry_reason": "Vendor delay"}, headers=admin
    )
    assert resp.status_code == 200
    assert resp.json()["expiry_date"] == "2027-06-30"
    resp = await client.patch(
        path, json={"expiry_date": "2027-09-30", "expiry_reason": "Second slip"}, headers=admin
    )
    history = (await client.get(f"{path}/transitions", headers=admin)).json()["transitions"]
    events = [t for t in history if t["event_kind"] == "expiry_changed"]
    assert [(t["previous_expiry_date"], t["expiry_date"], t["reason"]) for t in events] == [
        (None, "2027-06-30", "Vendor delay"),
        ("2027-06-30", "2027-09-30", "Second slip"),
    ]
    assert all(t["actor"]["id"] == str(lifecycle["admin"].id) for t in events)
    assert all(t["from_status"] == t["to_status"] == "approved" for t in events)
    # A plain field edit records nothing.
    before = len(await _rows(db, "exception", eid))
    await client.patch(path, json={"justification": "x"}, headers=admin)
    assert len(await _rows(db, "exception", eid)) == before


async def test_evidence_must_be_on_the_exceptions_own_card(client, db, lifecycle):
    eid = await _approved(client, lifecycle)
    elsewhere = await _document(db, lifecycle["secret"].id)
    member = auth_headers(lifecycle["member"])
    for ref in (
        {"kind": "document", "id": str(elsewhere.id)},
        {"kind": "attachment", "id": str(elsewhere.id)},
        {"kind": "document", "id": str(uuid.uuid4())},
    ):
        resp = await client.post(
            f"{API}/tech-standards/exceptions/{eid}/remediation",
            json={"evidence": "e", "evidence_refs": [ref]},
            headers=member,
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "invalid_evidence_ref"
    resp = await client.post(
        f"{API}/tech-standards/exceptions/{eid}/remediation",
        json={"evidence": "e", "evidence_refs": [{"kind": "ticket", "id": str(uuid.uuid4())}]},
        headers=member,
    )
    assert resp.status_code == 422  # unknown kind refused by the schema
    assert (await _rows(db, "exception", eid))[-1] == ("requested", "approved")


async def _governed_exception(db, lifecycle):
    """An approved exception for an app that uses a prohibited standard's category
    through an IT Component; returns its id and the app-to-component relation."""
    await create_card_type(db, key="ITComponent", label="IT Component")
    await create_card_type(db, key="TechCategory", label="Tech Category")
    admin = lifecycle["admin"]
    cat = await create_card(db, card_type="TechCategory", name="Messaging", user_id=admin.id)
    itc = await create_card(db, card_type="ITComponent", name="OldMQ", user_id=admin.id)
    await create_relation(db, type_key="relITCToTechCat", source_id=itc.id, target_id=cat.id)
    uses = await create_relation(
        db, type_key="relAppToITC", source_id=lifecycle["app"].id, target_id=itc.id
    )
    std = TechStandard(name="Legacy MQ", status="prohibited", tech_category_id=cat.id)
    db.add(std)
    await db.flush()
    exc = StandardException(
        standard_id=std.id, card_id=lifecycle["app"].id, status="approved", created_by=admin.id
    )
    db.add(exc)
    await db.flush()
    return str(exc.id), uses


async def test_verification_needs_the_violation_to_be_gone(client, db, lifecycle):
    """I-32: submitted evidence is not remediation; the standards check must agree."""
    eid, uses = await _governed_exception(db, lifecycle)
    base = f"{API}/tech-standards/exceptions/{eid}"
    await client.post(
        f"{base}/remediation",
        json={"evidence": "Moved to Kafka"},
        headers=auth_headers(lifecycle["member"]),
    )
    verifier = auth_headers(lifecycle["member2"])
    verify = {"outcome": "verified", "note": "Looks done"}
    resp = await client.post(f"{base}/remediation/verify", json=verify, headers=verifier)
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "violation_persists"
    assert (await _rows(db, "exception", eid)) == [("approved", "remediation_submitted")]

    await db.delete(uses)
    await db.flush()
    resp = await client.post(
        f"{base}/remediation/verify", json={"outcome": "verified"}, headers=verifier
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "remediated"
    assert resp.json()["remediation_verification_basis"] == "rule_check"


async def test_an_approval_records_its_expiry_on_the_transition(client, db, lifecycle):
    h = auth_headers(lifecycle["admin"])
    sid = (
        await client.post(
            f"{API}/tech-standards", json={"name": "Old", "status": "sunset"}, headers=h
        )
    ).json()["id"]
    eid = (
        await client.post(
            f"{API}/tech-standards/{sid}/exceptions",
            json={"card_id": str(lifecycle["app"].id), "expiry_date": "2026-12-31"},
            headers=h,
        )
    ).json()["id"]
    await client.post(f"{API}/tech-standards/exceptions/{eid}/decision?action=approve", headers=h)
    # A later edit of the expiry does not touch the recorded approval (I-31).
    await client.patch(
        f"{API}/tech-standards/exceptions/{eid}", json={"expiry_date": "2027-06-30"}, headers=h
    )
    res = await db.execute(
        select(GovernanceTransition.approved_expiry_date).where(
            GovernanceTransition.record_id == uuid.UUID(eid),
            GovernanceTransition.to_status == "approved",
        )
    )
    assert [d.isoformat() for (d,) in res.all()] == ["2026-12-31"]


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


async def test_an_expired_or_awaiting_verification_exception_can_be_withdrawn(
    client, db, lifecycle
):
    """I-30: withdrawal is open until a terminal state, past expiry too, and is
    never a verification."""
    std = TechStandard(name="Old FTP", status="prohibited")
    db.add(std)
    await db.flush()
    expired = StandardException(
        standard_id=std.id,
        card_id=lifecycle["app"].id,
        status="approved",
        expiry_date=date(2020, 1, 31),
        created_by=lifecycle["requester"].id,
    )
    pending = StandardException(
        standard_id=std.id,
        card_id=lifecycle["app"].id,
        status="remediation_submitted",
        created_by=lifecycle["requester"].id,
        remediation_evidence="e",
        remediation_submitted_by=lifecycle["member"].id,
    )
    db.add_all([expired, pending])
    await db.flush()
    for exc in (expired, pending):
        resp = await client.post(
            f"{API}/tech-standards/exceptions/{exc.id}/withdraw",
            json={"reason": "No longer needed"},
            headers=auth_headers(lifecycle["requester"]),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "withdrawn"
        assert body["remediation_verified_by"] is None
        assert body["remediation_verification_basis"] is None
        assert body["expiry_date"] in (None, "2020-01-31")


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


async def test_deleting_an_exception_rewrites_no_history(client, db, lifecycle):
    """I-33 (approved with changes): the history is immutable — earlier rows
    keep what they recorded, a final row is appended, and the deletion reason
    is held in the audit record only."""
    eid = await _approved(client, lifecycle)
    path = f"{API}/tech-standards/exceptions/{eid}"
    await client.post(
        f"{path}/remediation",
        json={"evidence": "Restricted detail about Billing"},
        headers=auth_headers(lifecycle["member"]),
    )
    resp = await client.delete(
        f"{path}?reason=Wrong%20card%20Billing", headers=auth_headers(lifecycle["admin"])
    )
    assert resp.status_code == 204
    rows = await _rows_full(db, "exception", eid)
    assert [(t.to_status, t.reason) for t in rows][-2:] == [
        ("remediation_submitted", "Restricted detail about Billing"),
        ("deleted", None),
    ]
    assert (await _audit(db))[0].details["context"]["deletion_reason"] == "Wrong card Billing"


async def test_ordinary_readers_see_the_moves_but_not_the_lifecycle_text(client, db, lifecycle):
    """I-33: the requester and the people who act on exceptions read the
    evidence and reasons; a viewer sees that they exist, not what they say."""
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
    resp = await client.post(
        f"{API}/tech-standards/exceptions/{exc.id}/withdraw",
        json={"reason": "Confidential vendor dispute"},
        headers=auth_headers(lifecycle["requester"]),
    )
    assert resp.status_code == 200
    history = f"{API}/tech-standards/exceptions/{exc.id}/transitions"

    viewer = await client.get(history, headers=auth_headers(lifecycle["stranger"]))
    assert viewer.status_code == 200
    (row,) = viewer.json()["transitions"]
    assert (row["to_status"], row["reason"], row["reason_withheld"]) == ("withdrawn", None, True)
    assert "Confidential vendor dispute" not in viewer.text
    listed = await client.get(
        f"{API}/tech-standards/exceptions", headers=auth_headers(lifecycle["stranger"])
    )
    mine = next(e for e in listed.json() if e["id"] == str(exc.id))
    assert mine["withdrawal_reason"] is None and mine["lifecycle_text_withheld"] is True

    for who in ("requester", "member"):
        resp = await client.get(history, headers=auth_headers(lifecycle[who]))
        (row,) = resp.json()["transitions"]
        assert (row["reason"], row["reason_withheld"]) == ("Confidential vendor dispute", False)


async def test_a_standard_with_decided_exceptions_cannot_be_deleted(client, lifecycle):
    eid = await _approved(client, lifecycle)
    admin = auth_headers(lifecycle["admin"])
    sid = (await client.get(f"{API}/tech-standards/exceptions", headers=admin)).json()
    sid = next(e["standard_id"] for e in sid if e["id"] == eid)
    resp = await client.delete(f"{API}/tech-standards/{sid}", headers=admin)
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "exceptions_have_lifecycle"


async def test_arb_delay_reason_text_is_for_managers_creator_and_reviewer(client, db, env):
    """Decision D / I-37: other arb.view readers see the attribution, the time
    and that a reason exists, never the text."""
    await create_role(
        db,
        key="arbview",
        label="ARB viewer",
        permissions={"arb.view": True, "inventory.view": True},
        is_system=False,
    )
    viewer = await create_user(db, email="arbviewer@test.com", role="arbview")
    r = ArbReview(title="R", status="deferred", subject_card_id=env["app"].id)
    db.add(r)
    await db.flush()
    db.add(
        GovernanceTransition(
            instrument="arb",
            record_id=r.id,
            from_status="scheduled",
            to_status="deferred",
            delay_attribution="external",
            reason="Vendor contract renegotiation",
        )
    )
    await db.flush()
    path = f"{API}/arb/{r.id}/transitions"
    resp = await client.get(path, headers=auth_headers(viewer))
    assert resp.status_code == 200
    (row,) = resp.json()["transitions"]
    assert (row["delay_attribution"], row["reason"], row["reason_withheld"]) == (
        "external",
        None,
        True,
    )
    assert row["occurred_at"] is not None
    assert "renegotiation" not in resp.text
    (row,) = (await client.get(path, headers=auth_headers(env["member"]))).json()["transitions"]
    assert row["reason"] == "Vendor contract renegotiation"  # arb.manage
    r.reviewer_id = viewer.id
    await db.flush()
    (row,) = (await client.get(path, headers=auth_headers(viewer))).json()["transitions"]
    assert row["reason"] == "Vendor contract renegotiation"  # the assigned reviewer


async def test_adr_delay_reason_text_is_for_managers_creator_and_signatories(client, db, env):
    await create_role(
        db, key="adrview", label="ADR viewer", permissions={"adr.view": True}, is_system=False
    )
    viewer = await create_user(db, email="adrviewer@test.com", role="adrview")
    adr = ArchitectureDecision(reference_number="ADR-77", title="Delayed", status="draft")
    db.add(adr)
    await db.flush()
    db.add(
        GovernanceTransition(
            instrument="adr",
            record_id=adr.id,
            from_status=None,
            to_status="draft",
            delay_attribution="requester",
            reason="Budget hold on the programme",
        )
    )
    await db.flush()
    path = f"{API}/adr/{adr.id}/transitions"
    (row,) = (await client.get(path, headers=auth_headers(viewer))).json()["transitions"]
    assert (row["delay_attribution"], row["reason"], row["reason_withheld"]) == (
        "requester",
        None,
        True,
    )
    adr.signatories = [{"user_id": str(viewer.id), "status": "pending"}]
    await db.flush()
    (row,) = (await client.get(path, headers=auth_headers(viewer))).json()["transitions"]
    assert row["reason"] == "Budget hold on the programme"


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
