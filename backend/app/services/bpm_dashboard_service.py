"""BPM dashboard aggregation, shared by ``GET /reports/bpm/dashboard`` and the
executive dashboard.

The caller decides who may see it and passes the read-scope predicate; this
module only counts what that predicate admits.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.process_flow_version import ProcessFlowVersion


def summarize_processes(
    processes: Sequence[Card], published_ids: Iterable[uuid.UUID]
) -> dict[str, Any]:
    """KPI rollup over already-loaded BusinessProcess cards."""
    by_process_type: dict[str, int] = {}
    by_maturity: dict[str, int] = {}
    by_automation: dict[str, int] = {}
    by_risk: dict[str, int] = {}
    top_risk: list[dict] = []

    for p in processes:
        attrs = p.attributes or {}
        pt = attrs.get("processType", "unknown")
        by_process_type[pt] = by_process_type.get(pt, 0) + 1
        mat = attrs.get("maturity", "unknown")
        by_maturity[mat] = by_maturity.get(mat, 0) + 1
        auto = attrs.get("automationLevel", "unknown")
        by_automation[auto] = by_automation.get(auto, 0) + 1
        risk = attrs.get("riskLevel", "unknown")
        by_risk[risk] = by_risk.get(risk, 0) + 1
        if risk in ("high", "critical"):
            top_risk.append({"id": str(p.id), "name": p.name, "risk": risk, "maturity": mat})

    risk_order = {"critical": 0, "high": 1}
    top_risk.sort(key=lambda x: risk_order.get(x["risk"], 99))

    total = len(processes)
    # Coverage of the processes counted above, not of every process there is.
    process_ids = {p.id for p in processes}
    with_diagram = len(process_ids & set(published_ids))

    return {
        "total_processes": total,
        "by_process_type": by_process_type,
        "by_maturity": by_maturity,
        "by_automation": by_automation,
        "by_risk": by_risk,
        "top_risk_processes": top_risk[:10],
        "diagram_coverage": {
            "with_diagram": with_diagram,
            "total": total,
            "percentage": round(with_diagram / total * 100, 1) if total else 0,
        },
    }


async def build_bpm_dashboard(db: AsyncSession, readable: tuple) -> dict[str, Any]:
    """Load the readable ACTIVE processes and their published flows, then summarize."""
    result = await db.execute(
        select(Card).where(
            Card.type == "BusinessProcess",
            Card.status == "ACTIVE",
            *readable,
        )
    )
    processes = result.scalars().all()
    diag_result = await db.execute(
        select(ProcessFlowVersion.process_id)
        .where(ProcessFlowVersion.status == "published")
        .distinct()
    )
    return summarize_processes(processes, (pid for (pid,) in diag_result.all()))
