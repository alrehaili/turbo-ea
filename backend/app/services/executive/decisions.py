"""Executive decisions and escalations (DEC-01, DEC-02).

* **Risks** (D-04, approved 2026-10-24): *open* is any status but ``closed`` /
  ``accepted``; *executive-escalated* is an open risk whose residual level (or
  initial level when none is assessed) is ``critical``, or ``high`` and overdue
  by the register's own rule (target date passed, not ``mitigated``). Category
  ``strategic`` is deliberately **not** an escalation signal, and there is no
  manual escalation yet.
* **Operational governance pipeline**: ADRs ``in_review`` (awaiting signatures),
  ARB reviews ``scheduled`` / ``deferred``, standard exceptions ``requested``.
  These are routine governance activity, not executive escalations: no approved
  rule escalates any of them, so they never enter the CEO attention panel and
  are grouped apart (``group``) wherever they are listed.

Counts are aggregates over records the caller's scope admits; listing a record
needs that module's own view permission (D-03: the executive permission grants
no record access). Records about hidden cards follow D-30 exactly as their own
modules do: an ARB review or an exception about a hidden card is omitted; an
ADR is a multi-card record and is kept, with no linked card named here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.risk import Risk
from app.models.tech_standard import StandardException, TechStandard
from app.models.user import User
from app.services.card_read_scope import CardReadScope

CLOSED_RISK_STATUSES = frozenset({"closed", "accepted"})
#: Records meeting an approved executive-escalation rule (D-04: risks only).
EXECUTIVE_ESCALATION = "executive_escalation"
#: Routine governance activity: shown, counted, never escalated.
OPERATIONAL_PIPELINE = "operational_pipeline"
PENDING_ARB_STATUSES = ("scheduled", "deferred")


def _risk_level(risk: Risk) -> str:
    return risk.residual_level or risk.initial_level


def is_escalated(risk: Risk, today: date) -> bool:
    """The D-04 automated escalation rule for one risk."""
    if risk.status in CLOSED_RISK_STATUSES:
        return False
    level = _risk_level(risk)
    if level == "critical":
        return True
    overdue = (
        risk.target_resolution_date is not None
        and risk.target_resolution_date < today
        and risk.status != "mitigated"
    )
    return level == "high" and overdue


@dataclass(frozen=True)
class RiskPicture:
    open: int
    mitigated: int
    escalated: list[Risk]


def classify_risks(risks: Sequence[Risk], today: date) -> RiskPicture:
    """Open, mitigated (a subset of open) and escalated, reported separately."""
    open_risks = [r for r in risks if r.status not in CLOSED_RISK_STATUSES]
    escalated = [r for r in open_risks if is_escalated(r, today)]
    rank = {"critical": 0, "high": 1}
    # Most severe first, then oldest first.
    escalated.sort(key=lambda r: (rank.get(_risk_level(r), 2), r.created_at or datetime.max))
    return RiskPicture(
        open=len(open_risks),
        mitigated=sum(1 for r in open_risks if r.status == "mitigated"),
        escalated=escalated,
    )


def _age_days(moment: datetime | date | None, today: date) -> int | None:
    if moment is None:
        return None
    day = moment.date() if isinstance(moment, datetime) else moment
    return max(0, (today - day).days)


async def _display_names(db: AsyncSession, ids: set) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = await db.execute(select(User.id, User.display_name).where(User.id.in_(ids)))
    return dict(rows.all())


async def risk_items(db: AsyncSession, risks: Sequence[Risk], today: date) -> list[dict[str, Any]]:
    names = await _display_names(db, {r.owner_id for r in risks})
    return [
        {
            "kind": "risk",
            "id": str(r.id),
            "reference": r.reference,
            "title": r.title,
            "level": _risk_level(r),
            "status": r.status,
            "owner": names.get(r.owner_id),
            "due_date": r.target_resolution_date.isoformat() if r.target_resolution_date else None,
            "age_days": _age_days(r.created_at, today),
            "path": f"/grc/risks/{r.id}",
        }
        for r in risks
    ]


async def pending_adrs(db: AsyncSession) -> list[ArchitectureDecision]:
    rows = await db.execute(
        select(ArchitectureDecision)
        .where(ArchitectureDecision.status == "in_review")
        .order_by(ArchitectureDecision.updated_at)
    )
    return list(rows.scalars().all())


def adr_items(adrs: Sequence[ArchitectureDecision], today: date) -> list[dict[str, Any]]:
    out = []
    for a in adrs:
        signatories = a.signatories or []
        out.append(
            {
                "kind": "adr",
                "id": str(a.id),
                "reference": a.reference_number,
                "title": a.title,
                "pending_signatures": sum(
                    1 for s in signatories if isinstance(s, dict) and s.get("status") != "signed"
                ),
                "age_days": _age_days(a.updated_at, today),
                "path": f"/ea-delivery/adr/{a.id}/preview",
            }
        )
    return out


async def pending_arb(db: AsyncSession, read_scope: CardReadScope) -> list[ArbReview]:
    rows = await db.execute(
        select(ArbReview)
        .where(ArbReview.status.in_(PENDING_ARB_STATUSES))
        .order_by(ArbReview.created_at)
    )
    reviews = list(rows.scalars().all())
    readable = await read_scope.readable_card_ids(
        db, {r.subject_card_id for r in reviews if r.subject_card_id}, mode="module"
    )
    # A review of a hidden subject card does not exist for the reader (D-30).
    return [r for r in reviews if not r.subject_card_id or r.subject_card_id in readable]


def arb_items(reviews: Sequence[ArbReview], today: date) -> list[dict[str, Any]]:
    return [
        {
            "kind": "arb",
            "id": str(r.id),
            "title": r.title,
            "status": r.status,
            "age_days": _age_days(r.created_at, today),
            "path": "/arb",
        }
        for r in reviews
    ]


async def pending_exceptions(
    db: AsyncSession, read_scope: CardReadScope
) -> list[tuple[StandardException, str]]:
    rows = await db.execute(
        select(StandardException, TechStandard.name)
        .join(TechStandard, TechStandard.id == StandardException.standard_id)
        .where(StandardException.status == "requested")
        .order_by(StandardException.created_at)
    )
    pairs = [(e, name) for e, name in rows.all()]
    hidden = await read_scope.hidden_card_ids(
        db, {e.card_id for e, _ in pairs if e.card_id}, mode="module"
    )
    # An exception about a hidden card is omitted, as on the standards page (D-30).
    return [(e, name) for e, name in pairs if e.card_id not in hidden]


def exception_items(
    pairs: Sequence[tuple[StandardException, str]], today: date
) -> list[dict[str, Any]]:
    return [
        {
            "kind": "exception",
            "id": str(e.id),
            "title": name,
            "status": e.status,
            "due_date": e.expiry_date.isoformat() if e.expiry_date else None,
            "age_days": _age_days(e.created_at, today),
            "path": "/tech-standards",
        }
        for e, name in pairs
    ]


def section(
    count: int,
    items: list[dict[str, Any]],
    *,
    can_list: bool,
    group: str,
    enabled: bool = True,
) -> dict[str, Any]:
    """A count always (scoped), the records only with the module's permission."""
    if not enabled:
        return {"status": "disabled", "group": group}
    if not can_list:
        return {"status": "restricted", "group": group, "count": count, "items": None}
    return {"status": "ok", "group": group, "count": count, "items": items}
