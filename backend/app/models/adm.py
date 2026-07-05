"""ADM Governance Workspace models.

Three tables that overlay TOGAF ADM phase governance onto an existing SoAW
(or, less commonly, an Initiative card). Zero data duplication — evidence
lives on the AdmPhaseArtefact rows as ``(kind, ref_id)`` pointers to existing
Turbo EA entities.

[FORK FEATURE]
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

ADM_WORKSPACE_STATUSES: tuple[str, ...] = (
    "draft",
    "active",
    "on_hold",
    "completed",
    "archived",
)

ADM_PHASE_STATUSES: tuple[str, ...] = (
    "not_started",
    "in_progress",
    "blocked",
    "ready_for_gate",
    "approved",
    "skipped",
)

# Phases in canonical TOGAF ADM order. ``requirements_management`` is
# flagged ``is_continuous`` on the row and rendered separately in the UI.
ADM_PHASE_KEYS: tuple[str, ...] = (
    "preliminary",
    "phase_a",
    "phase_b",
    "phase_c",
    "phase_d",
    "phase_e",
    "phase_f",
    "phase_g",
    "phase_h",
    "requirements_management",
)

# Artefact kinds allowlist. ``ref_id`` is a soft FK dispatched by kind at the
# API layer; ``url`` uses ``ref_url`` instead of ``ref_id``.
ADM_ARTEFACT_KINDS: tuple[str, ...] = (
    "soaw",
    "adr",
    "arb_review",
    "diagram",
    "roadmap",
    "risk",
    "compliance_finding",
    "tech_standard",
    "standard_exception",
    "rationalization_assessment",
    "card",
    "url",
    "document",
    "file_attachment",
    "requirement",
)


class AdmWorkspace(UUIDMixin, TimestampMixin, Base):
    """One governed architecture engagement.

    Anchored to a SoAW (primary) and/or an Initiative card. At least one
    anchor is required, enforced by a table-level ``CHECK`` constraint —
    the model does not attempt to validate this in Python beyond a schema
    check on the create payload.
    """

    __tablename__ = "adm_workspaces"

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    soaw_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("statement_of_architecture_works.id", ondelete="SET NULL"),
        nullable=True,
    )
    initiative_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(24), default="active")
    description: Mapped[str | None] = mapped_column(Text)
    target_completion: Mapped[date | None] = mapped_column(Date)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "soaw_id IS NOT NULL OR initiative_id IS NOT NULL",
            name="ck_adm_workspaces_has_anchor",
        ),
        Index("ix_adm_workspaces_soaw_id", "soaw_id"),
        Index("ix_adm_workspaces_initiative_id", "initiative_id"),
        Index("ix_adm_workspaces_status", "status"),
        # Partial unique — v1 constraint is at most one workspace per SoAW.
        Index(
            "uq_adm_workspaces_soaw_single",
            "soaw_id",
            unique=True,
            postgresql_where="soaw_id IS NOT NULL",
        ),
    )

    phases = relationship(
        "AdmPhase",
        back_populates="workspace",
        cascade="all, delete-orphan",
        order_by="AdmPhase.sort_order",
        lazy="noload",
    )


class AdmPhase(UUIDMixin, TimestampMixin, Base):
    """One phase within an ADM workspace. Seeded from a code template."""

    __tablename__ = "adm_phases"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("adm_workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    phase_key: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_continuous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="not_started")
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completion_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    gate_notes: Mapped[str | None] = mapped_column(Text)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_comment: Mapped[str | None] = mapped_column(Text)
    approval_override_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("workspace_id", "phase_key", name="uq_adm_phases_workspace_phase"),
        Index("ix_adm_phases_workspace_sort", "workspace_id", "sort_order"),
        Index("ix_adm_phases_status", "status"),
        Index("ix_adm_phases_owner_id", "owner_id"),
    )

    workspace = relationship("AdmWorkspace", back_populates="phases", lazy="noload")
    artefacts = relationship(
        "AdmPhaseArtefact",
        back_populates="phase",
        cascade="all, delete-orphan",
        order_by="AdmPhaseArtefact.sort_order",
        lazy="noload",
    )


class AdmPhaseArtefact(UUIDMixin, TimestampMixin, Base):
    """Evidence link from an ADM phase to an existing Turbo EA entity.

    Never stores the underlying artefact data. ``ref_id`` is a soft foreign
    key dispatched by ``kind`` (see :data:`ADM_ARTEFACT_KINDS`). ``ref_url``
    holds the URL target when ``kind == "url"``.
    """

    __tablename__ = "adm_phase_artefacts"

    phase_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("adm_phases.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ref_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_waived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    waived_reason: Mapped[str | None] = mapped_column(Text)
    waived_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    waived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    linked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_adm_phase_artefacts_phase_id", "phase_id"),
        Index("ix_adm_phase_artefacts_kind_ref", "kind", "ref_id"),
    )

    phase = relationship("AdmPhase", back_populates="artefacts", lazy="noload")
