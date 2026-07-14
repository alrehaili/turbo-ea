"""NORA EA Program tracker — stage deliverables with evidence links.

[FORK FEATURE] — noraPlan.md WP3.1.

The NORA methodology is ten sequential stages (plus continuous governance),
each with named deliverables that require EA Governance Committee approval.
This table tracks one row per deliverable per install; the stage catalogue
itself is static (stage numbers 1–10, 0 = continuous governance) and stage
titles are i18n keys on the frontend.

Design deltas from the original plan:

* No separate ``ea_program_stages`` table — stages are a fixed, well-known
  list; tailoring happens by descoping deliverables (status ``descoped``) or
  adding custom ones, which covers NORA's explicit tailoring allowance with
  half the schema.
* Deliverable titles are **data** (admin-editable, like card names), so they
  are stored plain and not translated; only UI chrome and stage names carry
  i18n keys.

``evidence`` is a JSONB list of ``{kind, ref, label}`` links — a card query,
a report path, a diagram, a document URL, a SoAW/ADR — kept deliberately
loose so any artifact the agency produces can serve as proof.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

DELIVERABLE_STATUSES = ("notStarted", "inProgress", "inReview", "approved", "descoped")
# Stage 0 is the cross-cutting "Continuous Governance" track.
NORA_STAGE_NUMBERS = tuple(range(0, 11))


class EaProgramDeliverable(UUIDMixin, TimestampMixin, Base):
    """One NORA stage deliverable being tracked by the agency."""

    __tablename__ = "ea_program_deliverables"

    stage_no: Mapped[int] = mapped_column(Integer, nullable=False)
    # Stable identity for seeded deliverables (idempotent re-seed); custom
    # deliverables get a generated key.
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="notStarted")
    built_in: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    evidence: Mapped[list] = mapped_column(JSONB, default=list)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_ea_program_deliverables_stage_no", "stage_no"),)
