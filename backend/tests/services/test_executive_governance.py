"""EA governance effectiveness service (Batch 3.1, DECISION_LOG §3.1).

Activity dating (ARB by latest decision date, deferred apart), compliance and
assessment coverage as two separate figures, expired-waiver-is-a-violation, and
the Unavailable cases. Three classes are kept apart and nothing without a
defensible calculation carries a value.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.governance_transition import GovernanceTransition
from app.models.tech_standard import StandardException, TechStandard
from app.services.card_read_scope import CardReadScope
from app.services.executive import governance as gov
from app.services.executive import periods
from tests.conftest import create_card, create_relation, create_user

START_MONTH = 1


def _period():
    return periods.parse(None, START_MONTH, date.today())


async def _standard(db, *, category_card_id, status="prohibited", name="Legacy SOAP"):
    std = TechStandard(
        name=name, category="integration", status=status, tech_category_id=category_card_id
    )
    db.add(std)
    await db.flush()
    return std


@pytest.fixture
async def landscape(db):
    admin = await create_user(db, email="g@example.com", role="admin")
    cat = await create_card(db, card_type="TechCategory", name="Messaging", user_id=admin.id)
    itc = await create_card(db, card_type="ITComponent", name="OldMQ", user_id=admin.id)
    app = await create_card(db, card_type="Application", name="Billing", user_id=admin.id)
    await create_relation(db, type_key="relITCToTechCat", source_id=itc.id, target_id=cat.id)
    await create_relation(db, type_key="relAppToITC", source_id=app.id, target_id=itc.id)
    std = await _standard(db, category_card_id=cat.id)
    return {"admin": admin, "cat": cat, "itc": itc, "app": app, "std": std}


async def test_activity_counts_decisions_and_keeps_deferred_apart(db):
    now = datetime.now(timezone.utc)
    last_year = now.replace(year=now.year - 1)
    db.add_all(
        [
            ArchitectureDecision(
                reference_number="ADR-1", title="In period", status="signed", signed_at=now
            ),
            ArchitectureDecision(
                reference_number="ADR-2", title="Earlier", status="signed", signed_at=last_year
            ),
            ArchitectureDecision(reference_number="ADR-3", title="Draft", status="draft"),
            ArbReview(title="Approved", status="approved", decided_at=now),
            ArbReview(title="Rejected", status="rejected", decided_at=now),
            ArbReview(title="Deferred", status="deferred", decided_at=now),
            ArbReview(title="Scheduled", status="scheduled"),  # no decided_at → not counted
        ]
    )
    await db.flush()
    summary = await gov.governance_summary(
        db, CardReadScope.everything(), _period(), gov03_link=None
    )
    activity = summary["activity"]
    assert activity["adrs_signed"] == 1
    assert activity["arb"]["approved"] == 1
    assert activity["arb"]["rejected"] == 1
    # Deferred is counted on its own and never folded into the decisions.
    assert activity["arb"]["deferred"] == 1
    assert activity["arb"]["dating"] == "latest_decision"


async def test_exceptions_are_bucketed_by_current_state(db, landscape):
    today = date.today()
    db.add_all(
        [
            StandardException(
                standard_id=landscape["std"].id, card_id=landscape["app"].id, status="requested"
            ),
            StandardException(
                standard_id=landscape["std"].id,
                card_id=landscape["itc"].id,
                status="approved",
                expiry_date=today + timedelta(days=30),
            ),
            StandardException(
                standard_id=landscape["std"].id,
                card_id=landscape["cat"].id,
                status="approved",
                expiry_date=today - timedelta(days=1),
            ),
        ]
    )
    await db.flush()
    summary = await gov.governance_summary(
        db, CardReadScope.everything(), _period(), gov03_link=None
    )
    exc = summary["activity"]["exceptions"]
    assert exc["requested"] == 1
    assert exc["approved_active"] == 1
    assert exc["expired"] == 1
    assert exc["rejected"] == 0
    assert exc["temporal"] == "current_state"


async def test_compliance_and_coverage_are_two_distinct_figures(db, landscape):
    # One more Application that reaches no governed category: assessed, no, but
    # it is still in the coverage denominator.
    await create_card(db, card_type="Application", name="Standalone", user_id=landscape["admin"].id)
    summary = await gov.governance_summary(
        db, CardReadScope.everything(), _period(), gov03_link=None
    )
    eff = summary["effectiveness"]
    assert eff["compliance"]["status"] == "ok"
    assert eff["compliance"]["value"] == 0.0  # both assessed cards violate
    cov = eff["coverage"]
    assert cov["status"] == "ok"
    assert cov["assessed"] == 2
    assert cov["population"] == 3
    # Coverage is its own figure, not the compliance value.
    assert cov["percentage"] != eff["compliance"]["value"]


async def test_expired_waiver_is_still_a_violation(db, landscape):
    db.add(
        StandardException(
            standard_id=landscape["std"].id,
            card_id=landscape["itc"].id,
            status="approved",
            expiry_date=date.today() - timedelta(days=1),
        )
    )
    await db.flush()
    summary = await gov.governance_summary(
        db, CardReadScope.everything(), _period(), gov03_link=None
    )
    # The expired waiver does not make the component compliant.
    assert summary["effectiveness"]["compliance"]["value"] == 0.0


async def test_active_waiver_makes_the_card_compliant(db, landscape):
    db.add(
        StandardException(
            standard_id=landscape["std"].id,
            card_id=landscape["itc"].id,
            status="approved",
            expiry_date=date.today() + timedelta(days=30),
        )
    )
    await db.flush()
    summary = await gov.governance_summary(
        db, CardReadScope.everything(), _period(), gov03_link=None
    )
    eff = summary["effectiveness"]
    # OldMQ is waived; only Billing (reaching the category through it) violates.
    assert eff["compliance"]["details"]["compliant"] == 1
    assert eff["compliance"]["value"] == 50.0


async def test_unavailable_when_no_standard_governs_a_category(db):
    summary = await gov.governance_summary(
        db, CardReadScope.everything(), _period(), gov03_link=None
    )
    eff = summary["effectiveness"]
    assert eff["compliance"]["status"] == "not_available"
    assert eff["compliance"]["reason"]["code"] == "no_governed_category"
    assert eff["coverage"]["status"] == "not_available"


async def test_unavailable_when_nothing_falls_under_a_governed_standard(db):
    admin = await create_user(db, email="h@example.com", role="admin")
    cat = await create_card(db, card_type="TechCategory", name="Orphan", user_id=admin.id)
    await _standard(db, category_card_id=cat.id)  # governs a category nothing links to
    summary = await gov.governance_summary(
        db, CardReadScope.everything(), _period(), gov03_link=None
    )
    assert summary["effectiveness"]["compliance"]["reason"]["code"] == "no_assessed_population"


async def test_later_batch_indicators_are_not_available_with_reasons(db):
    summary = await gov.governance_summary(
        db, CardReadScope.everything(), _period(), gov03_link=None
    )
    eff, impact = summary["effectiveness"], summary["impact"]
    assert eff["decision_implementation"]["status"] == "not_available"
    assert eff["decision_implementation"]["reason"]["decisions"] == ["D-41"]
    # Nothing due: GOV-04 is Not Available with its reason, never zero.
    assert eff["exception_resolution"]["status"] == "not_available"
    assert eff["exception_resolution"]["reason"] == {"code": "no_eligible_exceptions"}
    # GOV-07: elapsed and governance-controlled time side by side; working days later.
    turnaround = eff["turnaround"]
    assert turnaround["measure"] == "elapsed"
    assert turnaround["processing_time"]["measure"] == "governance_controlled"
    # No confirmed business calendar for the period: Not Available, naming the years (D-38).
    assert turnaround["working_days"]["status"] == "not_available"
    assert turnaround["working_days"]["reason"]["code"] == "calendar_not_confirmed"
    assert turnaround["working_days"]["reason"]["fiscal_years"]
    for block in (
        impact["architecture_risks"],
        impact["governed_delivery"],
        impact["business_value"],
    ):
        assert block["status"] == "not_available"
        assert block["reason"]


# --------------------------------------------------------------------------- #
# GOV-07 elapsed time (Batch 3.2, D-35)                                        #
# --------------------------------------------------------------------------- #
def _t(**delta):
    return datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc) + timedelta(**delta)


def test_elapsed_days_is_calendar_days_and_refuses_an_impossible_order():
    assert gov.elapsed_days(_t(), _t(days=2, hours=12)) == 2.5
    assert gov.elapsed_days(_t(), _t()) == 0
    assert gov.elapsed_days(_t(days=1), _t()) is None
    assert gov.elapsed_days(None, _t()) is None
    assert gov.elapsed_days(_t(), None) is None


def test_elapsed_figure_reports_median_and_slowest():
    fig = gov.elapsed_figure([1.0, 4.0, 10.04], 2, "basis")
    assert fig == {
        "status": "ok",
        "decisions": 3,
        "median_days": 4.0,
        "max_days": 10.0,
        "not_recorded": 2,
        "basis": "basis",
    }
    assert gov.elapsed_figure([2.0, 3.0], 0, "b")["median_days"] == 2.5


def test_elapsed_figure_without_samples_is_not_available_never_zero():
    fig = gov.elapsed_figure([], 4, "b")
    assert fig["status"] == "not_available"
    assert fig["reason"] == {"code": "no_recorded_decisions"}
    assert fig["not_recorded"] == 4
    assert "median_days" not in fig


def _arb(db, title, *, created, status="scheduled", decided_at=None):
    r = ArbReview(title=title, status=status, created_at=created, decided_at=decided_at)
    db.add(r)
    return r


def _move(db, instrument, record_id, frm, to, at, approved_expiry=None):
    db.add(
        GovernanceTransition(
            instrument=instrument,
            record_id=record_id,
            from_status=frm,
            to_status=to,
            occurred_at=at,
            approved_expiry_date=approved_expiry,
        )
    )


def _fy_period():
    """The current fiscal year (calendar year here). The GOV-07 / GOV-04 cases
    date records some days back, which must stay inside the period."""
    today = date.today()
    if today.timetuple().tm_yday <= 15:
        pytest.skip("first days of the fiscal year: dated records would fall outside it")
    return periods.parse(f"FY{today.year}", START_MONTH, today)


async def _turnaround(db):
    return (
        await gov.governance_summary(db, CardReadScope.everything(), _fy_period(), gov03_link=None)
    )["effectiveness"]["turnaround"]


async def test_adr_elapsed_runs_from_creation_to_signature(db):
    now = datetime.now(timezone.utc)
    db.add_all(
        [
            ArchitectureDecision(
                reference_number="ADR-10",
                title="Four days",
                status="signed",
                created_at=now - timedelta(days=4),
                signed_at=now,
            ),
            ArchitectureDecision(
                reference_number="ADR-11",
                title="Out of period",
                status="signed",
                created_at=now - timedelta(days=450),
                signed_at=now - timedelta(days=400),
            ),
        ]
    )
    await db.flush()
    adr = (await _turnaround(db))["instruments"]["adr"]
    assert adr["status"] == "ok"
    assert adr["decisions"] == 1
    assert adr["median_days"] == 4.0
    assert adr["basis"] == "created_to_signed"


async def test_arb_deferral_is_never_the_decision_and_the_first_decision_counts(db):
    now = datetime.now(timezone.utc)
    r = _arb(db, "Deferred then approved", created=now - timedelta(days=10), status="rejected")
    await db.flush()
    _move(db, "arb", r.id, None, "scheduled", now - timedelta(days=10))
    _move(db, "arb", r.id, "scheduled", "deferred", now - timedelta(days=8))
    _move(db, "arb", r.id, "deferred", "approved", now - timedelta(days=4))
    # A later change of mind does not re-time the first decision.
    _move(db, "arb", r.id, "approved", "rejected", now - timedelta(days=1))
    await db.flush()
    arb = (await _turnaround(db))["instruments"]["arb"]
    assert arb["decisions"] == 1
    assert arb["median_days"] == 6.0
    assert arb["not_recorded"] == 0


async def test_arb_only_deferred_has_no_decision_to_time(db):
    now = datetime.now(timezone.utc)
    r = _arb(db, "Only deferred", created=now - timedelta(days=3), status="deferred")
    await db.flush()
    _move(db, "arb", r.id, "scheduled", "deferred", now)
    await db.flush()
    arb = (await _turnaround(db))["instruments"]["arb"]
    assert arb["status"] == "not_available"
    assert arb["not_recorded"] == 0


async def test_arb_decided_before_the_history_is_not_recorded_not_reconstructed(db):
    now = datetime.now(timezone.utc)
    _arb(db, "Legacy", created=now - timedelta(days=30), status="approved", decided_at=now)
    _arb(db, "Legacy deferred", created=now - timedelta(days=30), status="deferred", decided_at=now)
    await db.flush()
    arb = (await _turnaround(db))["instruments"]["arb"]
    # decided_at is never used as the decision instant (it is overwritten, I-12).
    assert arb["status"] == "not_available"
    assert arb["not_recorded"] == 1


async def test_exception_elapsed_runs_from_request_to_first_decision(db, landscape):
    now = datetime.now(timezone.utc)
    timed = StandardException(
        standard_id=landscape["std"].id,
        card_id=landscape["app"].id,
        status="approved",
        created_at=now - timedelta(days=2),
    )
    legacy = StandardException(
        standard_id=landscape["std"].id, card_id=landscape["itc"].id, status="rejected"
    )
    pending = StandardException(standard_id=landscape["std"].id, status="requested")
    db.add_all([timed, legacy, pending])
    await db.flush()
    _move(db, "exception", timed.id, None, "requested", now - timedelta(days=2))
    _move(db, "exception", timed.id, "requested", "approved", now)
    await db.flush()
    exc = (await _turnaround(db))["instruments"]["exception"]
    assert exc["decisions"] == 1
    assert exc["median_days"] == 2.0
    # The legacy decision has no recorded lifecycle; a pending request is no decision.
    assert exc["not_recorded"] == 1
    assert exc["not_recorded_temporal"] == "current_state"
    assert exc["basis"] == "requested_to_first_decision"


async def test_expiry_is_never_a_decision_or_a_resolution(db, landscape):
    now = datetime.now(timezone.utc)
    expired = StandardException(
        standard_id=landscape["std"].id,
        card_id=landscape["app"].id,
        status="approved",
        expiry_date=date.today() - timedelta(days=1),
        created_at=now - timedelta(days=5),
    )
    db.add(expired)
    await db.flush()
    _move(
        db,
        "exception",
        expired.id,
        "requested",
        "approved",
        now - timedelta(days=3),
        expired.expiry_date,
    )
    await db.flush()
    summary = await gov.governance_summary(
        db, CardReadScope.everything(), _fy_period(), gov03_link=None
    )
    # Timed once, by its approval; the expired waiver is still a violation.
    assert summary["effectiveness"]["turnaround"]["instruments"]["exception"]["decisions"] == 1
    # Expiry resolves nothing: due, unremediated, so 0 % and counted as unresolved.
    gov04 = summary["effectiveness"]["exception_resolution"]
    assert gov04["eligible"] == 1
    assert gov04["outcomes"]["expired_unresolved"] == 1
    assert gov04["outcomes"]["remediated_on_time"] == 0
    assert gov04["value"] == 0.0
    assert summary["effectiveness"]["compliance"]["details"]["violating"] >= 1


# --------------------------------------------------------------------------- #
# GOV-07 governance-controlled processing time (D-39)                          #
# --------------------------------------------------------------------------- #
def _row(frm, to, hours, attribution=None, reason=None):
    from types import SimpleNamespace

    return SimpleNamespace(
        from_status=frm,
        to_status=to,
        occurred_at=_t(hours=hours),
        delay_attribution=attribution,
        reason=reason,
    )


ARB_OUT = ("approved", "rejected")


def test_requester_attributed_deferral_with_a_reason_is_left_out():
    chain = [
        _row(None, "scheduled", 0),
        _row("scheduled", "deferred", 24, "requester", "Awaiting the business case"),
        _row("deferred", "scheduled", 72),
        _row("scheduled", "approved", 96),
    ]
    assert gov.processing_days(chain, ARB_OUT, ("deferred",)) == (2.0, None)


def test_external_attribution_is_left_out_too():
    chain = [
        _row(None, "scheduled", 0),
        _row("scheduled", "deferred", 0, "external", "Vendor security review"),
        _row("deferred", "approved", 48),
    ]
    assert gov.processing_days(chain, ARB_OUT, ("deferred",)) == (0.0, None)


def test_a_governance_caused_deferral_stays_in():
    chain = [
        _row(None, "scheduled", 0),
        _row("scheduled", "deferred", 24, "governance", "Board quorum not met"),
        _row("deferred", "approved", 72),
    ]
    assert gov.processing_days(chain, ARB_OUT, ("deferred",)) == (3.0, None)


def test_an_unattributed_waiting_interval_makes_the_record_untimed():
    chain = [
        _row(None, "scheduled", 0),
        _row("scheduled", "deferred", 24),
        _row("deferred", "approved", 72),
    ]
    assert gov.processing_days(chain, ARB_OUT, ("deferred",)) == (None, "delay_unattributed")


def test_an_attribution_without_a_reason_is_not_excluded():
    chain = [
        _row(None, "scheduled", 0),
        _row("scheduled", "deferred", 24, "requester", "  "),
        _row("deferred", "approved", 72),
    ]
    assert gov.processing_days(chain, ARB_OUT, ("deferred",)) == (3.0, None)


def test_adr_initial_draft_needs_an_attribution_like_any_draft():
    unattributed = [
        _row(None, "draft", 0),
        _row("draft", "in_review", 24),
        _row("in_review", "signed", 48),
    ]
    assert gov.processing_days(unattributed, ("signed",), ("draft",)) == (
        None,
        "delay_unattributed",
    )
    attributed = [
        _row(None, "draft", 0, "requester", "Author drafting"),
        _row("draft", "in_review", 24),
        _row("in_review", "draft", 36, "requester", "Signatory asked for options"),
        _row("draft", "in_review", 60),
        _row("in_review", "signed", 72),
    ]
    # 12 h + 12 h in review count; 24 h + 24 h of drafting are the author's.
    assert gov.processing_days(attributed, ("signed",), ("draft",)) == (1.0, None)


def test_the_history_must_start_with_creation_and_chain_unbroken():
    assert gov.processing_days([], ARB_OUT, ())[1] == "history_not_recorded"
    late = [_row("scheduled", "approved", 5)]
    assert gov.processing_days(late, ARB_OUT, ())[1] == "history_not_recorded"
    gap = [_row(None, "scheduled", 0), _row("deferred", "approved", 5)]
    assert gov.processing_days(gap, ARB_OUT, ())[1] == "history_broken"
    backwards = [_row(None, "scheduled", 5), _row("scheduled", "approved", 1)]
    assert gov.processing_days(backwards, ARB_OUT, ())[1] == "history_broken"
    undecided = [_row(None, "scheduled", 0), _row("scheduled", "deferred", 1, "governance")]
    assert gov.processing_days(undecided, ARB_OUT, ("deferred",))[1] == "no_decision"


def test_only_the_first_decision_closes_the_window():
    chain = [
        _row(None, "requested", 0),
        _row("requested", "approved", 48),
        _row("approved", "rejected", 200),
    ]
    assert gov.processing_days(chain, ARB_OUT, ()) == (2.0, None)


def test_processing_figure_counts_untimed_records_by_cause():
    fig = gov.processing_figure(
        [(1.0, None), (3.0, None), (None, "delay_unattributed"), (None, "history_not_recorded")]
    )
    assert fig == {
        "status": "ok",
        "decisions": 2,
        "median_days": 2.0,
        "max_days": 3.0,
        "not_computable": {"delay_unattributed": 1, "history_not_recorded": 1},
    }
    empty = gov.processing_figure([(None, "history_not_recorded")])
    assert empty["status"] == "not_available"
    assert empty["reason"] == {"code": "processing_not_computable"}
    assert "median_days" not in empty


# --------------------------------------------------------------------------- #
# GOV-04 exception resolution (D-40)                                           #
# --------------------------------------------------------------------------- #
def test_only_verification_on_or_before_the_original_expiry_counts_as_on_time():
    expiry = _t().date()
    on_time = [
        _row("approved", "remediation_submitted", -5),
        _row("remediation_submitted", "remediated", 0),
    ]
    late = [
        _row("approved", "remediation_submitted", -5),
        _row("remediation_submitted", "remediated", 48),
    ]
    assert gov.classify_resolution(on_time, expiry) == "remediated_on_time"
    assert gov.classify_resolution(late, expiry) == "remediated_late"


def test_administrative_and_unresolved_outcomes_stay_apart():
    expiry = _t().date()
    approved = _row("requested", "approved", -100)
    assert gov.classify_resolution([approved, _row("approved", "withdrawn", 1)], expiry) == (
        "withdrawn"
    )
    assert gov.classify_resolution([approved, _row("approved", "rejected", 1)], expiry) == (
        "rejected"
    )
    submitted = _row("approved", "remediation_submitted", 1)
    assert gov.classify_resolution([approved, submitted], expiry) == "awaiting_verification"
    assert gov.classify_resolution([approved], expiry) == "expired_unresolved"
    assert gov.classify_resolution([], expiry) == "not_recorded"


def test_a_withdrawal_after_submission_is_never_remediation():
    expiry = _t().date()
    chain = [
        _row("requested", "approved", -100),
        _row("approved", "remediation_submitted", -10),
        _row("remediation_submitted", "withdrawn", -1),
    ]
    assert gov.classify_resolution(chain, expiry) == "withdrawn"


def test_each_approval_decision_opens_a_cycle_a_returned_remediation_does_not():
    created = _row(None, "requested", -1)
    first = _row("requested", "approved", 0)
    submitted = _row("approved", "remediation_submitted", 5)
    returned = _row("remediation_submitted", "approved", 6)
    rejected = _row("approved", "rejected", 7)
    second = _row("rejected", "approved", 8)
    chain = [created, first, submitted, returned, rejected, second]
    assert gov.approval_cycles(chain) == [
        (first, [first, submitted, returned, rejected]),
        (second, [second]),
    ]
    assert gov.approval_cycles([created]) == []


def _exc_move(e, frm, to, at, approved_expiry=None):
    """One exception transition; an approval carries its approved expiry (I-31)."""
    is_approval = to == "approved" and frm in ("requested", "rejected")
    return GovernanceTransition(
        instrument="exception",
        record_id=e.id,
        from_status=frm,
        to_status=to,
        occurred_at=at,
        approved_expiry_date=approved_expiry if is_approval else None,
    )


async def _gov04(db, scope=None):
    summary = await gov.governance_summary(
        db, scope or CardReadScope.everything(), _fy_period(), gov03_link=None
    )
    return summary["effectiveness"]["exception_resolution"]


async def test_gov04_counts_verified_remediation_only(db, landscape):
    now = datetime.now(timezone.utc)
    today = date.today()
    expiry = today - timedelta(days=2)
    std = landscape["std"]

    def mk(status, *moves):
        e = StandardException(
            standard_id=std.id, card_id=landscape["app"].id, status=status, expiry_date=expiry
        )
        db.add(e)
        return e, moves

    rows = [
        mk(
            "remediated",
            (None, "requested", 10),
            ("requested", "approved", 9),
            ("approved", "remediation_submitted", 4),
            ("remediation_submitted", "remediated", 3),
        ),
        mk(
            "remediated",
            (None, "requested", 10),
            ("requested", "approved", 9),
            ("approved", "remediation_submitted", 1),
            ("remediation_submitted", "remediated", 0),
        ),
        mk(
            "withdrawn",
            (None, "requested", 10),
            ("requested", "approved", 9),
            ("approved", "withdrawn", 5),
        ),
        mk(
            "remediation_submitted",
            (None, "requested", 10),
            ("requested", "approved", 9),
            ("approved", "remediation_submitted", 3),
        ),
        mk("approved", (None, "requested", 10), ("requested", "approved", 9)),
        mk("approved"),  # approved before the history existed
        mk("withdrawn", (None, "requested", 10), ("requested", "withdrawn", 9)),  # never a waiver
    ]
    await db.flush()
    for e, moves in rows:
        for frm, to, days_ago in moves:
            db.add(_exc_move(e, frm, to, now - timedelta(days=days_ago), expiry))
    await db.flush()
    res = await _gov04(db)
    assert res["eligible"] == 5
    assert res["outcomes"] == {
        "remediated_on_time": 1,
        "remediated_late": 1,
        "withdrawn": 1,
        "rejected": 0,
        "awaiting_verification": 1,
        "expired_unresolved": 1,
    }
    assert res["not_recorded"] == 1
    assert res["value"] == 20.0
    assert res["basis"] == "verified_by_expiry"


async def test_gov04_ignores_exceptions_not_yet_due_or_outside_the_period(db, landscape):
    now = datetime.now(timezone.utc)
    future = StandardException(
        standard_id=landscape["std"].id,
        card_id=landscape["app"].id,
        status="approved",
        expiry_date=date.today() + timedelta(days=30),
    )
    no_expiry = StandardException(
        standard_id=landscape["std"].id, card_id=landscape["app"].id, status="approved"
    )
    db.add_all([future, no_expiry])
    await db.flush()
    for e in (future, no_expiry):
        db.add(
            GovernanceTransition(
                instrument="exception",
                record_id=e.id,
                from_status=None,
                to_status="requested",
                occurred_at=now - timedelta(days=3),
            )
        )
        db.add(_exc_move(e, "requested", "approved", now - timedelta(days=2), e.expiry_date))
    await db.flush()
    res = await _gov04(db)
    assert res["status"] == "not_available"
    assert res["eligible"] == 0


async def _approved_exception(db, landscape, *, expiry, approved_expiry, approved_at):
    e = StandardException(
        standard_id=landscape["std"].id,
        card_id=landscape["app"].id,
        status="approved",
        expiry_date=expiry,
    )
    db.add(e)
    await db.flush()
    db.add(_exc_move(e, None, "requested", approved_at - timedelta(days=1)))
    db.add(_exc_move(e, "requested", "approved", approved_at, approved_expiry))
    await db.flush()
    return e


async def test_gov04_uses_the_original_approved_expiry_not_a_later_edit(db, landscape):
    """I-31: an expiry pushed out after approval does not take the exception out
    of the period it was due in, and one pulled in does not bring it in."""
    now = datetime.now(timezone.utc)
    today = date.today()
    await _approved_exception(
        db,
        landscape,
        expiry=today + timedelta(days=300),  # edited after the approval
        approved_expiry=today - timedelta(days=2),
        approved_at=now - timedelta(days=9),
    )
    await _approved_exception(
        db,
        landscape,
        expiry=today - timedelta(days=2),  # edited after the approval
        approved_expiry=today + timedelta(days=300),
        approved_at=now - timedelta(days=9),
    )
    res = await _gov04(db)
    assert res["eligible"] == 1
    assert res["outcomes"]["expired_unresolved"] == 1
    assert res["not_recorded"] == 0


async def _two_cycle_exception(db, landscape):
    """Approved last year (expiry mid-last-year), rejected before that expiry,
    then approved again with an expiry a few days ago this year."""
    today = date.today()
    first_expiry = date(today.year - 1, 6, 30)
    second_expiry = today - timedelta(days=2)
    e = await _approved_exception(
        db,
        landscape,
        expiry=second_expiry,
        approved_expiry=first_expiry,
        approved_at=datetime(today.year - 1, 2, 1, tzinfo=timezone.utc),
    )
    db.add(
        _exc_move(e, "approved", "rejected", datetime(today.year - 1, 4, 1, tzinfo=timezone.utc))
    )
    db.add(
        _exc_move(
            e,
            "rejected",
            "approved",
            datetime(today.year - 1, 9, 1, tzinfo=timezone.utc),
            second_expiry,
        )
    )
    await db.flush()
    return e


async def test_gov04_each_period_uses_its_own_approval_cycle(db, landscape):
    """I-31 (approved with changes): each approval cycle keeps the expiry it
    granted; a period uses the cycle that fell due in it, with that cycle's
    outcome — never the first approval or the current expiry for every period."""
    today = date.today()
    await _two_cycle_exception(db, landscape)
    last_fy = periods.parse(f"FY{today.year - 1}", START_MONTH, today)
    past = await gov.exception_resolution(db, CardReadScope.everything(), last_fy)
    assert past["eligible"] == 1
    assert past["outcomes"]["rejected"] == 1  # the first cycle ended in rejection
    current = await _gov04(db)
    assert current["eligible"] == 1
    assert current["outcomes"]["expired_unresolved"] == 1  # the second cycle
    assert current["outcomes"]["rejected"] == 0


def _expiry_event(e, at, previous, new, status="approved"):
    return GovernanceTransition(
        instrument="exception",
        record_id=e.id,
        from_status=status,
        to_status=status,
        occurred_at=at,
        event_kind="expiry_changed",
        previous_expiry_date=previous,
        approved_expiry_date=new,
        reason="Vendor delay",
    )


def test_the_expiry_in_force_is_the_approval_s_until_a_recorded_change():
    from types import SimpleNamespace

    approval = SimpleNamespace(approved_expiry_date=date(2026, 3, 31), event_kind=None)
    change = SimpleNamespace(approved_expiry_date=date(2026, 6, 30), event_kind="expiry_changed")
    other = SimpleNamespace(approved_expiry_date=None, event_kind=None)
    assert gov.effective_expiry([approval]) == date(2026, 3, 31)
    assert gov.effective_expiry([approval, other, change]) == date(2026, 6, 30)
    legacy = SimpleNamespace(approved_expiry_date=None, event_kind=None)
    assert gov.effective_expiry([legacy]) is gov.UNKNOWN
    assert gov.effective_expiry([legacy, change]) == date(2026, 6, 30)


async def test_gov04_two_approvals_due_in_one_period_count_one_exception_two_cycles(db, landscape):
    """Decision A: the denominator is unique exceptions; every due approval
    cycle, the earlier rejected one included, is reported apart in cycles and
    never added to the exception distribution."""
    now = datetime.now(timezone.utc)
    today = date.today()
    e = await _approved_exception(
        db,
        landscape,
        expiry=today - timedelta(days=2),
        approved_expiry=today - timedelta(days=3),
        approved_at=now - timedelta(days=12),
    )
    db.add(_exc_move(e, "approved", "rejected", now - timedelta(days=10)))
    db.add(_exc_move(e, "rejected", "approved", now - timedelta(days=8), today - timedelta(days=2)))
    await db.flush()
    res = await _gov04(db)
    assert res["unit_of_count"] == "exceptions"
    assert res["eligible"] == 1
    assert sum(res["outcomes"].values()) == res["eligible"]
    assert res["outcomes"]["expired_unresolved"] == 1  # the applicable (latest) cycle
    assert res["outcomes"]["rejected"] == 0
    cycles = res["approval_cycles"]
    assert cycles["unit_of_count"] == "approval_cycles"
    assert cycles["eligible"] == 2
    assert cycles["outcomes"]["rejected"] == 1
    assert cycles["outcomes"]["expired_unresolved"] == 1


async def test_gov04_uses_the_expiry_in_force_for_the_cycle_and_period(db, landscape):
    """Decision B: an extension recorded inside the period moves the deadline
    for it; one recorded after the period's end does not rewrite that period."""
    today = date.today()
    last_fy = periods.parse(f"FY{today.year - 1}", START_MONTH, today)
    first = date(today.year - 1, 3, 31)
    e = await _approved_exception(
        db,
        landscape,
        expiry=today - timedelta(days=2),
        approved_expiry=first,
        approved_at=datetime(today.year - 1, 1, 10, tzinfo=timezone.utc),
    )
    # Extended in March of last year to June, then after last year's end to now-2.
    db.add(
        _expiry_event(
            e,
            datetime(today.year - 1, 3, 20, tzinfo=timezone.utc),
            first,
            date(today.year - 1, 6, 30),
        )
    )
    db.add(
        _expiry_event(
            e,
            datetime(today.year, 1, 2, tzinfo=timezone.utc),
            date(today.year - 1, 6, 30),
            today - timedelta(days=2),
        )
    )
    await db.flush()
    past = await gov.exception_resolution(db, CardReadScope.everything(), last_fy)
    # Due in June last year (the expiry in force then), not in March, not now.
    assert past["eligible"] == 1
    assert past["outcomes"]["expired_unresolved"] == 1
    q1 = await gov.exception_resolution(
        db, CardReadScope.everything(), periods.parse(f"FY{today.year - 1}-Q1", START_MONTH, today)
    )
    assert q1["eligible"] == 0  # the March expiry was extended before it passed
    current = await _gov04(db)
    assert current["eligible"] == 1


async def test_an_expiry_change_is_never_a_decision_for_gov07(db, landscape):
    """An expiry-change event keeps the status; GOV-07 never times it as a
    decision (it filters status changes only)."""
    now = datetime.now(timezone.utc)
    e = StandardException(
        standard_id=landscape["std"].id,
        card_id=landscape["app"].id,
        status="approved",
        expiry_date=date.today(),
        created_at=now - timedelta(days=5),
    )
    db.add(e)
    await db.flush()
    db.add(_expiry_event(e, now - timedelta(days=1), None, date.today()))
    await db.flush()
    t = await _turnaround(db)
    assert t["instruments"]["exception"]["decisions"] == 0


async def test_gov04_a_cycle_without_its_expiry_is_never_given_another(db, landscape):
    """A cycle recorded before its approved expiry was kept is not measured
    against the current expiry or another cycle's expiry."""
    today = date.today()
    e = await _approved_exception(
        db,
        landscape,
        expiry=today - timedelta(days=2),
        approved_expiry=None,
        approved_at=datetime.now(timezone.utc) - timedelta(days=40),
    )
    db.add(_exc_move(e, "approved", "rejected", datetime.now(timezone.utc) - timedelta(days=30)))
    db.add(
        _exc_move(
            e,
            "rejected",
            "approved",
            datetime.now(timezone.utc) - timedelta(days=20),
            today + timedelta(days=200),
        )
    )
    await db.flush()
    res = await _gov04(db)
    assert res["eligible"] == 0
    assert res["not_recorded"] == 1


async def test_gov04_an_approval_without_its_approved_expiry_is_not_recorded(db, landscape):
    now = datetime.now(timezone.utc)
    expiry = date.today() - timedelta(days=2)
    await _approved_exception(
        db, landscape, expiry=expiry, approved_expiry=None, approved_at=now - timedelta(days=9)
    )
    res = await _gov04(db)
    assert res["eligible"] == 0
    assert res["not_recorded"] == 1
    assert res["status"] == "not_available"


async def test_gov04_a_completed_period_is_not_rewritten_by_later_events(db, landscape):
    """I-31: last year's figure is judged from last year's boundaries and the
    history recorded up to its end — a verification this year does not turn an
    exception that was unresolved at the period's end into a remediation."""
    today = date.today()
    last_fy = periods.parse(f"FY{today.year - 1}", START_MONTH, today)
    assert not last_fy.is_current
    expiry = date(today.year - 1, 6, 30)
    approved_at = datetime(today.year - 1, 3, 1, tzinfo=timezone.utc)
    e = await _approved_exception(
        db, landscape, expiry=expiry, approved_expiry=expiry, approved_at=approved_at
    )
    e.status = "remediated"
    db.add(
        _exc_move(
            e,
            "approved",
            "remediation_submitted",
            datetime(today.year - 1, 12, 30, tzinfo=timezone.utc),
        )
    )
    db.add(
        _exc_move(
            e,
            "remediation_submitted",
            "remediated",
            datetime(today.year, 1, 1, 9, tzinfo=timezone.utc),
        )
    )
    await db.flush()
    res = await gov.exception_resolution(db, CardReadScope.everything(), last_fy)
    assert res["eligible"] == 1
    assert res["outcomes"]["awaiting_verification"] == 1
    assert res["outcomes"]["remediated_late"] == 0
    assert res["value"] == 0.0


async def test_gov04_an_expiry_on_the_last_day_of_a_completed_period_is_due(db, landscape):
    today = date.today()
    last_fy = periods.parse(f"FY{today.year - 1}", START_MONTH, today)
    expiry = last_fy.end - timedelta(days=1)
    await _approved_exception(
        db,
        landscape,
        expiry=expiry,
        approved_expiry=expiry,
        approved_at=datetime(today.year - 1, 2, 1, tzinfo=timezone.utc),
    )
    res = await gov.exception_resolution(db, CardReadScope.everything(), last_fy)
    assert res["eligible"] == 1
    assert res["outcomes"]["expired_unresolved"] == 1


async def test_gov07_elapsed_stays_available_when_a_delay_is_unattributed(db):
    """D-39 / I-22: an unattributed deferral makes processing time Not Available
    for that review and never gives it a value — elapsed is still reported."""
    now = datetime.now(timezone.utc)
    r = ArbReview(title="Untimed", status="approved", created_at=now - timedelta(days=4))
    db.add(r)
    await db.flush()
    for frm, to, days_ago in (
        (None, "scheduled", 4),
        ("scheduled", "deferred", 3),  # nobody said who the wait was due to
        ("deferred", "scheduled", 1),
        ("scheduled", "approved", 0),
    ):
        db.add(
            GovernanceTransition(
                instrument="arb",
                record_id=r.id,
                from_status=frm,
                to_status=to,
                occurred_at=now - timedelta(days=days_ago),
            )
        )
    await db.flush()
    t = await _turnaround(db)
    assert t["instruments"]["arb"]["status"] == "ok"
    assert t["instruments"]["arb"]["median_days"] == 4.0
    proc = t["processing_time"]["instruments"]["arb"]
    assert proc["status"] == "not_available"
    assert proc["not_computable"] == {"delay_unattributed": 1}
    assert "median_days" not in proc


async def test_activity_keeps_every_lifecycle_state_apart(db, landscape):
    for status in ("remediation_submitted", "remediated", "withdrawn", "withdrawn"):
        db.add(StandardException(standard_id=landscape["std"].id, status=status))
    await db.flush()
    summary = await gov.governance_summary(
        db, CardReadScope.everything(), _period(), gov03_link=None
    )
    exc = summary["activity"]["exceptions"]
    assert (exc["remediation_submitted"], exc["remediated"], exc["withdrawn"]) == (1, 1, 2)
    assert "exception_lifecycle" not in summary["activity"]


async def test_processing_time_in_the_summary_uses_the_recorded_attribution(db):
    now = datetime.now(timezone.utc)
    r = ArbReview(title="Timed", status="approved", created_at=now - timedelta(days=4))
    db.add(r)
    await db.flush()
    for frm, to, days_ago, who, why in (
        (None, "scheduled", 4, None, None),
        ("scheduled", "deferred", 3, "requester", "Business case missing"),
        ("deferred", "scheduled", 1, None, None),
        ("scheduled", "approved", 0, None, None),
    ):
        db.add(
            GovernanceTransition(
                instrument="arb",
                record_id=r.id,
                from_status=frm,
                to_status=to,
                occurred_at=now - timedelta(days=days_ago),
                delay_attribution=who,
                reason=why,
            )
        )
    await db.flush()
    t = await _turnaround(db)
    assert t["instruments"]["arb"]["median_days"] == 4.0  # elapsed is unchanged
    proc = t["processing_time"]["instruments"]["arb"]
    assert proc["status"] == "ok"
    assert proc["median_days"] == 2.0


# --------------------------------------------------------------------------- #
# GOV-07 working days on the business calendar (D-28, D-38; Batch 3.3)         #
# --------------------------------------------------------------------------- #
async def _confirm_years(db, *years):
    from app.models.business_calendar import BusinessCalendarYear

    for fy in years:
        db.add(
            BusinessCalendarYear(
                fiscal_year=fy, working_weekdays=[7, 1, 2, 3, 4], holidays=[], confirmed=True
            )
        )
    await db.flush()


async def test_gov07_working_days_appear_once_the_period_is_confirmed(db):
    now = datetime.now(timezone.utc)
    db.add(
        ArchitectureDecision(
            reference_number="ADR-WD",
            title="Timed",
            status="signed",
            created_at=now - timedelta(days=7),
            signed_at=now,
        )
    )
    await db.flush()
    period = _fy_period()
    # Seven calendar days always hold five Sunday–Thursday working days; the
    # span may start in the previous fiscal year, so both are confirmed.
    await _confirm_years(db, period.fy - 1, period.fy)
    wd = (await _turnaround(db))["working_days"]
    assert wd["status"] == "ok" and wd["unit"] == "working_days"
    adr = wd["instruments"]["adr"]
    assert (adr["status"], adr["decisions"], adr["median_days"]) == ("ok", 1, 5)


async def test_gov07_a_span_into_an_unconfirmed_year_is_untimed_not_estimated(db):
    now = datetime.now(timezone.utc)
    db.add(
        ArchitectureDecision(
            reference_number="ADR-OLD",
            title="Started long ago",
            status="signed",
            created_at=now.replace(year=now.year - 2),
            signed_at=now,
        )
    )
    await db.flush()
    period = _fy_period()
    await _confirm_years(db, period.fy)  # the period is valid; the span's start year is not
    adr = (await _turnaround(db))["working_days"]["instruments"]["adr"]
    assert adr["status"] == "not_available"
    assert adr["not_computable"] == {"calendar_not_confirmed": 1}
    assert "median_days" not in adr
