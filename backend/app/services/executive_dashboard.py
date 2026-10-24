"""Executive dashboard aggregates (phase one).

Every figure here is an aggregate over data Turbo EA already records — counts,
distributions and recorded totals. Nothing is a verified financial benefit:
rationalization savings are carried with ``provenance="estimated"`` and the
frontend labels them as planned, never realised (see
``docs/executive-dashboard-assessment/EXECUTIVE_KPI_CATALOG.md``).

Each section carries a ``status`` so the page never renders an authoritative
zero for something it does not know:

* ``ok`` — computed from the caller's readable cards;
* ``disabled`` — the module is switched off on this instance;
* ``restricted`` — a money figure the caller lacks ``costs.view`` for.

The loaders take the caller's read-scope predicate (``CardReadScope.where``);
the builders are pure so the shaping rules are easy to read in one place.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.rationalization import AssessmentDecision, RationalizationAssessment
from app.models.risk import Risk
from app.services.lifecycle import current_lifecycle_phase

OK = "ok"
DISABLED = "disabled"
RESTRICTED = "restricted"

LIFECYCLE_PHASES = ("plan", "phaseIn", "active", "phaseOut", "endOfLife")
# A risk is "open" until it is closed or formally accepted; mitigated and
# monitoring risks are still tracked on the register.
CLOSED_RISK_STATUSES = frozenset({"closed", "accepted"})
# Mirrors ``risk_service.compute_metrics``: a mitigated risk is no longer overdue.
NOT_OVERDUE_STATUSES = frozenset({"closed", "accepted", "mitigated"})
RISK_LEVELS = ("critical", "high", "medium", "low")
# Assessments that are still a draft or have been archived are not a pipeline.
PIPELINE_ASSESSMENT_STATUSES = ("active", "completed")


def section(status: str, **data: Any) -> dict[str, Any]:
    return {"status": status, **data}


# ── Portfolio health ────────────────────────────────────────────────────


def summarize_lifecycle(lifecycles: Iterable[dict | None]) -> dict[str, int]:
    dist = {phase: 0 for phase in LIFECYCLE_PHASES}
    dist["none"] = 0
    for lc in lifecycles:
        phase = current_lifecycle_phase(lc)
        dist[phase if phase in dist else "none"] += 1
    return dist


async def load_portfolio(db: AsyncSession, readable: tuple) -> dict[str, Any]:
    active = (Card.status == "ACTIVE", *readable)

    by_type_rows = await db.execute(
        select(Card.type, func.count(Card.id)).where(*active).group_by(Card.type)
    )
    by_type = {card_type: n for card_type, n in by_type_rows.all()}

    approval_rows = await db.execute(
        select(Card.approval_status, func.count(Card.id))
        .where(*active)
        .group_by(Card.approval_status)
    )
    approval = {status or "DRAFT": n for status, n in approval_rows.all()}

    avg_dq = (await db.execute(select(func.avg(Card.data_quality)).where(*active))).scalar()

    lifecycles = (await db.execute(select(Card.lifecycle).where(*active))).scalars().all()

    total = sum(by_type.values())
    approved = approval.get("APPROVED", 0)
    return section(
        OK,
        total_cards=total,
        avg_data_quality=round(avg_dq or 0, 1),
        approved_pct=round(approved / total * 100, 1) if total else 0,
        by_type=by_type,
        approval=approval,
        lifecycle=summarize_lifecycle(lifecycles),
    )


# ── Delivery (PPM) ──────────────────────────────────────────────────────


def summarize_delivery(ppm: dict[str, Any], *, can_view_costs: bool) -> dict[str, Any]:
    """Shape the PPM portfolio rollup (``ppm_portfolio_service.build_dashboard``)."""
    schedule = ppm.get("health_schedule", {})
    if can_view_costs:
        budget = section(
            OK,
            total_budget=ppm.get("total_budget", 0),
            total_actual=ppm.get("total_actual", 0),
        )
    else:
        budget = section(RESTRICTED)
    return section(
        OK,
        total_initiatives=ppm.get("total_initiatives", 0),
        off_track=schedule.get("offTrack", 0),
        health_schedule=schedule,
        health_cost=ppm.get("health_cost", {}),
        health_scope=ppm.get("health_scope", {}),
        budget=budget,
    )


# ── Processes (BPM) ─────────────────────────────────────────────────────


def summarize_processes(bpm: dict[str, Any]) -> dict[str, Any]:
    """Shape ``bpm_dashboard_service.summarize_processes`` — no process names."""
    return section(
        OK,
        total_processes=bpm.get("total_processes", 0),
        by_automation=bpm.get("by_automation", {}),
        by_maturity=bpm.get("by_maturity", {}),
        diagram_coverage=bpm.get("diagram_coverage", {}),
    )


# ── Risk ────────────────────────────────────────────────────────────────


def summarize_risks(risks: Sequence[Risk], *, today: date) -> dict[str, Any]:
    open_by_level = {lvl: 0 for lvl in RISK_LEVELS}
    open_total = 0
    overdue = 0
    for r in risks:
        if r.status not in CLOSED_RISK_STATUSES:
            open_total += 1
            level = r.residual_level or r.initial_level
            if level in open_by_level:
                open_by_level[level] += 1
        if (
            r.target_resolution_date
            and r.target_resolution_date < today
            and r.status not in NOT_OVERDUE_STATUSES
        ):
            overdue += 1
    return section(
        OK,
        open=open_total,
        critical_high_open=open_by_level["critical"] + open_by_level["high"],
        open_by_level=open_by_level,
        overdue=overdue,
    )


# ── Rationalization ─────────────────────────────────────────────────────


def summarize_rationalization(
    decisions: Iterable[tuple[str, float | None]], *, can_view_costs: bool
) -> dict[str, Any]:
    """``decisions`` is ``(time_decision, planned_savings)`` per readable application."""
    by_decision: dict[str, int] = {}
    savings = 0.0
    with_savings = 0
    count = 0
    for time_decision, planned in decisions:
        count += 1
        by_decision[time_decision] = by_decision.get(time_decision, 0) + 1
        if planned:
            savings += planned
            with_savings += 1
    if can_view_costs:
        planned_savings = section(OK, total=round(savings, 2), decisions_with_savings=with_savings)
    else:
        planned_savings = section(RESTRICTED)
    return section(
        OK,
        decisions=count,
        by_decision=by_decision,
        # Planned estimates captured on TIME decisions — never realised savings.
        planned_savings={**planned_savings, "provenance": "estimated"},
    )


async def load_rationalization_decisions(
    db: AsyncSession, readable: tuple
) -> list[tuple[str, float | None]]:
    rows = await db.execute(
        select(AssessmentDecision.time_decision, AssessmentDecision.planned_savings)
        .join(
            RationalizationAssessment,
            RationalizationAssessment.id == AssessmentDecision.assessment_id,
        )
        .join(Card, Card.id == AssessmentDecision.card_id)
        .where(
            RationalizationAssessment.status.in_(PIPELINE_ASSESSMENT_STATUSES),
            Card.status == "ACTIVE",
            *readable,
        )
    )
    return [(d, s) for d, s in rows.all()]
