"""``metricKey`` on the paths that synchronise data in (decision D-26).

ServiceNow pull and platform-migration apply write card attributes directly,
many cards in one transaction. They apply the same rule as every other write
path through ``kpi_metric_link.guard_inbound``: a refused link is reverted on
its own and reported, the rest of the record lands, and the unique index is
never reached — so one bad value cannot abort the whole run.
"""

from __future__ import annotations

import pytest

from app.models.card import Card
from app.models.migration import StagedRecord
from app.models.servicenow import SnowStagedRecord
from app.services import kpi_metric_link as link
from app.services.migration import apply as ap
from app.services.servicenow_service import SyncEngine
from tests.conftest import create_card, create_card_type, create_role, create_user
from tests.migration_helpers import make_migration


@pytest.fixture
async def env(db):
    await create_role(db, key="admin", permissions={"*": True})
    await create_role(
        db, key="integrator", label="Integrator", permissions={"servicenow.manage": True}
    )
    await create_card_type(db, key="KPI", label="KPI")
    await create_card_type(db, key="Application", label="Application")
    admin = await create_user(db, email="admin@test.com", role="admin")
    integrator = await create_user(db, email="int@test.com", role="integrator")
    holder = await create_card(
        db, card_type="KPI", name="Holder", attributes={"metricKey": "TR-03"}
    )
    return {"admin": admin, "integrator": integrator, "holder": holder}


# ── The shared helper ────────────────────────────────────────────────────


async def test_a_valid_link_is_kept(db, env):
    attrs = {"metricKey": " DEC-01 ", "unit": "%"}
    note = await link.guard_inbound(db, card_type="KPI", new_attributes=attrs, user=env["admin"])
    assert note is None
    assert attrs == {"metricKey": "DEC-01", "unit": "%"}


@pytest.mark.parametrize("key", ["NOT-A-METRIC", "TR-03"])
async def test_an_unknown_or_taken_key_is_dropped_from_a_new_card(db, env, key):
    attrs = {"metricKey": key, "unit": "%"}
    note = await link.guard_inbound(db, card_type="KPI", new_attributes=attrs, user=env["admin"])
    assert note is not None and note.startswith("metric link not applied")
    assert attrs == {"unit": "%"}


async def test_a_refused_change_goes_back_to_the_cards_own_link(db, env):
    attrs = {"metricKey": "TR-03"}
    note = await link.guard_inbound(
        db,
        card_type="KPI",
        new_attributes=attrs,
        old_attributes={"metricKey": "DEC-01"},
        card_id=None,
        user=env["admin"],
    )
    assert note is not None
    assert attrs == {"metricKey": "DEC-01"}


async def test_the_run_owner_needs_metamodel_administration(db, env):
    attrs = {"metricKey": "DEC-01"}
    note = await link.guard_inbound(
        db, card_type="KPI", new_attributes=attrs, user=env["integrator"]
    )
    assert note is not None and "metamodel administration" in note
    assert "metricKey" not in attrs


async def test_other_types_and_inactive_cards_are_left_alone(db, env):
    app_attrs = {"metricKey": "NOT-A-METRIC"}
    assert await link.guard_inbound(db, card_type="Application", new_attributes=app_attrs) is None
    assert app_attrs == {"metricKey": "NOT-A-METRIC"}
    archived = {"metricKey": "TR-03"}
    assert (
        await link.guard_inbound(db, card_type="KPI", new_attributes=archived, status="ARCHIVED")
        is None
    )
    assert archived == {"metricKey": "TR-03"}


# ── Platform migration (LeanIX) ──────────────────────────────────────────


async def _stage(db, migration, source_id, payload, **kw):
    row = StagedRecord(
        migration_id=migration.id,
        source_type="inmem",
        entity_kind="card",
        source_id=source_id,
        source_data={"payload": payload},
        action=kw.pop("action", "create"),
        **kw,
    )
    db.add(row)
    await db.flush()
    return row


async def test_migration_lands_the_card_without_a_taken_link(db, env):
    migration = await make_migration(db, user=env["admin"])
    ok = await _stage(
        db,
        migration,
        "K1",
        {"type": "KPI", "name": "Escalations", "attributes": {"metricKey": "DEC-01"}},
    )
    dup = await _stage(
        db,
        migration,
        "K2",
        {
            "type": "KPI",
            "name": "Second delivery",
            "external_id": "lx-42",
            "attributes": {"metricKey": "TR-03", "unit": "%"},
        },
    )

    counts = await ap._apply_card_pass(db, migration, env["admin"])

    assert counts["created"] == 2 and counts["errors"] == 0
    assert (ok.status, ok.error_message) == ("applied", None)
    assert dup.status == "applied"
    assert dup.error_message.startswith("metric link not applied")
    first = await db.get(Card, ok.target_id)
    second = await db.get(Card, dup.target_id)
    assert first.attributes == {"metricKey": "DEC-01"}
    assert second.attributes == {"unit": "%"}
    assert second.external_id == "lx-42"


async def test_migration_update_keeps_the_cards_link(db, env):
    migration = await make_migration(db, user=env["admin"])
    card = await create_card(
        db, card_type="KPI", name="Escalations", attributes={"metricKey": "DEC-01"}
    )
    staged = await _stage(
        db,
        migration,
        "K3",
        {"attributes": {"metricKey": "TR-03", "unit": "count"}},
        action="update",
        target_id=card.id,
    )

    await ap._apply_single_card(db, staged, env["admin"])

    assert card.attributes == {"metricKey": "DEC-01", "unit": "count"}
    assert staged.error_message.startswith("metric link not applied")


# ── ServiceNow ───────────────────────────────────────────────────────────


async def test_servicenow_update_keeps_the_cards_link_and_the_rest_of_the_record(db, env):
    card = await create_card(
        db, card_type="KPI", name="Escalations", attributes={"metricKey": "DEC-01"}
    )
    staged = SnowStagedRecord(
        sync_run_id=None,
        mapping_id=None,
        snow_sys_id="sys-kpi-1",
        snow_data={},
        card_id=card.id,
        action="update",
        status="pending",
        diff={
            "attributes.metricKey": {"old": "DEC-01", "new": "TR-03"},
            "attributes.unit": {"old": None, "new": "count"},
        },
    )
    engine = SyncEngine(db, client=None)

    await engine._apply_update(staged, [], env["admin"].id)
    await db.flush()

    assert card.attributes == {"metricKey": "DEC-01", "unit": "count"}
    assert staged.error_message.startswith("metric link not applied")


async def test_servicenow_update_accepts_a_free_registered_key(db, env):
    card = await create_card(db, card_type="KPI", name="Escalations", attributes={})
    staged = SnowStagedRecord(
        sync_run_id=None,
        mapping_id=None,
        snow_sys_id="sys-kpi-2",
        snow_data={},
        card_id=card.id,
        action="update",
        status="pending",
        diff={"attributes.metricKey": {"old": None, "new": "DEC-01"}},
    )
    engine = SyncEngine(db, client=None)

    await engine._apply_update(staged, [], env["admin"].id)

    assert card.attributes == {"metricKey": "DEC-01"}
    assert staged.error_message is None
