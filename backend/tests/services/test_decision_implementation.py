"""Decision implementation rules (D-13, D-32, D-41; Batch 3.4). No database needed.

Only an independent verification makes a decision implemented; the verifier
owned, completed and submitted none of it; completion needs a note and
evidence; the original approved deadline never moves and every revision needs
a reason; GOV-05 judges each decision against its original deadline from the
history recorded before the period's end.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.decision_implementation import DecisionImplementation
from app.models.governance_transition import GovernanceTransition
from app.models.todo import Todo
from app.services import decision_implementation as di
from app.services.governance_transitions import LifecycleError

OWNER = uuid.uuid4()
COMPLETER = uuid.uuid4()
SUBMITTER = uuid.uuid4()
VERIFIER = uuid.uuid4()


class _Session:
    """Just enough of AsyncSession for the helpers that only add rows."""

    def __init__(self):
        self.added: list = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def get(self, model, ident):
        return None

    async def commit(self):  # pragma: no cover - would fail the test if reached
        raise AssertionError("a helper must not commit the caller's session")


def _at(y, m, d):
    return datetime(y, m, d, 9, 0, tzinfo=timezone.utc)


def _impl(status="open", **kw) -> DecisionImplementation:
    return DecisionImplementation(
        decision_kind="adr", decision_id=kw.pop("decision_id", uuid.uuid4()), status=status, **kw
    )


def _action(status="done", evidence=None, **kw) -> Todo:
    return Todo(
        id=uuid.uuid4(),
        description="Migrate",
        status=status,
        assigned_to=kw.get("assigned_to", OWNER),
        completed_by=kw.get("completed_by", COMPLETER if status == "done" else None),
        evidence_refs=evidence
        if evidence is not None
        else [{"kind": "reference", "text": "CHG-1"}],
    )


def _ctx(impl, actions, status="signed"):
    decision = SimpleNamespace(id=impl.decision_id, status=status, subject_card_id=None)
    return di.DecisionContext(kind="adr", decision=decision, impl=impl, actions=actions)


def _row(to_status, at, from_status=None, event_kind=None, due=None):
    return GovernanceTransition(
        instrument="adr_impl",
        record_id=uuid.uuid4(),
        from_status=from_status,
        to_status=to_status,
        occurred_at=at,
        event_kind=event_kind,
        due_date=due,
    )


# ── State ────────────────────────────────────────────────────────────────


def test_states_need_verification_to_be_implemented():
    assert di.derive_state(None, []) == di.STATE_NO_PLAN
    assert di.derive_state(_impl(), [_action()]) == di.STATE_IN_PROGRESS
    assert di.derive_state(_impl("submitted"), [_action()]) == di.STATE_AWAITING
    assert di.derive_state(_impl("verified"), [_action()]) == di.STATE_IMPLEMENTED


def test_all_actions_done_is_still_not_implemented():
    assert di.derive_state(_impl(), [_action(), _action()]) == di.STATE_IN_PROGRESS


def test_overdue_only_while_unverified_and_past_the_deadline():
    today = date(2026, 10, 27)
    assert di.is_overdue(_impl(due_date=date(2026, 10, 26)), today)
    assert not di.is_overdue(_impl(due_date=date(2026, 10, 27)), today)
    assert not di.is_overdue(_impl("verified", due_date=date(2026, 1, 1)), today)
    assert not di.is_overdue(_impl(), today)
    assert not di.is_overdue(None, today)


def test_approved_means_signed_adr_or_approved_review():
    assert di.is_approved("adr", SimpleNamespace(status="signed"))
    assert not di.is_approved("adr", SimpleNamespace(status="in_review"))
    assert di.is_approved("arb", SimpleNamespace(status="approved"))
    assert not di.is_approved("arb", SimpleNamespace(status="deferred"))


# ── Independence (D-41.1) ────────────────────────────────────────────────


def test_involved_people_are_owners_completers_and_the_submitter():
    impl = _impl("submitted", submitted_by=SUBMITTER)
    ctx = _ctx(impl, [_action(assigned_to=OWNER, completed_by=COMPLETER)])
    assert di.involved_in_execution(ctx) == {OWNER, COMPLETER, SUBMITTER}


@pytest.mark.parametrize("who", [OWNER, COMPLETER, SUBMITTER])
async def test_self_verification_is_refused(who):
    ctx = _ctx(_impl("submitted", submitted_by=SUBMITTER), [_action()])
    with pytest.raises(LifecycleError) as err:
        await di.verify(_Session(), ctx, "verified", None, _attestation(), who)
    assert (err.value.status, err.value.code) == (403, "self_verification")


async def test_independent_verifier_with_attestation_verifies(monkeypatch):
    monkeypatch.setattr(di, "linked_card_ids", _no_cards)
    db = _Session()
    ctx = _ctx(_impl("submitted", submitted_by=SUBMITTER), [_action()])
    impl = await di.verify(db, ctx, "verified", "ok", _attestation(), VERIFIER)
    assert impl.status == "verified" and impl.verified_by == VERIFIER
    assert impl.attestation["examined"] == "release notes"
    assert impl.attestation["actions"][0]["evidence"] == [{"kind": "reference", "text": "CHG-1"}]
    assert [(r.from_status, r.to_status) for r in db.added] == [("submitted", "verified")]


async def test_a_signatory_who_did_not_execute_may_verify(monkeypatch):
    # Signing the decision is not executing it: only owners, completers and
    # the submitter are excluded (D-41.1 as approved).
    monkeypatch.setattr(di, "linked_card_ids", _no_cards)
    signatory = uuid.uuid4()
    ctx = _ctx(_impl("submitted", submitted_by=SUBMITTER), [_action()])
    ctx.decision.signatories = [{"user_id": str(signatory)}]
    ctx.decision.created_by = signatory
    impl = await di.verify(_Session(), ctx, "verified", None, _attestation(), signatory)
    assert impl.status == "verified"


@pytest.mark.parametrize(
    "attestation",
    [
        None,
        {"examined": "x", "demonstrates": "", "confirmed": True},
        {"examined": "x", "demonstrates": "y"},
    ],
)
async def test_verification_needs_a_confirmed_attestation(monkeypatch, attestation):
    monkeypatch.setattr(di, "linked_card_ids", _no_cards)
    ctx = _ctx(_impl("submitted", submitted_by=SUBMITTER), [_action()])
    with pytest.raises(LifecycleError) as err:
        await di.verify(_Session(), ctx, "verified", None, attestation, VERIFIER)
    assert err.value.code == "attestation_required"


async def test_return_needs_a_note_and_reopens():
    db = _Session()
    ctx = _ctx(_impl("submitted", submitted_by=SUBMITTER), [_action()])
    with pytest.raises(LifecycleError) as err:
        await di.verify(db, ctx, "returned", " ", None, VERIFIER)
    assert err.value.code == "note_required"
    impl = await di.verify(db, ctx, "returned", "evidence unclear", None, VERIFIER)
    assert impl.status == "open"
    assert db.added[-1].reason == "evidence unclear"


async def test_only_a_submitted_implementation_is_verified():
    with pytest.raises(LifecycleError) as err:
        await di.verify(
            _Session(), _ctx(_impl("open"), [_action()]), "verified", None, None, VERIFIER
        )
    assert (err.value.status, err.value.code) == (409, "invalid_state")


async def test_missing_card_evidence_refuses_verification(monkeypatch):
    async def linked(db, kind, decision):
        return {uuid.uuid4()}

    monkeypatch.setattr(di, "linked_card_ids", linked)
    gone = [{"kind": "document", "id": str(uuid.uuid4()), "name": "Runbook"}]
    ctx = _ctx(_impl("submitted", submitted_by=SUBMITTER), [_action(evidence=gone)])
    with pytest.raises(LifecycleError) as err:
        await di.verify(_Session(), ctx, "verified", None, _attestation(), VERIFIER)
    assert (err.value.status, err.value.code) == (409, "evidence_missing")


# ── Submission ───────────────────────────────────────────────────────────


async def test_submission_needs_actions_all_done_with_evidence():
    impl = _impl()
    with pytest.raises(LifecycleError) as err:
        await di.submit(_Session(), _ctx(impl, []), None, SUBMITTER)
    assert err.value.code == "no_actions"
    with pytest.raises(LifecycleError) as err:
        await di.submit(_Session(), _ctx(impl, [_action("open")]), None, SUBMITTER)
    assert err.value.code == "actions_open"
    with pytest.raises(LifecycleError) as err:
        await di.submit(_Session(), _ctx(impl, [_action(evidence=[])]), None, SUBMITTER)
    assert err.value.code == "evidence_required"


async def test_submission_records_who_and_moves_to_submitted():
    db = _Session()
    impl = await di.submit(db, _ctx(_impl(), [_action()]), " done ", SUBMITTER)
    assert impl.status == "submitted" and impl.submitted_by == SUBMITTER
    assert impl.submission_note == "done"
    assert [(r.from_status, r.to_status) for r in db.added] == [("open", "submitted")]


async def test_submission_needs_an_approved_decision():
    with pytest.raises(LifecycleError) as err:
        await di.submit(_Session(), _ctx(_impl(), [_action()], status="draft"), None, SUBMITTER)
    assert err.value.code == "decision_not_approved"


# ── Completion and evidence (D-41.2) ─────────────────────────────────────


async def test_completion_needs_a_note_and_evidence(monkeypatch):
    ctx = _ctx(_impl(), [])
    todo = _action("open")
    with pytest.raises(LifecycleError) as err:
        await di.complete_action(_Session(), None, ctx, todo, note=" ", evidence=[{"k": 1}])
    assert err.value.code == "completion_note_required"
    with pytest.raises(LifecycleError) as err:
        await di.complete_action(_Session(), None, ctx, todo, note="done", evidence=[])
    assert err.value.code == "evidence_required"


async def test_a_verified_implementation_is_frozen():
    ctx = _ctx(_impl("verified"), [])
    with pytest.raises(LifecycleError) as err:
        await di.complete_action(_Session(), None, ctx, _action("open"), note="x", evidence=[{}])
    assert (err.value.status, err.value.code) == (409, "implementation_verified")


async def test_a_reference_is_evidence_for_a_decision_with_no_card():
    refs = await di.resolve_evidence(
        _Session(), [{"kind": "reference", "text": " CHG-42 "}], set(), set()
    )
    assert refs == [{"kind": "reference", "text": "CHG-42"}]


async def test_evidence_is_required_and_bounded():
    with pytest.raises(LifecycleError) as err:
        await di.resolve_evidence(_Session(), [], set(), set())
    assert err.value.code == "evidence_required"
    with pytest.raises(LifecycleError) as err:
        await di.resolve_evidence(
            _Session(), [{"kind": "reference", "text": "x" * 501}], set(), set()
        )
    assert err.value.code == "invalid_evidence_ref"
    many = [{"kind": "reference", "text": f"R{i}"} for i in range(21)]
    with pytest.raises(LifecycleError) as err:
        await di.resolve_evidence(_Session(), many, set(), set())
    assert err.value.code == "too_many_evidence_refs"


async def test_duplicate_references_are_kept_once():
    refs = [{"kind": "reference", "text": "A"}, {"kind": "reference", "text": "A"}]
    assert len(await di.resolve_evidence(_Session(), refs, set(), set())) == 1


async def test_a_document_not_on_a_linked_card_is_refused():
    ref = [{"kind": "document", "id": str(uuid.uuid4())}]
    with pytest.raises(LifecycleError) as err:
        await di.resolve_evidence(_Session(), ref, {uuid.uuid4()}, set())
    assert err.value.code == "invalid_evidence_ref"


# ── Deadline (D-41.3) ────────────────────────────────────────────────────


async def test_first_deadline_after_the_decision_needs_a_reason(monkeypatch):
    impl = _impl()
    monkeypatch.setattr(di, "get_implementation", _returns(impl))
    decision = SimpleNamespace(id=impl.decision_id, status="signed")
    with pytest.raises(LifecycleError) as err:
        await di.change_due_date(_Session(), "adr", decision, date(2027, 1, 1), " ", VERIFIER)
    assert err.value.code == "due_date_reason_required"
    db = _Session()
    await di.change_due_date(db, "adr", decision, date(2027, 1, 1), "legacy plan", VERIFIER)
    assert impl.original_due_date == impl.due_date == date(2027, 1, 1)
    assert impl.due_date_basis == "set_after_decision"
    assert db.added[0].event_kind == "due_date_set"


async def test_a_revision_keeps_the_original_and_appends_an_event(monkeypatch):
    impl = _impl(due_date=date(2027, 1, 1), original_due_date=date(2027, 1, 1))
    monkeypatch.setattr(di, "get_implementation", _returns(impl))
    decision = SimpleNamespace(id=impl.decision_id, status="signed")
    db = _Session()
    await di.change_due_date(db, "adr", decision, date(2027, 3, 1), "supplier delay", VERIFIER)
    assert impl.original_due_date == date(2027, 1, 1)
    assert impl.due_date == date(2027, 3, 1)
    event = db.added[0]
    assert (event.event_kind, event.previous_due_date, event.due_date, event.reason) == (
        "due_date_changed",
        date(2027, 1, 1),
        date(2027, 3, 1),
        "supplier delay",
    )


async def test_an_approved_deadline_cannot_be_removed():
    decision = SimpleNamespace(id=uuid.uuid4(), status="approved")
    with pytest.raises(LifecycleError) as err:
        await di.change_due_date(_Session(), "arb", decision, None, "why", VERIFIER)
    assert err.value.code == "due_date_required"


async def test_signing_approves_the_proposed_deadline(monkeypatch):
    impl = _impl(due_date=date(2027, 6, 30))
    monkeypatch.setattr(di, "get_implementation", _returns(impl))
    db = _Session()
    await di.approve_proposed_due_date(db, "adr", impl.decision_id, VERIFIER)
    assert impl.original_due_date == date(2027, 6, 30)
    assert impl.due_date_basis == "with_decision"
    assert db.added[0].event_kind == "due_date_set"


# ── GOV-05 classification ────────────────────────────────────────────────


def test_on_time_is_judged_against_the_original_deadline():
    original = date(2026, 9, 30)
    end = date(2026, 10, 1)
    assert di.outcome_at(original, _at(2026, 9, 30), [], [], end) == "verified_on_time"
    assert di.outcome_at(original, _at(2026, 10, 2), [], [], date(2026, 12, 1)) == "verified_late"


def test_a_verification_after_the_period_end_does_not_count_for_it():
    original = date(2026, 9, 15)
    end = date(2026, 10, 1)
    created = [_at(2026, 8, 1)]
    assert di.outcome_at(original, _at(2026, 10, 5), [], created, end) == "in_progress"


def test_unverified_outcomes_follow_the_recorded_state():
    original, end = date(2026, 9, 1), date(2026, 10, 1)
    submitted = [_row("submitted", _at(2026, 8, 20), "open")]
    assert (
        di.outcome_at(original, None, submitted, [_at(2026, 8, 1)], end) == "awaiting_verification"
    )
    assert di.outcome_at(original, None, [], [_at(2026, 8, 1)], end) == "in_progress"
    assert di.outcome_at(original, None, [], [], end) == "no_plan"
    # Actions added only after the period are not part of it.
    assert di.outcome_at(original, None, [], [_at(2026, 10, 3)], end) == "no_plan"


def test_a_due_date_event_is_not_a_state_change():
    original, end = date(2026, 9, 1), date(2026, 10, 1)
    rows = [_row("submitted", _at(2026, 8, 20), "submitted", "due_date_changed", date(2026, 12, 1))]
    assert di.outcome_at(original, None, rows, [_at(2026, 8, 1)], end) == "in_progress"


def test_deadline_in_force_takes_revisions_recorded_before_the_boundary():
    original = date(2026, 9, 1)
    rows = [
        _row("open", _at(2026, 8, 1), "open", "due_date_changed", date(2026, 10, 1)),
        _row("open", _at(2026, 11, 1), "open", "due_date_changed", date(2027, 1, 1)),
    ]
    assert di.due_in_force(original, rows, date(2026, 10, 1)) == date(2026, 10, 1)
    assert di.due_in_force(original, rows, date(2027, 1, 1)) == date(2027, 1, 1)
    assert di.due_in_force(original, [], date(2027, 1, 1)) == original


def _attestation():
    return {"examined": "release notes", "demonstrates": "deployed", "confirmed": True}


async def _no_cards(db, kind, decision):
    return set()


def _returns(value):
    async def _get(*args, **kwargs):
        return value

    return _get


# ── Material vs cosmetic action changes (D-41 implementation rule 3) ─────


def test_owner_or_due_date_change_is_material_wording_is_not():
    todo = _action("open")
    todo.due_date = date(2027, 1, 15)
    assert di.is_material_change(todo, {"assigned_to": uuid.uuid4()})
    assert di.is_material_change(todo, {"due_date": "2027-02-01"})
    assert not di.is_material_change(todo, {"description": "Clearer wording"})
    # Re-sending the current values changes nothing.
    assert not di.is_material_change(todo, {"assigned_to": str(OWNER), "due_date": "2027-01-15"})


async def test_wording_change_keeps_a_submission_and_a_verification(monkeypatch):
    calls = []

    async def fake_update(db, actor, todo, changes, **kw):
        calls.append(changes)

    monkeypatch.setattr(di.todo_service, "update_todo", fake_update)
    for status in ("submitted", "verified"):
        db = _Session()
        impl = _impl(status, submitted_by=SUBMITTER)
        await di.update_action(db, None, _ctx(impl, []), _action(), {"description": "Reworded"})
        assert impl.status == status and db.added == []
    assert calls[-1] == {"description": "Reworded"}


async def test_material_change_reopens_a_submission_and_is_refused_once_verified(monkeypatch):
    async def fake_update(db, actor, todo, changes, **kw):
        return None

    monkeypatch.setattr(di.todo_service, "update_todo", fake_update)
    actor = SimpleNamespace(user_id=OWNER)
    db = _Session()
    impl = _impl("submitted", submitted_by=SUBMITTER)
    await di.update_action(db, actor, _ctx(impl, []), _action(), {"assigned_to": uuid.uuid4()})
    assert impl.status == "open"
    assert [(r.from_status, r.to_status, r.reason) for r in db.added] == [
        ("submitted", "open", "action_changed")
    ]
    with pytest.raises(LifecycleError) as err:
        await di.update_action(
            _Session(),
            actor,
            _ctx(_impl("verified"), []),
            _action(),
            {"due_date": date(2030, 1, 1)},
        )
    assert err.value.code == "implementation_verified"
