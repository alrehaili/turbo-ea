"""Multi-step approval chain for card governance (NORA stage gates).

[FORK FEATURE] — noraPlan.md WP2.2.

When governance mode is enabled (Admin → Settings → Governance), a card's
approval no longer flips straight to APPROVED: submitting it creates one
``ApprovalStep`` row per configured chain role (e.g. chief_architect →
ea_governance_committee). Each step must be approved, in order, by a user
holding that role (plus the ``governance.approve_step`` permission); the final
step sets the card's ``approval_status`` to APPROVED. Rejection at any step
sets REJECTED. Steps are recreated on every (re)submission — the durable audit
trail lives in the events table, which records every transition.

Approval steps are instance-local governance state (like ``last_confirmed_at``)
and are intentionally NOT carried in the workspace-transfer bundle.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

STEP_STATUSES = ("pending", "approved", "rejected")


class ApprovalStep(UUIDMixin, TimestampMixin, Base):
    """One role-gated step in a card's review chain."""

    __tablename__ = "approval_steps"

    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    required_role_key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    # Who submitted the card for review (same value on every step of a round;
    # used for the segregation-of-duties check).
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(Text)
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_approval_steps_card_id", "card_id"),)
