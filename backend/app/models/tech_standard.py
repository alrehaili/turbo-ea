"""Technology Standards catalogue + exception register (Wave 2 #5).

A **clean, separate** catalogue distinct from the fork's principle-linked
``standards`` table. Where ``standards`` captures *which principle a spec
implements*, this catalogue captures the *operational adoption status* of a
technology/cloud/integration/data/security standard on the classic radar scale:

    Preferred → Allowed → Tolerated → Sunset → Prohibited

Each standard can nominate a ``replacement`` (another standard to migrate to),
and carries an **exception register**: time-boxed, approver-gated waivers that
let a specific application/initiative deviate from the standard with documented
compensating controls and an expiry date.

[FORK FEATURE]
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

# Radar adoption rings + the categories a standard can belong to.
STANDARD_STATUSES = ("preferred", "allowed", "tolerated", "sunset", "prohibited")
STANDARD_CATEGORIES = ("technology", "cloud", "integration", "data", "security", "other")
# NORA TRM mandate levels (noraPlan.md WP1.3).
STANDARD_MANDATES = ("mandatory", "recommended", "optional")
# Exception lifecycle (D-34, D-40). ``expired`` is never stored: it is derived
# at read time from an approved (or awaiting-verification) waiver past expiry.
EXCEPTION_STATUSES = (
    "requested",
    "approved",
    "rejected",
    "remediation_submitted",
    "remediated",
    "withdrawn",
    "expired",
)
#: Statuses whose waiver still covers the card until ``expiry_date``. A
#: submitted remediation is not yet verified, so it leaves the waiver as it was
#: (I-23); ``remediated`` and ``withdrawn`` no longer waive anything.
WAIVER_ACTIVE_STATUSES = ("approved", "remediation_submitted")


class TechStandard(UUIDMixin, TimestampMixin, Base):
    """A technology standard with a radar adoption status."""

    __tablename__ = "tech_standards"

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(24), default="technology")
    status: Mapped[str] = mapped_column(String(16), default="allowed")
    description: Mapped[str | None] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text)
    # Recommended replacement (another standard) — used for sunset/prohibited.
    replacement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tech_standards.id", ondelete="SET NULL"), nullable=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # NORA TRM metadata (noraPlan.md WP1.3): issuing body (DGA, NCA, W3C, …),
    # mandate level, next review date, spec link, TRM code, and an optional
    # link to a TechCategory card (the TRM Service Area / Category tree).
    standard_body: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mandate: Mapped[str] = mapped_column(
        String(16), nullable=False, default="recommended", server_default="recommended"
    )
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    spec_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    trm_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tech_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )

    exceptions = relationship(
        "StandardException",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    __table_args__ = (
        Index("ix_tech_standards_category", "category"),
        Index("ix_tech_standards_status", "status"),
        Index("ix_tech_standards_tech_category_id", "tech_category_id"),
    )


class StandardException(UUIDMixin, TimestampMixin, Base):
    """A time-boxed, approver-gated waiver from a technology standard."""

    __tablename__ = "tech_standard_exceptions"

    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tech_standards.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The application/component getting the waiver, and the initiative driving it.
    card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    initiative_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    justification: Mapped[str | None] = mapped_column(Text)
    compensating_controls: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="requested")
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # When the latest approve / reject was recorded (migration 1166). NULL on
    # every decision taken before then: no date is invented (D-34).
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Remediation and withdrawal (D-40, migration 1167): the current values; each
    # step is also a ``governance_transitions`` row. All NULL on earlier rows.
    remediation_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation_submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    remediation_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    remediation_verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    remediation_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    withdrawn_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_tech_standard_exceptions_standard_id", "standard_id"),
        Index("ix_tech_standard_exceptions_card_id", "card_id"),
        Index("ix_tech_standard_exceptions_status", "status"),
    )
