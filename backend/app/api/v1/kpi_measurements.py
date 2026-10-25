"""KPI measurement history and target ratification (decisions D-19, D-17a).

* **Reads** follow the KPI card: a card the caller may not read does not exist
  for them (404, ``CardReadScope``, hidden types included). A system metric's
  history is landscape-wide, so it is shown only to executive-dashboard readers
  whose scope is unrestricted — the dashboard trend's existing rule.
* **Writes** need ``kpis.measure`` (record, correct), ``kpis.verify`` (verify,
  never one's own row) or, for a target, ``kpis.ratify_targets`` landscape-wide
  or ``card.ratify_kpi_target`` on that KPI through a stakeholder role. The
  rules themselves live in ``app.services.kpi_measurement_service``.
"""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.kpi_measurement import KIND_DAILY, KIND_PERIOD, KpiMeasurement
from app.models.user import User
from app.services import kpi_measurement_service as svc
from app.services.card_read_scope import CardReadScope, require_card_readable
from app.services.executive.registry import METRICS
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/kpis", tags=["kpis"])


def _finite(v: float) -> float:
    if not math.isfinite(v):
        raise ValueError("value must be a finite number")
    return v


class MeasurementIn(BaseModel):
    period_key: str = Field(..., max_length=16)
    value: float
    evidence: str | None = Field(None, max_length=2000)

    _check_value = field_validator("value")(_finite)


class CorrectionIn(BaseModel):
    value: float
    evidence: str | None = Field(None, max_length=2000)
    reason: str = Field(..., min_length=1, max_length=2000)

    _check_value = field_validator("value")(_finite)


class RatificationIn(BaseModel):
    note: str | None = Field(None, max_length=2000)


async def _readable_kpi(db: AsyncSession, user: User, card_id: uuid.UUID):
    await require_card_readable(db, user, card_id, mode="inventory")
    return await svc.require_kpi_card(db, card_id)


async def _measurement_for(
    db: AsyncSession, user: User, measurement_id: uuid.UUID
) -> KpiMeasurement:
    """The row, if the caller may see its subject; 404 otherwise."""
    m = await db.get(KpiMeasurement, measurement_id)
    if m is None:
        raise HTTPException(404, "Measurement not found")
    if m.kpi_card_id is not None:
        await _readable_kpi(db, user, m.kpi_card_id)
    elif not await _can_read_metric_history(db, user):
        raise HTTPException(404, "Measurement not found")
    return m


async def _can_read_metric_history(db: AsyncSession, user: User) -> bool:
    if not await PermissionService.has_app_permission(db, user, "reports.executive_dashboard"):
        return False
    scope = await CardReadScope.load(db, user)
    return scope.is_unrestricted(mode="module")


async def _performance(db: AsyncSession, user: User, card) -> dict:
    ratification = await svc.latest_ratification(db, card.id)
    history = await svc.card_history(db, card.id)
    return {
        "card_id": str(card.id),
        "metric_key": (card.attributes or {}).get("metricKey"),
        "target": svc.target_state(card, ratification),
        "measurements": [svc.measurement_to_dict(m) for m in history],
        "can_measure": await PermissionService.has_app_permission(db, user, "kpis.measure"),
        "can_verify": await PermissionService.has_app_permission(db, user, "kpis.verify"),
        "can_ratify": await PermissionService.check_permission(
            db, user, "kpis.ratify_targets", card.id, "card.ratify_kpi_target"
        ),
    }


@router.get("/{card_id}/performance")
async def kpi_performance(
    card_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """A KPI card's target (with its ratification state) and measurement history."""
    card = await _readable_kpi(db, user, card_id)
    return await _performance(db, user, card)


@router.post("/{card_id}/measurements", status_code=201)
async def record_measurement(
    card_id: uuid.UUID,
    body: MeasurementIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = await _readable_kpi(db, user, card_id)
    await PermissionService.require_permission(db, user, "kpis.measure")
    m = await svc.record_card_measurement(
        db, user, card, period_key=body.period_key, value=body.value, evidence=body.evidence
    )
    await db.commit()
    return svc.measurement_to_dict(m)


@router.post("/measurements/{measurement_id}/corrections", status_code=201)
async def correct_measurement(
    measurement_id: uuid.UUID,
    body: CorrectionIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    current = await _measurement_for(db, user, measurement_id)
    await PermissionService.require_permission(db, user, "kpis.measure")
    m = await svc.correct_measurement(
        db, user, current, value=body.value, evidence=body.evidence, reason=body.reason
    )
    await db.commit()
    return svc.measurement_to_dict(m)


@router.post("/measurements/{measurement_id}/verify")
async def verify_measurement(
    measurement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = await _measurement_for(db, user, measurement_id)
    await PermissionService.require_permission(db, user, "kpis.verify")
    m = await svc.verify_measurement(db, user, m)
    await db.commit()
    return svc.measurement_to_dict(m)


@router.post("/{card_id}/target-ratifications", status_code=201)
async def ratify_target(
    card_id: uuid.UUID,
    body: RatificationIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ratify the KPI's current target as its authorized target approver (D-17a)."""
    card = await _readable_kpi(db, user, card_id)
    await PermissionService.require_permission(
        db, user, "kpis.ratify_targets", card_id=card.id, card_permission="card.ratify_kpi_target"
    )
    await svc.ratify_target(db, user, card, note=body.note)
    await db.commit()
    return (await _performance(db, user, card))["target"]


@router.get("/metrics/{metric_key}/history")
async def metric_history(
    metric_key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """A registered executive metric's period values and recent daily observations."""
    await PermissionService.require_permission(db, user, "reports.executive_dashboard")
    if metric_key not in METRICS:
        raise HTTPException(404, "Unknown metric")
    if not await _can_read_metric_history(db, user):
        # Landscape-wide figures are not shown to a restricted reader.
        return {"metric_key": metric_key, "status": "restricted", "periods": [], "daily": []}
    rows = (
        (
            await db.execute(
                select(KpiMeasurement)
                .where(
                    KpiMeasurement.metric_key == metric_key,
                    KpiMeasurement.kpi_card_id.is_(None),
                )
                .order_by(KpiMeasurement.period_end.desc(), KpiMeasurement.recorded_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "metric_key": metric_key,
        "status": "ok",
        "periods": [svc.measurement_to_dict(m) for m in rows if m.kind == KIND_PERIOD],
        "daily": [svc.measurement_to_dict(m) for m in rows if m.kind == KIND_DAILY][:400],
    }
