"""Integration tests for Phase B.9: segment filtering in inventory and reports."""

from __future__ import annotations

import pytest

from app.core.permissions import MEMBER_PERMISSIONS
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
async def segment_test_env(db):
    """Set up test environment with segment, related cards, and users."""
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    admin = await create_user(db, email="admin@test.com", role="admin")
    member = await create_user(db, email="member@test.com", role="member")
    await db.flush()

    # Create card types
    await create_card_type(
        db, key="BusinessCapability", label="Capability", category="Business"
    )
    await create_card_type(db, key="Application", label="Application", category="Application")
    await create_card_type(db, key="ITComponent", label="IT Component", category="Technology")

    # Create relation types
    await create_relation_type(
        db,
        key="relCapToApp",
        label="is supported by",
        source_type_key="BusinessCapability",
        target_type_key="Application",
    )
    await create_relation_type(
        db,
        key="relAppToComponent",
        label="runs on",
        source_type_key="Application",
        target_type_key="ITComponent",
    )

    # Create segment root and hierarchy
    root = await create_card(db, card_type="BusinessCapability", name="Payments")
    child = await create_card(
        db, card_type="BusinessCapability", name="Card Payments", parent_id=root.id
    )

    # Create apps in and out of segment
    app_in = await create_card(db, card_type="Application", name="Payment Gateway")
    app_out = await create_card(db, card_type="Application", name="Unrelated App")

    # Create components
    component = await create_card(db, card_type="ITComponent", name="Database")

    # Link cards
    await create_relation(db, type_key="relCapToApp", source_id=child.id, target_id=app_in.id)
    await create_relation(
        db, type_key="relAppToComponent", source_id=app_in.id, target_id=component.id
    )

    await db.flush()

    return {
        "admin": admin,
        "member": member,
        "root": root,
        "child": child,
        "app_in": app_in,
        "app_out": app_out,
        "component": component,
    }


class TestInventorySegmentFiltering:
    async def test_list_cards_with_segment(self, client, db, segment_test_env):
        """Test that GET /cards with segment_id returns only cards in segment scope."""
        admin = segment_test_env["admin"]

        # Create segment
        seg = (
            await client.post(
                "/api/v1/nora-segments",
                json={"name": "Payments segment", "root_card_id": str(segment_test_env["root"].id)},
                headers=auth_headers(admin),
            )
        ).json()

        # Query without segment — should see all
        res_all = (
            await client.get(
                "/api/v1/cards?type=Application", headers=auth_headers(admin)
            )
        ).json()
        assert len(res_all["items"]) == 2

        # Query with segment — should see only in-scope app
        res_seg = (
            await client.get(
                f"/api/v1/cards?type=Application&segment_id={seg['id']}",
                headers=auth_headers(admin),
            )
        ).json()
        assert len(res_seg["items"]) == 1
        assert res_seg["items"][0]["name"] == "Payment Gateway"

    async def test_empty_segment_scope(self, client, db, segment_test_env):
        """Test that empty segment scope returns empty result."""
        admin = segment_test_env["admin"]

        # Create segment with no descendants or related cards
        orphan = await create_card(db, card_type="BusinessCapability", name="Orphan")
        await db.flush()

        seg = (
            await client.post(
                "/api/v1/nora-segments",
                json={"name": "Orphan segment", "root_card_id": str(orphan.id)},
                headers=auth_headers(admin),
            )
        ).json()

        # Query with segment should return empty result
        res = (
            await client.get(
                f"/api/v1/cards?type=Application&segment_id={seg['id']}",
                headers=auth_headers(admin),
            )
        ).json()
        assert len(res["items"]) == 0
        assert res["total"] == 0

    async def test_invalid_segment_id(self, client, segment_test_env):
        """Test that invalid segment_id is rejected."""
        admin = segment_test_env["admin"]

        # Query with malformed UUID
        res = await client.get(
            "/api/v1/cards?segment_id=not-a-uuid", headers=auth_headers(admin)
        )
        assert res.status_code == 400

    async def test_segment_not_found(self, client, segment_test_env):
        """Test that non-existent segment_id is rejected."""
        admin = segment_test_env["admin"]

        # Query with valid but non-existent UUID
        res = await client.get(
            "/api/v1/cards?segment_id=00000000-0000-0000-0000-000000000000",
            headers=auth_headers(admin),
        )
        assert res.status_code == 404

    async def test_requires_nora_view_permission(self, client, db, segment_test_env):
        """Test that segment filtering requires nora.view permission."""
        viewer = await create_user(db, email="viewer@test.com", role="member")
        await db.flush()

        seg = (
            await client.post(
                "/api/v1/nora-segments",
                json={"name": "Test segment", "root_card_id": str(segment_test_env["root"].id)},
                headers=auth_headers(segment_test_env["admin"]),
            )
        ).json()

        # Member role doesn't have nora.view
        res = await client.get(
            f"/api/v1/cards?segment_id={seg['id']}", headers=auth_headers(viewer)
        )
        assert res.status_code == 403


class TestReportSegmentFiltering:
    async def test_landscape_with_segment(self, client, db, segment_test_env):
        """Test that GET /reports/landscape with segment_id filters results."""
        admin = segment_test_env["admin"]

        seg = (
            await client.post(
                "/api/v1/nora-segments",
                json={"name": "Payments segment", "root_card_id": str(segment_test_env["root"].id)},
                headers=auth_headers(admin),
            )
        ).json()

        # Query without segment
        res_all = (
            await client.get(
                "/api/v1/reports/landscape?type=Application&group_by=BusinessCapability",
                headers=auth_headers(admin),
            )
        ).json()
        # Should have 2 apps: one grouped, one ungrouped
        grouped_count = sum(len(g["items"]) for g in res_all["groups"])
        ungrouped_count = len(res_all["ungrouped"])
        assert grouped_count + ungrouped_count == 2

        # Query with segment
        res_seg = (
            await client.get(
                f"/api/v1/reports/landscape?type=Application&group_by=BusinessCapability&segment_id={seg['id']}",
                headers=auth_headers(admin),
            )
        ).json()
        # Should have only 1 app (the in-scope one, grouped)
        grouped_count = sum(len(g["items"]) for g in res_seg["groups"])
        ungrouped_count = len(res_seg["ungrouped"])
        assert grouped_count + ungrouped_count == 1

    async def test_portfolio_with_segment(self, client, db, segment_test_env):
        """Test that GET /reports/portfolio with segment_id filters results."""
        admin = segment_test_env["admin"]

        seg = (
            await client.post(
                "/api/v1/nora-segments",
                json={"name": "Payments segment", "root_card_id": str(segment_test_env["root"].id)},
                headers=auth_headers(admin),
            )
        ).json()

        # Query without segment
        res_all = (
            await client.get(
                "/api/v1/reports/portfolio?type=Application", headers=auth_headers(admin)
            )
        ).json()
        assert len(res_all["items"]) == 2

        # Query with segment
        res_seg = (
            await client.get(
                f"/api/v1/reports/portfolio?type=Application&segment_id={seg['id']}",
                headers=auth_headers(admin),
            )
        ).json()
        assert len(res_seg["items"]) == 1
        assert res_seg["items"][0]["name"] == "Payment Gateway"

    async def test_matrix_with_segment(self, client, db, segment_test_env):
        """Test that GET /reports/matrix with segment_id filters results."""
        admin = segment_test_env["admin"]

        seg = (
            await client.post(
                "/api/v1/nora-segments",
                json={"name": "Payments segment", "root_card_id": str(segment_test_env["root"].id)},
                headers=auth_headers(admin),
            )
        ).json()

        # Query without segment
        res_all = (
            await client.get(
                "/api/v1/reports/matrix?row_type=Application&col_type=BusinessCapability",
                headers=auth_headers(admin),
            )
        ).json()
        assert len(res_all["rows"]) == 2  # Both apps
        assert len(res_all["columns"]) == 2  # Both capabilities

        # Query with segment
        res_seg = (
            await client.get(
                f"/api/v1/reports/matrix?row_type=Application&col_type=BusinessCapability&segment_id={seg['id']}",
                headers=auth_headers(admin),
            )
        ).json()
        assert len(res_seg["rows"]) == 1  # Only in-scope app
        assert len(res_seg["columns"]) == 2  # Both capabilities still visible (hierarchy-rooted)

    async def test_dependencies_with_segment(self, client, db, segment_test_env):
        """Test that GET /reports/dependencies with segment_id filters results."""
        admin = segment_test_env["admin"]

        seg = (
            await client.post(
                "/api/v1/nora-segments",
                json={"name": "Payments segment", "root_card_id": str(segment_test_env["root"].id)},
                headers=auth_headers(admin),
            )
        ).json()

        # Query without segment
        res_all = (
            await client.get(
                "/api/v1/reports/dependencies", headers=auth_headers(admin)
            )
        ).json()
        all_node_names = {n["name"] for n in res_all["nodes"]}
        # Should have: 2 capabilities, 2 apps, 1 component
        assert len(all_node_names) == 5

        # Query with segment
        res_seg = (
            await client.get(
                f"/api/v1/reports/dependencies?segment_id={seg['id']}", headers=auth_headers(admin)
            )
        ).json()
        seg_node_names = {n["name"] for n in res_seg["nodes"]}
        # Should have: Payments, Card Payments, Payment Gateway, Database
        expected = {"Payments", "Card Payments", "Payment Gateway", "Database"}
        assert seg_node_names == expected
