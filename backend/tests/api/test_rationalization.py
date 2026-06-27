"""Integration tests for the /rationalization endpoints.

Application Rationalization Campaigns — TIME-framework portfolio decisions.

[FORK FEATURE]
"""

from __future__ import annotations

import pytest

from app.core.permissions import MEMBER_PERMISSIONS, VIEWER_PERMISSIONS
from tests.conftest import (
    auth_headers,
    create_card,
    create_card_type,
    create_role,
    create_user,
)


@pytest.fixture
async def rat_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    await create_role(db, key="viewer", label="Viewer", permissions=VIEWER_PERMISSIONS)
    await create_card_type(db, key="Application", label="Application")
    admin = await create_user(db, email="admin@test.com", role="admin")
    member = await create_user(db, email="member@test.com", role="member")
    viewer = await create_user(db, email="viewer@test.com", role="viewer")
    app = await create_card(db, card_type="Application", name="Legacy CRM", user_id=admin.id)
    successor = await create_card(db, card_type="Application", name="New CRM", user_id=admin.id)
    await db.flush()
    return {
        "admin": admin,
        "member": member,
        "viewer": viewer,
        "app": app,
        "successor": successor,
    }


async def _create_campaign(client, user, **kwargs):
    payload = {"name": "Q3 Rationalization", **kwargs}
    resp = await client.post(
        "/api/v1/rationalization/campaigns", json=payload, headers=auth_headers(user)
    )
    return resp


class TestCampaignCrud:
    async def test_create_and_get_campaign(self, client, db, rat_env):
        admin = rat_env["admin"]
        resp = await _create_campaign(client, admin, target_savings=500000)
        assert resp.status_code == 201
        cid = resp.json()["id"]

        resp = await client.get(
            f"/api/v1/rationalization/campaigns/{cid}", headers=auth_headers(admin)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Q3 Rationalization"
        assert data["summary"]["target_savings"] == 500000
        assert data["decisions"] == []

    async def test_list_campaigns_rollup(self, client, db, rat_env):
        admin = rat_env["admin"]
        cid = (await _create_campaign(client, admin)).json()["id"]
        await client.post(
            f"/api/v1/rationalization/campaigns/{cid}/decisions",
            json={
                "card_id": str(rat_env["app"].id),
                "time_decision": "eliminate",
                "planned_savings": 120000,
            },
            headers=auth_headers(admin),
        )
        resp = await client.get("/api/v1/rationalization/campaigns", headers=auth_headers(admin))
        assert resp.status_code == 200
        row = next(c for c in resp.json() if c["id"] == cid)
        assert row["decision_count"] == 1
        assert row["planned_savings_total"] == 120000

    async def test_viewer_cannot_create(self, client, db, rat_env):
        resp = await _create_campaign(client, rat_env["viewer"])
        assert resp.status_code == 403

    async def test_viewer_can_view(self, client, db, rat_env):
        cid = (await _create_campaign(client, rat_env["admin"])).json()["id"]
        resp = await client.get(
            f"/api/v1/rationalization/campaigns/{cid}", headers=auth_headers(rat_env["viewer"])
        )
        assert resp.status_code == 200

    async def test_invalid_status_rejected(self, client, db, rat_env):
        resp = await _create_campaign(client, rat_env["admin"], status="bogus")
        assert resp.status_code == 400


class TestDecisions:
    async def test_decision_lifecycle_and_summary(self, client, db, rat_env):
        admin = rat_env["admin"]
        cid = (await _create_campaign(client, admin)).json()["id"]

        resp = await client.post(
            f"/api/v1/rationalization/campaigns/{cid}/decisions",
            json={
                "card_id": str(rat_env["app"].id),
                "time_decision": "migrate",
                "successor_id": str(rat_env["successor"].id),
                "annual_cost": 90000,
                "planned_savings": 60000,
                "progress": 25,
            },
            headers=auth_headers(admin),
        )
        assert resp.status_code == 201
        decision = resp.json()
        assert decision["card"]["name"] == "Legacy CRM"
        assert decision["successor"]["name"] == "New CRM"
        did = decision["id"]

        # Update the decision.
        resp = await client.patch(
            f"/api/v1/rationalization/decisions/{did}",
            json={"time_decision": "eliminate", "progress": 100},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["time_decision"] == "eliminate"

        # Campaign summary reflects the decision mix.
        resp = await client.get(
            f"/api/v1/rationalization/campaigns/{cid}", headers=auth_headers(admin)
        )
        summary = resp.json()["summary"]
        assert summary["decision_count"] == 1
        assert summary["by_decision"]["eliminate"] == 1
        assert summary["planned_savings_total"] == 60000

        # Delete it.
        resp = await client.delete(
            f"/api/v1/rationalization/decisions/{did}", headers=auth_headers(admin)
        )
        assert resp.status_code == 204

    async def test_invalid_time_decision_rejected(self, client, db, rat_env):
        admin = rat_env["admin"]
        cid = (await _create_campaign(client, admin)).json()["id"]
        resp = await client.post(
            f"/api/v1/rationalization/campaigns/{cid}/decisions",
            json={"card_id": str(rat_env["app"].id), "time_decision": "nuke"},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 400

    async def test_decision_on_missing_campaign_404(self, client, db, rat_env):
        resp = await client.post(
            "/api/v1/rationalization/campaigns/00000000-0000-0000-0000-000000000000/decisions",
            json={"card_id": str(rat_env["app"].id)},
            headers=auth_headers(rat_env["admin"]),
        )
        assert resp.status_code == 404
