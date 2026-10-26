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
    assert turnaround["working_days"]["reason"]["decisions"] == ["D-38"]
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


def _move(db, instrument, record_id, frm, to, at):
    db.add(
        GovernanceTransition(
            instrument=instrument,
            record_id=record_id,
            from_status=frm,
            to_status=to,
            occurred_at=at,
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
    _move(db, "exception", expired.id, "requested", "approved", now - timedelta(days=3))
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
def _exc_ns(status, expiry):
    from types import SimpleNamespace

    return SimpleNamespace(status=status, expiry_date=expiry)


def test_only_verification_on_or_before_expiry_counts_as_on_time():
    expiry = _t().date()
    on_time = [_row("remediation_submitted", "remediated", 0)]
    late = [_row("remediation_submitted", "remediated", 48)]
    assert gov.classify_resolution(_exc_ns("remediated", expiry), on_time) == "remediated_on_time"
    assert gov.classify_resolution(_exc_ns("remediated", expiry), late) == "remediated_late"


def test_administrative_and_unresolved_outcomes_stay_apart():
    expiry = _t().date()
    assert gov.classify_resolution(_exc_ns("withdrawn", expiry), []) == "withdrawn"
    assert gov.classify_resolution(_exc_ns("rejected", expiry), []) == "rejected"
    assert (
        gov.classify_resolution(_exc_ns("remediation_submitted", expiry), [])
        == "awaiting_verification"
    )
    assert gov.classify_resolution(_exc_ns("approved", expiry), []) == "expired_unresolved"
    # "remediated" with no recorded verification is never trusted.
    assert gov.classify_resolution(_exc_ns("remediated", expiry), []) == "not_recorded"


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
            db.add(
                GovernanceTransition(
                    instrument="exception",
                    record_id=e.id,
                    from_status=frm,
                    to_status=to,
                    occurred_at=now - timedelta(days=days_ago),
                )
            )
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
        db.add(
            GovernanceTransition(
                instrument="exception",
                record_id=e.id,
                from_status="requested",
                to_status="approved",
                occurred_at=now - timedelta(days=2),
            )
        )
    await db.flush()
    res = await _gov04(db)
    assert res["status"] == "not_available"
    assert res["eligible"] == 0


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
