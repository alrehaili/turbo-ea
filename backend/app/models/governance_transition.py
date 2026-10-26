"""Governance decision-transition history (D-35, D-34; Batch 3.2).

One append-only row per status change of a governance instrument — an
Architecture Decision Record, an ARB review or a technology-standard
exception — recorded **from the day this table ships**. Nothing is backfilled:
a record decided before then has no rows and is reported "lifecycle not
recorded", never given a manufactured history (D-34).

``record_id`` is polymorphic (``instrument`` names the table), so it carries no
foreign key: a row outlives the record it describes, which is what makes the
history auditable after a hard delete. ``from_status`` is NULL on creation.

[FORK]
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

INSTRUMENT_ADR = "adr"
INSTRUMENT_ARB = "arb"
INSTRUMENT_EXCEPTION = "exception"
INSTRUMENTS = (INSTRUMENT_ADR, INSTRUMENT_ARB, INSTRUMENT_EXCEPTION)

#: Who a waiting interval is attributable to (D-39). Only ``requester`` and
#: ``external`` intervals, with a reason, leave governance-controlled time.
#: A lifecycle event that is not a status change (I-35).
EVENT_EXPIRY_CHANGED = "expiry_changed"

ATTRIBUTION_GOVERNANCE = "governance"
ATTRIBUTION_REQUESTER = "requester"
ATTRIBUTION_EXTERNAL = "external"
DELAY_ATTRIBUTIONS = (ATTRIBUTION_GOVERNANCE, ATTRIBUTION_REQUESTER, ATTRIBUTION_EXTERNAL)


class GovernanceTransition(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "governance_transitions"

    instrument: Mapped[str] = mapped_column(String(16), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Why the move happened, as recorded by the actor (a withdrawal reason,
    # remediation evidence, a return note, a delay reason). Migration 1167.
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # For a move into a waiting state (ADR draft, ARB deferred): who the wait is
    # attributable to (D-39). NULL means nobody said, never "governance".
    delay_attribution: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # On an exception's move into ``approved`` from a request or a rejection:
    # the expiry date as approved. GOV-04 measures against it, never against a
    # later edit (migration 1168, I-31). On an ``expiry_changed`` event: the
    # new expiry (I-35). NULL on every other row.
    approved_expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # NULL for a status transition; ``expiry_changed`` for an authorized change
    # of an approved exception's expiry, which keeps the status (migration
    # 1170, I-35) and records the expiry it replaced.
    event_kind: Mapped[str | None] = mapped_column(String(24), nullable=True)
    previous_expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "instrument IN ('adr', 'arb', 'exception')",
            name="ck_governance_transitions_instrument",
        ),
        CheckConstraint(
            "delay_attribution IS NULL OR delay_attribution IN "
            "('governance', 'requester', 'external')",
            name="ck_governance_transitions_delay_attribution",
        ),
        CheckConstraint(
            "event_kind IS NULL OR event_kind IN ('expiry_changed')",
            name="ck_governance_transitions_event_kind",
        ),
        Index("ix_governance_transitions_record", "instrument", "record_id"),
        Index("ix_governance_transitions_occurred_at", "occurred_at"),
    )
