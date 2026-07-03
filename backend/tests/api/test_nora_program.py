"""Integration tests for the NORA EA Program tracker and Improvement
Opportunity registry ([FORK] — noraPlan.md WP3.1 / WP3.3)."""

from __future__ import annotations

import pytest

from app.core.permissions import MEMBER_PERMISSIONS
from app.services.nora_program import NORA_DELIVERABLE_CATALOGUE, seed_nora_program
from tests.conftest import auth_headers, create_card, create_card_type, create_role, create_user


@pytest.fixture
async def program_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    await create_role(
        db,
        key="ea_working_team",
        label="EA Working Team",
        permissions={**MEMBER_PERMISSIONS, "nora.view": True, "nora.manage": True},
    )
    admin = await create_user(db, email="admin@test.com", role="admin")
    worker = await create_user(db, email="worker@test.com", role="ea_working_team")
    await seed_nora_program(db)
    await db.flush()
    return {"admin": admin, "worker": worker}


class TestNoraProgram:
    async def test_catalogue_seeded_and_grouped(self, client, db, program_env):
        resp = await client.get("/api/v1/nora-program", headers=auth_headers(program_env["worker"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total"] == len(NORA_DELIVERABLE_CATALOGUE)
        stage5 = next(s for s in data["stages"] if s["stage_no"] == 5)
        assert {d["key"] for d in stage5["deliverables"]} == {
            "s5_prm",
            "s5_brm",
            "s5_arm",
            "s5_drm",
            "s5_trm",
        }
        assert stage5["progress"] == 0

    async def test_seed_is_idempotent(self, db, program_env):
        assert await seed_nora_program(db) == 0

    async def test_status_and_evidence_update(self, client, db, program_env):
        worker = program_env["worker"]
        data = (await client.get("/api/v1/nora-program", headers=auth_headers(worker))).json()
        target = data["stages"][1]["deliverables"][0]

        resp = await client.patch(
            f"/api/v1/nora-program/deliverables/{target['id']}",
            json={
                "status": "inProgress",
                "evidence": [{"kind": "link", "ref": "/reports/gap-analysis", "label": "Gap"}],
            },
            headers=auth_headers(worker),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "inProgress"
        assert body["evidence"][0]["ref"] == "/reports/gap-analysis"

    async def test_approval_requires_governance_permission(self, client, db, program_env):
        worker, admin = program_env["worker"], program_env["admin"]
        data = (await client.get("/api/v1/nora-program", headers=auth_headers(worker))).json()
        target = data["stages"][1]["deliverables"][0]

        # Working team can manage but not approve.
        resp = await client.patch(
            f"/api/v1/nora-program/deliverables/{target['id']}",
            json={"status": "approved"},
            headers=auth_headers(worker),
        )
        assert resp.status_code == 403

        # Admin wildcard approves; approved_by is stamped.
        resp = await client.patch(
            f"/api/v1/nora-program/deliverables/{target['id']}",
            json={"status": "approved"},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["approved_by"] is not None

        # Stage progress reflects the approval.
        data = (await client.get("/api/v1/nora-program", headers=auth_headers(worker))).json()
        stage1 = next(s for s in data["stages"] if s["stage_no"] == 1)
        assert stage1["progress"] == 50  # 1 of 2 stage-1 deliverables

    async def test_custom_deliverable_lifecycle(self, client, db, program_env):
        worker = program_env["worker"]
        resp = await client.post(
            "/api/v1/nora-program/deliverables",
            json={"stage_no": 3, "title": "Interview notes with DGA liaison"},
            headers=auth_headers(worker),
        )
        assert resp.status_code == 201
        did = resp.json()["id"]
        assert resp.json()["built_in"] is False

        resp = await client.delete(
            f"/api/v1/nora-program/deliverables/{did}", headers=auth_headers(worker)
        )
        assert resp.status_code == 204

    async def test_builtin_cannot_be_deleted(self, client, db, program_env):
        worker = program_env["worker"]
        data = (await client.get("/api/v1/nora-program", headers=auth_headers(worker))).json()
        target = data["stages"][1]["deliverables"][0]
        resp = await client.delete(
            f"/api/v1/nora-program/deliverables/{target['id']}", headers=auth_headers(worker)
        )
        assert resp.status_code == 400

    async def test_member_without_manage_cannot_update(self, client, db, program_env):
        member = await create_user(db, email="m2@test.com", role="member")
        await db.flush()
        data = (await client.get("/api/v1/nora-program", headers=auth_headers(member))).json()
        target = data["stages"][1]["deliverables"][0]
        resp = await client.patch(
            f"/api/v1/nora-program/deliverables/{target['id']}",
            json={"status": "inProgress"},
            headers=auth_headers(member),
        )
        assert resp.status_code == 403


class TestImprovementOpportunities:
    async def test_crud_and_initiative_assignment(self, client, db, program_env):
        admin = program_env["admin"]
        await create_card_type(db, key="Application", label="Application")
        await create_card_type(db, key="Initiative", label="Initiative")
        app_card = await create_card(db, card_type="Application", name="Legacy ECM")
        initiative = await create_card(db, card_type="Initiative", name="Shared Services Wave 2")
        await db.flush()

        resp = await client.post(
            "/api/v1/improvement-opportunities",
            json={
                "title": "Consolidate ECM platforms",
                "domain": "AA",
                "priority": "high",
                "card_ids": [str(app_card.id)],
            },
            headers=auth_headers(admin),
        )
        assert resp.status_code == 201
        opp = resp.json()
        assert opp["status"] == "proposed"
        assert opp["cards"][0]["name"] == "Legacy ECM"

        # Approving, then assigning the initiative flips it to inTransition.
        resp = await client.patch(
            f"/api/v1/improvement-opportunities/{opp['id']}",
            json={"status": "approved"},
            headers=auth_headers(admin),
        )
        assert resp.json()["status"] == "approved"
        resp = await client.patch(
            f"/api/v1/improvement-opportunities/{opp['id']}",
            json={"initiative_id": str(initiative.id)},
            headers=auth_headers(admin),
        )
        body = resp.json()
        assert body["status"] == "inTransition"
        assert body["initiative"]["name"] == "Shared Services Wave 2"

        # List + filters.
        resp = await client.get(
            "/api/v1/improvement-opportunities?domain=AA&status=inTransition",
            headers=auth_headers(admin),
        )
        assert len(resp.json()) == 1

        resp = await client.delete(
            f"/api/v1/improvement-opportunities/{opp['id']}", headers=auth_headers(admin)
        )
        assert resp.status_code == 204

    async def test_invalid_domain_rejected(self, client, db, program_env):
        resp = await client.post(
            "/api/v1/improvement-opportunities",
            json={"title": "X", "domain": "XX"},
            headers=auth_headers(program_env["admin"]),
        )
        assert resp.status_code == 400


class TestServiceTraceability:
    async def test_layers_grouped_by_category(self, client, db, program_env):
        admin = program_env["admin"]
        await create_card_type(
            db, key="GovService", label="Government Service", category="Business Architecture"
        )
        await create_card_type(
            db, key="Application", label="Application", category="Application & Data"
        )
        await create_card_type(
            db, key="ITComponent", label="IT Component", category="Technical Architecture"
        )
        from tests.conftest import create_relation, create_relation_type

        await create_relation_type(
            db,
            key="relGovServiceToApp",
            label="is delivered by",
            source_type_key="GovService",
            target_type_key="Application",
        )
        await create_relation_type(
            db,
            key="relAppToITC",
            label="uses",
            source_type_key="Application",
            target_type_key="ITComponent",
        )
        service = await create_card(db, card_type="GovService", name="Issue Licence")
        app = await create_card(db, card_type="Application", name="Licensing System")
        itc = await create_card(db, card_type="ITComponent", name="PostgreSQL")
        await create_relation(
            db, type_key="relGovServiceToApp", source_id=service.id, target_id=app.id
        )
        await create_relation(db, type_key="relAppToITC", source_id=app.id, target_id=itc.id)
        await db.flush()

        resp = await client.get(
            f"/api/v1/reports/service-traceability?card_id={service.id}",
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["root"]["name"] == "Issue Licence"
        by_cat = {layer["category"]: layer["cards"] for layer in data["layers"]}
        assert [c["name"] for c in by_cat["Application & Data"]] == ["Licensing System"]
        # The IT component is two hops away.
        tech = by_cat["Technical Architecture"][0]
        assert tech["name"] == "PostgreSQL"
        assert tech["hops"] == 2


class TestAdrCommitteeFields:
    async def test_committee_fields_roundtrip(self, client, db, program_env):
        admin = program_env["admin"]
        resp = await client.post(
            "/api/v1/adr",
            json={
                "title": "Adopt national GSB for external exchanges",
                "committee": "EA Governance Committee",
                "meeting_date": "2026-07-01",
                "stage_no": 7,
            },
            headers=auth_headers(admin),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["committee"] == "EA Governance Committee"
        assert body["meeting_date"] == "2026-07-01"
        assert body["stage_no"] == 7
