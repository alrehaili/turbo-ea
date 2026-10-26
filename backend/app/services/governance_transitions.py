"""Governance decision-transition history and exception lifecycle (Batch 3.2).

The one writer of ``governance_transitions``: every status change of an ADR,
an ARB review or a technology-standard exception goes through
:func:`record_transition` in the same transaction as the change itself, so a
change and its history row commit or roll back together. Helpers never commit
(the caller owns the session).

History starts the day this ships. Nothing here reconstructs an earlier
transition from ``updated_at``, ``decided_at`` or any other stamp: a record
with no rows is "lifecycle not recorded" (D-34).

Exception remediation and withdrawal (D-40) live here as plain functions, so
their rules carry a mutation score and the routes only gate and serialise:
submission needs evidence; verification is independent of the requester and of
the submitter; withdrawal needs a reason; nothing ever moves an exception to
``remediated`` without a verification step. A delay reason on a move into an
ADR draft or an ARB deferral (D-39) is validated by :func:`validate_delay`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.governance_transition import (
    ATTRIBUTION_EXTERNAL,
    ATTRIBUTION_REQUESTER,
    DELAY_ATTRIBUTIONS,
    INSTRUMENT_ADR,
    INSTRUMENT_ARB,
    INSTRUMENT_EXCEPTION,
    INSTRUMENTS,
    GovernanceTransition,
)
from app.models.tech_standard import StandardException
from app.models.user import User

#: ARB statuses that stamp ``reviewer_id`` / ``decided_at`` (unchanged rule;
#: deferral is stamped too but is never a final decision — I-12, D-35).
ARB_STAMPING_STATUSES = ("approved", "rejected", "deferred")

#: The terminal marker written when an exception is hard-deleted (I-27).
DELETED = "deleted"

#: Where each exception lifecycle step may start (I-23).
REMEDIATION_FROM = ("approved",)
VERIFY_FROM = ("remediation_submitted",)
WITHDRAW_FROM = ("requested", "approved")


class LifecycleError(Exception):
    """A lifecycle step the record's state or the actor does not allow.

    ``status`` is the HTTP status the route answers with; ``code`` is the
    machine-readable reason."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: str | None) -> str | None:
    """The text with surrounding whitespace removed; ``None`` when empty."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def validate_delay(attribution: str | None, reason: str | None) -> tuple[str | None, str | None]:
    """Check a delay attribution and its reason (D-39, I-20).

    Returns the cleaned ``(attribution, reason)``. A delay attributed to the
    requester or an external dependency needs an explicit reason; one
    attributed to governance may carry one. A reason without an attribution
    is refused, since it would read as an attribution nobody made.
    """
    reason = _text(reason)
    if attribution is None:
        if reason is not None:
            raise LifecycleError(422, "delay_attribution_required", "Say who the delay is due to")
        return None, None
    if attribution not in DELAY_ATTRIBUTIONS:
        raise LifecycleError(422, "invalid_delay_attribution", f"Unknown: {attribution!r}")
    if attribution in (ATTRIBUTION_REQUESTER, ATTRIBUTION_EXTERNAL) and reason is None:
        raise LifecycleError(
            422, "delay_reason_required", "A delay outside governance needs a reason"
        )
    return attribution, reason


def record_transition(
    db: AsyncSession,
    instrument: str,
    record_id: uuid.UUID,
    from_status: str | None,
    to_status: str,
    actor_id: uuid.UUID | None,
    *,
    occurred_at: datetime | None = None,
    reason: str | None = None,
    delay_attribution: str | None = None,
) -> GovernanceTransition | None:
    """Add one transition row; a same-status write is not a transition.

    Returns the row added, or ``None`` when ``from_status == to_status``.
    """
    if instrument not in INSTRUMENTS:
        raise ValueError(f"unknown governance instrument: {instrument!r}")
    if from_status == to_status:
        return None
    row = GovernanceTransition(
        instrument=instrument,
        record_id=record_id,
        from_status=from_status,
        to_status=to_status,
        actor_id=actor_id,
        occurred_at=occurred_at or _now(),
        reason=reason,
        delay_attribution=delay_attribution,
    )
    db.add(row)
    return row


def set_adr_status(
    db: AsyncSession,
    adr: ArchitectureDecision,
    new_status: str,
    actor_id: uuid.UUID | None,
    *,
    occurred_at: datetime | None = None,
    reason: str | None = None,
    delay_attribution: str | None = None,
) -> GovernanceTransition | None:
    """Set an ADR's status where a route already did, plus the transition row.

    Re-requesting signatures on a decision already in review is the same
    status, so it records nothing. ``occurred_at`` lets signing share the
    ``signed_at`` instant. A delay attribution is kept only on a move into
    ``draft`` — the one ADR waiting state (D-39).
    """
    old = adr.status
    adr.status = new_status
    if new_status != "draft":
        delay_attribution = None
    return record_transition(
        db,
        INSTRUMENT_ADR,
        adr.id,
        old,
        new_status,
        actor_id,
        occurred_at=occurred_at,
        reason=reason,
        delay_attribution=delay_attribution,
    )


def set_arb_status(
    db: AsyncSession,
    review: ArbReview,
    new_status: str,
    actor_id: uuid.UUID | None,
    *,
    reason: str | None = None,
    delay_attribution: str | None = None,
) -> GovernanceTransition | None:
    """Set an ARB review's status as ``PATCH /arb/{id}`` always has, plus history.

    The reviewer and ``decided_at`` stamp is unchanged (any approve / reject /
    defer write, as before — I-12). The transition row is added only when the
    status actually changes, and carries the same instant as the stamp. A
    delay attribution is kept only on a move into ``deferred`` (D-39).
    """
    now = _now()
    old = review.status
    if new_status in ARB_STAMPING_STATUSES:
        review.reviewer_id = actor_id
        review.decided_at = now
    review.status = new_status
    if new_status != "deferred":
        delay_attribution = None
    return record_transition(
        db,
        INSTRUMENT_ARB,
        review.id,
        old,
        new_status,
        actor_id,
        occurred_at=now,
        reason=reason,
        delay_attribution=delay_attribution,
    )


def decide_exception(
    db: AsyncSession, exc: StandardException, action: str, actor_id: uuid.UUID | None
) -> GovernanceTransition | None:
    """Approve or reject an exception, record ``decided_at`` and the transition.

    The permitted moves are the endpoint's existing ones (any of requested /
    approved / rejected may be decided again). Expiry is derived at read time
    and is never a transition, so an expired waiver is never "resolved".
    """
    if action not in ("approve", "reject"):
        raise ValueError(f"unknown exception decision: {action!r}")
    now = _now()
    old = exc.status
    new = "approved" if action == "approve" else "rejected"
    exc.status = new
    exc.approver_id = actor_id
    exc.decided_at = now
    return record_transition(db, INSTRUMENT_EXCEPTION, exc.id, old, new, actor_id, occurred_at=now)


def _require_state(exc: StandardException, allowed: tuple[str, ...], step: str) -> None:
    if exc.status not in allowed:
        raise LifecycleError(
            409, "invalid_state", f"Cannot {step} an exception that is {exc.status}"
        )


def submit_remediation(
    db: AsyncSession, exc: StandardException, evidence: str | None, actor_id: uuid.UUID
) -> GovernanceTransition | None:
    """Record remediation evidence on an approved exception (D-40, I-23).

    The exception becomes ``remediation_submitted``; it is **not** resolved
    until someone independent verifies it. An expired approval may be
    remediated too — expiry alone never resolves it.
    """
    _require_state(exc, REMEDIATION_FROM, "submit remediation for")
    evidence = _text(evidence)
    if evidence is None:
        raise LifecycleError(422, "evidence_required", "Remediation needs supporting evidence")
    now = _now()
    old = exc.status
    exc.status = "remediation_submitted"
    exc.remediation_evidence = evidence
    exc.remediation_submitted_by = actor_id
    exc.remediation_submitted_at = now
    exc.remediation_verified_by = None
    exc.remediation_verified_at = None
    return record_transition(
        db,
        INSTRUMENT_EXCEPTION,
        exc.id,
        old,
        exc.status,
        actor_id,
        occurred_at=now,
        reason=evidence,
    )


def verify_remediation(
    db: AsyncSession,
    exc: StandardException,
    outcome: str,
    note: str | None,
    actor_id: uuid.UUID,
) -> GovernanceTransition | None:
    """Verify submitted remediation, or return it to ``approved`` (D-40, I-24).

    The verifier must be neither the requester nor the remediation submitter.
    ``verified`` → ``remediated``; ``returned`` → ``approved`` with a note, so
    the waiver stands as it was and the evidence can be resubmitted.
    """
    if outcome not in ("verified", "returned"):
        raise LifecycleError(422, "invalid_outcome", f"Unknown outcome: {outcome!r}")
    _require_state(exc, VERIFY_FROM, "verify")
    if actor_id in {exc.created_by, exc.remediation_submitted_by}:
        raise LifecycleError(
            403,
            "self_verification",
            "Remediation must be verified by someone other than the requester and the submitter",
        )
    note = _text(note)
    now = _now()
    old = exc.status
    if outcome == "verified":
        exc.status = "remediated"
        exc.remediation_verified_by = actor_id
        exc.remediation_verified_at = now
    else:
        if note is None:
            raise LifecycleError(422, "note_required", "Say why the remediation is returned")
        exc.status = "approved"
    return record_transition(
        db, INSTRUMENT_EXCEPTION, exc.id, old, exc.status, actor_id, occurred_at=now, reason=note
    )


def withdraw_exception(
    db: AsyncSession, exc: StandardException, reason: str | None, actor_id: uuid.UUID
) -> GovernanceTransition | None:
    """Withdraw a pending or approved exception with a mandatory reason.

    Withdrawal is an administrative close, never a remediation: a withdrawn
    waiver stops covering the card, so a violation that is still there counts
    again. Who may withdraw is checked by the route (requester or manager).
    """
    _require_state(exc, WITHDRAW_FROM, "withdraw")
    reason = _text(reason)
    if reason is None:
        raise LifecycleError(422, "reason_required", "A withdrawal needs a reason")
    now = _now()
    old = exc.status
    exc.status = "withdrawn"
    exc.withdrawn_by = actor_id
    exc.withdrawn_at = now
    exc.withdrawal_reason = reason
    return record_transition(
        db, INSTRUMENT_EXCEPTION, exc.id, old, exc.status, actor_id, occurred_at=now, reason=reason
    )


def may_withdraw(exc: StandardException, actor_id: uuid.UUID, *, is_manager: bool) -> bool:
    """The original requester, or an authorized manager (D-40)."""
    return is_manager or (exc.created_by is not None and exc.created_by == actor_id)


def record_deletion(
    db: AsyncSession, exc: StandardException, reason: str | None, actor_id: uuid.UUID
) -> GovernanceTransition | None:
    """The last history row of a hard-deleted exception (I-27).

    Hard deletion corrects a record created in error; it needs a reason, and
    the row outlives the record, so the history still says what existed."""
    reason = _text(reason)
    if reason is None:
        raise LifecycleError(422, "reason_required", "A permanent deletion needs a reason")
    return record_transition(
        db, INSTRUMENT_EXCEPTION, exc.id, exc.status, DELETED, actor_id, reason=reason
    )


async def transition_history(db: AsyncSession, instrument: str, record_id: uuid.UUID) -> list[dict]:
    """A record's transitions, oldest first, actor as ``{id, display_name}``.

    The caller has already gated the record itself (permission and read scope).
    """
    rows = await db.execute(
        select(GovernanceTransition, User.display_name)
        .outerjoin(User, User.id == GovernanceTransition.actor_id)
        .where(
            GovernanceTransition.instrument == instrument,
            GovernanceTransition.record_id == record_id,
        )
        .order_by(GovernanceTransition.occurred_at, GovernanceTransition.created_at)
    )
    return [
        {
            "from_status": t.from_status,
            "to_status": t.to_status,
            "occurred_at": t.occurred_at.isoformat() if t.occurred_at else None,
            "actor": (
                {"id": str(t.actor_id), "display_name": name} if t.actor_id is not None else None
            ),
            "reason": t.reason,
            "delay_attribution": t.delay_attribution,
        }
        for t, name in rows.all()
    ]


def history_payload(transitions: list[dict]) -> dict:
    """The response shape: an empty history says so instead of looking blank."""
    return {"recorded": bool(transitions), "transitions": transitions}
