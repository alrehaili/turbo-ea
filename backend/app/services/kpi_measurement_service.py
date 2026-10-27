"""KPI measurement history and target ratification (decisions D-19, D-17a).

The rules every write path shares, kept out of the route module so they carry a
mutation score:

* **Append-only.** A period value is recorded once; every later change is a
  correction — a new row that supersedes the current one, with a reason — and
  the replaced row stays as ``superseded``. Nothing is updated in place except
  the status of the row being verified or superseded.
* **Separation of duties.** Recording or correcting needs ``kpis.measure``;
  verifying needs ``kpis.verify`` and is refused to the person who recorded
  that row (a value the system recorded may be verified by any verifier).
* **Frozen.** A verified value of a period that has ended can no longer be
  verified again or silently replaced; only an explicit correction, with a
  reason, supersedes it — and that correction needs verifying in turn.
* **Daily vs period.** Daily observations are what the daily capture saw and
  are never verified or corrected. A system metric's period value is the last
  daily observation inside the period, recorded after the period has closed
  (I-2): nothing is recomputed after the fact or backfilled.
* **Ratified targets.** A ratification records the KPI's target, target date,
  baseline, unit and direction as they stood; the target stays ratified only
  while the card still carries exactly those values (I-6 / D-17a).

Every recorded, corrected, verified or ratified value publishes an event with
``db=`` so it lands in the card's History tab (the audit trail).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSettings
from app.models.card import KPI_CARD_TYPE, Card
from app.models.kpi_measurement import (
    KIND_DAILY,
    KIND_PERIOD,
    STATUS_OBSERVED,
    STATUS_SUBMITTED,
    STATUS_SUPERSEDED,
    STATUS_VERIFIED,
    KpiMeasurement,
    KpiTargetRatification,
)
from app.models.risk import Risk
from app.models.user import User
from app.services import executive_dashboard as exe
from app.services import ppm_portfolio_service as portfolio
from app.services.card_read_scope import CardReadScope, visible_type_clause
from app.services.event_bus import event_bus
from app.services.executive import decisions as dec
from app.services.executive import periods
from app.services.executive.registry import METRICS, PERIOD_CALCULATED
from app.services.fiscal_year import (
    fiscal_quarter_bounds,
    fiscal_year_bounds,
    fiscal_year_for,
    get_fiscal_year_start,
)
from app.services.tech_standards_scan import assess_standard_compliance

CURRENT_STATUSES = (STATUS_SUBMITTED, STATUS_VERIFIED)
#: KPI card fields a ratification freezes; any change makes the target unratified.
RATIFIED_FIELDS = ("targetValue", "targetValueDate", "baselineValue", "unit", "direction")


def _today() -> date:
    return datetime.now(timezone.utc).date()


def is_frozen(m: KpiMeasurement, today: date | None = None) -> bool:
    """A verified value of a period that has ended."""
    return (
        m.kind == KIND_PERIOD and m.status == STATUS_VERIFIED and m.period_end < (today or _today())
    )


def period_type_of(period: periods.Period) -> str:
    return "quarter" if period.quarter else "fiscal_year"


async def parse_period(db: AsyncSession, key: str, today: date | None = None) -> periods.Period:
    """A started fiscal year or quarter, else 422."""
    start_month = await get_fiscal_year_start(db)
    try:
        return periods.parse(key, start_month, today or _today())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_text(value: Any) -> str | None:
    return None if value is None or value == "" else str(value)


async def require_kpi_card(db: AsyncSession, card_id: uuid.UUID) -> Card:
    """The KPI card, else 404 — also when the KPI type is hidden (I-5)."""
    card = (
        await db.execute(select(Card).where(Card.id == card_id, visible_type_clause(Card)))
    ).scalar_one_or_none()
    if card is None or card.type != KPI_CARD_TYPE:
        raise HTTPException(404, "KPI card not found")
    return card


# ── Reads ────────────────────────────────────────────────────────────────


async def card_history(db: AsyncSession, card_id: uuid.UUID) -> list[KpiMeasurement]:
    """Every measurement of a KPI card, newest period first, newest row first."""
    rows = await db.execute(
        select(KpiMeasurement)
        .where(KpiMeasurement.kpi_card_id == card_id)
        .order_by(KpiMeasurement.period_end.desc(), KpiMeasurement.recorded_at.desc())
    )
    return list(rows.scalars().all())


async def current_period_value(
    db: AsyncSession,
    period_key: str,
    *,
    card_id: uuid.UUID | None = None,
    metric_key: str | None = None,
) -> KpiMeasurement | None:
    """The current (not superseded) value of one subject for one period."""
    stmt = select(KpiMeasurement).where(
        KpiMeasurement.kind == KIND_PERIOD,
        KpiMeasurement.period_key == period_key,
        KpiMeasurement.status.in_(CURRENT_STATUSES),
    )
    if card_id is not None:
        stmt = stmt.where(KpiMeasurement.kpi_card_id == card_id)
    else:
        stmt = stmt.where(
            KpiMeasurement.metric_key == metric_key, KpiMeasurement.kpi_card_id.is_(None)
        )
    return (await db.execute(stmt)).scalar_one_or_none()


def measurement_to_dict(m: KpiMeasurement, today: date | None = None) -> dict[str, Any]:
    return {
        "id": str(m.id),
        "kind": m.kind,
        "metric_key": m.metric_key,
        "kpi_card_id": str(m.kpi_card_id) if m.kpi_card_id else None,
        "period_type": m.period_type,
        "period_key": m.period_key,
        "period_start": m.period_start.isoformat(),
        "period_end": m.period_end.isoformat(),
        "observed_on": m.observed_on.isoformat() if m.observed_on else None,
        "value": m.value,
        "numerator": m.numerator,
        "denominator": m.denominator,
        "unit": m.unit,
        "calculation_version": m.calculation_version,
        "source": m.source,
        "evidence": m.evidence,
        "status": m.status,
        "frozen": is_frozen(m, today),
        "recorded_by": str(m.recorded_by) if m.recorded_by else None,
        "recorded_at": m.recorded_at.isoformat() if m.recorded_at else None,
        "verified_by": str(m.verified_by) if m.verified_by else None,
        "verified_at": m.verified_at.isoformat() if m.verified_at else None,
        "supersedes_id": str(m.supersedes_id) if m.supersedes_id else None,
        "correction_reason": m.correction_reason,
    }


async def _publish(
    db: AsyncSession, event: str, m: KpiMeasurement, user_id: uuid.UUID | None, **extra: Any
) -> None:
    await event_bus.publish(
        event,
        {
            "measurement_id": str(m.id),
            "period_key": m.period_key,
            "metric_key": m.metric_key,
            "value": m.value,
            "status": m.status,
            **extra,
        },
        db=db,
        card_id=m.kpi_card_id,
        user_id=user_id,
    )


# ── Writes: record, correct, verify ──────────────────────────────────────


async def record_card_measurement(
    db: AsyncSession,
    user: User,
    card: Card,
    *,
    period_key: str,
    value: float,
    evidence: str | None,
    today: date | None = None,
) -> KpiMeasurement:
    """First value of a KPI card for a period. A second one is a correction."""
    if card.status != "ACTIVE":
        raise HTTPException(409, "An archived KPI card cannot be measured")
    period = await parse_period(db, period_key, today)
    if await current_period_value(db, period.key, card_id=card.id) is not None:
        raise HTTPException(409, "This period already has a value; record a correction instead")
    attrs = card.attributes or {}
    m = KpiMeasurement(
        kind=KIND_PERIOD,
        kpi_card_id=card.id,
        period_type=period_type_of(period),
        period_key=period.key,
        period_start=period.start,
        period_end=period.end - timedelta(days=1),
        value=float(value),
        unit=_as_text(attrs.get("unit")),
        source="manual",
        evidence=evidence or None,
        status=STATUS_SUBMITTED,
        recorded_by=user.id,
    )
    db.add(m)
    await db.flush()
    await _publish(db, "kpi.measurement_recorded", m, user.id)
    return m


async def correct_measurement(
    db: AsyncSession,
    user: User,
    current: KpiMeasurement,
    *,
    value: float,
    evidence: str | None,
    reason: str,
) -> KpiMeasurement:
    """Supersede a period value with a corrected one (append-only, audited)."""
    if current.kind != KIND_PERIOD:
        raise HTTPException(409, "Daily observations are not corrected")
    if current.status not in CURRENT_STATUSES:
        raise HTTPException(409, "Only the current value of a period can be corrected")
    reason = (reason or "").strip()
    if not reason:
        raise HTTPException(422, "A correction needs a reason")
    was_frozen = is_frozen(current)
    current.status = STATUS_SUPERSEDED
    await db.flush()
    m = KpiMeasurement(
        kind=KIND_PERIOD,
        metric_key=current.metric_key,
        kpi_card_id=current.kpi_card_id,
        period_type=current.period_type,
        period_key=current.period_key,
        period_start=current.period_start,
        period_end=current.period_end,
        value=float(value),
        unit=current.unit,
        calculation_version=current.calculation_version,
        source="manual",
        evidence=evidence or None,
        status=STATUS_SUBMITTED,
        recorded_by=user.id,
        supersedes_id=current.id,
        correction_reason=reason,
    )
    db.add(m)
    await db.flush()
    await _publish(
        db,
        "kpi.measurement_corrected",
        m,
        user.id,
        reason=reason,
        was_frozen=was_frozen,
        changes={"value": {"old": current.value, "new": m.value}},
    )
    return m


async def verify_measurement(db: AsyncSession, user: User, m: KpiMeasurement) -> KpiMeasurement:
    """Verify a submitted period value — never one the verifier recorded."""
    if m.kind != KIND_PERIOD or m.status != STATUS_SUBMITTED:
        raise HTTPException(409, "Only a submitted period value can be verified")
    if m.recorded_by is not None and m.recorded_by == user.id:
        raise HTTPException(403, "You cannot verify a measurement you recorded")
    m.status = STATUS_VERIFIED
    m.verified_by = user.id
    m.verified_at = datetime.now(timezone.utc)
    await db.flush()
    await _publish(db, "kpi.measurement_verified", m, user.id)
    return m


# ── Target ratification (D-17a) ──────────────────────────────────────────


def _target_snapshot(card: Card) -> dict[str, Any]:
    attrs = card.attributes or {}
    return {
        "target_value": _as_float(attrs.get("targetValue")),
        "target_date": _as_text(attrs.get("targetValueDate")),
        "baseline_value": _as_float(attrs.get("baselineValue")),
        "unit": _as_text(attrs.get("unit")),
        "direction": _as_text(attrs.get("direction")),
    }


async def latest_ratification(db: AsyncSession, card_id: uuid.UUID) -> KpiTargetRatification | None:
    rows = await db.execute(
        select(KpiTargetRatification)
        .where(KpiTargetRatification.kpi_card_id == card_id)
        .order_by(KpiTargetRatification.ratified_at.desc(), KpiTargetRatification.created_at.desc())
        .limit(1)
    )
    return rows.scalar_one_or_none()


def target_state(card: Card, ratification: KpiTargetRatification | None) -> dict[str, Any]:
    """``none`` (no target) / ``unratified`` / ``ratified``, with the target itself.

    A ratification stands only while every ratified field still matches the
    card; a changed target (or date, baseline, unit or direction) is
    ``unratified`` again, with ``invalidated`` telling the two cases apart.
    """
    snap = _target_snapshot(card)
    out: dict[str, Any] = {
        "value": snap["target_value"],
        "date": snap["target_date"],
        "baseline": snap["baseline_value"],
        "unit": snap["unit"],
        "direction": snap["direction"],
    }
    if snap["target_value"] is None:
        return out | {"status": "none", "invalidated": False}
    if ratification is None:
        return out | {"status": "unratified", "invalidated": False}
    ratified = {
        "target_value": ratification.target_value,
        "target_date": ratification.target_date,
        "baseline_value": ratification.baseline_value,
        "unit": ratification.unit,
        "direction": ratification.direction,
    }
    if ratified != snap:
        return out | {"status": "unratified", "invalidated": True}
    return out | {
        "status": "ratified",
        "invalidated": False,
        "ratified_at": ratification.ratified_at.isoformat() if ratification.ratified_at else None,
        "ratified_by": str(ratification.ratified_by) if ratification.ratified_by else None,
    }


async def ratify_target(
    db: AsyncSession, user: User, card: Card, *, note: str | None
) -> KpiTargetRatification:
    """Record the card's current target as ratified by ``user``."""
    snap = _target_snapshot(card)
    if snap["target_value"] is None:
        raise HTTPException(422, "The KPI has no target value to ratify")
    if card.status != "ACTIVE":
        raise HTTPException(409, "An archived KPI card cannot be ratified")
    current = target_state(card, await latest_ratification(db, card.id))
    if current["status"] == "ratified":
        raise HTTPException(409, "This target is already ratified")
    r = KpiTargetRatification(kpi_card_id=card.id, ratified_by=user.id, note=note or None, **snap)
    db.add(r)
    await db.flush()
    await event_bus.publish(
        "kpi.target_ratified",
        {"ratification_id": str(r.id), **snap},
        db=db,
        card_id=card.id,
        user_id=user.id,
    )
    return r


# ── Daily capture of the executive indicators (D-19, I-2) ────────────────


@dataclass(frozen=True)
class Observation:
    value: float | None
    numerator: float | None = None
    denominator: float | None = None


async def _general(db: AsyncSession) -> dict:
    row = (
        await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    ).scalar_one_or_none()
    return (row.general_settings if row else None) or {}


async def observe_executive_metrics(db: AsyncSession, today: date) -> dict[str, Observation]:
    """Today's landscape-wide value of every registered executive metric.

    Computed over the whole landscape (``CardReadScope.everything()``): the
    history is the organisation's record, shown only to readers who see the
    whole landscape — the dashboard trend's existing rule.
    """
    general = await _general(db)
    out: dict[str, Observation] = {}
    initiatives = await exe.load_visible_initiatives(db, CardReadScope.everything())
    latest = (
        await portfolio.latest_reports(db, [c.id for c in initiatives], as_of=today)
        if bool(general.get("ppmEnabled", False))
        else None
    )
    health = exe.summarize_delivery_health(
        initiatives, latest, today=today, stale=exe.staleness_days(general)
    )
    coverage = health["coverage"]
    out["TR-03"] = Observation(
        health["on_track_pct"],
        float(health["states"]["onTrack"]),
        float(coverage["reported"]),
    )
    if bool(general.get("grcEnabled", True)):
        risks = list((await db.execute(select(Risk))).scalars().all())
        picture = dec.classify_risks(risks, today)
        out["DEC-01"] = Observation(float(len(picture.escalated)), None, float(picture.open))
    # GOV-03 rule-based compliance, landscape-wide (D-33, I-13). Recorded only
    # when the assessed population can be established — an unavailable scan has
    # no defensible value to observe, so nothing is stored for it that day.
    scan = await assess_standard_compliance(db, read_scope=CardReadScope.everything())
    if scan["status"] == "ok":
        out["GOV-03"] = Observation(
            scan["compliance_pct"], float(scan["compliant"]), float(scan["assessed"])
        )
    # GOV-05 for the fiscal quarter today falls in, as of today (D-41, I-47).
    gov05 = await _gov05_observation(
        db, periods.parse(None, await get_fiscal_year_start(db), today)
    )
    if gov05 is not None:
        out["GOV-05"] = gov05
    return out


async def _gov05_observation(db: AsyncSession, period: periods.Period) -> Observation | None:
    """GOV-05 for ``period``, landscape-wide: verified by the original deadline
    (numerator) over decisions due (denominator). ``None`` when no decision is
    due — a rate with no eligible decision has no defensible value (C-04), so
    nothing is recorded rather than a zero."""
    # Imported here: the executive package imports this module (linkage).
    from app.services.executive.governance import decision_implementation

    result = await decision_implementation(db, CardReadScope.everything(), period)
    if result["status"] != "ok":
        return None
    return Observation(
        result["value"],
        float(result["outcomes"]["verified_on_time"]),
        float(result["eligible"]),
    )


async def _store_daily(db: AsyncSession, key: str, day: date, obs: Observation) -> None:
    values = {
        "value": obs.value,
        "numerator": obs.numerator,
        "denominator": obs.denominator,
        "unit": METRICS[key].unit,
        "calculation_version": METRICS[key].version,
    }
    stmt = (
        pg_insert(KpiMeasurement)
        .values(
            kind=KIND_DAILY,
            metric_key=key,
            period_type="day",
            period_key=day.isoformat(),
            period_start=day,
            period_end=day,
            source="system",
            status=STATUS_OBSERVED,
            **values,
        )
        .on_conflict_do_update(
            index_elements=["metric_key", "period_key"],
            index_where=text("kind = 'daily'"),
            set_={**values, "recorded_at": func.now()},
        )
    )
    await db.execute(stmt)


def _periods_of(day: date, start_month: int) -> list[tuple[str, str, date, date]]:
    """The fiscal year and quarter ``day`` falls in: (type, key, first, last)."""
    fy = fiscal_year_for(day, start_month)
    out = []
    fy_start, fy_end = fiscal_year_bounds(fy, start_month)
    out.append(("fiscal_year", f"FY{fy}", fy_start, fy_end - timedelta(days=1)))
    for q in range(1, 5):
        q_start, q_end = fiscal_quarter_bounds(fy, q, start_month)
        if q_start <= day < q_end:
            out.append(("quarter", f"FY{fy}-Q{q}", q_start, q_end - timedelta(days=1)))
    return out


async def close_ended_periods(db: AsyncSession, today: date) -> int:
    """Record each ended period's value of every metric: its last observation.

    Only periods that have daily observations, have ended, and have no value
    yet are recorded — as ``submitted``, by the system, with the observation's
    date in ``observed_on``. Idempotent.
    """
    start_month = await get_fiscal_year_start(db)
    created = 0
    for key in METRICS:
        days = (
            (
                await db.execute(
                    select(KpiMeasurement.period_start)
                    .where(KpiMeasurement.kind == KIND_DAILY, KpiMeasurement.metric_key == key)
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
        candidates = {p for d in days for p in _periods_of(d, start_month)}
        for ptype, pkey, first, last in sorted(candidates, key=lambda p: p[3]):
            if last >= today or await current_period_value(db, pkey, metric_key=key):
                continue
            obs = (
                await db.execute(
                    select(KpiMeasurement)
                    .where(
                        KpiMeasurement.kind == KIND_DAILY,
                        KpiMeasurement.metric_key == key,
                        KpiMeasurement.period_start >= first,
                        KpiMeasurement.period_start <= last,
                    )
                    .order_by(KpiMeasurement.period_start.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if obs is None:
                continue
            value, numerator, denominator = obs.value, obs.numerator, obs.denominator
            observed_on = obs.period_start
            if key in PERIOD_CALCULATED:
                # The period's own figure from its recorded history (GOV-05),
                # only for periods the daily capture ran in; nothing earlier.
                calc = await _gov05_observation(db, periods.parse(pkey, start_month, today))
                if calc is None:
                    continue
                value, numerator, denominator = calc.value, calc.numerator, calc.denominator
                observed_on = last
            m = KpiMeasurement(
                kind=KIND_PERIOD,
                metric_key=key,
                period_type=ptype,
                period_key=pkey,
                period_start=first,
                period_end=last,
                observed_on=observed_on,
                value=value,
                numerator=numerator,
                denominator=denominator,
                unit=obs.unit,
                calculation_version=obs.calculation_version,
                source="system",
                status=STATUS_SUBMITTED,
            )
            db.add(m)
            await db.flush()
            await _publish(db, "kpi.measurement_recorded", m, None)
            created += 1
    return created


async def capture_executive_observations(db: AsyncSession, today: date | None = None) -> dict:
    """The daily job: today's observation of each metric, then close ended periods."""
    day = today or _today()
    observed = await observe_executive_metrics(db, day)
    for key, obs in observed.items():
        await _store_daily(db, key, day, obs)
    await db.flush()
    closed = await close_ended_periods(db, day)
    return {"observed": sorted(observed), "periods_closed": closed}
