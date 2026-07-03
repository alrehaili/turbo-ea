"""NORA EA Program tracker API ([FORK] — noraPlan.md WP3.1).

The 10-stage NORA methodology (plus continuous governance, stage 0) tracked
as per-deliverable rows with evidence links and stage-gate approval.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.card import Card
from app.models.improvement_opportunity import ImprovementOpportunity
from app.models.nora_program import DELIVERABLE_STATUSES, NORA_STAGE_NUMBERS, EaProgramDeliverable
from app.models.ppm_status_report import PpmStatusReport
from app.models.relation import Relation
from app.models.tech_standard import StandardException
from app.models.turbolens import TurboLensComplianceFinding
from app.models.user import User
from app.services.event_bus import event_bus
from app.services.permission_service import PermissionService

log = logging.getLogger(__name__)

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


@router.get("/dashboard")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Executive dashboard aggregation (noraPlan.md WP3.1 — the committee view).

    One round-trip returning count-level KPIs across the NORA-relevant modules:
    approval coverage, landscape state split, gap buckets (+ untraceable),
    transition-initiative RAG from the latest PPM status reports, standards
    waivers, improvement opportunities, and open compliance findings. Counts
    only — no card payloads — so the single ``nora.view`` gate is sufficient.
    """
    await PermissionService.require_permission(db, user, "nora.view")

    async def _safe(name: str, coro):
        """Run a subsection; on failure log + rollback so later queries work."""
        try:
            return await coro
        except Exception as e:  # noqa: BLE001
            log.warning("nora dashboard subsection %s failed: %s", name, e)
            try:
                await db.rollback()
            except Exception:
                pass
            return None

    # --- Approval coverage (non-archived cards, by approval_status) ---------
    async def _approvals():
        rows = await db.execute(
            select(Card.approval_status, func.count())
            .where(Card.status != "ARCHIVED")
            .group_by(Card.approval_status)
        )
        return {status: count for status, count in rows.all()}

    approvals = await _safe("approvals", _approvals()) or {}
    total_cards = sum(approvals.values())

    # --- Landscape split by architecture state ------------------------------
    async def _landscape():
        rows = await db.execute(
            select(func.coalesce(Card.architecture_state, "current"), func.count())
            .where(Card.status != "ARCHIVED")
            .group_by(func.coalesce(Card.architecture_state, "current"))
        )
        return {state: count for state, count in rows.all()}

    landscape = await _safe("landscape", _landscape()) or {}

    # --- Gap buckets (same classification as /reports/gap-analysis) --------
    async def _gaps():
        changed_rows = (
            await db.execute(
                select(Card.id, Card.architecture_state, Card.change_type, Card.successor_id).where(
                    Card.status != "ARCHIVED",
                    (Card.architecture_state.in_(("target", "transition")))
                    | ((Card.architecture_state == "current") & (Card.change_type == "retire")),
                )
            )
        ).all()
        changed_ids = {row.id for row in changed_rows}
        traced_ids: set[uuid.UUID] = set()
        if changed_ids:
            rel_rows = await db.execute(
                select(Relation.source_id, Relation.target_id)
                .join(
                    Card,
                    ((Relation.source_id == Card.id) | (Relation.target_id == Card.id))
                    & (Card.type == "Initiative"),
                )
                .where(Relation.source_id.in_(changed_ids) | Relation.target_id.in_(changed_ids))
            )
            for source_id, target_id in rel_rows.all():
                traced_ids.add(source_id)
                traced_ids.add(target_id)
        g = {"create": 0, "replace": 0, "modify": 0, "retire": 0}
        for row in changed_rows:
            if row.architecture_state == "current":
                g["retire"] += 1
            elif row.successor_id or row.change_type in ("replace", "consolidate"):
                g["replace"] += 1
            elif row.change_type == "modify":
                g["modify"] += 1
            else:
                g["create"] += 1
        g["total"] = len(changed_rows)
        g["untraceable"] = len(changed_ids - traced_ids)
        return g

    gaps = await _safe("gaps", _gaps()) or {
        "create": 0,
        "replace": 0,
        "modify": 0,
        "retire": 0,
        "total": 0,
        "untraceable": 0,
    }

    # --- Transition-initiative RAG (latest PPM status report each) ---------
    async def _initiatives():
        latest_report = select(
            PpmStatusReport.initiative_id,
            PpmStatusReport.schedule_health,
            PpmStatusReport.cost_health,
            PpmStatusReport.scope_health,
            func.row_number()
            .over(
                partition_by=PpmStatusReport.initiative_id,
                order_by=(
                    PpmStatusReport.report_date.desc(),
                    PpmStatusReport.created_at.desc(),
                ),
            )
            .label("rn"),
        ).subquery()
        report_rows = (await db.execute(select(latest_report).where(latest_report.c.rn == 1))).all()
        rag_rank = {"onTrack": 0, "atRisk": 1, "offTrack": 2}
        counts = {"onTrack": 0, "atRisk": 0, "offTrack": 0, "noReport": 0}
        reported_ids = set()
        for row in report_rows:
            reported_ids.add(row.initiative_id)
            worst = max(
                (row.schedule_health, row.cost_health, row.scope_health),
                key=lambda h: rag_rank.get(h, 0),
            )
            counts[worst] = counts.get(worst, 0) + 1
        active_initiatives = (
            await db.execute(
                select(func.count()).where(Card.type == "Initiative", Card.status != "ARCHIVED")
            )
        ).scalar_one()
        counts["noReport"] = max(0, active_initiatives - len(reported_ids))
        return counts

    initiatives = await _safe("initiatives", _initiatives()) or {
        "onTrack": 0,
        "atRisk": 0,
        "offTrack": 0,
        "noReport": 0,
    }

    # --- Standards waivers (tech_standard_exceptions) -----------------------
    async def _waivers():
        today = date.today()
        rows = (
            await db.execute(select(StandardException.status, StandardException.expiry_date))
        ).all()
        w = {"active": 0, "pending": 0, "expiringSoon": 0, "expired": 0}
        horizon = today + timedelta(days=30)
        for status, expiry in rows:
            if status == "requested":
                w["pending"] += 1
            elif status == "approved":
                if expiry and expiry < today:
                    w["expired"] += 1
                else:
                    w["active"] += 1
                    if expiry and expiry <= horizon:
                        w["expiringSoon"] += 1
        return w

    waivers = await _safe("waivers", _waivers()) or {
        "active": 0,
        "pending": 0,
        "expiringSoon": 0,
        "expired": 0,
    }

    # --- Improvement opportunities by status --------------------------------
    async def _opportunities():
        rows = await db.execute(
            select(ImprovementOpportunity.status, func.count()).group_by(
                ImprovementOpportunity.status
            )
        )
        return {status: count for status, count in rows.all()}

    opportunities = await _safe("opportunities", _opportunities()) or {}

    # --- Open compliance findings by severity -------------------------------
    async def _compliance():
        rows = await db.execute(
            select(TurboLensComplianceFinding.severity, func.count())
            .where(
                TurboLensComplianceFinding.auto_resolved.is_(False),
                TurboLensComplianceFinding.status.in_(
                    ("non_compliant", "partial", "review_needed")
                ),
            )
            .group_by(TurboLensComplianceFinding.severity)
        )
        return {severity: count for severity, count in rows.all()}

    compliance = await _safe("compliance", _compliance()) or {}

    return {
        "approvals": {
            "total": total_cards,
            "approved": approvals.get("APPROVED", 0),
            "in_review": approvals.get("IN_REVIEW", 0),
            "draft": approvals.get("DRAFT", 0),
            "broken": approvals.get("BROKEN", 0),
            "rejected": approvals.get("REJECTED", 0),
            "approved_pct": round(100 * approvals.get("APPROVED", 0) / total_cards)
            if total_cards
            else 0,
        },
        "landscape": {
            "current": landscape.get("current", 0),
            "transition": landscape.get("transition", 0),
            "target": landscape.get("target", 0),
        },
        "gaps": gaps,
        "initiatives": initiatives,
        "waivers": waivers,
        "opportunities": {
            "proposed": opportunities.get("proposed", 0),
            "approved": opportunities.get("approved", 0),
            "inTransition": opportunities.get("inTransition", 0),
            "realized": opportunities.get("realized", 0),
        },
        "compliance": {
            "open": sum(compliance.values()),
            "critical": compliance.get("critical", 0),
            "high": compliance.get("high", 0),
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
