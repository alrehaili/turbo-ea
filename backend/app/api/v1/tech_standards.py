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
    STANDARD_MANDATES,
    STANDARD_STATUSES,
    StandardException,
    TechStandard,
)
from app.models.user import User
from app.services.card_read_scope import CardReadScope, require_card_readable
from app.services.permission_service import PermissionService
from app.services.tech_standards_scan import scan_standard_compliance

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
    # NORA TRM metadata (noraPlan.md WP1.3)
    standard_body: str | None = Field(default=None, max_length=200)
    mandate: str = "recommended"
    review_date: date | None = None
    spec_url: str | None = Field(default=None, max_length=500)
    trm_code: str | None = Field(default=None, max_length=50)
    tech_category_id: uuid.UUID | None = None


class StandardUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    category: str | None = None
    status: str | None = None
    description: str | None = None
    rationale: str | None = None
    replacement_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    sort_order: int | None = None
    # NORA TRM metadata (noraPlan.md WP1.3)
    standard_body: str | None = Field(default=None, max_length=200)
    mandate: str | None = None
    review_date: date | None = None
    spec_url: str | None = Field(default=None, max_length=500)
    trm_code: str | None = Field(default=None, max_length=50)
    tech_category_id: uuid.UUID | None = None


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
def _standard_dict(s: TechStandard, cards: dict[uuid.UUID, dict] | None = None) -> dict:
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
        "standard_body": s.standard_body,
        "mandate": s.mandate,
        "review_date": s.review_date.isoformat() if s.review_date else None,
        "spec_url": s.spec_url,
        "trm_code": s.trm_code,
        # A category the reader may not see is redacted, name and id (D-30).
        "tech_category_id": (
            str(s.tech_category_id) if s.tech_category_id in (cards or {}) else None
        ),
        "tech_category": (cards or {}).get(s.tech_category_id) if s.tech_category_id else None,
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


async def _get_standard(db: AsyncSession, sid: uuid.UUID) -> TechStandard:
    res = await db.execute(select(TechStandard).where(TechStandard.id == sid))
    s = res.scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Standard not found")
    return s


async def _get_exception(
    db: AsyncSession, eid: uuid.UUID, read_scope: CardReadScope
) -> StandardException:
    """The exception, or 404 — also when it is about a card hidden from the reader.

    An exception exists for exactly one card and its justification names it,
    so it is omitted rather than redacted (decision D-30). The row is untouched.
    """
    res = await db.execute(select(StandardException).where(StandardException.id == eid))
    e = res.scalar_one_or_none()
    if e is None or await read_scope.hidden_card_ids(db, {e.card_id}, mode="module"):
        raise HTTPException(status_code=404, detail="Exception not found")
    return e


async def _visible_exceptions(
    db: AsyncSession, exceptions: list[StandardException], read_scope: CardReadScope
) -> list[StandardException]:
    """Drop exceptions about hidden cards (D-30)."""
    hidden = await read_scope.hidden_card_ids(
        db, {e.card_id for e in exceptions if e.card_id}, mode="module"
    )
    return [e for e in exceptions if e.card_id not in hidden]


async def _keep_hidden_links(
    db: AsyncSession, data: dict, current: dict, read_scope: CardReadScope
) -> None:
    """An explicit null for a link the reader was shown redacted keeps the link."""
    for key, value in list(data.items()):
        if value is None and current.get(key) is not None:
            if await read_scope.hidden_card_ids(db, {current[key]}, mode="module"):
                data.pop(key)


def _validate(category: str | None, status: str | None, mandate: str | None = None) -> None:
    if category is not None and category not in STANDARD_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")
    if status is not None and status not in STANDARD_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if mandate is not None and mandate not in STANDARD_MANDATES:
        raise HTTPException(status_code=400, detail=f"Invalid mandate: {mandate}")


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
    standards = list(res.scalars().all())
    cards = await _card_brief_map(
        db, {s.tech_category_id for s in standards}, await CardReadScope.load(db, user)
    )
    return [_standard_dict(s, cards) for s in standards]


@router.post("", status_code=201)
async def create_standard(
    body: StandardCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "tech_standards.manage")
    _validate(body.category, body.status, body.mandate)
    if body.tech_category_id:
        await require_card_readable(db, user, body.tech_category_id, mode="module")
    s = TechStandard(**body.model_dump())
    db.add(s)
    await db.commit()
    await db.refresh(s)
    cards = await _card_brief_map(db, {s.tech_category_id}, await CardReadScope.load(db, user))
    return _standard_dict(s, cards)


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
    read_scope = await CardReadScope.load(db, user)
    cat_cards = await _card_brief_map(db, {s.tech_category_id for s in standards}, read_scope)

    # Open (approved + non-expired, or requested) exception counts per standard.
    # Exceptions about hidden cards are not counted (D-30).
    eres = await db.execute(
        select(
            StandardException.standard_id,
            StandardException.status,
            StandardException.expiry_date,
            StandardException.card_id,
        )
    )
    exc_rows = eres.all()
    hidden = await read_scope.hidden_card_ids(
        db, {cid for *_, cid in exc_rows if cid}, mode="module"
    )
    open_exc: dict[uuid.UUID, int] = {}
    for sid, status, expiry, cid in exc_rows:
        if cid in hidden:
            continue
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
        row = {**_standard_dict(s, cat_cards), "open_exceptions": open_exc.get(s.id, 0)}
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


@router.get("/compliance-scan")
async def compliance_scan(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Flag cards using a sunset/prohibited standard without an active waiver.

    Walks Application → ITComponent → TechCategory ← TechStandard and returns
    one row per (card, violated standard), marking rows waived by an approved,
    non-expired exception.
    """
    await PermissionService.require_permission(db, user, "tech_standards.view")
    return await scan_standard_compliance(db, read_scope=await CardReadScope.load(db, user))


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
    read_scope = await CardReadScope.load(db, user)
    exceptions = await _visible_exceptions(db, list(res.scalars().all()), read_scope)
    cards = await _card_brief_map(
        db, {e.card_id for e in exceptions} | {e.initiative_id for e in exceptions}, read_scope
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
    read_scope = await CardReadScope.load(db, user)
    exceptions = await _visible_exceptions(db, list(eres.scalars().all()), read_scope)
    cards = await _card_brief_map(
        db,
        {e.card_id for e in exceptions}
        | {e.initiative_id for e in exceptions}
        | {s.tech_category_id},
        read_scope,
    )
    return {
        **_standard_dict(s, cards),
        "exceptions": [_exception_dict(e, cards) for e in exceptions],
    }


@router.patch("/{standard_id}")
async def update_standard(
    standard_id: uuid.UUID,
    body: StandardUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "tech_standards.manage")
    s = await _get_standard(db, standard_id)
    read_scope = await CardReadScope.load(db, user)
    data = body.model_dump(exclude_unset=True)
    _validate(data.get("category"), data.get("status"), data.get("mandate"))
    await _keep_hidden_links(db, data, {"tech_category_id": s.tech_category_id}, read_scope)
    if data.get("tech_category_id"):
        await require_card_readable(db, user, data["tech_category_id"], mode="module")
    for key, value in data.items():
        setattr(s, key, value)
    await db.commit()
    await db.refresh(s)
    return _standard_dict(s, await _card_brief_map(db, {s.tech_category_id}, read_scope))


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
    for cid in (body.card_id, body.initiative_id):
        if cid:
            await require_card_readable(db, user, cid, mode="module")
    exc = StandardException(
        standard_id=standard_id,
        status="requested",
        created_by=user.id,
        **body.model_dump(),
    )
    db.add(exc)
    await db.commit()
    await db.refresh(exc)
    cards = await _card_brief_map(
        db, {exc.card_id, exc.initiative_id}, await CardReadScope.load(db, user)
    )
    return _exception_dict(exc, cards)


@router.patch("/exceptions/{exception_id}")
async def update_exception(
    exception_id: uuid.UUID,
    body: ExceptionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "tech_standards.manage")
    read_scope = await CardReadScope.load(db, user)
    exc = await _get_exception(db, exception_id, read_scope)
    data = body.model_dump(exclude_unset=True)
    await _keep_hidden_links(
        db, data, {"initiative_id": exc.initiative_id, "card_id": exc.card_id}, read_scope
    )
    for key in ("card_id", "initiative_id"):
        if data.get(key):
            await require_card_readable(db, user, data[key], mode="module")
    for key, value in data.items():
        setattr(exc, key, value)
    await db.commit()
    await db.refresh(exc)
    cards = await _card_brief_map(db, {exc.card_id, exc.initiative_id}, read_scope)
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
    read_scope = await CardReadScope.load(db, user)
    exc = await _get_exception(db, exception_id, read_scope)
    if exc.status not in ("requested", "approved", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot decide on status {exc.status}")
    exc.status = "approved" if action == "approve" else "rejected"
    exc.approver_id = user.id
    await db.commit()
    await db.refresh(exc)
    cards = await _card_brief_map(db, {exc.card_id, exc.initiative_id}, read_scope)
    return _exception_dict(exc, cards)


@router.delete("/exceptions/{exception_id}", status_code=204)
async def delete_exception(
    exception_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "tech_standards.manage")
    exc = await _get_exception(db, exception_id, await CardReadScope.load(db, user))
    await db.delete(exc)
    await db.commit()
