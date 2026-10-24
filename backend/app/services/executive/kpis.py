"""The six CEO indicators: one named, versioned builder each.

Every builder returns ``kpi(...)``: the same contract for every tile, so the page
renders actual, target, previous period, period, freshness, owner, confidence,
provenance and drill-down without special cases.

What the builders deliberately do **not** do:

* **No targets or owners yet.** D-17 (approved 2026-10-24) makes the KPI card
  the source of targets, but a computed KPI can only be matched to its card
  through D-26 (open). Until then every tile says ``target.status =
  "not_linked"``. Once linked, a target is still shown **unratified**: the card
  approval workflow approves the whole record and records nothing about the
  target, so it cannot stand in for an owner's ratification (D-17).
* **No fabricated values.** A KPI whose source or rule is not yet decided is
  ``not_available`` with the reason, never 0.
* **No ROI and no forecast as value.** Realised benefits need the Phase 4
  register; planned savings are carried only as a labelled forecast detail.

Confidence follows the KPI dictionary §1 standard: system-derived with ≥ 90%
completeness is *high*; self-reported, or 70-90%, is *medium*; below 70% is
*low*.
"""

from __future__ import annotations

from typing import Any

from app.services.executive.decisions import RiskPicture
from app.services.executive.periods import Period

OK = "ok"
NOT_AVAILABLE = "not_available"
RESTRICTED = "restricted"

TARGET_NOT_LINKED = {"status": "not_linked", "decision": "D-26"}
OWNER_NOT_LINKED = {"status": "not_linked", "decision": "D-26"}
NO_HISTORY = {"status": NOT_AVAILABLE, "reason": "no_history", "decision": "D-19"}

#: The Executive tab's decisions page, where the escalations are listed.
DECISIONS_PAGE = "/?tab=executive&page=decisions"

#: The landing page's six slots, in display order.
SLOTS = ("strategy", "governance", "delivery", "services", "value", "decisions")


def confidence(*, system_derived: bool, completeness_pct: float | None) -> str:
    if completeness_pct is not None and completeness_pct < 70:
        return "low"
    if not system_derived:
        return "medium"
    if completeness_pct is None or completeness_pct >= 90:
        return "high"
    return "medium"


def kpi(
    key: str,
    slot: str,
    version: str,
    *,
    status: str,
    period: Period,
    value: float | int | None = None,
    unit: str | None = None,
    provenance: str | None = None,
    confidence_level: str | None = None,
    previous: dict[str, Any] | None = None,
    freshness: str | None = None,
    completeness: dict[str, Any] | None = None,
    reason: dict[str, Any] | None = None,
    drilldown: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "slot": slot,
        "calculation_version": version,
        "status": status,
        "value": value if status == OK else None,
        "unit": unit,
        "target": TARGET_NOT_LINKED,
        "owner": OWNER_NOT_LINKED,
        "previous": previous or NO_HISTORY,
        "period": period.key,
        "as_of": period.as_of.isoformat(),
        "freshness": freshness,
        "confidence": confidence_level if status == OK else None,
        "provenance": provenance,
        "completeness": completeness,
        "reason": reason,
        "drilldown": drilldown,
        "details": details or {},
    }


def _not_available(key: str, slot: str, version: str, period: Period, reason: dict) -> dict:
    return kpi(key, slot, version, status=NOT_AVAILABLE, period=period, reason=reason)


# ── Slot 1: strategy achievement (TR-01) ────────────────────────────────


def strategy_execution(period: Period) -> dict[str, Any]:
    """TR-01 needs the strategy-progress source (D-21, open); nothing is inferred."""
    return _not_available(
        "TR-01", "strategy", "TR-01@0", period, {"code": "decision_pending", "decisions": ["D-21"]}
    )


# ── Slot 2: governance effectiveness (GOV-05, fallback GOV-01) ──────────


def governance_effectiveness(period: Period) -> dict[str, Any]:
    """GOV-05 needs decision actions (D-13); its fallback GOV-01 the in-scope rule
    (D-10). Both are Phase 3 decisions, so no review count stands in for them."""
    return _not_available(
        "GOV-05",
        "governance",
        "GOV-05@0",
        period,
        {"code": "later_phase", "phase": 3, "decisions": ["D-10", "D-13"]},
    )


# ── Slot 3: initiative delivery (TR-03 with TR-04) ──────────────────────


def initiative_delivery(
    period: Period,
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    previous_period: Period,
) -> dict[str, Any]:
    """On track among reporting initiatives, as of the period end.

    ``current`` / ``previous`` are ``summarize_delivery_health`` outputs computed
    as of each period's end; ``previous`` is ``None`` when it cannot be derived
    (PPM off: a card's status field keeps no history).
    """
    coverage = current["coverage"]
    reported = coverage["reported"]
    completeness = {
        "numerator": reported,
        "denominator": coverage["in_flight"],
        "percentage": coverage["percentage"],
    }
    if reported == 0:
        status, reason = (
            NOT_AVAILABLE,
            {"code": "not_reported" if coverage["in_flight"] else "no_records"},
        )
    else:
        status, reason = OK, None
    prev_block = None
    if previous is not None:
        prev_value = previous["on_track_pct"]
        prev_block = {
            "status": OK if prev_value is not None else NOT_AVAILABLE,
            "value": prev_value,
            "period": previous_period.key,
            "coverage_percentage": previous["coverage"]["percentage"],
        }
    return kpi(
        "TR-03",
        "delivery",
        "TR-03@2",
        status=status,
        period=period,
        value=current["on_track_pct"],
        unit="percent",
        provenance="reported",
        confidence_level=confidence(system_derived=False, completeness_pct=coverage["percentage"]),
        previous=prev_block,
        freshness=coverage["latest_report_date"],
        completeness=completeness,
        reason=reason,
        drilldown={"api": "TR-03", "path": "/ppm"},
        details={
            "source": current["source"],
            "states": current["states"],
            "excluded": current["excluded"],
            "staleness_days": current["staleness_days"],
            "stale_reports": coverage["stale_reports"],
        },
    )


# ── Slot 4: services digitalization and process automation ──────────────


def services_and_automation(period: Period) -> dict[str, Any]:
    """SVC-01 needs the digitalization source (D-08, Phase 5); SVC-02 the
    eligible-process rule (D-09). Neither is shown until decided."""
    return _not_available(
        "SVC-01",
        "services",
        "SVC-01@0",
        period,
        {"code": "decision_pending", "decisions": ["D-08", "D-09"]},
    )


# ── Slot 5: business value (FIN-01, forecast shown apart) ───────────────


def business_value(period: Period, planned_savings: dict[str, Any]) -> dict[str, Any]:
    """Realised benefits need the Phase 4 benefits register, so the value is not
    available. The planned-savings forecast (Phase 1 rules: deduplicated,
    conflicts excluded, D-31 open) is carried as a labelled detail only, and is
    never the tile's value or an input to ROI."""
    out = _not_available(
        "FIN-01",
        "value",
        "FIN-01@0",
        period,
        {"code": "later_phase", "phase": 4, "decisions": ["D-12", "D-14", "D-15"]},
    )
    out["details"] = {"forecast": planned_savings}
    out["drilldown"] = {"path": "/rationalization"}
    return out


# ── Slot 6: executive decisions and escalations (DEC-01, DEC-02) ────────


def decisions_and_escalations(
    period: Period, risks: RiskPicture | None, pending: dict[str, int]
) -> dict[str, Any]:
    """Escalated risks (D-04 automated rule) as the value; open and mitigated
    risks and pending governance decisions beside it. Current state, not a
    period figure: no previous value until KPI history exists (D-19)."""
    if risks is None:
        return _not_available(
            "DEC-01", "decisions", "DEC-01@1", period, {"code": "module_disabled", "module": "grc"}
        ) | {"details": {"pending": pending}, "drilldown": {"path": DECISIONS_PAGE}}
    return kpi(
        "DEC-01",
        "decisions",
        "DEC-01@1",
        status=OK,
        period=period,
        value=len(risks.escalated),
        unit="count",
        provenance="recorded",
        confidence_level=confidence(system_derived=True, completeness_pct=None),
        drilldown={"api": "DEC-01", "path": DECISIONS_PAGE},
        details={
            "open_risks": risks.open,
            "mitigated_risks": risks.mitigated,
            "pending": pending,
            "current_state": True,
        },
    )
