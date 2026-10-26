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
* **No history inferred from the present.** A tile is either a *period* figure
  or a *current-state* figure (``temporal``). A current-state figure (today's
  risk register, pending decisions, undated savings) is labelled as such and
  measured as of today whatever period is selected. A period figure for a
  finished period is shown only where dated records establish both its
  population and its values; otherwise it is ``historical_unavailable``.

Confidence follows the KPI dictionary §1 standard: system-derived with ≥ 90%
completeness is *high*; self-reported, or 70-90%, is *medium*; below 70% is
*low*.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.services.executive.decisions import RiskPicture
from app.services.executive.periods import Period

OK = "ok"
NOT_AVAILABLE = "not_available"
RESTRICTED = "restricted"

TARGET_NOT_LINKED = {"status": "not_linked", "decision": "D-26"}
OWNER_NOT_LINKED = {"status": "not_linked", "decision": "D-26"}
NO_HISTORY = {"status": NOT_AVAILABLE, "reason": "no_history", "decision": "D-19"}

#: A tile measured over the selected reporting period.
PERIOD_BASED = "period"
#: A tile describing the present, whatever period is selected.
CURRENT_STATE = "current_state"
#: A finished period whose population or values have no dated evidence.
HISTORICAL_UNAVAILABLE = {"code": "historical_unavailable"}

#: The Executive tab's decisions page, where the escalations are listed.
DECISIONS_PAGE = "/?tab=executive&page=decisions"
#: The Executive tab's EA governance page (Batch 3.1).
GOVERNANCE_PAGE = "/?tab=executive&page=governance"

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
    temporal: str = PERIOD_BASED,
    as_of: date | None = None,
) -> dict[str, Any]:
    current_state = temporal == CURRENT_STATE
    return {
        "key": key,
        "slot": slot,
        "calculation_version": version,
        "temporal": temporal,
        "status": status,
        "value": value if status == OK else None,
        "unit": unit,
        "target": TARGET_NOT_LINKED,
        "owner": OWNER_NOT_LINKED,
        "previous": previous or NO_HISTORY,
        # A current-state tile belongs to no reporting period.
        "period": None if current_state else period.key,
        "as_of": (as_of or period.as_of).isoformat(),
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


STRATEGY_PAGE = "/?tab=executive&page=strategy"


def strategy_execution(period: Period, summary: dict[str, Any] | None) -> dict[str, Any]:
    """TR-01 (D-21): strategic KPIs on target, among those measured this period.

    ``summary`` is ``strategy.strategy_achievement`` for the current period, or
    ``None`` for a finished one (its population of strategic links has no
    history). Value = KPIs on target; the denominator is the KPIs *measured*
    (ratified target + verified value), and coverage — measured of linked —
    travels beside it. No index, no weights, no ``Objective.progress``.
    """
    version = "TR-01@1"
    if summary is None:
        return _not_available("TR-01", "strategy", version, period, HISTORICAL_UNAVAILABLE)
    totals = summary["totals"]
    details = {"totals": totals, "execution": summary["execution"]}
    if totals["linked"] == 0:
        out = _not_available("TR-01", "strategy", version, period, {"code": "no_strategic_kpis"})
        return out | {"details": details, "drilldown": {"path": STRATEGY_PAGE}}
    completeness = {
        "numerator": totals["measured"],
        "denominator": totals["linked"],
        "percentage": round(totals["measured"] / totals["linked"] * 100, 1),
    }
    if totals["measured"] == 0:
        out = _not_available(
            "TR-01", "strategy", version, period, {"code": "no_verified_measurements"}
        )
        return out | {
            "details": details,
            "completeness": completeness,
            "drilldown": {"path": STRATEGY_PAGE},
        }
    return kpi(
        "TR-01",
        "strategy",
        version,
        status=OK,
        period=period,
        value=totals["on_target"],
        unit="count_of",
        provenance="recorded",
        # Verified measurements of KPIs, many entered by people: "medium" at best.
        confidence_level=confidence(
            system_derived=False, completeness_pct=completeness["percentage"]
        ),
        completeness=completeness,
        drilldown={"path": STRATEGY_PAGE},
        details=details,
    )


# ── Slot 2: governance effectiveness (GOV-05, fallback GOV-01) ──────────


def governance_effectiveness(period: Period) -> dict[str, Any]:
    """GOV-05 needs decision actions (D-13); its fallback GOV-01 the in-scope rule
    (D-10). Both are later-batch Phase 3 decisions, so no review count stands in
    for them (I-7). The tile links to the Governance page, where activity and the
    rule-based compliance that *are* available in Batch 3.1 are shown."""
    tile = _not_available(
        "GOV-05",
        "governance",
        "GOV-05@0",
        period,
        {"code": "later_phase", "phase": 3, "decisions": ["D-10", "D-13"]},
    )
    tile["drilldown"] = {"path": GOVERNANCE_PAGE}
    return tile


# ── Slot 3: initiative delivery (TR-03 with TR-04) ──────────────────────


def historical_previous(previous_period: Period) -> dict[str, Any]:
    """The previous-period block when that period's figure cannot be derived.

    The previous period has always ended, and nothing records which initiatives
    were in flight then: membership comes from each card's *current* status
    (``completed`` / ``onHold``), which keeps no history. So the comparison is
    unavailable rather than recomputed over today's population.
    """
    return {
        "status": NOT_AVAILABLE,
        "reason": HISTORICAL_UNAVAILABLE["code"],
        "period": previous_period.key,
    }


def previous_from_history(previous_period: Period, m: Any | None) -> dict[str, Any]:
    """The previous-period block from a **verified** period measurement (D-19)."""
    if m is None or m.value is None:
        return historical_previous(previous_period)
    return {"status": OK, "value": m.value, "period": previous_period.key, "verified": True}


def recorded_delivery(period: Period, m: Any | None, previous: dict[str, Any]) -> dict[str, Any]:
    """TR-03 for a finished period, from its verified period measurement only.

    The value is what the daily capture observed on ``observed_on`` (the last
    observation inside the period), verified by a person afterwards. Without a
    verified measurement the tile stays *historical data unavailable* — a
    submitted one says it is awaiting verification.
    """
    if m is None or m.status != "verified" or m.value is None:
        reason = (
            {"code": "awaiting_verification"}
            if m is not None and m.status == "submitted"
            else HISTORICAL_UNAVAILABLE
        )
        return _not_available("TR-03", "delivery", "TR-03@3", period, reason) | {
            "previous": previous
        }
    return kpi(
        "TR-03",
        "delivery",
        m.calculation_version or "TR-03@3",
        status=OK,
        period=period,
        value=m.value,
        unit="percent",
        provenance="recorded",
        confidence_level=confidence(system_derived=False, completeness_pct=None),
        previous=previous,
        freshness=m.observed_on.isoformat() if m.observed_on else None,
        details={
            "source": "history",
            "verified_at": m.verified_at.isoformat() if m.verified_at else None,
        },
    )


def initiative_delivery(
    period: Period,
    current: dict[str, Any] | None,
    previous_period: Period,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """On track among reporting initiatives, for the current period only.

    ``previous`` is the verified previous-period value when the history holds
    one (``previous_from_history``); otherwise the comparison is unavailable.

    ``current`` is the ``summarize_delivery_health`` output as of today, or
    ``None`` when the selected period has ended: the in-flight population is
    defined by the cards' present status, so a finished period's population is
    not on record and the tile says so instead of recounting today's cards.
    """
    previous = previous or historical_previous(previous_period)
    if current is None:
        return _not_available("TR-03", "delivery", "TR-03@3", period, HISTORICAL_UNAVAILABLE) | {
            "previous": previous
        }
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
    return kpi(
        "TR-03",
        "delivery",
        "TR-03@3",
        status=status,
        period=period,
        value=current["on_track_pct"],
        unit="percent",
        provenance="reported",
        confidence_level=confidence(system_derived=False, completeness_pct=coverage["percentage"]),
        previous=previous,
        freshness=coverage["latest_report_date"],
        completeness=completeness,
        reason=reason,
        drilldown={"api": "TR-03", "path": "/ppm"} if current["source"] == "ppm_reports" else None,
        details={
            "source": current["source"],
            "states": current["states"],
            "excluded": current["excluded"],
            "staleness_days": current["staleness_days"],
            "stale_reports": coverage["stale_reports"],
            "oldest_report_date": coverage.get("oldest_report_date"),
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
    never the tile's value or an input to ROI. The estimates carry no period
    (D-31), so the forecast is a current-state figure whatever period is shown."""
    out = _not_available(
        "FIN-01",
        "value",
        "FIN-01@1",
        period,
        {"code": "later_phase", "phase": 4, "decisions": ["D-12", "D-14", "D-15"]},
    )
    out["details"] = {"forecast": {**planned_savings, "temporal": CURRENT_STATE}}
    out["drilldown"] = {"path": "/rationalization"}
    return out


# ── Slot 6: executive decisions and escalations (DEC-01, DEC-02) ────────


def decisions_and_escalations(
    period: Period, risks: RiskPicture | None, pipeline: dict[str, int], today: date
) -> dict[str, Any]:
    """Escalated risks (D-04 automated rule) as the value; open and mitigated
    risks beside it, and the operational governance pipeline (ADRs awaiting
    signature, pending reviews, requested exceptions) kept apart as routine
    activity, not escalations. Always the current state, measured today."""
    common: dict[str, Any] = {"temporal": CURRENT_STATE, "as_of": today}
    if risks is None:
        return _not_available(
            "DEC-01", "decisions", "DEC-01@2", period, {"code": "module_disabled", "module": "grc"}
        ) | {
            "temporal": CURRENT_STATE,
            "period": None,
            "as_of": today.isoformat(),
            "details": {"operational_pipeline": pipeline},
            "drilldown": {"path": DECISIONS_PAGE},
        }
    return kpi(
        "DEC-01",
        "decisions",
        "DEC-01@2",
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
            "operational_pipeline": pipeline,
        },
        **common,
    )
