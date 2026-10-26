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
    for block in (eff["exception_resolution"], eff["decision_implementation"], eff["turnaround"]):
        assert block["status"] == "not_available"
        assert block["reason"]
    for block in (
        impact["architecture_risks"],
        impact["governed_delivery"],
        impact["business_value"],
    ):
        assert block["status"] == "not_available"
        assert block["reason"]
