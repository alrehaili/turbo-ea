"""KPI history, target ratification and the metric link (D-19, D-17a, D-26)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.kpi_measurement import (
    KIND_DAILY,
    KIND_PERIOD,
    STATUS_SUBMITTED,
    STATUS_SUPERSEDED,
    STATUS_VERIFIED,
    KpiMeasurement,
)
from app.services import kpi_measurement_service as svc
from app.services import kpi_metric_link as link
from tests.conftest import create_card, create_card_type, create_role, create_user

TODAY = date(2026, 10, 25)


@pytest.fixture
async def env(db):
    await create_role(db, key="admin", permissions={"*": True})
    await create_role(
        db, key="member", label="Member", permissions={"inventory.view": True}, is_system=False
    )
    await create_card_type(db, key="KPI", label="KPI")
    alice = await create_user(db, email="alice@test.com", role="member")
    bob = await create_user(db, email="bob@test.com", role="member")
    admin = await create_user(db, email="admin@test.com", role="admin")
    kpi = await create_card(
        db,
        card_type="KPI",
        name="Digital services uptake",
        attributes={
            "targetValue": 80,
            "targetValueDate": "2027-12-31",
            "baselineValue": 40,
            "unit": "%",
            "direction": "higherIsBetter",
        },
    )
    return {"alice": alice, "bob": bob, "admin": admin, "kpi": kpi}


# ── Measurements: record, correct, verify, freeze ────────────────────────


async def test_record_then_a_second_value_is_a_correction(db, env):
    m = await svc.record_card_measurement(
        db,
        env["alice"],
        env["kpi"],
        period_key="FY2026-Q3",
        value=55,
        evidence="report.pdf",
        today=TODAY,
    )
    assert (m.kind, m.status, m.value, m.period_end) == (
        KIND_PERIOD,
        STATUS_SUBMITTED,
        55.0,
        date(2026, 9, 30),
    )
    assert m.recorded_by == env["alice"].id and m.source == "manual"
    with pytest.raises(HTTPException) as exc:
        await svc.record_card_measurement(
            db, env["bob"], env["kpi"], period_key="FY2026-Q3", value=60, evidence=None, today=TODAY
        )
    assert exc.value.status_code == 409


async def test_future_or_malformed_period_is_refused(db, env):
    for key in ("FY2030", "2026-Q1", "FY2026-Q5"):
        with pytest.raises(HTTPException) as exc:
            await svc.record_card_measurement(
                db, env["alice"], env["kpi"], period_key=key, value=1, evidence=None, today=TODAY
            )
        assert exc.value.status_code == 422


async def test_nobody_verifies_their_own_measurement(db, env):
    m = await svc.record_card_measurement(
        db, env["alice"], env["kpi"], period_key="FY2026-Q3", value=55, evidence=None, today=TODAY
    )
    with pytest.raises(HTTPException) as exc:
        await svc.verify_measurement(db, env["alice"], m)
    assert exc.value.status_code == 403 and m.status == STATUS_SUBMITTED
    await svc.verify_measurement(db, env["bob"], m)
    assert m.status == STATUS_VERIFIED and m.verified_by == env["bob"].id
    with pytest.raises(HTTPException):
        await svc.verify_measurement(db, env["admin"], m)  # verified once


async def test_correction_is_append_only_audited_and_needs_reverification(db, env):
    m = await svc.record_card_measurement(
        db, env["alice"], env["kpi"], period_key="FY2026-Q3", value=55, evidence=None, today=TODAY
    )
    await svc.verify_measurement(db, env["bob"], m)
    assert svc.is_frozen(m, TODAY)  # verified, and Q3 has ended
    with pytest.raises(HTTPException) as exc:
        await svc.correct_measurement(db, env["bob"], m, value=58, evidence=None, reason="  ")
    assert exc.value.status_code == 422

    fixed = await svc.correct_measurement(
        db, env["bob"], m, value=58, evidence=None, reason="Source report revised"
    )
    assert m.status == STATUS_SUPERSEDED and m.value == 55.0  # original kept, unchanged
    assert fixed.supersedes_id == m.id and fixed.status == STATUS_SUBMITTED
    assert fixed.correction_reason == "Source report revised"
    current = await svc.current_period_value(db, "FY2026-Q3", card_id=env["kpi"].id)
    assert current.id == fixed.id
    # The corrector cannot verify the correction; someone else can.
    with pytest.raises(HTTPException):
        await svc.verify_measurement(db, env["bob"], fixed)
    await svc.verify_measurement(db, env["alice"], fixed)
    # A superseded row can never be corrected again.
    with pytest.raises(HTTPException):
        await svc.correct_measurement(db, env["alice"], m, value=1, evidence=None, reason="x")
    history = await svc.card_history(db, env["kpi"].id)
    assert {h.status for h in history} == {STATUS_SUPERSEDED, STATUS_VERIFIED}


async def test_open_period_value_is_not_frozen(db, env):
    m = await svc.record_card_measurement(
        db, env["alice"], env["kpi"], period_key="FY2026-Q4", value=60, evidence=None, today=TODAY
    )
    await svc.verify_measurement(db, env["bob"], m)
    assert not svc.is_frozen(m, TODAY)
    assert svc.is_frozen(m, date(2027, 1, 1))


async def test_measurement_events_reach_the_card_history(db, env):
    from app.models.event import Event

    m = await svc.record_card_measurement(
        db, env["alice"], env["kpi"], period_key="FY2026-Q3", value=55, evidence=None, today=TODAY
    )
    await svc.verify_measurement(db, env["bob"], m)
    events = (await db.execute(select(Event).where(Event.card_id == env["kpi"].id))).scalars().all()
    assert {e.event_type for e in events} >= {
        "kpi.measurement_recorded",
        "kpi.measurement_verified",
    }


# ── Target ratification (D-17a) ──────────────────────────────────────────


async def test_target_states_and_invalidation_on_change(db, env):
    kpi = env["kpi"]
    assert (svc.target_state(kpi, None))["status"] == "unratified"
    r = await svc.ratify_target(db, env["admin"], kpi, note="Board minute 12")
    state = svc.target_state(kpi, r)
    assert state["status"] == "ratified" and state["value"] == 80.0
    assert r.target_value == 80.0 and r.direction == "higherIsBetter"
    with pytest.raises(HTTPException):
        await svc.ratify_target(db, env["admin"], kpi, note=None)  # already ratified

    for field, new in (("targetValue", 85), ("direction", "lowerIsBetter"), ("unit", "pts")):
        kpi.attributes = {**kpi.attributes, field: new}
        changed = svc.target_state(kpi, r)
        assert changed["status"] == "unratified" and changed["invalidated"] is True, field
        kpi.attributes = {
            **kpi.attributes,
            field: {"targetValue": 80, "direction": "higherIsBetter", "unit": "%"}[field],
        }
    assert svc.target_state(kpi, r)["status"] == "ratified"


async def test_no_target_cannot_be_ratified(db, env):
    kpi = await create_card(db, card_type="KPI", name="No target", attributes={})
    assert svc.target_state(kpi, None)["status"] == "none"
    with pytest.raises(HTTPException) as exc:
        await svc.ratify_target(db, env["admin"], kpi, note=None)
    assert exc.value.status_code == 422


# ── Daily observations and period close (I-2) ─────────────────────────────


async def test_period_value_is_the_last_observation_inside_the_period(db, env):
    for day, value in (
        (date(2026, 9, 28), 70.0),
        (date(2026, 9, 29), 72.0),
        (date(2026, 10, 2), 90.0),
    ):
        await svc._store_daily(db, "TR-03", day, svc.Observation(value, 7, 10))
    await db.flush()
    created = await svc.close_ended_periods(db, TODAY)
    q3 = await svc.current_period_value(db, "FY2026-Q3", metric_key="TR-03")
    assert q3.value == 72.0 and q3.observed_on == date(2026, 9, 29)
    assert q3.status == STATUS_SUBMITTED and q3.recorded_by is None and q3.source == "system"
    # Q4 and FY2026 have not ended: nothing recorded for them.
    assert await svc.current_period_value(db, "FY2026-Q4", metric_key="TR-03") is None
    assert await svc.current_period_value(db, "FY2026", metric_key="TR-03") is None
    assert created == 1
    assert await svc.close_ended_periods(db, TODAY) == 0  # idempotent
    # The system recorded it, so any verifier may verify it.
    await svc.verify_measurement(db, env["alice"], q3)


async def test_daily_observation_is_one_row_per_metric_per_day(db, env):
    day = TODAY - timedelta(days=1)
    await svc._store_daily(db, "DEC-01", day, svc.Observation(2.0))
    await svc._store_daily(db, "DEC-01", day, svc.Observation(3.0))
    await db.flush()
    rows = (
        (
            await db.execute(
                select(KpiMeasurement)
                .where(KpiMeasurement.kind == KIND_DAILY, KpiMeasurement.metric_key == "DEC-01")
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    assert [r.value for r in rows] == [3.0]
    with pytest.raises(HTTPException):
        await svc.correct_measurement(db, env["alice"], rows[0], value=1, evidence=None, reason="x")


# ── metricKey (D-26) ─────────────────────────────────────────────────────


async def test_metric_key_must_be_registered_unique_and_authorized(db, env):
    attrs = {"metricKey": " TR-03 "}
    await link.validate_metric_key(db, card_type="KPI", new_attributes=attrs, user=env["admin"])
    assert attrs["metricKey"] == "TR-03"  # normalised
    with pytest.raises(HTTPException) as exc:
        await link.validate_metric_key(
            db, card_type="KPI", new_attributes={"metricKey": "NOPE"}, user=env["admin"]
        )
    assert exc.value.status_code == 422
    with pytest.raises(HTTPException) as exc:
        await link.validate_metric_key(
            db, card_type="KPI", new_attributes={"metricKey": "TR-03"}, user=env["alice"]
        )
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException) as exc:
        await link.validate_metric_key(
            db, card_type="KPI", new_attributes={"metricKey": "TR-03"}, ext_key="acme"
        )
    assert exc.value.status_code == 403

    linked = await create_card(
        db, card_type="KPI", name="Linked", attributes={"metricKey": "TR-03"}
    )
    with pytest.raises(HTTPException) as exc:
        await link.validate_metric_key(
            db, card_type="KPI", new_attributes={"metricKey": "TR-03"}, user=env["admin"]
        )
    assert exc.value.status_code == 409
    # Re-sending the stored value needs no authority and is not a duplicate of itself.
    await link.validate_metric_key(
        db,
        card_type="KPI",
        new_attributes={"metricKey": "TR-03", "unit": "%"},
        old_attributes=linked.attributes,
        card_id=linked.id,
        user=env["alice"],
    )
    # Other types are not concerned.
    await link.validate_metric_key(
        db, card_type="Application", new_attributes={"metricKey": "NOPE"}, user=env["alice"]
    )


async def test_metric_key_uniqueness_is_enforced_by_the_database(db, env):
    await create_card(db, card_type="KPI", name="One", attributes={"metricKey": "DEC-01"})
    # An archived holder does not count.
    await create_card(
        db, card_type="KPI", name="Old", status="ARCHIVED", attributes={"metricKey": "DEC-01"}
    )
    sp = await db.begin_nested()
    with pytest.raises(IntegrityError):
        await create_card(db, card_type="KPI", name="Two", attributes={"metricKey": "DEC-01"})
    await sp.rollback()


async def test_restoring_a_card_whose_key_is_taken_is_refused(db, env):
    await create_card(db, card_type="KPI", name="Live", attributes={"metricKey": "TR-03"})
    old = await create_card(
        db, card_type="KPI", name="Old", status="ARCHIVED", attributes={"metricKey": "TR-03"}
    )
    assert await link.restore_conflict(db, old) == "TR-03"
