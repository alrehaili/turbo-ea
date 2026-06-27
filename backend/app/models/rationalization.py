"""Application Rationalization Campaign models.

A rationalization campaign packages the portfolio-decision workflow that turns
inventory into action: assess applications with the **TIME** framework
(Tolerate / Invest / Migrate / Eliminate), nominate a successor, estimate the
annual cost and planned savings, link the delivering initiative, and track
progress.

A :class:`RationalizationCampaign` owns many :class:`CampaignDecision` rows —
one per application under review. The successor and the delivering initiative are
captured as nullable card FKs on the decision itself (not as landscape
relations), so the campaign is self-contained; promoting a successor choice into
a first-class landscape relation is a future enhancement (see plan.md item 1.3).

[FORK FEATURE]
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

# TIME-framework decision values + workflow statuses (validated in the schema).
TIME_DECISIONS = ("undecided", "tolerate", "invest", "migrate", "eliminate")
CAMPAIGN_STATUSES = ("draft", "active", "completed", "archived")


class RationalizationCampaign(UUIDMixin, TimestampMixin, Base):
    """A repeatable application-rationalization campaign over a portfolio."""

    __tablename__ = "rationalization_campaigns"

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="draft")
    target_savings: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    decisions = relationship(
        "CampaignDecision",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    __table_args__ = (Index("ix_rationalization_campaigns_status", "status"),)


class CampaignDecision(UUIDMixin, TimestampMixin, Base):
    """One application's TIME decision within a campaign."""

    __tablename__ = "campaign_decisions"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rationalization_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )
    time_decision: Mapped[str] = mapped_column(String(16), default="undecided")
    successor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    initiative_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    annual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    planned_savings: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_note: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    progress: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_campaign_decisions_campaign_id", "campaign_id"),
        Index("ix_campaign_decisions_card_id", "card_id"),
    )
