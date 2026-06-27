"""Architecture Review Board (ARB) API (Wave 2 #7).

CRUD for review records plus a live governance-context aggregation for a review's
subject card: change-impact summary, linked risks, ADRs, and standard exceptions
— pulled from the existing modules so nothing is duplicated.

[FORK FEATURE]
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
from app.models.arb_review import ARB_STATUSES, ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.architecture_decision_card import ArchitectureDecisionCard
from app.models.card import Card
from app.models.risk import Risk, RiskCard
from app.models.tech_standard import StandardException, TechStandard
from app.models.user import User
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


async def _get_review(db: AsyncSession, rid: uuid.UUID) -> ArbReview:
    res = await db.execute(select(ArbReview).where(ArbReview.id == rid))
    r = res.scalar_one_or_none()
    if r is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return r


@router.get("")
async def list_reviews(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status: str | None = Query(None),
):
    await PermissionService.require_permission(db, user, "arb.view")
    stmt = select(ArbReview).order_by(ArbReview.created_at.desc())
    if status:
        stmt = stmt.where(ArbReview.status == status)
    res = await db.execute(stmt)
    reviews = list(res.scalars().all())
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
    r = ArbReview(
        title=body.title,
        subject_card_id=body.subject_card_id,
        summary=body.summary,
        status="scheduled",
        created_by=user.id,
    )
    db.add(r)
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
    r = await _get_review(db, review_id)
    out = _review_dict(r, await _card_brief(db, r.subject_card_id))

    context: dict = {"impact": None, "risks": [], "adrs": [], "exceptions": []}
    if r.subject_card_id:
        try:
            impact = await gather_impact(db, r.subject_card_id, depth=2, change_type="modify")
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


@router.patch("/{review_id}")
async def update_review(
    review_id: uuid.UUID,
    body: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "arb.manage")
    r = await _get_review(db, review_id)
    data = body.model_dump(exclude_unset=True)
    if "status" in data:
        if data["status"] not in ARB_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status: {data['status']}")
        # Stamp reviewer + timestamp when a decision is recorded.
        if data["status"] in ("approved", "rejected", "deferred"):
            r.reviewer_id = user.id
            r.decided_at = datetime.now(timezone.utc)
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
    r = await _get_review(db, review_id)
    await db.delete(r)
    await db.commit()
