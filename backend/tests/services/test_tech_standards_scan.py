"""Tests for the Technology Standards compliance scan.

Covers the Application → ITComponent → TechCategory ← TechStandard mapping,
the sunset/prohibited flagging, and exception-based waiving.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.models.tech_standard import StandardException, TechStandard
from app.services.tech_standards_scan import scan_standard_compliance
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
    result = await scan_standard_compliance(db)
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
    result = await scan_standard_compliance(db)
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
    result = await scan_standard_compliance(db)
    assert result["summary"]["violations"] == 2
    assert result["summary"]["waived"] == 0


async def test_preferred_standard_is_not_flagged(db):
    admin = await create_user(db, email="b@example.com", role="admin")
    cat = await create_card(db, card_type="TechCategory", name="API", user_id=admin.id)
    itc = await create_card(db, card_type="ITComponent", name="REST GW", user_id=admin.id)
    await create_relation(db, type_key="relITCToTechCat", source_id=itc.id, target_id=cat.id)
    await _standard(db, category_card_id=cat.id, status="preferred", name="REST")
    result = await scan_standard_compliance(db)
    assert result["summary"]["violations"] == 0
    assert result["violations"] == []
