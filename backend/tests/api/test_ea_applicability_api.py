"""EA governance applicability and GOV-01 / GOV-09 over the API (D-37, D-20).

Assessments need ``governance.assess_applicability`` and every field; they
append and never edit; a hidden initiative is 404. GOV-01 counts only an
approved review whose subject is the initiative; GOV-09 keeps exempt and
unknown apart and suppresses rates below five reporting initiatives.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.permissions import MEMBER_PERMISSIONS
from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.architecture_decision_card import ArchitectureDecisionCard
from app.models.card_type import CardType
from app.models.ea_review_applicability import EaReviewApplicability
from app.services.card_read_scope import CardReadScope
from app.services.executive import governance as gov
from app.services.permission_service import PermissionService
from tests.conftest import auth_headers, create_card, create_card_type, create_role, create_user

API = "/api/v1"


@pytest.fixture
async def env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    await create_role(
        db,
        key="assessor",
        label="EA Governance Office",
        permissions={**MEMBER_PERMISSIONS, "governance.assess_applicability": True},
        is_system=False,
    )
    await create_card_type(db, key="Initiative", label="Initiative")
    await create_card_type(db, key="Application", label="Application")
    admin = await create_user(db, email="admin@test.com", role="admin")
    member = await create_user(db, email="member@test.com", role="member")
    assessor = await create_user(db, email="assessor@test.com", role="assessor")
    return {"admin": admin, "member": member, "assessor": assessor}


async def _assess(client, user, card, decision="required", criteria="v1 §2", why="Core system"):
    return await client.post(
        f"{API}/cards/{card.id}/ea-applicability",
        json={"decision": decision, "criteria_reference": criteria, "justification": why},
        headers=auth_headers(user),
    )


async def test_assessment_needs_the_permission(client, db, env):
    init = await create_card(db, card_type="Initiative", name="ERP renewal")
    r = await _assess(client, env["member"], init)
    assert r.status_code == 403


async def test_assessments_append_and_the_latest_is_current(client, db, env):
    init = await create_card(db, card_type="Initiative", name="ERP renewal")
    assert (await _assess(client, env["assessor"], init)).status_code == 201
    r = await _assess(client, env["assessor"], init, decision="not_required", why="Scope cut")
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "not_required"
    assert [h["decision"] for h in body["history"]] == ["not_required", "required"]
    rows = (await db.execute(select(EaReviewApplicability))).scalars().all()
    assert len(rows) == 2


async def test_undetermined_until_assessed(client, db, env):
    init = await create_card(db, card_type="Initiative", name="Portal")
    r = await client.get(
        f"{API}/cards/{init.id}/ea-applicability", headers=auth_headers(env["member"])
    )
    assert r.status_code == 200
    assert (r.json()["status"], r.json()["current"], r.json()["can_assess"]) == (
        "undetermined",
        None,
        False,
    )


async def test_only_initiatives_are_assessed(client, db, env):
    app = await create_card(db, card_type="Application", name="CRM")
    r = await _assess(client, env["assessor"], app)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "not_an_initiative"


async def test_a_justification_is_required(client, db, env):
    init = await create_card(db, card_type="Initiative", name="Portal")
    r = await _assess(client, env["assessor"], init, why="")
    assert r.status_code == 422


async def test_a_hidden_initiative_is_404(client, db, env):
    init = await create_card(db, card_type="Initiative", name="Secret programme")
    ct = (await db.execute(select(CardType).where(CardType.key == "Initiative"))).scalar_one()
    ct.role_permissions = {"assessor": {"inventory.view": False}}
    await db.flush()
    PermissionService.invalidate_type_permission_cache()
    r = await _assess(client, env["assessor"], init)
    assert r.status_code == 404


async def test_gov01_counts_only_an_approved_review_of_the_initiative(db, env):
    reviewed = await create_card(db, card_type="Initiative", name="A")
    rejected = await create_card(db, card_type="Initiative", name="B")
    adr_only = await create_card(db, card_type="Initiative", name="C")
    exempt = await create_card(db, card_type="Initiative", name="D")
    await create_card(db, card_type="Initiative", name="E (undetermined)")
    for card, decision in (
        (reviewed, "required"),
        (rejected, "required"),
        (adr_only, "required"),
        (exempt, "not_required"),
    ):
        db.add(
            EaReviewApplicability(
                card_id=card.id, decision=decision, criteria_reference="v1", justification="x"
            )
        )
    db.add(ArbReview(title="A review", subject_card_id=reviewed.id, status="approved"))
    db.add(ArbReview(title="B review", subject_card_id=rejected.id, status="rejected"))
    adr = ArchitectureDecision(
        reference_number=f"ADR-{uuid.uuid4().hex[:6]}",
        title="Unrelated",
        status="signed",
        signed_at=datetime.now(timezone.utc),
        signatories=[],
    )
    db.add(adr)
    await db.flush()
    db.add(ArchitectureDecisionCard(architecture_decision_id=adr.id, card_id=adr_only.id))
    await db.flush()

    out = await gov.review_coverage(db, CardReadScope.everything())
    # A signed ADR linked to C and a rejected review of B never complete a review.
    assert (out["requiring_review"], out["review_completed"], out["value"]) == (3, 1, 33.3)
    assert (out["exempt"], out["undetermined"], out["population"]) == (1, 1, 5)


async def test_gov09_keeps_exempt_and_unknown_apart_and_suppresses_small_groups(db, env):
    for i in range(6):
        card = await create_card(
            db, card_type="Initiative", name=f"G{i}", attributes={"initiativeStatus": "onTrack"}
        )
        db.add(
            EaReviewApplicability(
                card_id=card.id, decision="required", criteria_reference="v1", justification="x"
            )
        )
        db.add(ArbReview(title=f"R{i}", subject_card_id=card.id, status="approved"))
    for i in range(2):
        card = await create_card(
            db, card_type="Initiative", name=f"U{i}", attributes={"initiativeStatus": "offTrack"}
        )
        db.add(
            EaReviewApplicability(
                card_id=card.id, decision="required", criteria_reference="v1", justification="x"
            )
        )
    await create_card(
        db, card_type="Initiative", name="Unknown", attributes={"initiativeStatus": "atRisk"}
    )
    await db.flush()

    out = await gov.governed_delivery(
        db, CardReadScope.everything(), datetime.now(timezone.utc).date(), {}
    )
    groups = out["groups"]
    assert groups["governed"]["on_track_pct"] == 100.0
    assert groups["ungoverned"]["suppressed"] and groups["ungoverned"]["on_track_pct"] is None
    assert groups["ungoverned"]["in_flight"] == 2
    assert groups["unknown"]["in_flight"] == 1 and groups["exempt"]["in_flight"] == 0
    assert out["comparison"]["status"] == "suppressed"
    assert out["interpretation"] == "association_not_causation"


async def test_gov01_drilldown_needs_a_review_permission(client, db, env):
    role = await create_role(
        db,
        key="exec",
        label="Exec",
        permissions={"reports.executive_dashboard": True},
        is_system=False,
    )
    user = await create_user(db, email="exec@test.com", role=role.key)
    r = await client.get(
        f"{API}/reports/executive/kpi/GOV-01/drilldown", headers=auth_headers(user)
    )
    assert r.status_code == 403


async def test_governance_page_carries_gov01_and_gov09(client, db, env):
    init = await create_card(db, card_type="Initiative", name="ERP renewal")
    await _assess(client, env["assessor"], init)
    r = await client.get(f"{API}/reports/executive/governance", headers=auth_headers(env["admin"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["activity"]["review_coverage"]["requiring_review"] == 1
    tile = body["activity"]["review_coverage_tile"]
    assert (tile["key"], tile["value"], tile["temporal"]) == ("GOV-01", 0.0, "current_state")
    assert body["impact"]["governed_delivery"]["minimum_group_size"] == 5
