"""KPI measurement history and target ratification (decisions D-19, D-17a).

One history for every measured value (D-19): the four landscape-wide dashboard
series that ``kpi_snapshots`` used to hold, the system-calculated executive
indicators, and the values recorded for KPI cards. Two kinds of row, never
mixed:

* ``daily`` — an automatic observation (status ``observed``). Never verified,
  never corrected; it is what a day's capture saw.
* ``period`` — the value for a fiscal year or quarter (status ``submitted`` →
  ``verified``). A verified measurement of a period that has ended is
  *frozen*. Every change is a new row that supersedes the current one
  (``supersedes_id`` + ``correction_reason``); the replaced row is kept as
  ``superseded``, so the history is append-only.

A row measures either a registered system metric (``metric_key``) or a KPI
card (``kpi_card_id``); a KPI card's definition, target and owner stay on the
card.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

KIND_DAILY = "daily"
KIND_PERIOD = "period"

STATUS_OBSERVED = "observed"
STATUS_SUBMITTED = "submitted"
STATUS_VERIFIED = "verified"
STATUS_SUPERSEDED = "superseded"


class KpiMeasurement(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "kpi_measurements"

    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    metric_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kpi_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=True
    )
    #: ``day`` / ``quarter`` / ``fiscal_year``.
    period_type: Mapped[str] = mapped_column(String(16), nullable=False)
    #: ``2026-10-25`` / ``FY2026-Q3`` / ``FY2026``.
    period_key: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    #: The period's last day (inclusive).
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    #: For a system period value: the day of the observation it was taken from.
    observed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    numerator: Mapped[float | None] = mapped_column(Float, nullable=True)
    denominator: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    calculation_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #: ``system`` / ``manual``.
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    #: A link or note supporting a recorded value.
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    #: ``None`` for a value the system recorded.
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kpi_measurements.id", ondelete="SET NULL"), nullable=True
    )
    correction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "metric_key IS NOT NULL OR kpi_card_id IS NOT NULL", name="ck_kpi_measurements_subject"
        ),
        CheckConstraint("kind IN ('daily', 'period')", name="ck_kpi_measurements_kind"),
        # One daily observation per metric per day.
        Index(
            "uq_kpi_measurements_daily",
            "metric_key",
            "period_key",
            unique=True,
            postgresql_where=text("kind = 'daily'"),
        ),
        # One current period value per KPI card per period …
        Index(
            "uq_kpi_measurements_card_period",
            "kpi_card_id",
            "period_key",
            unique=True,
            postgresql_where=text(
                "kind = 'period' AND status <> 'superseded' AND kpi_card_id IS NOT NULL"
            ),
        ),
        # … and per system metric per period.
        Index(
            "uq_kpi_measurements_metric_period",
            "metric_key",
            "period_key",
            unique=True,
            postgresql_where=text(
                "kind = 'period' AND status <> 'superseded' AND kpi_card_id IS NULL"
            ),
        ),
        Index("ix_kpi_measurements_card", "kpi_card_id"),
    )


class KpiTargetRatification(Base, UUIDMixin, TimestampMixin):
    """A KPI target as ratified by an authorized target approver (D-17a).

    The target is copied as it stood. It stays ratified only while the card
    still carries exactly these values: a later change to the target, its
    date, the baseline, the unit or the direction makes it unratified again,
    and this row is kept as the record of what was ratified.
    """

    __tablename__ = "kpi_target_ratifications"

    kpi_card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    target_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ratified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    ratified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
