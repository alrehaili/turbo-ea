"""Integration tests for the deferred-backlog batch ([FORK]):
strategy-house settings (Strategic House viewpoint), and the TurboLens
duplicate/modernization → Improvement Opportunity promotions (WP3.3)."""

from __future__ import annotations

import pytest

from app.core.permissions import MEMBER_PERMISSIONS
from tests.conftest import auth_headers, create_card, create_card_type, create_role, create_user


@pytest.fixture
async def batch_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    admin = await create_user(db, email="admin@test.com", role="admin")
    member = await create_user(db, email="member@test.com", role="member")
    await db.flush()
    return {"admin": admin, "member": member}


class TestStrategyHouse:
    async def test_roundtrip_and_admin_gate(self, client, db, batch_env):
        admin, member = batch_env["admin"], batch_env["member"]

        resp = await client.get("/api/v1/settings/strategy-house", headers=auth_headers(member))
        assert resp.status_code == 200
        assert resp.json() == {"vision": "", "mission": ""}

        resp = await client.patch(
            "/api/v1/settings/strategy-house",
            json={"vision": "A digital-first agency", "mission": "Serve every beneficiary"},
            headers=auth_headers(member),
        )
        assert resp.status_code == 403

        resp = await client.patch(
            "/api/v1/settings/strategy-house",
            json={"vision": "A digital-first agency", "mission": "Serve every beneficiary"},
            headers=auth_headers(admin),
        )
        assert resp.status_code == 200
        body = (
            await client.get("/api/v1/settings/strategy-house", headers=auth_headers(member))
        ).json()
        assert body["vision"] == "A digital-first agency"
        assert body["mission"] == "Serve every beneficiary"


class TestTurboLensPromotions:
    async def test_cluster_promotes_to_opportunity(self, client, db, batch_env):
        from app.models.turbolens import TurboLensDuplicateCluster

        await create_card_type(db, key="Application", label="Application")
        a = await create_card(db, card_type="Application", name="Legacy DMS A")
        b = await create_card(db, card_type="Application", name="Legacy DMS B")
        cluster = TurboLensDuplicateCluster(
            cluster_name="Document management",
            card_type="Application",
            functional_domain="Content management",
            card_ids=[str(a.id), str(b.id)],
            card_names=["Legacy DMS A", "Legacy DMS B"],
            evidence="Same functional scope",
            recommendation="Consolidate onto one platform",
        )
        db.add(cluster)
        await db.flush()

        resp = await client.post(
            f"/api/v1/turbolens/duplicates/{cluster.id}/promote-opportunity",
            headers=auth_headers(batch_env["admin"]),
        )
        assert resp.status_code == 201
        opp_id = resp.json()["id"]

        rows = (
            await client.get(
                "/api/v1/improvement-opportunities", headers=auth_headers(batch_env["admin"])
            )
        ).json()
        opp = next(o for o in rows if o["id"] == opp_id)
        assert opp["source"] == "turbolens_duplicate"
        assert opp["status"] == "proposed"
        assert {c["name"] for c in opp["cards"]} == {"Legacy DMS A", "Legacy DMS B"}

    async def test_modernization_promotes_to_opportunity(self, client, db, batch_env):
        from app.models.turbolens import TurboLensModernization

        await create_card_type(db, key="ITComponent", label="IT Component")
        comp = await create_card(db, card_type="ITComponent", name="Oracle 11g")
        m = TurboLensModernization(
            target_type="ITComponent",
            card_id=comp.id,
            card_name="Oracle 11g",
            current_tech="Oracle 11g on-premise",
            modernization_type="database_upgrade",
            recommendation="Move to a supported managed database",
            effort="high",
            priority="high",
        )
        db.add(m)
        await db.flush()

        resp = await client.post(
            f"/api/v1/turbolens/duplicates/modernizations/{m.id}/promote-opportunity",
            headers=auth_headers(batch_env["admin"]),
        )
        assert resp.status_code == 201

        rows = (
            await client.get(
                "/api/v1/improvement-opportunities?domain=TA",
                headers=auth_headers(batch_env["admin"]),
            )
        ).json()
        assert len(rows) == 1
        assert rows[0]["source"] == "turbolens_modernization"
        assert rows[0]["priority"] == "high"
        assert rows[0]["cards"][0]["name"] == "Oracle 11g"

    async def test_promotion_requires_manage_permissions(self, client, db, batch_env):
        from app.models.turbolens import TurboLensDuplicateCluster

        cluster = TurboLensDuplicateCluster(
            cluster_name="X", card_type="Application", card_ids=[], card_names=[]
        )
        db.add(cluster)
        await db.flush()
        # Member lacks turbolens.manage.
        resp = await client.post(
            f"/api/v1/turbolens/duplicates/{cluster.id}/promote-opportunity",
            headers=auth_headers(batch_env["member"]),
        )
        assert resp.status_code == 403


class TestStrategyCascade:
    async def test_full_chain_and_unaligned_flag(self, client, db, batch_env):
        from tests.conftest import create_relation, create_relation_type

        await create_card_type(db, key="Pillar", label="Strategic Pillar", built_in=True)
        await create_card_type(db, key="Objective", label="Objective", built_in=True)
        await create_card_type(db, key="Initiative", label="Initiative", built_in=True)
        await create_relation_type(
            db,
            key="relInitiativeToObjective",
            label="supports",
            source_type_key="Initiative",
            target_type_key="Objective",
        )
        await create_relation_type(
            db,
            key="relObjectiveToPillar",
            label="supports",
            source_type_key="Objective",
            target_type_key="Pillar",
        )

        # First-class Pillar card (profile v6) with a relation-linked objective.
        pillar = await create_card(
            db,
            card_type="Pillar",
            name="Digital Government",
            attributes={"pillarCode": "P1", "pillarOrder": 1},
        )
        objective = await create_card(db, card_type="Objective", name="Paperless services by 2028")
        await create_relation(
            db,
            type_key="relObjectiveToPillar",
            source_id=objective.id,
            target_id=pillar.id,
        )
        # Legacy path: an Objective-subtype pillar with a child objective.
        legacy_pillar = await create_card(
            db, card_type="Objective", name="Legacy Pillar", subtype="pillar"
        )
        await create_card(
            db, card_type="Objective", name="Legacy Objective", parent_id=legacy_pillar.id
        )
        program = await create_card(
            db, card_type="Initiative", name="Service Digitization Program", subtype="program"
        )
        initiative = await create_card(
            db, card_type="Initiative", name="Licensing Wave 1", parent_id=program.id
        )
        await create_card(
            db,
            card_type="Initiative",
            name="Portal Relaunch",
            subtype="project",
            parent_id=initiative.id,
        )
        stray = await create_card(
            db, card_type="Initiative", name="Shadow Project", subtype="project"
        )
        await create_relation(
            db,
            type_key="relInitiativeToObjective",
            source_id=program.id,
            target_id=objective.id,
        )
        await db.flush()

        resp = await client.get(
            "/api/v1/reports/strategy-cascade", headers=auth_headers(batch_env["admin"])
        )
        assert resp.status_code == 200
        data = resp.json()

        # Pillar → objective → program → initiative → project, fully nested.
        p = next(x for x in data["pillars"] if x["name"] == "Digital Government")
        o = next(x for x in p["objectives"] if x["name"] == "Paperless services by 2028")
        prog = next(x for x in o["initiatives"] if x["name"] == "Service Digitization Program")
        assert prog["subtype"] == "program"
        init = prog["children"][0]
        assert init["name"] == "Licensing Wave 1"
        assert init["children"][0]["name"] == "Portal Relaunch"
        assert init["children"][0]["subtype"] == "project"

        # The legacy Objective-subtype pillar keeps working alongside.
        lp = next(x for x in data["pillars"] if x["name"] == "Legacy Pillar")
        assert [x["name"] for x in lp["objectives"]] == ["Legacy Objective"]

        # The stray project is flagged; the aligned chain is not.
        unaligned_names = {n["name"] for n in data["unaligned_initiatives"]}
        assert unaligned_names == {"Shadow Project"}
        assert data["summary"]["unaligned"] == 1
        assert data["summary"]["pillars"] == 2
        assert data["summary"]["programs"] == 1
        assert data["summary"]["projects"] == 2

        # The stray disappears once its chain is linked.
        await create_relation(
            db,
            type_key="relInitiativeToObjective",
            source_id=stray.id,
            target_id=objective.id,
        )
        await db.flush()
        data = (
            await client.get(
                "/api/v1/reports/strategy-cascade", headers=auth_headers(batch_env["admin"])
            )
        ).json()
        assert data["summary"]["unaligned"] == 0
