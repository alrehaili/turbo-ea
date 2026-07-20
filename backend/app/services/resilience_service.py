"""Resilience / Critical Service analysis (Wave 2 #6).

Maps critical business services down through their dependency chains
(service → process → app → integration → infrastructure → supplier) and surfaces:

* **Critical services** — cards flagged business-critical, with RTO/RPO and
  recovery tier read from the first-class ``rto`` / ``rpo`` / ``recoveryTier``
  Application fields (migration 158).
* **Single points of failure (SPOFs) / concentration risk** — nodes that two or
  more distinct critical services depend on (the more critical services reach a
  node, the higher its blast radius if it fails).
* **RTO/RPO coverage gaps** — critical services missing recovery objectives.

Reuses the same undirected dependency walk as ``impact_service`` so the three
change-governance views stay consistent. DORA / NIS2-aligned.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_type import CardType
from app.models.relation import Relation
from app.models.risk import Risk
from app.services.impact_service import CRITICAL_CRITICALITY

# Card-type keys treated as "suppliers" for supplier-concentration flags.
SUPPLIER_TYPE_KEYS = {"Provider"}


def _attr(card: Card, key: str) -> str | None:
    val = (card.attributes or {}).get(key)
    return str(val) if val else None


def _is_critical(card: Card) -> bool:
    crit = (card.attributes or {}).get("businessCriticality")
    return bool(crit and str(crit).lower() in CRITICAL_CRITICALITY)


async def gather_resilience(db: AsyncSession, *, depth: int = 4) -> dict:
    """Compute critical-service chains, SPOFs, and RTO/RPO gaps."""
    ct_res = await db.execute(select(CardType.key, CardType.category, CardType.is_hidden))
    layer_by_type: dict[str, str | None] = {}
    hidden: set[str] = set()
    for key, category, is_hidden in ct_res.all():
        layer_by_type[key] = category
        if is_hidden:
            hidden.add(key)

    cards_res = await db.execute(select(Card).where(Card.status == "ACTIVE"))
    card_map: dict[uuid.UUID, Card] = {
        c.id: c for c in cards_res.scalars().all() if c.type not in hidden
    }

    rels_res = await db.execute(select(Relation))
    adj: dict[uuid.UUID, set[uuid.UUID]] = {}
    for r in rels_res.scalars().all():
        if r.source_id in card_map and r.target_id in card_map:
            adj.setdefault(r.source_id, set()).add(r.target_id)
            adj.setdefault(r.target_id, set()).add(r.source_id)

    critical_roots = [c for c in card_map.values() if _is_critical(c)]

    # For each critical service, BFS its dependency neighbourhood to `depth`.
    concentration: dict[uuid.UUID, set[uuid.UUID]] = {}  # node -> {critical roots reaching it}
    critical_rows: list[dict] = []
    for root in sorted(critical_roots, key=lambda c: c.name.lower()):
        visited: set[uuid.UUID] = {root.id}
        frontier = {root.id}
        for _ in range(depth):
            nxt: set[uuid.UUID] = set()
            for nid in frontier:
                for nb in adj.get(nid, ()):
                    if nb not in visited:
                        visited.add(nb)
                        nxt.add(nb)
            frontier = nxt
        for nid in visited:
            if nid != root.id:
                concentration.setdefault(nid, set()).add(root.id)

        rto = _attr(root, "rto")
        rpo = _attr(root, "rpo")
        critical_rows.append(
            {
                "id": str(root.id),
                "name": root.name,
                "type": root.type,
                "criticality": _attr(root, "businessCriticality"),
                "rto": rto,
                "rpo": rpo,
                "recovery_tier": _attr(root, "recoveryTier"),
                "chain_size": len(visited) - 1,
            }
        )

    # SPOFs: nodes reached by >= 2 distinct critical services, ranked by reach.
    spofs: list[dict] = []
    for nid, roots in concentration.items():
        if len(roots) < 2:
            continue
        card = card_map[nid]
        spofs.append(
            {
                "id": str(nid),
                "name": card.name,
                "type": card.type,
                "layer": layer_by_type.get(card.type) or "Other",
                "is_supplier": card.type in SUPPLIER_TYPE_KEYS,
                "concentration": len(roots),
                "dependents": sorted(card_map[r].name for r in roots),
            }
        )
    spofs.sort(key=lambda s: (-s["concentration"], s["name"].lower()))

    # Already-promoted resilience risks, keyed by the affected card id, so the
    # UI can offer "Open risk R-xxxxxx" instead of "Create risk".
    risk_res = await db.execute(
        select(Risk.id, Risk.reference, Risk.source_ref).where(Risk.source_type == "resilience")
    )
    risk_by_card: dict[str, dict[str, str]] = {
        source_ref: {"risk_id": str(rid), "risk_reference": ref}
        for rid, ref, source_ref in risk_res.all()
        if source_ref
    }

    # RTO/RPO coverage gaps among critical services.
    gaps: list[dict] = []
    for row in critical_rows:
        missing = [k for k in ("rto", "rpo") if not row[k]]
        if missing:
            promoted = risk_by_card.get(row["id"])
            gaps.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "missing": missing,
                    "risk_id": promoted["risk_id"] if promoted else None,
                    "risk_reference": promoted["risk_reference"] if promoted else None,
                }
            )

    return {
        "summary": {
            "critical_services": len(critical_rows),
            "spof_count": len(spofs),
            "supplier_spofs": sum(1 for s in spofs if s["is_supplier"]),
            "rto_rpo_gaps": len(gaps),
        },
        "critical_services": critical_rows,
        "spofs": spofs,
        "rto_rpo_gaps": gaps,
    }
