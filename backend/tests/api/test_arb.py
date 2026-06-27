"""Integration tests for the /arb endpoints (Architecture Review Board).

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
async def arb_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    await create_role(db, key="viewer", label="Viewer", permissions=VIEWER_PERMISSIONS)
    await create_card_type(db, key="Application", label="Application")
    admin = await create_user(db, email="admin@test.com", role="admin")
    viewer = await create_user(db, email="viewer@test.com", role="viewer")
    card = await create_card(db, card_type="Application", name="New Platform", user_id=admin.id)
    await db.flush()
    return {"admin": admin, "viewer": viewer, "card": card}


class TestArb:
    async def test_create_get_decide(self, client, db, arb_env):
        admin = arb_env["admin"]
        resp = await client.post(
            "/api/v1/arb",
            json={"title": "Platform X review", "subject_card_id": str(arb_env["card"].id)},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 201
        rid = resp.json()["id"]
        assert resp.json()["status"] == "scheduled"

        # GET returns the live governance context block.
        resp = await client.get(f"/api/v1/arb/{rid}", headers=auth_headers(admin))
        assert resp.status_code == 200
        body = resp.json()
        assert body["subject"]["name"] == "New Platform"
        assert "context" in body
        assert body["context"]["impact"] is not None
        assert body["context"]["risks"] == []

        # Decide -> reviewer + decided_at stamped.
        resp = await client.patch(
            f"/api/v1/arb/{rid}",
            json={"status": "approved", "decision_notes": "Go ahead"},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
        assert resp.json()["reviewer_id"] is not None
        assert resp.json()["decided_at"] is not None

    async def test_invalid_status_rejected(self, client, db, arb_env):
        admin = arb_env["admin"]
        rid = (
            await client.post("/api/v1/arb", json={"title": "R"}, headers=auth_headers(admin))
        ).json()["id"]
        resp = await client.patch(
            f"/api/v1/arb/{rid}", json={"status": "bogus"}, headers=auth_headers(admin)
        )
        assert resp.status_code == 400

    async def test_viewer_cannot_create_but_can_view(self, client, db, arb_env):
        admin = arb_env["admin"]
        viewer = arb_env["viewer"]
        resp = await client.post("/api/v1/arb", json={"title": "R"}, headers=auth_headers(viewer))
        assert resp.status_code == 403
        rid = (
            await client.post("/api/v1/arb", json={"title": "R"}, headers=auth_headers(admin))
        ).json()["id"]
        resp = await client.get(f"/api/v1/arb/{rid}", headers=auth_headers(viewer))
        assert resp.status_code == 200
