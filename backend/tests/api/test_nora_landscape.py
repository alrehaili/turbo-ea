"""Integration tests for NORA plateaus + segment scopes
([FORK] — noraPlan.md WP5.4)."""

from __future__ import annotations

from datetime import date

import pytest

from app.core.permissions import MEMBER_PERMISSIONS
from app.services.nora_landscape import phase_as_of
from tests.conftest import (
    auth_headers,
    create_card,
    create_card_type,
    create_relation,
    create_relation_type,
    create_role,
    create_user,
)


@pytest.fixture
async def landscape_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    admin = await create_user(db, email="admin@test.com", role="admin")
    member = await create_user(db, email="member@test.com", role="member")
    await db.flush()
    return {"admin": admin, "member": member}


def test_phase_as_of_pure():
    lc = {"active": "2025-01-01", "phaseOut": "2028-01-01"}
    assert phase_as_of(lc, date(2026, 6, 1)) == "active"
    assert phase_as_of(lc, date(2029, 1, 1)) == "phaseOut"
    # Everything in the future → earliest set phase.
    assert phase_as_of({"active": "2030-01-01"}, date(2026, 1, 1)) == "active"
    assert phase_as_of(None, date(2026, 1, 1)) is None


class TestSegments:
    async def test_resolve_hierarchy_and_related(self, client, db, landscape_env):
        admin = landscape_env["admin"]
        await create_card_type(
            db, key="BusinessCapability", label="Capability", category="Business Architecture"
        )
        await create_card_type(
            db, key="Application", label="Application", category="Application & Data"
        )
        await create_relation_type(
            db,
            key="relCapToApp",
            label="is supported by",
            source_type_key="BusinessCapability",
            target_type_key="Application",
        )
        root = await create_card(db, card_type="BusinessCapability", name="Payments")
        child = await create_card(
            db, card_type="BusinessCapability", name="Card Payments", parent_id=root.id
        )
        app = await create_card(db, card_type="Application", name="Payment Gateway")
        await create_relation(db, type_key="relCapToApp", source_id=child.id, target_id=app.id)
        await db.flush()

        seg = (
            await client.post(
                "/api/v1/nora-segments",
                json={"name": "Payments segment", "root_card_id": str(root.id)},
                headers=auth_headers(admin),
            )
        ).json()

        res = (
            await client.get(
                f"/api/v1/nora-segments/{seg['id']}/cards", headers=auth_headers(admin)
            )
        ).json()
        names = {c["name"] for c in res["cards"]}
        assert names == {"Payments", "Card Payments", "Payment Gateway"}
        # Grouped into two EA layers.
        by_cat = {layer["category"]: [c["name"] for c in layer["cards"]] for layer in res["layers"]}
        assert by_cat["Business Architecture"] == ["Card Payments", "Payments"]
        assert by_cat["Application & Data"] == ["Payment Gateway"]

    async def test_related_type_narrowing(self, client, db, landscape_env):
        admin = landscape_env["admin"]
        await create_card_type(db, key="BusinessCapability", label="Capability")
        await create_card_type(db, key="Application", label="Application")
        await create_card_type(db, key="DataObject", label="Data Object")
        await create_relation_type(
            db,
            key="relCapToApp",
            label="supported by",
            source_type_key="BusinessCapability",
            target_type_key="Application",
        )
        await create_relation_type(
            db,
            key="relCapToData",
            label="uses",
            source_type_key="BusinessCapability",
            target_type_key="DataObject",
        )
        root = await create_card(db, card_type="BusinessCapability", name="Root")
        app = await create_card(db, card_type="Application", name="App1")
        data = await create_card(db, card_type="DataObject", name="Data1")
        await create_relation(db, type_key="relCapToApp", source_id=root.id, target_id=app.id)
        await create_relation(db, type_key="relCapToData", source_id=root.id, target_id=data.id)
        await db.flush()

        seg = (
            await client.post(
                "/api/v1/nora-segments",
                json={
                    "name": "Apps only",
                    "root_card_id": str(root.id),
                    "related_type_keys": ["Application"],
                },
                headers=auth_headers(admin),
            )
        ).json()
        res = (
            await client.get(
                f"/api/v1/nora-segments/{seg['id']}/cards", headers=auth_headers(admin)
            )
        ).json()
        names = {c["name"] for c in res["cards"]}
        # Root always kept; DataObject filtered out; Application kept.
        assert names == {"Root", "App1"}

    async def test_member_cannot_create(self, client, db, landscape_env):
        r = await client.post(
            "/api/v1/nora-segments",
            json={"name": "X"},
            headers=auth_headers(landscape_env["member"]),
        )
        assert r.status_code == 403


class TestPlateaus:
    async def test_crud_and_landscape(self, client, db, landscape_env):
        admin = landscape_env["admin"]
        await create_card_type(db, key="Application", label="Application")
        await create_card(
            db,
            card_type="Application",
            name="Legacy",
            lifecycle={"active": "2024-01-01", "phaseOut": "2028-01-01"},
        )
        await create_card(
            db,
            card_type="Application",
            name="Future",
            lifecycle={"plan": "2030-01-01"},
        )
        await db.flush()

        plateau = (
            await client.post(
                "/api/v1/nora-plateaus",
                json={"name": "2026 Interim", "target_date": "2026-06-01"},
                headers=auth_headers(admin),
            )
        ).json()

        land = (
            await client.get(
                f"/api/v1/nora-plateaus/{plateau['id']}/landscape", headers=auth_headers(admin)
            )
        ).json()
        assert land["total"] == 2
        # Legacy is active as of 2026; Future is planned (all dates future).
        assert land["phases"]["active"] == 1
        assert land["phases"]["plan"] == 1

        # List + delete.
        lst = await client.get("/api/v1/nora-plateaus", headers=auth_headers(admin))
        assert len(lst.json()) == 1
        d = await client.delete(
            f"/api/v1/nora-plateaus/{plateau['id']}", headers=auth_headers(admin)
        )
        assert d.status_code == 204

    async def test_member_cannot_create(self, client, db, landscape_env):
        r = await client.post(
            "/api/v1/nora-plateaus",
            json={"name": "X"},
            headers=auth_headers(landscape_env["member"]),
        )
        assert r.status_code == 403
