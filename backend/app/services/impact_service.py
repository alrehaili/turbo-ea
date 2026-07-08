"""Reusable change-impact / blast-radius engine.

This is the shared traversal that powers:

* the **Change Impact Workbench** (``GET /reports/impact``) — "what breaks if I
  replace / retire / modify card X?",
* the **Resilience / Critical Service** view (single-point-of-failure walk),
* and the **Scenario Planning** diff/impact rollup.

The design goal is *one* blast-radius walk so the three features stay
consistent. It performs a breadth-first traversal of the relation graph from a
center card out to ``depth`` hops, records each affected card's hop distance and
shortest name-path back to the center, groups results by EA layer
(``card_types.category``), weights them by ``businessCriticality``, and joins in
the risks and initiatives that hang off the affected set.

The walk is **undirected** (mirroring ``/reports/dependencies``): a change to a
card can ripple to both the things it depends on and the things that depend on
it. ``change_type`` is carried through for the caller's headline/messaging and
for future direction-aware refinement, but does not currently prune the walk.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_type import CardType
from app.models.relation import Relation
from app.models.relation_type import RelationType
from app.models.risk import Risk, RiskCard

# Canonical EA-layer ordering used to sort grouped output. Layers not in this
# list (custom card-type categories) sort last, alphabetically.
LAYER_ORDER = [
    "Business",
    "Beneficiary Experience",
    "Application",
    "Data",
    "Technology",
    "Security",
]

# Card-type keys treated as "initiatives / delivery" for the dedicated rollup.
INITIATIVE_TYPE_KEYS = {"Initiative"}

# businessCriticality option keys considered "critical" for critical-path flags.
CRITICAL_CRITICALITY = {"mission_critical", "business_critical", "critical", "high"}


def _criticality(card: Card) -> str | None:
    """Pull the ``businessCriticality`` attribute off a card, if present."""
    attrs = card.attributes or {}
    val = attrs.get("businessCriticality")
    return str(val) if val else None


async def gather_impact(
    db: AsyncSession,
    center_id: uuid.UUID,
    *,
    depth: int = 2,
    change_type: str = "modify",
) -> dict:
    """Compute the blast radius of a change to ``center_id``.

    Returns a JSON-serialisable dict (see module docstring for the shape).
    Raises ``ValueError`` if the center card does not exist or is not active.
    """
    # --- Load the center card -------------------------------------------------
    center_res = await db.execute(select(Card).where(Card.id == center_id))
    center = center_res.scalar_one_or_none()
    if center is None or center.status != "ACTIVE":
        raise ValueError("center card not found or not active")

    # --- Load layer map (card type key -> category/layer) --------------------
    ct_res = await db.execute(select(CardType.key, CardType.category, CardType.is_hidden))
    layer_by_type: dict[str, str | None] = {}
    hidden_types: set[str] = set()
    for key, category, is_hidden in ct_res.all():
        layer_by_type[key] = category
        if is_hidden:
            hidden_types.add(key)

    # --- Load active, non-hidden cards into a map ----------------------------
    cards_res = await db.execute(select(Card).where(Card.status == "ACTIVE"))
    card_map: dict[uuid.UUID, Card] = {
        c.id: c for c in cards_res.scalars().all() if c.type not in hidden_types
    }

    # --- Load relations + their labels ---------------------------------------
    rels_res = await db.execute(select(Relation))
    relations = list(rels_res.scalars().all())

    rt_res = await db.execute(
        select(RelationType.key, RelationType.label, RelationType.reverse_label)
    )
    rel_labels = {r[0]: {"label": r[1], "reverse_label": r[2]} for r in rt_res.all()}

    # Build undirected adjacency, recording the relation label seen on the edge.
    # adj[id] -> list of (neighbor_id, label)
    adj: dict[uuid.UUID, list[tuple[uuid.UUID, str]]] = {}
    for r in relations:
        if r.source_id not in card_map or r.target_id not in card_map:
            continue
        info = rel_labels.get(r.type, {})
        fwd = info.get("label") or r.type
        rev = info.get("reverse_label") or fwd
        adj.setdefault(r.source_id, []).append((r.target_id, fwd))
        adj.setdefault(r.target_id, []).append((r.source_id, rev))

    # --- BFS to `depth`, recording hop distance + shortest name-path ---------
    # path holds the chain of card names from the center to the node (exclusive
    # of the center itself), so the UI can render "App A → Interface B → ...".
    visited: dict[uuid.UUID, dict] = {center_id: {"depth": 0, "path": [], "relation_label": None}}
    frontier = [center_id]
    for hop in range(1, depth + 1):
        next_frontier: list[uuid.UUID] = []
        for nid in frontier:
            for neighbor, label in adj.get(nid, []):
                if neighbor in visited:
                    continue
                parent_path = visited[nid]["path"]
                neighbor_card = card_map.get(neighbor)
                if neighbor_card is None:
                    continue
                visited[neighbor] = {
                    "depth": hop,
                    "path": parent_path + [neighbor_card.name],
                    "relation_label": label,
                }
                next_frontier.append(neighbor)
        frontier = next_frontier

    affected_ids = [cid for cid in visited if cid != center_id]

    # --- Build affected-card rows + group by layer ---------------------------
    affected_rows: list[dict] = []
    by_layer_map: dict[str, list[dict]] = {}
    by_criticality: dict[str, int] = {}
    critical_count = 0
    initiative_rows: list[dict] = []

    for cid in affected_ids:
        card = card_map[cid]
        meta = visited[cid]
        layer = layer_by_type.get(card.type) or "Other"
        crit = _criticality(card)
        is_critical = bool(crit and crit.lower() in CRITICAL_CRITICALITY)
        if is_critical:
            critical_count += 1
        if crit:
            by_criticality[crit] = by_criticality.get(crit, 0) + 1

        row = {
            "id": str(cid),
            "name": card.name,
            "type": card.type,
            "layer": layer,
            "depth": meta["depth"],
            "path": meta["path"],
            "relation_label": meta["relation_label"],
            "criticality": crit,
            "is_critical": is_critical,
        }
        affected_rows.append(row)
        by_layer_map.setdefault(layer, []).append(row)

        if card.type in INITIATIVE_TYPE_KEYS:
            initiative_rows.append(
                {
                    "id": str(cid),
                    "name": card.name,
                    "subtype": card.subtype,
                    "depth": meta["depth"],
                }
            )

    # Sort affected rows: nearest first, then critical first, then name.
    affected_rows.sort(key=lambda r: (r["depth"], not r["is_critical"], r["name"].lower()))

    # --- Risks linked to any affected card (or the center) -------------------
    risk_scope_ids = set(affected_ids) | {center_id}
    risk_rows: list[dict] = []
    if risk_scope_ids:
        rc_res = await db.execute(
            select(RiskCard.risk_id, RiskCard.card_id).where(RiskCard.card_id.in_(risk_scope_ids))
        )
        risk_to_cards: dict[uuid.UUID, list[uuid.UUID]] = {}
        for risk_id, card_id in rc_res.all():
            risk_to_cards.setdefault(risk_id, []).append(card_id)

        if risk_to_cards:
            risks_res = await db.execute(select(Risk).where(Risk.id.in_(risk_to_cards.keys())))
            for risk in risks_res.scalars().all():
                via_ids = risk_to_cards.get(risk.id, [])
                via_names = [card_map[c].name for c in via_ids if c in card_map]
                risk_rows.append(
                    {
                        "id": str(risk.id),
                        "reference": risk.reference,
                        "title": risk.title,
                        "status": risk.status,
                        "level": risk.residual_level or risk.initial_level,
                        "via_cards": via_names,
                    }
                )
    risk_rows.sort(key=lambda r: r["reference"])

    # --- Assemble grouped-by-layer output in canonical layer order -----------
    def _layer_sort_key(layer: str) -> tuple[int, str]:
        try:
            return (LAYER_ORDER.index(layer), "")
        except ValueError:
            return (len(LAYER_ORDER), layer.lower())

    by_layer = [
        {"layer": layer, "count": len(rows), "cards": rows}
        for layer, rows in sorted(by_layer_map.items(), key=lambda kv: _layer_sort_key(kv[0]))
    ]

    return {
        "center": {
            "id": str(center.id),
            "name": center.name,
            "type": center.type,
            "subtype": center.subtype,
            "layer": layer_by_type.get(center.type) or "Other",
            "criticality": _criticality(center),
        },
        "change_type": change_type,
        "depth": depth,
        "summary": {
            "total_affected": len(affected_ids),
            "by_layer": {row["layer"]: row["count"] for row in by_layer},
            "by_criticality": by_criticality,
            "critical_count": critical_count,
            "risk_count": len(risk_rows),
            "initiative_count": len(initiative_rows),
        },
        "affected": affected_rows,
        "by_layer": by_layer,
        "risks": risk_rows,
        "initiatives": sorted(initiative_rows, key=lambda r: (r["depth"], r["name"].lower())),
    }
