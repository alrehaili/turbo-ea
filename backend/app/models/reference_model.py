"""Reference Models — per-domain classification schemes (NEA National RMs).

[FORK FEATURE] — noraPlan.md WP100.3.

The Dec-2024 National EA Framework defines one National Reference Model per
domain (Business, Beneficiary Experience, Applications, Data, Technology,
Security) — classification guidance agencies consult to build their own
taxonomies. Two tables:

* ``reference_models`` — one row per RM (a versioned, governable scheme with a
  domain discriminator). Lifecycle: draft → published → archived. Publishing
  supersedes: at most one *published* RM per domain at a time.
* ``reference_model_items`` — the classification entries, hierarchical via a
  self-referential ``parent_id``, uniquely coded per model.

RMs are reference data (like ``tech_standards``), never landscape cards. The
published RM per domain backs the card-detail code-field pickers
(brmCode/armCode/drmCode/trmCode/bxrmCode/srmCode) and the coverage numbers on
the Reference Models report.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

# The six NORA 2.0 domains (camelCase, same values as REQUIREMENT_DOMAINS).
RM_DOMAINS = (
    "business",
    "beneficiaryExperience",
    "applications",
    "data",
    "technology",
    "security",
)
RM_SOURCES = ("national", "sectoral", "agency")
RM_STATUSES = ("draft", "published", "archived")


class ReferenceModel(UUIDMixin, TimestampMixin, Base):
    """One reference model — a versioned classification scheme for a domain."""

    __tablename__ = "reference_models"

    domain: Mapped[str] = mapped_column(String(32), nullable=False)
    # Seed idempotency handle for built-in starters (e.g. "nea_business_preview").
    key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    source: Mapped[str] = mapped_column(String(16), default="agency")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    built_in: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_reference_models_domain", "domain"),
        Index("ix_reference_models_status", "status"),
    )


class ReferenceModelItem(UUIDMixin, TimestampMixin, Base):
    """One classification entry inside a reference model (hierarchical)."""

    __tablename__ = "reference_model_items"

    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reference_models.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reference_model_items.id", ondelete="CASCADE"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("model_id", "code", name="uq_reference_model_items_model_code"),
        Index("ix_reference_model_items_model", "model_id"),
        Index("ix_reference_model_items_parent", "parent_id"),
    )
