"""Integration tests for the ``/adm`` endpoints.

Follows the same shape as :mod:`tests.api.test_soaw`. Requires the test
Postgres — skipped automatically at fixture-setup time when the database
is not available (see ``tests/conftest.py::test_engine``).

[FORK FEATURE]
"""

from __future__ import annotations

import pytest

from app.core.permissions import MEMBER_PERMISSIONS, VIEWER_PERMISSIONS
from app.models.adm import AdmWorkspace
from app.models.soaw import SoAW
from tests.conftest import auth_headers, create_role, create_user


@pytest.fixture
async def adm_env(db):
    """Roles and users used by the ADM API tests."""
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    member_perms = dict(MEMBER_PERMISSIONS)
    # v1 defaults grant approve_gate to admin only for this test tenant; the
    # member role gets view + manage but not approve, so we can exercise
    # both the "authorized" and "not authorized" branches of the API.
    member_perms["adm.view"] = True
    member_perms["adm.manage"] = True
    member_perms["adm.approve_gate"] = False
    await create_role(db, key="member", label="Member", permissions=member_perms)
    await create_role(db, key="viewer", label="Viewer", permissions=VIEWER_PERMISSIONS)

    admin = await create_user(db, email="admin@adm.test", role="admin")
    member = await create_user(db, email="member@adm.test", role="member")
    viewer = await create_user(db, email="viewer@adm.test", role="viewer")

    soaw = SoAW(name="Test SoAW for ADM", status="draft", sections={})
    db.add(soaw)
    await db.flush()

    return {"admin": admin, "member": member, "viewer": viewer, "soaw": soaw}


# ---------------------------------------------------------------------------
# Workspace CRUD
# ---------------------------------------------------------------------------


class TestCreate:
    async def test_create_seeds_10_phases(self, client, adm_env):
        resp = await client.post(
            "/api/v1/adm/workspaces",
            json={"name": "Test WS", "soaw_id": str(adm_env["soaw"].id)},
            headers=auth_headers(adm_env["admin"]),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["phases"]) == 10
        assert body["soaw_id"] == str(adm_env["soaw"].id)
        # Requirements management is the continuous phase.
        continuous = [p for p in body["phases"] if p["is_continuous"]]
        assert len(continuous) == 1
        assert continuous[0]["phase_key"] == "requirements_management"

    async def test_rejects_missing_anchor(self, client, adm_env):
        resp = await client.post(
            "/api/v1/adm/workspaces",
            json={"name": "No anchor"},
            headers=auth_headers(adm_env["admin"]),
        )
        assert resp.status_code == 422

    async def test_viewer_forbidden(self, client, adm_env):
        resp = await client.post(
            "/api/v1/adm/workspaces",
            json={"name": "Test", "soaw_id": str(adm_env["soaw"].id)},
            headers=auth_headers(adm_env["viewer"]),
        )
        assert resp.status_code == 403

    async def test_one_workspace_per_soaw(self, client, adm_env):
        payload = {"name": "First", "soaw_id": str(adm_env["soaw"].id)}
        r1 = await client.post(
            "/api/v1/adm/workspaces", json=payload, headers=auth_headers(adm_env["admin"])
        )
        assert r1.status_code == 201
        r2 = await client.post(
            "/api/v1/adm/workspaces",
            json={**payload, "name": "Second"},
            headers=auth_headers(adm_env["admin"]),
        )
        assert r2.status_code == 409


class TestReadList:
    async def test_get_by_soaw_returns_ws(self, client, adm_env):
        await client.post(
            "/api/v1/adm/workspaces",
            json={"name": "WS", "soaw_id": str(adm_env["soaw"].id)},
            headers=auth_headers(adm_env["admin"]),
        )
        resp = await client.get(
            f"/api/v1/adm/workspaces/by-soaw/{adm_env['soaw'].id}",
            headers=auth_headers(adm_env["viewer"]),
        )
        assert resp.status_code == 200
        assert len(resp.json()["phases"]) == 10

    async def test_get_by_soaw_404(self, client, adm_env):
        resp = await client.get(
            f"/api/v1/adm/workspaces/by-soaw/{adm_env['soaw'].id}",
            headers=auth_headers(adm_env["viewer"]),
        )
        assert resp.status_code == 404

    async def test_list_rollup(self, client, adm_env):
        await client.post(
            "/api/v1/adm/workspaces",
            json={"name": "WS", "soaw_id": str(adm_env["soaw"].id)},
            headers=auth_headers(adm_env["admin"]),
        )
        resp = await client.get("/api/v1/adm/workspaces", headers=auth_headers(adm_env["viewer"]))
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 1
        assert rows[0]["phase_count"] == 10
        assert rows[0]["completion_pct"] == 0


# ---------------------------------------------------------------------------
# Gate workflow
# ---------------------------------------------------------------------------


class TestGateFlow:
    async def _make_ws(self, client, adm_env):
        r = await client.post(
            "/api/v1/adm/workspaces",
            json={"name": "WS", "soaw_id": str(adm_env["soaw"].id)},
            headers=auth_headers(adm_env["admin"]),
        )
        return r.json()

    async def _start_phase(self, client, adm_env, phase_id):
        """Fresh phases are ``not_started``; the gate only opens from ``in_progress``."""
        r = await client.patch(
            f"/api/v1/adm/phases/{phase_id}",
            json={"status": "in_progress"},
            headers=auth_headers(adm_env["admin"]),
        )
        assert r.status_code == 200, r.text

    async def test_mark_ready_blocks_from_not_started(self, client, adm_env):
        ws = await self._make_ws(client, adm_env)
        phase_a = next(p for p in ws["phases"] if p["phase_key"] == "phase_a")
        resp = await client.post(
            f"/api/v1/adm/phases/{phase_a['id']}/mark-ready",
            json={"override": True, "override_reason": "Board approved deferral"},
            headers=auth_headers(adm_env["admin"]),
        )
        assert resp.status_code == 422
        assert "not_started" in resp.json()["detail"]

    async def test_mark_ready_blocks_without_artefacts(self, client, adm_env):
        ws = await self._make_ws(client, adm_env)
        phase_a = next(p for p in ws["phases"] if p["phase_key"] == "phase_a")
        await self._start_phase(client, adm_env, phase_a["id"])
        # Phase A ships two required artefacts un-linked → mark-ready must
        # fail without override.
        resp = await client.post(
            f"/api/v1/adm/phases/{phase_a['id']}/mark-ready",
            json={},
            headers=auth_headers(adm_env["admin"]),
        )
        assert resp.status_code == 422

    async def test_mark_ready_override_ok(self, client, adm_env):
        ws = await self._make_ws(client, adm_env)
        phase_a = next(p for p in ws["phases"] if p["phase_key"] == "phase_a")
        await self._start_phase(client, adm_env, phase_a["id"])
        resp = await client.post(
            f"/api/v1/adm/phases/{phase_a['id']}/mark-ready",
            json={"override": True, "override_reason": "Board approved deferral"},
            headers=auth_headers(adm_env["admin"]),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "ready_for_gate"
        assert resp.json()["approval_override_reason"] == "Board approved deferral"

    async def test_member_cannot_approve(self, client, adm_env):
        ws = await self._make_ws(client, adm_env)
        phase_a = next(p for p in ws["phases"] if p["phase_key"] == "phase_a")
        await self._start_phase(client, adm_env, phase_a["id"])
        await client.post(
            f"/api/v1/adm/phases/{phase_a['id']}/mark-ready",
            json={"override": True, "override_reason": "Board approved deferral"},
            headers=auth_headers(adm_env["admin"]),
        )
        resp = await client.post(
            f"/api/v1/adm/phases/{phase_a['id']}/approve",
            json={},
            headers=auth_headers(adm_env["member"]),
        )
        assert resp.status_code == 403

    async def test_admin_can_approve(self, client, adm_env):
        ws = await self._make_ws(client, adm_env)
        phase_a = next(p for p in ws["phases"] if p["phase_key"] == "phase_a")
        await self._start_phase(client, adm_env, phase_a["id"])
        await client.post(
            f"/api/v1/adm/phases/{phase_a['id']}/mark-ready",
            json={"override": True, "override_reason": "Board approved deferral"},
            headers=auth_headers(adm_env["admin"]),
        )
        resp = await client.post(
            f"/api/v1/adm/phases/{phase_a['id']}/approve",
            json={"comment": "Approved at ARB 2026-07-04"},
            headers=auth_headers(adm_env["admin"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
        assert resp.json()["approval_comment"] == "Approved at ARB 2026-07-04"

    async def test_reopen_requires_reason(self, client, adm_env):
        ws = await self._make_ws(client, adm_env)
        phase_a = next(p for p in ws["phases"] if p["phase_key"] == "phase_a")
        # move to approved
        await self._start_phase(client, adm_env, phase_a["id"])
        await client.post(
            f"/api/v1/adm/phases/{phase_a['id']}/mark-ready",
            json={"override": True, "override_reason": "Board approved deferral"},
            headers=auth_headers(adm_env["admin"]),
        )
        await client.post(
            f"/api/v1/adm/phases/{phase_a['id']}/approve",
            json={},
            headers=auth_headers(adm_env["admin"]),
        )
        # short reason rejected
        r = await client.post(
            f"/api/v1/adm/phases/{phase_a['id']}/reopen",
            json={"reason": "no"},
            headers=auth_headers(adm_env["admin"]),
        )
        assert r.status_code == 422
        # long reason accepted
        r = await client.post(
            f"/api/v1/adm/phases/{phase_a['id']}/reopen",
            json={"reason": "Scope changed after ARB review"},
            headers=auth_headers(adm_env["admin"]),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    async def test_continuous_phase_cannot_be_marked_ready(self, client, adm_env):
        ws = await self._make_ws(client, adm_env)
        rm = next(p for p in ws["phases"] if p["phase_key"] == "requirements_management")
        resp = await client.post(
            f"/api/v1/adm/phases/{rm['id']}/mark-ready",
            json={"override": True, "override_reason": "Trying anyway"},
            headers=auth_headers(adm_env["admin"]),
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Artefacts
# ---------------------------------------------------------------------------


class TestArtefacts:
    async def test_link_url_artefact(self, client, adm_env, db):
        r = await client.post(
            "/api/v1/adm/workspaces",
            json={"name": "WS", "soaw_id": str(adm_env["soaw"].id)},
            headers=auth_headers(adm_env["admin"]),
        )
        phase = next(p for p in r.json()["phases"] if p["phase_key"] == "phase_a")

        resp = await client.post(
            f"/api/v1/adm/phases/{phase['id']}/artefacts",
            json={
                "kind": "url",
                "ref_url": "https://confluence.example.com/vision",
                "title": "Architecture Vision Draft",
            },
            headers=auth_headers(adm_env["admin"]),
        )
        assert resp.status_code == 201
        assert resp.json()["is_linked"] is True

    async def test_link_rejects_unknown_kind(self, client, adm_env):
        r = await client.post(
            "/api/v1/adm/workspaces",
            json={"name": "WS", "soaw_id": str(adm_env["soaw"].id)},
            headers=auth_headers(adm_env["admin"]),
        )
        phase = next(p for p in r.json()["phases"] if p["phase_key"] == "phase_a")
        resp = await client.post(
            f"/api/v1/adm/phases/{phase['id']}/artefacts",
            json={"kind": "bogus", "title": "Bad", "ref_id": None},
            headers=auth_headers(adm_env["admin"]),
        )
        assert resp.status_code == 422

    async def test_waive_requires_reason(self, client, adm_env):
        r = await client.post(
            "/api/v1/adm/workspaces",
            json={"name": "WS", "soaw_id": str(adm_env["soaw"].id)},
            headers=auth_headers(adm_env["admin"]),
        )
        phase = next(p for p in r.json()["phases"] if p["phase_key"] == "phase_a")
        artefact = phase["artefacts"][0]  # ships un-linked and required from seed
        resp = await client.post(
            f"/api/v1/adm/artefacts/{artefact['id']}/waive",
            json={"is_waived": True, "reason": "no"},
            headers=auth_headers(adm_env["admin"]),
        )
        assert resp.status_code == 422
        resp = await client.post(
            f"/api/v1/adm/artefacts/{artefact['id']}/waive",
            json={"is_waived": True, "reason": "Not applicable to this engagement"},
            headers=auth_headers(adm_env["admin"]),
        )
        assert resp.status_code == 200
        assert resp.json()["is_waived"] is True


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestDelete:
    async def test_cascade(self, client, adm_env, db):
        r = await client.post(
            "/api/v1/adm/workspaces",
            json={"name": "WS", "soaw_id": str(adm_env["soaw"].id)},
            headers=auth_headers(adm_env["admin"]),
        )
        ws_id = r.json()["id"]
        resp = await client.delete(
            f"/api/v1/adm/workspaces/{ws_id}", headers=auth_headers(adm_env["admin"])
        )
        assert resp.status_code == 204
        # SoAW row is untouched
        soaw_row = await db.get(SoAW, adm_env["soaw"].id)
        assert soaw_row is not None
        # Workspace and phases + artefacts gone
        ws_row = await db.get(AdmWorkspace, r.json()["id"])
        assert ws_row is None
