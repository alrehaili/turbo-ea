"""Application Rationalization Campaign API.

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
    CAMPAIGN_STATUSES,
    TIME_DECISIONS,
    CampaignDecision,
    RationalizationCampaign,
)
from app.models.user import User
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/rationalization", tags=["rationalization"])


# --------------------------------------------------------------------------- #
# Schemas                                                                      #
# --------------------------------------------------------------------------- #
class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None
    status: str = "draft"
    target_savings: float | None = None


class CampaignUpdate(BaseModel):
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
    risk_note: str | None = None
    notes: str | None = None
    progress: int = Field(default=0, ge=0, le=100)


class DecisionUpdate(BaseModel):
    time_decision: str | None = None
    successor_id: uuid.UUID | None = None
    initiative_id: uuid.UUID | None = None
    annual_cost: float | None = None
    planned_savings: float | None = None
    risk_note: str | None = None
    notes: str | None = None
    progress: int | None = Field(default=None, ge=0, le=100)


# --------------------------------------------------------------------------- #
# Serialisation helpers                                                        #
# --------------------------------------------------------------------------- #
def _campaign_brief(c: RationalizationCampaign) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "description": c.description,
        "status": c.status,
        "target_savings": c.target_savings,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _decision_dict(d: CampaignDecision, names: dict[uuid.UUID, dict]) -> dict:
    def brief(cid: uuid.UUID | None) -> dict | None:
        return names.get(cid) if cid else None

    return {
        "id": str(d.id),
        "card": brief(d.card_id),
        "time_decision": d.time_decision,
        "successor": brief(d.successor_id),
        "initiative": brief(d.initiative_id),
        "annual_cost": d.annual_cost,
        "planned_savings": d.planned_savings,
        "risk_note": d.risk_note,
        "notes": d.notes,
        "progress": d.progress,
    }


async def _card_brief_map(db: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, dict]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    res = await db.execute(select(Card.id, Card.name, Card.type).where(Card.id.in_(ids)))
    return {row[0]: {"id": str(row[0]), "name": row[1], "type": row[2]} for row in res.all()}


async def _get_campaign(db: AsyncSession, campaign_id: uuid.UUID) -> RationalizationCampaign:
    res = await db.execute(
        select(RationalizationCampaign).where(RationalizationCampaign.id == campaign_id)
    )
    campaign = res.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


def _validate_decision(time_decision: str | None) -> None:
    if time_decision is not None and time_decision not in TIME_DECISIONS:
        raise HTTPException(status_code=400, detail=f"Invalid TIME decision: {time_decision}")


# --------------------------------------------------------------------------- #
# Campaign endpoints                                                           #
# --------------------------------------------------------------------------- #
@router.get("/campaigns")
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.view")
    res = await db.execute(
        select(RationalizationCampaign).order_by(RationalizationCampaign.created_at.desc())
    )
    campaigns = res.scalars().all()

    # Per-campaign decision rollup (count + planned savings) in one query.
    dres = await db.execute(select(CampaignDecision.campaign_id, CampaignDecision.planned_savings))
    counts: dict[uuid.UUID, int] = {}
    savings: dict[uuid.UUID, float] = {}
    for cid, planned in dres.all():
        counts[cid] = counts.get(cid, 0) + 1
        if planned:
            savings[cid] = savings.get(cid, 0.0) + planned

    return [
        {
            **_campaign_brief(c),
            "decision_count": counts.get(c.id, 0),
            "planned_savings_total": savings.get(c.id, 0.0),
        }
        for c in campaigns
    ]


@router.post("/campaigns", status_code=201)
async def create_campaign(
    body: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.manage")
    if body.status not in CAMPAIGN_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")
    campaign = RationalizationCampaign(
        name=body.name,
        description=body.description,
        status=body.status,
        target_savings=body.target_savings,
        created_by=user.id,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return _campaign_brief(campaign)


@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.view")
    campaign = await _get_campaign(db, campaign_id)
    dres = await db.execute(
        select(CampaignDecision)
        .where(CampaignDecision.campaign_id == campaign_id)
        .order_by(CampaignDecision.created_at)
    )
    decisions = list(dres.scalars().all())

    ref_ids: set[uuid.UUID] = set()
    for d in decisions:
        ref_ids.update({d.card_id, d.successor_id, d.initiative_id})
    names = await _card_brief_map(db, ref_ids)

    # Savings + decision-mix rollup.
    by_decision: dict[str, int] = {}
    planned_total = 0.0
    for d in decisions:
        by_decision[d.time_decision] = by_decision.get(d.time_decision, 0) + 1
        if d.planned_savings:
            planned_total += d.planned_savings

    return {
        **_campaign_brief(campaign),
        "decisions": [_decision_dict(d, names) for d in decisions],
        "summary": {
            "decision_count": len(decisions),
            "by_decision": by_decision,
            "planned_savings_total": planned_total,
            "target_savings": campaign.target_savings,
        },
    }


@router.patch("/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: uuid.UUID,
    body: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.manage")
    campaign = await _get_campaign(db, campaign_id)
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in CAMPAIGN_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {data['status']}")
    for key, value in data.items():
        setattr(campaign, key, value)
    await db.commit()
    await db.refresh(campaign)
    return _campaign_brief(campaign)


@router.delete("/campaigns/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.manage")
    campaign = await _get_campaign(db, campaign_id)
    await db.delete(campaign)
    await db.commit()


# --------------------------------------------------------------------------- #
# Decision endpoints                                                           #
# --------------------------------------------------------------------------- #
@router.post("/campaigns/{campaign_id}/decisions", status_code=201)
async def create_decision(
    campaign_id: uuid.UUID,
    body: DecisionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.manage")
    await _get_campaign(db, campaign_id)
    _validate_decision(body.time_decision)
    decision = CampaignDecision(campaign_id=campaign_id, **body.model_dump())
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    names = await _card_brief_map(
        db, {decision.card_id, decision.successor_id, decision.initiative_id}
    )
    return _decision_dict(decision, names)


@router.patch("/decisions/{decision_id}")
async def update_decision(
    decision_id: uuid.UUID,
    body: DecisionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.manage")
    res = await db.execute(select(CampaignDecision).where(CampaignDecision.id == decision_id))
    decision = res.scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    data = body.model_dump(exclude_unset=True)
    _validate_decision(data.get("time_decision"))
    for key, value in data.items():
        setattr(decision, key, value)
    await db.commit()
    await db.refresh(decision)
    names = await _card_brief_map(
        db, {decision.card_id, decision.successor_id, decision.initiative_id}
    )
    return _decision_dict(decision, names)


@router.delete("/decisions/{decision_id}", status_code=204)
async def delete_decision(
    decision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "rationalization.manage")
    res = await db.execute(select(CampaignDecision).where(CampaignDecision.id == decision_id))
    decision = res.scalar_one_or_none()
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    await db.delete(decision)
    await db.commit()
