"""Integration tests for the NEA alignment / evidence-pack export
([FORK] — noraPlan.md WP5.3)."""

from __future__ import annotations

import pytest

from app.core.permissions import MEMBER_PERMISSIONS
from tests.conftest import auth_headers, create_card, create_card_type, create_role, create_user


@pytest.fixture
async def nea_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    admin = await create_user(db, email="admin@test.com", role="admin")
    member = await create_user(db, email="member@test.com", role="member")
    await db.flush()
    return {"admin": admin, "member": member}


class TestNeaEvidencePack:
    async def test_generate_download_list_delete(self, client, db, nea_env):
        admin = nea_env["admin"]
        # Seed a capability with a BRM code so coverage is non-trivial.
        await create_card_type(db, key="BusinessCapability", label="Business Capability")
        await create_card(
            db,
            card_type="BusinessCapability",
            name="Citizen Services",
            attributes={"brmCode": "BRM-1", "brmLevel": "businessArea"},
        )
        await create_card(db, card_type="BusinessCapability", name="Unmapped Cap")
        await db.flush()

        # Generate.
        resp = await client.post(
            "/api/v1/nea-evidence-packs", json={"title": "Q3 pack"}, headers=auth_headers(admin)
        )
        assert resp.status_code == 201
        pack = resp.json()
        assert pack["status"] == "ready"
        assert pack["file_size"] > 0
        # 1 of 2 capabilities mapped → 50% BRM coverage.
        assert pack["summary"]["brm_coverage"] == 50.0
        assert pack["summary"]["capabilities"] == 2

        # Download returns a real xlsx.
        dl = await client.get(
            f"/api/v1/nea-evidence-packs/{pack['id']}/download", headers=auth_headers(admin)
        )
        assert dl.status_code == 200
        assert dl.content[:2] == b"PK"  # zip/xlsx magic
        assert len(dl.content) > 100

        # List shows it.
        lst = await client.get("/api/v1/nea-evidence-packs", headers=auth_headers(admin))
        assert any(p["id"] == pack["id"] for p in lst.json())

        # Delete.
        d = await client.delete(
            f"/api/v1/nea-evidence-packs/{pack['id']}", headers=auth_headers(admin)
        )
        assert d.status_code == 204

    async def test_generate_on_empty_landscape_still_ready(self, client, db, nea_env):
        # No cards, no maturity, no standards — must not crash.
        resp = await client.post(
            "/api/v1/nea-evidence-packs", json={}, headers=auth_headers(nea_env["admin"])
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "ready"
        assert resp.json()["summary"]["brm_coverage"] == 0.0
        # File writes aren't transactional — delete so no stray file is left on disk.
        await client.delete(
            f"/api/v1/nea-evidence-packs/{resp.json()['id']}",
            headers=auth_headers(nea_env["admin"]),
        )

    async def test_member_can_view_but_not_generate(self, client, db, nea_env):
        member = nea_env["member"]
        # nora.view is granted to member → can list.
        lst = await client.get("/api/v1/nea-evidence-packs", headers=auth_headers(member))
        assert lst.status_code == 200
        # nora.manage is not → cannot generate.
        gen = await client.post("/api/v1/nea-evidence-packs", json={}, headers=auth_headers(member))
        assert gen.status_code == 403
