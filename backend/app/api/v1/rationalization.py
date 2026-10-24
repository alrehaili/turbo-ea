"""Application Rationalization Assessment API.

Packages the TIME-framework portfolio-decision workflow over a set of
applications. See ``app.models.rationalization`` for the data model.

[FORK FEATURE]
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.card import Card
from app.models.rationalization import (
    ASSESSMENT_STATUSES,
    TIME_DECISIONS,
    AssessmentDecision,
    RationalizationAssessment,
)
from app.models.user import User
from app.services.card_read_scope import CardReadScope, require_card_readable
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/rationalization", tags=["rationalization"])


# --------------------------------------------------------------------------- #
# Schemas                                                                      #
# --------------------------------------------------------------------------- #
class AssessmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None
    status: str = "draft"
    target_savings: float | None = None


class AssessmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: str | None = None
    target_savings: float | None = None


class DecisionCreate(BaseModel):
    card_id: uuid.UUID
    time_decision: str = "undecided"
    successor_id: uuid.UUID | None = None
    initiative_id: uuid.UUID | None = None
    annual_cost: float | None = None
    planned_savings: float | None = None
    rationale: str | None = None
    risk_note: str | None = None
    notes: str | None = None
    progress: int = Field(default=0, ge=0, le=100)


class DecisionUpdate(BaseModel):
    time_decision: str | None = None
    successor_id: uuid.UUID | None = None
    initiative_id: uuid.UUID | None = None
    annual_cost: float | None = None
    planned_savings: float | None = None
    rationale: str | None = None
    risk_note: str | None = None
    notes: str | None = None
    progress: int | None = Field(default=None, ge=0, le=100)


# --------------------------------------------------------------------------- #
# Serialisation helpers                                                        #
# --------------------------------------------------------------------------- #
def _assessment_brief(c: RationalizationAssessment, show_costs: bool) -> dict:
    """``show_costs``: the caller holds ``costs.view`` — the target is a
    portfolio-level money figure, so the stakeholder bypass does not apply."""
    return {
        "id": str(c.id),
        "name": c.name,
        "description": c.description,
        "status": c.status,
        "target_savings": c.target_savings if show_costs else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _decision_dict(
    d: AssessmentDecision, names: dict[uuid.UUID, dict], cost_ok: set[uuid.UUID] | None
) -> dict:
    """``names`` holds only readable cards, so a hidden successor or initiative
    is redacted; ``cost_ok`` (None = every card) gates the money fields with the
    card endpoints' rule — ``costs.view`` or a stakeholder role on the card."""

    def brief(cid: uuid.UUID | None) -> dict | None:
        return names.get(cid) if cid else None

    show_costs = cost_ok is None or d.card_id in cost_ok

    return {
        "id": str(d.id),
        "card": brief(d.card_id),
        "time_decision": d.time_decision,
        "successor": brief(d.successor_id),
        "initiative": brief(d.initiative_id),
        "annual_cost": d.annual_cost if show_costs else None,
        "planned_savings": d.planned_savings if show_costs else None,
        "rationale": d.rationale,
        "risk_note": d.risk_note,
        "notes": d.notes,
        "progress": d.progress,
    }


async def _card_brief_map(
    db: AsyncSession, ids: set[uuid.UUID], read_scope: CardReadScope
) -> dict[uuid.UUID, dict]:
    """Briefs of the readable cards among ``ids``; a hidden card is simply absent."""
    ids = {i for i in ids if i}
    if not ids:
        return {}
    res = await db.execute(
        select(Card.id, Card.name, Card.type).where(
            Card.id.in_(ids), *read_scope.where(Card, mode="module")
        )
    )
    return {row[0]: {"id": str(row[0]), "name": row[1], "type": row[2]} for row in res.all()}


async def _visible_decisions(
    db: AsyncSession, decisions: list[AssessmentDecision], read_scope: CardReadScope
) -> list[AssessmentDecision]:
    """Drop decisions about a hidden card: a decision row is one application's
    verdict, so it is omitted rather than redacted (decision D-30)."""
    hidden = await read_scope.hidden_card_ids(db, {d.card_id for d in decisions}, mode="module")
    return [d for d in decisions if d.card_id not in hidden]


async def _cost_ok(
    db: AsyncSession, user: User, decisions: list[AssessmentDecision]
) -> set[uuid.UUID] | None:
    """None when the caller holds ``costs.view``; else the card ids whose costs
    the caller may see through a stakeholder role."""
    if await PermissionService.has_app_permission(db, user, "costs.view"):
        return None
    ids = [d.card_id for d in decisions]
    return await PermissionService.card_ids_with_cost_access(db, user, ids) if ids else set()


async def _get_visible_decision(
    db: AsyncSession, decision_id: uuid.UUID, read_scope: CardReadScope
) -> AssessmentDecision:
    res = await db.execute(select(AssessmentDecision).where(AssessmentDecision.id == decision_id))
    decision = res.scalar_one_or_none()
    if decision is None or not await _visible_decisions(db, [decision], read_scope):
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


async def _get_assessment(db: AsyncSession, assessment_id: uuid.UUID) -> RationalizationAssessment:
    res = await db.execute(
        select(RationalizationAssessment).where(RationalizationAssessment.id == assessment_id)
    )
    assessment = res.scalar_one_or_none()
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


def _validate_decision(time_decision: str | None) -> None:
    if time_decision is not None and time_decision not in TIME_DECISIONS:
        raise HTTPException(status_code=400, detail=f"Invalid TIME decision: {time_decision}")


# --------------------------------------------------------------------------- #
# Assessment endpoints                                                           #
# --------------------------------------------------------------------------- #
@router.get("/assessments")
async def list_assessments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.view")
    res = await db.execute(
        select(RationalizationAssessment).order_by(RationalizationAssessment.created_at.desc())
    )
    assessments = res.scalars().all()
    read_scope = await CardReadScope.load(db, user)
    show_costs = await PermissionService.has_app_permission(db, user, "costs.view")

    # Per-assessment rollup over the decisions the reader may see; a total of
    # many cards' savings is a portfolio figure, so it needs ``costs.view``.
    all_decisions = list((await db.execute(select(AssessmentDecision))).scalars().all())
    counts: dict[uuid.UUID, int] = {}
    savings: dict[uuid.UUID, float] = {}
    for d in await _visible_decisions(db, all_decisions, read_scope):
        counts[d.assessment_id] = counts.get(d.assessment_id, 0) + 1
        if d.planned_savings:
            savings[d.assessment_id] = savings.get(d.assessment_id, 0.0) + d.planned_savings

    return [
        {
            **_assessment_brief(c, show_costs),
            "decision_count": counts.get(c.id, 0),
            "planned_savings_total": savings.get(c.id, 0.0) if show_costs else None,
        }
        for c in assessments
    ]


@router.post("/assessments", status_code=201)
async def create_assessment(
    body: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.manage")
    if body.status not in ASSESSMENT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
    assessment = RationalizationAssessment(
        name=body.name,
        description=body.description,
        status=body.status,
        target_savings=body.target_savings,
        created_by=user.id,
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return _assessment_brief(
        assessment, await PermissionService.has_app_permission(db, user, "costs.view")
    )


@router.get("/assessments/{assessment_id}")
async def get_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.view")
    assessment = await _get_assessment(db, assessment_id)
    dres = await db.execute(
        select(AssessmentDecision)
        .where(AssessmentDecision.assessment_id == assessment_id)
        .order_by(AssessmentDecision.created_at)
    )
    read_scope = await CardReadScope.load(db, user)
    decisions = await _visible_decisions(db, list(dres.scalars().all()), read_scope)
    show_costs = await PermissionService.has_app_permission(db, user, "costs.view")
    cost_ok = await _cost_ok(db, user, decisions)

    ref_ids: set[uuid.UUID] = set()
    for d in decisions:
        ref_ids.update({d.card_id, d.successor_id, d.initiative_id})
    names = await _card_brief_map(db, ref_ids, read_scope)

    # Savings + decision-mix rollup.
    by_decision: dict[str, int] = {}
    planned_total = 0.0
    for d in decisions:
        by_decision[d.time_decision] = by_decision.get(d.time_decision, 0) + 1
        if d.planned_savings:
            planned_total += d.planned_savings

    return {
        **_assessment_brief(assessment, show_costs),
        "decisions": [_decision_dict(d, names, cost_ok) for d in decisions],
        "summary": {
            "decision_count": len(decisions),
            "by_decision": by_decision,
            "planned_savings_total": planned_total if show_costs else None,
            "target_savings": assessment.target_savings if show_costs else None,
        },
    }


@router.patch("/assessments/{assessment_id}")
async def update_assessment(
    assessment_id: uuid.UUID,
    body: AssessmentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.manage")
    assessment = await _get_assessment(db, assessment_id)
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in ASSESSMENT_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {data['status']}")
    for key, value in data.items():
        setattr(assessment, key, value)
    await db.commit()
    await db.refresh(assessment)
    return _assessment_brief(
        assessment, await PermissionService.has_app_permission(db, user, "costs.view")
    )


@router.delete("/assessments/{assessment_id}", status_code=204)
async def delete_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.manage")
    assessment = await _get_assessment(db, assessment_id)
    await db.delete(assessment)
    await db.commit()


# --------------------------------------------------------------------------- #
# Decision endpoints                                                           #
# --------------------------------------------------------------------------- #
@router.post("/assessments/{assessment_id}/decisions", status_code=201)
async def create_decision(
    assessment_id: uuid.UUID,
    body: DecisionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.manage")
    await _get_assessment(db, assessment_id)
    _validate_decision(body.time_decision)
    for cid in (body.card_id, body.successor_id, body.initiative_id):
        if cid:
            await require_card_readable(db, user, cid, mode="module")
    decision = AssessmentDecision(assessment_id=assessment_id, **body.model_dump())
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    read_scope = await CardReadScope.load(db, user)
    names = await _card_brief_map(
        db, {decision.card_id, decision.successor_id, decision.initiative_id}, read_scope
    )
    return _decision_dict(decision, names, await _cost_ok(db, user, [decision]))


@router.patch("/decisions/{decision_id}")
async def update_decision(
    decision_id: uuid.UUID,
    body: DecisionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.manage")
    read_scope = await CardReadScope.load(db, user)
    decision = await _get_visible_decision(db, decision_id, read_scope)
    data = body.model_dump(exclude_unset=True)
    _validate_decision(data.get("time_decision"))
    # A link the caller was shown redacted (null) is kept, not cleared (D-30).
    for key in ("successor_id", "initiative_id"):
        current = getattr(decision, key)
        if key in data and data[key] is None and current is not None:
            if await read_scope.hidden_card_ids(db, {current}, mode="module"):
                data.pop(key)
    for key in ("card_id", "successor_id", "initiative_id"):
        if data.get(key):
            await require_card_readable(db, user, data[key], mode="module")
    for key, value in data.items():
        setattr(decision, key, value)
    await db.commit()
    await db.refresh(decision)
    names = await _card_brief_map(
        db, {decision.card_id, decision.successor_id, decision.initiative_id}, read_scope
    )
    return _decision_dict(decision, names, await _cost_ok(db, user, [decision]))


@router.delete("/decisions/{decision_id}", status_code=204)
async def delete_decision(
    decision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.manage")
    decision = await _get_visible_decision(db, decision_id, await CardReadScope.load(db, user))
    await db.delete(decision)
    await db.commit()


@router.get("/cards/{card_id}/decisions")
async def list_decisions_for_card(
    card_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List every rationalization decision recorded against a specific card.

    Powers the Portfolio Decisions section on the card detail page so users
    who visit an Application card see the board's verdict — including the
    strategic rationale — without having to remember which assessment it
    lives in. Returns rows across every assessment, most recent first.
    """
    await PermissionService.require_permission(db, user, "rationalization.view")
    # 404 for a hidden card as for a missing one: never confirm it exists.
    await require_card_readable(db, user, card_id, mode="module")
    read_scope = await CardReadScope.load(db, user)

    decisions_res = await db.execute(
        select(AssessmentDecision, RationalizationAssessment)
        .join(
            RationalizationAssessment,
            RationalizationAssessment.id == AssessmentDecision.assessment_id,
        )
        .where(AssessmentDecision.card_id == card_id)
        .order_by(RationalizationAssessment.created_at.desc())
    )
    rows = decisions_res.all()

    # Resolve successor + initiative card briefs in one query so the
    # payload is self-contained and the card-detail page needs no follow-up
    # lookups.
    ref_ids: set[uuid.UUID] = set()
    for decision, _ in rows:
        if decision.successor_id:
            ref_ids.add(decision.successor_id)
        if decision.initiative_id:
            ref_ids.add(decision.initiative_id)
    names = await _card_brief_map(db, ref_ids, read_scope)
    cost_ok = await _cost_ok(db, user, [d for d, _ in rows])

    return [
        {
            **_decision_dict(decision, names, cost_ok),
            "assessment": {
                "id": str(assessment.id),
                "name": assessment.name,
                "status": assessment.status,
            },
        }
        for decision, assessment in rows
    ]
