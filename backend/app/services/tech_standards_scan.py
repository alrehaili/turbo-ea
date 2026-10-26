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

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.relation import Relation
from app.models.tech_standard import WAIVER_ACTIVE_STATUSES, StandardException, TechStandard
from app.services.card_read_scope import CardReadScope, visible_type_clause

VIOLATING_STATUSES = ("sunset", "prohibited")
REL_APP_TO_ITC = "relAppToITC"
REL_ITC_TO_TECHCAT = "relITCToTechCat"
#: The card types that are assessed against the technology-standards catalogue.
ASSESSED_TYPES = ("Application", "ITComponent")


def _brief(card: Card) -> dict:
    return {"id": str(card.id), "name": card.name, "type": card.type}


async def scan_standard_compliance(db: AsyncSession, *, read_scope: CardReadScope) -> dict:
    """Return violations of sunset/prohibited standards across the landscape.

    Only cards ``read_scope`` admits are reported, and a violation path that
    runs through a hidden category or component is cut rather than shown with
    a gap, so the scan never discloses a hidden card or relation.
    """
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
        ).where(StandardException.status.in_(WAIVER_ACTIVE_STATUSES))
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
    hidden = await read_scope.hidden_card_ids(db, card_ids, mode="module")

    violations: list[dict] = []
    seen: set[tuple[uuid.UUID, uuid.UUID]] = set()

    def add(card_id: uuid.UUID, cat_id: uuid.UUID, via: str, component: Card | None) -> None:
        if card_id in hidden or cat_id in hidden:
            return  # hidden from the reader (D-01 / D-30)
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
            if itc_id in hidden:
                continue  # the path runs through a hidden component
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


async def assess_standard_compliance(db: AsyncSession, *, read_scope: CardReadScope) -> dict:
    """Rule-based technology-standards compliance over the assessed population (D-33).

    The *assessed population* (I-8) is every ACTIVE Application / IT Component the
    viewer can read that reaches a ``TechCategory`` referenced by **any** tech
    standard (whatever its radar status), through the same chain the violation
    scan walks and with the same hidden-path cuts. A card is *compliant* (I-9)
    when it has no un-waived use of a ``sunset`` / ``prohibited`` standard — a
    waiver counts only while approved and unexpired, so an expired waiver is a
    violation (D-34). *Assessment coverage* (I-10) is the assessed population over
    all ACTIVE readable Application / IT Component cards, reported **beside**
    compliance and never multiplied into it (D-33).

    Returns ``{"status": "unavailable", "reason": {...}}`` (I-11) when no standard
    governs a category, the viewer cannot read one of the assessed types at all,
    or the assessed population is empty; otherwise ``status = "ok"`` with the
    compliant / violating / assessed counts, the coverage denominator, and the
    non-compliant uses for the drill-down. Nothing here discloses a card the
    viewer may not read — a hidden card, component or category cuts the path.
    """
    # Any-status standards govern the assessed categories; the sunset / prohibited
    # subset is what a card can violate.
    std_res = await db.execute(
        select(TechStandard).where(TechStandard.tech_category_id.is_not(None))
    )
    governing = list(std_res.scalars().all())
    if not governing:
        return {"status": "unavailable", "reason": {"code": "no_governed_category"}}

    # A type the viewer cannot read at all makes the population unreliable (I-11).
    if any(
        not read_scope.type_readable(t, mode="module") for t in (*ASSESSED_TYPES, "TechCategory")
    ):
        return {"status": "unavailable", "reason": {"code": "type_hidden"}}

    governed_cats = {s.tech_category_id for s in governing}
    violating_by_cat: dict[uuid.UUID, list[TechStandard]] = {}
    for s in governing:
        if s.status in VIOLATING_STATUSES:
            violating_by_cat.setdefault(s.tech_category_id, []).append(s)

    # ITComponents linked to a governed category, then Applications using them.
    itc_rel = await db.execute(
        select(Relation.source_id, Relation.target_id).where(
            Relation.type == REL_ITC_TO_TECHCAT,
            Relation.target_id.in_(governed_cats),
        )
    )
    itc_to_cats: dict[uuid.UUID, set[uuid.UUID]] = {}
    for itc_id, cat_id in itc_rel.all():
        itc_to_cats.setdefault(itc_id, set()).add(cat_id)

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

    # Approved, non-expired waivers keyed (standard_id, card_id) — expired omitted.
    exc_res = await db.execute(
        select(
            StandardException.standard_id, StandardException.card_id, StandardException.expiry_date
        ).where(StandardException.status.in_(WAIVER_ACTIVE_STATUSES))
    )
    today = date.today()
    waived: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for sid, cid, expiry in exc_res.all():
        if cid is not None and (expiry is None or expiry >= today):
            waived.add((sid, cid))

    card_ids = set(itc_to_cats) | set(app_to_itcs)
    cards_res = await db.execute(select(Card).where(Card.id.in_(card_ids), Card.status == "ACTIVE"))
    card_map: dict[uuid.UUID, Card] = {c.id: c for c in cards_res.scalars().all()}
    hidden = await read_scope.hidden_card_ids(db, card_ids | governed_cats, mode="module")

    assessed: set[uuid.UUID] = set()
    non_compliant: set[uuid.UUID] = set()
    violations: list[dict] = []
    seen: set[tuple[uuid.UUID, uuid.UUID]] = set()

    def consider(card_id: uuid.UUID, cat_id: uuid.UUID, via: str, component: Card | None) -> None:
        if card_id in hidden or cat_id in hidden:
            return  # a hidden card or category cuts the path (D-01 / D-30)
        card = card_map.get(card_id)
        if card is None or card.type not in ASSESSED_TYPES:
            return
        assessed.add(card_id)
        for std in violating_by_cat.get(cat_id, ()):
            if (std.id, card_id) in waived:
                continue
            non_compliant.add(card_id)
            key = (std.id, card_id)
            if key in seen:
                continue
            seen.add(key)
            violations.append(
                {
                    "card_id": str(card_id),
                    "card_name": card.name,
                    "card_type": card.type,
                    "standard_name": std.name,
                    "standard_status": std.status,
                    "via": via,
                    "component_name": component.name if component else None,
                }
            )

    for itc_id, cats in itc_to_cats.items():
        for cat_id in cats:
            consider(itc_id, cat_id, "component", None)
    for app_id, itcs in app_to_itcs.items():
        for itc_id in itcs:
            if itc_id in hidden:
                continue  # the path runs through a hidden component
            for cat_id in itc_to_cats.get(itc_id, ()):
                consider(app_id, cat_id, "application", card_map.get(itc_id))

    if not assessed:
        return {"status": "unavailable", "reason": {"code": "no_assessed_population"}}

    population = (
        await db.execute(
            select(func.count())
            .select_from(Card)
            .where(
                Card.status == "ACTIVE",
                Card.type.in_(ASSESSED_TYPES),
                visible_type_clause(Card),
                *read_scope.where(Card, mode="module"),
            )
        )
    ).scalar_one()

    compliant = len(assessed) - len(non_compliant)
    violations.sort(key=lambda v: v["card_name"].lower())
    return {
        "status": "ok",
        "assessed": len(assessed),
        "compliant": compliant,
        "violating": len(non_compliant),
        "population": population,
        "compliance_pct": round(compliant / len(assessed) * 100, 1),
        "coverage_pct": round(len(assessed) / population * 100, 1) if population else None,
        "violations": violations,
    }


async def standard_usage_persists(
    db: AsyncSession, standard_id: uuid.UUID, card_id: uuid.UUID | None
) -> bool | None:
    """Whether one card still uses one standard, by the scan's chain (I-32).

    The check remediation verification relies on: ``True`` while the card still
    reaches the standard's ``TechCategory`` (an IT Component directly, an
    Application through an IT Component); ``False`` once it no longer does, or
    the card is no longer ACTIVE (the scan no longer counts it); ``None`` when
    the scan cannot assess the pair — no card, a standard governing no
    category, or a card type the catalogue does not assess.

    Unscoped on purpose: it is an integrity check on a record the caller has
    already been allowed to read, and its answer is a single boolean that names
    no component, category or path.
    """
    if card_id is None:
        return None
    standard = await db.get(TechStandard, standard_id)
    if standard is None or standard.tech_category_id is None:
        return None
    card = await db.get(Card, card_id)
    if card is None or card.type not in ASSESSED_TYPES:
        return None
    if card.status != "ACTIVE":
        return False
    on_category = select(Relation.source_id).where(
        Relation.type == REL_ITC_TO_TECHCAT, Relation.target_id == standard.tech_category_id
    )
    if card.type == "ITComponent":
        query = on_category.where(Relation.source_id == card.id)
    else:
        query = select(Relation.id).where(
            Relation.type == REL_APP_TO_ITC,
            Relation.source_id == card.id,
            Relation.target_id.in_(on_category),
        )
    return (await db.scalar(query.limit(1))) is not None
