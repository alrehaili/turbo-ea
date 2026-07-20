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


class TestBrowseEndpoints:
    """RMPlan Phase 1 browse surface: /overview, /{id}/summary, item cards."""

    async def _browse_env(self, client, db, rm_env):
        admin = rm_env["admin"]
        await create_card_type(db, key="BusinessCapability", label="Business Capability")
        await create_card(
            db,
            card_type="BusinessCapability",
            name="Core Management",
            attributes={"brmCode": "BRM-1"},
        )
        await create_card(
            db,
            card_type="BusinessCapability",
            name="Payments",
            attributes={"brmCode": "BRM-1.1"},
        )
        await create_card(
            db,
            card_type="BusinessCapability",
            name="Stray",
            attributes={"brmCode": "NOPE-9"},
        )
        await create_card(db, card_type="BusinessCapability", name="Uncoded")
        await db.flush()

        model = await _create_model(client, admin, name="Agency BRM")
        root = (
            await client.post(
                f"/api/v1/reference-models/{model['id']}/items",
                json={"code": "BRM-1", "name": "Core"},
                headers=auth_headers(admin),
            )
        ).json()
        child = (
            await client.post(
                f"/api/v1/reference-models/{model['id']}/items",
                json={"code": "BRM-1.1", "name": "Payments", "parent_id": root["id"]},
                headers=auth_headers(admin),
            )
        ).json()
        await client.post(
            f"/api/v1/reference-models/{model['id']}/publish", headers=auth_headers(admin)
        )
        return model, root, child

    async def test_overview_counts(self, client, db, rm_env):
        model, _root, _child = await self._browse_env(client, db, rm_env)

        resp = await client.get(
            "/api/v1/reference-models/overview", headers=auth_headers(rm_env["viewer"])
        )
        assert resp.status_code == 200
        entries = {e["domain"]: e for e in resp.json()["models"]}
        assert set(entries) == {
            "business",
            "beneficiaryExperience",
            "applications",
            "data",
            "technology",
            "security",
        }
        biz = entries["business"]
        assert biz["card_type"] == "BusinessCapability"
        assert biz["code_field"] == "brmCode"
        assert biz["model"]["id"] == model["id"]
        assert biz["model"]["item_count"] == 2
        assert biz["covered_items"] == 2
        assert biz["total_cards"] == 4
        assert biz["mapped_cards"] == 2
        assert biz["unmatched_cards"] == 1
        assert biz["uncoded_cards"] == 1
        # Domains without a published model return a bare entry.
        assert entries["technology"]["model"] is None

    async def test_summary_item_counts(self, client, db, rm_env):
        model, root, child = await self._browse_env(client, db, rm_env)

        resp = await client.get(
            f"/api/v1/reference-models/{model['id']}/summary",
            headers=auth_headers(rm_env["viewer"]),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["code_field"] == "brmCode"
        by_code = {i["code"]: i for i in body["items"]}
        assert by_code["BRM-1"]["mapped_direct"] == 1
        assert by_code["BRM-1"]["mapped_total"] == 2  # includes the child's card
        assert by_code["BRM-1.1"]["mapped_direct"] == 1
        assert by_code["BRM-1.1"]["mapped_total"] == 1
        totals = body["totals"]
        assert totals["total_items"] == 2
        assert totals["covered_items"] == 2
        assert totals["mapped_cards"] == 2
        assert totals["unmatched_cards"] == 1
        assert totals["uncoded_cards"] == 1
        assert root["id"] and child["id"]

    async def test_item_cards_descendant_toggle(self, client, db, rm_env):
        model, root, _child = await self._browse_env(client, db, rm_env)

        resp = await client.get(
            f"/api/v1/reference-models/{model['id']}/items/{root['id']}/cards",
            headers=auth_headers(rm_env["viewer"]),
        )
        assert resp.status_code == 200
        cards = resp.json()["cards"]
        assert [c["name"] for c in cards] == ["Core Management", "Payments"]

        resp = await client.get(
            f"/api/v1/reference-models/{model['id']}/items/{root['id']}/cards"
            "?include_descendants=false",
            headers=auth_headers(rm_env["viewer"]),
        )
        assert [c["name"] for c in resp.json()["cards"]] == ["Core Management"]

    async def test_item_cards_unknown_item_404(self, client, db, rm_env):
        model, _root, _child = await self._browse_env(client, db, rm_env)
        resp = await client.get(
            f"/api/v1/reference-models/{model['id']}/items/00000000-0000-0000-0000-000000000000/cards",
            headers=auth_headers(rm_env["admin"]),
        )
        assert resp.status_code == 404


class TestMappingEndpoints:
    """RMPlan Phase 2: explicit card↔item mappings + unmapped inventory."""

    async def _map_env(self, client, db, rm_env):
        admin = rm_env["admin"]
        await create_card_type(db, key="Application", label="Application")
        card_a = await create_card(
            db, card_type="Application", name="ERP", attributes={"armCode": "ARM-1"}
        )
        card_b = await create_card(db, card_type="Application", name="CRM")  # uncoded
        await db.flush()

        model = await _create_model(client, admin, domain="applications", name="Agency ARM")
        item = (
            await client.post(
                f"/api/v1/reference-models/{model['id']}/items",
                json={"code": "ARM-1", "name": "Core"},
                headers=auth_headers(admin),
            )
        ).json()
        await client.post(
            f"/api/v1/reference-models/{model['id']}/publish", headers=auth_headers(admin)
        )
        return model, item, card_a, card_b

    async def test_create_list_patch_delete_mapping(self, client, db, rm_env):
        model, item, _card_a, card_b = await self._map_env(client, db, rm_env)
        manager = rm_env["manager"]

        resp = await client.post(
            f"/api/v1/reference-models/items/{item['id']}/mappings",
            json={"card_id": str(card_b.id), "mapping_type": "secondary", "rationale": "shares fn"},
            headers=auth_headers(manager),
        )
        assert resp.status_code == 200, resp.text
        mapping = resp.json()
        assert mapping["mapping_type"] == "secondary"

        dup = await client.post(
            f"/api/v1/reference-models/items/{item['id']}/mappings",
            json={"card_id": str(card_b.id)},
            headers=auth_headers(manager),
        )
        assert dup.status_code == 409

        listed = await client.get(
            f"/api/v1/reference-models/items/{item['id']}/mappings",
            headers=auth_headers(rm_env["viewer"]),
        )
        rows = listed.json()["mappings"]
        assert len(rows) == 1
        assert rows[0]["card"]["name"] == "CRM"

        patched = await client.patch(
            f"/api/v1/reference-models/mappings/{mapping['id']}",
            json={"mapping_type": "candidate"},
            headers=auth_headers(manager),
        )
        assert patched.json()["mapping_type"] == "candidate"

        deleted = await client.delete(
            f"/api/v1/reference-models/mappings/{mapping['id']}", headers=auth_headers(manager)
        )
        assert deleted.status_code == 204

    async def test_viewer_cannot_map(self, client, db, rm_env):
        _model, item, _a, card_b = await self._map_env(client, db, rm_env)
        resp = await client.post(
            f"/api/v1/reference-models/items/{item['id']}/mappings",
            json={"card_id": str(card_b.id)},
            headers=auth_headers(rm_env["viewer"]),
        )
        assert resp.status_code == 403

    async def test_summary_merges_explicit_mapping(self, client, db, rm_env):
        model, item, card_a, card_b = await self._map_env(client, db, rm_env)
        manager = rm_env["manager"]

        before = await client.get(
            f"/api/v1/reference-models/{model['id']}/summary", headers=auth_headers(manager)
        )
        totals = before.json()["totals"]
        assert totals["mapped_cards"] == 1
        assert totals["uncoded_cards"] == 1

        await client.post(
            f"/api/v1/reference-models/items/{item['id']}/mappings",
            json={"card_id": str(card_b.id)},
            headers=auth_headers(manager),
        )
        after = await client.get(
            f"/api/v1/reference-models/{model['id']}/summary", headers=auth_headers(manager)
        )
        totals = after.json()["totals"]
        assert totals["mapped_cards"] == 2
        assert totals["uncoded_cards"] == 0
        by_code = {i["code"]: i for i in after.json()["items"]}
        assert by_code["ARM-1"]["mapped_direct"] == 2
        assert card_a.id

    async def test_unmapped_inventory(self, client, db, rm_env):
        model, item, _card_a, card_b = await self._map_env(client, db, rm_env)
        manager = rm_env["manager"]

        resp = await client.get(
            f"/api/v1/reference-models/{model['id']}/unmapped-inventory",
            headers=auth_headers(manager),
        )
        names = [c["name"] for c in resp.json()["cards"]]
        assert names == ["CRM"]

        await client.post(
            f"/api/v1/reference-models/items/{item['id']}/mappings",
            json={"card_id": str(card_b.id)},
            headers=auth_headers(manager),
        )
        resp = await client.get(
            f"/api/v1/reference-models/{model['id']}/unmapped-inventory",
            headers=auth_headers(manager),
        )
        assert resp.json()["cards"] == []

    async def test_item_cards_include_explicit(self, client, db, rm_env):
        model, item, _card_a, card_b = await self._map_env(client, db, rm_env)
        manager = rm_env["manager"]
        await client.post(
            f"/api/v1/reference-models/items/{item['id']}/mappings",
            json={"card_id": str(card_b.id), "mapping_type": "supporting"},
            headers=auth_headers(manager),
        )
        resp = await client.get(
            f"/api/v1/reference-models/{model['id']}/items/{item['id']}/cards",
            headers=auth_headers(manager),
        )
        cards = {c["name"]: c for c in resp.json()["cards"]}
        assert cards["ERP"]["source"] == "code"
        assert cards["ERP"]["mapping_type"] == "primary"
        assert cards["CRM"]["source"] == "explicit"
        assert cards["CRM"]["mapping_type"] == "supporting"


class TestNarrative:
    """RMPlan Phase 3: editable poster narrative panels."""

    async def test_patch_and_persist_narrative(self, client, db, rm_env):
        admin = rm_env["admin"]
        model = await _create_model(client, admin, name="Poster BRM")

        payload = {
            "panels": [
                {
                    "id": "mission",
                    "title": "Mission",
                    "kind": "text",
                    "text": "Ensure X",
                    "placement": "header",
                },
                {
                    "id": "objectives",
                    "title": "Objectives",
                    "kind": "list",
                    "items": ["A", "B", ""],
                    "placement": "grid",
                },
            ]
        }
        resp = await client.patch(
            f"/api/v1/reference-models/{model['id']}/narrative",
            json=payload,
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200, resp.text
        narrative = resp.json()["narrative"]
        assert len(narrative["panels"]) == 2
        assert narrative["panels"][0]["placement"] == "header"

        # Persisted + surfaced via GET.
        got = await client.get(
            f"/api/v1/reference-models/{model['id']}", headers=auth_headers(rm_env["viewer"])
        )
        panels = got.json()["model"]["narrative"]["panels"]
        assert panels[1]["items"] == ["A", "B", ""]  # kept verbatim; UI trims blanks

    async def test_narrative_requires_manage(self, client, db, rm_env):
        admin = rm_env["admin"]
        model = await _create_model(client, admin, name="Poster BRM")
        resp = await client.patch(
            f"/api/v1/reference-models/{model['id']}/narrative",
            json={"panels": []},
            headers=auth_headers(rm_env["viewer"]),
        )
        assert resp.status_code == 403

    async def test_narrative_rejects_bad_kind(self, client, db, rm_env):
        admin = rm_env["admin"]
        model = await _create_model(client, admin, name="Poster BRM")
        resp = await client.patch(
            f"/api/v1/reference-models/{model['id']}/narrative",
            json={"panels": [{"id": "x", "kind": "video"}]},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 422


class TestGapAnalysis:
    """RMPlan Phase 4: coverage & gap analysis."""

    async def _gap_env(self, client, db, rm_env):
        admin = rm_env["admin"]
        await create_card_type(db, key="Application", label="Application")
        # Retiring card (phaseOut in the past) mapped to ARM-1; current card on ARM-2.
        await create_card(
            db,
            card_type="Application",
            name="Legacy ERP",
            attributes={"armCode": "ARM-1"},
            lifecycle={"active": "2018-01-01", "phaseOut": "2023-01-01"},
        )
        await create_card(
            db,
            card_type="Application",
            name="New CRM",
            attributes={"armCode": "ARM-2"},
            lifecycle={"active": "2024-01-01"},
        )
        # Two cards on ARM-2 → duplicate support.
        await create_card(
            db,
            card_type="Application",
            name="Alt CRM",
            attributes={"armCode": "ARM-2"},
            lifecycle={"active": "2024-01-01"},
        )
        await db.flush()

        model = await _create_model(client, admin, domain="applications", name="ARM")
        for code in ("ARM-1", "ARM-2", "ARM-3"):
            await client.post(
                f"/api/v1/reference-models/{model['id']}/items",
                json={"code": code, "name": f"Item {code}"},
                headers=auth_headers(admin),
            )
        await client.post(
            f"/api/v1/reference-models/{model['id']}/publish", headers=auth_headers(admin)
        )
        return model

    async def test_gaps_classification(self, client, db, rm_env):
        model = await self._gap_env(client, db, rm_env)
        resp = await client.get(
            f"/api/v1/reference-models/{model['id']}/gaps", headers=auth_headers(rm_env["viewer"])
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        totals = body["totals"]
        assert totals["total_leaves"] == 3
        assert totals["uncovered_leaves"] == 1  # ARM-3 has no mapping
        assert totals["duplicate_leaves"] == 1  # ARM-2 has 2 cards
        assert totals["retiring_leaves"] == 1  # ARM-1 only card is phasing out
        kinds = {(g["code"], g["kind"]) for g in body["gaps"]}
        assert ("ARM-3", "no_mapping") in kinds
        assert ("ARM-2", "duplicate") in kinds
        assert ("ARM-1", "retiring_only") in kinds

    async def test_gaps_matrix_flags_lifecycle_risk(self, client, db, rm_env):
        model = await self._gap_env(client, db, rm_env)
        resp = await client.get(
            f"/api/v1/reference-models/{model['id']}/gaps", headers=auth_headers(rm_env["admin"])
        )
        by_code = {r["code"]: r for r in resp.json()["matrix"]}
        assert by_code["ARM-1"]["lifecycle_risk"] is True
        assert by_code["ARM-2"]["duplicate"] is True
        assert by_code["ARM-3"]["coverage"] == "none"


class TestVersioningAndReview:
    """RMPlan Phase 5: review workflow + version snapshots + diff."""

    async def test_review_workflow(self, client, db, rm_env):
        admin, manager = rm_env["admin"], rm_env["manager"]
        model = await _create_model(client, admin, name="Gov BRM")

        # Manager (no governance.approve_step) can submit but not publish/reject.
        r = await client.post(
            f"/api/v1/reference-models/{model['id']}/submit", headers=auth_headers(manager)
        )
        assert r.status_code == 200
        assert r.json()["status"] == "in_review"

        # Reject requires governance.approve_step → manager forbidden.
        r = await client.post(
            f"/api/v1/reference-models/{model['id']}/reject", headers=auth_headers(manager)
        )
        assert r.status_code == 403

        # Admin rejects → back to draft.
        r = await client.post(
            f"/api/v1/reference-models/{model['id']}/reject", headers=auth_headers(admin)
        )
        assert r.json()["status"] == "draft"

    async def test_publish_snapshots_version(self, client, db, rm_env):
        admin = rm_env["admin"]
        model = await _create_model(client, admin, name="Versioned BRM")
        await client.post(
            f"/api/v1/reference-models/{model['id']}/items",
            json={"code": "BRM-1", "name": "Core"},
            headers=auth_headers(admin),
        )
        # Publish v1.
        r = await client.post(
            f"/api/v1/reference-models/{model['id']}/publish",
            json={"change_summary": "initial"},
            headers=auth_headers(admin),
        )
        assert r.status_code == 200

        versions = (
            await client.get(
                f"/api/v1/reference-models/{model['id']}/versions", headers=auth_headers(admin)
            )
        ).json()["versions"]
        assert len(versions) == 1
        assert versions[0]["change_summary"] == "initial"
        assert versions[0]["item_count"] == 1
        v1_id = versions[0]["id"]

        # Add an item, then diff v1 vs current.
        await client.post(
            f"/api/v1/reference-models/{model['id']}/items",
            json={"code": "BRM-2", "name": "Support"},
            headers=auth_headers(admin),
        )
        diff = (
            await client.get(
                f"/api/v1/reference-models/{model['id']}/versions/{v1_id}/diff?against=current",
                headers=auth_headers(rm_env["viewer"]),
            )
        ).json()["diff"]
        assert diff["counts"]["added"] == 1
        assert diff["added"][0]["code"] == "BRM-2"
        assert diff["counts"]["removed"] == 0

    async def test_only_draft_can_submit(self, client, db, rm_env):
        admin = rm_env["admin"]
        model = await _create_model(client, admin, name="BRM")
        await client.post(
            f"/api/v1/reference-models/{model['id']}/publish", headers=auth_headers(admin)
        )
        r = await client.post(
            f"/api/v1/reference-models/{model['id']}/submit", headers=auth_headers(admin)
        )
        assert r.status_code == 400
