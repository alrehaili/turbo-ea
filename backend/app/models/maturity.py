"""EA maturity self-assessment (Qiyas-style).

[FORK FEATURE] — noraPlan.md WP5.2.

NORA Stage 1.3 (baseline maturity) and Stage 10 (periodic re-assessment) ask
the agency to score itself across a set of EA maturity dimensions on a fixed
1–5 scale and track the trend over time. Three tables:

* ``maturity_dimensions`` — the admin-definable catalogue of dimensions being
  scored (seeded with a NORA/Qiyas-style default set; agencies can add their
  own or deactivate built-ins).
* ``maturity_assessments`` — one row per assessment run (a point in time). The
  assessments themselves are the time series that powers the trend chart, so
  there is no separate snapshot table (delta from the ``kpi_snapshots`` pattern
  the plan referenced — an assessment already *is* a dated snapshot).
* ``maturity_dimension_scores`` — the per-dimension level within one assessment.
  Dimension key + name are **snapshotted** onto each score so historical
  assessments stay readable even after a dimension is renamed or deactivated.

The level scale is a fixed CMMI/Qiyas 1–5 (0 = not yet assessed); level *labels*
are i18n keys on the frontend. Per-dimension improvement gaps can be promoted
into the Improvement Opportunity registry (WP3.3), mirroring the
compliance-finding → risk promotion pattern.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

# Fixed CMMI/Qiyas maturity scale. 0 means "not yet assessed".
MATURITY_MAX_LEVEL = 5
MATURITY_ASSESSMENT_STATUSES = ("draft", "submitted", "approved")


class MaturityDimension(UUIDMixin, TimestampMixin, Base):
    """One EA maturity dimension in the admin-definable catalogue."""

    __tablename__ = "maturity_dimensions"

    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    built_in: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (Index("ix_maturity_dimensions_active", "is_active"),)


class MaturityAssessment(UUIDMixin, TimestampMixin, Base):
    """One maturity assessment run (a dated snapshot of the whole scorecard)."""

    __tablename__ = "maturity_assessments"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    assessment_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    notes: Mapped[str | None] = mapped_column(Text)
    # Weighted 0–100 overall, computed when the assessment is submitted.
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_maturity_assessments_date", "assessment_date"),)


class MaturityDimensionScore(UUIDMixin, TimestampMixin, Base):
    """The score for one dimension inside one assessment."""

    __tablename__ = "maturity_dimension_scores"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maturity_assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    dimension_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maturity_dimensions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Snapshots so history survives dimension rename/deactivate/delete.
    dimension_key: Mapped[str] = mapped_column(String(100), nullable=False)
    dimension_name: Mapped[str] = mapped_column(String(200), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=0)
    target_level: Mapped[int] = mapped_column(Integer, default=0)
    # Advisory repository-derived suggestion (0 = no automated evidence) and
    # the indicator snapshot it was banded from. The assessor always confirms
    # the actual ``level`` — the suggestion is never binding.
    suggested_level: Mapped[int] = mapped_column(Integer, default=0)
    evidence: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("assessment_id", "dimension_id", name="uq_maturity_score_assess_dim"),
        Index("ix_maturity_dimension_scores_assessment", "assessment_id"),
    )
