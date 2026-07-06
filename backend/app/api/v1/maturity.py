"""EA maturity self-assessment API ([FORK] — noraPlan.md WP5.2).

Admin-definable maturity dimensions + dated self-assessments scored on a fixed
1–5 scale, with a radar/trend overview and per-dimension gap promotion into the
Improvement Opportunity registry (WP3.3).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.improvement_opportunity import ImprovementOpportunity
from app.models.maturity import (
    MATURITY_ASSESSMENT_STATUSES,
    MATURITY_MAX_LEVEL,
    MaturityAssessment,
    MaturityDimension,
    MaturityDimensionScore,
)
from app.models.user import User
from app.services.event_bus import event_bus
from app.services.maturity import (
    assessment_dict,
    compute_overall_score,
    dimension_dict,
    score_dict,
)
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/maturity", tags=["maturity"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class DimensionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    weight: int = Field(default=1, ge=1, le=10)


class DimensionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    weight: int | None = Field(default=None, ge=1, le=10)
    sort_order: int | None = None
    is_active: bool | None = None


class AssessmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    assessment_date: date | None = None


class AssessmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    assessment_date: date | None = None
    notes: str | None = None
    status: str | None = None


class ScoreUpdate(BaseModel):
    level: int | None = Field(default=None, ge=0, le=MATURITY_MAX_LEVEL)
    target_level: int | None = Field(default=None, ge=0, le=MATURITY_MAX_LEVEL)
    notes: str | None = None


class PromoteOpportunity(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    domain: str = Field(default="BA", max_length=4)
    priority: str = Field(default="medium", max_length=8)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def _get_assessment(db: AsyncSession, aid: uuid.UUID) -> MaturityAssessment:
    row = (
        await db.execute(select(MaturityAssessment).where(MaturityAssessment.id == aid))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Assessment not found")
    return row


async def _scores_for(db: AsyncSession, aid: uuid.UUID) -> list[MaturityDimensionScore]:
    return list(
        (
            await db.execute(
                select(MaturityDimensionScore).where(MaturityDimensionScore.assessment_id == aid)
            )
        )
        .scalars()
        .all()
    )


async def _user_names(db: AsyncSession, ids: set) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    res = await db.execute(select(User.id, User.display_name).where(User.id.in_(ids)))
    return dict(res.all())


# --------------------------------------------------------------------------- #
# Dimensions (admin-definable catalogue)
# --------------------------------------------------------------------------- #
@router.get("/dimensions")
async def list_dimensions(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "maturity.view")
    stmt = select(MaturityDimension)
    if not include_inactive:
        stmt = stmt.where(MaturityDimension.is_active.is_(True))
    stmt = stmt.order_by(MaturityDimension.sort_order, MaturityDimension.name)
    rows = (await db.execute(stmt)).scalars().all()
    return [dimension_dict(d) for d in rows]


@router.post("/dimensions", status_code=201)
async def create_dimension(
    body: DimensionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "maturity.manage")
    max_sort = (
        (
            await db.execute(
                select(MaturityDimension.sort_order).order_by(MaturityDimension.sort_order.desc())
            )
        )
        .scalars()
        .first()
    )
    d = MaturityDimension(
        key=f"custom_{uuid.uuid4().hex[:12]}",
        name=body.name,
        description=body.description,
        weight=body.weight,
        sort_order=(max_sort or 0) + 1,
        is_active=True,
        built_in=False,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return dimension_dict(d)


@router.patch("/dimensions/{dimension_id}")
async def update_dimension(
    dimension_id: uuid.UUID,
    body: DimensionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "maturity.manage")
    d = (
        await db.execute(select(MaturityDimension).where(MaturityDimension.id == dimension_id))
    ).scalar_one_or_none()
    if d is None:
        raise HTTPException(404, "Dimension not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(d, field, value)
    await db.commit()
    await db.refresh(d)
    return dimension_dict(d)


@router.delete("/dimensions/{dimension_id}", status_code=204)
async def delete_dimension(
    dimension_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a custom dimension. Built-in dimensions are deactivated instead
    (so seeded assessments stay auditable)."""
    await PermissionService.require_permission(db, user, "maturity.manage")
    d = (
        await db.execute(select(MaturityDimension).where(MaturityDimension.id == dimension_id))
    ).scalar_one_or_none()
    if d is None:
        raise HTTPException(404, "Dimension not found")
    if d.built_in:
        raise HTTPException(400, "Built-in dimensions cannot be deleted — deactivate them instead")
    await db.delete(d)
    await db.commit()


# --------------------------------------------------------------------------- #
# Assessments
# --------------------------------------------------------------------------- #
@router.get("/assessments")
async def list_assessments(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "maturity.view")
    rows = list(
        (
            await db.execute(
                select(MaturityAssessment).order_by(
                    MaturityAssessment.assessment_date.desc(),
                    MaturityAssessment.created_at.desc(),
                )
            )
        )
        .scalars()
        .all()
    )
    names = await _user_names(db, {a.approved_by for a in rows})
    return [assessment_dict(a, names=names) for a in rows]


@router.post("/assessments", status_code=201)
async def create_assessment(
    body: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a draft assessment with one score row per active dimension."""
    await PermissionService.require_permission(db, user, "maturity.manage")
    a = MaturityAssessment(
        title=body.title,
        assessment_date=body.assessment_date or date.today(),
        status="draft",
        created_by=user.id,
    )
    db.add(a)
    await db.flush()

    dims = (
        (
            await db.execute(
                select(MaturityDimension)
                .where(MaturityDimension.is_active.is_(True))
                .order_by(MaturityDimension.sort_order, MaturityDimension.name)
            )
        )
        .scalars()
        .all()
    )
    for dim in dims:
        db.add(
            MaturityDimensionScore(
                assessment_id=a.id,
                dimension_id=dim.id,
                dimension_key=dim.key,
                dimension_name=dim.name,
                weight=dim.weight,
                sort_order=dim.sort_order,
                level=0,
                target_level=0,
            )
        )
    await db.commit()
    scores = await _scores_for(db, a.id)
    return assessment_dict(a, scores=scores)


@router.get("/assessments/{assessment_id}")
async def get_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "maturity.view")
    a = await _get_assessment(db, assessment_id)
    scores = await _scores_for(db, a.id)
    names = await _user_names(db, {a.approved_by})
    return assessment_dict(a, scores=scores, names=names)


@router.patch("/assessments/{assessment_id}")
async def update_assessment(
    assessment_id: uuid.UUID,
    body: AssessmentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "maturity.manage")
    a = await _get_assessment(db, assessment_id)
    data = body.model_dump(exclude_unset=True)

    if "status" in data:
        status = data["status"]
        if status not in MATURITY_ASSESSMENT_STATUSES:
            raise HTTPException(400, f"Invalid status: {status}")
        if status == "approved" and a.status != "approved":
            if not await PermissionService.check_permission(db, user, "governance.approve_step"):
                raise HTTPException(403, "Approving an assessment requires governance.approve_step")
            a.approved_by = user.id
            a.approved_at = datetime.now(timezone.utc)
        elif status != "approved":
            a.approved_by = None
            a.approved_at = None
        # Recompute the overall score whenever the assessment leaves draft.
        if status in ("submitted", "approved"):
            a.overall_score = compute_overall_score(await _scores_for(db, a.id))

    for field, value in data.items():
        setattr(a, field, value)

    await event_bus.publish(
        "maturity.assessment_updated",
        {"id": str(a.id), "status": a.status, "overall_score": a.overall_score},
        db=db,
        user_id=user.id,
    )
    await db.commit()
    await db.refresh(a)
    scores = await _scores_for(db, a.id)
    names = await _user_names(db, {a.approved_by})
    return assessment_dict(a, scores=scores, names=names)


@router.delete("/assessments/{assessment_id}", status_code=204)
async def delete_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "maturity.manage")
    a = await _get_assessment(db, assessment_id)
    await db.delete(a)
    await db.commit()


@router.patch("/assessments/{assessment_id}/scores/{score_id}")
async def update_score(
    assessment_id: uuid.UUID,
    score_id: uuid.UUID,
    body: ScoreUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "maturity.manage")
    s = (
        await db.execute(
            select(MaturityDimensionScore).where(
                MaturityDimensionScore.id == score_id,
                MaturityDimensionScore.assessment_id == assessment_id,
            )
        )
    ).scalar_one_or_none()
    if s is None:
        raise HTTPException(404, "Score not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(s, field, value)

    # Keep a submitted/approved assessment's headline score in sync with edits.
    a = await _get_assessment(db, assessment_id)
    if a.status in ("submitted", "approved"):
        a.overall_score = compute_overall_score(await _scores_for(db, a.id))
    await db.commit()
    await db.refresh(s)
    return score_dict(s)


@router.post("/assessments/{assessment_id}/scores/{score_id}/promote-opportunity", status_code=201)
async def promote_score_to_opportunity(
    assessment_id: uuid.UUID,
    score_id: uuid.UUID,
    body: PromoteOpportunity,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Spawn an Improvement Opportunity from a dimension gap (WP3.3 feed)."""
    await PermissionService.require_permission(db, user, "maturity.manage")
    await PermissionService.require_permission(db, user, "grc.manage")
    s = (
        await db.execute(
            select(MaturityDimensionScore).where(
                MaturityDimensionScore.id == score_id,
                MaturityDimensionScore.assessment_id == assessment_id,
            )
        )
    ).scalar_one_or_none()
    if s is None:
        raise HTTPException(404, "Score not found")

    title = body.title or f"Improve maturity: {s.dimension_name}"
    gap = max(0, (s.target_level or 0) - (s.level or 0))
    description = (
        f"Maturity gap on '{s.dimension_name}': current level {s.level}/"
        f"{MATURITY_MAX_LEVEL}, target level {s.target_level}/{MATURITY_MAX_LEVEL} "
        f"(gap of {gap})."
    )
    opp = ImprovementOpportunity(
        title=title[:300],
        description=description,
        domain=body.domain,
        source="maturity",
        priority=body.priority,
        status="proposed",
        created_by=user.id,
    )
    db.add(opp)
    await event_bus.publish(
        "improvement_opportunity.created",
        {"id": None, "source": "maturity", "dimension": s.dimension_key},
        db=db,
        user_id=user.id,
    )
    await db.commit()
    await db.refresh(opp)
    return {"id": str(opp.id), "title": opp.title, "source": opp.source, "status": opp.status}


# --------------------------------------------------------------------------- #
# Overview (radar + trend)
# --------------------------------------------------------------------------- #
@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Latest-assessment radar + trend across dated assessments."""
    await PermissionService.require_permission(db, user, "maturity.view")

    assessments = list(
        (
            await db.execute(
                select(MaturityAssessment).order_by(MaturityAssessment.assessment_date.asc())
            )
        )
        .scalars()
        .all()
    )
    # Trend: submitted/approved assessments with a computed overall score.
    trend = [
        {
            "id": str(a.id),
            "title": a.title,
            "date": a.assessment_date.isoformat() if a.assessment_date else None,
            "overall_score": a.overall_score,
            "status": a.status,
        }
        for a in assessments
        if a.status in ("submitted", "approved") and a.overall_score is not None
    ]

    # Radar: the most recent assessment (any status), per-dimension level vs target.
    latest = assessments[-1] if assessments else None
    radar: list[dict] = []
    below_target = 0
    if latest is not None:
        scores = await _scores_for(db, latest.id)
        for s in sorted(scores, key=lambda s: (s.sort_order, s.dimension_name)):
            radar.append(
                {
                    "dimension_key": s.dimension_key,
                    "dimension_name": s.dimension_name,
                    "level": s.level,
                    "target_level": s.target_level,
                    "max_level": MATURITY_MAX_LEVEL,
                }
            )
            if s.target_level and s.level < s.target_level:
                below_target += 1

    return {
        "latest": assessment_dict(latest) if latest else None,
        "radar": radar,
        "trend": trend,
        "summary": {
            "overall_score": latest.overall_score if latest else None,
            "dimensions": len(radar),
            "below_target": below_target,
            "assessments": len(assessments),
            "max_level": MATURITY_MAX_LEVEL,
        },
    }
