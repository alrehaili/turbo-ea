"""Integration tests for the NORA EA Program tracker and Improvement
Opportunity registry ([FORK] — noraPlan.md WP3.1 / WP3.3)."""

from __future__ import annotations

import pytest

from app.core.permissions import MEMBER_PERMISSIONS
from app.services.nora_program import (
    NORA_DELIVERABLE_CATALOGUE,
    NORA_V2_DELIVERABLE_CATALOGUE,
    seed_nora_program,
)
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


class TestMethodologyV2:
    """WP6.1 — 7-phase methodology switch + per-domain deliverables."""

    async def test_switch_to_v2_seeds_and_filters(self, client, db, program_env):
        admin, worker = program_env["admin"], program_env["worker"]

        # Working-team manage is not enough — switching is an admin act.
        resp = await client.post(
            "/api/v1/nora-program/methodology",
            json={"version": "v2"},
            headers=auth_headers(worker),
        )
        assert resp.status_code == 403

        resp = await client.post(
            "/api/v1/nora-program/methodology",
            json={"version": "v2"},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        assert resp.json()["deliverables_seeded"] == len(NORA_V2_DELIVERABLE_CATALOGUE)

        data = (await client.get("/api/v1/nora-program", headers=auth_headers(worker))).json()
        assert data["methodology"] == "v2"
        # Phases 1–7 only; the v1 rows are retained but not returned.
        assert [s["stage_no"] for s in data["stages"]] == list(range(1, 8))
        assert data["summary"]["total"] == len(NORA_V2_DELIVERABLE_CATALOGUE)
        # Phase 2 carries the per-domain deliverables with domain tokens.
        phase2 = next(s for s in data["stages"] if s["stage_no"] == 2)
        domains = {d["domain"] for d in phase2["deliverables"]}
        assert domains == {
            "business",
            "beneficiaryExperience",
            "applications",
            "data",
            "technology",
            "security",
        }
        assert len(phase2["deliverables"]) == 24
        # Cycle-level deliverables carry no domain.
        phase1 = next(s for s in data["stages"] if s["stage_no"] == 1)
        assert all(d["domain"] is None for d in phase1["deliverables"])

        # Switching back restores the v1 view untouched (history preserved).
        resp = await client.post(
            "/api/v1/nora-program/methodology",
            json={"version": "v1"},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        data = (await client.get("/api/v1/nora-program", headers=auth_headers(worker))).json()
        assert data["methodology"] == "v1"
        assert data["summary"]["total"] == len(NORA_DELIVERABLE_CATALOGUE)

    async def test_v2_custom_deliverable_scoped_to_v2(self, client, db, program_env):
        admin, worker = program_env["admin"], program_env["worker"]
        await client.post(
            "/api/v1/nora-program/methodology",
            json={"version": "v2"},
            headers=auth_headers(admin),
        )
        # Stage 0 was a v1 concept — invalid under v2.
        resp = await client.post(
            "/api/v1/nora-program/deliverables",
            json={"stage_no": 0, "title": "Continuous governance extra"},
            headers=auth_headers(worker),
        )
        assert resp.status_code == 400

        resp = await client.post(
            "/api/v1/nora-program/deliverables",
            json={"stage_no": 3, "title": "Regional benchmark study"},
            headers=auth_headers(worker),
        )
        assert resp.status_code == 201
        assert resp.json()["key"].startswith("custom_v2_")

        # The v2 custom row disappears from the v1 view after switching back.
        await client.post(
            "/api/v1/nora-program/methodology",
            json={"version": "v1"},
            headers=auth_headers(admin),
        )
        data = (await client.get("/api/v1/nora-program", headers=auth_headers(worker))).json()
        all_keys = {d["key"] for s in data["stages"] for d in s["deliverables"]}
        assert not any(k.startswith("custom_v2_") for k in all_keys)

    async def test_v2_seed_is_idempotent(self, client, db, program_env):
        admin = program_env["admin"]
        await client.post(
            "/api/v1/nora-program/methodology",
            json={"version": "v2"},
            headers=auth_headers(admin),
        )
        assert await seed_nora_program(db, methodology="v2") == 0


class TestPracticeChecklist:
    """WP6.8 — the pre-methodology practice-establishment checklist."""

    async def test_practice_block_seeded_and_separate(self, client, db, program_env):
        from app.services.nora_program import (
            PRACTICE_CHECKLIST_CATALOGUE,
            seed_practice_checklist,
        )

        assert await seed_practice_checklist(db) == len(PRACTICE_CHECKLIST_CATALOGUE)
        assert await seed_practice_checklist(db) == 0  # idempotent

        worker = program_env["worker"]
        data = (await client.get("/api/v1/nora-program", headers=auth_headers(worker))).json()
        practice = data["practice"]
        assert len(practice["deliverables"]) == 10
        assert {d["key"] for d in practice["deliverables"]} == {
            k for k, _ in PRACTICE_CHECKLIST_CATALOGUE
        }
        # Practice rows never pollute the methodology summary or stages.
        assert data["summary"]["total"] == len(NORA_DELIVERABLE_CATALOGUE)
        all_stage_keys = {d["key"] for s in data["stages"] for d in s["deliverables"]}
        assert not any(k.startswith("practice_") for k in all_stage_keys)

        # Status updates work through the ordinary deliverable endpoint.
        row = practice["deliverables"][0]
        resp = await client.patch(
            f"/api/v1/nora-program/deliverables/{row['id']}",
            json={"status": "inProgress"},
            headers=auth_headers(worker),
        )
        assert resp.status_code == 200

    async def test_practice_visible_under_v2_too(self, client, db, program_env):
        from app.services.nora_program import seed_practice_checklist

        await seed_practice_checklist(db)
        await client.post(
            "/api/v1/nora-program/methodology",
            json={"version": "v2"},
            headers=auth_headers(program_env["admin"]),
        )
        data = (
            await client.get("/api/v1/nora-program", headers=auth_headers(program_env["worker"]))
        ).json()
        assert len(data["practice"]["deliverables"]) == 10


class TestPracticeDocTypes:
    """WP6.8 — the operating-model artifacts are valid governed doc types."""

    async def test_practice_doc_type_roundtrip(self, client, db, program_env):
        admin = program_env["admin"]
        resp = await client.post(
            "/api/v1/soaw",
            json={"name": "EA Governance Model v1", "doc_type": "ea_governance_model"},
            headers=auth_headers(admin),
        )
        assert resp.status_code in (200, 201)
        body = resp.json()
        assert body["doc_type"] == "ea_governance_model"

        resp = await client.get(
            "/api/v1/soaw?doc_type=ea_governance_model", headers=auth_headers(admin)
        )
        assert len(resp.json()) == 1

        # Unknown doc types are still rejected.
        resp = await client.post(
            "/api/v1/soaw",
            json={"name": "Bad", "doc_type": "ea_nonexistent"},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 422


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

    async def test_journey_improvement_fields(self, client, db, program_env):
        """WP6.5 — BX/SEC domains + (journey, phase, feasibility) traceability."""
        admin = program_env["admin"]
        await create_card_type(db, key="BeneficiaryJourney", label="Beneficiary Journey")
        journey = await create_card(
            db, card_type="BeneficiaryJourney", name="Renew Commercial Licence"
        )
        await db.flush()

        resp = await client.post(
            "/api/v1/improvement-opportunities",
            json={
                "title": "Cut in-person visit from the renewal journey",
                "domain": "BX",
                "priority": "high",
                "journey_card_id": str(journey.id),
                "journey_phase": "Submit documents",
                "feasibility": "medium",
            },
            headers=auth_headers(admin),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["domain"] == "BX"
        assert body["journey"]["name"] == "Renew Commercial Licence"
        assert body["journey_phase"] == "Submit documents"
        assert body["feasibility"] == "medium"

        # SEC is a valid domain; a bogus feasibility is rejected.
        resp = await client.post(
            "/api/v1/improvement-opportunities",
            json={"title": "Harden the DMZ", "domain": "SEC"},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 201
        resp = await client.patch(
            f"/api/v1/improvement-opportunities/{body['id']}",
            json={"feasibility": "impossible"},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 400


class TestServiceTraceability:
    async def test_layers_grouped_by_category(self, client, db, program_env):
        admin = program_env["admin"]
        await create_card_type(
            db, key="GovService", label="Government Service", category="Beneficiary Experience"
        )
        await create_card_type(db, key="Application", label="Application", category="Application")
        await create_card_type(db, key="ITComponent", label="IT Component", category="Technology")
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
        assert [c["name"] for c in by_cat["Application"]] == ["Licensing System"]
        # The IT component is two hops away.
        tech = by_cat["Technology"][0]
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
