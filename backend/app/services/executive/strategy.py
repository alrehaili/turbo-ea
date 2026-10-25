"""Strategy achievement (TR-01, decision D-21): strategic outcomes, measured.

Two things the CEO must never see blended:

* **Outcome achievement** — of the strategic KPIs, how many are on target.
  A *strategic KPI* is an ACTIVE KPI card linked (``relObjectiveToKPI``) to an
  ACTIVE Objective whose ``objectiveType`` is ``strategic``. It is *assessable*
  when its definition is approved (card approval, I-6), its target is
  **ratified** (D-17a) and its ``direction`` is set; it is *measured* when it
  also has a **verified** value for the period. The headline is "X of Y
  measured on target", with coverage (measured of linked) beside it. No
  weights exist, so there is no index and no average (D-21).
* **Execution** — delivery health of the initiatives supporting the strategic
  objectives (``relInitiativeToObjective``), the same four-state rule as TR-03.

``Objective.progress`` is self-reported and is not read. Every card is the
viewer's ``CardReadScope`` with hidden types left out.

Like TR-03, the population comes from today's links (they keep no history), so
achievement is computed for the current period only; a finished period is
*historical data unavailable* (H-1).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import KPI_CARD_TYPE, Card
from app.models.kpi_measurement import STATUS_VERIFIED
from app.models.relation import Relation
from app.services import executive_dashboard as exe
from app.services import kpi_measurement_service as kms
from app.services import ppm_portfolio_service as portfolio
from app.services.card_read_scope import CardReadScope, visible_type_clause
from app.services.executive.linkage import assess, owner_names
from app.services.executive.periods import Period

REL_OBJECTIVE_KPI = "relObjectiveToKPI"
REL_OBJECTIVE_PILLAR = "relObjectiveToPillar"
REL_INITIATIVE_OBJECTIVE = "relInitiativeToObjective"
STRATEGIC = "strategic"

# Per-KPI states, worst evidence first.
NOT_APPROVED = "definition_not_approved"
NO_TARGET = "no_ratified_target"
NO_DIRECTION = "no_direction"
NOT_MEASURED = "not_measured"
ON_TARGET = "on_target"
OFF_TARGET = "off_target"


async def _readable(
    db: AsyncSession, read_scope: CardReadScope, type_key: str, ids: set | None = None
) -> list[Card]:
    stmt = select(Card).where(
        Card.type == type_key,
        Card.status == "ACTIVE",
        visible_type_clause(Card),
        *read_scope.where(Card, mode="module"),
    )
    if ids is not None:
        if not ids:
            return []
        stmt = stmt.where(Card.id.in_(ids))
    return list((await db.execute(stmt)).scalars().all())


async def _links(
    db: AsyncSession, rel_type: str, *, source_ids=None, target_ids=None
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    stmt = select(Relation.source_id, Relation.target_id).where(Relation.type == rel_type)
    if source_ids is not None:
        stmt = stmt.where(Relation.source_id.in_(source_ids))
    if target_ids is not None:
        stmt = stmt.where(Relation.target_id.in_(target_ids))
    return [(s, t) for s, t in (await db.execute(stmt)).all()]


def kpi_state(card: Card, target: dict[str, Any], value: float | None) -> tuple[str, dict]:
    """One strategic KPI's state for the period, from evidence only."""
    if card.approval_status != "APPROVED":
        return NOT_APPROVED, {}
    if target.get("status") != "ratified":
        return NO_TARGET, {}
    if target.get("direction") not in ("higherIsBetter", "lowerIsBetter"):
        return NO_DIRECTION, {}
    if value is None:
        return NOT_MEASURED, {}
    result = assess(value, target)
    return (ON_TARGET if result["achieved"] else OFF_TARGET), result


def _rollup(kpi_ids: list[uuid.UUID], states: dict[uuid.UUID, str]) -> dict[str, int]:
    measured = [k for k in kpi_ids if states.get(k) in (ON_TARGET, OFF_TARGET)]
    return {
        "linked": len(kpi_ids),
        "measured": len(measured),
        "on_target": sum(1 for k in measured if states[k] == ON_TARGET),
    }


async def strategy_achievement(
    db: AsyncSession, read_scope: CardReadScope, period: Period, general: dict, today: date
) -> dict[str, Any]:
    """Outcome achievement with objective and pillar drill-down, and execution apart."""
    objectives = [
        o
        for o in await _readable(db, read_scope, "Objective")
        if (o.attributes or {}).get("objectiveType") == STRATEGIC
    ]
    obj_ids = {o.id for o in objectives}
    obj_kpi = await _links(db, REL_OBJECTIVE_KPI, source_ids=obj_ids) if obj_ids else []
    kpis = {
        k.id: k for k in await _readable(db, read_scope, KPI_CARD_TYPE, {t for _, t in obj_kpi})
    }
    kpis_by_objective: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for o, k in obj_kpi:
        if k in kpis and k not in kpis_by_objective[o]:
            kpis_by_objective[o].append(k)

    owners = await owner_names(db, list(kpis))
    states: dict[uuid.UUID, str] = {}
    kpi_rows: dict[uuid.UUID, dict[str, Any]] = {}
    for kid, card in kpis.items():
        target = kms.target_state(card, await kms.latest_ratification(db, kid))
        m = await kms.current_period_value(db, period.key, card_id=kid)
        value = m.value if m is not None and m.status == STATUS_VERIFIED else None
        state, result = kpi_state(card, target, value)
        states[kid] = state
        kpi_rows[kid] = {
            "id": str(kid),
            "name": card.name,
            "state": state,
            "value": value,
            "unit": target.get("unit"),
            "target": target,
            "attainment": result.get("attainment"),
            "measurement_status": m.status if m is not None else None,
            "owners": owners.get(kid, []),
            "path": f"/cards/{kid}",
        }

    pillar_links = await _links(db, REL_OBJECTIVE_PILLAR, source_ids=obj_ids) if obj_ids else []
    pillars = {
        p.id: p for p in await _readable(db, read_scope, "Pillar", {t for _, t in pillar_links})
    }
    objectives_by_pillar: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for o, p in pillar_links:
        if p in pillars and o not in objectives_by_pillar[p]:
            objectives_by_pillar[p].append(o)

    objective_rows = []
    for obj in sorted(objectives, key=lambda c: c.name.lower()):
        ids = kpis_by_objective.get(obj.id, [])
        objective_rows.append(
            {
                "id": str(obj.id),
                "name": obj.name,
                "path": f"/cards/{obj.id}",
                **_rollup(ids, states),
                "kpis": [kpi_rows[k] for k in ids],
            }
        )
    pillar_rows = []
    for pid, pillar in sorted(pillars.items(), key=lambda kv: kv[1].name.lower()):
        ids = sorted({k for o in objectives_by_pillar[pid] for k in kpis_by_objective.get(o, [])})
        pillar_rows.append(
            {
                "id": str(pid),
                "name": pillar.name,
                "path": f"/cards/{pid}",
                "objectives": [str(o) for o in objectives_by_pillar[pid]],
                **_rollup(ids, states),
            }
        )

    totals: dict[str, Any] = dict(_rollup(list(kpis), states))
    totals["assessable"] = sum(
        1 for s in states.values() if s in (NOT_MEASURED, ON_TARGET, OFF_TARGET)
    )
    totals["strategic_objectives"] = len(objectives)
    totals["by_state"] = {
        s: sum(1 for v in states.values() if v == s)
        for s in (NOT_APPROVED, NO_TARGET, NO_DIRECTION, NOT_MEASURED, ON_TARGET, OFF_TARGET)
    }

    # Execution, kept apart: delivery health of initiatives supporting them.
    init_links = await _links(db, REL_INITIATIVE_OBJECTIVE, target_ids=obj_ids) if obj_ids else []
    supporting = {s for s, _ in init_links}
    initiatives = [
        c for c in await exe.load_visible_initiatives(db, read_scope) if c.id in supporting
    ]
    latest = (
        await portfolio.latest_reports(db, [c.id for c in initiatives], as_of=today)
        if bool(general.get("ppmEnabled", False))
        else None
    )
    execution = exe.summarize_delivery_health(
        initiatives, latest, today=today, stale=exe.staleness_days(general)
    )

    return {
        "period": period.to_dict(),
        "totals": totals,
        "objectives": objective_rows,
        "pillars": pillar_rows,
        "unlinked_objectives": sum(1 for o in objectives if not kpis_by_objective.get(o.id)),
        "execution": {
            "initiatives": len(initiatives),
            "on_track_pct": execution["on_track_pct"],
            "states": execution["states"],
            "coverage": execution["coverage"],
            "source": execution["source"],
        },
    }
