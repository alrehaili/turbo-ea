"""Integration tests for the /scenarios endpoints (Scenario Planning).

[FORK FEATURE]
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.permissions import MEMBER_PERMISSIONS, VIEWER_PERMISSIONS
from app.models.card import Card
from tests.conftest import (
    auth_headers,
    create_card,
    create_card_type,
    create_role,
    create_user,
)


@pytest.fixture
async def scn_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    await create_role(db, key="viewer", label="Viewer", permissions=VIEWER_PERMISSIONS)
    await create_card_type(db, key="Application", label="Application")
    admin = await create_user(db, email="admin@test.com", role="admin")
    viewer = await create_user(db, email="viewer@test.com", role="viewer")
    legacy = await create_card(db, card_type="Application", name="Legacy", user_id=admin.id)
    await db.flush()
    return {"admin": admin, "viewer": viewer, "legacy": legacy}


async def _new_scenario(client, user):
    return (
        await client.post(
            "/api/v1/scenarios", json={"name": "Cloud migration"}, headers=auth_headers(user)
        )
    ).json()["id"]


class TestScenarioCrud:
    async def test_create_and_add_changes(self, client, db, scn_env):
        admin = scn_env["admin"]
        sid = await _new_scenario(client, admin)

        # add op
        resp = await client.post(
            f"/api/v1/scenarios/{sid}/changes",
            json={"op": "add", "card_type": "Application", "name": "New SaaS"},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 201

        # retire op against the legacy card
        resp = await client.post(
            f"/api/v1/scenarios/{sid}/changes",
            json={"op": "retire", "target_card_id": str(scn_env["legacy"].id)},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 201
        assert resp.json()["card_type"] == "Application"
        assert resp.json()["name"] == "Legacy"

        resp = await client.get(f"/api/v1/scenarios/{sid}", headers=auth_headers(admin))
        assert len(resp.json()["changes"]) == 2

    async def test_add_requires_type_and_name(self, client, db, scn_env):
        admin = scn_env["admin"]
        sid = await _new_scenario(client, admin)
        resp = await client.post(
            f"/api/v1/scenarios/{sid}/changes",
            json={"op": "add"},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 400

    async def test_viewer_cannot_create(self, client, db, scn_env):
        resp = await client.post(
            "/api/v1/scenarios", json={"name": "X"}, headers=auth_headers(scn_env["viewer"])
        )
        assert resp.status_code == 403


class TestDiffAndMerge:
    async def test_diff_summary(self, client, db, scn_env):
        admin = scn_env["admin"]
        sid = await _new_scenario(client, admin)
        await client.post(
            f"/api/v1/scenarios/{sid}/changes",
            json={"op": "add", "card_type": "Application", "name": "New SaaS"},
            headers=auth_headers(admin),
        )
        await client.post(
            f"/api/v1/scenarios/{sid}/changes",
            json={"op": "retire", "target_card_id": str(scn_env["legacy"].id)},
            headers=auth_headers(admin),
        )
        resp = await client.get(f"/api/v1/scenarios/{sid}/diff", headers=auth_headers(admin))
        assert resp.status_code == 200
        summary = resp.json()["summary"]
        assert summary["added"] == 1
        assert summary["retired"] == 1
        assert summary["changes"] == 2

    async def test_merge_applies_changes(self, client, db, scn_env):
        admin = scn_env["admin"]
        sid = await _new_scenario(client, admin)
        await client.post(
            f"/api/v1/scenarios/{sid}/changes",
            json={
                "op": "add",
                "card_type": "Application",
                "name": "New SaaS",
                "payload": {"description": "from scenario"},
            },
            headers=auth_headers(admin),
        )
        await client.post(
            f"/api/v1/scenarios/{sid}/changes",
            json={"op": "retire", "target_card_id": str(scn_env["legacy"].id)},
            headers=auth_headers(admin),
        )

        # Dry-run first: reports outcomes, writes nothing.
        resp = await client.post(
            f"/api/v1/scenarios/{sid}/merge?dry_run=true", headers=auth_headers(admin)
        )
        assert resp.status_code == 200
        assert resp.json()["applied"] == 2
        assert resp.json()["conflicts"] == 0

        # Real merge.
        resp = await client.post(f"/api/v1/scenarios/{sid}/merge", headers=auth_headers(admin))
        assert resp.status_code == 200
        assert resp.json()["applied"] == 2

        # New card exists, legacy is archived.
        new_card = (
            await db.execute(select(Card).where(Card.name == "New SaaS"))
        ).scalar_one_or_none()
        assert new_card is not None
        legacy = (
            await db.execute(select(Card).where(Card.id == scn_env["legacy"].id))
        ).scalar_one()
        assert legacy.status == "ARCHIVED"

        # Scenario now merged; re-merge rejected.
        resp = await client.get(f"/api/v1/scenarios/{sid}", headers=auth_headers(admin))
        assert resp.json()["status"] == "merged"
        resp = await client.post(f"/api/v1/scenarios/{sid}/merge", headers=auth_headers(admin))
        assert resp.status_code == 400

    async def test_merge_detects_conflict(self, client, db, scn_env):
        admin = scn_env["admin"]
        sid = await _new_scenario(client, admin)
        # Retire a card, then hard-delete it so the merge target is missing.
        await client.post(
            f"/api/v1/scenarios/{sid}/changes",
            json={"op": "retire", "target_card_id": str(scn_env["legacy"].id)},
            headers=auth_headers(admin),
        )
        legacy = (
            await db.execute(select(Card).where(Card.id == scn_env["legacy"].id))
        ).scalar_one()
        await db.delete(legacy)
        await db.commit()

        resp = await client.post(f"/api/v1/scenarios/{sid}/merge", headers=auth_headers(admin))
        assert resp.status_code == 200
        assert resp.json()["conflicts"] == 1
        assert resp.json()["applied"] == 0
