"""Integration tests for the EA maturity self-assessment API
([FORK] — noraPlan.md WP5.2)."""

from __future__ import annotations

import pytest

from app.core.permissions import MEMBER_PERMISSIONS
from app.services.maturity import DEFAULT_MATURITY_DIMENSIONS, seed_maturity_dimensions
from tests.conftest import auth_headers, create_role, create_user


@pytest.fixture
async def maturity_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    await create_role(
        db,
        key="ea_working_team",
        label="EA Working Team",
        permissions={
            **MEMBER_PERMISSIONS,
            "maturity.view": True,
            "maturity.manage": True,
            "grc.manage": True,
        },
    )
    admin = await create_user(db, email="admin@test.com", role="admin")
    worker = await create_user(db, email="worker@test.com", role="ea_working_team")
    await seed_maturity_dimensions(db)
    await db.flush()
    return {"admin": admin, "worker": worker}


class TestMaturityDimensions:
    async def test_seed_and_list(self, client, db, maturity_env):
        resp = await client.get(
            "/api/v1/maturity/dimensions", headers=auth_headers(maturity_env["worker"])
        )
        assert resp.status_code == 200
        assert len(resp.json()) == len(DEFAULT_MATURITY_DIMENSIONS)

    async def test_seed_idempotent(self, db, maturity_env):
        assert await seed_maturity_dimensions(db) == 0

    async def test_custom_dimension_lifecycle(self, client, db, maturity_env):
        worker = maturity_env["worker"]
        resp = await client.post(
            "/api/v1/maturity/dimensions",
            json={"name": "Cloud Adoption", "weight": 2},
            headers=auth_headers(worker),
        )
        assert resp.status_code == 201
        did = resp.json()["id"]
        assert resp.json()["built_in"] is False

        resp = await client.delete(
            f"/api/v1/maturity/dimensions/{did}", headers=auth_headers(worker)
        )
        assert resp.status_code == 204

    async def test_builtin_cannot_be_deleted(self, client, db, maturity_env):
        worker = maturity_env["worker"]
        dims = (
            await client.get("/api/v1/maturity/dimensions", headers=auth_headers(worker))
        ).json()
        resp = await client.delete(
            f"/api/v1/maturity/dimensions/{dims[0]['id']}", headers=auth_headers(worker)
        )
        assert resp.status_code == 400


class TestMaturityAssessments:
    async def test_create_seeds_scores_per_dimension(self, client, db, maturity_env):
        resp = await client.post(
            "/api/v1/maturity/assessments",
            json={"title": "2026 Baseline"},
            headers=auth_headers(maturity_env["worker"]),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "draft"
        assert len(body["scores"]) == len(DEFAULT_MATURITY_DIMENSIONS)
        assert all(s["level"] == 0 for s in body["scores"])

    async def test_score_update_and_submit_computes_overall(self, client, db, maturity_env):
        worker = maturity_env["worker"]
        a = (
            await client.post(
                "/api/v1/maturity/assessments",
                json={"title": "Baseline"},
                headers=auth_headers(worker),
            )
        ).json()
        aid = a["id"]
        # Score two dimensions.
        for score, level in zip(a["scores"][:2], (4, 2)):
            r = await client.patch(
                f"/api/v1/maturity/assessments/{aid}/scores/{score['id']}",
                json={"level": level, "target_level": 5},
                headers=auth_headers(worker),
            )
            assert r.status_code == 200

        r = await client.patch(
            f"/api/v1/maturity/assessments/{aid}",
            json={"status": "submitted"},
            headers=auth_headers(worker),
        )
        assert r.status_code == 200
        # (4 + 2) / (5 * 2) * 100 = 60.0 — unscored rows ignored.
        assert r.json()["overall_score"] == 60.0

    async def test_approval_requires_governance(self, client, db, maturity_env):
        worker, admin = maturity_env["worker"], maturity_env["admin"]
        a = (
            await client.post(
                "/api/v1/maturity/assessments",
                json={"title": "Baseline"},
                headers=auth_headers(worker),
            )
        ).json()
        # Worker manages but lacks governance.approve_step.
        r = await client.patch(
            f"/api/v1/maturity/assessments/{a['id']}",
            json={"status": "approved"},
            headers=auth_headers(worker),
        )
        assert r.status_code == 403
        # Admin wildcard approves.
        r = await client.patch(
            f"/api/v1/maturity/assessments/{a['id']}",
            json={"status": "approved"},
            headers=auth_headers(admin),
        )
        assert r.status_code == 200
        assert r.json()["approved_by"] is not None

    async def test_promote_score_to_opportunity(self, client, db, maturity_env):
        worker = maturity_env["worker"]
        a = (
            await client.post(
                "/api/v1/maturity/assessments",
                json={"title": "Baseline"},
                headers=auth_headers(worker),
            )
        ).json()
        score = a["scores"][0]
        await client.patch(
            f"/api/v1/maturity/assessments/{a['id']}/scores/{score['id']}",
            json={"level": 1, "target_level": 4},
            headers=auth_headers(worker),
        )
        r = await client.post(
            f"/api/v1/maturity/assessments/{a['id']}/scores/{score['id']}/promote-opportunity",
            json={"domain": "BA", "priority": "high"},
            headers=auth_headers(worker),
        )
        assert r.status_code == 201
        assert r.json()["source"] == "maturity"

        # It shows up in the opportunity registry.
        opps = (
            await client.get("/api/v1/improvement-opportunities", headers=auth_headers(worker))
        ).json()
        assert any(o["source"] == "maturity" for o in opps)

    async def test_member_without_manage_cannot_create(self, client, db, maturity_env):
        member = await create_user(db, email="m2@test.com", role="member")
        await db.flush()
        r = await client.post(
            "/api/v1/maturity/assessments",
            json={"title": "X"},
            headers=auth_headers(member),
        )
        assert r.status_code == 403


class TestMaturityOverview:
    async def test_overview_radar_and_trend(self, client, db, maturity_env):
        worker = maturity_env["worker"]
        a = (
            await client.post(
                "/api/v1/maturity/assessments",
                json={"title": "Baseline", "assessment_date": "2026-01-01"},
                headers=auth_headers(worker),
            )
        ).json()
        for score, level in zip(a["scores"][:3], (3, 4, 2)):
            await client.patch(
                f"/api/v1/maturity/assessments/{a['id']}/scores/{score['id']}",
                json={"level": level, "target_level": 5},
                headers=auth_headers(worker),
            )
        await client.patch(
            f"/api/v1/maturity/assessments/{a['id']}",
            json={"status": "submitted"},
            headers=auth_headers(worker),
        )

        resp = await client.get("/api/v1/maturity/overview", headers=auth_headers(worker))
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["assessments"] == 1
        assert len(data["radar"]) == len(DEFAULT_MATURITY_DIMENSIONS)
        assert len(data["trend"]) == 1
        assert data["trend"][0]["overall_score"] is not None
        # Three dimensions scored below their target of 5.
        assert data["summary"]["below_target"] == 3
