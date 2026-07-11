"""EA Requirements register API ([FORK] — noraPlan.md WP6.1).

The continuous element (phase 7) of the updated NORA methodology: EA
requirements are registered, approved (governance-gated), tracked through
development cycles, and change-impact-assessed via the linked cards.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.card import Card
from app.models.ea_requirement import (
    REQUIREMENT_DOMAINS,
    REQUIREMENT_STATUSES,
    EaRequirement,
    EaRequirementCard,
)
from app.models.user import User
from app.services.event_bus import event_bus
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/ea-requirements", tags=["ea-requirements"])


class RequirementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    source: str | None = Field(default=None, max_length=200)
    domain: str | None = None
    card_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)


class RequirementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    source: str | None = Field(default=None, max_length=200)
    domain: str | None = None
    status: str | None = None
    initiative_id: uuid.UUID | None = None
    card_ids: list[uuid.UUID] | None = Field(default=None, max_length=50)


def _validate(domain=None, status=None):
    if domain is not None and domain not in REQUIREMENT_DOMAINS:
        raise HTTPException(400, f"Invalid domain: {domain}")
    if status is not None and status not in REQUIREMENT_STATUSES:
        raise HTTPException(400, f"Invalid status: {status}")


async def _card_briefs(db: AsyncSession, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, dict]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = await db.execute(select(Card.id, Card.name, Card.type).where(Card.id.in_(ids)))
    return {r[0]: {"id": str(r[0]), "name": r[1], "type": r[2]} for r in rows.all()}


async def _links_for(
    db: AsyncSession, req_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[uuid.UUID]]:
    if not req_ids:
        return {}
    rows = await db.execute(
        select(EaRequirementCard).where(EaRequirementCard.requirement_id.in_(req_ids))
    )
    out: dict[uuid.UUID, list[uuid.UUID]] = {}
    for link in rows.scalars().all():
        out.setdefault(link.requirement_id, []).append(link.card_id)
    return out


def _req_dict(
    r: EaRequirement, card_ids: list[uuid.UUID], briefs: dict, names: dict | None = None
) -> dict:
    names = names or {}
    return {
        "id": str(r.id),
        "title": r.title,
        "description": r.description,
        "source": r.source,
        "domain": r.domain,
        "status": r.status,
        "approved_by": str(r.approved_by) if r.approved_by else None,
        "approved_by_display_name": names.get(r.approved_by),
        "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        "initiative_id": str(r.initiative_id) if r.initiative_id else None,
        "initiative": briefs.get(r.initiative_id),
        "cards": [briefs[c] for c in card_ids if c in briefs],
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


async def _get_requirement(db: AsyncSession, rid: uuid.UUID) -> EaRequirement:
    row = (
        await db.execute(select(EaRequirement).where(EaRequirement.id == rid))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Requirement not found")
    return row


@router.get("")
async def list_requirements(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status: str | None = Query(None),
    domain: str | None = Query(None),
):
    await PermissionService.require_permission(db, user, "nora.view")
    stmt = select(EaRequirement).order_by(EaRequirement.created_at.desc())
    if status:
        stmt = stmt.where(EaRequirement.status == status)
    if domain:
        stmt = stmt.where(EaRequirement.domain == domain)
    reqs = list((await db.execute(stmt)).scalars().all())
    links = await _links_for(db, [r.id for r in reqs])
    briefs = await _card_briefs(
        db,
        {r.initiative_id for r in reqs} | {c for ids in links.values() for c in ids},
    )
    approver_ids = {r.approved_by for r in reqs}
    approver_ids.discard(None)
    names: dict = {}
    if approver_ids:
        res = await db.execute(select(User.id, User.display_name).where(User.id.in_(approver_ids)))
        names = dict(res.all())
    return [_req_dict(r, links.get(r.id, []), briefs, names) for r in reqs]


@router.post("", status_code=201)
async def create_requirement(
    body: RequirementCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    _validate(domain=body.domain)
    r = EaRequirement(
        title=body.title,
        description=body.description,
        source=body.source,
        domain=body.domain,
        created_by=user.id,
    )
    db.add(r)
    await db.flush()
    for cid in dict.fromkeys(body.card_ids):
        db.add(EaRequirementCard(requirement_id=r.id, card_id=cid))
    await event_bus.publish(
        "ea_requirement.created",
        {"id": str(r.id), "title": r.title},
        db=db,
        user_id=user.id,
    )
    await db.commit()
    await db.refresh(r)
    links = await _links_for(db, [r.id])
    briefs = await _card_briefs(db, set(links.get(r.id, [])))
    return _req_dict(r, links.get(r.id, []), briefs)


@router.patch("/{requirement_id}")
async def update_requirement(
    requirement_id: uuid.UUID,
    body: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    r = await _get_requirement(db, requirement_id)
    data = body.model_dump(exclude_unset=True)
    _validate(domain=data.get("domain"), status=data.get("status"))

    if data.get("status") == "approved" and r.status != "approved":
        # Approving a requirement is a governance act (same gate as the
        # program tracker's stage-gate approvals).
        if not await PermissionService.check_permission(db, user, "governance.approve_step"):
            raise HTTPException(403, "Approving a requirement requires governance.approve_step")
        r.approved_by = user.id
        r.approved_at = datetime.now(timezone.utc)
    elif data.get("status") == "proposed":
        r.approved_by = None
        r.approved_at = None

    card_ids = data.pop("card_ids", None)
    # Linking a cycle initiative moves an approved requirement into the cycle.
    if data.get("initiative_id") and r.status == "approved" and "status" not in data:
        data["status"] = "inCycle"
    for field, value in data.items():
        setattr(r, field, value)

    if card_ids is not None:
        existing = (
            await db.execute(
                select(EaRequirementCard).where(EaRequirementCard.requirement_id == r.id)
            )
        ).scalars()
        for link in existing:
            await db.delete(link)
        for cid in dict.fromkeys(card_ids):
            db.add(EaRequirementCard(requirement_id=r.id, card_id=cid))

    await event_bus.publish(
        "ea_requirement.updated",
        {"id": str(r.id), "title": r.title, "status": r.status},
        db=db,
        user_id=user.id,
    )
    await db.commit()
    await db.refresh(r)
    links = await _links_for(db, [r.id])
    briefs = await _card_briefs(db, set(links.get(r.id, [])) | {r.initiative_id})
    return _req_dict(r, links.get(r.id, []), briefs)


@router.delete("/{requirement_id}", status_code=204)
async def delete_requirement(
    requirement_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    r = await _get_requirement(db, requirement_id)
    await db.delete(r)
    await db.commit()
