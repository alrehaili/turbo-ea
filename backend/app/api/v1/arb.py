"""Architecture Review Board (ARB) API (Wave 2 #7).

CRUD for review records plus a live governance-context aggregation for a review's
subject card: change-impact summary, linked risks, ADRs, and standard exceptions
— pulled from the existing modules so nothing is duplicated.

[FORK FEATURE]
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.arb_review import ARB_STATUSES, ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.architecture_decision_card import ArchitectureDecisionCard
from app.models.card import Card
from app.models.governance_transition import INSTRUMENT_ARB
from app.models.risk import Risk, RiskCard
from app.models.tech_standard import StandardException, TechStandard
from app.models.user import User
from app.services import governance_transitions
from app.services.card_read_scope import CardReadScope, require_card_readable
from app.services.impact_service import gather_impact
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/arb", tags=["arb"])


class ReviewCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    subject_card_id: uuid.UUID | None = None
    summary: str | None = None


class ReviewUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    subject_card_id: uuid.UUID | None = None
    summary: str | None = None
    status: str | None = None
    decision_notes: str | None = None
    # D-39: only with ``status = deferred`` — who the deferral is due to, and why.
    delay_attribution: str | None = Field(default=None, pattern="^(governance|requester|external)$")
    delay_reason: str | None = Field(default=None, max_length=2000)


def _review_dict(r: ArbReview, subject: dict | None = None) -> dict:
    return {
        "id": str(r.id),
        "title": r.title,
        "subject_card_id": str(r.subject_card_id) if r.subject_card_id else None,
        "subject": subject,
        "summary": r.summary,
        "status": r.status,
        "decision_notes": r.decision_notes,
        "reviewer_id": str(r.reviewer_id) if r.reviewer_id else None,
        "decided_at": r.decided_at.isoformat() if r.decided_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


async def _card_brief(db: AsyncSession, cid: uuid.UUID | None) -> dict | None:
    if not cid:
        return None
    res = await db.execute(select(Card.id, Card.name, Card.type).where(Card.id == cid))
    row = res.first()
    return {"id": str(row[0]), "name": row[1], "type": row[2]} if row else None


async def _get_review(db: AsyncSession, rid: uuid.UUID, read_scope: CardReadScope) -> ArbReview:
    """The review, or 404 — also when its subject card is hidden from the reader.

    A review is about exactly one card: with the subject redacted its title and
    notes would still disclose it, so a review of a hidden card does not exist
    for the reader (decision D-30). The row itself is never touched.
    """
    res = await db.execute(select(ArbReview).where(ArbReview.id == rid))
    r = res.scalar_one_or_none()
    if r is None or (
        r.subject_card_id
        and not await read_scope.readable_card_ids(db, [r.subject_card_id], mode="module")
    ):
        raise HTTPException(status_code=404, detail="Review not found")
    return r


@router.get("")
async def list_reviews(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status: str | None = Query(None),
):
    await PermissionService.require_permission(db, user, "arb.view")
    read_scope = await CardReadScope.load(db, user)
    stmt = select(ArbReview).order_by(ArbReview.created_at.desc())
    if status:
        stmt = stmt.where(ArbReview.status == status)
    res = await db.execute(stmt)
    reviews = list(res.scalars().all())
    # Reviews of a hidden subject card are omitted (D-30); see `_get_review`.
    readable = await read_scope.readable_card_ids(
        db, {r.subject_card_id for r in reviews if r.subject_card_id}, mode="module"
    )
    reviews = [r for r in reviews if not r.subject_card_id or r.subject_card_id in readable]
    subjects = {}
    for r in reviews:
        if r.subject_card_id and r.subject_card_id not in subjects:
            subjects[r.subject_card_id] = await _card_brief(db, r.subject_card_id)
    return [_review_dict(r, subjects.get(r.subject_card_id)) for r in reviews]


@router.post("", status_code=201)
async def create_review(
    body: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "arb.manage")
    if body.subject_card_id:
        await require_card_readable(db, user, body.subject_card_id, mode="module")
    r = ArbReview(
        title=body.title,
        subject_card_id=body.subject_card_id,
        summary=body.summary,
        status="scheduled",
        created_by=user.id,
    )
    db.add(r)
    await db.flush()
    governance_transitions.record_transition(db, INSTRUMENT_ARB, r.id, None, r.status, user.id)
    await db.commit()
    await db.refresh(r)
    return _review_dict(r, await _card_brief(db, r.subject_card_id))


@router.get("/{review_id}")
async def get_review(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the review plus its live governance context (impact / risks / ADRs /
    standard exceptions) for the subject card."""
    await PermissionService.require_permission(db, user, "arb.view")
    read_scope = await CardReadScope.load(db, user)
    r = await _get_review(db, review_id, read_scope)
    out = _review_dict(r, await _card_brief(db, r.subject_card_id))

    context: dict = {"impact": None, "risks": [], "adrs": [], "exceptions": []}
    if r.subject_card_id:
        try:
            impact = await gather_impact(
                db, r.subject_card_id, depth=2, change_type="modify", read_scope=read_scope
            )
            context["impact"] = impact["summary"]
        except ValueError:
            context["impact"] = None

        # Risks linked to the subject card.
        risk_ids = (
            (
                await db.execute(
                    select(RiskCard.risk_id).where(RiskCard.card_id == r.subject_card_id)
                )
            )
            .scalars()
            .all()
        )
        if risk_ids:
            risks = (await db.execute(select(Risk).where(Risk.id.in_(risk_ids)))).scalars().all()
            context["risks"] = [
                {
                    "id": str(rk.id),
                    "reference": rk.reference,
                    "title": rk.title,
                    "level": rk.residual_level or rk.initial_level,
                    "status": rk.status,
                }
                for rk in risks
            ]

        # ADRs linked to the subject card.
        adr_ids = (
            (
                await db.execute(
                    select(ArchitectureDecisionCard.architecture_decision_id).where(
                        ArchitectureDecisionCard.card_id == r.subject_card_id
                    )
                )
            )
            .scalars()
            .all()
        )
        if adr_ids:
            adrs = (
                (
                    await db.execute(
                        select(ArchitectureDecision).where(ArchitectureDecision.id.in_(adr_ids))
                    )
                )
                .scalars()
                .all()
            )
            context["adrs"] = [
                {"id": str(a.id), "title": a.title, "status": a.status} for a in adrs
            ]

        # Standard exceptions on the subject card.
        excs = (
            await db.execute(
                select(StandardException, TechStandard.name)
                .join(TechStandard, TechStandard.id == StandardException.standard_id)
                .where(StandardException.card_id == r.subject_card_id)
            )
        ).all()
        context["exceptions"] = [
            {
                "id": str(e.id),
                "standard": name,
                "status": e.status,
                "expiry_date": e.expiry_date.isoformat() if e.expiry_date else None,
            }
            for e, name in excs
        ]

    out["context"] = context
    return out


@router.get("/{review_id}/transitions")
async def review_transitions(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The review's recorded status history (D-35); empty before Batch 3.2."""
    await PermissionService.require_permission(db, user, "arb.view")
    r = await _get_review(db, review_id, await CardReadScope.load(db, user))
    history = await governance_transitions.transition_history(db, INSTRUMENT_ARB, r.id)
    return governance_transitions.history_payload(history)


@router.patch("/{review_id}")
async def update_review(
    review_id: uuid.UUID,
    body: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "arb.manage")
    r = await _get_review(db, review_id, await CardReadScope.load(db, user))
    data = body.model_dump(exclude_unset=True)
    delay_attribution = data.pop("delay_attribution", None)
    delay_reason = data.pop("delay_reason", None)
    if (delay_attribution or delay_reason) and data.get("status") != "deferred":
        raise HTTPException(
            status_code=422,
            detail={"code": "delay_only_on_deferral", "message": "Only a deferral has a delay"},
        )
    try:
        delay_attribution, delay_reason = governance_transitions.validate_delay(
            delay_attribution, delay_reason
        )
    except governance_transitions.LifecycleError as err:
        raise HTTPException(err.status, {"code": err.code, "message": str(err)}) from err
    if data.get("subject_card_id"):
        await require_card_readable(db, user, data["subject_card_id"], mode="module")
    if "status" in data:
        if data["status"] not in ARB_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status: {data['status']}")
        # Stamps reviewer + timestamp on a decision and records the transition.
        governance_transitions.set_arb_status(
            db,
            r,
            data.pop("status"),
            user.id,
            reason=delay_reason,
            delay_attribution=delay_attribution,
        )
    for key, value in data.items():
        setattr(r, key, value)
    await db.commit()
    await db.refresh(r)
    return _review_dict(r, await _card_brief(db, r.subject_card_id))


@router.delete("/{review_id}", status_code=204)
async def delete_review(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "arb.manage")
    r = await _get_review(db, review_id, await CardReadScope.load(db, user))
    await db.delete(r)
    await db.commit()
