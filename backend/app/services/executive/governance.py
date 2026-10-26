"""EA governance effectiveness — Batch 3.1 (DECISION_LOG.md §3.1).

Three classes, **never mixed** (GOVERNANCE_MEASUREMENT_MODEL.md §1):

* **Activity** — governance happened. ADRs signed in the period; ARB reviews by
  their latest decision date (``decided_at`` is overwritten on each change, so
  the counts are labelled accordingly and deferred reviews are counted apart,
  never as decisions — I-12); standard exceptions by their current state. No
  value claim is attached to any of it.
* **Effectiveness** — governance was acted on. GOV-03 rule-based technology
  standards compliance (I-9) and assessment coverage (I-10) as **two separate
  figures**; GOV-04 / GOV-05 / GOV-07 are Not Available with the decision that
  blocks them (they arrive in later batches).
* **Impact** — governed work performs better. Architecture risks, governed vs
  ungoverned delivery (GOV-09) and business value are Not Available with their
  reason until their batch or Phase 4 lands.

Anything without a defensible calculation is Not Available **with its reason**,
never zero (C-04). Governance records about hidden cards are omitted exactly as
their own modules do (D-30), and every card population is the caller's
module-mode ``CardReadScope`` with hidden types excluded (D-01).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.tech_standard import StandardException
from app.services.card_read_scope import CardReadScope
from app.services.executive import kpis, linkage
from app.services.executive.periods import Period
from app.services.tech_standards_scan import assess_standard_compliance

#: ARB outcomes that count as a decision; deferral is reported apart (I-12).
ARB_DECISION_STATUSES = ("approved", "rejected")
ARB_DEFERRED = "deferred"


def _not_available(reason: dict[str, Any]) -> dict[str, Any]:
    return {"status": "not_available", "reason": reason}


def _in_period(moment, period: Period) -> bool:
    """True when a timestamp falls inside ``period`` (``end`` is exclusive)."""
    if moment is None:
        return False
    day = moment.date() if hasattr(moment, "date") else moment
    return period.start <= day < period.end


async def _activity(db: AsyncSession, read_scope: CardReadScope, period: Period) -> dict[str, Any]:
    """Governance that happened in the period — counts only, no value claim."""
    # ADRs signed in the period. An ADR is a multi-card record kept whole (D-30),
    # so no card scope is applied — as on the decisions page.
    adr_rows = await db.execute(
        select(ArchitectureDecision.signed_at).where(
            ArchitectureDecision.status == "signed",
            ArchitectureDecision.signed_at.is_not(None),
        )
    )
    adrs_signed = sum(1 for (signed_at,) in adr_rows.all() if _in_period(signed_at, period))

    # ARB reviews by their latest decision date (I-12). A review of a hidden
    # subject card does not exist for the reader (D-30).
    arb_rows = await db.execute(select(ArbReview).where(ArbReview.decided_at.is_not(None)))
    reviews = [r for r in arb_rows.scalars().all() if _in_period(r.decided_at, period)]
    readable = await read_scope.readable_card_ids(
        db, {r.subject_card_id for r in reviews if r.subject_card_id}, mode="module"
    )
    reviews = [r for r in reviews if not r.subject_card_id or r.subject_card_id in readable]
    arb = {"approved": 0, "rejected": 0, "deferred": 0}
    for r in reviews:
        if r.status in ARB_DECISION_STATUSES:
            arb[r.status] += 1
        elif r.status == ARB_DEFERRED:
            arb["deferred"] += 1

    # Exceptions by their current state (I-12): the lifecycle has no recorded
    # history yet, so this is a present-state snapshot, not a period figure.
    exc_rows = await db.execute(select(StandardException))
    exceptions = list(exc_rows.scalars().all())
    hidden = await read_scope.hidden_card_ids(
        db, {e.card_id for e in exceptions if e.card_id}, mode="module"
    )
    exceptions = [e for e in exceptions if e.card_id not in hidden]
    today = date.today()
    exc_counts = {"requested": 0, "approved_active": 0, "expired": 0, "rejected": 0}
    for e in exceptions:
        if e.status == "requested":
            exc_counts["requested"] += 1
        elif e.status == "rejected":
            exc_counts["rejected"] += 1
        elif e.status == "approved":
            if e.expiry_date is not None and e.expiry_date < today:
                exc_counts["expired"] += 1
            else:
                exc_counts["approved_active"] += 1

    return {
        "adrs_signed": adrs_signed,
        "arb": {**arb, "dating": "latest_decision"},
        "exceptions": {**exc_counts, "temporal": kpis.CURRENT_STATE},
        # Withdrawn / remediated states do not exist until Batch 3.2 (D-34).
        "exception_lifecycle": _not_available({"code": "later_batch", "batch": "3.2"}),
    }


def _gov03_tile(period: Period, scan: dict[str, Any]) -> dict[str, Any]:
    """The GOV-03 compliance tile from the assessment scan, as a KPI tile.

    Value = compliance %; the completeness block carries assessment coverage
    (assessed ÷ population), shown beside compliance and never multiplied into
    it (I-10). Unavailable with its reason when the population cannot be
    established (I-11)."""
    version = "GOV-03@1"
    if scan["status"] != "ok":
        return kpis._not_available("GOV-03", "governance", version, period, scan["reason"])
    completeness = {
        "numerator": scan["assessed"],
        "denominator": scan["population"],
        "percentage": scan["coverage_pct"],
    }
    return kpis.kpi(
        "GOV-03",
        "governance",
        version,
        status=kpis.OK,
        period=period,
        value=scan["compliance_pct"],
        unit="percent",
        provenance="recorded",
        confidence_level=kpis.confidence(
            system_derived=True, completeness_pct=scan["coverage_pct"]
        ),
        completeness=completeness,
        details={
            "assessed": scan["assessed"],
            "compliant": scan["compliant"],
            "violating": scan["violating"],
            "population": scan["population"],
            "coverage_pct": scan["coverage_pct"],
        },
    )


async def _effectiveness(
    db: AsyncSession,
    read_scope: CardReadScope,
    period: Period,
    gov03_link: dict[str, Any] | None,
) -> dict[str, Any]:
    scan = await assess_standard_compliance(db, read_scope=read_scope)
    compliance = linkage.apply_link(_gov03_tile(period, scan), gov03_link)
    coverage = (
        {
            "status": "ok",
            "assessed": scan["assessed"],
            "population": scan["population"],
            "percentage": scan["coverage_pct"],
        }
        if scan["status"] == "ok"
        else _not_available(scan["reason"])
    )
    return {
        "compliance": compliance,
        "coverage": coverage,
        # GOV-04 needs the exception lifecycle (D-34, Batch 3.2); GOV-05 the
        # decision actions and verification (D-41, Batch 3.4); GOV-07 the
        # transition history and business calendar (D-38 / D-39, Batches 3.2-3.3).
        "exception_resolution": _not_available({"code": "later_batch", "batch": "3.2"}),
        "decision_implementation": _not_available(
            {"code": "decision_pending", "decisions": ["D-41"], "batch": "3.4"}
        ),
        "turnaround": _not_available(
            {"code": "decision_pending", "decisions": ["D-38", "D-39"], "batch": "3.2"}
        ),
    }


def _impact() -> dict[str, Any]:
    return {
        # Technology risk is not automatically a governance risk; the explicit
        # link is D-42 (Batch 3.5), and verified reduction stays Not Available.
        "architecture_risks": _not_available(
            {"code": "decision_pending", "decisions": ["D-42"], "batch": "3.5"}
        ),
        # GOV-09 needs the applicability criteria (D-37, Batch 3.6).
        "governed_delivery": _not_available(
            {"code": "decision_pending", "decisions": ["D-37"], "batch": "3.6"}
        ),
        # Benefits and financial value arrive with the Phase 4 register.
        "business_value": _not_available({"code": "later_phase", "phase": 4}),
    }


async def governance_summary(
    db: AsyncSession,
    read_scope: CardReadScope,
    period: Period,
    *,
    gov03_link: dict[str, Any] | None,
) -> dict[str, Any]:
    """Activity, effectiveness and impact for the selected period, kept apart."""
    return {
        "period": period.to_dict(),
        "activity": await _activity(db, read_scope, period),
        "effectiveness": await _effectiveness(db, read_scope, period, gov03_link),
        "impact": _impact(),
    }


async def gov03_drilldown(db: AsyncSession, read_scope: CardReadScope) -> dict[str, Any]:
    """The non-compliant assessed cards behind GOV-03, under the same scope.

    These are the records that pull the compliance figure down — an assessed
    Application or IT Component with an un-waived use of a sunset / prohibited
    standard. Unavailable cases carry their reason and no rows (I-11)."""
    scan = await assess_standard_compliance(db, read_scope=read_scope)
    if scan["status"] != "ok":
        return {"key": "GOV-03", "status": "not_available", "reason": scan["reason"], "rows": []}
    rows = [{**v, "path": f"/cards/{v['card_id']}"} for v in scan["violations"]]
    return {
        "key": "GOV-03",
        "status": "ok",
        "assessed": scan["assessed"],
        "compliant": scan["compliant"],
        "rows": rows,
    }
