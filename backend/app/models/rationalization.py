"""Application Rationalization Assessment models.

A rationalization assessment packages the portfolio-decision workflow that turns
inventory into action: assess applications with the **TIME** framework
(Tolerate / Invest / Migrate / Eliminate), nominate a successor, estimate the
annual cost and planned savings, link the delivering initiative, and track
progress.

A :class:`RationalizationAssessment` owns many :class:`AssessmentDecision` rows —
one per application under review. The successor and the delivering initiative are
captured as nullable card FKs on the decision itself (not as landscape
relations), so the assessment is self-contained; promoting a successor choice into
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
ASSESSMENT_STATUSES = ("draft", "active", "completed", "archived")


class RationalizationAssessment(UUIDMixin, TimestampMixin, Base):
    """A repeatable application-rationalization assessment over a portfolio."""

    __tablename__ = "rationalization_assessments"

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="draft")
    target_savings: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    decisions = relationship(
        "AssessmentDecision",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    __table_args__ = (Index("ix_rationalization_assessments_status", "status"),)


class AssessmentDecision(UUIDMixin, TimestampMixin, Base):
    """One application's TIME decision within an assessment."""

    __tablename__ = "assessment_decisions"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rationalization_assessments.id", ondelete="CASCADE"),
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
    # Strategic reasoning for the TIME decision. Distinct from ``notes`` (how
    # to execute) and ``risk_note`` (what could go wrong) — this captures the
    # "why" that a board is expected to have on record: e.g. "Consolidate
    # analytics onto the Power BI standard" for a Tableau → Power BI migrate.
    rationale: Mapped[str | None] = mapped_column(Text)
    risk_note: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    progress: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_assessment_decisions_assessment_id", "assessment_id"),
        Index("ix_assessment_decisions_card_id", "card_id"),
    )
