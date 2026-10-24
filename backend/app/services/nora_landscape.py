"""Plateau + segment resolution helpers ([FORK] — noraPlan.md WP5.4).

Pure-ish helpers that resolve a segment scope to its in-scope cards (grouped by
EA layer) and classify the landscape's lifecycle phases as of a plateau date.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_type import CardType
from app.models.nora_landscape import NoraSegment
from app.models.relation import Relation
from app.services.card_read_scope import CardReadScope, visible_type_clause

# Lifecycle phases, newest → oldest (same order as reports._current_lifecycle_phase).
_PHASES_DESC = ("endOfLife", "phaseOut", "active", "phaseIn", "plan")
_PHASES_ASC = ("plan", "phaseIn", "active", "phaseOut", "endOfLife")


def _parse(date_str: object) -> date | None:
    if not date_str:
        return None
    try:
        s = str(date_str)
        return (
            datetime.fromisoformat(s).date()
            if "T" in s
            else datetime.strptime(s, "%Y-%m-%d").date()
        )
    except (ValueError, TypeError):
        return None


def phase_as_of(lifecycle: dict | None, as_of: date) -> str | None:
    """Which lifecycle phase a card sits in as of ``as_of`` (not today).

    Returns the latest phase whose date is on or before ``as_of``; if every set
    date is still in the future relative to ``as_of``, returns the earliest set
    phase (the card is "planned" from the plateau's vantage point).
    """
    if not lifecycle:
        return None
    for phase in _PHASES_DESC:
        d = _parse(lifecycle.get(phase))
        if d and d <= as_of:
            return phase
    for phase in _PHASES_ASC:
        if lifecycle.get(phase):
            return phase
    return None


async def _type_categories(db: AsyncSession) -> dict[str, str | None]:
    rows = await db.execute(select(CardType.key, CardType.category))
    return {key: category for key, category in rows.all()}


def _brief(card: Card, categories: dict) -> dict:
    return {
        "id": str(card.id),
        "name": card.name,
        "type": card.type,
        "category": categories.get(card.type),
        "architecture_state": card.architecture_state or "current",
    }


async def get_segment_card_ids(
    db: AsyncSession, segment: NoraSegment, *, read_scope: CardReadScope
) -> set[uuid.UUID]:
    """Resolve a segment to its in-scope card IDs (without the display formatting).

    Scope = root + (descendants if enabled) + (related cards if enabled, narrowed
    to ``related_type_keys`` when set), **walked through readable cards only**:
    a card hidden from the reader neither appears nor bridges to the cards
    beyond it. Membership is therefore never derived from a hidden card's
    hierarchy or relations — a segment rooted at a hidden card is empty for
    that reader, and a readable card reachable only through a hidden child or
    hidden hierarchy member is left out (otherwise the set itself, and every
    count built on it, would disclose the hidden card's neighbourhood).
    """
    if segment.root_card_id is None:
        return set()

    async def readable(ids: set[uuid.UUID]) -> set[uuid.UUID]:
        if not ids:
            return set()
        return await read_scope.readable_card_ids(db, ids, mode="module")

    if not await readable({segment.root_card_id}):
        return set()

    # Hierarchy set (root + descendants) is always kept in full; related cards
    # may be narrowed by ``related_type_keys``.
    hierarchy_ids: set[uuid.UUID] = {segment.root_card_id}

    if segment.include_descendants:
        frontier = {segment.root_card_id}
        while frontier:
            rows = await db.execute(
                select(Card.id).where(Card.parent_id.in_(frontier), Card.status != "ARCHIVED")
            )
            children = await readable({cid for (cid,) in rows.all()} - hierarchy_ids)
            if not children:
                break
            hierarchy_ids |= children
            frontier = children

    related_ids: set[uuid.UUID] = set()
    if segment.include_related and hierarchy_ids:
        rel_rows = await db.execute(
            select(Relation.source_id, Relation.target_id).where(
                Relation.source_id.in_(hierarchy_ids) | Relation.target_id.in_(hierarchy_ids)
            )
        )
        for source_id, target_id in rel_rows.all():
            related_ids.add(source_id)
            related_ids.add(target_id)
        related_ids = await readable(related_ids - hierarchy_ids)

    scope_ids = hierarchy_ids | related_ids

    allowed = set(segment.related_type_keys or [])
    if allowed:
        # Narrow related cards to the allowed types; hierarchy cards stay.
        rows = await db.execute(
            select(Card.id).where(
                Card.id.in_(scope_ids),
                Card.status != "ARCHIVED",
                (Card.id.in_(hierarchy_ids)) | (Card.type.in_(allowed)),
            )
        )
        return {cid for (cid,) in rows.all()}

    rows = await db.execute(
        select(Card.id).where(Card.id.in_(scope_ids), Card.status != "ARCHIVED")
    )
    return {cid for (cid,) in rows.all()}


async def resolve_segment(
    db: AsyncSession, segment: NoraSegment, *, read_scope: CardReadScope
) -> dict:
    """Resolve a segment to its in-scope cards grouped by EA layer.

    Scope = root + (descendants if enabled) + (related cards if enabled, narrowed
    to ``related_type_keys`` when set). Returns ``{cards, layers, count}``,
    limited to the cards ``read_scope`` admits.
    """
    categories = await _type_categories(db)
    scope_ids = await get_segment_card_ids(db, segment, read_scope=read_scope)
    if not scope_ids:
        return {"cards": [], "layers": [], "count": 0}

    rows = await db.execute(
        select(Card).where(Card.id.in_(scope_ids), *read_scope.where(Card, mode="module"))
    )
    cards = list(rows.scalars().all())

    briefs = [_brief(c, categories) for c in cards]
    briefs.sort(key=lambda b: (b["category"] or "zz", b["name"]))

    # Group into layers preserving a stable EA order.
    layer_order = [
        "Business",
        "Beneficiary Experience",
        "Application",
        "Data",
        "Technology",
        "Security",
    ]
    by_cat: dict[str, list] = {}
    for b in briefs:
        by_cat.setdefault(b["category"] or "Other", []).append(b)
    ordered = [c for c in layer_order if c in by_cat] + [c for c in by_cat if c not in layer_order]
    layers = [{"category": c, "cards": by_cat[c]} for c in ordered]

    return {"cards": briefs, "layers": layers, "count": len(briefs)}


async def plateau_landscape(db: AsyncSession, as_of: date, *, read_scope: CardReadScope) -> dict:
    """Classify the non-archived landscape by lifecycle phase + architecture
    state as of a plateau date — over the cards ``read_scope`` admits, hidden
    card types left out (decision D-01)."""
    rows = await db.execute(
        select(Card.lifecycle, Card.architecture_state).where(
            Card.status != "ARCHIVED",
            *read_scope.where(Card, mode="module"),
            visible_type_clause(Card),
        )
    )
    phase_counts = {p: 0 for p in _PHASES_ASC}
    phase_counts["unknown"] = 0
    state_counts = {"current": 0, "transition": 0, "target": 0}
    total = 0
    for lifecycle, arch_state in rows.all():
        total += 1
        phase = phase_as_of(lifecycle, as_of) or "unknown"
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        st = arch_state or "current"
        state_counts[st] = state_counts.get(st, 0) + 1
    return {
        "as_of": as_of.isoformat(),
        "total": total,
        "phases": phase_counts,
        "states": state_counts,
    }
