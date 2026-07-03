"""NORA EA Program tracker API ([FORK] — noraPlan.md WP3.1).

The 10-stage NORA methodology (plus continuous governance, stage 0) tracked
as per-deliverable rows with evidence links and stage-gate approval.
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
from app.models.nora_program import DELIVERABLE_STATUSES, NORA_STAGE_NUMBERS, EaProgramDeliverable
from app.models.user import User
from app.services.event_bus import event_bus
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/nora-program", tags=["nora-program"])


class EvidenceItem(BaseModel):
    kind: str = Field(default="link", max_length=32)
    ref: str = Field(max_length=1000)
    label: str | None = Field(default=None, max_length=300)


class DeliverableCreate(BaseModel):
    stage_no: int
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    due_date: date | None = None


class DeliverableUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: str | None = None
    owner_id: uuid.UUID | None = None
    due_date: date | None = None
    evidence: list[EvidenceItem] | None = Field(default=None, max_length=50)


def _deliverable_dict(d: EaProgramDeliverable, names: dict | None = None) -> dict:
    names = names or {}
    return {
        "id": str(d.id),
        "stage_no": d.stage_no,
        "key": d.key,
        "title": d.title,
        "description": d.description,
        "status": d.status,
        "built_in": d.built_in,
        "sort_order": d.sort_order,
        "evidence": d.evidence or [],
        "owner_id": str(d.owner_id) if d.owner_id else None,
        "owner_display_name": names.get(d.owner_id),
        "due_date": d.due_date.isoformat() if d.due_date else None,
        "approved_by": str(d.approved_by) if d.approved_by else None,
        "approved_by_display_name": names.get(d.approved_by),
        "approved_at": d.approved_at.isoformat() if d.approved_at else None,
    }


async def _get_deliverable(db: AsyncSession, did: uuid.UUID) -> EaProgramDeliverable:
    row = (
        await db.execute(select(EaProgramDeliverable).where(EaProgramDeliverable.id == did))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Deliverable not found")
    return row


@router.get("")
async def get_program(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The full program: deliverables grouped by stage + per-stage progress."""
    await PermissionService.require_permission(db, user, "nora.view")
    rows = list(
        (
            await db.execute(
                select(EaProgramDeliverable).order_by(
                    EaProgramDeliverable.stage_no, EaProgramDeliverable.sort_order
                )
            )
        )
        .scalars()
        .all()
    )
    user_ids = {d.owner_id for d in rows} | {d.approved_by for d in rows}
    user_ids.discard(None)
    names: dict = {}
    if user_ids:
        res = await db.execute(select(User.id, User.display_name).where(User.id.in_(user_ids)))
        names = dict(res.all())

    stages = []
    for stage_no in NORA_STAGE_NUMBERS:
        stage_rows = [d for d in rows if d.stage_no == stage_no]
        in_scope = [d for d in stage_rows if d.status != "descoped"]
        approved = [d for d in in_scope if d.status == "approved"]
        stages.append(
            {
                "stage_no": stage_no,
                "deliverables": [_deliverable_dict(d, names) for d in stage_rows],
                "progress": round(100 * len(approved) / len(in_scope)) if in_scope else 0,
                "complete": bool(in_scope) and len(approved) == len(in_scope),
            }
        )
    in_scope_all = [d for d in rows if d.status != "descoped"]
    approved_all = [d for d in in_scope_all if d.status == "approved"]
    return {
        "stages": stages,
        "summary": {
            "total": len(in_scope_all),
            "approved": len(approved_all),
            "progress": round(100 * len(approved_all) / len(in_scope_all)) if in_scope_all else 0,
        },
    }


@router.post("/deliverables", status_code=201)
async def create_deliverable(
    body: DeliverableCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    if body.stage_no not in NORA_STAGE_NUMBERS:
        raise HTTPException(400, "Invalid stage number")
    d = EaProgramDeliverable(
        stage_no=body.stage_no,
        key=f"custom_{uuid.uuid4().hex[:12]}",
        title=body.title,
        description=body.description,
        due_date=body.due_date,
        built_in=False,
        sort_order=1000,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return _deliverable_dict(d)


@router.patch("/deliverables/{deliverable_id}")
async def update_deliverable(
    deliverable_id: uuid.UUID,
    body: DeliverableUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    d = await _get_deliverable(db, deliverable_id)
    data = body.model_dump(exclude_unset=True)

    if "status" in data:
        status = data["status"]
        if status not in DELIVERABLE_STATUSES:
            raise HTTPException(400, f"Invalid status: {status}")
        if status == "approved" and d.status != "approved":
            # Stage-gate: only chain approvers can mark a deliverable approved.
            if not await PermissionService.check_permission(db, user, "governance.approve_step"):
                raise HTTPException(403, "Approving a deliverable requires governance.approve_step")
            d.approved_by = user.id
            d.approved_at = datetime.now(timezone.utc)
        elif status != "approved":
            d.approved_by = None
            d.approved_at = None

    if "evidence" in data and data["evidence"] is not None:
        data["evidence"] = [e for e in data["evidence"]]

    for field, value in data.items():
        setattr(d, field, value)

    await event_bus.publish(
        "nora_program.deliverable_updated",
        {"id": str(d.id), "key": d.key, "status": d.status},
        db=db,
        user_id=user.id,
    )
    await db.commit()
    await db.refresh(d)
    return _deliverable_dict(d)


@router.delete("/deliverables/{deliverable_id}", status_code=204)
async def delete_deliverable(
    deliverable_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a custom deliverable. Built-in catalogue rows are descoped, not
    deleted, so the NORA baseline stays auditable."""
    await PermissionService.require_permission(db, user, "nora.manage")
    d = await _get_deliverable(db, deliverable_id)
    if d.built_in:
        raise HTTPException(400, "Built-in deliverables cannot be deleted — descope them instead")
    await db.delete(d)
    await db.commit()
