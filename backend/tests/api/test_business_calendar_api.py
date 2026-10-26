"""Business calendar administration over the API (D-38; Batch 3.3).

Only holders of ``admin.business_calendar`` read or change it; every write is
an admin audit record; a change to a confirmed year withdraws its confirmation.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.permissions import MEMBER_PERMISSIONS
from app.models.audit_log import AuditLogEntry
from tests.conftest import auth_headers, create_role, create_user

BASE = "/api/v1/business-calendar"


@pytest.fixture
async def env(db):
    await create_role(db, key="admin", label="Admin", permissions={"*": True})
    await create_role(db, key="member", label="Member", permissions=MEMBER_PERMISSIONS)
    admin = await create_user(db, email="cal-admin@test.com", role="admin")
    member = await create_user(db, email="cal-member@test.com", role="member")
    return {"admin": admin, "member": member}


async def _audit(db, action):
    await db.rollback()
    rows = await db.execute(select(AuditLogEntry).where(AuditLogEntry.action == action))
    return list(rows.scalars().all())


async def test_only_calendar_administrators_read_or_write(client, env):
    member = auth_headers(env["member"])
    assert (await client.get(BASE, headers=member)).status_code == 403
    assert (await client.put(f"{BASE}/2026", json={}, headers=member)).status_code == 403
    assert (await client.post(f"{BASE}/2026/confirm", headers=member)).status_code == 403


async def test_a_year_is_saved_with_the_default_week_and_audited(client, db, env):
    admin = auth_headers(env["admin"])
    resp = await client.put(
        f"{BASE}/2026",
        json={"holidays": [{"date": "2026-09-23", "name": "National Day"}]},
        headers=admin,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["working_weekdays"] == [7, 1, 2, 3, 4]
    assert body["holidays"] == [{"date": "2026-09-23", "name": "National Day"}]
    assert body["confirmed"] is False
    listed = (await client.get(BASE, headers=admin)).json()
    assert [y["fiscal_year"] for y in listed["years"]] == [2026]
    (row,) = await _audit(db, "admin.business_calendar.created")
    assert row.details["context"]["fiscal_year"] == "FY2026"


async def test_invalid_input_is_refused(client, env):
    admin = auth_headers(env["admin"])
    resp = await client.put(
        f"{BASE}/2026", json={"holidays": [{"date": "2027-01-05", "name": "x"}]}, headers=admin
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "holiday_outside_year"
    resp = await client.put(f"{BASE}/2026", json={"working_weekdays": []}, headers=admin)
    assert resp.json()["detail"]["code"] == "invalid_working_week"
    assert (await client.post(f"{BASE}/2030/confirm", headers=admin)).status_code == 404


async def test_confirming_then_editing_withdraws_the_confirmation(client, db, env):
    admin = auth_headers(env["admin"])
    await client.put(f"{BASE}/2026", json={}, headers=admin)
    resp = await client.post(f"{BASE}/2026/confirm", headers=admin)
    assert resp.json()["confirmed"] is True and resp.json()["confirmed_at"]
    resp = await client.put(
        f"{BASE}/2026",
        json={"holidays": [{"date": "2026-02-22", "name": "Founding"}]},
        headers=admin,
    )
    assert resp.json()["confirmed"] is False
    (row,) = await _audit(db, "admin.business_calendar.updated")
    assert row.details["changes"]["confirmed"] == {"old": True, "new": False}
    assert len(await _audit(db, "admin.business_calendar.confirmed")) == 1
