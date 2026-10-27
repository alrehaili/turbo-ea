"""EA governance applicability assessments of initiatives (D-37; Batch 3.6).

Append-only: each row is one authorized decision that an Initiative does, or
does not, require EA governance review, with the criteria applied and why. The
latest row is the initiative's current status; an initiative with no row is
**Undetermined** — never exempt, never compliant. No row is ever edited, and
none is created for any earlier date, so applicability exists only from the
day it was recorded.

[FORK]
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin

REQUIRED = "required"
NOT_REQUIRED = "not_required"
DECISIONS = (REQUIRED, NOT_REQUIRED)


class EaReviewApplicability(UUIDMixin, Base):
    __tablename__ = "ea_review_applicability_assessments"

    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    criteria_reference: Mapped[str] = mapped_column(String(300), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "decision IN ('required', 'not_required')",
            name="ck_ea_review_applicability_decision",
        ),
        Index("ix_ea_review_applicability_card", "card_id", "decided_at"),
    )
