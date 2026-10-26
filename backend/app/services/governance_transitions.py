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

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.document import Document
from app.models.file_attachment import FileAttachment
from app.models.governance_transition import (
    ATTRIBUTION_EXTERNAL,
    ATTRIBUTION_REQUESTER,
    DELAY_ATTRIBUTIONS,
    EVENT_EXPIRY_CHANGED,
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

#: Where each exception lifecycle step may start (I-23, I-30). Withdrawal is
#: open from every non-terminal state, an approval past its expiry included
#: (expiry is derived, never stored, so it never blocks a withdrawal).
REMEDIATION_FROM = ("approved",)
VERIFY_FROM = ("remediation_submitted",)
WITHDRAW_FROM = ("requested", "approved", "remediation_submitted")
#: States in which the expiry date is that of a standing approval, so changing
#: it is a recorded lifecycle event (I-35).
EXPIRY_EVENT_STATES = ("approved", "remediation_submitted")
#: Moves that are an approval decision, so they carry the approved expiry (I-31).
#: ``remediation_submitted -> approved`` (a returned remediation) is not one.
APPROVAL_FROM = (None, "requested", "rejected")


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
    approved_expiry_date: date | None = None,
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
        approved_expiry_date=approved_expiry_date,
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

    An approval records the expiry date it approved on its transition (I-31):
    GOV-04 measures against that original date, so a later edit of
    ``expiry_date`` never moves the deadline of a recorded approval.
    """
    if action not in ("approve", "reject"):
        raise ValueError(f"unknown exception decision: {action!r}")
    now = _now()
    old = exc.status
    new = "approved" if action == "approve" else "rejected"
    exc.status = new
    exc.approver_id = actor_id
    exc.decided_at = now
    approved_expiry = exc.expiry_date if new == "approved" and old in APPROVAL_FROM else None
    return record_transition(
        db,
        INSTRUMENT_EXCEPTION,
        exc.id,
        old,
        new,
        actor_id,
        occurred_at=now,
        approved_expiry_date=approved_expiry,
    )


def _require_state(exc: StandardException, allowed: tuple[str, ...], step: str) -> None:
    if exc.status not in allowed:
        raise LifecycleError(
            409, "invalid_state", f"Cannot {step} an exception that is {exc.status}"
        )


#: The existing card evidence a remediation may reference (I-32).
EVIDENCE_MODELS = {"document": Document, "attachment": FileAttachment}
MAX_EVIDENCE_REFS = 20


def _fingerprint(kind: str, row) -> dict:
    """A stable fingerprint of one cited evidence item (I-36).

    A file attachment is fingerprinted by its **content** (SHA-256 of the bytes
    and their size), so a replaced file is detected; nothing is copied. A
    document is a link whose target lives elsewhere: only the link itself can be
    fingerprinted, never what it points to."""
    if kind == "attachment":
        return {
            "fingerprint_of": "content",
            "sha256": hashlib.sha256(row.data or b"").hexdigest(),
            "size": row.size,
        }
    return {
        "fingerprint_of": "link",
        "sha256": hashlib.sha256((row.url or "").encode()).hexdigest(),
    }


async def resolve_evidence_refs(
    db: AsyncSession, exc: StandardException, refs: list[dict] | None
) -> list[dict]:
    """Check remediation evidence references and fingerprint them (I-32, I-36).

    Each reference names a document or a file attachment **of the exception's
    own card** — the card evidence mechanisms that already exist; an unknown
    kind or id, or evidence on another card, is refused (422
    ``invalid_evidence_ref``). Evidence is never refused for being older than
    the approval. Each kept reference carries its name and fingerprint at
    submission. Duplicates are kept once, in the order given.
    """
    resolved: list[dict] = []
    seen: set[tuple[str, uuid.UUID]] = set()
    for ref in refs or []:
        model = EVIDENCE_MODELS.get(ref.get("kind"))
        try:
            ref_id = uuid.UUID(str(ref.get("id")))
        except ValueError:
            model = None
        row = await db.get(model, ref_id) if model is not None else None
        if row is None or exc.card_id is None or row.card_id != exc.card_id:
            raise LifecycleError(
                422,
                "invalid_evidence_ref",
                "Evidence must be a document or file attached to the exception's card",
            )
        if (ref["kind"], ref_id) in seen:
            continue
        seen.add((ref["kind"], ref_id))
        resolved.append(
            {
                "kind": ref["kind"],
                "id": str(ref_id),
                "name": row.name,
                **_fingerprint(ref["kind"], row),
            }
        )
    if len(resolved) > MAX_EVIDENCE_REFS:
        raise LifecycleError(422, "too_many_evidence_refs", "Reference at most 20 items")
    return resolved


@dataclass
class EvidenceCheck:
    """The submission's evidence as it stands at verification (I-36)."""

    intact: list[dict] = field(default_factory=list)
    changed: list[dict] = field(default_factory=list)
    missing: list[dict] = field(default_factory=list)

    @property
    def cited(self) -> int:
        return len(self.intact) + len(self.changed) + len(self.missing)

    @property
    def content_verified(self) -> int:
        """Cited files whose content is unchanged since submission."""
        return sum(1 for r in self.intact if r.get("fingerprint_of") == "content")


async def check_evidence(db: AsyncSession, exc: StandardException) -> EvidenceCheck:
    """Re-fingerprint every cited item and compare it with the submission.

    An item gone from the card is ``missing``; one whose content (a file) or
    link (a document) differs from its submission fingerprint is ``changed``;
    a reference recorded before fingerprints were kept has nothing to compare
    with and is ``changed`` too — its integrity cannot be established."""
    check = EvidenceCheck()
    for ref in exc.remediation_evidence_refs or []:
        model = EVIDENCE_MODELS.get(ref.get("kind"))
        row = await db.get(model, uuid.UUID(ref["id"])) if model is not None else None
        if row is None or row.card_id != exc.card_id:
            check.missing.append(ref)
            continue
        now = _fingerprint(ref["kind"], row)
        same = ref.get("sha256") is not None and now["sha256"] == ref.get("sha256")
        if ref["kind"] == "attachment":
            same = same and now["size"] == ref.get("size")
        (check.intact if same else check.changed).append(ref)
    return check


def submit_remediation(
    db: AsyncSession,
    exc: StandardException,
    evidence: str | None,
    actor_id: uuid.UUID,
    *,
    evidence_refs: list[dict] | None = None,
) -> GovernanceTransition | None:
    """Record remediation evidence on an approved exception (D-40, I-23).

    The exception becomes ``remediation_submitted``; it is **not** resolved
    until someone independent verifies it. An expired approval may be
    remediated too — expiry alone never resolves it. While the submission
    awaits verification the waiver keeps covering the card until its expiry
    date (``WAIVER_ACTIVE_STATUSES``); the expiry is never extended (I-29).
    ``evidence_refs`` are the references :func:`resolve_evidence_refs` checked.
    """
    _require_state(exc, REMEDIATION_FROM, "submit remediation for")
    evidence = _text(evidence)
    if evidence is None:
        raise LifecycleError(422, "evidence_required", "Remediation needs supporting evidence")
    now = _now()
    old = exc.status
    exc.status = "remediation_submitted"
    exc.remediation_evidence = evidence
    exc.remediation_evidence_refs = list(evidence_refs) if evidence_refs else None
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
    *,
    usage_persists: bool | None = None,
    evidence: EvidenceCheck | None = None,
    attestation: dict | None = None,
) -> GovernanceTransition | None:
    """Verify submitted remediation, or return it to ``approved`` (D-40, I-24).

    The verifier must be neither the requester nor the remediation submitter.
    ``verified`` → ``remediated``; ``returned`` → ``approved`` with a note, so
    the waiver stands as it was and the evidence can be resubmitted.

    Submitted evidence is never itself the proof (I-32). ``usage_persists`` is
    the standards scan's answer for this exception's card and standard
    (:func:`app.services.tech_standards_scan.standard_usage_persists`):
    ``True`` — the card still uses the standard, so ``verified`` is refused
    (409 ``violation_persists``); ``False`` — the scan confirms the usage is
    gone (basis ``rule_check``); ``None`` — the scan cannot assess the pair, so
    the verification rests on evidence whose integrity is established (I-32,
    I-36): the submission must cite evidence from the card (422
    ``verifiable_evidence_required``); every cited item must be unchanged since
    submission (``evidence``, from :func:`check_evidence`; 409
    ``evidence_changed`` — return it and resubmit); at least one must be a
    file, whose content can be fingerprinted (a link's target cannot; 422
    ``evidence_integrity_unavailable``); and the verifier must attest what was
    examined and why it demonstrates remediation, and confirm it (422
    ``attestation_required``). The attestation, the confirmed fingerprints and
    the verifier are kept on the exception (basis ``attested``). The verifier
    is independent and authorized in every case.
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
        if usage_persists:
            raise LifecycleError(
                409,
                "violation_persists",
                "The standards check still finds this card using the standard",
            )
        attested = None
        if usage_persists is None:
            attested = _attest(evidence or EvidenceCheck(), attestation)
        exc.status = "remediated"
        exc.remediation_verified_by = actor_id
        exc.remediation_verified_at = now
        exc.remediation_verification_basis = "attested" if usage_persists is None else "rule_check"
        exc.remediation_attestation = attested
    else:
        if note is None:
            raise LifecycleError(422, "note_required", "Say why the remediation is returned")
        exc.status = "approved"
    return record_transition(
        db, INSTRUMENT_EXCEPTION, exc.id, old, exc.status, actor_id, occurred_at=now, reason=note
    )


def _attest(evidence: EvidenceCheck, attestation: dict | None) -> dict:
    """The attestation record for an unassessable verification, or the refusal."""
    if evidence.cited == 0:
        raise LifecycleError(
            422,
            "verifiable_evidence_required",
            "This pair cannot be checked automatically; the remediation must cite a document "
            "or file on the card",
        )
    if evidence.changed or evidence.missing:
        raise LifecycleError(
            409,
            "evidence_changed",
            "Cited evidence changed or was removed after submission; return the remediation "
            "so it can be resubmitted",
        )
    if evidence.content_verified == 0:
        raise LifecycleError(
            422,
            "evidence_integrity_unavailable",
            "A link's content cannot be fingerprinted; cite at least one file on the card",
        )
    attestation = attestation or {}
    examined = _text(attestation.get("examined"))
    demonstrates = _text(attestation.get("demonstrates"))
    if examined is None or demonstrates is None or attestation.get("confirmed") is not True:
        raise LifecycleError(
            422,
            "attestation_required",
            "Say what you examined and why it shows the violation is resolved, and confirm it",
        )
    return {
        "examined": examined,
        "demonstrates": demonstrates,
        "confirmed": True,
        # Who verified and when are the remediation_verified_by / _at columns,
        # which workspace transfer remaps; a user id is never kept in this blob.
        "evidence": evidence.intact,
    }


def change_expiry(
    db: AsyncSession,
    exc: StandardException,
    new_expiry: date | None,
    reason: str | None,
    actor_id: uuid.UUID,
) -> GovernanceTransition | None:
    """Change an exception's expiry date; on a standing approval, an event (I-35).

    While the exception is ``approved`` or ``remediation_submitted`` its expiry
    is the one an approval granted, so a change is an auditable lifecycle
    event: it needs a reason (422 ``expiry_reason_required``) and appends an
    ``expiry_changed`` row keeping the status, with the previous and the new
    expiry, the actor and the time. Earlier rows are never touched, so the
    expiry each approval granted stays on record. In any other state the date
    is not (or no longer) an approved one and is set as before, with no event.
    The same date again changes nothing.
    """
    old = exc.expiry_date
    if new_expiry == old:
        return None
    if exc.status not in EXPIRY_EVENT_STATES:
        exc.expiry_date = new_expiry
        return None
    reason = _text(reason)
    if reason is None:
        raise LifecycleError(
            422, "expiry_reason_required", "Say why the approved expiry date changes"
        )
    exc.expiry_date = new_expiry
    row = GovernanceTransition(
        instrument=INSTRUMENT_EXCEPTION,
        record_id=exc.id,
        from_status=exc.status,
        to_status=exc.status,
        actor_id=actor_id,
        occurred_at=_now(),
        reason=reason,
        event_kind=EVENT_EXPIRY_CHANGED,
        previous_expiry_date=old,
        approved_expiry_date=new_expiry,
    )
    db.add(row)
    return row


def withdraw_exception(
    db: AsyncSession, exc: StandardException, reason: str | None, actor_id: uuid.UUID
) -> GovernanceTransition | None:
    """Withdraw a non-terminal exception with a mandatory reason (D-40, I-30).

    Open from ``requested``, ``approved`` (past its expiry too) and
    ``remediation_submitted``; refused once ``rejected``, ``remediated`` or
    ``withdrawn``. Withdrawal is an administrative close, never a remediation:
    no verification is recorded, a withdrawn waiver stops covering the card,
    and a violation that is still there counts again. Who may withdraw is
    checked by the route (requester or manager).
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
) -> tuple[GovernanceTransition | None, str]:
    """The last history row of a hard-deleted exception (I-27, I-33).

    Hard deletion corrects a record created in error; it needs a reason. The
    history is immutable: every earlier row is kept exactly as written and a
    final ``deleted`` row is appended, so the history still says what existed
    and how it moved. The deletion reason is held in the admin audit record,
    not on the row, because once the record is gone nothing can apply its
    card's read scope; no endpoint serves a deleted record's history.
    Returns the row and the cleaned reason."""
    reason = _text(reason)
    if reason is None:
        raise LifecycleError(422, "reason_required", "A permanent deletion needs a reason")
    row = record_transition(db, INSTRUMENT_EXCEPTION, exc.id, exc.status, DELETED, actor_id)
    return row, reason


def may_read_lifecycle_text(
    exc: StandardException, actor_id: uuid.UUID, *, privileged: bool
) -> bool:
    """Who may read an exception's lifecycle free text (I-33).

    Remediation evidence, return notes and withdrawal reasons can be
    confidential, so ordinary readers (``tech_standards.view`` only) see the
    status moves, times and actors without them. The requester and the people
    who act on exceptions (``privileged``: ``tech_standards.manage`` or
    ``tech_standards.approve_exception``) see the text."""
    return privileged or (exc.created_by is not None and exc.created_by == actor_id)


async def transition_history(
    db: AsyncSession, instrument: str, record_id: uuid.UUID, *, withhold_reason: bool = False
) -> list[dict]:
    """A record's transitions, oldest first, actor as ``{id, display_name}``.

    The caller has already gated the record itself (permission and read scope).
    ``withhold_reason`` leaves the free-text ``reason`` out (``reason_withheld``
    says one exists), never the row itself (I-33).
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
            "reason": None if withhold_reason else t.reason,
            "reason_withheld": withhold_reason and t.reason is not None,
            "delay_attribution": t.delay_attribution,
            # An expiry change keeps the status and says what changed (I-35).
            "event_kind": t.event_kind,
            "previous_expiry_date": _date(t.previous_expiry_date),
            "expiry_date": _date(t.approved_expiry_date),
        }
        for t, name in rows.all()
    ]


def _date(value: date | None) -> str | None:
    return value.isoformat() if value else None


def may_read_delay_reason_adr(
    adr: ArchitectureDecision, actor_id: uuid.UUID, *, manager: bool
) -> bool:
    """Who may read an ADR's free-text delay reasons (I-37): ``adr.manage``
    holders, its creator and its signatories. Others see the attribution,
    the times and that a reason exists."""
    if manager or (adr.created_by is not None and adr.created_by == actor_id):
        return True
    return any(s.get("user_id") == str(actor_id) for s in adr.signatories or [])


def may_read_delay_reason_arb(review: ArbReview, actor_id: uuid.UUID, *, manager: bool) -> bool:
    """Who may read an ARB review's free-text delay reasons (I-37): ``arb.manage``
    holders, its creator and its assigned reviewer."""
    return manager or actor_id in {review.created_by, review.reviewer_id} - {None}


def history_payload(transitions: list[dict]) -> dict:
    """The response shape: an empty history says so instead of looking blank."""
    return {"recorded": bool(transitions), "transitions": transitions}
