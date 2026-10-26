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
from app.models.governance_transition import INSTRUMENT_EXCEPTION
from app.models.tech_standard import (
    STANDARD_CATEGORIES,
    STANDARD_MANDATES,
    STANDARD_STATUSES,
    WAIVER_ACTIVE_STATUSES,
    StandardException,
    TechStandard,
)
from app.models.user import User
from app.services import audit_log, governance_transitions
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


class RemediationSubmit(BaseModel):
    evidence: str = Field(min_length=1, max_length=10000)


class RemediationVerify(BaseModel):
    outcome: str = Field(pattern="^(verified|returned)$")
    note: str | None = Field(default=None, max_length=5000)


class ExceptionWithdraw(BaseModel):
    reason: str = Field(min_length=1, max_length=5000)


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

    # Past expiry and still relying on the waiver: shown as expired while only
    # approved; a submitted remediation keeps its own status and says so.
    past_expiry = bool(
        e.expiry_date and e.expiry_date < date.today() and e.status in WAIVER_ACTIVE_STATUSES
    )
    expired = past_expiry and e.status == "approved"
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
        # Latest approve / reject; null for decisions taken before it was kept.
        "decided_at": e.decided_at.isoformat() if e.decided_at else None,
        "past_expiry": past_expiry,
        "created_by": str(e.created_by) if e.created_by else None,
        # Remediation and withdrawal (D-40); null on records that never had them.
        "remediation_evidence": e.remediation_evidence,
        "remediation_submitted_by": (
            str(e.remediation_submitted_by) if e.remediation_submitted_by else None
        ),
        "remediation_submitted_at": _iso(e.remediation_submitted_at),
        "remediation_verified_by": (
            str(e.remediation_verified_by) if e.remediation_verified_by else None
        ),
        "remediation_verified_at": _iso(e.remediation_verified_at),
        "withdrawn_at": _iso(e.withdrawn_at),
        "withdrawal_reason": e.withdrawal_reason,
    }


def _iso(moment) -> str | None:
    return moment.isoformat() if moment else None


def _lifecycle_http(err: governance_transitions.LifecycleError) -> HTTPException:
    return HTTPException(status_code=err.status, detail={"code": err.code, "message": str(err)})


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
            status in WAIVER_ACTIVE_STATUSES and (expiry is None or expiry >= date.today())
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
    # The cascade would hard-delete decided exceptions, which only an audited
    # administrative correction may do (D-40, I-28).
    decided = await db.scalar(
        select(StandardException.id)
        .where(StandardException.standard_id == s.id, StandardException.status != "requested")
        .limit(1)
    )
    if decided is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "exceptions_have_lifecycle",
                "message": "This standard has decided exceptions; withdraw or keep them instead",
            },
        )
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
    await db.flush()
    governance_transitions.record_transition(
        db, INSTRUMENT_EXCEPTION, exc.id, None, exc.status, user.id
    )
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
    governance_transitions.decide_exception(db, exc, action, user.id)
    await db.commit()
    await db.refresh(exc)
    cards = await _card_brief_map(db, {exc.card_id, exc.initiative_id}, read_scope)
    return _exception_dict(exc, cards)


@router.get("/exceptions/{exception_id}/transitions")
async def exception_transitions(
    exception_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The exception's recorded status history (D-34); empty before Batch 3.2."""
    await PermissionService.require_permission(db, user, "tech_standards.view")
    exc = await _get_exception(db, exception_id, await CardReadScope.load(db, user))
    history = await governance_transitions.transition_history(db, INSTRUMENT_EXCEPTION, exc.id)
    return governance_transitions.history_payload(history)


@router.post("/exceptions/{exception_id}/remediation")
async def submit_remediation(
    exception_id: uuid.UUID,
    body: RemediationSubmit,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit remediation evidence for an approved exception (D-40)."""
    await PermissionService.require_permission(db, user, "tech_standards.manage")
    read_scope = await CardReadScope.load(db, user)
    exc = await _get_exception(db, exception_id, read_scope)
    try:
        governance_transitions.submit_remediation(db, exc, body.evidence, user.id)
    except governance_transitions.LifecycleError as err:
        raise _lifecycle_http(err) from err
    await db.commit()
    await db.refresh(exc)
    cards = await _card_brief_map(db, {exc.card_id, exc.initiative_id}, read_scope)
    return _exception_dict(exc, cards)


@router.post("/exceptions/{exception_id}/remediation/verify")
async def verify_remediation(
    exception_id: uuid.UUID,
    body: RemediationVerify,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Independently verify submitted remediation, or return it (D-40)."""
    await PermissionService.require_permission(db, user, "tech_standards.approve_exception")
    read_scope = await CardReadScope.load(db, user)
    exc = await _get_exception(db, exception_id, read_scope)
    try:
        governance_transitions.verify_remediation(db, exc, body.outcome, body.note, user.id)
    except governance_transitions.LifecycleError as err:
        raise _lifecycle_http(err) from err
    await db.commit()
    await db.refresh(exc)
    cards = await _card_brief_map(db, {exc.card_id, exc.initiative_id}, read_scope)
    return _exception_dict(exc, cards)


@router.post("/exceptions/{exception_id}/withdraw")
async def withdraw_exception(
    exception_id: uuid.UUID,
    body: ExceptionWithdraw,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Withdraw a pending or approved exception with a reason (D-40).

    The original requester or a holder of ``tech_standards.manage``."""
    await PermissionService.require_permission(db, user, "tech_standards.view")
    read_scope = await CardReadScope.load(db, user)
    exc = await _get_exception(db, exception_id, read_scope)
    is_manager = await PermissionService.check_permission(db, user, "tech_standards.manage")
    if not governance_transitions.may_withdraw(exc, user.id, is_manager=is_manager):
        raise HTTPException(
            status_code=403,
            detail={"code": "not_requester", "message": "Only the requester or a manager"},
        )
    try:
        governance_transitions.withdraw_exception(db, exc, body.reason, user.id)
    except governance_transitions.LifecycleError as err:
        raise _lifecycle_http(err) from err
    await db.commit()
    await db.refresh(exc)
    cards = await _card_brief_map(db, {exc.card_id, exc.initiative_id}, read_scope)
    return _exception_dict(exc, cards)


@router.delete("/exceptions/{exception_id}", status_code=204)
async def delete_exception(
    exception_id: uuid.UUID,
    reason: str | None = Query(None, max_length=2000),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Permanently delete an exception recorded in error (D-40, I-27).

    An administrative correction: it needs ``tech_standards.delete_exception``
    (no default role holds it) and a reason, writes an admin audit record, and
    leaves a final ``deleted`` row in the exception's history. Routine closing
    is a withdrawal, not a delete."""
    await PermissionService.require_permission(db, user, "tech_standards.delete_exception")
    exc = await _get_exception(db, exception_id, await CardReadScope.load(db, user))
    try:
        governance_transitions.record_deletion(db, exc, reason, user.id)
    except governance_transitions.LifecycleError as err:
        raise _lifecycle_http(err) from err
    standard = await db.get(TechStandard, exc.standard_id)
    card_name = (
        await db.scalar(select(Card.name).where(Card.id == exc.card_id)) if exc.card_id else None
    )
    await audit_log.record(
        db,
        action="admin.tech_standard_exception.deleted",
        category="admin",
        actor=user,
        target=("tech_standard_exception", str(exc.id), standard.name if standard else None),
        context={
            "standard": standard.name if standard else None,
            "card": card_name,
            "status": exc.status,
            "deletion_reason": reason.strip() if reason else None,
        },
    )
    await db.delete(exc)
    await db.commit()
