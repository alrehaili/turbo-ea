"""Standards-compliance scan for the Technology Standards Radar (Wave 2 #5).

Maps the live card landscape onto the technology-standards catalogue and flags
**violations** — cards that use a technology governed by a ``sunset`` or
``prohibited`` standard without an active waiver.

Mapping chain (built-in metamodel, no schema change)::

    Application --relAppToITC--> ITComponent --relITCToTechCat--> TechCategory
                                                                       ^
                                              TechStandard.tech_category_id

A standard "governs" the TechCategory card it points at via
``tech_category_id``. Any ITComponent linked to that category — and any
Application using such an ITComponent — is using the standard. When the
standard's status is ``sunset`` / ``prohibited`` that usage is a violation,
unless an **approved, non-expired** :class:`StandardException` waives it for
that exact card.

Read-only: gated by ``tech_standards.view``. The catalogue's own exception
workflow (request → approve, with expiry) remains the only way to waive.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.relation import Relation
from app.models.tech_standard import StandardException, TechStandard

VIOLATING_STATUSES = ("sunset", "prohibited")
REL_APP_TO_ITC = "relAppToITC"
REL_ITC_TO_TECHCAT = "relITCToTechCat"


def _brief(card: Card) -> dict:
    return {"id": str(card.id), "name": card.name, "type": card.type}


async def scan_standard_compliance(db: AsyncSession) -> dict:
    """Return violations of sunset/prohibited standards across the landscape."""
    # 1. Sunset / prohibited standards that actually govern a tech category.
    std_res = await db.execute(
        select(TechStandard).where(
            TechStandard.status.in_(VIOLATING_STATUSES),
            TechStandard.tech_category_id.is_not(None),
        )
    )
    governing = list(std_res.scalars().all())
    stds_by_cat: dict[uuid.UUID, list[TechStandard]] = {}
    for s in governing:
        stds_by_cat.setdefault(s.tech_category_id, []).append(s)

    empty = {
        "summary": {
            "violations": 0,
            "waived": 0,
            "sunset_standards": sum(1 for s in governing if s.status == "sunset"),
            "prohibited_standards": sum(1 for s in governing if s.status == "prohibited"),
        },
        "violations": [],
    }
    if not stds_by_cat:
        return empty

    cat_ids = set(stds_by_cat)

    # 2. ACTIVE ITComponents linked to those TechCategory cards.
    itc_rel = await db.execute(
        select(Relation.source_id, Relation.target_id).where(
            Relation.type == REL_ITC_TO_TECHCAT,
            Relation.target_id.in_(cat_ids),
        )
    )
    itc_to_cats: dict[uuid.UUID, set[uuid.UUID]] = {}
    for itc_id, cat_id in itc_rel.all():
        itc_to_cats.setdefault(itc_id, set()).add(cat_id)

    # 3. Applications using those ITComponents.
    app_to_itcs: dict[uuid.UUID, set[uuid.UUID]] = {}
    if itc_to_cats:
        app_rel = await db.execute(
            select(Relation.source_id, Relation.target_id).where(
                Relation.type == REL_APP_TO_ITC,
                Relation.target_id.in_(set(itc_to_cats)),
            )
        )
        for app_id, itc_id in app_rel.all():
            app_to_itcs.setdefault(app_id, set()).add(itc_id)

    # 4. Approved, non-expired exceptions keyed by (standard_id, card_id).
    exc_res = await db.execute(
        select(
            StandardException.standard_id,
            StandardException.card_id,
            StandardException.id,
            StandardException.expiry_date,
        ).where(StandardException.status == "approved")
    )
    today = date.today()
    waived: dict[tuple[uuid.UUID, uuid.UUID], dict] = {}
    for sid, cid, eid, expiry in exc_res.all():
        if cid is None or (expiry is not None and expiry < today):
            continue
        waived[(sid, cid)] = {
            "exception_id": str(eid),
            "exception_expiry": expiry.isoformat() if expiry else None,
        }

    # 5. Resolve the cards we need (ITCs, Apps, categories) — ACTIVE only.
    card_ids = set(itc_to_cats) | set(app_to_itcs) | cat_ids
    cards_res = await db.execute(select(Card).where(Card.id.in_(card_ids), Card.status == "ACTIVE"))
    card_map: dict[uuid.UUID, Card] = {c.id: c for c in cards_res.scalars().all()}

    violations: list[dict] = []
    seen: set[tuple[uuid.UUID, uuid.UUID]] = set()

    def add(card_id: uuid.UUID, cat_id: uuid.UUID, via: str, component: Card | None) -> None:
        card = card_map.get(card_id)
        cat = card_map.get(cat_id)
        if card is None:
            return  # archived / filtered out
        for std in stds_by_cat.get(cat_id, ()):
            key = (std.id, card_id)
            if key in seen:
                continue
            seen.add(key)
            wv = waived.get(key)
            violations.append(
                {
                    "card_id": str(card_id),
                    "card_name": card.name,
                    "card_type": card.type,
                    "standard_id": str(std.id),
                    "standard_name": std.name,
                    "standard_status": std.status,
                    "tech_category": _brief(cat) if cat else None,
                    "via": via,
                    "component_name": component.name if component else None,
                    "waived": wv is not None,
                    "exception_id": wv["exception_id"] if wv else None,
                    "exception_expiry": wv["exception_expiry"] if wv else None,
                }
            )

    # ITComponents directly on a governed category.
    for itc_id, cats in itc_to_cats.items():
        for cat_id in cats:
            add(itc_id, cat_id, "component", None)

    # Applications reaching a governed category through an ITComponent.
    for app_id, itcs in app_to_itcs.items():
        for itc_id in itcs:
            for cat_id in itc_to_cats.get(itc_id, ()):
                add(app_id, cat_id, "application", card_map.get(itc_id))

    # Active violations first, then waived; alphabetical within each group.
    violations.sort(key=lambda v: (v["waived"], v["card_name"].lower()))
    active = [v for v in violations if not v["waived"]]
    return {
        "summary": {
            "violations": len(active),
            "waived": len(violations) - len(active),
            "sunset_standards": empty["summary"]["sunset_standards"],
            "prohibited_standards": empty["summary"]["prohibited_standards"],
        },
        "violations": violations,
    }
