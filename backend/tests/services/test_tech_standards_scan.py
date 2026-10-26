"""Tests for the Technology Standards compliance scan.

Covers the Application → ITComponent → TechCategory ← TechStandard mapping,
the sunset/prohibited flagging, and exception-based waiving.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.models.tech_standard import StandardException, TechStandard
from app.services.card_read_scope import CardReadScope
from app.services.tech_standards_scan import (
    assess_standard_compliance,
    scan_standard_compliance,
)
from tests.conftest import create_card, create_relation, create_user


async def _standard(db, *, category_card_id, status="prohibited", name="Legacy SOAP"):
    std = TechStandard(
        name=name,
        category="integration",
        status=status,
        tech_category_id=category_card_id,
    )
    db.add(std)
    await db.flush()
    return std


@pytest.fixture
async def landscape(db):
    """A category governed by a prohibited standard, an ITC on it, an app using the ITC."""
    admin = await create_user(db, email="a@example.com", role="admin")
    cat = await create_card(db, card_type="TechCategory", name="Messaging", user_id=admin.id)
    itc = await create_card(db, card_type="ITComponent", name="OldMQ", user_id=admin.id)
    app = await create_card(db, card_type="Application", name="Billing", user_id=admin.id)
    await create_relation(db, type_key="relITCToTechCat", source_id=itc.id, target_id=cat.id)
    await create_relation(db, type_key="relAppToITC", source_id=app.id, target_id=itc.id)
    std = await _standard(db, category_card_id=cat.id)
    return {"admin": admin, "cat": cat, "itc": itc, "app": app, "std": std}


async def test_scan_flags_component_and_application(db, landscape):
    result = await scan_standard_compliance(db, read_scope=CardReadScope.everything())
    assert result["summary"]["violations"] == 2  # ITComponent + Application
    assert result["summary"]["prohibited_standards"] == 1
    vias = {v["via"] for v in result["violations"]}
    assert vias == {"component", "application"}
    app_row = next(v for v in result["violations"] if v["via"] == "application")
    assert app_row["component_name"] == "OldMQ"
    assert app_row["card_name"] == "Billing"


async def test_approved_exception_waives_the_component(db, landscape):
    db.add(
        StandardException(
            standard_id=landscape["std"].id,
            card_id=landscape["itc"].id,
            status="approved",
            expiry_date=date.today() + timedelta(days=30),
        )
    )
    await db.flush()
    result = await scan_standard_compliance(db, read_scope=CardReadScope.everything())
    # The ITComponent is waived; the Application is still an active violation.
    assert result["summary"]["violations"] == 1
    assert result["summary"]["waived"] == 1
    waived_row = next(v for v in result["violations"] if v["waived"])
    assert waived_row["card_name"] == "OldMQ"


async def test_expired_exception_does_not_waive(db, landscape):
    db.add(
        StandardException(
            standard_id=landscape["std"].id,
            card_id=landscape["itc"].id,
            status="approved",
            expiry_date=date.today() - timedelta(days=1),
        )
    )
    await db.flush()
    result = await scan_standard_compliance(db, read_scope=CardReadScope.everything())
    assert result["summary"]["violations"] == 2
    assert result["summary"]["waived"] == 0


async def test_preferred_standard_is_not_flagged(db):
    admin = await create_user(db, email="b@example.com", role="admin")
    cat = await create_card(db, card_type="TechCategory", name="API", user_id=admin.id)
    itc = await create_card(db, card_type="ITComponent", name="REST GW", user_id=admin.id)
    await create_relation(db, type_key="relITCToTechCat", source_id=itc.id, target_id=cat.id)
    await _standard(db, category_card_id=cat.id, status="preferred", name="REST")
    result = await scan_standard_compliance(db, read_scope=CardReadScope.everything())
    assert result["summary"]["violations"] == 0
    assert result["violations"] == []


async def test_scan_skips_paths_through_cards_the_reader_may_not_see(db, landscape):
    """A reader who may not see IT components gets neither the component row
    nor the application reached through it — the path itself is hidden."""
    restricted = CardReadScope(
        role_key="r",
        wildcard=False,
        base_view=True,
        denied_types=frozenset({"ITComponent"}),
        allowed_types=frozenset(),
        stakeholder_card_ids=frozenset(),
    )
    result = await scan_standard_compliance(db, read_scope=restricted)
    assert result["summary"]["violations"] == 0
    assert "OldMQ" not in str(result) and str(landscape["itc"].id) not in str(result)


# ── Assessment coverage + compliance (I-8..I-11) ──────────────────────────


async def test_assessment_population_counts_both_assessed_cards(db, landscape):
    """The ITComponent on the governed category and the Application reaching it
    through it are both assessed; both violate the prohibited standard (I-8/I-9)."""
    result = await assess_standard_compliance(db, read_scope=CardReadScope.everything())
    assert result["status"] == "ok"
    assert result["assessed"] == 2  # OldMQ + Billing
    assert result["violating"] == 2
    assert result["compliant"] == 0
    assert result["compliance_pct"] == 0.0
    # Coverage denominator = all ACTIVE Application + IT Component cards.
    assert result["population"] == 2
    assert result["coverage_pct"] == 100.0


async def test_assessment_coverage_is_below_full_when_cards_are_unassessed(db, landscape):
    """A standard reaching only one category leaves other App/ITC cards
    unassessed, so coverage drops below 100 % while compliance is unaffected."""
    await create_card(db, card_type="Application", name="Unassessed", user_id=landscape["admin"].id)
    result = await assess_standard_compliance(db, read_scope=CardReadScope.everything())
    assert result["assessed"] == 2
    assert result["population"] == 3
    assert result["coverage_pct"] == round(2 / 3 * 100, 1)


async def test_assessment_skips_paths_through_hidden_components(db, landscape):
    """A reader who cannot see IT components has that type hidden entirely, so
    the whole assessment is Unavailable rather than silently partial (I-11)."""
    restricted = CardReadScope(
        role_key="r",
        wildcard=False,
        base_view=True,
        denied_types=frozenset({"ITComponent"}),
        allowed_types=frozenset(),
        stakeholder_card_ids=frozenset(),
    )
    result = await assess_standard_compliance(db, read_scope=restricted)
    assert result["status"] == "unavailable"
    assert result["reason"]["code"] == "type_hidden"
    assert "OldMQ" not in str(result) and str(landscape["itc"].id) not in str(result)


@pytest.mark.parametrize(
    ("status", "waived"),
    [("remediation_submitted", 1), ("remediated", 0), ("withdrawn", 0), ("rejected", 0)],
)
async def test_only_a_live_waiver_waives(db, landscape, status, waived):
    """A submitted, unverified remediation keeps its approved waiver until expiry
    (I-23); a remediated or withdrawn exception waives nothing any more."""
    db.add(
        StandardException(
            standard_id=landscape["std"].id,
            card_id=landscape["itc"].id,
            status=status,
            expiry_date=date.today() + timedelta(days=30),
        )
    )
    await db.flush()
    result = await scan_standard_compliance(db, read_scope=CardReadScope.everything())
    assert result["summary"]["waived"] == waived
    assert result["summary"]["violations"] == 2 - waived


async def test_awaiting_verification_past_expiry_does_not_waive(db, landscape):
    db.add(
        StandardException(
            standard_id=landscape["std"].id,
            card_id=landscape["itc"].id,
            status="remediation_submitted",
            expiry_date=date.today() - timedelta(days=1),
        )
    )
    await db.flush()
    result = await scan_standard_compliance(db, read_scope=CardReadScope.everything())
    assert result["summary"]["waived"] == 0
