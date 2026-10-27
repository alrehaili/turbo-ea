"""Decision actions and implementation verification routes (D-13, D-41; Batch 3.4).

The same routes under ``/adr/{id}`` and ``/arb/{id}``:

* ``GET  …/implementation`` — deadline, state, actions, history (``adr.view`` /
  ``arb.view``; an ARB review of a hidden subject card is 404, D-30).
* ``POST …/actions``, ``PATCH`` / ``DELETE …/actions/{action_id}`` — the
  decision's manage permission.
* ``POST …/actions/{action_id}/complete`` / ``reopen`` — the action's owner or
  a manager.
* ``POST …/implementation/submit`` — a manager or an action owner.
* ``POST …/implementation/verify`` — ``governance.verify_implementation``,
  independent of the execution (D-41.1).
* ``PUT  …/implementation/due-date`` — the decision's manage permission (the
  governance owner); after approval with a reason (D-41.3). On an unsigned ADR
  it sets the proposed deadline the signatories approve.

Rules live in ``services/decision_implementation.py``; these routes gate,
scope and serialise. Free text (completion notes, evidence, the attestation,
history reasons) goes only to people involved with the decision; others get
``*_withheld: true`` (as I-33 / I-37).

[FORK]
"""

from __future__ import annotations

import uuid
from datetime import date, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.decision_implementation import DECISION_ADR, DECISION_ARB
from app.models.todo import Todo
from app.models.user import User
from app.services import decision_implementation as impl_service
from app.services import governance_transitions
from app.services.card_read_scope import CardReadScope
from app.services.event_bus import event_bus
from app.services.governance_transitions import LifecycleError
from app.services.permission_service import PermissionService
from app.services.todo_service import TodoActor

router = APIRouter(tags=["decision-actions"])


class ActionEvidenceRef(BaseModel):
    kind: str = Field(pattern="^(document|attachment|reference)$")
    id: str | None = None
    text: str | None = Field(default=None, max_length=500)


class ActionCreate(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    assigned_to: uuid.UUID | None = None
    due_date: date | None = None


class ActionUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=2000)
    assigned_to: uuid.UUID | None = None
    due_date: date | None = None


class ActionComplete(BaseModel):
    note: str | None = Field(default=None, max_length=4000)
    evidence: list[ActionEvidenceRef] = Field(default_factory=list, max_length=20)


class SubmitBody(BaseModel):
    note: str | None = Field(default=None, max_length=4000)


class Attestation(BaseModel):
    examined: str | None = Field(default=None, max_length=4000)
    demonstrates: str | None = Field(default=None, max_length=4000)
    confirmed: bool = False


class VerifyBody(BaseModel):
    outcome: str = Field(pattern="^(verified|returned)$")
    note: str | None = Field(default=None, max_length=4000)
    attestation: Attestation | None = None


class DueDateBody(BaseModel):
    due_date: date | None = None
    reason: str | None = Field(default=None, max_length=2000)


def _raise(err: LifecycleError) -> None:
    raise HTTPException(err.status, {"code": err.code, "message": str(err)}) from err


async def _load(db: AsyncSession, user: User, kind: str, decision_id: uuid.UUID):
    """The decision after the module's view gate, or 404 (also for an ARB review
    of a hidden subject card — it does not exist for the reader, D-30)."""
    await PermissionService.require_permission(db, user, impl_service.VIEW_PERMISSION[kind])
    decision = await impl_service.load_decision(db, kind, decision_id)
    if decision is None:
        raise HTTPException(404, "Decision not found")
    if kind == DECISION_ARB and decision.subject_card_id:
        scope = await CardReadScope.load(db, user)
        if not await scope.readable_card_ids(db, [decision.subject_card_id], mode="module"):
            raise HTTPException(404, "Decision not found")
    return decision


async def _is_manager(db: AsyncSession, user: User, kind: str) -> bool:
    return await PermissionService.check_permission(db, user, impl_service.MANAGE_PERMISSION[kind])


async def _require_manager(db: AsyncSession, user: User, kind: str) -> None:
    await PermissionService.require_permission(db, user, impl_service.MANAGE_PERMISSION[kind])


async def _action(ctx: impl_service.DecisionContext, action_id: uuid.UUID) -> Todo:
    for a in ctx.actions:
        if a.id == action_id:
            return a
    raise HTTPException(404, "Action not found")


def _actor(user: User) -> TodoActor:
    return TodoActor(user_id=user.id, display_name=user.display_name)


async def _publish(db: AsyncSession, kind: str, decision_id: uuid.UUID, event: str, user: User):
    """An audit row for each implementation step (no card: decisions are not cards)."""
    await event_bus.publish(
        f"decision_implementation.{event}",
        {"decision_kind": kind, "decision_id": str(decision_id)},
        db=db,
        user_id=user.id,
    )


async def _names(db: AsyncSession, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = await db.execute(select(User.id, User.display_name).where(User.id.in_(ids)))
    return dict(rows.all())


def _person(uid: uuid.UUID | None, names: dict[uuid.UUID, str]) -> dict | None:
    return {"id": str(uid), "display_name": names.get(uid)} if uid else None


def _iso(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "tzinfo") and value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


async def _payload(db: AsyncSession, user: User, ctx: impl_service.DecisionContext) -> dict:
    kind, decision, impl, actions = ctx.kind, ctx.decision, ctx.impl, ctx.actions
    manager = await _is_manager(db, user, kind)
    verifier = await PermissionService.check_permission(db, user, impl_service.VERIFY_PERMISSION)
    involved = impl_service.involved_in_execution(ctx)
    # Free text goes to the people the decision concerns (I-33 / I-37 posture).
    may_read_text = manager or verifier or user.id in involved or decision.created_by == user.id
    scope = await CardReadScope.load(db, user)
    cited = await impl_service.evidence_card_ids(db, actions)
    on_cards = {c for c in cited.values() if c is not None}
    readable = await scope.readable_card_ids(db, on_cards, mode="module") if on_cards else set()

    def evidence(refs: list[dict] | None) -> list[dict]:
        out = []
        for r in refs or []:
            card = cited.get(r.get("id")) if r.get("kind") != "reference" else None
            if card is not None and card not in readable:
                out.append({"kind": r["kind"], "hidden": True})
            else:
                out.append(r)
        return out

    names = await _names(
        db,
        {a.assigned_to for a in actions}
        | {a.completed_by for a in actions}
        | ({impl.submitted_by, impl.verified_by} if impl else set()),
    )
    today = date.today()
    instrument = impl_service.INSTRUMENT_BY_KIND[kind]
    history = await governance_transitions.transition_history(
        db, instrument, decision.id, withhold_reason=not may_read_text
    )
    return {
        "decision": {
            "kind": kind,
            "id": str(decision.id),
            "status": decision.status,
            "approved": impl_service.is_approved(kind, decision),
        },
        "state": impl_service.derive_state(impl, actions),
        "overdue": impl_service.is_overdue(impl, today),
        "implementation": {
            "status": impl.status if impl else "open",
            "due_date": impl.due_date.isoformat() if impl and impl.due_date else None,
            "original_due_date": (
                impl.original_due_date.isoformat() if impl and impl.original_due_date else None
            ),
            "due_date_basis": impl.due_date_basis if impl else None,
            "revised": bool(
                impl and impl.original_due_date and impl.due_date != impl.original_due_date
            ),
            "submitted_by": _person(impl.submitted_by, names) if impl else None,
            "submitted_at": _iso(impl.submitted_at) if impl else None,
            "submission_note": (impl.submission_note if impl and may_read_text else None),
            "verified_by": _person(impl.verified_by, names) if impl else None,
            "verified_at": _iso(impl.verified_at) if impl else None,
            "attestation": (impl.attestation if impl and may_read_text else None),
            "text_withheld": not may_read_text,
        },
        "actions": [
            {
                "id": str(a.id),
                "description": a.description,
                "status": a.status,
                "assigned_to": _person(a.assigned_to, names),
                "due_date": a.due_date.isoformat() if a.due_date else None,
                "completed_by": _person(a.completed_by, names),
                "completed_at": _iso(a.completed_at),
                "completion_note": a.completion_note if may_read_text else None,
                "evidence": evidence(a.evidence_refs) if may_read_text else [],
                "evidence_count": len(a.evidence_refs or []),
                # The action's owner or a manager may complete or reopen it.
                "can_complete": manager or a.assigned_to == user.id,
            }
            for a in actions
        ],
        "history": governance_transitions.history_payload(history),
        "permissions": {
            "manage": manager,
            "verify": verifier and user.id not in involved,
            "submit": manager or any(a.assigned_to == user.id for a in actions),
        },
    }


async def _evidence(
    db: AsyncSession, user: User, ctx: impl_service.DecisionContext, refs: list[ActionEvidenceRef]
) -> list[dict]:
    linked = await impl_service.linked_card_ids(db, ctx.kind, ctx.decision)
    scope = await CardReadScope.load(db, user)
    readable = await scope.readable_card_ids(db, linked, mode="module") if linked else set()
    return await impl_service.resolve_evidence(
        db, [r.model_dump() for r in refs], linked, set(readable)
    )


def _register(kind: str) -> None:
    """The routes for one decision kind (explicit prefixes, never a ``{kind}``
    wildcard that would shadow other routers)."""
    base = f"/{kind}/{{decision_id}}"

    @router.get(base + "/implementation", name=f"{kind}_implementation")
    async def get_implementation(
        decision_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        decision = await _load(db, user, kind, decision_id)
        return await _payload(db, user, await impl_service.context(db, kind, decision))

    @router.post(base + "/actions", status_code=201, name=f"{kind}_create_action")
    async def create_action(
        decision_id: uuid.UUID,
        body: ActionCreate,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        decision = await _load(db, user, kind, decision_id)
        await _require_manager(db, user, kind)
        ctx = await impl_service.context(db, kind, decision)
        try:
            await impl_service.create_action(
                db,
                _actor(user),
                ctx,
                description=body.description,
                assigned_to=body.assigned_to,
                due_date=body.due_date,
            )
        except LifecycleError as err:
            _raise(err)
        await db.commit()
        return await _payload(db, user, await impl_service.context(db, kind, decision))

    @router.patch(base + "/actions/{action_id}", name=f"{kind}_update_action")
    async def update_action(
        decision_id: uuid.UUID,
        action_id: uuid.UUID,
        body: ActionUpdate,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        decision = await _load(db, user, kind, decision_id)
        await _require_manager(db, user, kind)
        ctx = await impl_service.context(db, kind, decision)
        todo = await _action(ctx, action_id)
        try:
            await impl_service.update_action(
                db, _actor(user), ctx, todo, body.model_dump(exclude_unset=True)
            )
        except LifecycleError as err:
            _raise(err)
        await db.commit()
        return await _payload(db, user, await impl_service.context(db, kind, decision))

    @router.delete(base + "/actions/{action_id}", name=f"{kind}_delete_action")
    async def delete_action(
        decision_id: uuid.UUID,
        action_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        decision = await _load(db, user, kind, decision_id)
        await _require_manager(db, user, kind)
        ctx = await impl_service.context(db, kind, decision)
        todo = await _action(ctx, action_id)
        try:
            await impl_service.delete_action(db, _actor(user), ctx, todo)
        except LifecycleError as err:
            _raise(err)
        await db.commit()
        return await _payload(db, user, await impl_service.context(db, kind, decision))

    @router.post(base + "/actions/{action_id}/complete", name=f"{kind}_complete_action")
    async def complete_action(
        decision_id: uuid.UUID,
        action_id: uuid.UUID,
        body: ActionComplete,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        decision = await _load(db, user, kind, decision_id)
        ctx = await impl_service.context(db, kind, decision)
        todo = await _action(ctx, action_id)
        if not impl_service.may_complete(todo, user.id, manager=await _is_manager(db, user, kind)):
            raise HTTPException(403, "Only the action's owner or a manager can complete it")
        try:
            refs = await _evidence(db, user, ctx, body.evidence)
            await impl_service.complete_action(
                db, _actor(user), ctx, todo, note=body.note, evidence=refs
            )
        except LifecycleError as err:
            _raise(err)
        await db.commit()
        return await _payload(db, user, await impl_service.context(db, kind, decision))

    @router.post(base + "/actions/{action_id}/reopen", name=f"{kind}_reopen_action")
    async def reopen_action(
        decision_id: uuid.UUID,
        action_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        decision = await _load(db, user, kind, decision_id)
        ctx = await impl_service.context(db, kind, decision)
        todo = await _action(ctx, action_id)
        if not impl_service.may_complete(todo, user.id, manager=await _is_manager(db, user, kind)):
            raise HTTPException(403, "Only the action's owner or a manager can reopen it")
        try:
            await impl_service.reopen_action(db, _actor(user), ctx, todo)
        except LifecycleError as err:
            _raise(err)
        await db.commit()
        return await _payload(db, user, await impl_service.context(db, kind, decision))

    @router.post(base + "/implementation/submit", name=f"{kind}_submit_implementation")
    async def submit_implementation(
        decision_id: uuid.UUID,
        body: SubmitBody,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        decision = await _load(db, user, kind, decision_id)
        ctx = await impl_service.context(db, kind, decision)
        owner = any(a.assigned_to == user.id for a in ctx.actions)
        if not owner:
            await _require_manager(db, user, kind)
        try:
            await impl_service.submit(db, ctx, body.note, user.id)
        except LifecycleError as err:
            _raise(err)
        await _publish(db, kind, decision.id, "submitted", user)
        await db.commit()
        return await _payload(db, user, await impl_service.context(db, kind, decision))

    @router.post(base + "/implementation/verify", name=f"{kind}_verify_implementation")
    async def verify_implementation(
        decision_id: uuid.UUID,
        body: VerifyBody,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        decision = await _load(db, user, kind, decision_id)
        await PermissionService.require_permission(db, user, impl_service.VERIFY_PERMISSION)
        ctx = await impl_service.context(db, kind, decision)
        try:
            await impl_service.verify(
                db,
                ctx,
                body.outcome,
                body.note,
                body.attestation.model_dump() if body.attestation else None,
                user.id,
            )
        except LifecycleError as err:
            _raise(err)
        await _publish(db, kind, decision.id, body.outcome, user)
        await db.commit()
        return await _payload(db, user, await impl_service.context(db, kind, decision))

    @router.put(base + "/implementation/due-date", name=f"{kind}_implementation_due_date")
    async def set_due_date(
        decision_id: uuid.UUID,
        body: DueDateBody,
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        decision = await _load(db, user, kind, decision_id)
        await _require_manager(db, user, kind)
        try:
            if kind == DECISION_ADR and decision.status != "signed":
                # A proposal the signatories approve by signing (D-41.3).
                await impl_service.propose_due_date(db, decision, body.due_date)
            else:
                await impl_service.change_due_date(
                    db, kind, decision, body.due_date, body.reason, user.id
                )
                await _publish(db, kind, decision.id, "due_date_changed", user)
        except LifecycleError as err:
            _raise(err)
        await db.commit()
        return await _payload(db, user, await impl_service.context(db, kind, decision))


_register(DECISION_ADR)
_register(DECISION_ARB)
