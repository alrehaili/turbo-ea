"""Integration tests for the /roadmaps endpoints (Transformation Roadmap).

[FORK FEATURE]
"""

from __future__ import annotations

import pytest

from app.core.permissions import MEMBER_PERMISSIONS, VIEWER_PERMISSIONS
from tests.conftest import (
    auth_headers,
    create_card,
    create_relation,
    create_relation_type,
    create_role,
    create_user,
)


@pytest.fixture
async def roadmap_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    await create_role(db, key="viewer", label="Viewer", permissions=VIEWER_PERMISSIONS)
    admin = await create_user(db, email="admin@test.com", role="admin")
    member = await create_user(db, email="member@test.com", role="member")
    viewer = await create_user(db, email="viewer@test.com", role="viewer")
    return {"admin": admin, "member": member, "viewer": viewer}


class TestRoadmapData:
    async def test_groups_cards_into_lanes_by_relation(self, client, db, roadmap_env):
        admin = roadmap_env["admin"]
        # A capability (lane) and two applications (bars), one linked, one orphan.
        cap = await create_card(db, card_type="BusinessCapability", name="Finance")
        linked = await create_card(
            db, card_type="Application", name="ERP", lifecycle={"active": "2026-01-01"}
        )
        await create_card(
            db, card_type="Application", name="CRM", lifecycle={"active": "2026-02-01"}
        )
        await create_relation_type(
            db,
            key="app_to_cap",
            source_type_key="Application",
            target_type_key="BusinessCapability",
        )
        await create_relation(db, type_key="app_to_cap", source_id=linked.id, target_id=cap.id)
        await db.flush()

        resp = await client.get(
            "/api/v1/roadmaps/data?type=Application&group_by=BusinessCapability",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["lanes"]) == 1
        assert body["lanes"][0]["name"] == "Finance"
        assert [i["name"] for i in body["lanes"][0]["items"]] == ["ERP"]
        # The unlinked application falls into ungrouped.
        assert [i["name"] for i in body["ungrouped"]] == ["CRM"]

    async def test_excludes_cards_without_lifecycle(self, client, db, roadmap_env):
        admin = roadmap_env["admin"]
        await create_card(db, card_type="Application", name="NoDates", lifecycle={})
        await db.flush()
        resp = await client.get(
            "/api/v1/roadmaps/data?type=Application&group_by=BusinessCapability",
            headers=auth_headers(admin),
        )
        body = resp.json()
        assert body["lanes"] == []
        assert body["ungrouped"] == []


class TestRoadmapCrud:
    async def test_create_list_and_compute_saved(self, client, db, roadmap_env):
        admin = roadmap_env["admin"]
        await create_card(
            db, card_type="Application", name="App1", lifecycle={"active": "2026-01-01"}
        )
        await db.flush()

        created = await client.post(
            "/api/v1/roadmaps",
            headers=auth_headers(admin),
            json={
                "name": "My roadmap",
                "config": {"type": "Application", "group_by": "Organization"},
            },
        )
        assert created.status_code == 201
        rid = created.json()["id"]

        listed = await client.get("/api/v1/roadmaps", headers=auth_headers(admin))
        assert any(r["id"] == rid for r in listed.json())

        data = await client.get(f"/api/v1/roadmaps/{rid}/data", headers=auth_headers(admin))
        assert data.status_code == 200
        assert data.json()["card_type"] == "Application"
        assert data.json()["roadmap"]["name"] == "My roadmap"

    async def test_milestone_lifecycle(self, client, db, roadmap_env):
        admin = roadmap_env["admin"]
        rid = (
            await client.post(
                "/api/v1/roadmaps",
                headers=auth_headers(admin),
                json={"name": "R", "config": {}},
            )
        ).json()["id"]

        ms = await client.post(
            f"/api/v1/roadmaps/{rid}/milestones",
            headers=auth_headers(admin),
            json={"label": "Go-live", "target_date": "2026-09-01"},
        )
        assert ms.status_code == 201
        mid = ms.json()["id"]

        data = await client.get(f"/api/v1/roadmaps/{rid}/data", headers=auth_headers(admin))
        assert [m["label"] for m in data.json()["milestones"]] == ["Go-live"]

        deleted = await client.delete(
            f"/api/v1/roadmaps/milestones/{mid}", headers=auth_headers(admin)
        )
        assert deleted.status_code == 204

    async def test_viewer_cannot_create(self, client, db, roadmap_env):
        viewer = roadmap_env["viewer"]
        resp = await client.post(
            "/api/v1/roadmaps",
            headers=auth_headers(viewer),
            json={"name": "Nope", "config": {}},
        )
        assert resp.status_code == 403

    async def test_viewer_can_read(self, client, db, roadmap_env):
        viewer = roadmap_env["viewer"]
        resp = await client.get(
            "/api/v1/roadmaps/data?type=Application&group_by=Organization",
            headers=auth_headers(viewer),
        )
        assert resp.status_code == 200
