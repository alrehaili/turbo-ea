"""ADM Governance Workspace API.

Reference: ``backend/app/models/adm.py`` for the data model and
``backend/app/services/adm_service.py`` for the state machine + validation
rules.

[FORK FEATURE]
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.adm import (
    ADM_ARTEFACT_KINDS,
    ADM_WORKSPACE_STATUSES,
    AdmPhase,
    AdmPhaseArtefact,
    AdmWorkspace,
)
from app.models.card import Card
from app.models.soaw import SoAW
from app.models.user import User
from app.services import adm_service
from app.services.adm_templates import get_template
from app.services.event_bus import event_bus
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/adm", tags=["adm"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    soaw_id: uuid.UUID | None = None
    initiative_id: uuid.UUID | None = None
    description: str | None = None
    owner_id: uuid.UUID | None = None
    target_completion: date | None = None
    template: str = "togaf"

    @model_validator(mode="after")
    def _require_anchor(self) -> "WorkspaceCreate":
        if not self.soaw_id and not self.initiative_id:
            raise ValueError("Workspace must be anchored to a SoAW or an Initiative")
        return self


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    owner_id: uuid.UUID | None = None
    target_completion: date | None = None
    status: str | None = None


class PhaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    owner_id: uuid.UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    notes: str | None = None
    gate_notes: str | None = None
    status: str | None = None


class ArtefactCreate(BaseModel):
    kind: str
    ref_id: uuid.UUID | None = None
    ref_url: str | None = None
    title: str = Field(min_length=1, max_length=300)
    is_required: bool = False
    notes: str | None = None

    @model_validator(mode="after")
    def _validate_kind(self) -> "ArtefactCreate":
        if self.kind not in ADM_ARTEFACT_KINDS:
            raise ValueError(f"Unknown artefact kind: {self.kind}")
        if self.kind == "url":
            if not self.ref_url or not self.ref_url.strip():
                raise ValueError("URL artefact requires ref_url")
        return self


class ArtefactUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    notes: str | None = None
    sort_order: int | None = None
    is_required: bool | None = None


class ArtefactWaive(BaseModel):
    is_waived: bool
    reason: str | None = None


class MarkReadyRequest(BaseModel):
    gate_notes: str | None = None
    override: bool = False
    override_reason: str | None = None


class ApproveRequest(BaseModel):
    comment: str | None = None


class ReasonRequest(BaseModel):
    reason: str


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _phase_dict(p: AdmPhase, artefacts: list[AdmPhaseArtefact]) -> dict:
    required_count = sum(1 for a in artefacts if a.is_required)
    linked_count = sum(
        1
        for a in artefacts
        if a.is_required
        and (a.is_waived or a.ref_id is not None or (a.ref_url and a.ref_url.strip()))
    )
    waived_count = sum(1 for a in artefacts if a.is_required and a.is_waived)
    return {
        "id": str(p.id),
        "workspace_id": str(p.workspace_id),
        "phase_key": p.phase_key,
        "title": p.title,
        "description": p.description,
        "sort_order": p.sort_order,
        "is_continuous": p.is_continuous,
        "status": p.status,
        "owner_id": str(p.owner_id) if p.owner_id else None,
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "due_date": p.due_date.isoformat() if p.due_date else None,
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        "completion_pct": adm_service.compute_completion_pct(artefacts),
        "notes": p.notes,
        "gate_notes": p.gate_notes,
        "approved_by": str(p.approved_by) if p.approved_by else None,
        "approved_at": p.approved_at.isoformat() if p.approved_at else None,
        "approval_comment": p.approval_comment,
        "approval_override_reason": p.approval_override_reason,
        "required_count": required_count,
        "linked_count": linked_count,
        "waived_count": waived_count,
        "artefacts": [_artefact_dict(a) for a in artefacts],
    }


def _artefact_dict(a: AdmPhaseArtefact) -> dict:
    return {
        "id": str(a.id),
        "phase_id": str(a.phase_id),
        "kind": a.kind,
        "ref_id": str(a.ref_id) if a.ref_id else None,
        "ref_url": a.ref_url,
        "title": a.title,
        "is_required": a.is_required,
        "is_waived": a.is_waived,
        "waived_reason": a.waived_reason,
        "waived_by": str(a.waived_by) if a.waived_by else None,
        "waived_at": a.waived_at.isoformat() if a.waived_at else None,
        "linked_by": str(a.linked_by) if a.linked_by else None,
        "notes": a.notes,
        "sort_order": a.sort_order,
        "is_linked": a.ref_id is not None or bool(a.ref_url and a.ref_url.strip()),
    }


def _workspace_dict(w: AdmWorkspace, phases: list[AdmPhase] | None = None) -> dict:
    d = {
        "id": str(w.id),
        "name": w.name,
        "soaw_id": str(w.soaw_id) if w.soaw_id else None,
        "initiative_id": str(w.initiative_id) if w.initiative_id else None,
        "status": w.status,
        "description": w.description,
        "target_completion": w.target_completion.isoformat() if w.target_completion else None,
        "owner_id": str(w.owner_id) if w.owner_id else None,
        "created_by": str(w.created_by) if w.created_by else None,
        "created_at": w.created_at.isoformat() if w.created_at else None,
        "updated_at": w.updated_at.isoformat() if w.updated_at else None,
    }
    if phases is not None:
        d["phases"] = [
            _phase_dict(p, [a for a in (p.artefacts or [])])  # type: ignore[attr-defined]
            for p in phases
        ]
    return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> AdmWorkspace:
    res = await db.execute(select(AdmWorkspace).where(AdmWorkspace.id == workspace_id))
    ws = res.scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=404, detail="ADM workspace not found")
    return ws


async def _get_phase(db: AsyncSession, phase_id: uuid.UUID) -> AdmPhase:
    res = await db.execute(select(AdmPhase).where(AdmPhase.id == phase_id))
    p = res.scalar_one_or_none()
    if p is None:
        raise HTTPException(status_code=404, detail="ADM phase not found")
    return p


async def _get_artefact(db: AsyncSession, artefact_id: uuid.UUID) -> AdmPhaseArtefact:
    res = await db.execute(select(AdmPhaseArtefact).where(AdmPhaseArtefact.id == artefact_id))
    a = res.scalar_one_or_none()
    if a is None:
        raise HTTPException(status_code=404, detail="Artefact not found")
    return a


async def _load_phases_with_artefacts(db: AsyncSession, workspace_id: uuid.UUID) -> list[AdmPhase]:
    """Return the phases ordered by ``sort_order`` with their artefacts eagerly
    populated on ``phase.artefacts``."""
    phase_rows = (
        (
            await db.execute(
                select(AdmPhase)
                .where(AdmPhase.workspace_id == workspace_id)
                .order_by(AdmPhase.sort_order)
            )
        )
        .scalars()
        .all()
    )
    if not phase_rows:
        return []
    ids = [p.id for p in phase_rows]
    art_rows = (
        (
            await db.execute(
                select(AdmPhaseArtefact)
                .where(AdmPhaseArtefact.phase_id.in_(ids))
                .order_by(AdmPhaseArtefact.sort_order, AdmPhaseArtefact.created_at)
            )
        )
        .scalars()
        .all()
    )
    by_phase: dict[uuid.UUID, list[AdmPhaseArtefact]] = {pid: [] for pid in ids}
    for a in art_rows:
        by_phase[a.phase_id].append(a)
    for p in phase_rows:
        p.artefacts = by_phase.get(p.id, [])  # type: ignore[assignment]
    return phase_rows


async def _resolve_ref_for_kind(db: AsyncSession, kind: str, ref_id: uuid.UUID | None) -> None:
    """Confirm ``ref_id`` resolves in the appropriate table. Kinds without a
    known table (``url``, ``requirement``, ``document``, ``file_attachment``)
    are accepted as-is; the frontend is trusted to author them."""
    if ref_id is None:
        # ``requirement`` and ``url`` legitimately have no ref_id.
        if kind not in ("url", "requirement", "document", "file_attachment"):
            raise HTTPException(status_code=422, detail=f"kind={kind} requires a ref_id")
        return
    if kind == "soaw":
        row = await db.execute(select(SoAW.id).where(SoAW.id == ref_id))
    elif kind == "card":
        row = await db.execute(select(Card.id).where(Card.id == ref_id))
    else:
        # For the remaining kinds (adr, arb_review, diagram, roadmap, risk,
        # …) we accept the ref_id without a live existence check to keep
        # the MVP compact — the underlying tables all use UUID PKs and the
        # frontend authors the link from a live picker. A future PR should
        # add per-kind resolution + a "resolved title" refresh on read.
        return
    if row.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"{kind}:{ref_id} does not exist")


# ---------------------------------------------------------------------------
# Workspace endpoints
# ---------------------------------------------------------------------------


@router.get("/workspaces")
async def list_workspaces(
    soaw_id: uuid.UUID | None = None,
    initiative_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.view")
    stmt = select(AdmWorkspace).order_by(AdmWorkspace.created_at.desc())
    if soaw_id:
        stmt = stmt.where(AdmWorkspace.soaw_id == soaw_id)
    if initiative_id:
        stmt = stmt.where(AdmWorkspace.initiative_id == initiative_id)
    if status:
        stmt = stmt.where(AdmWorkspace.status == status)
    workspaces = (await db.execute(stmt)).scalars().all()
    if not workspaces:
        return []

    # Roll up phase counts + active phase per workspace in one query.
    ws_ids = [w.id for w in workspaces]
    phase_rows = (
        (
            await db.execute(
                select(AdmPhase)
                .where(AdmPhase.workspace_id.in_(ws_ids))
                .order_by(AdmPhase.sort_order)
            )
        )
        .scalars()
        .all()
    )
    by_ws: dict[uuid.UUID, list[AdmPhase]] = {wid: [] for wid in ws_ids}
    for p in phase_rows:
        by_ws[p.workspace_id].append(p)

    result = []
    for w in workspaces:
        phases = by_ws.get(w.id, [])
        approved = sum(1 for p in phases if p.status == "approved")
        blocked = sum(1 for p in phases if p.status == "blocked")
        overdue = sum(
            1
            for p in phases
            if p.due_date and p.due_date < date.today() and p.status not in ("approved", "skipped")
        )
        active = next(
            (
                p
                for p in phases
                if not p.is_continuous and p.status in ("in_progress", "ready_for_gate", "blocked")
            ),
            None,
        )
        total = sum(1 for p in phases if not p.is_continuous)
        result.append(
            {
                **_workspace_dict(w),
                "phase_count": len(phases),
                "approved_count": approved,
                "blocked_count": blocked,
                "overdue_count": overdue,
                "active_phase": (
                    {
                        "phase_key": active.phase_key,
                        "title": active.title,
                        "status": active.status,
                        "due_date": active.due_date.isoformat() if active.due_date else None,
                    }
                    if active
                    else None
                ),
                "completion_pct": (int(round(approved * 100 / total)) if total else 0),
            }
        )
    return result


@router.post("/workspaces", status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.manage")

    # Verify anchors exist.
    if payload.soaw_id:
        exists = await db.execute(select(SoAW.id).where(SoAW.id == payload.soaw_id))
        if exists.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="SoAW not found")
        # v1: enforce at most one workspace per SoAW at the app layer (DB has a
        # partial unique index as a safety net).
        existing = await db.execute(
            select(AdmWorkspace.id).where(AdmWorkspace.soaw_id == payload.soaw_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=409,
                detail="This SoAW already has an ADM workspace",
            )
    if payload.initiative_id:
        exists = await db.execute(select(Card.id).where(Card.id == payload.initiative_id))
        if exists.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Initiative card not found")

    template = get_template(payload.template)

    ws = AdmWorkspace(
        name=payload.name,
        soaw_id=payload.soaw_id,
        initiative_id=payload.initiative_id,
        description=payload.description,
        owner_id=payload.owner_id,
        target_completion=payload.target_completion,
        created_by=user.id,
        status="active",
    )
    db.add(ws)
    await db.flush()

    for phase_spec in template:
        phase = AdmPhase(
            workspace_id=ws.id,
            phase_key=phase_spec["phase_key"],
            title=phase_spec["title"],
            description=phase_spec["description"],
            sort_order=phase_spec["sort_order"],
            is_continuous=phase_spec["is_continuous"],
            status="not_started",
        )
        db.add(phase)
        await db.flush()
        for i, req in enumerate(phase_spec["required_artefacts"]):
            db.add(
                AdmPhaseArtefact(
                    phase_id=phase.id,
                    kind=req["kind"],
                    title=req["title"],
                    is_required=True,
                    sort_order=i,
                )
            )

    await event_bus.publish(
        "adm_workspace.created",
        {"workspace_id": str(ws.id), "template": payload.template},
        db=db,
        user_id=user.id,
    )
    await db.commit()

    phases = await _load_phases_with_artefacts(db, ws.id)
    return _workspace_dict(ws, phases)


@router.get("/workspaces/{workspace_id}")
async def get_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.view")
    ws = await _get_workspace(db, workspace_id)
    phases = await _load_phases_with_artefacts(db, ws.id)
    return _workspace_dict(ws, phases)


@router.patch("/workspaces/{workspace_id}")
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.manage")
    ws = await _get_workspace(db, workspace_id)
    if payload.status is not None and payload.status not in ADM_WORKSPACE_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status: {payload.status}")
    for field in ("name", "description", "owner_id", "target_completion", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(ws, field, value)
    await event_bus.publish(
        "adm_workspace.updated",
        {"workspace_id": str(ws.id)},
        db=db,
        user_id=user.id,
    )
    await db.commit()
    phases = await _load_phases_with_artefacts(db, ws.id)
    return _workspace_dict(ws, phases)


@router.delete("/workspaces/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.manage")
    ws = await _get_workspace(db, workspace_id)
    await event_bus.publish(
        "adm_workspace.deleted",
        {"workspace_id": str(ws.id), "name": ws.name},
        db=db,
        user_id=user.id,
    )
    await db.delete(ws)
    await db.commit()


@router.get("/workspaces/by-soaw/{soaw_id}")
async def workspace_by_soaw(
    soaw_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Convenience for the SoAW editor: returns the workspace or 404."""
    await PermissionService.require_permission(db, user, "adm.view")
    res = await db.execute(select(AdmWorkspace).where(AdmWorkspace.soaw_id == soaw_id))
    ws = res.scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=404, detail="No ADM workspace for this SoAW")
    phases = await _load_phases_with_artefacts(db, ws.id)
    return _workspace_dict(ws, phases)


# ---------------------------------------------------------------------------
# Phase endpoints
# ---------------------------------------------------------------------------


@router.get("/phases/{phase_id}")
async def get_phase(
    phase_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.view")
    p = await _get_phase(db, phase_id)
    art_rows = (
        (
            await db.execute(
                select(AdmPhaseArtefact)
                .where(AdmPhaseArtefact.phase_id == p.id)
                .order_by(AdmPhaseArtefact.sort_order, AdmPhaseArtefact.created_at)
            )
        )
        .scalars()
        .all()
    )
    return _phase_dict(p, list(art_rows))


@router.patch("/phases/{phase_id}")
async def update_phase(
    phase_id: uuid.UUID,
    payload: PhaseUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.manage")
    p = await _get_phase(db, phase_id)
    if payload.status is not None:
        try:
            adm_service.validate_transition(p.status, payload.status)
        except adm_service.AdmValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        # ready_for_gate / approved / skipped go through their own endpoints
        # for audit clarity; PATCH only supports lateral moves.
        if payload.status in ("ready_for_gate", "approved", "skipped"):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Use the dedicated endpoint (/mark-ready, /approve, "
                    f"/skip) to move a phase to {payload.status}"
                ),
            )
        p.status = payload.status
    for field in (
        "title",
        "description",
        "owner_id",
        "start_date",
        "due_date",
        "notes",
        "gate_notes",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(p, field, value)
    await event_bus.publish(
        "adm_phase.updated",
        {"phase_id": str(p.id), "workspace_id": str(p.workspace_id)},
        db=db,
        user_id=user.id,
    )
    await db.commit()
    art_rows = (
        (
            await db.execute(
                select(AdmPhaseArtefact)
                .where(AdmPhaseArtefact.phase_id == p.id)
                .order_by(AdmPhaseArtefact.sort_order, AdmPhaseArtefact.created_at)
            )
        )
        .scalars()
        .all()
    )
    return _phase_dict(p, list(art_rows))


@router.post("/phases/{phase_id}/mark-ready")
async def mark_ready(
    phase_id: uuid.UUID,
    payload: MarkReadyRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.manage")
    p = await _get_phase(db, phase_id)
    try:
        adm_service.validate_transition(p.status, "ready_for_gate")
    except adm_service.AdmValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    art_rows = (
        (await db.execute(select(AdmPhaseArtefact).where(AdmPhaseArtefact.phase_id == p.id)))
        .scalars()
        .all()
    )
    try:
        adm_service.can_mark_ready(
            p,
            list(art_rows),
            override=payload.override,
            override_reason=payload.override_reason,
        )
    except adm_service.AdmValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    from_status = p.status
    p.status = "ready_for_gate"
    if payload.gate_notes is not None:
        p.gate_notes = payload.gate_notes
    if payload.override and payload.override_reason:
        p.approval_override_reason = payload.override_reason.strip()

    await event_bus.publish(
        "adm_phase.transitioned",
        {
            "phase_id": str(p.id),
            "workspace_id": str(p.workspace_id),
            "from": from_status,
            "to": "ready_for_gate",
            "override": payload.override,
            "override_reason": (
                payload.override_reason.strip() if payload.override_reason else None
            ),
        },
        db=db,
        user_id=user.id,
    )
    await db.commit()
    return _phase_dict(p, list(art_rows))


@router.post("/phases/{phase_id}/approve")
async def approve_phase(
    phase_id: uuid.UUID,
    payload: ApproveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.approve_gate")
    p = await _get_phase(db, phase_id)
    try:
        adm_service.can_approve(p)
    except adm_service.AdmValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    from_status = p.status
    p.status = "approved"
    p.approved_by = user.id
    p.approved_at = datetime.now(timezone.utc)
    p.approval_comment = payload.comment
    p.completed_at = p.approved_at

    await event_bus.publish(
        "adm_phase.transitioned",
        {
            "phase_id": str(p.id),
            "workspace_id": str(p.workspace_id),
            "from": from_status,
            "to": "approved",
            "comment": payload.comment,
        },
        db=db,
        user_id=user.id,
    )
    await db.commit()
    art_rows = (
        (await db.execute(select(AdmPhaseArtefact).where(AdmPhaseArtefact.phase_id == p.id)))
        .scalars()
        .all()
    )
    return _phase_dict(p, list(art_rows))


@router.post("/phases/{phase_id}/reopen")
async def reopen_phase(
    phase_id: uuid.UUID,
    payload: ReasonRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.approve_gate")
    p = await _get_phase(db, phase_id)
    try:
        reason = adm_service.require_reason(payload.reason, "reopen")
        adm_service.validate_transition(p.status, "in_progress")
    except adm_service.AdmValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    from_status = p.status
    p.status = "in_progress"
    p.approved_by = None
    p.approved_at = None
    p.approval_comment = None
    p.completed_at = None
    p.gate_notes = (p.gate_notes or "") + f"\n[reopened] {reason}"
    await event_bus.publish(
        "adm_phase.transitioned",
        {
            "phase_id": str(p.id),
            "workspace_id": str(p.workspace_id),
            "from": from_status,
            "to": "in_progress",
            "reason": reason,
            "action": "reopen",
        },
        db=db,
        user_id=user.id,
    )
    await db.commit()
    art_rows = (
        (await db.execute(select(AdmPhaseArtefact).where(AdmPhaseArtefact.phase_id == p.id)))
        .scalars()
        .all()
    )
    return _phase_dict(p, list(art_rows))


@router.post("/phases/{phase_id}/skip")
async def skip_phase(
    phase_id: uuid.UUID,
    payload: ReasonRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.approve_gate")
    p = await _get_phase(db, phase_id)
    if p.is_continuous:
        raise HTTPException(status_code=422, detail="Continuous phases cannot be skipped")
    try:
        reason = adm_service.require_reason(payload.reason, "skip")
        adm_service.validate_transition(p.status, "skipped")
    except adm_service.AdmValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    from_status = p.status
    p.status = "skipped"
    p.approved_by = user.id
    p.approved_at = datetime.now(timezone.utc)
    p.approval_comment = reason
    p.completed_at = p.approved_at
    await event_bus.publish(
        "adm_phase.transitioned",
        {
            "phase_id": str(p.id),
            "workspace_id": str(p.workspace_id),
            "from": from_status,
            "to": "skipped",
            "reason": reason,
        },
        db=db,
        user_id=user.id,
    )
    await db.commit()
    art_rows = (
        (await db.execute(select(AdmPhaseArtefact).where(AdmPhaseArtefact.phase_id == p.id)))
        .scalars()
        .all()
    )
    return _phase_dict(p, list(art_rows))


# ---------------------------------------------------------------------------
# Artefact endpoints
# ---------------------------------------------------------------------------


@router.post("/phases/{phase_id}/artefacts", status_code=201)
async def create_artefact(
    phase_id: uuid.UUID,
    payload: ArtefactCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.manage")
    p = await _get_phase(db, phase_id)
    await _resolve_ref_for_kind(db, payload.kind, payload.ref_id)
    art = AdmPhaseArtefact(
        phase_id=p.id,
        kind=payload.kind,
        ref_id=payload.ref_id,
        ref_url=payload.ref_url,
        title=payload.title,
        is_required=payload.is_required,
        notes=payload.notes,
        linked_by=user.id,
    )
    db.add(art)
    await event_bus.publish(
        "adm_artefact.linked",
        {
            "phase_id": str(p.id),
            "workspace_id": str(p.workspace_id),
            "kind": payload.kind,
            "ref_id": str(payload.ref_id) if payload.ref_id else None,
        },
        db=db,
        user_id=user.id,
    )
    await db.commit()
    await db.refresh(art)
    return _artefact_dict(art)


@router.patch("/artefacts/{artefact_id}")
async def update_artefact(
    artefact_id: uuid.UUID,
    payload: ArtefactUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.manage")
    art = await _get_artefact(db, artefact_id)
    for field in ("title", "notes", "sort_order", "is_required"):
        v = getattr(payload, field)
        if v is not None:
            setattr(art, field, v)
    await db.commit()
    return _artefact_dict(art)


@router.post("/artefacts/{artefact_id}/waive")
async def waive_artefact(
    artefact_id: uuid.UUID,
    payload: ArtefactWaive,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.manage")
    art = await _get_artefact(db, artefact_id)
    if payload.is_waived:
        try:
            reason = adm_service.require_reason(payload.reason, "waive")
        except adm_service.AdmValidationError as e:
            raise HTTPException(status_code=422, detail=str(e))
        art.is_waived = True
        art.waived_reason = reason
        art.waived_by = user.id
        art.waived_at = datetime.now(timezone.utc)
        event_type = "adm_artefact.waived"
    else:
        art.is_waived = False
        art.waived_reason = None
        art.waived_by = None
        art.waived_at = None
        event_type = "adm_artefact.unwaived"
    await event_bus.publish(
        event_type,
        {"artefact_id": str(art.id), "phase_id": str(art.phase_id)},
        db=db,
        user_id=user.id,
    )
    await db.commit()
    return _artefact_dict(art)


@router.delete("/artefacts/{artefact_id}", status_code=204)
async def delete_artefact(
    artefact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "adm.manage")
    art = await _get_artefact(db, artefact_id)
    phase_id = art.phase_id
    await db.delete(art)
    await event_bus.publish(
        "adm_artefact.unlinked",
        {"phase_id": str(phase_id)},
        db=db,
        user_id=user.id,
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Cross-cutting: requirements management
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/requirements")
async def list_workspace_requirements(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return every ``kind='requirement'`` artefact across all phases of
    this workspace, so the Requirements Management panel can render a
    single continuous list."""
    await PermissionService.require_permission(db, user, "adm.view")
    ws = await _get_workspace(db, workspace_id)
    phase_ids_res = await db.execute(
        select(AdmPhase.id, AdmPhase.phase_key, AdmPhase.title).where(
            AdmPhase.workspace_id == ws.id
        )
    )
    phase_by_id: dict[uuid.UUID, tuple[str, str]] = {
        row[0]: (row[1], row[2]) for row in phase_ids_res.all()
    }
    if not phase_by_id:
        return []
    art_rows = (
        (
            await db.execute(
                select(AdmPhaseArtefact)
                .where(
                    AdmPhaseArtefact.phase_id.in_(phase_by_id.keys()),
                    AdmPhaseArtefact.kind == "requirement",
                )
                .order_by(AdmPhaseArtefact.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    result = []
    for a in art_rows:
        phase_key, phase_title = phase_by_id.get(a.phase_id, ("", ""))
        result.append({**_artefact_dict(a), "phase_key": phase_key, "phase_title": phase_title})
    return result


# ---------------------------------------------------------------------------
# Dashboard / list summary shortcut
# ---------------------------------------------------------------------------


@router.get("/my-actions")
async def my_actions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Rows for the "My ADM actions" dashboard widget.

    Returns three groups:

    * ``pending_gate``   — phases marked ready_for_gate (for approvers)
    * ``blocked``        — phases the user owns that are blocked
    * ``overdue``        — phases the user owns whose due_date has passed
                            and status is not approved/skipped
    """
    await PermissionService.require_permission(db, user, "adm.view")
    can_approve = await PermissionService.check_permission(db, user, "adm.approve_gate")

    pending_res = (
        (
            await db.execute(
                select(AdmPhase)
                .where(AdmPhase.status == "ready_for_gate")
                .order_by(AdmPhase.updated_at.desc())
            )
        )
        .scalars()
        .all()
        if can_approve
        else []
    )
    blocked_res = (
        (
            await db.execute(
                select(AdmPhase)
                .where(AdmPhase.owner_id == user.id, AdmPhase.status == "blocked")
                .order_by(AdmPhase.updated_at.desc())
            )
        )
        .scalars()
        .all()
    )
    overdue_res = (
        (
            await db.execute(
                select(AdmPhase)
                .where(
                    AdmPhase.owner_id == user.id,
                    AdmPhase.due_date < date.today(),
                    AdmPhase.status.notin_(("approved", "skipped")),
                )
                .order_by(AdmPhase.due_date.asc())
            )
        )
        .scalars()
        .all()
    )

    def brief(p: AdmPhase) -> dict:
        return {
            "id": str(p.id),
            "workspace_id": str(p.workspace_id),
            "phase_key": p.phase_key,
            "title": p.title,
            "status": p.status,
            "due_date": p.due_date.isoformat() if p.due_date else None,
        }

    return {
        "pending_gate": [brief(p) for p in pending_res],
        "blocked": [brief(p) for p in blocked_res],
        "overdue": [brief(p) for p in overdue_res],
    }
