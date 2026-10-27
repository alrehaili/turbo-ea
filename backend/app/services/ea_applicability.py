"""EA governance applicability and review coverage (D-37, D-20; Batch 3.6).

* **Applicability** is an authorized, append-only assessment per Initiative
  (``required`` / ``not_required``, criteria reference, justification, actor,
  time). The latest row is the current status; no row means **Undetermined**,
  which is never exempt and never compliant (D-37).
* **Completed review** (I-58): an ARB review whose subject card is the
  initiative and whose status is ``approved`` — by its own record the EA review
  of that initiative. Rejected, deferred and scheduled reviews do not complete
  it; signed ADRs are context only and never counted.
* **States** of an initiative: ``governed`` (required, completed),
  ``ungoverned`` (required, not completed), ``exempt`` (assessed not
  required), ``unknown`` (undetermined).

Helpers flush at most and never commit.

[FORK]
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.architecture_decision_card import ArchitectureDecisionCard
from app.models.card import Card
from app.models.ea_review_applicability import DECISIONS, NOT_REQUIRED, EaReviewApplicability
from app.services.event_bus import event_bus
from app.services.governance_transitions import LifecycleError

INITIATIVE_TYPE = "Initiative"
ASSESS_PERMISSION = "governance.assess_applicability"
MAX_CRITERIA = 300

GOVERNED = "governed"
UNGOVERNED = "ungoverned"
EXEMPT = "exempt"
UNKNOWN = "unknown"
STATES = (GOVERNED, UNGOVERNED, EXEMPT, UNKNOWN)

#: ARB statuses that are a review under way, not a completed one.
IN_PROGRESS_REVIEW = ("scheduled", "deferred")

#: D-20: the fewest initiatives that must have reported for a group's rate.
MIN_GROUP = 5


def _text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


async def record_assessment(
    db: AsyncSession,
    card: Card,
    decision: str | None,
    criteria_reference: str | None,
    justification: str | None,
    actor_id: uuid.UUID,
) -> EaReviewApplicability:
    """Append one applicability decision for an ACTIVE Initiative (D-37).

    Every field is required: the decision, the criteria applied and why. The
    earlier assessments are kept as they were."""
    if card.type != INITIATIVE_TYPE or card.status != "ACTIVE":
        raise LifecycleError(
            422, "not_an_initiative", "Applicability is assessed for active initiatives only"
        )
    if decision not in DECISIONS:
        raise LifecycleError(422, "invalid_decision", f"Unknown decision: {decision!r}")
    criteria_reference = _text(criteria_reference)
    if criteria_reference is None or len(criteria_reference) > MAX_CRITERIA:
        raise LifecycleError(
            422,
            "criteria_required",
            "Name the applicability criteria applied (300 characters at most)",
        )
    justification = _text(justification)
    if justification is None:
        raise LifecycleError(422, "justification_required", "Say why this decision was made")
    previous = (await latest_assessments(db, [card.id])).get(card.id)
    row = EaReviewApplicability(
        card_id=card.id,
        decision=decision,
        criteria_reference=criteria_reference,
        justification=justification,
        decided_by=actor_id,
    )
    db.add(row)
    await db.flush()
    await event_bus.publish(
        "ea_applicability.assessed",
        {
            "decision": decision,
            "previous_decision": previous.decision if previous else None,
            "criteria_reference": criteria_reference,
        },
        db=db,
        card_id=card.id,
        user_id=actor_id,
    )
    return row


async def latest_assessments(
    db: AsyncSession, card_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, EaReviewApplicability]:
    """The current (latest) assessment of each initiative that has one."""
    if not card_ids:
        return {}
    rows = await db.execute(
        select(EaReviewApplicability)
        .where(EaReviewApplicability.card_id.in_(list(card_ids)))
        .order_by(EaReviewApplicability.decided_at, EaReviewApplicability.id)
    )
    out: dict[uuid.UUID, EaReviewApplicability] = {}
    for row in rows.scalars().all():
        out[row.card_id] = row
    return out


async def assessment_history(db: AsyncSession, card_id: uuid.UUID) -> list[EaReviewApplicability]:
    rows = await db.execute(
        select(EaReviewApplicability)
        .where(EaReviewApplicability.card_id == card_id)
        .order_by(EaReviewApplicability.decided_at.desc(), EaReviewApplicability.id)
    )
    return list(rows.scalars().all())


async def subject_reviews(
    db: AsyncSession, card_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[ArbReview]]:
    """ARB reviews whose subject is each initiative (the only reviews that
    can complete its required EA review, I-58)."""
    if not card_ids:
        return {}
    rows = await db.execute(
        select(ArbReview)
        .where(ArbReview.subject_card_id.in_(list(card_ids)))
        .order_by(ArbReview.created_at)
    )
    out: dict[uuid.UUID, list[ArbReview]] = {}
    for r in rows.scalars().all():
        out.setdefault(r.subject_card_id, []).append(r)
    return out


async def signed_adrs(
    db: AsyncSession, card_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[ArchitectureDecision]]:
    """Signed ADRs linked to each initiative — context only, never counted."""
    if not card_ids:
        return {}
    rows = await db.execute(
        select(ArchitectureDecisionCard.card_id, ArchitectureDecision)
        .join(
            ArchitectureDecision,
            ArchitectureDecision.id == ArchitectureDecisionCard.architecture_decision_id,
        )
        .where(
            ArchitectureDecisionCard.card_id.in_(list(card_ids)),
            ArchitectureDecision.status == "signed",
        )
    )
    out: dict[uuid.UUID, list[ArchitectureDecision]] = {}
    for card_id, adr in rows.all():
        out.setdefault(card_id, []).append(adr)
    return out


def state_of(assessment: EaReviewApplicability | None, reviews: Sequence[ArbReview]) -> str:
    """One initiative's governance state (D-37)."""
    if assessment is None:
        return UNKNOWN
    if assessment.decision == NOT_REQUIRED:
        return EXEMPT
    completed = any(r.status == "approved" for r in reviews)
    return GOVERNED if completed else UNGOVERNED


def review_in_progress(reviews: Sequence[ArbReview]) -> bool:
    return any(r.status in IN_PROGRESS_REVIEW for r in reviews)


async def classify(
    db: AsyncSession, initiatives: Sequence[Card]
) -> tuple[dict[uuid.UUID, str], dict[uuid.UUID, EaReviewApplicability], dict[uuid.UUID, list]]:
    """Each initiative's state, with the assessments and reviews behind it."""
    ids = [c.id for c in initiatives]
    latest = await latest_assessments(db, ids)
    reviews = await subject_reviews(db, ids)
    states = {cid: state_of(latest.get(cid), reviews.get(cid, [])) for cid in ids}
    return states, latest, reviews


def coverage_figures(
    states: dict[uuid.UUID, str], reviews: dict[uuid.UUID, list[ArbReview]]
) -> dict[str, Any]:
    """GOV-01 (I-59): completed required reviews ÷ initiatives requiring review,
    with every other group and the assessment coverage reported apart."""
    counts = {s: 0 for s in STATES}
    in_progress = 0
    for cid, state in states.items():
        counts[state] += 1
        if state == UNGOVERNED and review_in_progress(reviews.get(cid, [])):
            in_progress += 1
    population = len(states)
    required = counts[GOVERNED] + counts[UNGOVERNED]
    assessed = required + counts[EXEMPT]
    common: dict[str, Any] = {
        "temporal": "current_state",
        "population": population,
        "requiring_review": required,
        "review_completed": counts[GOVERNED],
        "awaiting_review": counts[UNGOVERNED],
        "review_in_progress": in_progress,
        "exempt": counts[EXEMPT],
        "undetermined": counts[UNKNOWN],
        "assessment_coverage": {
            "assessed": assessed,
            "population": population,
            "percentage": round(100 * assessed / population, 1) if population else None,
        },
        "basis": "approved_subject_review",
    }
    if required == 0:
        return {"status": "not_available", "reason": {"code": "no_required_reviews"}, **common}
    return {
        "status": "ok",
        "value": round(100 * counts[GOVERNED] / required, 1),
        "unit": "percent",
        **common,
    }


def group_figure(summary: dict[str, Any], count: int) -> dict[str, Any]:
    """One GOV-09 group from the delivery-health summary (D-20, I-61).

    The rate is shown only when at least ``MIN_GROUP`` of the group's
    initiatives reported; counts and coverage are always shown."""
    coverage = summary["coverage"]
    reported = coverage["reported"]
    shown = reported >= MIN_GROUP
    return {
        "initiatives": count,
        "in_flight": summary["in_flight"],
        "reported": reported,
        "reporting_coverage": coverage["percentage"],
        "on_track_pct": summary["on_track_pct"] if shown else None,
        "suppressed": not shown,
        "states": summary["states"],
    }


def comparison(groups: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Governed vs ungoverned only, when both rates are shown (D-20)."""
    g, u = groups[GOVERNED], groups[UNGOVERNED]
    if g["suppressed"] or u["suppressed"]:
        return {
            "status": "suppressed",
            "minimum_group_size": MIN_GROUP,
            "reason": {"code": "group_below_minimum"},
        }
    return {
        "status": "ok",
        "difference_pct_points": round(g["on_track_pct"] - u["on_track_pct"], 1),
        "interpretation": "association_not_causation",
        "minimum_group_size": MIN_GROUP,
    }


def assessment_payload(row: EaReviewApplicability, names: dict) -> dict[str, Any]:
    return {
        "decision": row.decision,
        "criteria_reference": row.criteria_reference,
        "justification": row.justification,
        "decided_by": (
            {"id": str(row.decided_by), "display_name": names.get(row.decided_by)}
            if row.decided_by
            else None
        ),
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
    }
