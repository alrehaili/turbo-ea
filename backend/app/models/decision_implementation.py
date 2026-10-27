"""Implementation of an approved architecture decision (D-13, D-32, D-41; Batch 3.4).

One row per decision — a signed ADR or an approved ARB review — holding its
implementation deadline and whether its implementation was submitted for, and
received, independent verification. The actions themselves are todos linked by
``source_kind`` / ``source_id`` (D-13).

``original_due_date`` is the deadline as approved and **never changes**;
``due_date`` is the one in force, moved only by an authorized revision that
appends a ``due_date_changed`` row to ``governance_transitions`` (D-41.3). On
an unsigned ADR ``due_date`` is the proposed deadline the signatories approve
when they sign. Nothing is created for decisions taken before this table
existed: they have no deadline until someone sets one (``set_after_decision``).

``decision_id`` names an ADR or an ARB review by ``decision_kind``, so it carries
no foreign key (like ``governance_transitions.record_id``); the routes that
delete a decision delete its row.

[FORK]
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

DECISION_ADR = "adr"
DECISION_ARB = "arb"
DECISION_KINDS = (DECISION_ADR, DECISION_ARB)

#: The deadline was approved together with the decision (ADR signing, ARB approval).
BASIS_WITH_DECISION = "with_decision"
#: The decision was approved without one; a governance owner set it later, with a reason.
BASIS_AFTER_DECISION = "set_after_decision"

STATUS_OPEN = "open"
STATUS_SUBMITTED = "submitted"
STATUS_VERIFIED = "verified"


class DecisionImplementation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "decision_implementations"

    decision_kind: Mapped[str] = mapped_column(String(8), nullable=False)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    original_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date_basis: Mapped[str | None] = mapped_column(String(24), nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_OPEN)
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # What the verifier examined, why it shows the decision implemented, their
    # confirmation, and the action evidence as it stood (no user ids inside).
    attestation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint("decision_kind IN ('adr', 'arb')", name="ck_decision_implementations_kind"),
        CheckConstraint(
            "status IN ('open', 'submitted', 'verified')",
            name="ck_decision_implementations_status",
        ),
        UniqueConstraint(
            "decision_kind", "decision_id", name="uq_decision_implementations_decision"
        ),
    )
