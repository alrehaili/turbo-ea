"""Integration tests for the Reference Models API ([FORK] — noraPlan.md
WP100.3): per-domain RM CRUD, governed publish/supersede lifecycle,
hierarchical items, xlsx export/import roundtrip, and the /active endpoints
that back the card-detail code pickers."""

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

_XLSX_MAGIC = b"PK\x03\x04"


@pytest.fixture
async def rm_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="viewer", label="Viewer", permissions=VIEWER_PERMISSIONS)
    # Manager can CRUD reference models but lacks governance.approve_step.
    await create_role(
        db,
        key="rm_manager",
        label="RM Manager",
        permissions={
            **MEMBER_PERMISSIONS,
            "reference_models.view": True,
            "reference_models.manage": True,
        },
    )
    admin = await create_user(db, email="admin@test.com", role="admin")
    manager = await create_user(db, email="manager@test.com", role="rm_manager")
    viewer = await create_user(db, email="viewer@test.com", role="viewer")
    await db.flush()
    return {"admin": admin, "manager": manager, "viewer": viewer}


async def _create_model(client, user, domain="business", name="Agency BRM", **extra):
    resp = await client.post(
        "/api/v1/reference-models",
        json={"domain": domain, "name": name, **extra},
        headers=auth_headers(user),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestReferenceModelCrud:
    async def test_model_and_item_crud(self, client, db, rm_env):
        manager = rm_env["manager"]
        model = await _create_model(client, manager, name_ar="النموذج المرجعي للأعمال")
        assert model["status"] == "draft"
        assert model["source"] == "agency"
        assert model["item_count"] == 0

        # Root + child items.
        resp = await client.post(
            f"/api/v1/reference-models/{model['id']}/items",
            json={"code": "BRM-1", "name": "Core", "name_ar": "أساسية"},
            headers=auth_headers(manager),
        )
        assert resp.status_code == 200
        root = resp.json()
        resp = await client.post(
            f"/api/v1/reference-models/{model['id']}/items",
            json={"code": "BRM-1.1", "name": "Payments", "parent_id": root["id"]},
            headers=auth_headers(manager),
        )
        child = resp.json()
        assert child["parent_id"] == root["id"]

        # Duplicate code in the same model → 409.
        resp = await client.post(
            f"/api/v1/reference-models/{model['id']}/items",
            json={"code": "BRM-1", "name": "Dup"},
            headers=auth_headers(manager),
        )
        assert resp.status_code == 409

        # Cycle guard: root cannot become a child of its own descendant.
        resp = await client.patch(
            f"/api/v1/reference-models/items/{root['id']}",
            json={"parent_id": child["id"]},
            headers=auth_headers(manager),
        )
        assert resp.status_code == 400

        # Item edit.
        resp = await client.patch(
            f"/api/v1/reference-models/items/{child['id']}",
            json={"name": "Payments & Transfers", "sort_order": 5},
            headers=auth_headers(manager),
        )
        assert resp.json()["name"] == "Payments & Transfers"

        # Detail returns both items sorted.
        resp = await client.get(
            f"/api/v1/reference-models/{model['id']}", headers=auth_headers(manager)
        )
        body = resp.json()
        assert body["model"]["item_count"] == 2
        assert [i["code"] for i in body["items"]] == ["BRM-1", "BRM-1.1"]

        # Deleting the root cascades to the child.
        resp = await client.delete(
            f"/api/v1/reference-models/items/{root['id']}", headers=auth_headers(manager)
        )
        assert resp.status_code == 200
        resp = await client.get(
            f"/api/v1/reference-models/{model['id']}", headers=auth_headers(manager)
        )
        assert resp.json()["items"] == []

    async def test_invalid_domain_rejected(self, client, db, rm_env):
        resp = await client.post(
            "/api/v1/reference-models",
            json={"domain": "BA", "name": "Nope"},
            headers=auth_headers(rm_env["manager"]),
        )
        assert resp.status_code == 422

    async def test_viewer_can_list_but_not_mutate(self, client, db, rm_env):
        manager, viewer = rm_env["manager"], rm_env["viewer"]
        await _create_model(client, manager)
        resp = await client.get("/api/v1/reference-models", headers=auth_headers(viewer))
        assert resp.status_code == 200
        assert len(resp.json()["models"]) == 1
        resp = await client.post(
            "/api/v1/reference-models",
            json={"domain": "data", "name": "Nope"},
            headers=auth_headers(viewer),
        )
        assert resp.status_code == 403


class TestPublishLifecycle:
    async def test_publish_requires_governance_approve_step(self, client, db, rm_env):
        manager = rm_env["manager"]
        model = await _create_model(client, manager)
        resp = await client.post(
            f"/api/v1/reference-models/{model['id']}/publish", headers=auth_headers(manager)
        )
        assert resp.status_code == 403

    async def test_publish_supersedes_and_gates_delete(self, client, db, rm_env):
        admin = rm_env["admin"]
        first = await _create_model(client, admin, name="BRM v1")
        second = await _create_model(client, admin, name="BRM v2")

        resp = await client.post(
            f"/api/v1/reference-models/{first['id']}/publish", headers=auth_headers(admin)
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

        # A published model cannot be deleted.
        resp = await client.delete(
            f"/api/v1/reference-models/{first['id']}", headers=auth_headers(admin)
        )
        assert resp.status_code == 409

        # Publishing the second archives the first (supersede).
        resp = await client.post(
            f"/api/v1/reference-models/{second['id']}/publish", headers=auth_headers(admin)
        )
        assert resp.status_code == 200
        resp = await client.get(
            f"/api/v1/reference-models/{first['id']}", headers=auth_headers(admin)
        )
        assert resp.json()["model"]["status"] == "archived"

        # /active resolves to the newly published model.
        resp = await client.get(
            "/api/v1/reference-models/active?domain=business", headers=auth_headers(admin)
        )
        assert resp.json()["model"]["id"] == second["id"]

        # /active-summary reflects only domains with a published RM.
        resp = await client.get(
            "/api/v1/reference-models/active-summary", headers=auth_headers(admin)
        )
        summary = resp.json()
        assert summary["business"] is True
        assert summary["technology"] is False

    async def test_active_empty_domain(self, client, db, rm_env):
        resp = await client.get(
            "/api/v1/reference-models/active?domain=security",
            headers=auth_headers(rm_env["viewer"]),
        )
        assert resp.status_code == 200
        assert resp.json() == {"model": None, "items": []}


class TestImportExport:
    async def test_export_import_roundtrip(self, client, db, rm_env):
        manager = rm_env["manager"]
        model = await _create_model(client, manager)
        r1 = await client.post(
            f"/api/v1/reference-models/{model['id']}/items",
            json={"code": "BRM-1", "name": "Core", "name_ar": "أساسية"},
            headers=auth_headers(manager),
        )
        await client.post(
            f"/api/v1/reference-models/{model['id']}/items",
            json={"code": "BRM-1.1", "name": "Payments", "parent_id": r1.json()["id"]},
            headers=auth_headers(manager),
        )

        resp = await client.get(
            f"/api/v1/reference-models/{model['id']}/export", headers=auth_headers(manager)
        )
        assert resp.status_code == 200
        exported = resp.content
        assert exported.startswith(_XLSX_MAGIC)

        # Re-import into the same model → all-unchanged no-op.
        resp = await client.post(
            f"/api/v1/reference-models/{model['id']}/import",
            files={"file": ("rm.xlsx", exported, "application/octet-stream")},
            headers=auth_headers(manager),
        )
        assert resp.status_code == 200
        summary = resp.json()["summary"]
        assert summary["created"] == 0
        assert summary["updated"] == 0
        assert summary["unchanged"] == 2

        # Import into a brand-new model recreates the tree.
        resp = await client.post(
            "/api/v1/reference-models/import",
            files={"file": ("rm.xlsx", exported, "application/octet-stream")},
            data={"domain": "business", "name": "Imported BRM"},
            headers=auth_headers(manager),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["summary"]["created"] == 2
        detail = await client.get(
            f"/api/v1/reference-models/{body['model']['id']}", headers=auth_headers(manager)
        )
        items = detail.json()["items"]
        by_code = {i["code"]: i for i in items}
        assert by_code["BRM-1.1"]["parent_id"] == by_code["BRM-1"]["id"]

    async def test_import_garbage_rejected(self, client, db, rm_env):
        resp = await client.post(
            "/api/v1/reference-models/import",
            files={"file": ("rm.xlsx", b"not a workbook", "application/octet-stream")},
            data={"domain": "business", "name": "Broken"},
            headers=auth_headers(rm_env["manager"]),
        )
        assert resp.status_code == 400


class TestReportCoverage:
    async def test_reference_models_report_carries_rm_coverage(self, client, db, rm_env):
        admin = rm_env["admin"]
        await create_card_type(
            db,
            key="BusinessCapability",
            label="Business Capability",
            built_in=True,
            fields_schema=[
                {
                    "section": "NORA Alignment",
                    "fields": [
                        {
                            "key": "brmLevel",
                            "label": "BRM Level",
                            "type": "single_select",
                            "options": [{"key": "businessArea", "label": "Business Area"}],
                        },
                        {"key": "brmCode", "label": "BRM Code", "type": "text"},
                    ],
                }
            ],
        )
        await create_card(
            db,
            card_type="BusinessCapability",
            name="Payments",
            attributes={"brmLevel": "businessArea", "brmCode": "BRM-1"},
        )
        await create_card(
            db,
            card_type="BusinessCapability",
            name="Licensing",
            attributes={"brmCode": "NOPE-9"},
        )
        await create_card(db, card_type="BusinessCapability", name="Uncoded")
        await db.flush()

        # Without a published RM the block is absent.
        resp = await client.get("/api/v1/reports/reference-models", headers=auth_headers(admin))
        brm = next(m for m in resp.json()["models"] if m["key"] == "brm")
        assert "reference_model" not in brm

        # Publish a business RM with one matching code.
        model = await _create_model(client, admin, name="National BRM")
        await client.post(
            f"/api/v1/reference-models/{model['id']}/items",
            json={"code": "BRM-1", "name": "Core"},
            headers=auth_headers(admin),
        )
        await client.post(
            f"/api/v1/reference-models/{model['id']}/publish", headers=auth_headers(admin)
        )

        resp = await client.get("/api/v1/reports/reference-models", headers=auth_headers(admin))
        brm = next(m for m in resp.json()["models"] if m["key"] == "brm")
        rm = brm["reference_model"]
        assert rm["name"] == "National BRM"
        assert rm["item_count"] == 1
        assert rm["mapped"] == 1
        assert rm["unmatched"] == 1
        assert rm["uncoded"] == 1


class TestStarterSeed:
    async def test_seed_is_idempotent(self, client, db, rm_env):
        from app.services.reference_models import seed_reference_model_starters

        first = await seed_reference_model_starters(db)
        assert first == 2
        second = await seed_reference_model_starters(db)
        assert second == 0

        resp = await client.get(
            "/api/v1/reference-models?domain=business", headers=auth_headers(rm_env["viewer"])
        )
        models = resp.json()["models"]
        starter = next(m for m in models if m["key"] == "nea_business_preview")
        assert starter["status"] == "draft"
        assert starter["source"] == "national"
        assert starter["built_in"] is True
        assert starter["item_count"] == 5
