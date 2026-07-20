"""Reference Models — per-domain classification schemes (NEA National RMs).

[FORK FEATURE] — noraPlan.md WP100.3.

The Dec-2024 National EA Framework defines one National Reference Model per
domain (Business, Beneficiary Experience, Applications, Data, Technology,
Security) — classification guidance agencies consult to build their own
taxonomies. Tables:

* ``reference_models`` — one row per RM (a versioned, governable scheme with a
  domain discriminator). Lifecycle: draft → published → archived. Publishing
  supersedes: at most one *published* RM per domain at a time.
* ``reference_model_items`` — the classification entries, hierarchical via a
  self-referential ``parent_id``, uniquely coded per model.
* ``reference_model_mappings`` — explicit item ↔ inventory-card links.
* ``reference_model_versions`` — frozen snapshots captured at publish time.
* ``reference_model_relationships`` — typed cross-model item↔item links
  (RMPlan §10: supports / consumes / realizes / depends_on / aligns_with).

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
from sqlalchemy.dialects.postgresql import JSONB, UUID
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
# draft → in_review → published → archived. in_review is the governance gate
# (submit for review; a governance.approve_step holder publishes or rejects).
RM_STATUSES = ("draft", "in_review", "published", "archived")

# Explicit card↔item mapping metadata (WP100.3 Phase 2 / RMPlan §6-7, §11).
# The lightweight card-detail *code field* (brmCode/…) expresses a card's single
# primary classification; this table adds the M:N richer mappings — secondary /
# supporting / candidate / historical — with a rationale, a confidence and a
# review status. Coverage/browse counts merge both (dedup by card).
RM_MAPPING_TYPES = ("primary", "secondary", "supporting", "candidate", "historical")
RM_MAPPING_STATUSES = ("proposed", "confirmed", "rejected")


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
    # Poster narrative (RMPlan Phase 3 / §18) — editable panels (mission, vision,
    # objectives, stakeholders, principles, KPIs, value, …) rendered around the
    # capability map. Shape: {"panels": [NarrativePanel, ...]}. Generic on
    # purpose so admins add/reorder panels without a schema change per model type.
    narrative: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

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


class ReferenceModelVersion(UUIDMixin, TimestampMixin, Base):
    """A preserved snapshot of a reference model captured at publish time.

    Published models are never silently overwritten — each publish records the
    item tree as it was approved, so history is preserved and any two versions
    (or a version vs. the live model) can be compared. [FORK] RMPlan Phase 5.
    """

    __tablename__ = "reference_model_versions"

    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reference_models.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    change_summary: Mapped[str | None] = mapped_column(Text)
    # Frozen item tree: list of {code, parent_code, name, name_ar, description,
    # sort_order}. Codes are stable, so this is directly diff-able by code.
    snapshot: Mapped[list | None] = mapped_column(JSONB, default=list)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_reference_model_versions_model", "model_id"),)


class ReferenceModelMapping(UUIDMixin, TimestampMixin, Base):
    """One explicit mapping between a reference-model item and an inventory card."""

    __tablename__ = "reference_model_mappings"

    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reference_models.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reference_model_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    mapping_type: Mapped[str] = mapped_column(String(16), default="primary")
    mapping_status: Mapped[str] = mapped_column(String(16), default="confirmed")
    rationale: Mapped[str | None] = mapped_column(Text)
    # 0-100 human/AI confidence (Phase 6 assisted mapping fills this in).
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("item_id", "card_id", name="uq_reference_model_mappings_item_card"),
        Index("ix_reference_model_mappings_model", "model_id"),
        Index("ix_reference_model_mappings_item", "item_id"),
        Index("ix_reference_model_mappings_card", "card_id"),
    )


# Cross-model item↔item relationship types (RMPlan §10). These express
# non-parent links between components, typically *across* models — e.g. an ARM
# application component that *realizes* a BRM capability, or a TRM technology
# service that *supports* an ARM component.
REFERENCE_MODEL_RELATIONSHIP_TYPES = (
    "supports",
    "consumes",
    "realizes",
    "depends_on",
    "aligns_with",
)


class ReferenceModelRelationship(UUIDMixin, TimestampMixin, Base):
    """A typed link between two reference-model items (RMPlan §10).

    Unlike the ``parent_id`` hierarchy (which is intra-model composition), this
    captures cross-cutting relationships — usually between items of *different*
    models — so agencies can trace, e.g., which BRM capability an ARM
    application component realizes. Item deletion cascades the link away.
    """

    __tablename__ = "reference_model_relationships"

    source_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reference_model_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reference_model_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(String(32), default="supports")
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "source_item_id",
            "target_item_id",
            "relationship_type",
            name="uq_reference_model_relationships_triple",
        ),
        Index("ix_reference_model_relationships_source", "source_item_id"),
        Index("ix_reference_model_relationships_target", "target_item_id"),
    )
