"""Governance transition writer (D-35, D-34; Batch 3.2). No database needed.

The writer adds rows to the caller's session and never commits; a same-status
write is not a transition; ARB and exception status rules stay what the
endpoints always did, with the history row sharing the stamp's instant.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest

from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.governance_transition import GovernanceTransition
from app.models.tech_standard import StandardException
from app.services import governance_transitions as gt


class _Session:
    """Just enough of AsyncSession: what was added, and proof nothing committed."""

    def __init__(self):
        self.added: list = []

        self.executed: list = []

    def add(self, obj):
        self.added.append(obj)

    async def execute(self, statement):
        self.executed.append(statement)

    async def commit(self):  # pragma: no cover - would fail the test if reached
        raise AssertionError("a helper must not commit the caller's session")


ACTOR = uuid.uuid4()


def test_record_transition_adds_one_row_with_every_field():
    db = _Session()
    rid = uuid.uuid4()
    at = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
    row = gt.record_transition(db, "arb", rid, "scheduled", "approved", ACTOR, occurred_at=at)
    assert db.added == [row]
    assert isinstance(row, GovernanceTransition)
    assert (row.instrument, row.record_id, row.from_status, row.to_status) == (
        "arb",
        rid,
        "scheduled",
        "approved",
    )
    assert row.actor_id == ACTOR
    assert row.occurred_at == at


def test_record_transition_defaults_occurred_at_to_now():
    db = _Session()
    before = datetime.now(timezone.utc)
    row = gt.record_transition(db, "adr", uuid.uuid4(), None, "draft", ACTOR)
    assert row is not None and row.from_status is None
    assert before <= row.occurred_at <= datetime.now(timezone.utc)


def test_same_status_is_not_a_transition():
    db = _Session()
    assert gt.record_transition(db, "adr", uuid.uuid4(), "in_review", "in_review", ACTOR) is None
    assert db.added == []


def test_unknown_instrument_is_refused():
    with pytest.raises(ValueError):
        gt.record_transition(_Session(), "risk", uuid.uuid4(), None, "open", ACTOR)


def test_arb_decision_stamps_reviewer_and_records_with_the_same_instant():
    db = _Session()
    review = ArbReview(id=uuid.uuid4(), title="R", status="scheduled")
    row = gt.set_arb_status(db, review, "approved", ACTOR)
    assert review.status == "approved"
    assert review.reviewer_id == ACTOR
    assert review.decided_at is not None
    assert row is not None and row.occurred_at == review.decided_at
    assert (row.from_status, row.to_status) == ("scheduled", "approved")


def test_arb_deferral_is_stamped_as_before_and_recorded_as_deferred():
    db = _Session()
    review = ArbReview(id=uuid.uuid4(), title="R", status="scheduled")
    row = gt.set_arb_status(db, review, "deferred", ACTOR)
    assert review.decided_at is not None  # unchanged I-12 behaviour
    assert row is not None and row.to_status == "deferred"


def test_arb_back_to_scheduled_does_not_stamp_but_is_recorded():
    db = _Session()
    review = ArbReview(id=uuid.uuid4(), title="R", status="deferred", decided_at=None)
    row = gt.set_arb_status(db, review, "scheduled", None)
    assert review.decided_at is None and review.reviewer_id is None
    assert row is not None and (row.from_status, row.to_status) == ("deferred", "scheduled")


def test_arb_same_status_restamps_as_before_but_records_nothing():
    db = _Session()
    review = ArbReview(id=uuid.uuid4(), title="R", status="approved")
    assert gt.set_arb_status(db, review, "approved", ACTOR) is None
    assert db.added == []
    assert review.decided_at is not None


@pytest.mark.parametrize(("action", "status"), [("approve", "approved"), ("reject", "rejected")])
def test_exception_decision_sets_decided_at_and_records(action, status):
    db = _Session()
    exc = StandardException(id=uuid.uuid4(), standard_id=uuid.uuid4(), status="requested")
    row = gt.decide_exception(db, exc, action, ACTOR)
    assert exc.status == status
    assert exc.approver_id == ACTOR
    assert exc.decided_at is not None
    assert row is not None and row.occurred_at == exc.decided_at
    assert (row.instrument, row.from_status, row.to_status) == ("exception", "requested", status)


def test_exception_redecision_to_the_same_outcome_records_nothing():
    db = _Session()
    exc = StandardException(id=uuid.uuid4(), standard_id=uuid.uuid4(), status="approved")
    assert gt.decide_exception(db, exc, "approve", ACTOR) is None
    assert exc.decided_at is not None


def test_exception_unknown_action_is_refused_before_any_change():
    exc = StandardException(id=uuid.uuid4(), standard_id=uuid.uuid4(), status="requested")
    with pytest.raises(ValueError):
        gt.decide_exception(_Session(), exc, "withdraw", ACTOR)
    assert exc.status == "requested" and exc.decided_at is None


def test_adr_status_change_records_with_a_given_instant():
    db = _Session()
    adr = ArchitectureDecision(id=uuid.uuid4(), reference_number="ADR-1", status="in_review")
    at = datetime(2026, 10, 2, tzinfo=timezone.utc)
    row = gt.set_adr_status(db, adr, "signed", ACTOR, occurred_at=at)
    assert adr.status == "signed"
    assert row is not None
    assert (row.instrument, row.from_status, row.to_status, row.occurred_at) == (
        "adr",
        "in_review",
        "signed",
        at,
    )


def test_history_payload_says_when_nothing_was_recorded():
    assert gt.history_payload([]) == {"recorded": False, "transitions": []}
    one = [{"to_status": "draft"}]
    assert gt.history_payload(one) == {"recorded": True, "transitions": one}


# --------------------------------------------------------------------------- #
# D-39: delay attribution                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("who", ["requester", "external"])
def test_a_delay_outside_governance_needs_a_reason(who):
    with pytest.raises(gt.LifecycleError) as err:
        gt.validate_delay(who, "   ")
    assert (err.value.status, err.value.code) == (422, "delay_reason_required")
    assert gt.validate_delay(who, "  waiting on vendor  ") == (who, "waiting on vendor")


def test_a_governance_delay_may_carry_no_reason():
    assert gt.validate_delay("governance", None) == ("governance", None)
    assert gt.validate_delay("governance", "board quorum") == ("governance", "board quorum")


def test_no_attribution_is_kept_as_none_and_a_bare_reason_is_refused():
    assert gt.validate_delay(None, None) == (None, None)
    assert gt.validate_delay(None, "  ") == (None, None)
    with pytest.raises(gt.LifecycleError) as err:
        gt.validate_delay(None, "why")
    assert err.value.code == "delay_attribution_required"


def test_an_unknown_attribution_is_refused():
    with pytest.raises(gt.LifecycleError) as err:
        gt.validate_delay("board", "x")
    assert (err.value.status, err.value.code) == (422, "invalid_delay_attribution")


def test_arb_deferral_keeps_its_attribution_and_reason():
    db = _Session()
    review = ArbReview(id=uuid.uuid4(), title="R", status="scheduled")
    row = gt.set_arb_status(
        db, review, "deferred", ACTOR, reason="Vendor quote pending", delay_attribution="external"
    )
    assert (row.delay_attribution, row.reason) == ("external", "Vendor quote pending")


def test_an_attribution_on_a_non_waiting_move_is_dropped():
    db = _Session()
    review = ArbReview(id=uuid.uuid4(), title="R", status="deferred")
    row = gt.set_arb_status(db, review, "approved", ACTOR, delay_attribution="requester")
    assert row.delay_attribution is None
    adr = ArchitectureDecision(id=uuid.uuid4(), reference_number="A", status="draft")
    row = gt.set_adr_status(db, adr, "in_review", ACTOR, delay_attribution="requester")
    assert row.delay_attribution is None
    adr2 = ArchitectureDecision(id=uuid.uuid4(), reference_number="B", status="in_review")
    row = gt.set_adr_status(db, adr2, "draft", ACTOR, reason="r", delay_attribution="requester")
    assert (row.delay_attribution, row.reason) == ("requester", "r")


# --------------------------------------------------------------------------- #
# D-40: remediation, verification, withdrawal, deletion                        #
# --------------------------------------------------------------------------- #
REQUESTER = uuid.uuid4()
SUBMITTER = uuid.uuid4()
VERIFIER = uuid.uuid4()


def _exc(status="approved", **kw):
    return StandardException(
        id=uuid.uuid4(), standard_id=uuid.uuid4(), status=status, created_by=REQUESTER, **kw
    )


def test_submission_records_evidence_and_is_not_a_resolution():
    db = _Session()
    exc = _exc()
    row = gt.submit_remediation(db, exc, "  Migrated to Kafka, ticket OPS-12  ", SUBMITTER)
    assert exc.status == "remediation_submitted"
    assert exc.remediation_evidence == "Migrated to Kafka, ticket OPS-12"
    assert exc.remediation_submitted_by == SUBMITTER
    assert exc.remediation_submitted_at == row.occurred_at
    assert exc.remediation_verified_by is None and exc.remediation_verified_at is None
    assert (row.from_status, row.to_status, row.reason) == (
        "approved",
        "remediation_submitted",
        "Migrated to Kafka, ticket OPS-12",
    )


def test_submission_needs_evidence():
    with pytest.raises(gt.LifecycleError) as err:
        gt.submit_remediation(_Session(), _exc(), "   ", SUBMITTER)
    assert (err.value.status, err.value.code) == (422, "evidence_required")


@pytest.mark.parametrize("status", ["requested", "rejected", "withdrawn", "remediated"])
def test_submission_only_from_an_approved_exception(status):
    exc = _exc(status)
    with pytest.raises(gt.LifecycleError) as err:
        gt.submit_remediation(_Session(), exc, "e", SUBMITTER)
    assert (err.value.status, err.value.code) == (409, "invalid_state")
    assert exc.status == status


def test_independent_verification_makes_it_remediated():
    db = _Session()
    exc = _exc("remediation_submitted", remediation_submitted_by=SUBMITTER)
    row = gt.verify_remediation(db, exc, "verified", None, VERIFIER, usage_persists=False)
    assert exc.status == "remediated"
    assert exc.remediation_verified_by == VERIFIER
    assert exc.remediation_verified_at == row.occurred_at
    assert exc.remediation_verification_basis == "rule_check"
    assert (row.from_status, row.to_status) == ("remediation_submitted", "remediated")


def test_verification_is_refused_while_the_violation_persists():
    """I-32: evidence submitted is not the violation resolved."""
    exc = _exc("remediation_submitted", remediation_submitted_by=SUBMITTER)
    db = _Session()
    with pytest.raises(gt.LifecycleError) as err:
        gt.verify_remediation(db, exc, "verified", "Looks done", VERIFIER, usage_persists=True)
    assert (err.value.status, err.value.code) == (409, "violation_persists")
    assert exc.status == "remediation_submitted"
    assert exc.remediation_verified_by is None and exc.remediation_verification_basis is None
    assert db.added == []


FILE_REF = {"kind": "attachment", "id": "f", "fingerprint_of": "content", "sha256": "a"}
LINK_REF = {"kind": "document", "id": "d", "fingerprint_of": "link", "sha256": "b"}
ATTEST = {"examined": "config export", "demonstrates": "no MQ endpoint left", "confirmed": True}


def _verify_unassessable(exc, evidence, attestation=ATTEST, db=None):
    return gt.verify_remediation(
        db or _Session(),
        exc,
        "verified",
        None,
        VERIFIER,
        usage_persists=None,
        evidence=evidence,
        attestation=attestation,
    )


@pytest.mark.parametrize(
    ("evidence", "status", "code"),
    [
        (None, 422, "verifiable_evidence_required"),
        (gt.EvidenceCheck(), 422, "verifiable_evidence_required"),
        (gt.EvidenceCheck(intact=[FILE_REF], changed=[LINK_REF]), 409, "evidence_changed"),
        (gt.EvidenceCheck(intact=[FILE_REF], missing=[LINK_REF]), 409, "evidence_changed"),
        (gt.EvidenceCheck(intact=[LINK_REF]), 422, "evidence_integrity_unavailable"),
    ],
)
def test_unassessable_verification_needs_intact_fingerprinted_evidence(evidence, status, code):
    """I-36: evidence must be cited, unchanged since submission, and include a
    file whose content is fingerprinted; a note or a document's existence alone
    is not enough."""
    exc = _exc("remediation_submitted", remediation_submitted_by=SUBMITTER)
    with pytest.raises(gt.LifecycleError) as err:
        _verify_unassessable(exc, evidence)
    assert (err.value.status, err.value.code) == (status, code)
    assert exc.status == "remediation_submitted" and exc.remediation_attestation is None


@pytest.mark.parametrize(
    "attestation",
    [
        None,
        {**ATTEST, "confirmed": False},
        {**ATTEST, "examined": "  "},
        {**ATTEST, "demonstrates": ""},
    ],
)
def test_unassessable_verification_needs_an_explicit_attestation(attestation):
    exc = _exc("remediation_submitted", remediation_submitted_by=SUBMITTER)
    with pytest.raises(gt.LifecycleError) as err:
        _verify_unassessable(exc, gt.EvidenceCheck(intact=[FILE_REF]), attestation)
    assert (err.value.status, err.value.code) == (422, "attestation_required")
    assert exc.status == "remediation_submitted"


def test_an_attested_verification_keeps_who_when_what_and_the_evidence():
    exc = _exc("remediation_submitted", remediation_submitted_by=SUBMITTER)
    row = _verify_unassessable(exc, gt.EvidenceCheck(intact=[FILE_REF, LINK_REF]))
    assert exc.status == "remediated"
    assert exc.remediation_verification_basis == "attested"
    att = exc.remediation_attestation
    assert (att["examined"], att["demonstrates"], att["confirmed"]) == (
        "config export",
        "no MQ endpoint left",
        True,
    )
    assert exc.remediation_verified_by == VERIFIER
    assert exc.remediation_verified_at == row.occurred_at
    assert "verified_by" not in att  # identity lives in the remapped column
    assert att["evidence"] == [FILE_REF, LINK_REF]


def test_evidence_check_counts_only_unchanged_files_as_content_verified():
    check = gt.EvidenceCheck(intact=[FILE_REF, LINK_REF], changed=[FILE_REF])
    assert (check.cited, check.content_verified) == (3, 1)


def test_a_file_is_fingerprinted_by_content_and_a_document_by_its_link():
    import hashlib
    from types import SimpleNamespace

    f = gt._fingerprint("attachment", SimpleNamespace(data=b"abc", size=3))
    assert f == {
        "fingerprint_of": "content",
        "sha256": hashlib.sha256(b"abc").hexdigest(),
        "size": 3,
    }
    d = gt._fingerprint("document", SimpleNamespace(url="https://x/y"))
    assert d == {"fingerprint_of": "link", "sha256": hashlib.sha256(b"https://x/y").hexdigest()}


def test_an_assessable_pair_needs_no_evidence_reference():
    exc = _exc("remediation_submitted", remediation_submitted_by=SUBMITTER)
    gt.verify_remediation(_Session(), exc, "verified", None, VERIFIER, usage_persists=False)
    assert exc.remediation_verification_basis == "rule_check"
    assert exc.remediation_attestation is None


# --------------------------------------------------------------------------- #
# I-35: expiry changes on a standing approval                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("status", ["approved", "remediation_submitted"])
def test_changing_an_approved_expiry_is_a_recorded_event(status):
    exc = _exc(status, expiry_date=date(2026, 12, 31))
    db = _Session()
    row = gt.change_expiry(db, exc, date(2027, 6, 30), " Vendor delay ", ACTOR)
    assert exc.expiry_date == date(2027, 6, 30)
    assert db.added == [row]
    assert (row.event_kind, row.from_status, row.to_status) == ("expiry_changed", status, status)
    assert (row.previous_expiry_date, row.approved_expiry_date) == (
        date(2026, 12, 31),
        date(2027, 6, 30),
    )
    assert (row.actor_id, row.reason) == (ACTOR, "Vendor delay")
    assert row.occurred_at is not None


def test_an_approved_expiry_change_needs_a_reason_and_changes_nothing_without_one():
    exc = _exc("approved", expiry_date=date(2026, 12, 31))
    db = _Session()
    with pytest.raises(gt.LifecycleError) as err:
        gt.change_expiry(db, exc, date(2027, 6, 30), "  ", ACTOR)
    assert (err.value.status, err.value.code) == (422, "expiry_reason_required")
    assert exc.expiry_date == date(2026, 12, 31) and db.added == []


def test_removing_an_approved_expiry_is_recorded_too():
    exc = _exc("approved", expiry_date=date(2026, 12, 31))
    row = gt.change_expiry(_Session(), exc, None, "Made permanent", ACTOR)
    assert (row.previous_expiry_date, row.approved_expiry_date) == (date(2026, 12, 31), None)


@pytest.mark.parametrize("status", ["requested", "rejected", "remediated", "withdrawn"])
def test_an_expiry_outside_a_standing_approval_is_set_without_an_event(status):
    exc = _exc(status, expiry_date=date(2026, 12, 31))
    db = _Session()
    assert gt.change_expiry(db, exc, date(2027, 1, 31), None, ACTOR) is None
    assert exc.expiry_date == date(2027, 1, 31) and db.added == []


def test_the_same_expiry_again_is_no_event():
    exc = _exc("approved", expiry_date=date(2026, 12, 31))
    db = _Session()
    assert gt.change_expiry(db, exc, date(2026, 12, 31), None, ACTOR) is None
    assert db.added == []


# --------------------------------------------------------------------------- #
# I-37: ADR / ARB delay-reason visibility                                      #
# --------------------------------------------------------------------------- #
def test_adr_delay_reasons_are_for_managers_the_creator_and_signatories():
    signer = uuid.uuid4()
    adr = ArchitectureDecision(
        id=uuid.uuid4(),
        reference_number="ADR-9",
        created_by=REQUESTER,
        signatories=[{"user_id": str(signer), "status": "pending"}],
    )
    assert gt.may_read_delay_reason_adr(adr, REQUESTER, manager=False)
    assert gt.may_read_delay_reason_adr(adr, signer, manager=False)
    assert gt.may_read_delay_reason_adr(adr, VERIFIER, manager=True)
    assert not gt.may_read_delay_reason_adr(adr, VERIFIER, manager=False)
    adr.created_by, adr.signatories = None, None
    assert not gt.may_read_delay_reason_adr(adr, REQUESTER, manager=False)


def test_arb_delay_reasons_are_for_managers_the_creator_and_the_reviewer():
    review = ArbReview(id=uuid.uuid4(), title="R", created_by=REQUESTER, reviewer_id=SUBMITTER)
    assert gt.may_read_delay_reason_arb(review, REQUESTER, manager=False)
    assert gt.may_read_delay_reason_arb(review, SUBMITTER, manager=False)
    assert gt.may_read_delay_reason_arb(review, VERIFIER, manager=True)
    assert not gt.may_read_delay_reason_arb(review, VERIFIER, manager=False)
    review.created_by = review.reviewer_id = None
    assert not gt.may_read_delay_reason_arb(review, VERIFIER, manager=False)


def test_submission_keeps_the_checked_evidence_references():
    exc = _exc()
    refs = [{"kind": "document", "id": str(uuid.uuid4()), "name": "Cutover report"}]
    gt.submit_remediation(_Session(), exc, "Moved", SUBMITTER, evidence_refs=refs)
    assert exc.remediation_evidence_refs == refs
    exc2 = _exc()
    gt.submit_remediation(_Session(), exc2, "Moved", SUBMITTER)
    assert exc2.remediation_evidence_refs is None


def test_returning_ignores_the_usage_check():
    exc = _exc("remediation_submitted", remediation_submitted_by=SUBMITTER)
    row = gt.verify_remediation(
        _Session(), exc, "returned", "Still calls SOAP", VERIFIER, usage_persists=True
    )
    assert exc.status == "approved"
    assert exc.remediation_verification_basis is None
    assert row.to_status == "approved"


@pytest.mark.parametrize("who", [REQUESTER, SUBMITTER])
def test_the_requester_or_submitter_cannot_verify(who):
    exc = _exc("remediation_submitted", remediation_submitted_by=SUBMITTER)
    with pytest.raises(gt.LifecycleError) as err:
        gt.verify_remediation(_Session(), exc, "verified", None, who)
    assert (err.value.status, err.value.code) == (403, "self_verification")
    assert exc.status == "remediation_submitted"


def test_returning_needs_a_note_and_restores_the_approval():
    exc = _exc("remediation_submitted", remediation_submitted_by=SUBMITTER)
    with pytest.raises(gt.LifecycleError) as err:
        gt.verify_remediation(_Session(), exc, "returned", " ", VERIFIER)
    assert err.value.code == "note_required"
    db = _Session()
    row = gt.verify_remediation(db, exc, "returned", "Still calls SOAP", VERIFIER)
    assert exc.status == "approved"
    assert exc.remediation_verified_by is None
    assert (row.to_status, row.reason) == ("approved", "Still calls SOAP")


def test_verification_only_from_a_submission_and_with_a_known_outcome():
    with pytest.raises(gt.LifecycleError) as err:
        gt.verify_remediation(_Session(), _exc("approved"), "verified", None, VERIFIER)
    assert err.value.code == "invalid_state"
    with pytest.raises(gt.LifecycleError) as err:
        gt.verify_remediation(_Session(), _exc("remediation_submitted"), "ok", None, VERIFIER)
    assert err.value.code == "invalid_outcome"


@pytest.mark.parametrize("status", ["requested", "approved", "remediation_submitted"])
def test_withdrawal_needs_a_reason_and_records_who(status):
    exc = _exc(status)
    with pytest.raises(gt.LifecycleError) as err:
        gt.withdraw_exception(_Session(), exc, "", REQUESTER)
    assert err.value.code == "reason_required"
    db = _Session()
    row = gt.withdraw_exception(db, exc, "Project cancelled", REQUESTER)
    assert exc.status == "withdrawn"
    assert (exc.withdrawn_by, exc.withdrawal_reason) == (REQUESTER, "Project cancelled")
    assert exc.withdrawn_at == row.occurred_at
    assert (row.from_status, row.to_status) == (status, "withdrawn")
    # An administrative close, never a verification (I-30).
    assert exc.remediation_verified_by is None and exc.remediation_verified_at is None
    assert exc.remediation_verification_basis is None


def test_an_approval_past_its_expiry_can_still_be_withdrawn():
    exc = _exc("approved", expiry_date=date(2020, 1, 31))
    row = gt.withdraw_exception(_Session(), exc, "Replaced by EX-9", REQUESTER)
    assert (row.from_status, row.to_status) == ("approved", "withdrawn")
    assert exc.expiry_date == date(2020, 1, 31)


@pytest.mark.parametrize("status", ["rejected", "remediated", "withdrawn"])
def test_withdrawal_is_refused_once_terminal(status):
    with pytest.raises(gt.LifecycleError) as err:
        gt.withdraw_exception(_Session(), _exc(status), "r", REQUESTER)
    assert err.value.code == "invalid_state"


def test_may_withdraw_is_the_requester_or_a_manager():
    exc = _exc()
    assert gt.may_withdraw(exc, REQUESTER, is_manager=False)
    assert not gt.may_withdraw(exc, VERIFIER, is_manager=False)
    assert gt.may_withdraw(exc, VERIFIER, is_manager=True)
    orphan = _exc()
    orphan.created_by = None
    assert not gt.may_withdraw(orphan, VERIFIER, is_manager=False)


def test_deletion_appends_a_last_row_and_rewrites_nothing():
    """I-33 (approved with changes): history is immutable; the reason goes to
    the audit record, not onto a row no read scope can protect."""
    with pytest.raises(gt.LifecycleError) as err:
        gt.record_deletion(_Session(), _exc(), None, VERIFIER)
    assert err.value.code == "reason_required"
    db = _Session()
    row, reason = gt.record_deletion(db, _exc("rejected"), " Duplicate of EX-4 ", VERIFIER)
    assert reason == "Duplicate of EX-4"
    assert (row.from_status, row.to_status, row.reason) == ("rejected", "deleted", None)
    assert db.added == [row]
    assert db.executed == []  # no earlier row is touched


@pytest.mark.parametrize(
    ("actor", "privileged", "allowed"),
    [(REQUESTER, False, True), (VERIFIER, False, False), (VERIFIER, True, True)],
)
def test_lifecycle_text_is_for_the_requester_and_the_people_who_act(actor, privileged, allowed):
    assert gt.may_read_lifecycle_text(_exc(), actor, privileged=privileged) is allowed
    orphan = _exc()
    orphan.created_by = None
    assert gt.may_read_lifecycle_text(orphan, VERIFIER, privileged=False) is False


def test_an_approval_records_the_expiry_it_approved():
    """I-31: GOV-04 measures against the original approved expiry."""
    exc = _exc("requested", expiry_date=date(2026, 12, 31))
    row = gt.decide_exception(_Session(), exc, "approve", ACTOR)
    assert row.approved_expiry_date == date(2026, 12, 31)
    exc2 = _exc("rejected", expiry_date=date(2027, 3, 31))
    assert gt.decide_exception(_Session(), exc2, "approve", ACTOR).approved_expiry_date == date(
        2027, 3, 31
    )


def test_a_rejection_records_no_approved_expiry():
    exc = _exc("approved", expiry_date=date(2026, 12, 31))
    row = gt.decide_exception(_Session(), exc, "reject", ACTOR)
    assert row.approved_expiry_date is None


def test_a_returned_remediation_is_not_a_new_approval():
    exc = _exc(
        "remediation_submitted",
        expiry_date=date(2026, 12, 31),
        remediation_submitted_by=SUBMITTER,
    )
    row = gt.verify_remediation(_Session(), exc, "returned", "Incomplete", VERIFIER)
    assert row.approved_expiry_date is None
    assert exc.expiry_date == date(2026, 12, 31)  # never extended (I-29)
