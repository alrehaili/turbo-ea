"""Benefits register (D-12, D-14, D-29, D-43; Phase 4 Batch 4.1).

* ``GET  /benefits`` / ``GET /benefits/{id}`` — ``benefits.view``. Amounts
  only with ``costs.view`` (I-66); a benefit linked to hidden cards only does
  not exist for the reader (404), hidden links are omitted.
* ``POST /benefits`` / ``PATCH /benefits/{id}`` — ``benefits.manage``.
* ``POST /benefits/{id}/validate`` and ``/reopen`` — ``benefits.validate``.
* ``POST /benefits/{id}/close`` — ``withdrawn`` by ``benefits.manage``,
  ``not_realised`` by ``benefits.confirm``.
* ``POST /benefits/{id}/actuals`` — report an actual, ``benefits.manage``.
* ``POST /benefits/{id}/actuals/{actual_id}/confirm|reject|reverse`` —
  ``benefits.confirm``, independent of the benefit (D-29, no admin bypass).
* ``POST /benefits/{id}/assessments`` — qualitative outcome, ``benefits.manage``.

Every write that names or moves money also needs ``costs.view``: nobody
writes an amount they may not read. Rules live in ``services/benefits.py``.

[FORK]
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.benefit import (
    BENEFIT_TYPES,
    DECISION_ADR,
    DECISION_ARB,
    DECISION_OPPORTUNITY,
    DECISION_RATIONALIZATION,
    STATUSES,
    Benefit,
)
from app.models.benefit_actual import CONFIRMED
from app.models.benefit_assessment import BenefitHistory
from app.models.card import Card
from app.models.document import Document
from app.models.file_attachment import FileAttachment
from app.models.improvement_opportunity import ImprovementOpportunity
from app.models.rationalization import AssessmentDecision, RationalizationAssessment
from app.models.user import User
from app.services import benefits as svc
from app.services.card_read_scope import CardReadScope
from app.services.fiscal_year import current_fiscal_year, get_fiscal_year_start
from app.services.governance_transitions import LifecycleError
from app.services.opportunity_access import inaccessible_opportunity_ids
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/benefits", tags=["Benefits"])

EVIDENCE_MODELS = {"document": Document, "attachment": FileAttachment}


# ── Schemas ─────────────────────────────────────────────────────────────


class InitiativeLink(BaseModel):
    card_id: uuid.UUID
    classification: Literal["direct", "contributing", "not_attributable"]


class EvidenceRef(BaseModel):
    kind: Literal["document", "attachment", "reference"]
    id: uuid.UUID | None = None
    text: str | None = Field(None, max_length=500)


class BenefitBase(BaseModel):
    title: str | None = Field(None, max_length=300)
    description: str | None = Field(None, max_length=10000)
    owner_id: uuid.UUID | None = None
    decision_kind: Literal["adr", "arb", "rationalization", "opportunity"] | None = None
    decision_id: uuid.UUID | None = None
    kpi_card_id: uuid.UUID | None = None
    currency: str | None = Field(None, max_length=3)
    recurrence: Literal["one_time", "annual"] | None = None
    planned_amount: float | None = Field(None, ge=0)
    baseline_amount: float | None = Field(None, ge=0)
    counterfactual_amount: float | None = Field(None, ge=0)
    counterfactual_note: str | None = Field(None, max_length=4000)
    method_note: str | None = Field(None, max_length=4000)
    expected_fiscal_year: int | None = Field(None, ge=2000, le=2100)
    initiatives: list[InitiativeLink] | None = Field(None, max_length=50)
    affected: list[uuid.UUID] | None = Field(None, max_length=200)


class BenefitCreate(BenefitBase):
    title: str = Field(min_length=1, max_length=300)
    benefit_type: Literal[
        "cost_saving", "cost_avoidance", "revenue", "productivity", "non_financial"
    ]
    measurement: Literal["financial", "kpi", "qualitative"] | None = None


class Reason(BaseModel):
    reason: str | None = Field(None, max_length=4000)


class ValidateBody(BaseModel):
    note: str | None = Field(None, max_length=4000)


class CloseBody(BaseModel):
    outcome: Literal["withdrawn", "not_realised"]
    reason: str = Field(min_length=1, max_length=4000)


class ActualCreate(BaseModel):
    fiscal_year: int = Field(ge=2000, le=2100)
    amount: float = Field(ge=0)
    note: str | None = Field(None, max_length=4000)
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=20)


class Allocation(BaseModel):
    card_id: uuid.UUID
    amount: float = Field(gt=0)
    rationale: str = Field(min_length=1, max_length=4000)


class ConfirmBody(BaseModel):
    finance_reference: str = Field(min_length=1, max_length=200)
    note: str | None = Field(None, max_length=4000)
    allocations: list[Allocation] = Field(default_factory=list, max_length=50)


class AssessmentCreate(BaseModel):
    fiscal_year: int = Field(ge=2000, le=2100)
    outcome: Literal["achieved", "partially_achieved", "not_achieved"]
    note: str = Field(min_length=1, max_length=4000)
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=20)


# ── Helpers ─────────────────────────────────────────────────────────────


def _raise(err: LifecycleError) -> HTTPException:
    return HTTPException(err.status, {"code": err.code, "message": str(err)})


async def _can(db: AsyncSession, user: User, key: str) -> bool:
    return await PermissionService.check_permission(db, user, key)


async def _names(db: AsyncSession, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = await db.execute(select(User.id, User.display_name).where(User.id.in_(ids)))
    return dict(rows.all())


async def _load(
    db: AsyncSession, read_scope: CardReadScope, benefit_id: uuid.UUID
) -> tuple[svc.BenefitBundle, set[uuid.UUID]]:
    benefit = await db.get(Benefit, benefit_id)
    if benefit is None:
        raise HTTPException(404, "Benefit not found")
    visible, readable = await svc.visible_bundles(
        db, read_scope, await svc.load_bundles(db, [benefit])
    )
    if not visible:
        raise HTTPException(404, "Benefit not found")
    return visible[0], readable


async def _decision_summary(
    db: AsyncSession, user: User, read_scope: CardReadScope, benefit: Benefit
) -> dict[str, Any] | None:
    """The governing decision, titled only for a reader of its module whose
    linked card is readable (D-30); otherwise its kind alone."""
    kind, did = benefit.decision_kind, benefit.decision_id
    if kind is None or did is None:
        return None
    out: dict[str, Any] = {"kind": kind, "id": None, "title": None, "path": None}
    if not await _can(db, user, svc.DECISION_VIEW_PERMISSION[kind]):
        return out
    title = path = None
    if kind == DECISION_ADR:
        adr = await db.get(ArchitectureDecision, did)
        if adr is not None:
            title, path = f"{adr.reference_number} {adr.title}", f"/ea-delivery/adr/{did}/preview"
    elif kind == DECISION_ARB:
        review = await db.get(ArbReview, did)
        if review is not None and (
            review.subject_card_id is None
            or await read_scope.readable_card_ids(db, [review.subject_card_id], mode="module")
        ):
            title, path = review.title, f"/arb?review={did}"
    elif kind == DECISION_RATIONALIZATION:
        row = (
            await db.execute(
                select(Card.name, RationalizationAssessment.name, AssessmentDecision.card_id)
                .join(Card, Card.id == AssessmentDecision.card_id)
                .join(
                    RationalizationAssessment,
                    RationalizationAssessment.id == AssessmentDecision.assessment_id,
                )
                .where(AssessmentDecision.id == did)
            )
        ).first()
        if row is not None and await read_scope.readable_card_ids(db, [row[2]], mode="module"):
            title, path = f"{row[1]} — {row[0]}", "/rationalization"
    elif kind == DECISION_OPPORTUNITY:
        opp = await db.get(ImprovementOpportunity, did)
        if opp is not None and not await inaccessible_opportunity_ids(db, read_scope, [opp]):
            title, path = opp.title, "/grc?tab=governance"
    if title is not None:
        out.update(id=str(did), title=title, path=path)
    return out


async def _evidence(
    db: AsyncSession, refs: list[dict] | None, readable: set[uuid.UUID]
) -> list[dict]:
    """Evidence on a card the reader cannot see is shown as restricted."""
    out = []
    for ref in refs or []:
        model = EVIDENCE_MODELS.get(ref.get("kind"))
        if model is None:
            out.append(ref)
            continue
        row = await db.get(model, uuid.UUID(ref["id"]))
        if row is not None and row.card_id in readable:
            out.append({**ref, "card_id": str(row.card_id)})
        elif row is None:
            out.append({**ref, "missing": True})
        else:
            out.append({"kind": ref["kind"], "restricted": True})
    return out


def _money(value: float | None, can_costs: bool) -> float | None:
    return value if can_costs else None


async def _payload(
    db: AsyncSession,
    user: User,
    read_scope: CardReadScope,
    bundle: svc.BenefitBundle,
    readable: set[uuid.UUID],
    *,
    can_costs: bool,
    detail: bool,
) -> dict[str, Any]:
    b = bundle.benefit
    card_ids = [cid for cid in bundle.card_ids() if cid in readable]
    cards = (
        {
            c.id: c
            for c in (await db.execute(select(Card).where(Card.id.in_(card_ids)))).scalars().all()
        }
        if card_ids
        else {}
    )

    def _card(cid: uuid.UUID | None) -> dict | None:
        c = cards.get(cid) if cid else None
        return {"id": str(c.id), "name": c.name, "type": c.type} if c is not None else None

    confirmed = [a for a in bundle.actuals if a.status == CONFIRMED]
    people = {b.owner_id}
    out: dict[str, Any] = {
        "id": str(b.id),
        "reference": b.reference,
        "title": b.title,
        "benefit_type": b.benefit_type,
        "measurement": b.measurement,
        "status": b.status,
        "owner_id": str(b.owner_id) if b.owner_id else None,
        "currency": b.currency,
        "recurrence": b.recurrence,
        "planned_amount": _money(b.planned_amount, can_costs),
        "expected_fiscal_year": b.expected_fiscal_year,
        "confirmed_total": (
            round(sum(a.amount for a in confirmed), 2) if can_costs and confirmed else None
        ),
        "confirmed_years": sorted(a.fiscal_year for a in confirmed),
        "awaiting_finance": sum(1 for a in bundle.actuals if a.status == "reported"),
        "governance_link": b.decision_kind is not None,
        "initiatives": [
            {**card, "classification": lk.classification}
            for lk in bundle.links
            if lk.role == "initiative" and (card := _card(lk.card_id))
        ],
        "kpi_card": _card(b.kpi_card_id),
        "amounts_restricted": not can_costs and b.measurement == "financial",
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }
    if not detail:
        names = await _names(db, people)
        out["owner_name"] = names.get(b.owner_id) if b.owner_id else None
        return out

    history = (
        (
            await db.execute(
                select(BenefitHistory)
                .where(BenefitHistory.benefit_id == b.id)
                .order_by(BenefitHistory.occurred_at.desc(), BenefitHistory.id)
            )
        )
        .scalars()
        .all()
    )
    people |= {b.created_by, b.estimated_by, b.validated_by, b.closed_by}
    people |= {h.actor_id for h in history}
    for a in bundle.actuals:
        people |= {a.reported_by, a.decided_by, a.reversed_by}
    people |= {r.assessed_by for r in bundle.assessments}
    names = await _names(db, people)

    def _who(uid: uuid.UUID | None) -> dict | None:
        return {"id": str(uid), "name": names.get(uid)} if uid else None

    money_changes = {"planned_amount", "baseline_amount", "counterfactual_amount", "amount"}
    money_changes |= {"allocated"}

    def _changes(raw: dict | None) -> dict | None:
        if not raw:
            return None
        if can_costs:
            return raw
        return {k: v for k, v in raw.items() if k not in money_changes}

    actuals = []
    for a in bundle.actuals:
        allocations = bundle.allocations.get(a.id, [])
        actuals.append(
            {
                "id": str(a.id),
                "fiscal_year": a.fiscal_year,
                "amount": _money(a.amount, can_costs),
                "status": a.status,
                "reported_by": _who(a.reported_by),
                "reported_at": a.reported_at.isoformat() if a.reported_at else None,
                "note": a.report_note,
                "evidence": await _evidence(db, a.evidence_refs, readable),
                "decided_by": _who(a.decided_by),
                "decided_at": a.decided_at.isoformat() if a.decided_at else None,
                "finance_reference": a.finance_reference if can_costs else None,
                "decision_note": a.decision_note,
                "reversed_by": _who(a.reversed_by),
                "reversed_at": a.reversed_at.isoformat() if a.reversed_at else None,
                "reverse_reason": a.reverse_reason,
                "allocations": [
                    {
                        "initiative": _card(al.card_id),
                        "classification": al.classification,
                        "amount": _money(al.amount, can_costs),
                        "rationale": al.rationale,
                    }
                    for al in allocations
                    if al.card_id is None or al.card_id in readable
                ]
                if can_costs
                else [],
                "independence_conflict": user.id in svc.independence_conflicts(b, a),
            }
        )
    out.update(
        description=b.description,
        baseline_amount=_money(b.baseline_amount, can_costs),
        counterfactual_amount=_money(b.counterfactual_amount, can_costs),
        counterfactual_note=b.counterfactual_note,
        method_note=b.method_note,
        decision=await _decision_summary(db, user, read_scope, b),
        affected=[c for lk in bundle.links if lk.role == "affected" and (c := _card(lk.card_id))],
        owner=_who(b.owner_id),
        created_by=_who(b.created_by),
        estimated_by=_who(b.estimated_by),
        validated_by=_who(b.validated_by),
        validated_at=b.validated_at.isoformat() if b.validated_at else None,
        validation_note=b.validation_note,
        closed_by=_who(b.closed_by),
        closed_at=b.closed_at.isoformat() if b.closed_at else None,
        close_reason=b.close_reason,
        created_at=b.created_at.isoformat() if b.created_at else None,
        actuals=actuals,
        assessments=[
            {
                "id": str(r.id),
                "fiscal_year": r.fiscal_year,
                "outcome": r.outcome,
                "note": r.note,
                "evidence": await _evidence(db, r.evidence_refs, readable),
                "assessed_by": _who(r.assessed_by),
                "assessed_at": r.assessed_at.isoformat() if r.assessed_at else None,
            }
            for r in bundle.assessments
        ],
        history=[
            {
                "id": str(h.id),
                "action": h.action,
                "from_status": h.from_status,
                "to_status": h.to_status,
                "note": h.note,
                "changes": _changes(h.changes),
                "actor": _who(h.actor_id),
                "occurred_at": h.occurred_at.isoformat() if h.occurred_at else None,
            }
            for h in history
        ],
        permissions={
            "manage": await _can(db, user, svc.MANAGE_PERMISSION),
            "validate": await _can(db, user, svc.VALIDATE_PERMISSION),
            "confirm": await _can(db, user, svc.CONFIRM_PERMISSION),
            "costs": can_costs,
        },
    )
    return out


async def _detail(
    db: AsyncSession, user: User, read_scope: CardReadScope, benefit_id: uuid.UUID
) -> dict[str, Any]:
    bundle, readable = await _load(db, read_scope, benefit_id)
    return await _payload(
        db,
        user,
        read_scope,
        bundle,
        readable,
        can_costs=await _can(db, user, svc.COSTS_PERMISSION),
        detail=True,
    )


async def _require(db: AsyncSession, user: User, *keys: str) -> None:
    for key in keys:
        await PermissionService.require_permission(db, user, key)


def _touches_money(data: dict) -> bool:
    return any(data.get(k) is not None for k in svc.BASIS_FIELDS)


async def _check_owner(db: AsyncSession, owner_id: uuid.UUID | None) -> None:
    if owner_id is None:
        return
    owner = await db.get(User, owner_id)
    if owner is None or not owner.is_active:
        raise HTTPException(422, {"code": "invalid_owner", "message": "Unknown owner"})


async def _current_fy(db: AsyncSession) -> int:
    return current_fiscal_year(await get_fiscal_year_start(db))


# ── Routes ──────────────────────────────────────────────────────────────


@router.get("")
async def list_benefits(
    status: str | None = Query(None, max_length=16),
    benefit_type: str | None = Query(None, max_length=20),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require(db, user, svc.VIEW_PERMISSION)
    if status is not None and status not in STATUSES:
        raise HTTPException(422, "Unknown status")
    if benefit_type is not None and benefit_type not in BENEFIT_TYPES:
        raise HTTPException(422, "Unknown benefit type")
    read_scope = await CardReadScope.load(db, user)
    stmt = select(Benefit).order_by(Benefit.reference.desc())
    if status:
        stmt = stmt.where(Benefit.status == status)
    if benefit_type:
        stmt = stmt.where(Benefit.benefit_type == benefit_type)
    benefits = list((await db.execute(stmt)).scalars().all())
    visible, readable = await svc.visible_bundles(
        db, read_scope, await svc.load_bundles(db, benefits)
    )
    can_costs = await _can(db, user, svc.COSTS_PERMISSION)
    items = [
        await _payload(db, user, read_scope, b, readable, can_costs=can_costs, detail=False)
        for b in visible
    ]
    return {
        "items": items,
        "permissions": {
            "manage": await _can(db, user, svc.MANAGE_PERMISSION),
            "validate": await _can(db, user, svc.VALIDATE_PERMISSION),
            "confirm": await _can(db, user, svc.CONFIRM_PERMISSION),
            "costs": can_costs,
        },
    }


@router.post("", status_code=201)
async def create_benefit(
    body: BenefitCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = body.model_dump()
    await _require(db, user, svc.MANAGE_PERMISSION)
    if _touches_money(data) or body.benefit_type in ("cost_saving", "cost_avoidance", "revenue"):
        await _require(db, user, svc.COSTS_PERMISSION)
    await _check_owner(db, body.owner_id)
    data["initiatives"] = [i.model_dump() for i in body.initiatives or []]
    read_scope = await CardReadScope.load(db, user)
    try:
        bundle = await svc.create_benefit(db, read_scope, data, user.id)
    except LifecycleError as err:
        raise _raise(err) from err
    await db.commit()
    return await _detail(db, user, read_scope, bundle.benefit.id)


@router.get("/{benefit_id}")
async def get_benefit(
    benefit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require(db, user, svc.VIEW_PERMISSION)
    read_scope = await CardReadScope.load(db, user)
    return await _detail(db, user, read_scope, benefit_id)


@router.patch("/{benefit_id}")
async def update_benefit(
    benefit_id: uuid.UUID,
    body: BenefitBase,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require(db, user, svc.MANAGE_PERMISSION)
    data = body.model_dump(exclude_unset=True)
    if any(k in data for k in svc.BASIS_FIELDS):
        await _require(db, user, svc.COSTS_PERMISSION)
    if "initiatives" in data and data["initiatives"] is not None:
        data["initiatives"] = [i.model_dump() for i in body.initiatives or []]
    await _check_owner(db, body.owner_id)
    read_scope = await CardReadScope.load(db, user)
    bundle, _ = await _load(db, read_scope, benefit_id)
    names = await _names(db, {bundle.benefit.owner_id, body.owner_id})
    try:
        await svc.update_benefit(db, read_scope, bundle, data, user.id, owner_names=names)
    except LifecycleError as err:
        raise _raise(err) from err
    await db.commit()
    return await _detail(db, user, read_scope, benefit_id)


@router.post("/{benefit_id}/validate")
async def validate_benefit(
    benefit_id: uuid.UUID,
    body: ValidateBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require(db, user, svc.VALIDATE_PERMISSION, svc.COSTS_PERMISSION)
    read_scope = await CardReadScope.load(db, user)
    bundle, _ = await _load(db, read_scope, benefit_id)
    try:
        await svc.validate(db, bundle.benefit, body.note, user.id)
    except LifecycleError as err:
        raise _raise(err) from err
    await db.commit()
    return await _detail(db, user, read_scope, benefit_id)


@router.post("/{benefit_id}/reopen")
async def reopen_benefit(
    benefit_id: uuid.UUID,
    body: Reason,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require(db, user, svc.VALIDATE_PERMISSION, svc.COSTS_PERMISSION)
    read_scope = await CardReadScope.load(db, user)
    bundle, _ = await _load(db, read_scope, benefit_id)
    try:
        await svc.reopen(db, bundle.benefit, body.reason, user.id)
    except LifecycleError as err:
        raise _raise(err) from err
    await db.commit()
    return await _detail(db, user, read_scope, benefit_id)


@router.post("/{benefit_id}/close")
async def close_benefit(
    benefit_id: uuid.UUID,
    body: CloseBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require(
        db,
        user,
        svc.MANAGE_PERMISSION if body.outcome == "withdrawn" else svc.CONFIRM_PERMISSION,
    )
    read_scope = await CardReadScope.load(db, user)
    bundle, _ = await _load(db, read_scope, benefit_id)
    try:
        await svc.close(db, bundle, body.outcome, body.reason, user.id)
    except LifecycleError as err:
        raise _raise(err) from err
    await db.commit()
    return await _detail(db, user, read_scope, benefit_id)


@router.post("/{benefit_id}/actuals", status_code=201)
async def report_actual(
    benefit_id: uuid.UUID,
    body: ActualCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require(db, user, svc.MANAGE_PERMISSION, svc.COSTS_PERMISSION)
    read_scope = await CardReadScope.load(db, user)
    bundle, _ = await _load(db, read_scope, benefit_id)
    data = body.model_dump(mode="json")
    try:
        await svc.report_actual(
            db, read_scope, bundle, data, user.id, current_fiscal_year=await _current_fy(db)
        )
    except LifecycleError as err:
        raise _raise(err) from err
    await db.commit()
    return await _detail(db, user, read_scope, benefit_id)


@router.post("/{benefit_id}/actuals/{actual_id}/confirm")
async def confirm_actual(
    benefit_id: uuid.UUID,
    actual_id: uuid.UUID,
    body: ConfirmBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require(db, user, svc.CONFIRM_PERMISSION, svc.COSTS_PERMISSION)
    read_scope = await CardReadScope.load(db, user)
    bundle, _ = await _load(db, read_scope, benefit_id)
    try:
        await svc.confirm_actual(
            db, read_scope, bundle, actual_id, body.model_dump(mode="json"), user.id
        )
    except LifecycleError as err:
        raise _raise(err) from err
    await db.commit()
    return await _detail(db, user, read_scope, benefit_id)


@router.post("/{benefit_id}/actuals/{actual_id}/reject")
async def reject_actual(
    benefit_id: uuid.UUID,
    actual_id: uuid.UUID,
    body: Reason,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require(db, user, svc.CONFIRM_PERMISSION, svc.COSTS_PERMISSION)
    read_scope = await CardReadScope.load(db, user)
    bundle, _ = await _load(db, read_scope, benefit_id)
    try:
        await svc.reject_actual(db, bundle, actual_id, body.reason, user.id)
    except LifecycleError as err:
        raise _raise(err) from err
    await db.commit()
    return await _detail(db, user, read_scope, benefit_id)


@router.post("/{benefit_id}/actuals/{actual_id}/reverse")
async def reverse_actual(
    benefit_id: uuid.UUID,
    actual_id: uuid.UUID,
    body: Reason,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require(db, user, svc.CONFIRM_PERMISSION, svc.COSTS_PERMISSION)
    read_scope = await CardReadScope.load(db, user)
    bundle, _ = await _load(db, read_scope, benefit_id)
    try:
        await svc.reverse_actual(db, bundle, actual_id, body.reason, user.id)
    except LifecycleError as err:
        raise _raise(err) from err
    await db.commit()
    return await _detail(db, user, read_scope, benefit_id)


@router.post("/{benefit_id}/assessments", status_code=201)
async def assess_benefit(
    benefit_id: uuid.UUID,
    body: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require(db, user, svc.MANAGE_PERMISSION)
    read_scope = await CardReadScope.load(db, user)
    bundle, _ = await _load(db, read_scope, benefit_id)
    try:
        await svc.assess(
            db,
            read_scope,
            bundle,
            body.model_dump(mode="json"),
            user.id,
            current_fiscal_year=await _current_fy(db),
        )
    except LifecycleError as err:
        raise _raise(err) from err
    await db.commit()
    return await _detail(db, user, read_scope, benefit_id)
