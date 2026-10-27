"""Reported actuals of financial benefits and Finance's allocations (D-14, D-29).

``benefit_actuals``: one value realised in one fiscal year, reported by the
benefit's side with evidence and then **confirmed** or **rejected** by an
independent Finance user (D-29). A confirmed actual may be **reversed** with a
reason; at most one live (reported or confirmed) actual exists per benefit and
fiscal year. Rows are never deleted.

``benefit_allocations``: the attributable amounts Finance assigns to the
benefit's ``direct`` / ``contributing`` initiatives when confirming an actual,
each with a rationale. Together they never exceed the actual, so a benefit is
never claimed twice (D-14).

[FORK]
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

REPORTED = "reported"
CONFIRMED = "confirmed"
REJECTED = "rejected"
REVERSED = "reversed"
ACTUAL_STATUSES = (REPORTED, CONFIRMED, REJECTED, REVERSED)
LIVE_STATUSES = (REPORTED, CONFIRMED)


class BenefitActual(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "benefit_actuals"

    benefit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("benefits.id", ondelete="CASCADE"), nullable=False
    )
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default=REPORTED)
    reported_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    report_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Evidence references (I-69): documents / files by id, or recorded text.
    evidence_refs: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finance_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reversed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reverse_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('reported', 'confirmed', 'rejected', 'reversed')",
            name="ck_benefit_actuals_status",
        ),
        CheckConstraint("amount >= 0", name="ck_benefit_actuals_amount"),
        Index(
            "uq_benefit_actuals_live",
            "benefit_id",
            "fiscal_year",
            unique=True,
            postgresql_where=sa_text("status IN ('reported', 'confirmed')"),
        ),
    )


class BenefitAllocation(UUIDMixin, Base):
    __tablename__ = "benefit_allocations"

    actual_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("benefit_actuals.id", ondelete="CASCADE"), nullable=False
    )
    # The initiative. SET NULL keeps Finance's record if the card is deleted.
    card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    # The link's classification when Finance allocated (direct / contributing).
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "classification IN ('direct', 'contributing')",
            name="ck_benefit_allocations_classification",
        ),
        CheckConstraint("amount > 0", name="ck_benefit_allocations_amount"),
        Index("ix_benefit_allocations_actual", "actual_id"),
    )
