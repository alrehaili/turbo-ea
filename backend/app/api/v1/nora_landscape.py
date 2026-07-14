"""Plateaus + segment scopes API ([FORK] — noraPlan.md WP5.4).

Named plateaus (time-slice dates with an as-of landscape breakdown) and segment
scopes (a card-rooted cross-entity filter resolved to its in-scope cards grouped
by EA layer). Gated by the existing ``nora`` permissions.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.nora_landscape import NoraPlateau, NoraSegment
from app.models.user import User
from app.services.nora_landscape import plateau_landscape, resolve_segment
from app.services.permission_service import PermissionService

router = APIRouter(tags=["nora-landscape"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class PlateauIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    target_date: date | None = None
    sort_order: int | None = None


class SegmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    root_card_id: uuid.UUID | None = None
    include_descendants: bool = True
    include_related: bool = True
    related_type_keys: list[str] = Field(default_factory=list)
    color: str | None = Field(default=None, max_length=20)
    sort_order: int | None = None


def _plateau_dict(p: NoraPlateau) -> dict:
    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description,
        "target_date": p.target_date.isoformat() if p.target_date else None,
        "sort_order": p.sort_order,
        "built_in": p.built_in,
    }


def _segment_dict(s: NoraSegment) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "description": s.description,
        "root_card_id": str(s.root_card_id) if s.root_card_id else None,
        "include_descendants": s.include_descendants,
        "include_related": s.include_related,
        "related_type_keys": s.related_type_keys or [],
        "color": s.color,
        "sort_order": s.sort_order,
    }


# --------------------------------------------------------------------------- #
# Plateaus
# --------------------------------------------------------------------------- #
plateaus = APIRouter(prefix="/nora-plateaus", tags=["nora-landscape"])


@plateaus.get("")
async def list_plateaus(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.view")
    rows = (
        (
            await db.execute(
                select(NoraPlateau).order_by(NoraPlateau.sort_order, NoraPlateau.target_date)
            )
        )
        .scalars()
        .all()
    )
    return [_plateau_dict(p) for p in rows]


@plateaus.post("", status_code=201)
async def create_plateau(
    body: PlateauIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    p = NoraPlateau(
        name=body.name,
        description=body.description,
        target_date=body.target_date,
        sort_order=body.sort_order or 0,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return _plateau_dict(p)


@plateaus.patch("/{plateau_id}")
async def update_plateau(
    plateau_id: uuid.UUID,
    body: PlateauIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    p = (
        await db.execute(select(NoraPlateau).where(NoraPlateau.id == plateau_id))
    ).scalar_one_or_none()
    if p is None:
        raise HTTPException(404, "Plateau not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    await db.commit()
    await db.refresh(p)
    return _plateau_dict(p)


@plateaus.delete("/{plateau_id}", status_code=204)
async def delete_plateau(
    plateau_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    p = (
        await db.execute(select(NoraPlateau).where(NoraPlateau.id == plateau_id))
    ).scalar_one_or_none()
    if p is None:
        raise HTTPException(404, "Plateau not found")
    await db.delete(p)
    await db.commit()


@plateaus.get("/{plateau_id}/landscape")
async def plateau_landscape_view(
    plateau_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Lifecycle-phase + architecture-state breakdown of the landscape as of the
    plateau's target date."""
    await PermissionService.require_permission(db, user, "nora.view")
    p = (
        await db.execute(select(NoraPlateau).where(NoraPlateau.id == plateau_id))
    ).scalar_one_or_none()
    if p is None:
        raise HTTPException(404, "Plateau not found")
    if p.target_date is None:
        raise HTTPException(400, "Plateau has no target date to slice by")
    return {"plateau": _plateau_dict(p), **(await plateau_landscape(db, p.target_date))}


# --------------------------------------------------------------------------- #
# Segments
# --------------------------------------------------------------------------- #
segments = APIRouter(prefix="/nora-segments", tags=["nora-landscape"])


@segments.get("")
async def list_segments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.view")
    rows = (
        (await db.execute(select(NoraSegment).order_by(NoraSegment.sort_order, NoraSegment.name)))
        .scalars()
        .all()
    )
    return [_segment_dict(s) for s in rows]


@segments.post("", status_code=201)
async def create_segment(
    body: SegmentIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    s = NoraSegment(
        name=body.name,
        description=body.description,
        root_card_id=body.root_card_id,
        include_descendants=body.include_descendants,
        include_related=body.include_related,
        related_type_keys=body.related_type_keys,
        color=body.color,
        sort_order=body.sort_order or 0,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return _segment_dict(s)


@segments.patch("/{segment_id}")
async def update_segment(
    segment_id: uuid.UUID,
    body: SegmentIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    s = (
        await db.execute(select(NoraSegment).where(NoraSegment.id == segment_id))
    ).scalar_one_or_none()
    if s is None:
        raise HTTPException(404, "Segment not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    await db.commit()
    await db.refresh(s)
    return _segment_dict(s)


@segments.delete("/{segment_id}", status_code=204)
async def delete_segment(
    segment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    s = (
        await db.execute(select(NoraSegment).where(NoraSegment.id == segment_id))
    ).scalar_one_or_none()
    if s is None:
        raise HTTPException(404, "Segment not found")
    await db.delete(s)
    await db.commit()


@segments.get("/{segment_id}/cards")
async def resolve_segment_cards(
    segment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Resolve the segment scope to its in-scope cards grouped by EA layer."""
    await PermissionService.require_permission(db, user, "nora.view")
    s = (
        await db.execute(select(NoraSegment).where(NoraSegment.id == segment_id))
    ).scalar_one_or_none()
    if s is None:
        raise HTTPException(404, "Segment not found")
    return {"segment": _segment_dict(s), **(await resolve_segment(db, s))}


router.include_router(plateaus)
router.include_router(segments)
