"""Integration tests for Phase 2 NORA governance features ([FORK]).

* WP2.1 — architecture-state dimension on cards (create/filter/promote).
* WP2.2 — multi-step approval chain (submit → chief_architect →
  ea_governance_committee), SoD, mid-review edit invalidation.
* WP2.4 — gap-analysis report buckets + untraceable list.
"""

from __future__ import annotations

import pytest

from app.core.permissions import MEMBER_PERMISSIONS, VIEWER_PERMISSIONS
from app.models.app_settings import AppSettings
from tests.conftest import (
    auth_headers,
    create_card,
    create_card_type,
    create_relation_type,
    create_role,
    create_user,
)


async def _enable_governance(db, chain=None, sod=True):
    db.add(
        AppSettings(
            id="default",
            email_settings={},
            general_settings={
                "governanceMode": True,
                "governanceChain": chain or ["chief_architect", "ea_governance_committee"],
                "governanceSodEnabled": sod,
            },
        )
    )
    await db.flush()


@pytest.fixture
async def gov_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    await create_role(
        db,
        key="chief_architect",
        label="Chief Architect",
        permissions={**MEMBER_PERMISSIONS, "governance.approve_step": True},
    )
    await create_role(
        db,
        key="ea_governance_committee",
        label="EA Governance Committee",
        permissions={
            **VIEWER_PERMISSIONS,
            "inventory.approval_status": True,
            "governance.approve_step": True,
        },
    )
    await create_card_type(db, key="Application", label="Application")
    member = await create_user(db, email="member@test.com", role="member")
    chief = await create_user(db, email="chief@test.com", role="chief_architect")
    committee = await create_user(db, email="committee@test.com", role="ea_governance_committee")
    card = await create_card(db, card_type="Application", name="Permit System", user_id=member.id)
    await db.flush()
    return {"member": member, "chief": chief, "committee": committee, "card": card}


class TestArchitectureState:
    async def test_create_target_card_with_change_semantics(self, client, db, gov_env):
        member = gov_env["member"]
        current = gov_env["card"]
        resp = await client.post(
            "/api/v1/cards",
            json={
                "type": "Application",
                "name": "Unified Permit Platform",
                "architecture_state": "target",
                "change_type": "replace",
                "successor_id": str(current.id),
            },
            headers=auth_headers(member),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["architecture_state"] == "target"
        assert body["change_type"] == "replace"
        assert body["successor_id"] == str(current.id)

    async def test_list_filter_by_state(self, client, db, gov_env):
        member = gov_env["member"]
        await create_card(
            db,
            card_type="Application",
            name="Future App",
            architecture_state="target",
            change_type="create",
        )
        await db.flush()
        resp = await client.get(
            "/api/v1/cards?architecture_state=target", headers=auth_headers(member)
        )
        names = {c["name"] for c in resp.json()["items"]}
        assert names == {"Future App"}

    async def test_invalid_state_rejected(self, client, db, gov_env):
        resp = await client.post(
            "/api/v1/cards",
            json={"type": "Application", "name": "X", "architecture_state": "future"},
            headers=auth_headers(gov_env["member"]),
        )
        assert resp.status_code == 422

    async def test_self_successor_rejected(self, client, db, gov_env):
        card = gov_env["card"]
        resp = await client.patch(
            f"/api/v1/cards/{card.id}",
            json={"successor_id": str(card.id)},
            headers=auth_headers(gov_env["member"]),
        )
        assert resp.status_code == 400

    async def test_promotion_to_current(self, client, db, gov_env):
        target = await create_card(
            db,
            card_type="Application",
            name="Go Live App",
            architecture_state="target",
            change_type="create",
        )
        await db.flush()
        resp = await client.patch(
            f"/api/v1/cards/{target.id}",
            json={"architecture_state": "current"},
            headers=auth_headers(gov_env["member"]),
        )
        assert resp.status_code == 200
        assert resp.json()["architecture_state"] == "current"


class TestGovernanceChain:
    async def test_full_chain_happy_path(self, client, db, gov_env):
        await _enable_governance(db)
        member, chief, committee = gov_env["member"], gov_env["chief"], gov_env["committee"]
        card = gov_env["card"]

        # Working-team member submits.
        resp = await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=submit",
            headers=auth_headers(member),
        )
        assert resp.status_code == 200
        assert resp.json()["approval_status"] == "IN_REVIEW"

        # Steps exposed for the stepper UI.
        resp = await client.get(
            f"/api/v1/cards/{card.id}/approval-steps", headers=auth_headers(member)
        )
        steps = resp.json()["steps"]
        assert [s["required_role_key"] for s in steps] == [
            "chief_architect",
            "ea_governance_committee",
        ]

        # Committee cannot jump the queue (step 1 belongs to the chief).
        resp = await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=approve",
            headers=auth_headers(committee),
        )
        assert resp.status_code == 403

        # Chief approves step 1 — still in review.
        resp = await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=approve",
            headers=auth_headers(chief),
        )
        assert resp.status_code == 200
        assert resp.json()["approval_status"] == "IN_REVIEW"

        # Committee approves the final step — APPROVED.
        resp = await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=approve",
            headers=auth_headers(committee),
        )
        assert resp.status_code == 200
        assert resp.json()["approval_status"] == "APPROVED"

    async def test_member_cannot_approve_step(self, client, db, gov_env):
        await _enable_governance(db)
        card = gov_env["card"]
        await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=submit",
            headers=auth_headers(gov_env["member"]),
        )
        resp = await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=approve",
            headers=auth_headers(gov_env["member"]),
        )
        assert resp.status_code == 403

    async def test_sod_blocks_submitter(self, client, db, gov_env):
        """The chief submits — SoD forbids them deciding their own submission."""
        await _enable_governance(db, sod=True)
        chief = gov_env["chief"]
        card = gov_env["card"]
        await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=submit",
            headers=auth_headers(chief),
        )
        resp = await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=approve",
            headers=auth_headers(chief),
        )
        assert resp.status_code == 403
        assert "Segregation" in resp.json()["detail"]

    async def test_reject_ends_round(self, client, db, gov_env):
        await _enable_governance(db)
        card = gov_env["card"]
        await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=submit",
            headers=auth_headers(gov_env["member"]),
        )
        resp = await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=reject&comment=Missing+BRM+link",
            headers=auth_headers(gov_env["chief"]),
        )
        assert resp.status_code == 200
        assert resp.json()["approval_status"] == "REJECTED"

    async def test_edit_mid_review_invalidates_round(self, client, db, gov_env):
        await _enable_governance(db)
        card = gov_env["card"]
        await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=submit",
            headers=auth_headers(gov_env["member"]),
        )
        resp = await client.patch(
            f"/api/v1/cards/{card.id}",
            json={"description": "changed mid-review"},
            headers=auth_headers(gov_env["member"]),
        )
        assert resp.status_code == 200
        assert resp.json()["approval_status"] == "DRAFT"
        steps = (
            await client.get(
                f"/api/v1/cards/{card.id}/approval-steps", headers=auth_headers(gov_env["member"])
            )
        ).json()["steps"]
        assert steps == []

    async def test_submit_without_governance_mode_rejected(self, client, db, gov_env):
        resp = await client.post(
            f"/api/v1/cards/{gov_env['card'].id}/approval-status?action=submit",
            headers=auth_headers(gov_env["member"]),
        )
        assert resp.status_code == 400

    async def test_legacy_flow_unchanged_when_disabled(self, client, db, gov_env):
        resp = await client.post(
            f"/api/v1/cards/{gov_env['card'].id}/approval-status?action=approve",
            headers=auth_headers(gov_env["member"]),
        )
        assert resp.status_code == 200
        assert resp.json()["approval_status"] == "APPROVED"


class TestGapAnalysisReport:
    async def test_buckets_and_untraceable(self, client, db, gov_env):
        member = gov_env["member"]
        current = gov_env["card"]
        await create_card_type(db, key="Initiative", label="Initiative")
        await create_relation_type(
            db,
            key="relInitiativeToApp",
            label="delivers",
            source_type_key="Initiative",
            target_type_key="Application",
        )
        initiative = await create_card(db, card_type="Initiative", name="Modernization 1446H")
        replacement = await create_card(
            db,
            card_type="Application",
            name="Unified Platform",
            architecture_state="target",
            change_type="replace",
            successor_id=current.id,
        )
        await create_card(
            db,
            card_type="Application",
            name="Brand New Service",
            architecture_state="target",
            change_type="create",
        )
        from tests.conftest import create_relation

        await create_relation(
            db,
            type_key="relInitiativeToApp",
            source_id=initiative.id,
            target_id=replacement.id,
            attributes={"transitionRole": "introduces"},
        )
        await db.flush()

        resp = await client.get("/api/v1/reports/gap-analysis", headers=auth_headers(member))
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["replace"] == 1
        assert data["summary"]["create"] == 1
        replace_row = data["buckets"]["replace"][0]
        assert replace_row["replaces"]["name"] == "Permit System"
        assert replace_row["initiatives"][0]["name"] == "Modernization 1446H"
        assert replace_row["initiatives"][0]["transition_role"] == "introduces"
        # The brand-new card has no initiative → untraceable.
        assert [r["name"] for r in data["untraceable"]] == ["Brand New Service"]
