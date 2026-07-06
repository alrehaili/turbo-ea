"""Improvement Opportunity registry (NORA Stage 6.6).

[FORK FEATURE] — noraPlan.md WP3.3.

The approved output of current-architecture analysis: one governable record
per improvement idea, classified by architecture domain, traceable to the
cards it concerns and to the transition initiative that realises it.
Human analysis and TurboLens findings converge here before feeding the
transition plan.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

OPPORTUNITY_DOMAINS = ("BA", "AA", "DA", "TA")
OPPORTUNITY_SOURCES = (
    "manual",
    "turbolens_duplicate",
    "turbolens_modernization",
    "swot",
    "maturity",
    "ai",
)
OPPORTUNITY_PRIORITIES = ("low", "medium", "high")
OPPORTUNITY_STATUSES = ("proposed", "approved", "inTransition", "realized", "rejected")


class ImprovementOpportunity(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "improvement_opportunities"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(4), default="AA")
    source: Mapped[str] = mapped_column(String(32), default="manual")
    priority: Mapped[str] = mapped_column(String(8), default="medium")
    status: Mapped[str] = mapped_column(String(16), default="proposed")
    # The transition initiative that realises this opportunity.
    initiative_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("ix_improvement_opportunities_status", "status"),
        Index("ix_improvement_opportunities_domain", "domain"),
    )


class ImprovementOpportunityCard(UUIDMixin, TimestampMixin, Base):
    """M:N link between an opportunity and the cards it concerns."""

    __tablename__ = "improvement_opportunity_cards"

    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("improvement_opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        Index("ix_improvement_opportunity_cards_opp", "opportunity_id"),
        Index("ix_improvement_opportunity_cards_card", "card_id"),
    )
