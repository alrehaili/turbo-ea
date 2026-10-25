"""``/kpis`` — measurement history, verification and target ratification, and
the KPI ``metricKey`` on the card write paths (D-19, D-17a, D-26)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.card_type import CardType
from app.models.stakeholder import Stakeholder
from tests.conftest import (
    auth_headers,
    create_card,
    create_card_type,
    create_role,
    create_stakeholder_role_def,
    create_user,
)

BASE = "/api/v1/kpis"


@pytest.fixture
async def env(db):
    await create_role(db, key="admin", permissions={"*": True})
    await create_role(
        db,
        key="analyst",
        label="Analyst",
        permissions={"inventory.view": True, "inventory.edit": True, "kpis.measure": True},
        is_system=False,
    )
    await create_role(
        db,
        key="checker",
        label="Checker",
        permissions={"inventory.view": True, "kpis.measure": True, "kpis.verify": True},
        is_system=False,
    )
    await create_role(
        db, key="reader", label="Reader", permissions={"inventory.view": True}, is_system=False
    )
    await create_card_type(db, key="KPI", label="KPI")
    # The built-in owner role: full card rights, but not target ratification.
    await create_stakeholder_role_def(
        db,
        card_type_key="KPI",
        key="responsible",
        permissions={"card.view": True, "card.edit": True, "card.ratify_kpi_target": False},
    )
    # The smallest extension (D-17a): an admin-defined approver role on the KPI type.
    await create_stakeholder_role_def(
        db,
        card_type_key="KPI",
        key="kpiTargetApprover",
        label="KPI target approver",
        permissions={"card.view": True, "card.ratify_kpi_target": True},
    )
    admin = await create_user(db, email="admin@test.com", role="admin")
    analyst = await create_user(db, email="analyst@test.com", role="analyst")
    checker = await create_user(db, email="checker@test.com", role="checker")
    reader = await create_user(db, email="reader@test.com", role="reader")
    kpi = await create_card(
        db,
        card_type="KPI",
        name="Uptake",
        attributes={"targetValue": 80, "baselineValue": 40, "direction": "higherIsBetter"},
    )
    return {"admin": admin, "analyst": analyst, "checker": checker, "reader": reader, "kpi": kpi}


async def _post(client, user, path, body):
    return await client.post(f"{BASE}{path}", json=body, headers=auth_headers(user))


async def test_record_needs_kpis_measure(client, env):
    kid = env["kpi"].id
    body = {"period_key": "FY2025-Q4", "value": 55}
    assert (await _post(client, env["reader"], f"/{kid}/measurements", body)).status_code == 403
    r = await _post(client, env["analyst"], f"/{kid}/measurements", body)
    assert r.status_code == 201 and r.json()["status"] == "submitted"
    # A second first value is refused; it has to be a correction.
    assert (await _post(client, env["analyst"], f"/{kid}/measurements", body)).status_code == 409
    bad = {"period_key": "FY2025-Q4", "value": "NaN"}
    assert (await _post(client, env["analyst"], f"/{kid}/measurements", bad)).status_code == 422


async def test_verify_needs_kpis_verify_and_another_person(client, env):
    kid = env["kpi"].id
    m = (
        await _post(
            client, env["checker"], f"/{kid}/measurements", {"period_key": "FY2025-Q4", "value": 55}
        )
    ).json()
    path = f"/measurements/{m['id']}/verify"
    assert (await _post(client, env["analyst"], path, {})).status_code == 403  # no kpis.verify
    assert (await _post(client, env["checker"], path, {})).status_code == 403  # own row
    r = await _post(client, env["admin"], path, {})
    assert r.status_code == 200 and r.json()["status"] == "verified" and r.json()["frozen"] is True


async def test_correction_supersedes_and_keeps_the_original(client, env):
    kid = env["kpi"].id
    m = (
        await _post(
            client, env["analyst"], f"/{kid}/measurements", {"period_key": "FY2025-Q4", "value": 55}
        )
    ).json()
    path = f"/measurements/{m['id']}/corrections"
    assert (await _post(client, env["analyst"], path, {"value": 57})).status_code == 422  # reason
    r = await _post(client, env["analyst"], path, {"value": 57, "reason": "Late data"})
    assert r.status_code == 201 and r.json()["supersedes_id"] == m["id"]
    perf = (
        await client.get(f"{BASE}/{kid}/performance", headers=auth_headers(env["reader"]))
    ).json()
    statuses = sorted((x["value"], x["status"]) for x in perf["measurements"])
    assert statuses == [(55.0, "superseded"), (57.0, "submitted")]
    assert perf["can_measure"] is False and perf["can_ratify"] is False


async def test_hidden_kpi_type_does_not_exist_for_the_reader(client, db, env):
    kpi_type = (await db.execute(select(CardType).where(CardType.key == "KPI"))).scalar_one()
    kpi_type.role_permissions = {"reader": {"inventory.view": False}}
    await db.flush()
    from app.services.permission_service import PermissionService

    PermissionService.invalidate_type_permission_cache()
    r = await client.get(f"{BASE}/{env['kpi'].id}/performance", headers=auth_headers(env["reader"]))
    assert r.status_code == 404


async def test_ratification_needs_the_approver_authority_not_the_owner_role(client, db, env):
    kid = env["kpi"].id
    owner = env["analyst"]
    db.add(Stakeholder(card_id=kid, user_id=owner.id, role="responsible"))
    await db.flush()
    assert (await _post(client, owner, f"/{kid}/target-ratifications", {})).status_code == 403

    approver = await create_user(db, email="approver@test.com", role="reader")
    db.add(Stakeholder(card_id=kid, user_id=approver.id, role="kpiTargetApprover"))
    await db.flush()
    r = await _post(client, approver, f"/{kid}/target-ratifications", {"note": "Minute 12"})
    assert r.status_code == 201 and r.json()["status"] == "ratified"
    assert r.json()["value"] == 80.0

    # Changing the target makes it unratified again.
    env["kpi"].attributes = {**env["kpi"].attributes, "targetValue": 90}
    await db.flush()
    perf = (await client.get(f"{BASE}/{kid}/performance", headers=auth_headers(owner))).json()
    assert perf["target"]["status"] == "unratified" and perf["target"]["invalidated"] is True


async def test_metric_history_is_withheld_from_a_restricted_reader(client, db, env):
    await create_role(
        db,
        key="exec",
        label="Exec",
        permissions={"reports.executive_dashboard": True},
        is_system=False,
    )
    executive = await create_user(db, email="exec@test.com", role="exec")
    kpi_type = (await db.execute(select(CardType).where(CardType.key == "KPI"))).scalar_one()
    kpi_type.role_permissions = {"exec": {"inventory.view": False}}
    await db.flush()
    from app.services.permission_service import PermissionService

    PermissionService.invalidate_type_permission_cache()
    r = await client.get(f"{BASE}/metrics/TR-03/history", headers=auth_headers(executive))
    assert r.json() == {"metric_key": "TR-03", "status": "restricted", "periods": [], "daily": []}
    r = await client.get(f"{BASE}/metrics/TR-03/history", headers=auth_headers(env["admin"]))
    assert r.json()["status"] == "ok"
    assert (
        await client.get(f"{BASE}/metrics/NOPE/history", headers=auth_headers(env["admin"]))
    ).status_code == 404
    assert (
        await client.get(f"{BASE}/metrics/TR-03/history", headers=auth_headers(env["reader"]))
    ).status_code == 403


# ── metricKey on the card write paths (D-26) ─────────────────────────────


async def test_patch_card_metric_key_needs_metamodel_admin(client, env):
    kid = env["kpi"].id
    attrs = {**env["kpi"].attributes, "metricKey": "TR-03"}
    r = await client.patch(
        f"/api/v1/cards/{kid}", json={"attributes": attrs}, headers=auth_headers(env["analyst"])
    )
    assert r.status_code == 403
    r = await client.patch(
        f"/api/v1/cards/{kid}", json={"attributes": attrs}, headers=auth_headers(env["admin"])
    )
    assert r.status_code == 200 and r.json()["attributes"]["metricKey"] == "TR-03"
    # An unrelated edit of the linked card by the analyst still works.
    r = await client.patch(
        f"/api/v1/cards/{kid}",
        json={"attributes": {**attrs, "unit": "%"}},
        headers=auth_headers(env["analyst"]),
    )
    assert r.status_code == 200


async def test_bulk_create_refuses_a_duplicate_metric_key(client, db, env):
    await create_card(db, card_type="KPI", name="Linked", attributes={"metricKey": "DEC-01"})
    r = await client.post(
        "/api/v1/cards/bulk-create",
        json={
            "cards": [
                {
                    "row_index": 0,
                    "type": "KPI",
                    "name": "Dup",
                    "attributes": {"metricKey": "DEC-01"},
                }
            ]
        },
        headers=auth_headers(env["admin"]),
    )
    body = r.json()
    assert r.status_code in (200, 201) and body["created"] == 0
    assert body["results"][0]["status"] == "failed" and "DEC-01" in body["results"][0]["error"]


async def test_bulk_update_cannot_put_one_key_on_two_cards(client, db, env):
    other = await create_card(db, card_type="KPI", name="Other")
    r = await client.patch(
        "/api/v1/cards/bulk",
        json={
            "ids": [str(env["kpi"].id), str(other.id)],
            "updates": {"attributes": {"metricKey": "TR-03"}},
        },
        headers=auth_headers(env["admin"]),
    )
    assert r.status_code == 409
