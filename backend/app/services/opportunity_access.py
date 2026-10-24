"""Which improvement opportunities a reader may see (decision S-12, D-30).

An improvement opportunity is a governance record that may link cards: its
``card_ids``, an ``initiative_id`` and a ``journey_card_id``. Under D-30 a
record that stays meaningful once its hidden links are removed is shown with
those links *redacted*; a record that cannot is *omitted*.

An opportunity is **independently accessible** when it links no card at all,
or when at least one card it links is readable: the reader then has a card of
their own to anchor it to, and every hidden link is redacted. An opportunity
whose every linked card is hidden is about hidden cards only — what is left
after redaction is a title and description describing them — so it is omitted
from lists, 404 on update, and left out of every count (the opportunity list,
realized value, the NORA dashboard). The row itself is never touched.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.improvement_opportunity import (
    ImprovementOpportunity,
    ImprovementOpportunityCard,
)
from app.services.card_read_scope import CardReadScope


async def linked_card_ids(
    db: AsyncSession, opportunities: Iterable[ImprovementOpportunity]
) -> dict[uuid.UUID, set[uuid.UUID]]:
    """Every card each opportunity references: linked cards, initiative, journey."""
    opps = list(opportunities)
    out: dict[uuid.UUID, set[uuid.UUID]] = {
        o.id: {c for c in (o.initiative_id, o.journey_card_id) if c} for o in opps
    }
    if not opps:
        return out
    rows = await db.execute(
        select(ImprovementOpportunityCard.opportunity_id, ImprovementOpportunityCard.card_id).where(
            ImprovementOpportunityCard.opportunity_id.in_(list(out))
        )
    )
    for opp_id, card_id in rows.all():
        out[opp_id].add(card_id)
    return out


async def inaccessible_opportunity_ids(
    db: AsyncSession,
    read_scope: CardReadScope,
    opportunities: Iterable[ImprovementOpportunity],
) -> set[uuid.UUID]:
    """Ids of the opportunities that are *not* independently accessible."""
    if read_scope.is_unrestricted(mode="module"):
        return set()
    refs = await linked_card_ids(db, opportunities)
    every = set().union(*refs.values()) if refs else set()
    hidden = await read_scope.hidden_card_ids(db, every, mode="module")
    if not hidden:
        return set()
    return {oid for oid, ids in refs.items() if ids and ids <= hidden}


async def accessible_opportunities(
    db: AsyncSession,
    read_scope: CardReadScope,
    opportunities: Iterable[ImprovementOpportunity],
) -> list[ImprovementOpportunity]:
    """``opportunities`` minus those that are not independently accessible."""
    opps = list(opportunities)
    drop = await inaccessible_opportunity_ids(db, read_scope, opps)
    return [o for o in opps if o.id not in drop]
