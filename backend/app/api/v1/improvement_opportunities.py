"""Improvement Opportunity registry API ([FORK] — noraPlan.md WP3.3).

NORA Stage 6.6 "Summary of Improvement Opportunities" as governable records:
classified by architecture domain, linked to the cards they concern and to
the transition initiative that realises them. Gated by the existing GRC
permissions (grc.view / grc.manage).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.card import Card
from app.models.improvement_opportunity import (
    OPPORTUNITY_DOMAINS,
    OPPORTUNITY_FEASIBILITIES,
    OPPORTUNITY_PRIORITIES,
    OPPORTUNITY_SOURCES,
    OPPORTUNITY_STATUSES,
    ImprovementOpportunity,
    ImprovementOpportunityCard,
)
from app.models.user import User
from app.services.nora_authoring import suggest_opportunities
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/improvement-opportunities", tags=["improvement-opportunities"])


class AiSuggestRequest(BaseModel):
    locale: str = Field(default="en", max_length=8)
    focus: str | None = Field(default=None, max_length=500)


class OpportunityCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    domain: str = "AA"
    source: str = "manual"
    priority: str = "medium"
    card_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    journey_card_id: uuid.UUID | None = None
    journey_phase: str | None = Field(default=None, max_length=200)
    feasibility: str | None = None


class OpportunityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    domain: str | None = None
    priority: str | None = None
    status: str | None = None
    initiative_id: uuid.UUID | None = None
    card_ids: list[uuid.UUID] | None = Field(default=None, max_length=50)
    journey_card_id: uuid.UUID | None = None
    journey_phase: str | None = Field(default=None, max_length=200)
    feasibility: str | None = None


def _validate(domain=None, source=None, priority=None, status=None, feasibility=None):
    if domain is not None and domain not in OPPORTUNITY_DOMAINS:
        raise HTTPException(400, f"Invalid domain: {domain}")
    if source is not None and source not in OPPORTUNITY_SOURCES:
        raise HTTPException(400, f"Invalid source: {source}")
    if priority is not None and priority not in OPPORTUNITY_PRIORITIES:
        raise HTTPException(400, f"Invalid priority: {priority}")
    if status is not None and status not in OPPORTUNITY_STATUSES:
        raise HTTPException(400, f"Invalid status: {status}")
    if feasibility is not None and feasibility not in OPPORTUNITY_FEASIBILITIES:
        raise HTTPException(400, f"Invalid feasibility: {feasibility}")


async def _card_briefs(db: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, dict]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = await db.execute(select(Card.id, Card.name, Card.type).where(Card.id.in_(ids)))
    return {r[0]: {"id": str(r[0]), "name": r[1], "type": r[2]} for r in rows.all()}


async def _links_for(
    db: AsyncSession, opp_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[uuid.UUID]]:
    if not opp_ids:
        return {}
    rows = await db.execute(
        select(ImprovementOpportunityCard).where(
            ImprovementOpportunityCard.opportunity_id.in_(opp_ids)
        )
    )
    out: dict[uuid.UUID, list[uuid.UUID]] = {}
    for link in rows.scalars().all():
        out.setdefault(link.opportunity_id, []).append(link.card_id)
    return out


def _opp_dict(o: ImprovementOpportunity, card_ids: list[uuid.UUID], briefs: dict) -> dict:
    return {
        "id": str(o.id),
        "title": o.title,
        "description": o.description,
        "domain": o.domain,
        "source": o.source,
        "priority": o.priority,
        "status": o.status,
        "initiative_id": str(o.initiative_id) if o.initiative_id else None,
        "initiative": briefs.get(o.initiative_id),
        "cards": [briefs[c] for c in card_ids if c in briefs],
        "journey_card_id": str(o.journey_card_id) if o.journey_card_id else None,
        "journey": briefs.get(o.journey_card_id),
        "journey_phase": o.journey_phase,
        "feasibility": o.feasibility,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


@router.get("")
async def list_opportunities(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status: str | None = Query(None),
    domain: str | None = Query(None),
):
    await PermissionService.require_permission(db, user, "grc.view")
    stmt = select(ImprovementOpportunity).order_by(ImprovementOpportunity.created_at.desc())
    if status:
        stmt = stmt.where(ImprovementOpportunity.status == status)
    if domain:
        stmt = stmt.where(ImprovementOpportunity.domain == domain)
    opps = list((await db.execute(stmt)).scalars().all())
    links = await _links_for(db, [o.id for o in opps])
    briefs = await _card_briefs(
        db,
        {o.initiative_id for o in opps}
        | {o.journey_card_id for o in opps}
        | {c for ids in links.values() for c in ids},
    )
    return [_opp_dict(o, links.get(o.id, []), briefs) for o in opps]


@router.post("", status_code=201)
async def create_opportunity(
    body: OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "grc.manage")
    _validate(
        domain=body.domain,
        source=body.source,
        priority=body.priority,
        feasibility=body.feasibility,
    )
    o = ImprovementOpportunity(
        title=body.title,
        description=body.description,
        domain=body.domain,
        source=body.source,
        priority=body.priority,
        journey_card_id=body.journey_card_id,
        journey_phase=body.journey_phase,
        feasibility=body.feasibility,
        created_by=user.id,
    )
    db.add(o)
    await db.flush()
    for cid in dict.fromkeys(body.card_ids):
        db.add(ImprovementOpportunityCard(opportunity_id=o.id, card_id=cid))
    await db.commit()
    await db.refresh(o)
    links = await _links_for(db, [o.id])
    briefs = await _card_briefs(db, set(links.get(o.id, [])) | {o.journey_card_id})
    return _opp_dict(o, links.get(o.id, []), briefs)


@router.post("/ai-suggest")
async def ai_suggest_opportunities(
    body: AiSuggestRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI-draft NORA improvement opportunities from live landscape signals
    ([FORK] — WP5.5). Advisory only: nothing is persisted here. The frontend
    commits accepted suggestions via ``POST ""`` with ``source="ai"`` so they
    land as ``proposed`` records for human governance."""
    await PermissionService.require_permission(db, user, "grc.manage")
    await PermissionService.require_permission(db, user, "ai.suggest")
    try:
        suggestions = await suggest_opportunities(db, locale=body.locale, focus=body.focus)
    except ValueError as e:
        if str(e) == "AI_NOT_CONFIGURED":
            raise HTTPException(400, "AI is not configured") from e
        raise HTTPException(400, str(e)) from e
    return {"suggestions": suggestions}


@router.patch("/{opportunity_id}")
async def update_opportunity(
    opportunity_id: uuid.UUID,
    body: OpportunityUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "grc.manage")
    o = (
        await db.execute(
            select(ImprovementOpportunity).where(ImprovementOpportunity.id == opportunity_id)
        )
    ).scalar_one_or_none()
    if o is None:
        raise HTTPException(404, "Opportunity not found")
    data = body.model_dump(exclude_unset=True)
    _validate(
        domain=data.get("domain"),
        priority=data.get("priority"),
        status=data.get("status"),
        feasibility=data.get("feasibility"),
    )

    card_ids = data.pop("card_ids", None)
    # Linking an initiative moves a merely-approved opportunity into transition.
    if data.get("initiative_id") and o.status in ("proposed", "approved"):
        data.setdefault("status", "inTransition")
    for field, value in data.items():
        setattr(o, field, value)

    if card_ids is not None:
        existing = (
            await db.execute(
                select(ImprovementOpportunityCard).where(
                    ImprovementOpportunityCard.opportunity_id == o.id
                )
            )
        ).scalars()
        for link in existing:
            await db.delete(link)
        for cid in dict.fromkeys(card_ids):
            db.add(ImprovementOpportunityCard(opportunity_id=o.id, card_id=cid))

    await db.commit()
    await db.refresh(o)
    links = await _links_for(db, [o.id])
    briefs = await _card_briefs(db, set(links.get(o.id, [])) | {o.initiative_id, o.journey_card_id})
    return _opp_dict(o, links.get(o.id, []), briefs)


@router.delete("/{opportunity_id}", status_code=204)
async def delete_opportunity(
    opportunity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "grc.manage")
    o = (
        await db.execute(
            select(ImprovementOpportunity).where(ImprovementOpportunity.id == opportunity_id)
        )
    ).scalar_one_or_none()
    if o is None:
        raise HTTPException(404, "Opportunity not found")
    await db.delete(o)
    await db.commit()
