"""Executive dashboard aggregates (Phase 1: KPI correctness).

Every figure here is an aggregate over data Turbo EA already records — counts,
distributions and recorded totals. Nothing is a verified financial benefit:
rationalization savings are carried as a **forecast** and the frontend labels
them so, never as realised. The rules follow the approved decisions in
``docs/executive-dashboard-implementation/DECISION_LOG.md`` and the corrections
CR-01..CR-10 in ``FINAL_KPI_DICTIONARY.md``.

Each section carries a ``status`` so the page never renders an authoritative
zero for something it does not know:

* ``ok`` — computed from the caller's readable cards;
* ``disabled`` — the module is switched off on this instance;
* ``restricted`` — a money figure the caller lacks ``costs.view`` for;
* ``not_available`` — no source records this yet (e.g. realised savings before
  the benefits register exists); never shown as 0.

The loaders take the caller's read-scope predicate (``CardReadScope.where`` plus
the hidden-type rule), so restricted cards are gone before anything is counted;
the builders are pure so the shaping rules are easy to read in one place.

Money (D-05): PPM budget / cost lines and rationalization planned savings carry
no currency of their own — they are recorded in the instance currency — so every
money block names that ``currency`` and every total stays within it. No amount
is ever converted or relabelled here.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_type import CardType
from app.models.ppm_cost_line import PpmBudgetLine, PpmCostLine
from app.models.ppm_status_report import PpmStatusReport
from app.models.rationalization import AssessmentDecision, RationalizationAssessment
from app.models.risk import Risk
from app.services import ppm_portfolio_service as ppm_portfolio
from app.services.card_read_scope import CardReadScope
from app.services.fiscal_year import fiscal_year_bounds, fiscal_year_for
from app.services.lifecycle import current_lifecycle_phase

OK = "ok"
DISABLED = "disabled"
RESTRICTED = "restricted"
NOT_AVAILABLE = "not_available"

LIFECYCLE_PHASES = ("plan", "phaseIn", "active", "phaseOut", "endOfLife")
# A risk is "open" until it is closed or formally accepted; mitigated and
# monitoring risks are still tracked on the register.
CLOSED_RISK_STATUSES = frozenset({"closed", "accepted"})
# Mirrors ``risk_service.compute_metrics``: a mitigated risk is no longer overdue.
NOT_OVERDUE_STATUSES = frozenset({"closed", "accepted", "mitigated"})
RISK_LEVELS = ("critical", "high", "medium", "low")
# Assessments that are still a draft or have been archived are not a pipeline.
PIPELINE_ASSESSMENT_STATUSES = ("active", "completed")

# ── Initiative delivery (CR-01 / CR-02, D-02) ──
#: The four delivery states. ``notReported`` is "Unknown / Not reported": no
#: report, a report older than the configured staleness threshold, or a report
#: whose health values are not recognised. It is never healthy and never At Risk.
DELIVERY_STATES = ("onTrack", "atRisk", "offTrack", "notReported")
HEALTH_RANK = {"onTrack": 0, "atRisk": 1, "offTrack": 2}
#: Initiatives in these ``initiativeStatus`` values are not in flight: they are
#: reported beside the health mix, never inside it.
EXCLUDED_INITIATIVE_STATUSES = ("completed", "onHold")
HEALTH_DIMENSIONS = ("schedule", "cost", "scope")

#: Source of the delivery state: PPM status reports when PPM is enabled,
#: otherwise the Initiative card's own ``initiativeStatus`` (D-02 notes).
SOURCE_PPM_REPORTS = "ppm_reports"
SOURCE_INITIATIVE_STATUS = "initiative_status"

#: ``app_settings.general_settings`` key for the staleness threshold, in days.
#: Deliberately no default (D-02): while it is unset no report is ever stale.
STALENESS_SETTING = "initiativeReportStalenessDays"
MAX_STALENESS_DAYS = 3650


def section(status: str, **data: Any) -> dict[str, Any]:
    return {"status": status, **data}


def staleness_days(general: dict[str, Any]) -> int | None:
    """The configured staleness threshold, or ``None`` when unset or malformed."""
    value = general.get(STALENESS_SETTING)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 1 <= value <= MAX_STALENESS_DAYS else None


# ── Portfolio health ────────────────────────────────────────────────────


def summarize_lifecycle(lifecycles: Iterable[dict | None]) -> dict[str, int]:
    dist = {phase: 0 for phase in LIFECYCLE_PHASES}
    dist["none"] = 0
    for lc in lifecycles:
        phase = current_lifecycle_phase(lc)
        dist[phase if phase in dist else "none"] += 1
    return dist


async def load_portfolio(db: AsyncSession, readable: tuple) -> dict[str, Any]:
    """Repository-level figures over the caller's readable, visible-type cards.

    ``data_completeness`` is the weighted field completeness (``cards.data_quality``),
    renamed from "data quality" (CR-08) — it measures filled-in fields, not the
    correctness of the data. ``approval`` is the repository review status
    (CR-07), never architecture compliance.
    """
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

    completeness = select(func.avg(Card.data_quality), func.max(Card.updated_at)).where(*active)
    avg_dq, last_updated = (await db.execute(completeness)).one()

    lifecycles = (await db.execute(select(Card.lifecycle).where(*active))).scalars().all()

    return section(
        OK,
        total_cards=sum(by_type.values()),
        data_completeness=round(avg_dq or 0, 1),
        by_type=by_type,
        approval=approval,
        lifecycle=summarize_lifecycle(lifecycles),
        last_updated=last_updated.isoformat() if last_updated else None,
    )


# ── Delivery: initiative health and reporting coverage ──────────────────


async def load_visible_initiatives(db: AsyncSession, read_scope: CardReadScope) -> list[Card]:
    """ACTIVE Initiatives the caller may read, hidden card types left out (D-01).

    The one population every executive delivery figure counts over, so the
    Executive tab and the CEO overview cannot disagree on the denominator.
    """
    initiatives = await ppm_portfolio.load_initiatives(
        db, ppm_portfolio.PortfolioScope(), read_scope=read_scope
    )
    hidden = set(
        (await db.execute(select(CardType.key).where(CardType.is_hidden.is_(True)))).scalars().all()
    )
    return [c for c in initiatives if c.type not in hidden]


def _report_in_window(report: PpmStatusReport | None, *, today: date, stale: int | None) -> bool:
    if report is None:
        return False
    return stale is None or report.report_date >= today - timedelta(days=stale)


def report_state(report: PpmStatusReport | None, *, today: date, stale: int | None) -> str:
    """One initiative's delivery state from its latest report.

    The worst of schedule, cost and scope health. No report, a report outside
    the staleness window, or an unrecognised health value is ``notReported``.
    """
    if not _report_in_window(report, today=today, stale=stale):
        return "notReported"
    values = (report.schedule_health, report.cost_health, report.scope_health)
    if any(v not in HEALTH_RANK for v in values):
        return "notReported"
    return max(values, key=HEALTH_RANK.__getitem__)


def status_state(card: Card) -> str:
    """Fallback state from ``initiativeStatus`` when PPM reports are off."""
    value = (card.attributes or {}).get("initiativeStatus")
    return value if value in HEALTH_RANK else "notReported"


def _initiative_status(card: Card) -> str | None:
    value = (card.attributes or {}).get("initiativeStatus")
    return value if isinstance(value, str) else None


def summarize_delivery_health(
    initiatives: Sequence[Card],
    latest: dict[uuid.UUID, PpmStatusReport] | None,
    *,
    today: date,
    stale: int | None,
) -> dict[str, Any]:
    """Four-state health with reporting coverage kept separate (CR-01 / CR-02).

    ``latest`` is the latest PPM report per initiative, or ``None`` when PPM is
    off — then each initiative's own ``initiativeStatus`` is the source, and
    coverage counts initiatives with a status set. The state counts plus the
    excluded initiatives always equal ``total_initiatives``.
    """
    excluded = {s: 0 for s in EXCLUDED_INITIATIVE_STATUSES}
    states = {s: 0 for s in DELIVERY_STATES}
    dims = {d: {**{s: 0 for s in HEALTH_RANK}, "noReport": 0} for d in HEALTH_DIMENSIONS}
    stale_reports = 0
    report_dates: list[date] = []
    in_flight = 0

    for card in initiatives:
        init_status = _initiative_status(card)
        if init_status in excluded:
            excluded[init_status] += 1
            continue
        in_flight += 1
        if latest is None:
            states[status_state(card)] += 1
            continue
        report = latest.get(card.id)
        in_window = _report_in_window(report, today=today, stale=stale)
        if report is not None and not in_window:
            stale_reports += 1
        states[report_state(report, today=today, stale=stale)] += 1
        if in_window:
            report_dates.append(report.report_date)
        for dim in HEALTH_DIMENSIONS:
            value = getattr(report, f"{dim}_health") if in_window else "noReport"
            dims[dim][value if value in dims[dim] else "noReport"] += 1

    reported = in_flight - states["notReported"]
    coverage = section(
        OK,
        reported=reported,
        in_flight=in_flight,
        percentage=round(reported / in_flight * 100, 1) if in_flight else None,
        stale_reports=stale_reports,
        latest_report_date=max(report_dates).isoformat() if report_dates else None,
        oldest_report_date=min(report_dates).isoformat() if report_dates else None,
    )
    return section(
        OK,
        source=SOURCE_INITIATIVE_STATUS if latest is None else SOURCE_PPM_REPORTS,
        staleness_days=stale,
        total_initiatives=len(initiatives),
        in_flight=in_flight,
        excluded=excluded,
        states=states,
        # Headline: On Track among the initiatives that reported — never over
        # the whole population, which would read a missing report as unhealthy.
        on_track_pct=round(states["onTrack"] / reported * 100, 1) if reported else None,
        coverage=coverage,
        dimensions=dims if latest is not None else None,
    )


def delivery_rows(
    initiatives: Sequence[Card],
    latest: dict[uuid.UUID, PpmStatusReport] | None,
    *,
    today: date,
    stale: int | None,
) -> list[dict[str, Any]]:
    """One row per in-flight initiative with its delivery state — the drill-down
    behind ``summarize_delivery_health``, classified by the same functions so the
    rows always add up to the counts."""
    rows = []
    for card in initiatives:
        if _initiative_status(card) in EXCLUDED_INITIATIVE_STATUSES:
            continue
        if latest is None:
            state, report_date = status_state(card), None
        else:
            report = latest.get(card.id)
            state = report_state(report, today=today, stale=stale)
            report_date = report.report_date.isoformat() if report is not None else None
        rows.append(
            {"id": str(card.id), "name": card.name, "state": state, "report_date": report_date}
        )
    # Worst first: an executive opens this list to find what needs attention.
    order = {"offTrack": 0, "atRisk": 1, "notReported": 2, "onTrack": 3}
    rows.sort(key=lambda r: (order[r["state"]], r["name"].lower()))
    return rows


# ── Delivery: budget and actuals for one fiscal year (CR-03, D-06) ──────


@dataclass(frozen=True)
class FiscalMoney:
    budget: float
    actual: float
    undated_cost_lines: int
    years: tuple[int, ...]


async def load_fiscal_money(
    db: AsyncSession, initiative_ids: Sequence[uuid.UUID], *, fy: int, start_month: int
) -> FiscalMoney:
    """FY budget (lines whose ``fiscal_year`` is ``fy``) and FY actuals (cost
    lines dated inside the fiscal year). Never sums across fiscal years: a cost
    line with no date belongs to no year and is only counted, not summed.

    Sums each initiative's **own** lines, like the PPM board's KPI bar: a
    parent's derived roll-up is its children's lines, which are counted here
    already, so nothing is double-counted.
    """
    if not initiative_ids:
        return FiscalMoney(0.0, 0.0, 0, ())
    start, end = fiscal_year_bounds(fy, start_month)
    budget = await db.execute(
        select(func.coalesce(func.sum(PpmBudgetLine.amount), 0)).where(
            PpmBudgetLine.initiative_id.in_(initiative_ids), PpmBudgetLine.fiscal_year == fy
        )
    )
    actual = await db.execute(
        select(func.coalesce(func.sum(PpmCostLine.actual), 0)).where(
            PpmCostLine.initiative_id.in_(initiative_ids),
            PpmCostLine.date >= start,
            PpmCostLine.date < end,
        )
    )
    undated = await db.execute(
        select(func.count(PpmCostLine.id)).where(
            PpmCostLine.initiative_id.in_(initiative_ids), PpmCostLine.date.is_(None)
        )
    )
    budget_years = await db.execute(
        select(PpmBudgetLine.fiscal_year)
        .where(PpmBudgetLine.initiative_id.in_(initiative_ids))
        .distinct()
    )
    cost_dates = await db.execute(
        select(PpmCostLine.date)
        .where(PpmCostLine.initiative_id.in_(initiative_ids), PpmCostLine.date.is_not(None))
        .distinct()
    )
    years = {y for y in budget_years.scalars().all() if y is not None}
    years |= {fiscal_year_for(d, start_month) for d in cost_dates.scalars().all()}
    return FiscalMoney(
        budget=float(budget.scalar() or 0),
        actual=float(actual.scalar() or 0),
        undated_cost_lines=int(undated.scalar() or 0),
        years=tuple(sorted(years)),
    )


def summarize_budget(
    money: FiscalMoney | None,
    *,
    enabled: bool,
    fy: int,
    start_month: int,
    current_fy: int,
    currency: str,
    can_view_costs: bool,
) -> dict[str, Any]:
    """Budget execution for one fiscal year. The period is always named, even
    when the amounts are restricted — a period is not a money figure."""
    period = {
        "fiscal_year": fy,
        "fiscal_year_start": start_month,
        "current_fiscal_year": current_fy,
        "available_years": sorted({current_fy, fy, *(money.years if money else ())}),
    }
    if not enabled:
        return section(DISABLED, **period)
    if not can_view_costs or money is None:
        return section(RESTRICTED, **period)
    return section(
        OK,
        **period,
        currency=currency,
        budget=round(money.budget, 2),
        actual=round(money.actual, 2),
        # Budget execution (FIN-07): None when no budget is recorded for the year.
        execution_pct=round(money.actual / money.budget * 100, 1) if money.budget else None,
        undated_cost_lines=money.undated_cost_lines,
    )


# ── Processes (BPM) ─────────────────────────────────────────────────────


def summarize_processes(bpm: dict[str, Any]) -> dict[str, Any]:
    """Shape ``bpm_dashboard_service.summarize_processes`` — no process names.

    ``documentation_coverage`` is processes with a published BPMN flow: it says
    the process is documented, not how automated or mature it is (CR-10).
    """
    return section(
        OK,
        total_processes=bpm.get("total_processes", 0),
        by_automation=bpm.get("by_automation", {}),
        by_maturity=bpm.get("by_maturity", {}),
        documentation_coverage=bpm.get("diagram_coverage", {}),
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


# ── Rationalization and planned savings (CR-04, D-24) ───────────────────


@dataclass(frozen=True)
class DecisionRow:
    card_id: uuid.UUID
    card_name: str
    assessment_id: uuid.UUID
    assessment_name: str
    time_decision: str
    planned_savings: float | None
    #: The ``assessment_decisions`` row, which a benefit may name (I-71).
    decision_id: uuid.UUID | None = None


def summarize_planned_savings(
    rows: Sequence[DecisionRow], superseded: set[uuid.UUID] | None = None
) -> dict[str, Any]:
    """Deduplicate planned savings by identity and flag conflicts (D-24).

    Identity is the application (``card_id``) — no benefit record exists before
    the benefits register (Phase 4). Within one identity, estimates that agree
    count once; estimates that differ are a **conflict**: listed with every
    candidate and excluded from the total. Neither the latest nor the lowest
    amount is ever picked. A decision with no estimate is not a candidate.

    D-31 (approved 2026-10-27, option c): planned savings are an **annual
    run-rate forecast with no fiscal year**, so the identity has no period half
    and the figure says so. They never count as realised or as an ROI input.
    """
    by_identity: dict[uuid.UUID, list[DecisionRow]] = {}
    superseded = superseded or set()
    for row in rows:
        # A decision a benefit names is counted in the register, not here (I-71).
        if row.decision_id is not None and row.decision_id in superseded:
            continue
        if row.planned_savings is not None:
            by_identity.setdefault(row.card_id, []).append(row)

    total = 0.0
    counted = 0
    merged = 0
    conflicts: list[dict[str, Any]] = []
    for card_id, estimates in by_identity.items():
        distinct = {round(r.planned_savings or 0.0, 2) for r in estimates}
        if len(distinct) == 1:
            total += distinct.pop()
            counted += 1
            merged += len(estimates) - 1
            continue
        conflicts.append(
            {
                "card_id": str(card_id),
                "card_name": estimates[0].card_name,
                "candidates": sorted(
                    (
                        {
                            "assessment_id": str(r.assessment_id),
                            "assessment_name": r.assessment_name,
                            "amount": round(r.planned_savings or 0.0, 2),
                        }
                        for r in estimates
                    ),
                    key=lambda c: (c["amount"], c["assessment_name"]),
                ),
            }
        )
    conflicts.sort(key=lambda c: c["card_name"].lower())
    amounts = [c["amount"] for conflict in conflicts for c in conflict["candidates"]]
    return {
        "total": round(total, 2),
        "applications_counted": counted,
        "duplicates_merged": merged,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "excluded_range": [min(amounts), max(amounts)] if amounts else None,
        "period": {"status": "run_rate", "decision": "D-31"},
    }


def summarize_rationalization(
    rows: Sequence[DecisionRow],
    *,
    can_view_costs: bool,
    can_view_rationalization: bool,
    currency: str,
    superseded: set[uuid.UUID] | None = None,
) -> dict[str, Any]:
    """TIME decisions and planned savings.

    The conflict list names applications, assessments and each assessment's
    estimate — record-level rationalization data — so it needs
    ``rationalization.view`` as the module's own routes do. Without it only the
    count of conflicts is returned, never the names or the amounts behind it
    (not even their range, which for one conflict would be both estimates).
    """
    by_decision: dict[str, int] = {}
    for row in rows:
        by_decision[row.time_decision] = by_decision.get(row.time_decision, 0) + 1
    if can_view_costs:
        savings = summarize_planned_savings(rows, superseded)
        if can_view_rationalization:
            savings["conflict_detail"] = OK
        else:
            savings.update(conflicts=None, excluded_range=None, conflict_detail=RESTRICTED)
        planned = section(OK, currency=currency, **savings)
    else:
        planned = section(RESTRICTED)
    return section(
        OK,
        decisions=len(rows),
        applications=len({r.card_id for r in rows}),
        by_decision=by_decision,
        # Planned estimates captured on TIME decisions — a forecast, never realised.
        planned_savings={**planned, "provenance": "forecast"},
        # Realised savings are Finance-confirmed benefits (Phase 4 register),
        # reported on the Benefits page — never mixed with the forecast above.
        realized_savings=section(NOT_AVAILABLE),
    )


async def load_rationalization_decisions(db: AsyncSession, readable: tuple) -> list[DecisionRow]:
    rows = await db.execute(
        select(
            AssessmentDecision.card_id,
            Card.name,
            RationalizationAssessment.id,
            RationalizationAssessment.name,
            AssessmentDecision.time_decision,
            AssessmentDecision.planned_savings,
            AssessmentDecision.id,
        )
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
    return [DecisionRow(*r) for r in rows.all()]
