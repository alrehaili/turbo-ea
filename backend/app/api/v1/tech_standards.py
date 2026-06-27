"""Technology Standards catalogue + exception register API (Wave 2 #5).

A clean, separate catalogue from the principle-linked ``standards`` table. See
``app.models.tech_standard`` for the data model.

[FORK FEATURE]
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.card import Card
from app.models.tech_standard import (
    STANDARD_CATEGORIES,
    STANDARD_STATUSES,
    StandardException,
    TechStandard,
)
from app.models.user import User
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/tech-standards", tags=["tech-standards"])


# --------------------------------------------------------------------------- #
# Schemas                                                                      #
# --------------------------------------------------------------------------- #
class StandardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    category: str = "technology"
    status: str = "allowed"
    description: str | None = None
    rationale: str | None = None
    replacement_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    sort_order: int = 0


class StandardUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    category: str | None = None
    status: str | None = None
    description: str | None = None
    rationale: str | None = None
    replacement_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    sort_order: int | None = None


class ExceptionCreate(BaseModel):
    card_id: uuid.UUID | None = None
    initiative_id: uuid.UUID | None = None
    justification: str | None = None
    compensating_controls: str | None = None
    expiry_date: date | None = None


class ExceptionUpdate(BaseModel):
    card_id: uuid.UUID | None = None
    initiative_id: uuid.UUID | None = None
    justification: str | None = None
    compensating_controls: str | None = None
    expiry_date: date | None = None


# --------------------------------------------------------------------------- #
# Serialisation                                                                #
# --------------------------------------------------------------------------- #
def _standard_dict(s: TechStandard) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "category": s.category,
        "status": s.status,
        "description": s.description,
        "rationale": s.rationale,
        "replacement_id": str(s.replacement_id) if s.replacement_id else None,
        "owner_id": str(s.owner_id) if s.owner_id else None,
        "sort_order": s.sort_order,
    }


def _exception_dict(e: StandardException, cards: dict[uuid.UUID, dict]) -> dict:
    def brief(cid: uuid.UUID | None) -> dict | None:
        return cards.get(cid) if cid else None

    expired = bool(e.expiry_date and e.expiry_date < date.today() and e.status == "approved")
    return {
        "id": str(e.id),
        "standard_id": str(e.standard_id),
        "card": brief(e.card_id),
        "initiative": brief(e.initiative_id),
        "justification": e.justification,
        "compensating_controls": e.compensating_controls,
        "status": "expired" if expired else e.status,
        "expiry_date": e.expiry_date.isoformat() if e.expiry_date else None,
        "approver_id": str(e.approver_id) if e.approver_id else None,
    }


async def _card_brief_map(db: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, dict]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    res = await db.execute(select(Card.id, Card.name, Card.type).where(Card.id.in_(ids)))
    return {row[0]: {"id": str(row[0]), "name": row[1], "type": row[2]} for row in res.all()}


async def _get_standard(db: AsyncSession, sid: uuid.UUID) -> TechStandard:
    res = await db.execute(select(TechStandard).where(TechStandard.id == sid))
    s = res.scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Standard not found")
    return s


async def _get_exception(db: AsyncSession, eid: uuid.UUID) -> StandardException:
    res = await db.execute(select(StandardException).where(StandardException.id == eid))
    e = res.scalar_one_or_none()
    if e is None:
        raise HTTPException(status_code=404, detail="Exception not found")
    return e


def _validate(category: str | None, status: str | None) -> None:
    if category is not None and category not in STANDARD_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    if status is not None and status not in STANDARD_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")


# --------------------------------------------------------------------------- #
# Standards CRUD                                                               #
# --------------------------------------------------------------------------- #
@router.get("")
async def list_standards(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    category: str | None = Query(None),
    status: str | None = Query(None),
):
    await PermissionService.require_permission(db, user, "tech_standards.view")
    stmt = select(TechStandard).order_by(TechStandard.sort_order, TechStandard.name)
    if category:
        stmt = stmt.where(TechStandard.category == category)
    if status:
        stmt = stmt.where(TechStandard.status == status)
    res = await db.execute(stmt)
    return [_standard_dict(s) for s in res.scalars().all()]


@router.post("", status_code=201)
async def create_standard(
    body: StandardCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "tech_standards.manage")
    _validate(body.category, body.status)
    s = TechStandard(**body.model_dump())
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return _standard_dict(s)


@router.get("/radar")
async def radar(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Radar / heatmap matrix: standards grouped by category × adoption status,
    plus open-exception counts per standard."""
    await PermissionService.require_permission(db, user, "tech_standards.view")
    res = await db.execute(select(TechStandard).order_by(TechStandard.name))
    standards = list(res.scalars().all())

    # Open (approved + non-expired, or requested) exception counts per standard.
    eres = await db.execute(
        select(
            StandardException.standard_id, StandardException.status, StandardException.expiry_date
        )
    )
    open_exc: dict[uuid.UUID, int] = {}
    for sid, status, expiry in eres.all():
        is_open = status == "requested" or (
            status == "approved" and (expiry is None or expiry >= date.today())
        )
        if is_open:
            open_exc[sid] = open_exc.get(sid, 0) + 1

    matrix: dict[str, dict[str, list[dict]]] = {
        cat: {st: [] for st in STANDARD_STATUSES} for cat in STANDARD_CATEGORIES
    }
    by_status: dict[str, int] = {st: 0 for st in STANDARD_STATUSES}
    for s in standards:
        cat = s.category if s.category in matrix else "other"
        st = s.status if s.status in by_status else "allowed"
        row = {**_standard_dict(s), "open_exceptions": open_exc.get(s.id, 0)}
        matrix[cat][st].append(row)
        by_status[st] += 1

    return {
        "categories": list(STANDARD_CATEGORIES),
        "statuses": list(STANDARD_STATUSES),
        "matrix": matrix,
        "summary": {
            "total": len(standards),
            "by_status": by_status,
            "open_exceptions": sum(open_exc.values()),
        },
    }


@router.get("/exceptions")
async def list_exceptions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status: str | None = Query(None),
):
    await PermissionService.require_permission(db, user, "tech_standards.view")
    stmt = select(StandardException).order_by(StandardException.created_at.desc())
    if status:
        stmt = stmt.where(StandardException.status == status)
    res = await db.execute(stmt)
    exceptions = list(res.scalars().all())
    cards = await _card_brief_map(
        db, {e.card_id for e in exceptions} | {e.initiative_id for e in exceptions}
    )
    return [_exception_dict(e, cards) for e in exceptions]


@router.get("/{standard_id}")
async def get_standard(
    standard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "tech_standards.view")
    s = await _get_standard(db, standard_id)
    eres = await db.execute(
        select(StandardException)
        .where(StandardException.standard_id == standard_id)
        .order_by(StandardException.created_at.desc())
    )
    exceptions = list(eres.scalars().all())
    cards = await _card_brief_map(
        db, {e.card_id for e in exceptions} | {e.initiative_id for e in exceptions}
    )
    return {**_standard_dict(s), "exceptions": [_exception_dict(e, cards) for e in exceptions]}


@router.patch("/{standard_id}")
async def update_standard(
    standard_id: uuid.UUID,
    body: StandardUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "tech_standards.manage")
    s = await _get_standard(db, standard_id)
    data = body.model_dump(exclude_unset=True)
    _validate(data.get("category"), data.get("status"))
    for key, value in data.items():
        setattr(s, key, value)
    await db.commit()
    await db.refresh(s)
    return _standard_dict(s)


@router.delete("/{standard_id}", status_code=204)
async def delete_standard(
    standard_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "tech_standards.manage")
    s = await _get_standard(db, standard_id)
    await db.delete(s)
    await db.commit()


# --------------------------------------------------------------------------- #
# Exception register                                                          #
# --------------------------------------------------------------------------- #
@router.post("/{standard_id}/exceptions", status_code=201)
async def create_exception(
    standard_id: uuid.UUID,
    body: ExceptionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "tech_standards.manage")
    await _get_standard(db, standard_id)
    exc = StandardException(
        standard_id=standard_id,
        status="requested",
        created_by=user.id,
        **body.model_dump(),
    )
    db.add(exc)
    await db.commit()
    await db.refresh(exc)
    cards = await _card_brief_map(db, {exc.card_id, exc.initiative_id})
    return _exception_dict(exc, cards)


@router.patch("/exceptions/{exception_id}")
async def update_exception(
    exception_id: uuid.UUID,
    body: ExceptionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "tech_standards.manage")
    exc = await _get_exception(db, exception_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(exc, key, value)
    await db.commit()
    await db.refresh(exc)
    cards = await _card_brief_map(db, {exc.card_id, exc.initiative_id})
    return _exception_dict(exc, cards)


@router.post("/exceptions/{exception_id}/decision")
async def decide_exception(
    exception_id: uuid.UUID,
    action: str = Query(..., pattern="^(approve|reject)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Approve or reject an exception request (separate approver permission)."""
    await PermissionService.require_permission(db, user, "tech_standards.approve_exception")
    exc = await _get_exception(db, exception_id)
    if exc.status not in ("requested", "approved", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot decide on status {exc.status}")
    exc.status = "approved" if action == "approve" else "rejected"
    exc.approver_id = user.id
    await db.commit()
    await db.refresh(exc)
    cards = await _card_brief_map(db, {exc.card_id, exc.initiative_id})
    return _exception_dict(exc, cards)


@router.delete("/exceptions/{exception_id}", status_code=204)
async def delete_exception(
    exception_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "tech_standards.manage")
    exc = await _get_exception(db, exception_id)
    await db.delete(exc)
    await db.commit()
