"""Explicit risk ↔ EA governance-record links and architecture-risk figures (D-42).

A risk is **architecture-related** only through an explicit link to an ADR, an
ARB review or a technology-standard exception (D-36, D-42.2); nothing is
inferred from its category, source or wording.

Visibility (D-42.5, I-52) follows the governance record's own module:

* an ADR is kept whole (as on the decisions page) and needs ``adr.view``;
* an ARB review needs ``arb.view`` and a readable subject card (D-30);
* an exception needs ``tech_standards.view`` and a readable card.

Aggregates (the Governance page) count with the card scope only, as every
other governance aggregate does (D-03); naming a record needs its module
permission as well. Links are added and removed one at a time, so a link the
editor cannot see is never touched.

Helpers flush at most and never commit.

[FORK]
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.risk import Risk
from app.models.risk_governance_link import (
    LINK_ADR,
    LINK_ARB,
    LINK_EXCEPTION,
    LINK_INSTRUMENTS,
    RiskGovernanceLink,
)
from app.models.tech_standard import WAIVER_ACTIVE_STATUSES, StandardException, TechStandard
from app.models.user import User
from app.services.card_read_scope import CardReadScope
from app.services.event_bus import event_bus
from app.services.executive import decisions as dec
from app.services.governance_transitions import LifecycleError
from app.services.permission_service import PermissionService

#: The module permission that names each kind of governance record.
VIEW_PERMISSION = {
    LINK_ADR: "adr.view",
    LINK_ARB: "arb.view",
    LINK_EXCEPTION: "tech_standards.view",
}


@dataclass(frozen=True)
class RecordInfo:
    """What a link may say about its governance record."""

    instrument: str
    id: uuid.UUID
    label: str
    status: str
    #: The card the record is about (ARB subject, exception card); ``None``
    #: for an ADR (kept whole) or a record about no card.
    card_id: uuid.UUID | None
    #: Signed ADR, approved review, approved and unexpired exception.
    approved: bool
    path: str


def _exception_approved(exc: StandardException, today: date) -> bool:
    return exc.status in WAIVER_ACTIVE_STATUSES and (
        exc.expiry_date is None or exc.expiry_date >= today
    )


async def describe(
    db: AsyncSession, keys: set[tuple[str, uuid.UUID]], today: date | None = None
) -> dict[tuple[str, uuid.UUID], RecordInfo]:
    """The governance records behind ``keys``; a deleted record is absent."""
    today = today or date.today()
    out: dict[tuple[str, uuid.UUID], RecordInfo] = {}
    by_kind: dict[str, set[uuid.UUID]] = {}
    for kind, rid in keys:
        by_kind.setdefault(kind, set()).add(rid)
    if by_kind.get(LINK_ADR):
        rows = await db.execute(
            select(ArchitectureDecision).where(ArchitectureDecision.id.in_(by_kind[LINK_ADR]))
        )
        for a in rows.scalars().all():
            out[(LINK_ADR, a.id)] = RecordInfo(
                LINK_ADR,
                a.id,
                f"{a.reference_number} — {a.title}",
                a.status,
                None,
                a.status == "signed",
                f"/ea-delivery/adr/{a.id}/preview",
            )
    if by_kind.get(LINK_ARB):
        rows = await db.execute(select(ArbReview).where(ArbReview.id.in_(by_kind[LINK_ARB])))
        for r in rows.scalars().all():
            out[(LINK_ARB, r.id)] = RecordInfo(
                LINK_ARB,
                r.id,
                r.title,
                r.status,
                r.subject_card_id,
                r.status == "approved",
                f"/arb?review={r.id}",
            )
    if by_kind.get(LINK_EXCEPTION):
        rows = await db.execute(
            select(StandardException, TechStandard.name)
            .join(TechStandard, TechStandard.id == StandardException.standard_id)
            .where(StandardException.id.in_(by_kind[LINK_EXCEPTION]))
        )
        for e, name in rows.all():
            out[(LINK_EXCEPTION, e.id)] = RecordInfo(
                LINK_EXCEPTION,
                e.id,
                name,
                e.status,
                e.card_id,
                _exception_approved(e, today),
                "/tech-standards",
            )
    return out


async def allowed_instruments(db: AsyncSession, user: User) -> set[str]:
    """The kinds of governance record ``user`` may name (module permission)."""
    return {
        kind
        for kind, perm in VIEW_PERMISSION.items()
        if await PermissionService.check_permission(db, user, perm)
    }


async def visible_keys(
    db: AsyncSession,
    read_scope: CardReadScope,
    infos: dict[tuple[str, uuid.UUID], RecordInfo],
    instruments: set[str] | frozenset[str] = frozenset(LINK_INSTRUMENTS),
) -> set[tuple[str, uuid.UUID]]:
    """Records the reader may see: an allowed kind, and (ARB, exception) a
    readable card. A record about no card is visible with its kind."""
    cards = {i.card_id for i in infos.values() if i.card_id is not None}
    readable = await read_scope.readable_card_ids(db, cards, mode="module") if cards else set()
    return {
        key
        for key, info in infos.items()
        if info.instrument in instruments and (info.card_id is None or info.card_id in readable)
    }


async def links_of(
    db: AsyncSession, risk_ids: list[uuid.UUID] | None = None
) -> list[RiskGovernanceLink]:
    stmt = select(RiskGovernanceLink).order_by(RiskGovernanceLink.created_at)
    if risk_ids is not None:
        stmt = stmt.where(RiskGovernanceLink.risk_id.in_(risk_ids))
    return list((await db.execute(stmt)).scalars().all())


def link_payload(link: RiskGovernanceLink, info: RecordInfo) -> dict[str, Any]:
    return {
        "instrument": info.instrument,
        "record_id": str(info.id),
        "label": info.label,
        "status": info.status,
        "approved": info.approved,
        "path": info.path,
        "linked_at": link.created_at.isoformat() if link.created_at else None,
    }


async def visible_links_for_risk(
    db: AsyncSession, user: User, read_scope: CardReadScope, risk_id: uuid.UUID
) -> list[dict[str, Any]]:
    """A risk's links the reader may see (module permission and card scope)."""
    links = await links_of(db, [risk_id])
    infos = await describe(db, {(lk.instrument, lk.record_id) for lk in links})
    visible = await visible_keys(db, read_scope, infos, await allowed_instruments(db, user))
    return [
        link_payload(lk, infos[(lk.instrument, lk.record_id)])
        for lk in links
        if (lk.instrument, lk.record_id) in visible
    ]


async def require_visible_record(
    db: AsyncSession, user: User, read_scope: CardReadScope, instrument: str, record_id: uuid.UUID
) -> RecordInfo:
    """The record, or 404 when it does not exist **for this user** (D-42.3)."""
    if instrument not in LINK_INSTRUMENTS:
        raise LifecycleError(422, "invalid_instrument", f"Unknown record type: {instrument!r}")
    infos = await describe(db, {(instrument, record_id)})
    visible = await visible_keys(db, read_scope, infos, await allowed_instruments(db, user))
    if (instrument, record_id) not in visible:
        raise LifecycleError(404, "record_not_found", "Governance record not found")
    return infos[(instrument, record_id)]


async def _publish(
    db: AsyncSession,
    event: str,
    risk: Risk,
    instrument: str,
    record_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    extra: dict[str, Any] | None = None,
) -> None:
    """The audit record of a link change (D-42.4). No record title is carried,
    so the event names nothing a card reader could not already see."""
    await event_bus.publish(
        event,
        {
            "risk_id": str(risk.id),
            "reference": risk.reference,
            "instrument": instrument,
            "record_id": str(record_id),
            **(extra or {}),
        },
        db=db,
        user_id=actor_id,
    )


async def link(
    db: AsyncSession, risk: Risk, info: RecordInfo, actor_id: uuid.UUID
) -> RiskGovernanceLink:
    """Link ``risk`` to a record the caller may see; a repeated link is a no-op."""
    existing = (
        await db.execute(
            select(RiskGovernanceLink).where(
                RiskGovernanceLink.risk_id == risk.id,
                RiskGovernanceLink.instrument == info.instrument,
                RiskGovernanceLink.record_id == info.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    row = RiskGovernanceLink(
        risk_id=risk.id, instrument=info.instrument, record_id=info.id, created_by=actor_id
    )
    db.add(row)
    await db.flush()
    await _publish(db, "risk.governance_linked", risk, info.instrument, info.id, actor_id)
    return row


async def unlink(db: AsyncSession, risk: Risk, info: RecordInfo, actor_id: uuid.UUID) -> bool:
    """Remove one visible link; ``False`` when there was none."""
    row = (
        await db.execute(
            select(RiskGovernanceLink).where(
                RiskGovernanceLink.risk_id == risk.id,
                RiskGovernanceLink.instrument == info.instrument,
                RiskGovernanceLink.record_id == info.id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return False
    await db.delete(row)
    await _publish(db, "risk.governance_unlinked", risk, info.instrument, info.id, actor_id)
    return True


async def remove_record_links(
    db: AsyncSession, instrument: str, record_id: uuid.UUID, actor_id: uuid.UUID | None
) -> int:
    """A governance record was deleted: remove its links, each one recorded
    as ``risk.governance_unlinked`` with ``reason: record_deleted`` (D-42.4)."""
    rows = (
        await db.execute(
            select(RiskGovernanceLink, Risk)
            .join(Risk, Risk.id == RiskGovernanceLink.risk_id)
            .where(
                RiskGovernanceLink.instrument == instrument,
                RiskGovernanceLink.record_id == record_id,
            )
        )
    ).all()
    for row, risk in rows:
        await _publish(
            db,
            "risk.governance_unlinked",
            risk,
            instrument,
            record_id,
            actor_id,
            {"reason": "record_deleted"},
        )
        await db.delete(row)
    return len(rows)


async def risks_for_record(db: AsyncSession, instrument: str, record_id: uuid.UUID) -> list[Risk]:
    """The risks linked to one record (the caller has gated the record)."""
    rows = await db.execute(
        select(Risk)
        .join(RiskGovernanceLink, RiskGovernanceLink.risk_id == Risk.id)
        .where(
            RiskGovernanceLink.instrument == instrument,
            RiskGovernanceLink.record_id == record_id,
        )
        .order_by(Risk.reference)
    )
    return list(rows.scalars().all())


def risk_brief(risk: Risk, today: date) -> dict[str, Any]:
    return {
        "id": str(risk.id),
        "reference": risk.reference,
        "title": risk.title,
        "level": risk.residual_level or risk.initial_level,
        "status": risk.status,
        "escalated": dec.is_escalated(risk, today),
        "path": f"/grc/risks/{risk.id}",
    }


# ── Architecture-risk figures (D-42.6, I-53) ─────────────────────────────


async def architecture_risk_figures(
    db: AsyncSession, read_scope: CardReadScope, today: date
) -> dict[str, Any]:
    """Current-state architecture-risk counts over the links the scope admits.

    Each risk counts once in ``total`` / ``open`` / ``escalated`` /
    ``mitigated`` however many records it is linked to. ``by_record_type`` and
    ``linked_to_approved`` are overlapping breakdowns — a risk linked to an
    ADR and an exception appears under both — and are marked non-additive.
    Verified reduction is Not Available (D-42.8): no verification rule exists,
    and residual ratings, closure or mitigation are never presented as one."""
    links = await links_of(db)
    infos = await describe(db, {(lk.instrument, lk.record_id) for lk in links}, today)
    visible = await visible_keys(db, read_scope, infos)
    per_risk: dict[uuid.UUID, set[tuple[str, uuid.UUID]]] = {}
    for lk in links:
        key = (lk.instrument, lk.record_id)
        if key in visible:
            per_risk.setdefault(lk.risk_id, set()).add(key)
    reduction = {
        "status": "not_available",
        "reason": {"code": "no_verification_rule", "decisions": ["D-36", "D-42"]},
    }
    if not per_risk:
        return {
            "status": "not_available",
            "reason": {"code": "no_linked_risks"},
            "temporal": "current_state",
            "verified_reduction": reduction,
        }
    risks = list(
        (await db.execute(select(Risk).where(Risk.id.in_(list(per_risk))))).scalars().all()
    )
    picture = dec.classify_risks(risks, today)
    by_type = {kind: 0 for kind in LINK_INSTRUMENTS}
    approved = 0
    for r in risks:
        keys = per_risk[r.id]
        for kind in {k for k, _ in keys}:
            by_type[kind] += 1
        approved += any(infos[k].approved for k in keys)
    return {
        "status": "ok",
        "temporal": "current_state",
        "as_of": today.isoformat(),
        "basis": "explicit_governance_links",
        "total": len(risks),
        "open": picture.open,
        "escalated": len(picture.escalated),
        "mitigated": picture.mitigated,
        "by_record_type": {**by_type, "additive": False},
        "linked_to_approved": {"count": approved, "additive": False},
        "verified_reduction": reduction,
    }


async def architecture_risk_rows(
    db: AsyncSession, user: User, read_scope: CardReadScope, today: date
) -> list[dict[str, Any]]:
    """The drill-down: each architecture-related risk the aggregate counts,
    with the records the reader may also name; records whose module the
    reader lacks are counted (``records_withheld``), never named."""
    links = await links_of(db)
    infos = await describe(db, {(lk.instrument, lk.record_id) for lk in links}, today)
    counted = await visible_keys(db, read_scope, infos)
    named = await visible_keys(db, read_scope, infos, await allowed_instruments(db, user))
    per_risk: dict[uuid.UUID, list[RiskGovernanceLink]] = {}
    for lk in links:
        if (lk.instrument, lk.record_id) in counted:
            per_risk.setdefault(lk.risk_id, []).append(lk)
    if not per_risk:
        return []
    risks = (
        (await db.execute(select(Risk).where(Risk.id.in_(list(per_risk))).order_by(Risk.reference)))
        .scalars()
        .all()
    )
    rows = []
    for r in risks:
        own = per_risk[r.id]
        shown = [lk for lk in own if (lk.instrument, lk.record_id) in named]
        rows.append(
            {
                **risk_brief(r, today),
                "records": [link_payload(lk, infos[(lk.instrument, lk.record_id)]) for lk in shown],
                "records_withheld": len(own) - len(shown),
            }
        )
    return rows
