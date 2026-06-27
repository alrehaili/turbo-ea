"""Strategy-to-Execution traversal.

Powers the **Executive Strategy Map** (``GET /reports/strategy-map``): one
traceable chain per strategic objective —

    Objective → (Business Capability) → Initiative → Application

assembled from the default metamodel relation types. PPM health/budget is read
opportunistically off the Initiative card's own attributes (``costBudget`` /
``costActual`` / lifecycle), so the view works with or without the PPM module.

KPIs/outcomes are surfaced opportunistically from the Objective's attributes
(any of ``kpi`` / ``outcome`` / ``targetMetric`` keys) until they become a
first-class metamodel concept — see plan.md item 1.2.

The traversal degrades gracefully on customised metamodels: it keys off the
built-in relation-type keys but simply yields empty branches when they are
absent rather than erroring.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.relation import Relation

# Built-in relation-type keys that wire the strategy chain together.
REL_OBJECTIVE_TO_BC = "relObjectiveToBC"  # Objective -> BusinessCapability
REL_INITIATIVE_TO_OBJECTIVE = "relInitiativeToObjective"  # Initiative -> Objective
REL_INITIATIVE_TO_BC = "relInitiativeToBC"  # Initiative -> BusinessCapability
REL_INITIATIVE_TO_APP = "relInitiativeToApp"  # Initiative -> Application

# Objective attribute keys we treat as a KPI/outcome, in priority order.
_KPI_KEYS = ("kpi", "outcome", "targetMetric", "successMetric")


def _kpi(card: Card) -> str | None:
    attrs = card.attributes or {}
    for key in _KPI_KEYS:
        val = attrs.get(key)
        if val:
            return str(val)
    return None


def _num_attr(card: Card, key: str) -> float | None:
    val = (card.attributes or {}).get(key)
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _lifecycle_status(card: Card) -> str | None:
    """Best-effort current lifecycle phase / status string for a card."""
    if card.status and card.status != "ACTIVE":
        return card.status
    lc = card.lifecycle or {}
    # Prefer an explicit phase marker if the metamodel sets one.
    for key in ("phase", "status", "current"):
        if lc.get(key):
            return str(lc[key])
    return None


async def gather_strategy_map(db: AsyncSession) -> dict:
    """Assemble the objective → capability → initiative → application chains."""
    cards_res = await db.execute(select(Card).where(Card.status == "ACTIVE"))
    card_map: dict[uuid.UUID, Card] = {c.id: c for c in cards_res.scalars().all()}

    rels_res = await db.execute(select(Relation))
    relations = list(rels_res.scalars().all())

    # Index relations by type for the directed lookups we need.
    # obj_bc[objective_id] -> {bc_id}
    obj_bc: dict[uuid.UUID, set[uuid.UUID]] = {}
    # init_obj[objective_id] -> {initiative_id}
    init_obj: dict[uuid.UUID, set[uuid.UUID]] = {}
    # init_bc[initiative_id] -> {bc_id}
    init_bc: dict[uuid.UUID, set[uuid.UUID]] = {}
    # init_app[initiative_id] -> {app_id}
    init_app: dict[uuid.UUID, set[uuid.UUID]] = {}

    for r in relations:
        if r.source_id not in card_map or r.target_id not in card_map:
            continue
        if r.type == REL_OBJECTIVE_TO_BC:
            obj_bc.setdefault(r.source_id, set()).add(r.target_id)
        elif r.type == REL_INITIATIVE_TO_OBJECTIVE:
            init_obj.setdefault(r.target_id, set()).add(r.source_id)
        elif r.type == REL_INITIATIVE_TO_BC:
            init_bc.setdefault(r.source_id, set()).add(r.target_id)
        elif r.type == REL_INITIATIVE_TO_APP:
            init_app.setdefault(r.source_id, set()).add(r.target_id)

    objectives = sorted(
        (c for c in card_map.values() if c.type == "Objective"),
        key=lambda c: c.name.lower(),
    )

    def _card_brief(cid: uuid.UUID) -> dict:
        c = card_map[cid]
        return {"id": str(cid), "name": c.name, "type": c.type, "subtype": c.subtype}

    out_objectives: list[dict] = []
    total_budget = 0.0
    total_actual = 0.0
    total_initiatives: set[uuid.UUID] = set()
    total_apps: set[uuid.UUID] = set()

    for obj in objectives:
        # Capabilities directly tied to the objective.
        cap_ids = set(obj_bc.get(obj.id, set()))

        # Initiatives delivering this objective + the apps/capabilities they touch.
        init_rows: list[dict] = []
        for init_id in sorted(init_obj.get(obj.id, set()), key=lambda i: card_map[i].name.lower()):
            init = card_map[init_id]
            total_initiatives.add(init_id)
            cap_ids |= init_bc.get(init_id, set())
            app_ids = sorted(init_app.get(init_id, set()), key=lambda a: card_map[a].name.lower())
            total_apps.update(app_ids)
            budget = _num_attr(init, "costBudget")
            actual = _num_attr(init, "costActual")
            if budget:
                total_budget += budget
            if actual:
                total_actual += actual
            init_rows.append(
                {
                    **_card_brief(init_id),
                    "status": _lifecycle_status(init),
                    "budget": budget,
                    "actual": actual,
                    "applications": [_card_brief(a) for a in app_ids],
                }
            )

        out_objectives.append(
            {
                **_card_brief(obj.id),
                "kpi": _kpi(obj),
                "capabilities": [
                    _card_brief(c) for c in sorted(cap_ids, key=lambda x: card_map[x].name.lower())
                ],
                "initiatives": init_rows,
            }
        )

    return {
        "objectives": out_objectives,
        "summary": {
            "objective_count": len(out_objectives),
            "initiative_count": len(total_initiatives),
            "application_count": len(total_apps),
            "total_budget": total_budget,
            "total_actual": total_actual,
        },
    }
