"""Qualitative outcome assessments and the benefit history (D-43, D-12).

``benefit_assessments``: append-only business-owner assessments of a
qualitative outcome benefit, each with evidence. The latest row is the current
assessment. It is reported as **assessed**, never as verified KPI achievement
(D-43).

``benefit_history``: one append-only row per change of a benefit, its links,
actuals or assessments — the actor, the time, the action, the status move, the
note and the changed values (labels and amounts, never ids).

[FORK]
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin

ACHIEVED = "achieved"
PARTIALLY_ACHIEVED = "partially_achieved"
NOT_ACHIEVED = "not_achieved"
OUTCOMES = (ACHIEVED, PARTIALLY_ACHIEVED, NOT_ACHIEVED)


class BenefitAssessment(UUIDMixin, Base):
    __tablename__ = "benefit_assessments"

    benefit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("benefits.id", ondelete="CASCADE"), nullable=False
    )
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    assessed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('achieved', 'partially_achieved', 'not_achieved')",
            name="ck_benefit_assessments_outcome",
        ),
        Index("ix_benefit_assessments_benefit", "benefit_id", "assessed_at"),
    )


class BenefitHistory(UUIDMixin, Base):
    __tablename__ = "benefit_history"

    benefit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("benefits.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_benefit_history_benefit", "benefit_id", "occurred_at"),)
