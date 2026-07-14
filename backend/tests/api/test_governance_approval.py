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


class TestPerTypeApprovalChains:
    """Tests for per-type approval chain resolution (Phase A.3)."""

    async def test_type_specific_chain_overrides_global(self, client, db, gov_env):
        """When a type has a custom chain, it should be used instead of the global chain."""
        await create_card_type(db, key="Initiative", label="Initiative")
        await db.flush()

        # Enable governance with global chain
        await _enable_governance(
            db,
            chain=["chief_architect", "ea_governance_committee"],
        )

        # Set a type-specific chain for Initiative
        settings = AppSettings(
            id="default",
            email_settings={},
            general_settings={
                "governanceMode": True,
                "governanceChain": ["chief_architect", "ea_governance_committee"],
                "governanceSodEnabled": True,
                "typeGovernanceChains": {
                    "Initiative": ["ea_governance_committee"]  # Shorter chain for initiatives
                },
            },
        )
        await db.merge(settings)
        await db.flush()

        member = gov_env["member"]
        initiative = await create_card(
            db, card_type="Initiative", name="Test Initiative", user_id=member.id
        )
        await db.flush()

        # Submit for review
        resp = await client.post(
            f"/api/v1/cards/{initiative.id}/approval-status?action=submit",
            headers=auth_headers(member),
        )
        assert resp.status_code == 200

        # Fetch approval steps — should have only 1 step (ea_governance_committee)
        steps_resp = await client.get(
            f"/api/v1/cards/{initiative.id}/approval-steps",
            headers=auth_headers(member),
        )
        steps = steps_resp.json()["steps"]
        assert len(steps) == 1
        assert steps[0]["required_role_key"] == "ea_governance_committee"

    async def test_default_chain_used_when_type_not_customized(self, client, db, gov_env):
        """When a type has no custom chain, the global chain should be used."""
        from sqlalchemy import text

        await db.execute(
            text(
                "UPDATE app_settings SET general_settings = "
                "jsonb_set(general_settings, '{typeGovernanceChains}', '{}'::jsonb) "
                "WHERE id = 'default'"
            )
        )
        await _enable_governance(
            db,
            chain=["chief_architect", "ea_governance_committee"],
        )

        member = gov_env["member"]
        card = gov_env["card"]  # Application type with no custom chain
        await db.flush()

        # Submit for review
        resp = await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=submit",
            headers=auth_headers(member),
        )
        assert resp.status_code == 200

        # Fetch approval steps — should use global chain
        steps_resp = await client.get(
            f"/api/v1/cards/{card.id}/approval-steps",
            headers=auth_headers(member),
        )
        steps = steps_resp.json()["steps"]
        assert len(steps) == 2
        assert steps[0]["required_role_key"] == "chief_architect"
        assert steps[1]["required_role_key"] == "ea_governance_committee"

    async def test_type_specific_chain_endpoint_validation(self, client, db, gov_env):
        """Endpoint should accept and persist per-type chains."""
        member = gov_env["member"]
        member.role = "admin"
        await db.flush()

        # Update governance settings with a per-type chain
        resp = await client.patch(
            "/api/v1/settings/governance",
            json={
                "governance_mode": True,
                "chain": ["chief_architect"],
                "sod_enabled": False,
                "type_chains": {
                    "Application": ["ea_governance_committee"],
                },
            },
            headers=auth_headers(member),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["type_chains"]["Application"] == ["ea_governance_committee"]

        # Verify settings persisted
        get_resp = await client.get("/api/v1/settings/governance", headers=auth_headers(member))
        assert get_resp.json()["type_chains"]["Application"] == ["ea_governance_committee"]

    async def test_empty_type_chain_ignored(self, client, db, gov_env):
        """A type chain with empty roles should fall back to global chain."""
        await _enable_governance(
            db,
            chain=["chief_architect", "ea_governance_committee"],
        )

        # Set type-specific chain that's empty
        settings = AppSettings(
            id="default",
            email_settings={},
            general_settings={
                "governanceMode": True,
                "governanceChain": ["chief_architect", "ea_governance_committee"],
                "governanceSodEnabled": True,
                "typeGovernanceChains": {
                    "Application": []  # Empty chain — should fall back to global
                },
            },
        )
        await db.merge(settings)
        await db.flush()

        member = gov_env["member"]
        card = gov_env["card"]

        # Submit for review
        resp = await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=submit",
            headers=auth_headers(member),
        )
        assert resp.status_code == 200

        # Fetch approval steps — should use global chain (fallback)
        steps_resp = await client.get(
            f"/api/v1/cards/{card.id}/approval-steps",
            headers=auth_headers(member),
        )
        steps = steps_resp.json()["steps"]
        assert len(steps) == 2
        assert steps[0]["required_role_key"] == "chief_architect"
        assert steps[1]["required_role_key"] == "ea_governance_committee"


class TestApprovalEmailNotifications:
    """Tests for email notifications on approval step pending (Phase A.4)."""

    async def test_email_sent_when_user_opted_in(self, client, db, gov_env, monkeypatch):
        """Email notification should be sent if user has approval_step_pending enabled."""
        await _enable_governance(db)

        # Enable approval step pending email for chief
        chief = gov_env["chief"]
        chief.notification_preferences = {
            "in_app": {"approval_step_pending": True},
            "email": {"approval_step_pending": True},  # Opted in
        }
        await db.flush()

        # Mock send_notification_email to track if it was called
        email_calls = []

        async def mock_send_email(to: str, title: str, message: str, link: str | None = None):
            email_calls.append({"to": to, "title": title, "message": message, "link": link})
            return True

        monkeypatch.setattr(
            "app.services.governance_service.send_notification_email",
            mock_send_email,
        )

        member = gov_env["member"]
        card = gov_env["card"]

        # Submit for review — this triggers notify_role_members for chief_architect role
        await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=submit",
            headers=auth_headers(member),
        )

        # Verify email was sent to chief
        assert len(email_calls) == 1
        assert email_calls[0]["to"] == chief.email
        assert "Review Needed" in email_calls[0]["title"]
        assert card.name in email_calls[0]["message"]
        assert f"/cards/{card.id}" in email_calls[0]["link"]

    async def test_email_not_sent_when_user_opted_out(self, client, db, gov_env, monkeypatch):
        """Email notification should not be sent if user has approval_step_pending disabled."""
        await _enable_governance(db)

        # Disable approval step pending email for chief
        chief = gov_env["chief"]
        chief.notification_preferences = {
            "in_app": {"approval_step_pending": True},
            "email": {"approval_step_pending": False},  # Opted out
        }
        await db.flush()

        # Mock send_notification_email to track if it was called
        email_calls = []

        async def mock_send_email(to: str, title: str, message: str, link: str | None = None):
            email_calls.append({"to": to, "title": title, "message": message, "link": link})
            return True

        monkeypatch.setattr(
            "app.services.governance_service.send_notification_email",
            mock_send_email,
        )

        member = gov_env["member"]
        card = gov_env["card"]

        # Submit for review
        await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=submit",
            headers=auth_headers(member),
        )

        # Verify no email was sent
        assert len(email_calls) == 0

    async def test_in_app_notification_always_sent(self, client, db, gov_env):
        """In-app notifications should always be sent regardless of email preference."""
        await _enable_governance(db)

        # Disable approval step pending email
        chief = gov_env["chief"]
        chief.notification_preferences = {
            "in_app": {"approval_step_pending": True},
            "email": {"approval_step_pending": False},  # Email disabled
        }
        await db.flush()

        member = gov_env["member"]
        card = gov_env["card"]

        # Submit for review
        await client.post(
            f"/api/v1/cards/{card.id}/approval-status?action=submit",
            headers=auth_headers(member),
        )

        # Fetch notifications for chief — in-app notification should exist
        notif_resp = await client.get("/api/v1/notifications", headers=auth_headers(chief))
        assert notif_resp.status_code == 200
        notifications = notif_resp.json()["items"]
        assert any(n["type"] == "approval_step_pending" for n in notifications)


class TestTargetPromotionGovernance:
    """Tests for coupled target promotion to governance approval (Phase A.5)."""

    async def test_promote_target_requires_approval_when_enabled(self, client, db, gov_env):
        """When promotion_requires_approval is ON, target promotion enters approval workflow."""
        # Enable governance with promotion approval required
        await _enable_governance(db)
        settings = AppSettings(
            id="default",
            email_settings={},
            general_settings={
                "governanceMode": True,
                "governanceChain": ["chief_architect", "ea_governance_committee"],
                "governanceSodEnabled": True,
                "promotionRequiresApproval": True,
            },
        )
        await db.merge(settings)
        await db.flush()

        member = gov_env["member"]
        # Create a target card
        target = await create_card(
            db,
            card_type="Application",
            name="Future App",
            user_id=member.id,
            architecture_state="target",
        )
        await db.flush()

        # Promote the target card
        resp = await client.post(
            f"/api/v1/cards/{target.id}/promote-target",
            headers=auth_headers(member),
        )
        assert resp.status_code == 200
        body = resp.json()
        # Should be in transition state and under review
        assert body["architecture_state"] == "transition"
        assert body["approval_status"] == "IN_REVIEW"

        # Verify approval steps were created
        steps_resp = await client.get(
            f"/api/v1/cards/{target.id}/approval-steps",
            headers=auth_headers(member),
        )
        steps = steps_resp.json()["steps"]
        assert len(steps) == 2
        assert steps[0]["required_role_key"] == "chief_architect"

    async def test_promote_target_immediate_when_disabled(self, client, db, gov_env):
        """When promotion_requires_approval is OFF, target promotion is immediate."""
        # Enable governance but disable promotion approval
        await _enable_governance(db)
        settings = AppSettings(
            id="default",
            email_settings={},
            general_settings={
                "governanceMode": True,
                "governanceChain": ["chief_architect", "ea_governance_committee"],
                "governanceSodEnabled": True,
                "promotionRequiresApproval": False,  # Disabled
            },
        )
        await db.merge(settings)
        await db.flush()

        member = gov_env["member"]
        # Create a target card
        target = await create_card(
            db,
            card_type="Application",
            name="Future App",
            user_id=member.id,
            architecture_state="target",
        )
        await db.flush()

        # Promote the target card
        resp = await client.post(
            f"/api/v1/cards/{target.id}/promote-target",
            headers=auth_headers(member),
        )
        assert resp.status_code == 200
        body = resp.json()
        # Should be immediately promoted to current
        assert body["architecture_state"] == "current"
        assert body["approval_status"] == "APPROVED"

        # Verify no approval steps were created
        steps_resp = await client.get(
            f"/api/v1/cards/{target.id}/approval-steps",
            headers=auth_headers(member),
        )
        steps = steps_resp.json()["steps"]
        assert len(steps) == 0

    async def test_promote_non_target_card_fails(self, client, db, gov_env):
        """Cannot promote a card that is not in target state."""
        member = gov_env["member"]
        # Use the existing current-state card
        card = gov_env["card"]

        resp = await client.post(
            f"/api/v1/cards/{card.id}/promote-target",
            headers=auth_headers(member),
        )
        assert resp.status_code == 400
        assert "target" in resp.json()["detail"]

    async def test_promote_target_governance_mode_off(self, client, db, gov_env):
        """When governance is OFF, promotion is always immediate."""
        # Governance off
        member = gov_env["member"]
        target = await create_card(
            db,
            card_type="Application",
            name="Future App",
            user_id=member.id,
            architecture_state="target",
        )
        await db.flush()

        resp = await client.post(
            f"/api/v1/cards/{target.id}/promote-target",
            headers=auth_headers(member),
        )
        assert resp.status_code == 200
        body = resp.json()
        # Governance off → immediate promotion
        assert body["architecture_state"] == "current"
        assert body["approval_status"] == "APPROVED"
