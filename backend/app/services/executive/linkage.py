"""Executive indicators ↔ their KPI cards (D-26) and the on-target rule (D-21).

A registered calculation finds its KPI card through ``metricKey``. The card
supplies the definition the CEO reads beside the computed value — target,
target date, baseline, unit, direction, owner — and whether the target has
been ratified (D-17a). A card the viewer may not read does not exist for them,
so that tile is simply *not linked* (``CardReadScope``, "omit entirely").

``assess`` is the single on-target rule used by the tiles and by strategy
achievement: a value meets its target only when the target is **ratified** and
the KPI's ``direction`` says which way is better; otherwise nothing is judged.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import KPI_CARD_TYPE, Card
from app.models.stakeholder import Stakeholder
from app.models.user import User
from app.services import kpi_measurement_service as kms
from app.services.card_read_scope import CardReadScope, visible_type_clause
from app.services.executive.registry import METRICS
from app.services.kpi_metric_link import FIELD

#: The stakeholder role that names a KPI's owner (D-26: reuse ownership).
OWNER_ROLE = "responsible"
HIGHER = "higherIsBetter"
LOWER = "lowerIsBetter"

NOT_LINKED = {"status": "not_linked"}


def assess(value: float | None, target: dict[str, Any]) -> dict[str, Any]:
    """On/off target and attainment for one value against one target state.

    ``achieved`` is ``None`` unless the target is ratified, a value exists and
    the direction is known. ``attainment`` = (value − baseline) ÷ (target −
    baseline), capped 0–100 — shown per KPI only, never averaged (D-21).
    """
    out: dict[str, Any] = {"achieved": None, "attainment": None}
    tv, direction = target.get("value"), target.get("direction")
    if value is None or tv is None or target.get("status") != "ratified":
        return out
    if direction == HIGHER:
        out["achieved"] = value >= tv
    elif direction == LOWER:
        out["achieved"] = value <= tv
    else:
        return out
    baseline = target.get("baseline")
    if baseline is not None and tv != baseline:
        pct = (value - baseline) / (tv - baseline) * 100
        out["attainment"] = round(max(0.0, min(100.0, pct)), 1)
    return out


async def owner_names(db: AsyncSession, card_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
    """Display names of each KPI's ``responsible`` stakeholders (id + name only)."""
    if not card_ids:
        return {}
    rows = await db.execute(
        select(Stakeholder.card_id, User.display_name)
        .join(User, User.id == Stakeholder.user_id)
        .where(Stakeholder.card_id.in_(card_ids), Stakeholder.role == OWNER_ROLE)
        .order_by(User.display_name)
    )
    out: dict[uuid.UUID, list[str]] = {}
    for card_id, name in rows.all():
        out.setdefault(card_id, []).append(name)
    return out


async def linked_cards(db: AsyncSession, read_scope: CardReadScope) -> dict[str, dict[str, Any]]:
    """Per registered metric: its linked KPI card as this viewer may see it."""
    rows = await db.execute(
        select(Card).where(
            Card.type == KPI_CARD_TYPE,
            Card.status == "ACTIVE",
            Card.attributes[FIELD].astext.in_(list(METRICS)),
            visible_type_clause(Card),
            *read_scope.where(Card, mode="module"),
        )
    )
    # The query keeps only registered keys, so each key is a non-empty string.
    cards = {str((c.attributes or {}).get(FIELD)): c for c in rows.scalars().all()}
    owners = await owner_names(db, [c.id for c in cards.values()])
    out: dict[str, dict[str, Any]] = {}
    for key, card in cards.items():
        target = kms.target_state(card, await kms.latest_ratification(db, card.id))
        out[key] = {
            "card_id": str(card.id),
            "name": card.name,
            "target": target,
            "owners": owners.get(card.id, []),
        }
    return out


def apply_link(tile: dict[str, Any], link: dict[str, Any] | None) -> dict[str, Any]:
    """Fill a tile's target and owner blocks from its linked KPI card."""
    if link is None:
        return tile
    target = dict(link["target"])
    target["card_id"] = link["card_id"]
    target |= assess(tile.get("value"), target)
    tile["target"] = target
    tile["owner"] = (
        {"status": "ok", "name": ", ".join(link["owners"])}
        if link["owners"]
        else {"status": "unassigned"}
    )
    tile["kpi_card"] = {"id": link["card_id"], "name": link["name"]}
    return tile
