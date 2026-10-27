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
from tests.conftest import create_card, create_card_type, create_relation, create_role, create_user

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


# ── GOV-03 daily capture (Batch 3.1, I-13) ───────────────────────────────


async def _governed_landscape(db):
    from app.models.tech_standard import TechStandard

    await create_card_type(db, key="TechCategory", label="Tech Category")
    await create_card_type(db, key="ITComponent", label="IT Component")
    await create_card_type(db, key="Application", label="Application")
    cat = await create_card(db, card_type="TechCategory", name="Messaging")
    itc = await create_card(db, card_type="ITComponent", name="OldMQ")
    app = await create_card(db, card_type="Application", name="Billing")
    await create_relation(db, type_key="relITCToTechCat", source_id=itc.id, target_id=cat.id)
    await create_relation(db, type_key="relAppToITC", source_id=app.id, target_id=itc.id)
    db.add(
        TechStandard(
            name="Legacy SOAP", category="integration", status="prohibited", tech_category_id=cat.id
        )
    )
    await db.flush()


async def test_gov03_is_observed_when_the_population_can_be_assessed(db, env):
    await _governed_landscape(db)
    observed = await svc.observe_executive_metrics(db, TODAY)
    assert "GOV-03" in observed
    gov = observed["GOV-03"]
    # Two assessed cards, both violating → 0 % compliant.
    assert gov.value == 0.0
    assert gov.numerator == 0.0
    assert gov.denominator == 2.0


async def test_gov03_is_not_observed_when_nothing_is_assessable(db, env):
    # No technology standard governs any category, so there is nothing to record.
    observed = await svc.observe_executive_metrics(db, TODAY)
    assert "GOV-03" not in observed


# ── GOV-05 daily capture and period value (Batch 3.4, D-41) ──────────────


async def _decision(db, author, due, verified_at=None):
    import uuid as _uuid
    from datetime import datetime, timezone

    from app.models.architecture_decision import ArchitectureDecision
    from app.models.decision_implementation import DecisionImplementation

    adr = ArchitectureDecision(
        reference_number=f"ADR-{_uuid.uuid4().hex[:6]}",
        title="Decision",
        status="signed",
        created_by=author.id,
        signed_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        signatories=[],
    )
    db.add(adr)
    await db.flush()
    db.add(
        DecisionImplementation(
            decision_kind="adr",
            decision_id=adr.id,
            status="verified" if verified_at else "open",
            due_date=due,
            original_due_date=due,
            due_date_basis="with_decision",
            verified_at=verified_at,
        )
    )
    await db.flush()


async def test_gov05_is_observed_for_the_current_quarter_only_when_decisions_are_due(db, env):
    observed = await svc.observe_executive_metrics(db, TODAY)
    # Nothing due in FY2026-Q4 yet: no value, never a zero.
    assert "GOV-05" not in observed
    await _decision(db, env["admin"], date(2026, 10, 10))
    observed = await svc.observe_executive_metrics(db, TODAY)
    gov = observed["GOV-05"]
    assert (gov.value, gov.numerator, gov.denominator) == (0.0, 0.0, 1.0)


async def test_gov05_period_value_is_calculated_for_the_period_not_the_last_observation(db, env):
    from datetime import datetime, timezone

    await _decision(
        db,
        env["admin"],
        date(2026, 8, 15),
        verified_at=datetime(2026, 8, 10, tzinfo=timezone.utc),
    )
    # The capture ran in Q3; whatever it observed, the closed value is Q3's own.
    await svc._store_daily(db, "GOV-05", date(2026, 9, 1), svc.Observation(0.0, 0, 1))
    await db.flush()
    await svc.close_ended_periods(db, TODAY)
    q3 = await svc.current_period_value(db, "FY2026-Q3", metric_key="GOV-05")
    assert (q3.value, q3.numerator, q3.denominator) == (100.0, 1.0, 1.0)
    assert q3.observed_on == date(2026, 9, 30)
    assert q3.status == STATUS_SUBMITTED and q3.calculation_version == "GOV-05@1"
    # A quarter the capture never ran in gets no value (nothing invented).
    assert await svc.current_period_value(db, "FY2026-Q2", metric_key="GOV-05") is None


# ── RSK-01 daily capture (Batch 3.5, D-42) ───────────────────────────────


async def test_rsk01_is_observed_only_when_a_governance_link_exists(db, env):
    import uuid as _uuid
    from datetime import datetime, timezone

    from app.models.architecture_decision import ArchitectureDecision
    from app.services import risk_governance as rg
    from tests.conftest import create_risk

    await create_risk(db, title="Unlinked")
    assert "RSK-01" not in await svc.observe_executive_metrics(db, TODAY)
    adr = ArchitectureDecision(
        reference_number=f"ADR-{_uuid.uuid4().hex[:6]}",
        title="Decision",
        status="signed",
        signed_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        signatories=[],
    )
    db.add(adr)
    await db.flush()
    linked = await create_risk(db, title="Linked")
    closed = await create_risk(db, title="Closed", status="closed")
    info = (await rg.describe(db, {("adr", adr.id)}))[("adr", adr.id)]
    for risk in (linked, closed):
        await rg.link(db, risk, info, env["admin"].id)
    rsk = (await svc.observe_executive_metrics(db, TODAY))["RSK-01"]
    # Open architecture-related risks over all linked ones; the unlinked risk is not counted.
    assert (rsk.value, rsk.numerator, rsk.denominator) == (1.0, None, 2.0)


# ── GOV-01 daily capture (Batch 3.6, D-37) ───────────────────────────────


async def test_gov01_is_observed_only_when_an_initiative_requires_review(db, env):
    from app.models.arb_review import ArbReview
    from app.models.ea_review_applicability import EaReviewApplicability

    await create_card_type(db, key="Initiative", label="Initiative")
    reviewed = await create_card(db, card_type="Initiative", name="Reviewed")
    waiting = await create_card(db, card_type="Initiative", name="Waiting")
    assert "GOV-01" not in await svc.observe_executive_metrics(db, TODAY)
    for card in (reviewed, waiting):
        db.add(
            EaReviewApplicability(
                card_id=card.id, decision="required", criteria_reference="v1", justification="x"
            )
        )
    db.add(ArbReview(title="Review", subject_card_id=reviewed.id, status="approved"))
    await db.flush()
    gov = (await svc.observe_executive_metrics(db, TODAY))["GOV-01"]
    assert (gov.value, gov.numerator, gov.denominator) == (50.0, 1.0, 2.0)
