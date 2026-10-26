"""``/reports/executive/governance`` and the GOV-03 drill-down (Batch 3.1).

Aggregates need the executive permission (D-03); a card the caller cannot read
changes no count (D-01/D-30); the drill-down list needs ``tech_standards.view``.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.app_settings import AppSettings
from app.models.card_type import CardType
from app.models.governance_transition import GovernanceTransition
from app.models.tech_standard import StandardException, TechStandard
from app.services.permission_service import PermissionService
from tests.conftest import (
    auth_headers,
    create_card,
    create_card_type,
    create_relation,
    create_role,
    create_user,
)

BASE = "/api/v1/reports/executive"


async def _settings(db, **general):
    row = (
        await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    ).scalar_one_or_none()
    if row is None:
        db.add(AppSettings(id="default", general_settings=general))
    else:
        row.general_settings = {**(row.general_settings or {}), **general}
    await db.flush()


async def _deny_view(db, type_key: str, role_key: str) -> None:
    ct = (await db.execute(select(CardType).where(CardType.key == type_key))).scalar_one()
    ct.role_permissions = {**(ct.role_permissions or {}), role_key: {"inventory.view": False}}
    await db.flush()
    PermissionService.invalidate_type_permission_cache()


@pytest.fixture
async def env(db):
    await create_role(db, key="admin", permissions={"*": True})
    await create_role(
        db,
        key="exec",
        label="Exec",
        permissions={
            "reports.executive_dashboard": True,
            "inventory.view": True,
            "tech_standards.view": True,
        },
        is_system=False,
    )
    await create_role(
        db,
        key="exec_notech",
        label="Exec no tech",
        permissions={"reports.executive_dashboard": True, "inventory.view": True},
        is_system=False,
    )
    await create_role(
        db, key="plain", label="Plain", permissions={"inventory.view": True}, is_system=False
    )
    admin = await create_user(db, email="admin@test.com", role="admin")
    executive = await create_user(db, email="exec@test.com", role="exec")
    exec_notech = await create_user(db, email="nt@test.com", role="exec_notech")
    plain = await create_user(db, email="plain@test.com", role="plain")

    await create_card_type(db, key="TechCategory", label="Tech Category")
    await create_card_type(db, key="ITComponent", label="IT Component")
    await create_card_type(db, key="Application", label="Application")
    await create_card_type(db, key="Secret", label="Secret")
    await _settings(db, grcEnabled=True, fiscalYearStart=1)

    cat = await create_card(db, card_type="TechCategory", name="Messaging")
    itc = await create_card(db, card_type="ITComponent", name="OldMQ")
    app = await create_card(db, card_type="Application", name="Billing")
    await create_relation(db, type_key="relITCToTechCat", source_id=itc.id, target_id=cat.id)
    await create_relation(db, type_key="relAppToITC", source_id=app.id, target_id=itc.id)
    std = TechStandard(
        name="Legacy SOAP", category="integration", status="prohibited", tech_category_id=cat.id
    )
    db.add(std)
    await db.flush()

    hidden = await create_card(db, card_type="Secret", name="Zephyr Programme")
    seen = StandardException(standard_id=std.id, card_id=app.id, status="requested")
    unseen = StandardException(standard_id=std.id, card_id=hidden.id, status="requested")
    decided = StandardException(standard_id=std.id, card_id=app.id, status="approved")
    decided_hidden = StandardException(standard_id=std.id, card_id=hidden.id, status="approved")
    db.add_all([seen, unseen, decided, decided_hidden])
    await db.flush()
    for exc in (decided, decided_hidden):
        db.add(
            GovernanceTransition(
                instrument="exception",
                record_id=exc.id,
                from_status="requested",
                to_status="approved",
            )
        )
    await db.flush()
    await _deny_view(db, "Secret", "exec")
    return {
        "admin": admin,
        "exec": executive,
        "exec_notech": exec_notech,
        "plain": plain,
        "hidden": hidden,
    }


async def _get(client, user, path):
    return await client.get(f"{BASE}{path}", headers=auth_headers(user))


async def test_needs_the_executive_permission(client, env):
    assert (await _get(client, env["plain"], "/governance")).status_code == 403


async def test_three_sections_and_compliance_are_present(client, env):
    body = (await _get(client, env["admin"], "/governance")).json()
    assert set(body) >= {"activity", "effectiveness", "impact", "period", "generated_at"}
    assert body["effectiveness"]["compliance"]["status"] == "ok"
    # Compliance and coverage are two distinct figures.
    assert "coverage" in body["effectiveness"]
    assert body["effectiveness"]["coverage"]["status"] == "ok"


async def test_a_hidden_card_is_absent_from_every_count(client, env):
    admin_body = (await _get(client, env["admin"], "/governance")).json()
    exec_body = (await _get(client, env["exec"], "/governance")).json()
    # Admin sees both requested exceptions; exec cannot read the Secret card.
    assert admin_body["activity"]["exceptions"]["requested"] == 2
    assert exec_body["activity"]["exceptions"]["requested"] == 1
    # The hidden card never appears in the exec payload.
    assert "Zephyr Programme" not in (await _get(client, env["exec"], "/governance")).text
    assert str(env["hidden"].id) not in (await _get(client, env["exec"], "/governance")).text


async def test_drilldown_needs_tech_standards_view(client, env):
    denied = await _get(client, env["exec_notech"], "/kpi/GOV-03/drilldown")
    assert denied.status_code == 403
    allowed = await _get(client, env["exec"], "/kpi/GOV-03/drilldown")
    assert allowed.status_code == 200
    body = allowed.json()
    assert body["key"] == "GOV-03"
    # The non-compliant cards behind the gap are listed.
    assert any(r["card_name"] == "Billing" for r in body["rows"])


async def test_invalid_period_is_422(client, env):
    assert (await _get(client, env["admin"], "/governance?period=BOGUS")).status_code == 422


async def test_gov07_elapsed_ignores_a_hidden_cards_exception(client, env):
    admin = (await _get(client, env["admin"], "/governance")).json()
    exe = (await _get(client, env["exec"], "/governance")).json()
    a = admin["effectiveness"]["turnaround"]["instruments"]["exception"]
    e = exe["effectiveness"]["turnaround"]["instruments"]["exception"]
    assert a["decisions"] == 2
    assert e["decisions"] == 1
    assert exe["effectiveness"]["turnaround"]["processing_time"]["status"] == "not_available"
