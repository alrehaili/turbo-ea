"""Integration tests for the EA Requirements register ([FORK] — noraPlan.md
WP6.1, the continuous phase-7 element of the updated NORA methodology)."""

from __future__ import annotations

import pytest

from app.core.permissions import MEMBER_PERMISSIONS, VIEWER_PERMISSIONS
from tests.conftest import auth_headers, create_card, create_card_type, create_role, create_user


@pytest.fixture
async def req_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="viewer", label="Viewer", permissions=VIEWER_PERMISSIONS)
    await create_role(
        db,
        key="ea_working_team",
        label="EA Working Team",
        permissions={**MEMBER_PERMISSIONS, "nora.view": True, "nora.manage": True},
    )
    admin = await create_user(db, email="admin@test.com", role="admin")
    worker = await create_user(db, email="worker@test.com", role="ea_working_team")
    viewer = await create_user(db, email="viewer@test.com", role="viewer")
    await create_card_type(db, key="Application", label="Application")
    await create_card_type(db, key="Initiative", label="Initiative")
    app_card = await create_card(db, card_type="Application", name="National Payment Gateway")
    initiative = await create_card(db, card_type="Initiative", name="Digital Cycle 2027")
    await db.flush()
    return {
        "admin": admin,
        "worker": worker,
        "viewer": viewer,
        "app": app_card,
        "initiative": initiative,
    }


class TestEaRequirements:
    async def test_crud_with_cards_and_initiative(self, client, db, req_env):
        worker, admin = req_env["worker"], req_env["admin"]

        resp = await client.post(
            "/api/v1/ea-requirements",
            json={
                "title": "All external payments must route via the national gateway",
                "source": "SAMA circular 2026-14",
                "domain": "applications",
                "card_ids": [str(req_env["app"].id)],
            },
            headers=auth_headers(worker),
        )
        assert resp.status_code == 201
        req = resp.json()
        assert req["status"] == "proposed"
        assert req["cards"][0]["name"] == "National Payment Gateway"

        # Approving requires governance.approve_step (worker lacks it).
        resp = await client.patch(
            f"/api/v1/ea-requirements/{req['id']}",
            json={"status": "approved"},
            headers=auth_headers(worker),
        )
        assert resp.status_code == 403

        resp = await client.patch(
            f"/api/v1/ea-requirements/{req['id']}",
            json={"status": "approved"},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "approved"
        assert body["approved_by"] is not None

        # Linking the cycle initiative moves an approved requirement inCycle.
        resp = await client.patch(
            f"/api/v1/ea-requirements/{req['id']}",
            json={"initiative_id": str(req_env["initiative"].id)},
            headers=auth_headers(worker),
        )
        body = resp.json()
        assert body["status"] == "inCycle"
        assert body["initiative"]["name"] == "Digital Cycle 2027"

        # Filters.
        resp = await client.get(
            "/api/v1/ea-requirements?domain=applications&status=inCycle",
            headers=auth_headers(worker),
        )
        assert len(resp.json()) == 1

        resp = await client.delete(
            f"/api/v1/ea-requirements/{req['id']}", headers=auth_headers(worker)
        )
        assert resp.status_code == 204

    async def test_invalid_domain_and_status_rejected(self, client, db, req_env):
        worker = req_env["worker"]
        resp = await client.post(
            "/api/v1/ea-requirements",
            json={"title": "X", "domain": "BA"},
            headers=auth_headers(worker),
        )
        assert resp.status_code == 400

        resp = await client.post(
            "/api/v1/ea-requirements",
            json={"title": "Valid", "domain": "security"},
            headers=auth_headers(worker),
        )
        rid = resp.json()["id"]
        resp = await client.patch(
            f"/api/v1/ea-requirements/{rid}",
            json={"status": "done"},
            headers=auth_headers(worker),
        )
        assert resp.status_code == 400

    async def test_viewer_cannot_mutate(self, client, db, req_env):
        viewer, worker = req_env["viewer"], req_env["worker"]
        resp = await client.post(
            "/api/v1/ea-requirements",
            json={"title": "Nope"},
            headers=auth_headers(viewer),
        )
        assert resp.status_code == 403
        # Viewers hold nora.view, so listing works.
        await client.post(
            "/api/v1/ea-requirements",
            json={"title": "Readable"},
            headers=auth_headers(worker),
        )
        resp = await client.get("/api/v1/ea-requirements", headers=auth_headers(viewer))
        assert resp.status_code == 200
        assert len(resp.json()) == 1
