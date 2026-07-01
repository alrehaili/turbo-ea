"""Data Architecture — Data Domain & Flow Map (Wave 4 #10).

Builds a data-centric view over the existing metamodel: for each Data Object
(the data entity), which Applications produce/consume it, which Interfaces carry
it, and which IT Components store it. A "data domain" grouping is read
opportunistically from the Data Object's ``dataDomain`` attribute (or its parent
card) until Data Domain / Data Product become first-class card types.

No schema change — traverses the built-in ``relAppToDataObj`` /
``relInterfaceToDataObj`` (+ app→interface, app→ITC) relations. The
OpenMetadata connector that would *populate* these cards is a separate
integration tracked in plan.md #10.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_type import CardType
from app.models.relation import Relation

DATA_OBJECT_TYPE = "DataObject"
APP_TYPE = "Application"
INTERFACE_TYPE = "Interface"
ITC_TYPE = "ITComponent"


def _domain(card: Card) -> str | None:
    val = (card.attributes or {}).get("dataDomain")
    return str(val) if val else None


async def gather_data_flow(db: AsyncSession) -> dict:
    """For each Data Object, resolve the apps/interfaces/components around it."""
    ct_res = await db.execute(select(CardType.key, CardType.is_hidden))
    hidden = {k for k, h in ct_res.all() if h}

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

    data_objects = sorted(
        (c for c in card_map.values() if c.type == DATA_OBJECT_TYPE),
        key=lambda c: c.name.lower(),
    )

    def brief(cid: uuid.UUID) -> dict:
        c = card_map[cid]
        return {"id": str(cid), "name": c.name, "type": c.type}

    rows: list[dict] = []
    by_domain: dict[str, int] = {}
    orphan_count = 0
    apps_touching: set[uuid.UUID] = set()

    for do in data_objects:
        neighbours = adj.get(do.id, set())
        apps = [n for n in neighbours if card_map[n].type == APP_TYPE]
        interfaces = [n for n in neighbours if card_map[n].type == INTERFACE_TYPE]
        components = [n for n in neighbours if card_map[n].type == ITC_TYPE]
        apps_touching.update(apps)
        if not apps and not interfaces:
            orphan_count += 1
        domain = _domain(do) or "Ungrouped"
        by_domain[domain] = by_domain.get(domain, 0) + 1
        rows.append(
            {
                "id": str(do.id),
                "name": do.name,
                "domain": domain,
                "applications": [brief(a) for a in sorted(apps, key=lambda x: card_map[x].name)],
                "interfaces": [
                    brief(i) for i in sorted(interfaces, key=lambda x: card_map[x].name)
                ],
                "components": [
                    brief(c) for c in sorted(components, key=lambda x: card_map[x].name)
                ],
                "is_orphan": not apps and not interfaces,
            }
        )

    return {
        "summary": {
            "data_objects": len(data_objects),
            "domains": len(by_domain),
            "apps_touching_data": len(apps_touching),
            "orphans": orphan_count,
        },
        "by_domain": [{"domain": k, "count": v} for k, v in sorted(by_domain.items())],
        "data_objects": rows,
    }
