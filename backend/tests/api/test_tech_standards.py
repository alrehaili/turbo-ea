"""Integration tests for the /tech-standards endpoints.

Technology Standards catalogue + exception register (clean separate catalogue).

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
async def std_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    # A role that can manage standards but NOT approve exceptions.
    await create_role(
        db,
        key="author",
        label="Author",
        permissions={
            "tech_standards.view": True,
            "tech_standards.manage": True,
            "tech_standards.approve_exception": False,
        },
    )
    await create_role(db, key="viewer", label="Viewer", permissions=VIEWER_PERMISSIONS)
    await create_card_type(db, key="Application", label="Application")
    admin = await create_user(db, email="admin@test.com", role="admin")
    author = await create_user(db, email="author@test.com", role="author")
    viewer = await create_user(db, email="viewer@test.com", role="viewer")
    app = await create_card(db, card_type="Application", name="Legacy DB", user_id=admin.id)
    await db.flush()
    return {"admin": admin, "author": author, "viewer": viewer, "app": app}


async def _mk_standard(client, user, **kwargs):
    payload = {"name": "PostgreSQL", "category": "data", "status": "preferred", **kwargs}
    return await client.post("/api/v1/tech-standards", json=payload, headers=auth_headers(user))


class TestStandardCrud:
    async def test_create_list_get(self, client, db, std_env):
        admin = std_env["admin"]
        resp = await _mk_standard(client, admin)
        assert resp.status_code == 201
        sid = resp.json()["id"]

        resp = await client.get("/api/v1/tech-standards", headers=auth_headers(admin))
        assert resp.status_code == 200
        assert any(s["id"] == sid for s in resp.json())

        resp = await client.get(f"/api/v1/tech-standards/{sid}", headers=auth_headers(admin))
        assert resp.status_code == 200
        assert resp.json()["status"] == "preferred"
        assert resp.json()["exceptions"] == []

    async def test_invalid_status_rejected(self, client, db, std_env):
        resp = await _mk_standard(client, std_env["admin"], status="banned")
        assert resp.status_code == 400

    async def test_invalid_category_rejected(self, client, db, std_env):
        resp = await _mk_standard(client, std_env["admin"], category="bogus")
        assert resp.status_code == 400

    async def test_viewer_cannot_create(self, client, db, std_env):
        resp = await _mk_standard(client, std_env["viewer"])
        assert resp.status_code == 403

    async def test_radar_matrix(self, client, db, std_env):
        admin = std_env["admin"]
        await _mk_standard(client, admin, name="PostgreSQL", category="data", status="preferred")
        await _mk_standard(client, admin, name="Oracle", category="data", status="sunset")
        resp = await client.get("/api/v1/tech-standards/radar", headers=auth_headers(admin))
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total"] == 2
        assert data["summary"]["by_status"]["preferred"] == 1
        assert data["summary"]["by_status"]["sunset"] == 1
        # Both land in the data category, in their respective status rings.
        names = {s["name"] for s in data["matrix"]["data"]["sunset"]}
        assert "Oracle" in names


class TestExceptions:
    async def test_exception_request_and_approval_flow(self, client, db, std_env):
        admin = std_env["admin"]
        author = std_env["author"]
        sid = (await _mk_standard(client, admin, status="prohibited")).json()["id"]

        # Author (manage) can raise an exception request.
        resp = await client.post(
            f"/api/v1/tech-standards/{sid}/exceptions",
            json={
                "card_id": str(std_env["app"].id),
                "justification": "Legacy migration in flight",
                "compensating_controls": "Network isolation",
                "expiry_date": "2027-01-01",
            },
            headers=auth_headers(author),
        )
        assert resp.status_code == 201
        exc = resp.json()
        assert exc["status"] == "requested"
        assert exc["card"]["name"] == "Legacy DB"
        eid = exc["id"]

        # Author CANNOT approve (no approve_exception permission).
        resp = await client.post(
            f"/api/v1/tech-standards/exceptions/{eid}/decision?action=approve",
            headers=auth_headers(author),
        )
        assert resp.status_code == 403

        # Admin can approve.
        resp = await client.post(
            f"/api/v1/tech-standards/exceptions/{eid}/decision?action=approve",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
        assert resp.json()["approver_id"] is not None

        # Listed under the standard.
        resp = await client.get(f"/api/v1/tech-standards/{sid}", headers=auth_headers(admin))
        assert len(resp.json()["exceptions"]) == 1

    async def test_expired_exception_surfaces_as_expired(self, client, db, std_env):
        admin = std_env["admin"]
        sid = (await _mk_standard(client, admin)).json()["id"]
        eid = (
            await client.post(
                f"/api/v1/tech-standards/{sid}/exceptions",
                json={"expiry_date": "2000-01-01"},
                headers=auth_headers(admin),
            )
        ).json()["id"]
        await client.post(
            f"/api/v1/tech-standards/exceptions/{eid}/decision?action=approve",
            headers=auth_headers(admin),
        )
        resp = await client.get("/api/v1/tech-standards/exceptions", headers=auth_headers(admin))
        match = next(e for e in resp.json() if e["id"] == eid)
        # Approved but past expiry -> reported as expired.
        assert match["status"] == "expired"

    async def test_delete_standard_cascades_exceptions(self, client, db, std_env):
        admin = std_env["admin"]
        sid = (await _mk_standard(client, admin)).json()["id"]
        await client.post(
            f"/api/v1/tech-standards/{sid}/exceptions",
            json={"justification": "x"},
            headers=auth_headers(admin),
        )
        resp = await client.delete(f"/api/v1/tech-standards/{sid}", headers=auth_headers(admin))
        assert resp.status_code == 204
        resp = await client.get("/api/v1/tech-standards/exceptions", headers=auth_headers(admin))
        assert all(e["standard_id"] != sid for e in resp.json())
