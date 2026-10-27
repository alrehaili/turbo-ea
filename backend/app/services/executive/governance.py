"""EA governance effectiveness — Batch 3.1 (DECISION_LOG.md §3.1).

Three classes, **never mixed** (GOVERNANCE_MEASUREMENT_MODEL.md §1):

* **Activity** — governance happened. ADRs signed in the period; ARB reviews by
  their latest decision date (``decided_at`` is overwritten on each change, so
  the counts are labelled accordingly and deferred reviews are counted apart,
  never as decisions — I-12); standard exceptions by their current state. No
  value claim is attached to any of it.
* **Effectiveness** — governance was acted on. GOV-03 rule-based technology
  standards compliance (I-9) and assessment coverage (I-10) as **two separate
  figures**; GOV-07 **elapsed** calendar days per instrument (Batch 3.2, D-35)
  from the recorded transition history and reliable existing stamps, beside
  governance-controlled processing time (D-39: only intervals explicitly
  attributed to the requester or an external dependency are left out; working
  days wait on the business calendar, D-38, Batch 3.3). GOV-04 exception
  resolution counts verified remediation only, with rejection, withdrawal and
  expired-unresolved reported apart (D-40). GOV-05 decision implementation
  counts only **independently verified** implementation against the original
  approved deadline, with planning coverage and every excluded decision
  disclosed beside it (D-32, D-41; Batch 3.4).
* **Impact** — governed work performs better. Architecture risks, governed vs
  ungoverned delivery (GOV-09) and business value are Not Available with their
  reason until their batch or Phase 4 lands.

Anything without a defensible calculation is Not Available **with its reason**,
never zero (C-04). Governance records about hidden cards are omitted exactly as
their own modules do (D-30), and every card population is the caller's
module-mode ``CardReadScope`` with hidden types excluded (D-01).
"""

from __future__ import annotations

import statistics
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.decision_implementation import DECISION_ADR, DECISION_ARB, DecisionImplementation
from app.models.governance_transition import (
    ATTRIBUTION_EXTERNAL,
    ATTRIBUTION_REQUESTER,
    EVENT_EXPIRY_CHANGED,
    INSTRUMENT_ADR,
    INSTRUMENT_ADR_IMPL,
    INSTRUMENT_ARB,
    INSTRUMENT_ARB_IMPL,
    INSTRUMENT_EXCEPTION,
    GovernanceTransition,
)
from app.models.tech_standard import StandardException
from app.models.todo import Todo
from app.services import decision_implementation as impl_service
from app.services import ea_applicability as ea
from app.services import executive_dashboard as exe
from app.services import ppm_portfolio_service as portfolio
from app.services import risk_governance
from app.services.business_calendar import BusinessCalendar, load_calendar
from app.services.card_read_scope import CardReadScope
from app.services.executive import kpis, linkage
from app.services.executive.periods import Period
from app.services.fiscal_year import get_fiscal_year_start
from app.services.tech_standards_scan import assess_standard_compliance

#: ARB outcomes that count as a decision; deferral is reported apart (I-12).
ARB_DECISION_STATUSES = ("approved", "rejected")
ARB_DEFERRED = "deferred"
#: Exception outcomes that are a decision (expiry is derived, never one — D-34).
EXCEPTION_DECISION_STATUSES = ("approved", "rejected")


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

    # Exceptions by their current state (I-12): a present-state snapshot, not a
    # period figure. Verified remediation, administrative closes (rejected,
    # withdrawn), expired-unresolved and active approvals stay apart (D-40).
    exc_rows = await db.execute(select(StandardException))
    exceptions = list(exc_rows.scalars().all())
    hidden = await read_scope.hidden_card_ids(
        db, {e.card_id for e in exceptions if e.card_id}, mode="module"
    )
    exceptions = [e for e in exceptions if e.card_id not in hidden]
    today = date.today()
    exc_counts = {
        "requested": 0,
        "approved_active": 0,
        "expired": 0,
        "remediation_submitted": 0,
        "remediated": 0,
        "rejected": 0,
        "withdrawn": 0,
    }
    for e in exceptions:
        if e.status == "approved":
            if e.expiry_date is not None and e.expiry_date < today:
                exc_counts["expired"] += 1
            else:
                exc_counts["approved_active"] += 1
        elif e.status in exc_counts:
            exc_counts[e.status] += 1

    return {
        "adrs_signed": adrs_signed,
        "arb": {**arb, "dating": "latest_decision"},
        "exceptions": {**exc_counts, "temporal": kpis.CURRENT_STATE},
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
        "exception_resolution": await exception_resolution(db, read_scope, period),
        "decision_implementation": await decision_implementation(db, read_scope, period),
        "turnaround": await turnaround(db, read_scope, period),
    }


def elapsed_days(start: datetime | None, end: datetime | None) -> float | None:
    """Calendar days from ``start`` to ``end``; ``None`` when either is missing
    or the order is impossible (an end before its start is not a duration)."""
    if start is None or end is None or end < start:
        return None
    return (end - start).total_seconds() / 86400


def elapsed_figure(samples: list[float], not_recorded: int, basis: str) -> dict[str, Any]:
    """One instrument's GOV-07 elapsed figure: median and slowest, in days.

    No sample means no figure: Not Available with the count of decisions whose
    lifecycle was not recorded, never a zero (C-04)."""
    if not samples:
        return {
            "status": "not_available",
            "reason": {"code": "no_recorded_decisions"},
            "decisions": 0,
            "not_recorded": not_recorded,
            "basis": basis,
        }
    return {
        "status": "ok",
        "decisions": len(samples),
        "median_days": round(statistics.median(samples), 1),
        "max_days": round(max(samples), 1),
        "not_recorded": not_recorded,
        "basis": basis,
    }


async def _first_decisions(
    db: AsyncSession, instrument: str, outcomes: tuple[str, ...]
) -> dict[uuid.UUID, datetime]:
    """Each record's first recorded transition into a final outcome."""
    rows = await db.execute(
        select(GovernanceTransition.record_id, GovernanceTransition.occurred_at)
        .where(
            GovernanceTransition.instrument == instrument,
            GovernanceTransition.to_status.in_(outcomes),
            # An expiry change keeps the status; it is never a decision (I-35).
            GovernanceTransition.event_kind.is_(None),
        )
        .order_by(GovernanceTransition.occurred_at)
    )
    first: dict[uuid.UUID, datetime] = {}
    for record_id, occurred_at in rows.all():
        first.setdefault(record_id, occurred_at)
    return first


def _split(
    records: list[Any], first: dict[uuid.UUID, datetime], period: Period, legacy_decided
) -> tuple[list[float], int, list[tuple[datetime, datetime]]]:
    """Samples for records first decided in the period, the not-recorded count,
    and the timed ``(start, end)`` pairs the working-day figure reuses.

    ``legacy_decided(record)`` says whether a record with no recorded decision
    transition counts as a decision this figure cannot time."""
    samples: list[float] = []
    pairs: list[tuple[datetime, datetime]] = []
    not_recorded = 0
    for rec in records:
        decided = first.get(rec.id)
        if decided is None:
            if legacy_decided(rec):
                not_recorded += 1
            continue
        if not _in_period(decided, period):
            continue
        days = elapsed_days(rec.created_at, decided)
        if days is None:
            not_recorded += 1
        else:
            samples.append(days)
            pairs.append((rec.created_at, decided))
    return samples, not_recorded, pairs


async def turnaround(db: AsyncSession, read_scope: CardReadScope, period: Period) -> dict[str, Any]:
    """GOV-07 **elapsed** calendar days, request to decision, per instrument (D-35).

    Only reliable instants are used, and nothing is reconstructed:

    * **ADR**: ``created_at`` to ``signed_at``, decisions signed in the period.
      Both are stored once and never rewritten (a signed ADR is frozen).
    * **ARB**: ``created_at`` to the first recorded approve / reject transition
      in the period. Deferral is never final (D-35). A review decided in the
      period with no recorded transition is "not recorded": its ``decided_at``
      is overwritten on each change (I-12).
    * **Exception**: ``created_at`` (the request) to the first recorded
      approve / reject transition in the period. Decisions taken before the
      history existed are "not recorded" (current state; they carry no date).

    Instruments are never pooled. Governance-controlled processing time is
    computed for the same decisions from their recorded transitions only
    (:func:`processing_days`); working days count the same decisions on the
    confirmed business calendar (D-28, D-38, :func:`working_days_block`).
    """
    # ADR: kept whole, no card scope, as on the decisions page (D-30).
    adr_rows = await db.execute(
        select(
            ArchitectureDecision.id, ArchitectureDecision.created_at, ArchitectureDecision.signed_at
        ).where(
            ArchitectureDecision.status == "signed",
            ArchitectureDecision.signed_at.is_not(None),
        )
    )
    adr_samples: list[float] = []
    adr_pairs: list[tuple[datetime, datetime]] = []
    adr_unreliable = 0
    adr_timed: list[uuid.UUID] = []
    for adr_id, created_at, signed_at in adr_rows.all():
        if not _in_period(signed_at, period):
            continue
        days = elapsed_days(created_at, signed_at)
        if days is None:
            adr_unreliable += 1
        else:
            adr_samples.append(days)
            adr_pairs.append((created_at, signed_at))
            adr_timed.append(adr_id)

    # ARB: a review of a hidden subject card does not exist for the reader.
    reviews = list((await db.execute(select(ArbReview))).scalars().all())
    readable = await read_scope.readable_card_ids(
        db, {r.subject_card_id for r in reviews if r.subject_card_id}, mode="module"
    )
    reviews = [r for r in reviews if not r.subject_card_id or r.subject_card_id in readable]
    arb_first = await _first_decisions(db, INSTRUMENT_ARB, ARB_DECISION_STATUSES)
    arb_samples, arb_not_recorded, arb_pairs = _split(
        reviews,
        arb_first,
        period,
        lambda r: r.status in ARB_DECISION_STATUSES and _in_period(r.decided_at, period),
    )

    # Exceptions: an exception about a hidden card is omitted (D-30).
    exceptions = list((await db.execute(select(StandardException))).scalars().all())
    hidden = await read_scope.hidden_card_ids(
        db, {e.card_id for e in exceptions if e.card_id}, mode="module"
    )
    exceptions = [e for e in exceptions if e.card_id not in hidden]
    exc_first = await _first_decisions(db, INSTRUMENT_EXCEPTION, EXCEPTION_DECISION_STATUSES)
    exc_samples, exc_not_recorded, exc_pairs = _split(
        exceptions,
        exc_first,
        period,
        lambda e: e.status in EXCEPTION_DECISION_STATUSES,
    )

    def decided_in_period(first: dict[uuid.UUID, datetime], records: list[Any]):
        return [r.id for r in records if _in_period(first.get(r.id), period)]

    processing = {
        "adr": processing_figure(
            _processing_for(
                await _chains(db, INSTRUMENT_ADR, adr_timed), adr_timed, ("signed",), ADR_WAITING
            )
        ),
        "arb": processing_figure(
            _processing_for(
                await _chains(db, INSTRUMENT_ARB, decided_in_period(arb_first, reviews)),
                decided_in_period(arb_first, reviews),
                ARB_DECISION_STATUSES,
                ARB_WAITING,
            )
        ),
        "exception": processing_figure(
            _processing_for(
                await _chains(db, INSTRUMENT_EXCEPTION, decided_in_period(exc_first, exceptions)),
                decided_in_period(exc_first, exceptions),
                EXCEPTION_DECISION_STATUSES,
                (),
            )
        ),
    }

    return {
        "status": "ok",
        "measure": "elapsed",
        "unit": "calendar_days",
        "instruments": {
            "adr": elapsed_figure(adr_samples, adr_unreliable, "created_to_signed"),
            "arb": elapsed_figure(arb_samples, arb_not_recorded, "created_to_first_decision"),
            "exception": {
                **elapsed_figure(exc_samples, exc_not_recorded, "requested_to_first_decision"),
                # Decisions before the history carry no date: a current-state count.
                "not_recorded_temporal": kpis.CURRENT_STATE,
            },
        },
        # D-39: governance-controlled time, reported beside elapsed, never instead.
        "processing_time": {
            "status": "ok",
            "measure": "governance_controlled",
            "unit": "calendar_days",
            "instruments": processing,
        },
        # D-28 / D-38: the same elapsed decisions in working days, only where
        # the business calendar is confirmed for the period (Batch 3.3).
        "working_days": working_days_block(
            await load_calendar(db, await get_fiscal_year_start(db)),
            period,
            {"adr": adr_pairs, "arb": arb_pairs, "exception": exc_pairs},
        ),
    }


def working_days_figure(
    calendar: BusinessCalendar, pairs: list[tuple[datetime, datetime]]
) -> dict[str, Any]:
    """One instrument's elapsed working days: median and slowest (D-28, D-38).

    A decision whose span reaches into a fiscal year without a confirmed
    calendar has no working-day duration and is counted by cause, never
    estimated; with no timed decision the figure is Not Available, never zero."""
    results = [calendar.working_days(start, end) for start, end in pairs]
    samples = [days for days in results if days is not None]
    untimed = len(results) - len(samples)
    not_computable = {"calendar_not_confirmed": untimed} if untimed else {}
    if not samples:
        return {
            "status": "not_available",
            "reason": {"code": "no_recorded_decisions"},
            "decisions": 0,
            "not_computable": not_computable,
        }
    return {
        "status": "ok",
        "decisions": len(samples),
        "median_days": round(statistics.median(samples), 1),
        "max_days": max(samples),
        "not_computable": not_computable,
    }


def working_days_block(
    calendar: BusinessCalendar,
    period: Period,
    pairs_by_instrument: dict[str, list[tuple[datetime, datetime]]],
) -> dict[str, Any]:
    """GOV-07 in working days, or Not Available while the period is not valid.

    The period is valid only when every fiscal year it touches has a confirmed
    calendar (D-38); otherwise no instrument gets a working-day figure and the
    unconfirmed years are named."""
    years = calendar.fiscal_years(period.start, period.end - timedelta(days=1))
    missing = calendar.unconfirmed(years)
    if missing:
        return _not_available({"code": "calendar_not_confirmed", "fiscal_years": missing})
    return {
        "status": "ok",
        "measure": "elapsed",
        "unit": "working_days",
        "instruments": {
            key: working_days_figure(calendar, pairs) for key, pairs in pairs_by_instrument.items()
        },
    }


#: Waiting states whose interval may leave governance-controlled time, when
#: explicitly attributed to the requester or an external dependency (I-21).
ADR_WAITING = ("draft",)
ARB_WAITING = ("deferred",)
#: States that can only follow an approval. A legacy ``rejected`` row is left
#: out: with no history it may never have been approved (GOV-04, I-26).
RESOLUTION_STATES = ("approved", "remediation_submitted", "remediated", "withdrawn")
#: Attributions that take an interval out of governance-controlled time.
EXCLUDABLE = (ATTRIBUTION_REQUESTER, ATTRIBUTION_EXTERNAL)


async def _chains(
    db: AsyncSession, instrument: str, record_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[GovernanceTransition]]:
    """Each record's transitions in order (only records that have any)."""
    if not record_ids:
        return {}
    rows = await db.execute(
        select(GovernanceTransition)
        .where(
            GovernanceTransition.instrument == instrument,
            GovernanceTransition.record_id.in_(record_ids),
        )
        .order_by(GovernanceTransition.occurred_at, GovernanceTransition.created_at)
    )
    chains: dict[uuid.UUID, list[GovernanceTransition]] = {}
    for t in rows.scalars().all():
        chains.setdefault(t.record_id, []).append(t)
    return chains


def _missing(record_ids: list[uuid.UUID], chains: dict) -> int:
    return sum(1 for rid in record_ids if rid not in chains)


def _processing_for(
    chains: dict[uuid.UUID, list[GovernanceTransition]],
    record_ids: list[uuid.UUID],
    outcomes: tuple[str, ...],
    waiting: tuple[str, ...],
) -> list[tuple[float | None, str | None]]:
    results = [
        processing_days(chains[rid], outcomes, waiting) for rid in record_ids if rid in chains
    ]
    return results + [(None, "history_not_recorded")] * _missing(record_ids, chains)


def processing_days(
    chain: list[Any], outcomes: tuple[str, ...], waiting: tuple[str, ...]
) -> tuple[float | None, str | None]:
    """Governance-controlled calendar days of one record, or why there are none.

    ``chain`` is the record's transitions in order. The window runs from the
    creation transition to the first transition into an ``outcome``. An
    interval in a ``waiting`` state is left out only when the transition that
    entered it attributes it to the requester or an external dependency **with
    a reason**; attributed to governance it stays in; unattributed, the record
    cannot be timed (D-39, I-21, I-22). Returns ``(days, None)`` or
    ``(None, cause)`` with cause ``history_not_recorded`` / ``history_broken``
    / ``delay_unattributed`` / ``no_decision``.
    """
    if not chain or chain[0].from_status is not None:
        return None, "history_not_recorded"
    for prev, nxt in zip(chain, chain[1:]):
        if nxt.from_status != prev.to_status or nxt.occurred_at < prev.occurred_at:
            return None, "history_broken"
    end = next((i for i, t in enumerate(chain) if t.to_status in outcomes), None)
    if end is None:
        return None, "no_decision"
    excluded = 0.0
    for entered, left in zip(chain[:end], chain[1 : end + 1]):
        if entered.to_status not in waiting:
            continue
        if entered.delay_attribution is None:
            return None, "delay_unattributed"
        if entered.delay_attribution in EXCLUDABLE and (entered.reason or "").strip():
            excluded += (left.occurred_at - entered.occurred_at).total_seconds()
    total = (chain[end].occurred_at - chain[0].occurred_at).total_seconds()
    return (total - excluded) / 86400, None


def processing_figure(results: list[tuple[float | None, str | None]]) -> dict[str, Any]:
    """Median and slowest governance-controlled days, with untimed records by cause.

    Not Available when no record could be timed — never a zero, and never the
    elapsed figure in its place (D-39)."""
    samples = [days for days, _ in results if days is not None]
    causes: dict[str, int] = {}
    for _, cause in results:
        if cause is not None:
            causes[cause] = causes.get(cause, 0) + 1
    if not samples:
        return {
            "status": "not_available",
            "reason": {"code": "processing_not_computable"},
            "decisions": 0,
            "not_computable": causes,
        }
    return {
        "status": "ok",
        "decisions": len(samples),
        "median_days": round(statistics.median(samples), 1),
        "max_days": round(max(samples), 1),
        "not_computable": causes,
    }


def _is_approval(t: Any) -> bool:
    """A move into ``approved`` from a request or a rejection. A returned
    remediation (``remediation_submitted -> approved``) is not an approval."""
    return t.to_status == "approved" and t.from_status in ("requested", "rejected")


def approval_cycles(chain: list[Any]) -> list[tuple[Any, list[Any]]]:
    """Each recorded approval cycle of a chain, oldest first (I-31).

    A cycle opens with an approval decision — which carries the expiry that
    approval granted — and holds every transition up to, not including, the
    next approval decision. Returns ``(approval, transitions)`` pairs."""
    starts = [i for i, t in enumerate(chain) if _is_approval(t)]
    ends = starts[1:] + [len(chain)]
    return [(chain[i], chain[i:j]) for i, j in zip(starts, ends)]


#: An approval cycle whose expiry is not on record (approved before it was kept).
UNKNOWN = object()


def effective_expiry(cycle: list[Any]) -> Any:
    """The expiry in force at the end of a (period-cut) cycle (I-31, I-35).

    The approval's own expiry, replaced by each recorded ``expiry_changed``
    event in the cycle, in order. ``UNKNOWN`` when the approval carries no
    expiry and no later change set one; a ``None`` expiry means "no expiry"."""
    expiry = cycle[0].approved_expiry_date if cycle[0].approved_expiry_date else UNKNOWN
    for t in cycle[1:]:
        if getattr(t, "event_kind", None) == EVENT_EXPIRY_CHANGED:
            expiry = t.approved_expiry_date
    return expiry


def classify_resolution(chain: list[Any], approved_expiry: date) -> str:
    """One eligible approval cycle's GOV-04 outcome (D-40, I-26, I-31).

    ``chain`` is the cycle's transitions (see :func:`approval_cycles`) **up to
    the end of the reporting period**, so a completed period's figure never
    changes with what happened after it. ``remediated_on_time`` only when the
    verification is recorded on or before the expiry that cycle's approval
    granted; a later one is ``remediated_late``.
    Otherwise the state the chain reached decides: rejection and withdrawal
    are administrative outcomes, never remediation; awaiting verification
    (``unverified``) and plain expiry are unresolved."""
    verified = next((t for t in chain if t.to_status == "remediated"), None)
    if verified is not None:
        on_time = verified.occurred_at.date() <= approved_expiry
        return "remediated_on_time" if on_time else "remediated_late"
    state = chain[-1].to_status if chain else None
    if state == "withdrawn":
        return "withdrawn"
    if state == "rejected":
        return "rejected"
    if state == "remediation_submitted":
        return "awaiting_verification"
    if state == "approved":
        return "expired_unresolved"
    return "not_recorded"


def _until_period_end(chain: list[Any], period: Period) -> list[Any]:
    """The transitions recorded before the period's (exclusive) end."""
    return [t for t in chain if t.occurred_at.date() < period.end]


async def exception_resolution(
    db: AsyncSession, read_scope: CardReadScope, period: Period
) -> dict[str, Any]:
    """GOV-04: share of due exceptions resolved by **verified** remediation (D-40).

    Eligible population (I-26, I-31): exceptions about a card the viewer may
    read with an **approval cycle** recorded before the period's end whose
    expiry in force by then — the approval's own, or the latest recorded
    ``expiry_changed`` event in that cycle (I-35) — falls in the period and has
    passed. Each exception counts once, through its latest such cycle — the
    applicable one — and that cycle's transitions up to the period's end decide
    the outcome. Every due cycle, earlier ones included, is also classified in
    a separate ``approval_cycles`` breakdown counted in cycles, never added to
    the exception counts. "Has passed" uses today's date only while
    the period is still running; a completed period is judged from its own
    boundaries and history, so later events never rewrite it. Numerator:
    remediation verified on or before the cycle's approved expiry. Everything
    else is reported in its own bucket and never in the numerator: remediated
    late, withdrawn, rejected after approval, awaiting verification, expired
    unresolved. Due exceptions whose approval predates the history, or whose
    cycle was approved before its expiry was kept, are "lifecycle not
    recorded"; no expiry is reconstructed for them. Requests rejected in the
    period are counted apart.
    """
    cutoff = date.today() if period.is_current else period.end

    def due(expiry: date | None) -> bool:
        return expiry is not None and period.start <= expiry < period.end and expiry < cutoff

    exceptions = list((await db.execute(select(StandardException))).scalars().all())
    hidden = await read_scope.hidden_card_ids(
        db, {e.card_id for e in exceptions if e.card_id}, mode="module"
    )
    exceptions = [e for e in exceptions if e.card_id not in hidden]
    chains = await _chains(db, INSTRUMENT_EXCEPTION, [e.id for e in exceptions])

    buckets = {
        "remediated_on_time": 0,
        "remediated_late": 0,
        "withdrawn": 0,
        "rejected": 0,
        "awaiting_verification": 0,
        "expired_unresolved": 0,
    }
    cycle_buckets = dict.fromkeys(buckets, 0)
    not_recorded = 0
    rejected_requests = 0
    for e in exceptions:
        full = chains.get(e.id, [])
        rejected_requests += sum(
            1
            for t in full
            if t.from_status == "requested"
            and t.to_status == "rejected"
            and _in_period(t.occurred_at, period)
        )
        cycles = approval_cycles(_until_period_end(full, period))
        if not cycles:
            recorded = bool(full) and full[0].from_status is None
            # A recorded lifecycle with no approval was never a waiver; an
            # approval-type state with no recorded approval predates the history.
            if not recorded and e.status in RESOLUTION_STATES and due(e.expiry_date):
                not_recorded += 1
            continue
        # Each cycle against the expiry in force for it by the period's end. A
        # cycle whose expiry is not on record is never given one — not the
        # current date, nor another cycle's.
        expiries = [(effective_expiry(c), c) for _, c in cycles]
        due_cycles = [(x, c) for x, c in expiries if x is not UNKNOWN and due(x)]
        for x, c in due_cycles:
            outcome = classify_resolution(c, x)
            if outcome != "not_recorded":
                cycle_buckets[outcome] += 1
        if not due_cycles:
            if any(x is UNKNOWN for x, _ in expiries) and due(e.expiry_date):
                not_recorded += 1
            continue
        # The exception counts once, through its applicable (latest due) cycle.
        expiry, cycle = due_cycles[-1]
        outcome = classify_resolution(cycle, expiry)
        if outcome == "not_recorded":
            not_recorded += 1
        else:
            buckets[outcome] += 1

    eligible = sum(buckets.values())
    common = {
        # The primary figure and its distribution count EXCEPTIONS (each once).
        "unit_of_count": "exceptions",
        "eligible": eligible,
        "outcomes": buckets,
        "not_recorded": not_recorded,
        "rejected_requests": rejected_requests,
        "basis": "verified_by_expiry",
        # Every approval cycle that fell due, earlier rejected ones included,
        # counted in APPROVAL CYCLES and kept apart: its total may exceed the
        # exception count and is never added to it (I-31).
        "approval_cycles": {
            "unit_of_count": "approval_cycles",
            "eligible": sum(cycle_buckets.values()),
            "outcomes": cycle_buckets,
        },
    }
    if eligible == 0:
        return {"status": "not_available", "reason": {"code": "no_eligible_exceptions"}, **common}
    return {
        "status": "ok",
        "value": round(100 * buckets["remediated_on_time"] / eligible, 1),
        "unit": "percent",
        **common,
    }


#: GOV-05 outcomes of an eligible decision; they always sum to ``eligible``.
GOV05_OUTCOMES = (
    "verified_on_time",
    "verified_late",
    impl_service.STATE_AWAITING,
    impl_service.STATE_IN_PROGRESS,
    impl_service.STATE_NO_PLAN,
)


async def approved_decisions(
    db: AsyncSession, read_scope: CardReadScope
) -> list[tuple[str, uuid.UUID]]:
    """Every decision that can be implemented, as ``(kind, id)``: signed ADRs
    (kept whole, no card scope, as on the decisions page) and approved ARB
    reviews whose subject card the viewer may read (D-30)."""
    adr_ids = (
        (
            await db.execute(
                select(ArchitectureDecision.id).where(ArchitectureDecision.status == "signed")
            )
        )
        .scalars()
        .all()
    )
    reviews = (
        await db.execute(
            select(ArbReview.id, ArbReview.subject_card_id).where(ArbReview.status == "approved")
        )
    ).all()
    readable = await read_scope.readable_card_ids(
        db, {subject for _, subject in reviews if subject}, mode="module"
    )
    return [(DECISION_ADR, i) for i in adr_ids] + [
        (DECISION_ARB, rid) for rid, subject in reviews if not subject or subject in readable
    ]


async def decision_implementation(
    db: AsyncSession, read_scope: CardReadScope, period: Period
) -> dict[str, Any]:
    """GOV-05: approved decisions **independently verified** as implemented by
    their **original** approved deadline (D-32, D-41).

    Eligible: approved decisions whose original deadline falls in the period
    and has passed (today while the period runs, its end once closed). Each
    counts once, judged from its recorded history up to the period's end, so a
    closed period never changes. Numerator: verification recorded on or before
    the original deadline; completed actions alone never count. Every other
    eligible decision sits in its own bucket — verified late, awaiting
    verification, in progress, no plan (no actions) — and the buckets sum to
    ``eligible``. Performance against **revised** deadlines is reported apart.

    Decisions with no approved deadline cannot be timed, so they are outside
    the rate's denominator — never hidden: they are counted in
    ``excluded.no_deadline`` and in ``planning_coverage``, the share of
    approved decisions that have both a deadline and at least one action
    (current state)."""
    cutoff = date.today() if period.is_current else period.end
    decisions = await approved_decisions(db, read_scope)
    impls = {
        (i.decision_kind, i.decision_id): i
        for i in (await db.execute(select(DecisionImplementation))).scalars().all()
    }
    action_rows = (
        await db.execute(
            select(Todo.source_kind, Todo.source_id, Todo.created_at).where(
                Todo.source_kind.is_not(None)
            )
        )
    ).all()
    actions: dict[tuple[str, uuid.UUID], list[datetime]] = {}
    for kind, source_id, created_at in action_rows:
        actions.setdefault((kind, source_id), []).append(created_at)
    instrument_kind = {INSTRUMENT_ADR_IMPL: DECISION_ADR, INSTRUMENT_ARB_IMPL: DECISION_ARB}
    events: dict[tuple[str, uuid.UUID], list[GovernanceTransition]] = {}
    rows = await db.execute(
        select(GovernanceTransition)
        .where(GovernanceTransition.instrument.in_(tuple(instrument_kind)))
        .order_by(GovernanceTransition.occurred_at, GovernanceTransition.created_at)
    )
    for t in rows.scalars().all():
        events.setdefault((instrument_kind[t.instrument], t.record_id), []).append(t)

    outcomes = dict.fromkeys(GOV05_OUTCOMES, 0)
    by_instrument = {
        k: {"eligible": 0, "verified_on_time": 0} for k in (DECISION_ADR, DECISION_ARB)
    }
    revised = verified_within_revised = 0
    with_deadline = with_actions = planned = 0
    for key in decisions:
        impl = impls.get(key)
        original = impl.original_due_date if impl else None
        has_actions = bool(actions.get(key))
        with_deadline += original is not None
        with_actions += has_actions
        planned += original is not None and has_actions
        if original is None or not (period.start <= original < period.end and original < cutoff):
            continue
        history = events.get(key, [])
        outcome = impl_service.outcome_at(
            original, impl.verified_at, history, actions.get(key, []), period.end
        )
        outcomes[outcome] += 1
        by_instrument[key[0]]["eligible"] += 1
        by_instrument[key[0]]["verified_on_time"] += outcome == "verified_on_time"
        in_force = impl_service.due_in_force(original, history, period.end)
        if in_force != original:
            revised += 1
            verified = impl.verified_at is not None and impl.verified_at.date() < period.end
            verified_within_revised += verified and impl.verified_at.date() <= in_force

    eligible = sum(outcomes.values())
    total = len(decisions)
    common: dict[str, Any] = {
        "unit_of_count": "decisions",
        "basis": "verified_by_original_deadline",
        "eligible": eligible,
        "outcomes": outcomes,
        "overdue_or_unverified": eligible
        - outcomes["verified_on_time"]
        - outcomes["verified_late"],
        "revised_deadlines": {
            "revised": revised,
            "verified_within_revised": verified_within_revised,
        },
        "by_instrument": by_instrument,
        # Never hidden: decisions the rate cannot time, disclosed beside it.
        "excluded": {"no_deadline": total - with_deadline},
        "planning_coverage": {
            "temporal": kpis.CURRENT_STATE,
            "approved_decisions": total,
            "with_deadline": with_deadline,
            "with_actions": with_actions,
            "planned": planned,
            "without_deadline": total - with_deadline,
            "without_actions": total - with_actions,
            "percentage": round(100 * planned / total, 1) if total else None,
        },
    }
    if eligible == 0:
        reason = "no_approved_decisions" if total == 0 else "no_eligible_decisions"
        return {"status": "not_available", "reason": {"code": reason}, **common}
    return {
        "status": "ok",
        "value": round(100 * outcomes["verified_on_time"] / eligible, 1),
        "unit": "percent",
        **common,
    }


async def review_coverage(db: AsyncSession, read_scope: CardReadScope) -> dict[str, Any]:
    """GOV-01 over the ACTIVE initiatives the viewer may read, completed and on
    hold included (D-37, I-59). Current state."""
    initiatives = await exe.load_visible_initiatives(db, read_scope)
    states, _, reviews = await ea.classify(db, initiatives)
    return ea.coverage_figures(states, reviews)


async def governed_delivery(
    db: AsyncSession, read_scope: CardReadScope, today: date, general: dict[str, Any]
) -> dict[str, Any]:
    """GOV-09 (D-37, D-20, I-61): delivery health of governed and ungoverned
    initiatives compared, exempt and unknown shown apart, never compared.

    The groups reuse the TR-03 calculation and its reporting coverage over the
    same in-flight population; a group's rate is shown only when at least five
    of its initiatives reported. An observed difference is an association, not
    an effect of governance."""
    initiatives = await exe.load_visible_initiatives(db, read_scope)
    states, _, _ = await ea.classify(db, initiatives)
    latest = (
        await portfolio.latest_reports(db, [c.id for c in initiatives], as_of=today)
        if bool(general.get("ppmEnabled", False))
        else None
    )
    stale = exe.staleness_days(general)
    groups: dict[str, dict[str, Any]] = {}
    for state in ea.STATES:
        members = [c for c in initiatives if states[c.id] == state]
        summary = exe.summarize_delivery_health(members, latest, today=today, stale=stale)
        groups[state] = ea.group_figure(summary, len(members))
    common = {
        "temporal": kpis.CURRENT_STATE,
        "as_of": today.isoformat(),
        "minimum_group_size": ea.MIN_GROUP,
        "interpretation": "association_not_causation",
        "source": exe.SOURCE_INITIATIVE_STATUS if latest is None else exe.SOURCE_PPM_REPORTS,
        "groups": groups,
    }
    if groups[ea.GOVERNED]["in_flight"] + groups[ea.UNGOVERNED]["in_flight"] == 0:
        return {"status": "not_available", "reason": {"code": "no_required_reviews"}, **common}
    return {"status": "ok", "comparison": ea.comparison(groups), **common}


async def _impact(
    db: AsyncSession,
    read_scope: CardReadScope,
    period: Period,
    rsk01_link: dict[str, Any] | None,
    rsk01_previous: dict[str, Any] | None,
    grc_enabled: bool,
    general: dict[str, Any] | None = None,
) -> dict[str, Any]:
    today = date.today()
    if grc_enabled:
        # Only explicitly linked risks are architecture-related (D-36, D-42).
        figures = await risk_governance.architecture_risk_figures(db, read_scope, today)
    else:
        figures = {
            "status": "not_available",
            "reason": {"code": "module_disabled", "module": "grc"},
            "temporal": kpis.CURRENT_STATE,
        }
    return {
        "architecture_risks": figures,
        "architecture_risk_tile": linkage.apply_link(
            kpis.architecture_risk_tile(period, figures, today, rsk01_previous), rsk01_link
        ),
        # GOV-09: governed vs ungoverned delivery, association only (D-37, D-20).
        "governed_delivery": await governed_delivery(db, read_scope, today, general or {}),
        # Benefits and financial value arrive with the Phase 4 register.
        "business_value": _not_available({"code": "later_phase", "phase": 4}),
    }


async def governance_summary(
    db: AsyncSession,
    read_scope: CardReadScope,
    period: Period,
    *,
    gov03_link: dict[str, Any] | None,
    gov05_link: dict[str, Any] | None = None,
    gov05_previous: dict[str, Any] | None = None,
    rsk01_link: dict[str, Any] | None = None,
    rsk01_previous: dict[str, Any] | None = None,
    grc_enabled: bool = True,
    gov01_link: dict[str, Any] | None = None,
    gov01_previous: dict[str, Any] | None = None,
    general: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Activity, effectiveness and impact for the selected period, kept apart.

    GOV-05 is returned twice from one calculation: the breakdown
    (``decision_implementation``) and the KPI tile built from it
    (``decision_implementation_tile``) with its KPI-card target and the
    previous period's verified value."""
    effectiveness = await _effectiveness(db, read_scope, period, gov03_link)
    effectiveness["decision_implementation_tile"] = linkage.apply_link(
        kpis.governance_effectiveness(
            period, effectiveness["decision_implementation"], gov05_previous
        ),
        gov05_link,
    )
    activity = await _activity(db, read_scope, period)
    # GOV-01 is governance activity (GOVERNANCE_MEASUREMENT_MODEL §1): reviews
    # happened where they were required, no value claim.
    coverage = await review_coverage(db, read_scope)
    activity["review_coverage"] = coverage
    activity["review_coverage_tile"] = linkage.apply_link(
        kpis.review_coverage_tile(period, coverage, date.today(), gov01_previous), gov01_link
    )
    return {
        "period": period.to_dict(),
        "activity": activity,
        "effectiveness": effectiveness,
        "impact": await _impact(
            db, read_scope, period, rsk01_link, rsk01_previous, grc_enabled, general
        ),
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


async def review_coverage_rows(
    db: AsyncSession,
    read_scope: CardReadScope,
    *,
    include_reviews: bool,
    include_adrs: bool,
) -> list[dict[str, Any]]:
    """The GOV-01 drill-down (I-62): every initiative in the population with
    its state and latest assessment; its subject reviews with ``arb.view``;
    its signed ADRs, as context never counted, with ``adr.view``."""
    initiatives = await exe.load_visible_initiatives(db, read_scope)
    states, latest, reviews = await ea.classify(db, initiatives)
    adrs = await ea.signed_adrs(db, [c.id for c in initiatives]) if include_adrs else {}
    deciders = {a.decided_by for a in latest.values() if a.decided_by}
    names = await _names(db, deciders)
    rows = []
    for c in sorted(initiatives, key=lambda c: (ea.STATES.index(states[c.id]), c.name.lower())):
        assessment = latest.get(c.id)
        own = reviews.get(c.id, [])
        rows.append(
            {
                "id": str(c.id),
                "name": c.name,
                "subtype": c.subtype,
                "path": f"/cards/{c.id}",
                "state": states[c.id],
                "review_in_progress": states[c.id] == ea.UNGOVERNED and ea.review_in_progress(own),
                "assessment": ea.assessment_payload(assessment, names) if assessment else None,
                "reviews": [
                    {
                        "id": str(r.id),
                        "title": r.title,
                        "status": r.status,
                        "path": f"/arb?review={r.id}",
                    }
                    for r in own
                ]
                if include_reviews
                else None,
                "signed_adrs": [
                    {
                        "id": str(a.id),
                        "label": f"{a.reference_number} — {a.title}",
                        "path": f"/ea-delivery/adr/{a.id}/preview",
                    }
                    for a in adrs.get(c.id, [])
                ]
                if include_adrs
                else None,
            }
        )
    return rows


async def governed_delivery_rows(
    db: AsyncSession, read_scope: CardReadScope, today: date, general: dict[str, Any]
) -> list[dict[str, Any]]:
    """The GOV-09 drill-down (I-62): in-flight initiatives with their
    governance group and delivery state, from the TR-03 rows."""
    initiatives = await exe.load_visible_initiatives(db, read_scope)
    states, _, _ = await ea.classify(db, initiatives)
    ppm = bool(general.get("ppmEnabled", False))
    latest = (
        await portfolio.latest_reports(db, [c.id for c in initiatives], as_of=today)
        if ppm
        else None
    )
    rows = exe.delivery_rows(initiatives, latest, today=today, stale=exe.staleness_days(general))
    for row in rows:
        row["group"] = states.get(uuid.UUID(str(row["id"])), ea.UNKNOWN)
        row["path"] = f"/ppm/{row['id']}" if ppm else f"/cards/{row['id']}"
    return rows


async def _names(db: AsyncSession, ids: set) -> dict:
    if not ids:
        return {}
    from app.models.user import User

    rows = await db.execute(select(User.id, User.display_name).where(User.id.in_(ids)))
    return dict(rows.all())
