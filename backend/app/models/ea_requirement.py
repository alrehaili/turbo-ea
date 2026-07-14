"""EA Requirements register (updated NORA methodology phase 7).

[FORK FEATURE] — noraPlan.md WP6.1.

The continuous element of the Dec-2024 National EA Framework: architecture
requirements are registered *before* a development cycle, approved, tracked
through the cycle, and change-impact-assessed. Distinct from Improvement
Opportunities (which come *out of* current-state analysis) — requirements
precede the cycle.

Change-impact assessment reuses the existing dependency machinery on the
linked cards; the register itself stays a thin governable record.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

# The six NORA 2.0 domains (camelCase, matching the v2 program tracker).
REQUIREMENT_DOMAINS = (
    "business",
    "beneficiaryExperience",
    "applications",
    "data",
    "technology",
    "security",
)
REQUIREMENT_STATUSES = ("proposed", "approved", "inCycle", "fulfilled", "rejected", "changed")


class EaRequirement(UUIDMixin, TimestampMixin, Base):
    """One registered EA requirement (methodology phase 7)."""

    __tablename__ = "ea_requirements"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Where the requirement came from (free text — a stakeholder, a mandate,
    # a regulation, an audit finding, …).
    source: Mapped[str | None] = mapped_column(String(200))
    domain: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="proposed")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The development-cycle initiative that fulfils this requirement.
    initiative_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("ix_ea_requirements_status", "status"),
        Index("ix_ea_requirements_domain", "domain"),
    )


class EaRequirementCard(UUIDMixin, TimestampMixin, Base):
    """M:N link between a requirement and the cards it concerns."""

    __tablename__ = "ea_requirement_cards"

    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ea_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        Index("ix_ea_requirement_cards_req", "requirement_id"),
        Index("ix_ea_requirement_cards_card", "card_id"),
    )
