"""Transformation Roadmap — saved, scoped lifecycle-timeline views.

A roadmap groups cards of one type into swimlanes by a related card type and
plots each card's ``lifecycle`` phases as a timeline bar, overlaying transformation
milestones. The timeline is computed on demand from the card graph; the roadmap
row stores only its view configuration.

[FORK FEATURE]
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.card import Card
from app.models.relation import Relation
from app.models.roadmap import Roadmap, RoadmapMilestone
from app.models.user import User
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])


# ── Schemas ────────────────────────────────────────────────────────────


class MilestoneIn(BaseModel):
    label: str = Field(min_length=1, max_length=300)
    target_date: date
    initiative_id: uuid.UUID | None = None
    color: str | None = Field(default=None, max_length=20)


class RoadmapCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None
    config: dict = Field(default_factory=dict)


class RoadmapUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    config: dict | None = None


# ── Serialisers ────────────────────────────────────────────────────────


def _serialize_milestone(m: RoadmapMilestone) -> dict:
    return {
        "id": str(m.id),
        "roadmap_id": str(m.roadmap_id),
        "label": m.label,
        "target_date": m.target_date.isoformat() if m.target_date else None,
        "initiative_id": str(m.initiative_id) if m.initiative_id else None,
        "color": m.color,
    }


def _serialize_roadmap(r: Roadmap, milestones: list[RoadmapMilestone]) -> dict:
    return {
        "id": str(r.id),
        "name": r.name,
        "description": r.description,
        "config": r.config or {},
        "owner_id": str(r.owner_id) if r.owner_id else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        "milestones": [_serialize_milestone(m) for m in milestones],
    }


async def _milestones_for(db: AsyncSession, roadmap_id: uuid.UUID) -> list[RoadmapMilestone]:
    rows = await db.execute(
        select(RoadmapMilestone)
        .where(RoadmapMilestone.roadmap_id == roadmap_id)
        .order_by(RoadmapMilestone.target_date)
    )
    return list(rows.scalars().all())


# ── Timeline computation ───────────────────────────────────────────────


def _has_lifecycle(card: Card) -> bool:
    lc = card.lifecycle or {}
    return any(lc.values())


async def _compute_timeline(db: AsyncSession, card_type: str, group_by: str) -> dict:
    """Group active ``card_type`` cards into swimlanes by a related ``group_by``
    card, returning each card's lifecycle for the timeline bars.

    A card is placed under the first lane it relates to (deterministic by lane
    name); cards with no relation to a lane fall into ``ungrouped``.
    """
    # 1. Bars: active cards of card_type that carry at least one lifecycle date.
    bars_result = await db.execute(
        select(Card).where(Card.type == card_type, Card.status == "ACTIVE")
    )
    bars = [c for c in bars_result.scalars().all() if _has_lifecycle(c)]
    bar_ids = {str(c.id) for c in bars}

    # 2. Lanes: active cards of the grouping type.
    lanes_result = await db.execute(
        select(Card).where(Card.type == group_by, Card.status == "ACTIVE").order_by(Card.name)
    )
    lane_cards = list(lanes_result.scalars().all())
    lane_ids = {str(c.id) for c in lane_cards}
    lane_order = [str(c.id) for c in lane_cards]

    # 3. Relations connecting a bar to a lane.
    bar_to_lanes: dict[str, list[str]] = {bid: [] for bid in bar_ids}
    if bar_ids and lane_ids:
        rels_result = await db.execute(
            select(Relation).where(
                (Relation.source_id.in_([c.id for c in bars]))
                | (Relation.target_id.in_([c.id for c in bars]))
            )
        )
        for r in rels_result.scalars().all():
            sid, tid = str(r.source_id), str(r.target_id)
            if sid in bar_ids and tid in lane_ids:
                bar_to_lanes[sid].append(tid)
            elif tid in bar_ids and sid in lane_ids:
                bar_to_lanes[tid].append(sid)

    def _bar_payload(c: Card) -> dict:
        return {
            "id": str(c.id),
            "name": c.name,
            "type": c.type,
            "subtype": c.subtype,
            "lifecycle": c.lifecycle or {},
        }

    lane_buckets: dict[str, list[dict]] = {lid: [] for lid in lane_ids}
    ungrouped: list[dict] = []
    for c in bars:
        matched = bar_to_lanes.get(str(c.id), [])
        if matched:
            # First lane in display order that this card links to.
            chosen = next((lid for lid in lane_order if lid in matched), matched[0])
            lane_buckets[chosen].append(_bar_payload(c))
        else:
            ungrouped.append(_bar_payload(c))

    lanes = [
        {"id": lc_id, "name": lc.name, "items": lane_buckets[lc_id]}
        for lc in lane_cards
        for lc_id in [str(lc.id)]
        if lane_buckets[lc_id]
    ]
    return {
        "group_by": group_by,
        "card_type": card_type,
        "lanes": lanes,
        "ungrouped": ungrouped,
    }


# ── Ad-hoc timeline (Phase 1 view, no persistence) ─────────────────────


@router.get("/data")
async def roadmap_data(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    type: str = Query("Application"),
    group_by: str = Query("BusinessCapability"),
):
    """Compute an unsaved roadmap timeline for the given card type + grouping."""
    await PermissionService.require_permission(db, user, "reports.ea_dashboard")
    return await _compute_timeline(db, type, group_by)


# ── Saved-roadmap CRUD ─────────────────────────────────────────────────


@router.get("")
async def list_roadmaps(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reports.ea_dashboard")
    rows = await db.execute(select(Roadmap).order_by(Roadmap.name))
    roadmaps = list(rows.scalars().all())
    out = []
    for r in roadmaps:
        out.append(_serialize_roadmap(r, await _milestones_for(db, r.id)))
    return out


@router.post("", status_code=201)
async def create_roadmap(
    body: RoadmapCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reports.roadmap_manage")
    r = Roadmap(
        name=body.name,
        description=body.description,
        config=body.config or {},
        owner_id=user.id,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return _serialize_roadmap(r, [])


@router.get("/{roadmap_id}")
async def get_roadmap(
    roadmap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reports.ea_dashboard")
    r = (await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))).scalars().first()
    if r is None:
        raise HTTPException(404, "Roadmap not found")
    return _serialize_roadmap(r, await _milestones_for(db, r.id))


@router.get("/{roadmap_id}/data")
async def saved_roadmap_data(
    roadmap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compute the timeline for a saved roadmap using its stored config."""
    await PermissionService.require_permission(db, user, "reports.ea_dashboard")
    r = (await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))).scalars().first()
    if r is None:
        raise HTTPException(404, "Roadmap not found")
    cfg = r.config or {}
    data = await _compute_timeline(
        db,
        cfg.get("type", "Application"),
        cfg.get("group_by", "BusinessCapability"),
    )
    data["milestones"] = [_serialize_milestone(m) for m in await _milestones_for(db, r.id)]
    data["roadmap"] = _serialize_roadmap(r, [])
    return data


@router.patch("/{roadmap_id}")
async def update_roadmap(
    roadmap_id: uuid.UUID,
    body: RoadmapUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reports.roadmap_manage")
    r = (await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))).scalars().first()
    if r is None:
        raise HTTPException(404, "Roadmap not found")
    if body.name is not None:
        r.name = body.name
    if body.description is not None:
        r.description = body.description
    if body.config is not None:
        r.config = body.config
    await db.commit()
    await db.refresh(r)
    return _serialize_roadmap(r, await _milestones_for(db, r.id))


@router.delete("/{roadmap_id}", status_code=204)
async def delete_roadmap(
    roadmap_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reports.roadmap_manage")
    await db.execute(delete(Roadmap).where(Roadmap.id == roadmap_id))
    await db.commit()


# ── Milestones ─────────────────────────────────────────────────────────


@router.post("/{roadmap_id}/milestones", status_code=201)
async def add_milestone(
    roadmap_id: uuid.UUID,
    body: MilestoneIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reports.roadmap_manage")
    r = (await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id))).scalars().first()
    if r is None:
        raise HTTPException(404, "Roadmap not found")
    m = RoadmapMilestone(
        roadmap_id=roadmap_id,
        label=body.label,
        target_date=body.target_date,
        initiative_id=body.initiative_id,
        color=body.color,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return _serialize_milestone(m)


@router.patch("/milestones/{milestone_id}")
async def update_milestone(
    milestone_id: uuid.UUID,
    body: MilestoneIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reports.roadmap_manage")
    m = (
        (await db.execute(select(RoadmapMilestone).where(RoadmapMilestone.id == milestone_id)))
        .scalars()
        .first()
    )
    if m is None:
        raise HTTPException(404, "Milestone not found")
    m.label = body.label
    m.target_date = body.target_date
    m.initiative_id = body.initiative_id
    m.color = body.color
    await db.commit()
    await db.refresh(m)
    return _serialize_milestone(m)


@router.delete("/milestones/{milestone_id}", status_code=204)
async def delete_milestone(
    milestone_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reports.roadmap_manage")
    await db.execute(delete(RoadmapMilestone).where(RoadmapMilestone.id == milestone_id))
    await db.commit()
