"""Risk ↔ EA governance-record links (D-42; Batch 3.5).

* ``GET    /risks/{id}/governance-links`` — the risk's links the reader may see
  (``risks.view``; a record is named only with its module permission and,
  for ARB reviews and exceptions, a readable card).
* ``POST   /risks/{id}/governance-links`` — link a record (``risks.manage`` and
  visibility of the record, else 404).
* ``DELETE /risks/{id}/governance-links/{instrument}/{record_id}`` — remove one
  link, under the same rule; links the caller cannot see are never touched.
* ``GET    /adr/{id}/risks`` / ``GET /arb/{id}/risks`` — read-only Linked risks
  (``risks.view`` and the record's own view rule).

The rules live in ``services/risk_governance.py``.

[FORK]
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.risk import Risk
from app.models.risk_governance_link import LINK_ADR, LINK_ARB
from app.models.user import User
from app.services import risk_governance as rg
from app.services.card_read_scope import CardReadScope
from app.services.governance_transitions import LifecycleError
from app.services.permission_service import PermissionService

router = APIRouter(tags=["Risks"])


class GovernanceLinkCreate(BaseModel):
    instrument: str = Field(pattern="^(adr|arb|exception)$")
    record_id: uuid.UUID


def _http(err: LifecycleError) -> HTTPException:
    return HTTPException(err.status, {"code": err.code, "message": str(err)})


async def _risk(db: AsyncSession, risk_id: uuid.UUID) -> Risk:
    risk = await db.get(Risk, risk_id)
    if risk is None:
        raise HTTPException(404, "Risk not found")
    return risk


@router.get("/risks/{risk_id}/governance-links")
async def list_governance_links(
    risk_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "risks.view")
    risk = await _risk(db, risk_id)
    scope = await CardReadScope.load(db, user)
    return {"links": await rg.visible_links_for_risk(db, user, scope, risk.id)}


@router.post("/risks/{risk_id}/governance-links", status_code=201)
async def create_governance_link(
    risk_id: uuid.UUID,
    body: GovernanceLinkCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "risks.manage")
    risk = await _risk(db, risk_id)
    scope = await CardReadScope.load(db, user)
    try:
        info = await rg.require_visible_record(db, user, scope, body.instrument, body.record_id)
    except LifecycleError as err:
        raise _http(err) from err
    await rg.link(db, risk, info, user.id)
    await db.commit()
    return {"links": await rg.visible_links_for_risk(db, user, scope, risk.id)}


@router.delete("/risks/{risk_id}/governance-links/{instrument}/{record_id}")
async def delete_governance_link(
    risk_id: uuid.UUID,
    instrument: str,
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "risks.manage")
    risk = await _risk(db, risk_id)
    scope = await CardReadScope.load(db, user)
    try:
        info = await rg.require_visible_record(db, user, scope, instrument, record_id)
    except LifecycleError as err:
        raise _http(err) from err
    if not await rg.unlink(db, risk, info, user.id):
        raise HTTPException(404, "Link not found")
    await db.commit()
    return {"links": await rg.visible_links_for_risk(db, user, scope, risk.id)}


async def _record_risks(db: AsyncSession, user: User, instrument: str, record_id: uuid.UUID):
    await PermissionService.require_permission(db, user, "risks.view")
    scope = await CardReadScope.load(db, user)
    try:
        await rg.require_visible_record(db, user, scope, instrument, record_id)
    except LifecycleError as err:
        raise _http(err) from err
    today = date.today()
    return {
        "risks": [
            rg.risk_brief(r, today) for r in await rg.risks_for_record(db, instrument, record_id)
        ]
    }


@router.get("/adr/{adr_id}/risks")
async def adr_linked_risks(
    adr_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Risks explicitly linked to this decision record (read-only, D-42.9)."""
    return await _record_risks(db, user, LINK_ADR, adr_id)


@router.get("/arb/{review_id}/risks")
async def arb_linked_risks(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Risks explicitly linked to this review (read-only, D-42.9); a review of
    a hidden subject card is 404 (D-30)."""
    return await _record_risks(db, user, LINK_ARB, review_id)
