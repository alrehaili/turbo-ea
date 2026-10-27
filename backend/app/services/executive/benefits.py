"""Benefits reporting (Phase 4 Batches 4.2 and 4.3; DECISION_LOG I-70..I-74).

Three kinds of financial value, never added together (C-06):

* **Planned** — the open benefits' planned amounts, by currency, status
  (planned / validated) and recurrence (one-time / annual, never summed); and,
  apart, the rationalization **run-rate forecast** (D-31), with the decisions a
  benefit already names taken out so nothing is counted twice (I-71).
* **Reported** — actuals reported for the fiscal year and awaiting Finance.
* **Finance-confirmed** — FIN-01 (cost saving and revenue) and FIN-02 (cost
  avoidance), each counted once per benefit whatever the number of initiatives.

Beside them: FIN-04 realisation rate, Finance's attribution (allocated direct,
allocated contributing, unallocated) and the governance link as counts only —
EA contribution is never money (D-14). Every amount is per currency (D-05); a
reader without ``costs.view`` gets counts and no amount.

**Outcomes** (D-43): KPI-measured benefits from the KPI's verified value for
the fiscal year against its ratified target (D-21 states); qualitative ones
from the business owner's latest assessment for the year, labelled
*assessed* — never verified. No amount anywhere.

**ROI** is not calculated (Batch 4.4; D-15, D-05 pending).

[FORK]
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benefit import (
    COST_AVOIDANCE,
    DECISION_RATIONALIZATION,
    DIRECT,
    MEASUREMENT_FINANCIAL,
    MEASUREMENT_KPI,
    MEASUREMENT_QUALITATIVE,
    OUTCOME_TYPES,
    STATUS_PLANNED,
    STATUS_VALIDATED,
    STATUS_WITHDRAWN,
    Benefit,
)
from app.models.benefit_actual import CONFIRMED, REPORTED
from app.models.card import Card
from app.models.kpi_measurement import STATUS_VERIFIED
from app.services import benefits as svc
from app.services import kpi_measurement_service as kms
from app.services.card_read_scope import CardReadScope
from app.services.executive.strategy import kpi_state

OK = "ok"
RESTRICTED = "restricted"
NOT_AVAILABLE = "not_available"

ROI_NOT_AVAILABLE = {
    "status": NOT_AVAILABLE,
    "reason": {"code": "decisions_pending", "batch": "4.4", "decisions": ["D-15", "D-05"]},
}

NOT_ASSESSED = "not_assessed"
KPI_UNAVAILABLE = "kpi_unavailable"

BENEFITS_PAGE = "/?tab=executive&page=benefits"


def _r(value: float) -> float:
    return round(value, 2)


async def load_visible(
    db: AsyncSession, read_scope: CardReadScope
) -> tuple[list[svc.BenefitBundle], set[uuid.UUID]]:
    """Every benefit the reader may see (I-66), with the readable card ids."""
    benefits = list((await db.execute(select(Benefit))).scalars().all())
    return await svc.visible_bundles(db, read_scope, await svc.load_bundles(db, benefits))


async def all_superseded_ids(db: AsyncSession) -> set[uuid.UUID]:
    """Rationalization decisions any benefit names (I-71), whatever its status
    or visibility: the forecast steps aside once the register holds the
    decision's benefit, so its value is never counted twice."""
    rows = await db.execute(
        select(Benefit.decision_id).where(
            Benefit.decision_kind == DECISION_RATIONALIZATION, Benefit.decision_id.is_not(None)
        )
    )
    return set(rows.scalars().all())


def _bucket() -> dict[str, Any]:
    return {"total": 0.0, "count": 0}


def _add(bucket: dict[str, Any], amount: float | None) -> None:
    bucket["count"] += 1
    bucket["total"] = _r(bucket["total"] + (amount or 0.0))


def financial_summary(
    bundles: list[svc.BenefitBundle],
    fy: int,
    readable: set[uuid.UUID],
    card_names: dict[uuid.UUID, str],
) -> dict[str, Any]:
    """Per-currency planned, reported and confirmed value for one fiscal year."""
    currencies: dict[str, dict[str, Any]] = {}

    def cur(code: str) -> dict[str, Any]:
        if code not in currencies:
            currencies[code] = {
                "planned": {
                    status: {rec: _bucket() for rec in ("one_time", "annual")}
                    for status in (STATUS_PLANNED, STATUS_VALIDATED)
                },
                "reported": _bucket(),
                "confirmed_cash": _bucket(),
                "confirmed_avoidance": _bucket(),
                "rate": {"confirmed": 0.0, "validated": 0.0, "benefits": 0},
                "attribution": {"direct": 0.0, "contributing": 0.0, "unallocated": 0.0},
                "by_initiative": defaultdict(lambda: {"direct": 0.0, "contributing": 0.0}),
                "governance": {"linked": 0, "not_linked": 0},
            }
        return currencies[code]

    for bundle in bundles:
        b = bundle.benefit
        if b.measurement != MEASUREMENT_FINANCIAL or not b.currency:
            continue
        c = cur(b.currency)
        if b.status in (STATUS_PLANNED, STATUS_VALIDATED) and b.planned_amount is not None:
            _add(c["planned"][b.status][b.recurrence or "one_time"], b.planned_amount)
        confirmed_fy = [a for a in bundle.actuals if a.fiscal_year == fy and a.status == CONFIRMED]
        for a in bundle.actuals:
            if a.fiscal_year == fy and a.status == REPORTED:
                _add(c["reported"], a.amount)
        for a in confirmed_fy:
            key = "confirmed_avoidance" if b.benefit_type == COST_AVOIDANCE else "confirmed_cash"
            _add(c[key], a.amount)
            allocated = 0.0
            for al in bundle.allocations.get(a.id, []):
                cls = "direct" if al.classification == DIRECT else "contributing"
                c["attribution"][cls] = _r(c["attribution"][cls] + al.amount)
                allocated += al.amount
                if al.card_id in readable:
                    row = c["by_initiative"][al.card_id]
                    row[cls] = _r(row[cls] + al.amount)
            c["attribution"]["unallocated"] = _r(
                c["attribution"]["unallocated"] + max(0.0, a.amount - allocated)
            )
            c["governance"]["linked" if b.decision_kind else "not_linked"] += 1
        # FIN-04: validated benefits expected this year (I-74); a benefit later
        # closed as not realised still counts — it was expected and missed.
        if (
            b.validated_at is not None
            and b.status != STATUS_WITHDRAWN
            and b.expected_fiscal_year == fy
            and b.planned_amount
        ):
            c["rate"]["validated"] = _r(c["rate"]["validated"] + b.planned_amount)
            c["rate"]["confirmed"] = _r(
                c["rate"]["confirmed"] + sum(a.amount for a in confirmed_fy)
            )
            c["rate"]["benefits"] += 1

    out = []
    for code in sorted(currencies):
        c = currencies[code]
        rate = c["rate"]
        c["rate"] = {
            **rate,
            "status": OK if rate["validated"] else NOT_AVAILABLE,
            "value": _r(rate["confirmed"] / rate["validated"] * 100) if rate["validated"] else None,
            "reason": None if rate["validated"] else {"code": "no_validated_benefits_due"},
        }
        c["by_initiative"] = sorted(
            (
                {
                    "id": str(cid),
                    "name": card_names.get(cid),
                    "path": f"/cards/{cid}",
                    **vals,
                    "total": _r(vals["direct"] + vals["contributing"]),
                }
                for cid, vals in c["by_initiative"].items()
            ),
            key=lambda r: (-r["total"], (r["name"] or "").lower()),
        )
        out.append({"currency": code, **c})
    return {"status": OK, "currencies": out, "mixed_currencies": len(out) > 1}


def counts(bundles: list[svc.BenefitBundle], fy: int) -> dict[str, Any]:
    """Counts only — what a reader without ``costs.view`` still sees."""
    by_status: dict[str, int] = defaultdict(int)
    by_type: dict[str, int] = defaultdict(int)
    reported = confirmed = 0
    for bundle in bundles:
        by_status[bundle.benefit.status] += 1
        by_type[bundle.benefit.benefit_type] += 1
        for a in bundle.actuals:
            if a.fiscal_year == fy:
                reported += a.status == REPORTED
                confirmed += a.status == CONFIRMED
    return {
        "benefits": len(bundles),
        "by_status": dict(by_status),
        "by_type": dict(by_type),
        "actuals_awaiting_finance": reported,
        "actuals_confirmed": confirmed,
        "without_governance_link": sum(1 for b in bundles if not b.benefit.decision_kind),
    }


async def outcomes(
    db: AsyncSession,
    bundles: list[svc.BenefitBundle],
    fy: int,
    readable: set[uuid.UUID],
) -> dict[str, Any]:
    """Non-financial outcomes for one fiscal year (D-43, I-72): KPI-verified
    and qualitatively assessed kept apart; productivity and other outcomes
    grouped apart. No amount."""
    period_key = f"FY{fy}"
    groups: dict[str, dict[str, Any]] = {
        t: {"kpi": defaultdict(int), "qualitative": defaultdict(int), "items": []}
        for t in OUTCOME_TYPES
    }
    for bundle in bundles:
        b = bundle.benefit
        if b.benefit_type not in OUTCOME_TYPES or b.status == STATUS_WITHDRAWN:
            continue
        group = groups[b.benefit_type]
        item: dict[str, Any] = {
            "id": str(b.id),
            "reference": b.reference,
            "title": b.title,
            "measurement": b.measurement,
            "status": b.status,
        }
        if b.measurement == MEASUREMENT_KPI:
            card = (
                await db.get(Card, b.kpi_card_id)
                if b.kpi_card_id and b.kpi_card_id in readable
                else None
            )
            if card is None or card.status != "ACTIVE":
                state, result, value, target = KPI_UNAVAILABLE, {}, None, None
            else:
                target = kms.target_state(card, await kms.latest_ratification(db, card.id))
                m = await kms.current_period_value(db, period_key, card_id=card.id)
                value = m.value if m is not None and m.status == STATUS_VERIFIED else None
                state, result = kpi_state(card, target, value)
                item["kpi"] = {"id": str(card.id), "name": card.name, "path": f"/cards/{card.id}"}
            item.update(
                state=state,
                evidence="verified_kpi",
                value=value,
                target=target,
                attainment=result.get("attainment"),
            )
            group["kpi"][state] += 1
        elif b.measurement == MEASUREMENT_QUALITATIVE:
            latest = next((r for r in bundle.assessments if r.fiscal_year == fy), None)
            state = latest.outcome if latest is not None else NOT_ASSESSED
            item.update(
                state=state,
                # D-43: assessed by the business owner, never verified.
                evidence="assessed",
                assessed_at=latest.assessed_at.isoformat() if latest is not None else None,
            )
            group["qualitative"][state] += 1
        group["items"].append(item)
    for group in groups.values():
        group["kpi"] = dict(group["kpi"])
        group["qualitative"] = dict(group["qualitative"])
        group["items"].sort(key=lambda i: i["reference"])
    return {"status": OK, "fiscal_year": fy, "groups": groups}


async def card_names(db: AsyncSession, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    rows = await db.execute(select(Card.id, Card.name).where(Card.id.in_(ids)))
    return dict(rows.all())


def confirmed_cash(bundles: list[svc.BenefitBundle], fy: int) -> dict[str, float]:
    """FIN-01 per currency: Finance-confirmed cost saving and revenue in ``fy``."""
    out: dict[str, float] = defaultdict(float)
    for bundle in bundles:
        b = bundle.benefit
        if b.measurement != MEASUREMENT_FINANCIAL or b.benefit_type == COST_AVOIDANCE:
            continue
        for a in bundle.actuals:
            if a.fiscal_year == fy and a.status == CONFIRMED and b.currency:
                out[b.currency] = _r(out[b.currency] + a.amount)
    return dict(out)
