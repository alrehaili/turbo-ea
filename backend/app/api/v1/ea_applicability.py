"""EA governance applicability of an initiative (D-37; Batch 3.6).

* ``GET  /cards/{id}/ea-applicability`` — the current status and the full
  assessment history, to anyone who may read the initiative.
* ``POST /cards/{id}/ea-applicability`` — append one assessment
  (``governance.assess_applicability``, no default role).

Rules live in ``services/ea_applicability.py``.

[FORK]
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.card import Card
from app.models.user import User
from app.services import ea_applicability as ea
from app.services.card_read_scope import require_card_readable
from app.services.governance_transitions import LifecycleError
from app.services.permission_service import PermissionService

router = APIRouter(tags=["EA governance"])


class AssessmentCreate(BaseModel):
    decision: str = Field(pattern="^(required|not_required)$")
    criteria_reference: str = Field(min_length=1, max_length=300)
    justification: str = Field(min_length=1, max_length=4000)


async def _initiative(db: AsyncSession, user: User, card_id: uuid.UUID) -> Card:
    await require_card_readable(db, user, card_id, mode="module")
    card = await db.get(Card, card_id)
    if card is None:
        raise HTTPException(404, "Card not found")
    return card


async def _payload(db: AsyncSession, user: User, card: Card) -> dict:
    history = await ea.assessment_history(db, card.id)
    ids = {r.decided_by for r in history if r.decided_by}
    names = (
        dict((await db.execute(select(User.id, User.display_name).where(User.id.in_(ids)))).all())
        if ids
        else {}
    )
    return {
        "card_id": str(card.id),
        "current": ea.assessment_payload(history[0], names) if history else None,
        "status": history[0].decision if history else "undetermined",
        "history": [ea.assessment_payload(r, names) for r in history],
        "can_assess": await PermissionService.check_permission(db, user, ea.ASSESS_PERMISSION),
    }


@router.get("/cards/{card_id}/ea-applicability")
async def get_applicability(
    card_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _payload(db, user, await _initiative(db, user, card_id))


@router.post("/cards/{card_id}/ea-applicability", status_code=201)
async def assess_applicability(
    card_id: uuid.UUID,
    body: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, ea.ASSESS_PERMISSION)
    card = await _initiative(db, user, card_id)
    try:
        await ea.record_assessment(
            db, card, body.decision, body.criteria_reference, body.justification, user.id
        )
    except LifecycleError as err:
        raise HTTPException(err.status, {"code": err.code, "message": str(err)}) from err
    await db.commit()
    return await _payload(db, user, card)
