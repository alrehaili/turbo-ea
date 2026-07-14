"""Integration tests for the Technology Landscape report ([FORK] — noraPlan.md
WP6.3 + WP6.4: data-center containment + network segments + security flags)."""

from __future__ import annotations

import pytest

from tests.conftest import auth_headers, create_card, create_card_type, create_role, create_user


@pytest.fixture
async def landscape_env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    admin = await create_user(db, email="admin@test.com", role="admin")
    await create_card_type(db, key="ITComponent", label="IT Component", category="Technology")

    dc = await create_card(db, card_type="ITComponent", name="Riyadh DC", subtype="dataCenter")
    host = await create_card(
        db,
        card_type="ITComponent",
        name="ESX Host 01",
        subtype="physicalHost",
        parent_id=dc.id,
        attributes={"networkSegment": "core"},
    )
    vm = await create_card(
        db,
        card_type="ITComponent",
        name="App VM 12",
        subtype="virtualServer",
        parent_id=host.id,
        attributes={"networkSegment": "core"},
    )
    fw = await create_card(
        db,
        card_type="ITComponent",
        name="Perimeter Firewall",
        subtype="securityHardware",
        attributes={"networkSegment": "dmz"},
    )
    await db.flush()
    return {"admin": admin, "dc": dc, "host": host, "vm": vm, "fw": fw}


class TestTechnologyLandscape:
    async def test_dc_containment_and_segments(self, client, db, landscape_env):
        resp = await client.get(
            "/api/v1/reports/technology-landscape",
            headers=auth_headers(landscape_env["admin"]),
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["summary"]["total"] == 4
        assert data["summary"]["data_centers"] == 1
        assert data["summary"]["security_components"] == 1

        # The containment chain DC ⊃ host ⊃ VM with depth markers.
        dc = data["data_centers"][0]
        assert dc["name"] == "Riyadh DC"
        chain = [(c["name"], c["depth"]) for c in dc["components"]]
        assert chain == [("ESX Host 01", 1), ("App VM 12", 2)]

        # The firewall hangs under no DC and is flagged as security.
        unassigned = {c["name"]: c for c in data["unassigned"]}
        assert unassigned["Perimeter Firewall"]["security"] is True

        # Network segments group by the Technical Specification field.
        segments = {s["segment"]: [c["name"] for c in s["components"]] for s in data["segments"]}
        assert set(segments) == {"core", "dmz"}
        assert sorted(segments["core"]) == ["App VM 12", "ESX Host 01"]
        assert segments["dmz"] == ["Perimeter Firewall"]

    async def test_requires_report_permission(self, client, db, landscape_env):
        from app.core.permissions import VIEWER_PERMISSIONS

        no_reports = {**VIEWER_PERMISSIONS, "reports.ea_dashboard": False}
        await create_role(db, key="norep", label="No Reports", permissions=no_reports)
        user = await create_user(db, email="norep@test.com", role="norep")
        await db.flush()
        resp = await client.get("/api/v1/reports/technology-landscape", headers=auth_headers(user))
        assert resp.status_code == 403
