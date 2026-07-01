"""Architecture Review Board (ARB) review records (Wave 2 #7).

An ARB review captures a governance decision on a proposed solution (anchored to
a subject card). The *context* — change impact, linked risks, ADRs, and standard
exceptions — is aggregated live at read time from the existing modules; only the
decision/sign-off itself is persisted here.

[FORK FEATURE]
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

ARB_STATUSES = ("scheduled", "approved", "rejected", "deferred")


class ArbReview(UUIDMixin, TimestampMixin, Base):
    """A single Architecture Review Board decision on a proposed solution."""

    __tablename__ = "arb_reviews"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    subject_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    summary: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="scheduled")
    decision_notes: Mapped[str | None] = mapped_column(Text)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("ix_arb_reviews_status", "status"),
        Index("ix_arb_reviews_subject_card_id", "subject_card_id"),
    )
