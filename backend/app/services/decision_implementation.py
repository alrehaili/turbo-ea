"""Decision actions and implementation verification (D-13, D-32, D-41; Batch 3.4).

The one definition of how an approved architecture decision — a **signed ADR**
or an **approved ARB review** — is implemented and verified:

* **Actions** are todos linked to the decision (``source_kind`` /
  ``source_id``), each with an accountable owner and a due date (D-13). An
  action is completed with a note and **at least one evidence reference**
  (D-41.2): a document or file on a card linked to the decision, or — for any
  decision, including one with no linked card — a recorded system reference
  (a change ticket, release, deployment record, document number or in-app
  path). No file is required per action and nothing is fingerprinted; the
  references are checked when cited and again at verification.
* **Implementation** is submitted once every action is complete, then
  **independently verified** (D-41.1): the verifier holds
  ``governance.verify_implementation`` and owns, completed and submitted none
  of it. ADR signatories and the ARB reviewer may verify when independent.
  Completed actions alone never make a decision implemented (D-32).
* **Deadline** (D-41.3): the implementation due date approved with the
  decision is kept as ``original_due_date`` and never changes; a governance
  owner may revise the date in force with a mandatory reason, each revision an
  append-only ``due_date_changed`` row. Nothing is invented for decisions
  approved before this existed.

Helpers flush at most and never commit (the route owns the session). Errors are
:class:`~app.services.governance_transitions.LifecycleError` with an HTTP status
and a machine-readable code.

[FORK]
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.architecture_decision_card import ArchitectureDecisionCard
from app.models.decision_implementation import (
    BASIS_AFTER_DECISION,
    BASIS_WITH_DECISION,
    DECISION_ADR,
    DECISION_ARB,
    DECISION_KINDS,
    STATUS_OPEN,
    STATUS_SUBMITTED,
    STATUS_VERIFIED,
    DecisionImplementation,
)
from app.models.document import Document
from app.models.file_attachment import FileAttachment
from app.models.governance_transition import (
    EVENT_DUE_DATE_CHANGED,
    EVENT_DUE_DATE_SET,
    INSTRUMENT_ADR_IMPL,
    INSTRUMENT_ARB_IMPL,
    GovernanceTransition,
)
from app.models.todo import Todo
from app.services import todo_service
from app.services.governance_transitions import LifecycleError, record_transition
from app.services.todo_service import TodoActor

#: Evidence a decision action may cite. Documents and files are the existing
#: card evidence mechanisms; a reference is recorded on the action itself.
EVIDENCE_CARD_MODELS = {"document": Document, "attachment": FileAttachment}
EVIDENCE_REFERENCE = "reference"
MAX_EVIDENCE_REFS = 20
MAX_REFERENCE_LENGTH = 500

#: Derived states of a decision's implementation (D-41.4).
STATE_NO_PLAN = "no_plan"
STATE_IN_PROGRESS = "in_progress"
STATE_AWAITING = "awaiting_verification"
STATE_IMPLEMENTED = "implemented"

INSTRUMENT_BY_KIND = {DECISION_ADR: INSTRUMENT_ADR_IMPL, DECISION_ARB: INSTRUMENT_ARB_IMPL}
MANAGE_PERMISSION = {DECISION_ADR: "adr.manage", DECISION_ARB: "arb.manage"}
VIEW_PERMISSION = {DECISION_ADR: "adr.view", DECISION_ARB: "arb.view"}
VERIFY_PERMISSION = "governance.verify_implementation"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _instrument(kind: str) -> str:
    if kind not in DECISION_KINDS:
        raise ValueError(f"unknown decision kind: {kind!r}")
    return INSTRUMENT_BY_KIND[kind]


def is_approved(kind: str, decision: Any) -> bool:
    """A decision that can be implemented: a signed ADR, an approved ARB review."""
    if kind == DECISION_ADR:
        return decision.status == "signed"
    return decision.status == "approved"


def decision_link(kind: str, decision_id: uuid.UUID) -> str:
    """Where an action's todo points: the decision's own page."""
    if kind == DECISION_ADR:
        return f"/ea-delivery/adr/{decision_id}/preview"
    return f"/arb?review={decision_id}"


async def load_decision(db: AsyncSession, kind: str, decision_id: uuid.UUID) -> Any | None:
    model = ArchitectureDecision if kind == DECISION_ADR else ArbReview
    return await db.get(model, decision_id)


async def linked_card_ids(db: AsyncSession, kind: str, decision: Any) -> set[uuid.UUID]:
    """The cards a decision is about: an ADR's linked cards, an ARB subject."""
    if kind == DECISION_ARB:
        return {decision.subject_card_id} if decision.subject_card_id else set()
    rows = await db.execute(
        select(ArchitectureDecisionCard.card_id).where(
            ArchitectureDecisionCard.architecture_decision_id == decision.id
        )
    )
    return set(rows.scalars().all())


async def get_implementation(
    db: AsyncSession, kind: str, decision_id: uuid.UUID, *, create: bool = False
) -> DecisionImplementation | None:
    row = (
        await db.execute(
            select(DecisionImplementation).where(
                DecisionImplementation.decision_kind == kind,
                DecisionImplementation.decision_id == decision_id,
            )
        )
    ).scalar_one_or_none()
    if row is None and create:
        row = DecisionImplementation(
            decision_kind=kind, decision_id=decision_id, status=STATUS_OPEN
        )
        db.add(row)
        await db.flush()
    return row


async def list_actions(db: AsyncSession, kind: str, decision_id: uuid.UUID) -> list[Todo]:
    rows = await db.execute(
        select(Todo)
        .where(Todo.source_kind == kind, Todo.source_id == decision_id)
        .order_by(Todo.created_at)
    )
    return list(rows.scalars().all())


async def delete_decision_records(db: AsyncSession, kind: str, decision_id: uuid.UUID) -> None:
    """Remove a deleted decision's actions and implementation row.

    The transition history is kept (it is append-only and has no FK)."""
    for todo in await list_actions(db, kind, decision_id):
        await db.delete(todo)
    impl = await get_implementation(db, kind, decision_id)
    if impl is not None:
        await db.delete(impl)


# ── State ────────────────────────────────────────────────────────────────


def derive_state(impl: DecisionImplementation | None, actions: list[Todo]) -> str:
    """The decision's implementation state now (D-41.4).

    Only an independent verification makes a decision implemented; actions all
    done but not verified are ``in_progress`` until submitted, then awaiting."""
    if impl is not None and impl.status == STATUS_VERIFIED:
        return STATE_IMPLEMENTED
    if impl is not None and impl.status == STATUS_SUBMITTED:
        return STATE_AWAITING
    return STATE_IN_PROGRESS if actions else STATE_NO_PLAN


def is_overdue(impl: DecisionImplementation | None, today: date) -> bool:
    """The deadline in force has passed and the decision is not verified."""
    return (
        impl is not None
        and impl.status != STATUS_VERIFIED
        and impl.due_date is not None
        and impl.due_date < today
    )


def _require_not_verified(impl: DecisionImplementation | None) -> None:
    if impl is not None and impl.status == STATUS_VERIFIED:
        raise LifecycleError(
            409,
            "implementation_verified",
            "The implementation is verified; it can no longer change",
        )


def _require_approved(kind: str, decision: Any) -> None:
    if not is_approved(kind, decision):
        raise LifecycleError(
            409,
            "decision_not_approved",
            "Actions and deadlines apply to a signed ADR or an approved ARB review",
        )


def _reopen(
    db: AsyncSession,
    kind: str,
    impl: DecisionImplementation | None,
    actor_id: uuid.UUID | None,
    reason: str,
) -> None:
    """A change to the actions after submission returns it to ``open``: what was
    submitted is no longer what would be verified."""
    if impl is None or impl.status != STATUS_SUBMITTED:
        return
    impl.status = STATUS_OPEN
    record_transition(
        db,
        _instrument(kind),
        impl.decision_id,
        STATUS_SUBMITTED,
        STATUS_OPEN,
        actor_id,
        reason=reason,
    )


# ── Deadline (D-41.3) ────────────────────────────────────────────────────


def _due_event(
    db: AsyncSession,
    kind: str,
    impl: DecisionImplementation,
    event_kind: str,
    previous: date | None,
    new: date,
    actor_id: uuid.UUID | None,
    reason: str | None,
    occurred_at: datetime | None = None,
) -> GovernanceTransition:
    row = GovernanceTransition(
        instrument=_instrument(kind),
        record_id=impl.decision_id,
        from_status=impl.status,
        to_status=impl.status,
        actor_id=actor_id,
        occurred_at=occurred_at or _now(),
        reason=reason,
        event_kind=event_kind,
        previous_due_date=previous,
        due_date=new,
    )
    db.add(row)
    return row


async def propose_due_date(
    db: AsyncSession, decision: ArchitectureDecision, due: date | None
) -> None:
    """Set or clear the deadline of an **unsigned** ADR. It is a proposal the
    signatories approve by signing; no event, since nothing is approved yet."""
    if decision.status == "signed":
        raise LifecycleError(409, "decision_signed", "A signed decision's deadline is revised")
    impl = await get_implementation(db, DECISION_ADR, decision.id, create=due is not None)
    if impl is not None:
        impl.due_date = due


async def approve_proposed_due_date(
    db: AsyncSession,
    kind: str,
    decision_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    occurred_at: datetime | None = None,
) -> None:
    """At signing: the proposed deadline becomes the original approved one."""
    impl = await get_implementation(db, kind, decision_id)
    if impl is None or impl.due_date is None or impl.original_due_date is not None:
        return
    impl.original_due_date = impl.due_date
    impl.due_date_basis = BASIS_WITH_DECISION
    _due_event(db, kind, impl, EVENT_DUE_DATE_SET, None, impl.due_date, actor_id, None, occurred_at)


async def approve_with_due_date(
    db: AsyncSession,
    kind: str,
    decision_id: uuid.UUID,
    due: date,
    actor_id: uuid.UUID | None,
) -> None:
    """An ARB approval that carries its deadline. A deadline already approved
    is revised through :func:`change_due_date`, with a reason."""
    impl = await get_implementation(db, kind, decision_id, create=True)
    if impl.original_due_date is not None:
        if impl.due_date == due:
            return
        raise LifecycleError(
            409, "due_date_already_approved", "Revise the approved deadline with a reason"
        )
    impl.due_date = due
    impl.original_due_date = due
    impl.due_date_basis = BASIS_WITH_DECISION
    _due_event(db, kind, impl, EVENT_DUE_DATE_SET, None, due, actor_id, None)


async def change_due_date(
    db: AsyncSession,
    kind: str,
    decision: Any,
    new_due: date | None,
    reason: str | None,
    actor_id: uuid.UUID,
) -> DecisionImplementation:
    """Set or revise an approved decision's deadline, with a mandatory reason.

    With no approved deadline yet (approved without one, or before this
    existed) the date becomes the original deadline with basis
    ``set_after_decision``; otherwise it replaces the deadline in force and the
    original stays as approved. Every step is an append-only event."""
    _require_approved(kind, decision)
    if new_due is None:
        raise LifecycleError(422, "due_date_required", "An approved deadline cannot be removed")
    reason = _text(reason)
    if reason is None:
        raise LifecycleError(
            422, "due_date_reason_required", "Say why the deadline is set or changed"
        )
    impl = await get_implementation(db, kind, decision.id, create=True)
    _require_not_verified(impl)
    if impl.original_due_date is None:
        impl.original_due_date = new_due
        impl.due_date = new_due
        impl.due_date_basis = BASIS_AFTER_DECISION
        _due_event(db, kind, impl, EVENT_DUE_DATE_SET, None, new_due, actor_id, reason)
        return impl
    if new_due == impl.due_date:
        return impl
    previous = impl.due_date
    impl.due_date = new_due
    _due_event(db, kind, impl, EVENT_DUE_DATE_CHANGED, previous, new_due, actor_id, reason)
    return impl


# ── Evidence (D-41.2) ────────────────────────────────────────────────────


async def resolve_evidence(
    db: AsyncSession,
    refs: list[dict] | None,
    linked_ids: set[uuid.UUID],
    readable_ids: set[uuid.UUID],
) -> list[dict]:
    """Check an action's evidence references; at least one is required.

    ``document`` / ``attachment``: an existing document or file on a card linked
    to the decision that the person completing the action may read
    (``readable_ids``). ``reference``: a recorded system reference, accepted for
    any decision — the way a decision with no linked card carries evidence.
    Duplicates are kept once."""
    resolved: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for ref in refs or []:
        kind = ref.get("kind")
        if kind == EVIDENCE_REFERENCE:
            text = _text(ref.get("text"))
            if text is None or len(text) > MAX_REFERENCE_LENGTH:
                raise LifecycleError(
                    422, "invalid_evidence_ref", "A reference needs text of at most 500 characters"
                )
            key = (kind, text)
            item = {"kind": kind, "text": text}
        else:
            model = EVIDENCE_CARD_MODELS.get(kind)
            try:
                ref_id = uuid.UUID(str(ref.get("id")))
            except ValueError:
                model = None
            row = await db.get(model, ref_id) if model is not None else None
            if row is None or row.card_id not in linked_ids or row.card_id not in readable_ids:
                raise LifecycleError(
                    422,
                    "invalid_evidence_ref",
                    "Evidence must be a document or file on a card linked to the decision",
                )
            key = (kind, str(ref_id))
            # Ids of module rows only (kept by workspace transfer); the card is
            # looked up from the row whenever it matters.
            item = {"kind": kind, "id": str(ref_id), "name": row.name}
        if key in seen:
            continue
        seen.add(key)
        resolved.append(item)
    if not resolved:
        raise LifecycleError(422, "evidence_required", "Cite at least one piece of evidence")
    if len(resolved) > MAX_EVIDENCE_REFS:
        raise LifecycleError(422, "too_many_evidence_refs", "Cite at most 20 items")
    return resolved


async def evidence_card_ids(db: AsyncSession, actions: list[Todo]) -> dict[str, uuid.UUID | None]:
    """The card each cited document or file is on now (``None`` when gone),
    keyed by the cited id — what decides whether a reader may see the item."""
    cards: dict[str, uuid.UUID | None] = {}
    for action in actions:
        for ref in action.evidence_refs or []:
            model = EVIDENCE_CARD_MODELS.get(ref.get("kind"))
            if model is None or ref["id"] in cards:
                continue
            row = await db.get(model, uuid.UUID(ref["id"]))
            cards[ref["id"]] = row.card_id if row is not None else None
    return cards


async def missing_evidence(
    db: AsyncSession, actions: list[Todo], linked_ids: set[uuid.UUID]
) -> list[dict]:
    """Cited documents and files that are gone, or no longer on a linked card."""
    missing: list[dict] = []
    for action in actions:
        for ref in action.evidence_refs or []:
            model = EVIDENCE_CARD_MODELS.get(ref.get("kind"))
            if model is None:
                continue
            row = await db.get(model, uuid.UUID(ref["id"]))
            if row is None or row.card_id not in linked_ids:
                missing.append({"action_id": str(action.id), **ref})
    return missing


# ── Actions (D-13) ───────────────────────────────────────────────────────


@dataclass
class DecisionContext:
    kind: str
    decision: Any
    impl: DecisionImplementation | None
    actions: list[Todo]


async def context(db: AsyncSession, kind: str, decision: Any) -> DecisionContext:
    return DecisionContext(
        kind=kind,
        decision=decision,
        impl=await get_implementation(db, kind, decision.id),
        actions=await list_actions(db, kind, decision.id),
    )


async def create_action(
    db: AsyncSession,
    actor: TodoActor,
    ctx: DecisionContext,
    *,
    description: str | None,
    assigned_to: uuid.UUID | None,
    due_date: date | None,
) -> Todo:
    """An action with an accountable owner and a due date (D-13)."""
    _require_approved(ctx.kind, ctx.decision)
    _require_not_verified(ctx.impl)
    description = _text(description)
    if description is None:
        raise LifecycleError(422, "description_required", "Describe the action")
    if assigned_to is None:
        raise LifecycleError(422, "owner_required", "An action needs an accountable owner")
    if due_date is None:
        raise LifecycleError(422, "due_date_required", "An action needs a due date")
    todo = await todo_service.create_todo(
        db,
        actor,
        description=description,
        assigned_to=assigned_to,
        due_date=due_date,
        link=decision_link(ctx.kind, ctx.decision.id),
    )
    todo.source_kind = ctx.kind
    todo.source_id = ctx.decision.id
    _reopen(db, ctx.kind, ctx.impl, actor.user_id, "action_added")
    return todo


async def update_action(
    db: AsyncSession, actor: TodoActor, ctx: DecisionContext, todo: Todo, changes: dict
) -> Todo:
    """Change an action's description, owner or due date; neither the owner nor
    the due date can be removed.

    A change of owner or due date is **material**: it is refused once the
    implementation is verified and returns a submitted one to ``open``. A
    wording change of the description is **cosmetic**: it is accepted in every
    state and never invalidates a submission or a verification (the
    verification keeps the description it verified)."""
    allowed = {"description", "assigned_to", "due_date"}
    changes = {k: v for k, v in changes.items() if k in allowed}
    if "description" in changes:
        changes["description"] = _text(changes["description"])
        if changes["description"] is None:
            raise LifecycleError(422, "description_required", "Describe the action")
    if "assigned_to" in changes and changes["assigned_to"] is None:
        raise LifecycleError(422, "owner_required", "An action needs an accountable owner")
    if "due_date" in changes and changes["due_date"] is None:
        raise LifecycleError(422, "due_date_required", "An action needs a due date")
    material = is_material_change(todo, changes)
    if material:
        _require_not_verified(ctx.impl)
    if not changes:
        return todo
    await todo_service.update_todo(db, actor, todo, changes, allow_decision_action=True)
    if material:
        _reopen(db, ctx.kind, ctx.impl, actor.user_id, "action_changed")
    return todo


#: Action fields whose change alters what was planned and would be verified.
MATERIAL_FIELDS = ("assigned_to", "due_date")


def is_material_change(todo: Todo, changes: dict) -> bool:
    """True when the owner or the due date actually changes (D-41, rule 3).

    Re-sending the current value is no change; the description is cosmetic."""
    for field in MATERIAL_FIELDS:
        if field not in changes:
            continue
        new = changes[field]
        if field == "assigned_to" and new is not None and not isinstance(new, uuid.UUID):
            new = uuid.UUID(str(new))
        if field == "due_date" and isinstance(new, str):
            new = date.fromisoformat(new)
        if new != getattr(todo, field):
            return True
    return False


async def complete_action(
    db: AsyncSession,
    actor: TodoActor,
    ctx: DecisionContext,
    todo: Todo,
    *,
    note: str | None,
    evidence: list[dict],
) -> Todo:
    """Complete an action with a note and the evidence :func:`resolve_evidence`
    accepted. Completing never verifies anything (D-32)."""
    _require_not_verified(ctx.impl)
    if todo.status == "done":
        raise LifecycleError(409, "action_done", "The action is already complete")
    note = _text(note)
    if note is None:
        raise LifecycleError(422, "completion_note_required", "Say what was done")
    if not evidence:
        raise LifecycleError(422, "evidence_required", "Cite at least one piece of evidence")
    todo.completion_note = note
    todo.evidence_refs = list(evidence)
    todo.completed_by = actor.user_id
    todo.completed_at = _now()
    await todo_service.update_todo(db, actor, todo, {"status": "done"}, allow_decision_action=True)
    return todo


async def reopen_action(
    db: AsyncSession, actor: TodoActor, ctx: DecisionContext, todo: Todo
) -> Todo:
    """Reopen a completed action; its completion record is cleared and a
    submitted implementation returns to ``open``."""
    _require_not_verified(ctx.impl)
    if todo.status != "done":
        raise LifecycleError(409, "action_open", "The action is not complete")
    todo.completion_note = None
    todo.evidence_refs = None
    todo.completed_by = None
    todo.completed_at = None
    await todo_service.update_todo(db, actor, todo, {"status": "open"}, allow_decision_action=True)
    _reopen(db, ctx.kind, ctx.impl, actor.user_id, "action_reopened")
    return todo


async def delete_action(
    db: AsyncSession, actor: TodoActor, ctx: DecisionContext, todo: Todo
) -> None:
    _require_not_verified(ctx.impl)
    _reopen(db, ctx.kind, ctx.impl, actor.user_id, "action_deleted")
    await todo_service.delete_todo(db, actor, todo, allow_decision_action=True)


def may_complete(todo: Todo, actor_id: uuid.UUID, *, manager: bool) -> bool:
    """The action's owner, or a holder of the decision's manage permission."""
    return manager or (todo.assigned_to is not None and todo.assigned_to == actor_id)


# ── Submission and verification (D-41.1) ────────────────────────────────


async def submit(
    db: AsyncSession, ctx: DecisionContext, note: str | None, actor_id: uuid.UUID
) -> DecisionImplementation:
    """Submit the implementation for verification: at least one action, every
    action complete with evidence."""
    _require_approved(ctx.kind, ctx.decision)
    impl = ctx.impl or await get_implementation(db, ctx.kind, ctx.decision.id, create=True)
    if impl.status != STATUS_OPEN:
        raise LifecycleError(409, "invalid_state", f"The implementation is {impl.status}")
    if not ctx.actions:
        raise LifecycleError(409, "no_actions", "A decision with no actions has no plan to verify")
    if any(a.status != "done" for a in ctx.actions):
        raise LifecycleError(409, "actions_open", "Every action must be complete")
    if any(not a.evidence_refs for a in ctx.actions):
        raise LifecycleError(409, "evidence_required", "Every action must cite evidence")
    impl.status = STATUS_SUBMITTED
    impl.submitted_by = actor_id
    impl.submitted_at = _now()
    impl.submission_note = _text(note)
    record_transition(
        db,
        _instrument(ctx.kind),
        impl.decision_id,
        STATUS_OPEN,
        STATUS_SUBMITTED,
        actor_id,
        occurred_at=impl.submitted_at,
        reason=impl.submission_note,
    )
    ctx.impl = impl
    return impl


def involved_in_execution(ctx: DecisionContext) -> set[uuid.UUID]:
    """Everyone the verifier must not be: owners and completers of any action,
    and the person who submitted the implementation (D-41.1)."""
    people: set[uuid.UUID | None] = set()
    for a in ctx.actions:
        people.update({a.assigned_to, a.completed_by})
    if ctx.impl is not None:
        people.add(ctx.impl.submitted_by)
    people.discard(None)
    return people  # type: ignore[return-value]


async def verify(
    db: AsyncSession,
    ctx: DecisionContext,
    outcome: str,
    note: str | None,
    attestation: dict | None,
    actor_id: uuid.UUID,
) -> DecisionImplementation:
    """Verify a submitted implementation, or return it to ``open`` with a note.

    The verifier is independent of the execution (403 ``self_verification``).
    ``verified`` needs every cited document and file still on a linked card
    (409 ``evidence_missing`` — return it so the evidence can be re-cited) and
    an explicit attestation of what was examined and why it demonstrates the
    implementation, confirmed (422 ``attestation_required``). The attestation
    keeps the action evidence as verified."""
    if outcome not in ("verified", "returned"):
        raise LifecycleError(422, "invalid_outcome", f"Unknown outcome: {outcome!r}")
    impl = ctx.impl
    if impl is None or impl.status != STATUS_SUBMITTED:
        raise LifecycleError(409, "invalid_state", "Only a submitted implementation is verified")
    if actor_id in involved_in_execution(ctx):
        raise LifecycleError(
            403,
            "self_verification",
            "Implementation must be verified by someone who did not own, complete or submit it",
        )
    note = _text(note)
    now = _now()
    instrument = _instrument(ctx.kind)
    if outcome == "returned":
        if note is None:
            raise LifecycleError(422, "note_required", "Say why the implementation is returned")
        impl.status = STATUS_OPEN
        record_transition(
            db,
            instrument,
            impl.decision_id,
            STATUS_SUBMITTED,
            STATUS_OPEN,
            actor_id,
            occurred_at=now,
            reason=note,
        )
        return impl
    missing = await missing_evidence(
        db, ctx.actions, await linked_card_ids(db, ctx.kind, ctx.decision)
    )
    if missing:
        raise LifecycleError(
            409,
            "evidence_missing",
            "Cited evidence is no longer on a card linked to the decision; return it",
        )
    attestation = attestation or {}
    examined = _text(attestation.get("examined"))
    demonstrates = _text(attestation.get("demonstrates"))
    if examined is None or demonstrates is None or attestation.get("confirmed") is not True:
        raise LifecycleError(
            422,
            "attestation_required",
            "Say what you examined and why it shows the decision implemented, and confirm it",
        )
    impl.status = STATUS_VERIFIED
    impl.verified_by = actor_id
    impl.verified_at = now
    impl.attestation = {
        "examined": examined,
        "demonstrates": demonstrates,
        "confirmed": True,
        # The evidence as verified. Who verified and when are the verified_by /
        # verified_at columns (remapped by workspace transfer), never this blob.
        "actions": [
            {"action_id": str(a.id), "description": a.description, "evidence": a.evidence_refs}
            for a in ctx.actions
        ],
    }
    record_transition(
        db,
        instrument,
        impl.decision_id,
        STATUS_SUBMITTED,
        STATUS_VERIFIED,
        actor_id,
        occurred_at=now,
        reason=note,
    )
    return impl


# ── GOV-05 classification (D-41.4) ───────────────────────────────────────


def due_in_force(original: date, events: list[Any], boundary: date) -> date:
    """The deadline in force at ``boundary`` (exclusive): the original, replaced
    by each ``due_date_changed`` event recorded before it, in order."""
    due = original
    for e in events:
        if e.event_kind == EVENT_DUE_DATE_CHANGED and e.occurred_at.date() < boundary:
            due = e.due_date
    return due


def outcome_at(
    original: date,
    verified_at: datetime | None,
    status_events: list[Any],
    action_created: list[datetime],
    boundary: date,
) -> str:
    """One eligible decision's GOV-05 outcome, judged at ``boundary`` (exclusive).

    ``verified_on_time`` only when the verification is recorded on or before
    the **original** approved deadline; a later one is ``verified_late``.
    Otherwise the implementation state the history had reached decides:
    awaiting verification, in progress (actions existed) or no plan."""
    if verified_at is not None and verified_at.date() < boundary:
        return "verified_on_time" if verified_at.date() <= original else "verified_late"
    state = None
    for e in status_events:
        if e.event_kind is None and e.occurred_at.date() < boundary:
            state = e.to_status
    if state == STATUS_SUBMITTED:
        return STATE_AWAITING
    if any(c.date() < boundary for c in action_created):
        return STATE_IN_PROGRESS
    return STATE_NO_PLAN
