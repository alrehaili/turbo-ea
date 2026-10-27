"""Benefits register (D-12, D-14, D-43; Phase 4 Batch 4.1).

A **benefit** is a measurable business outcome expected from a digital
initiative or an architecture decision. Financial benefits (cost saving, cost
avoidance, revenue) carry a currency and amounts; productivity and other
non-financial benefits never carry an amount (D-43): they are measured by a KPI
card or assessed qualitatively.

``benefit_links`` ties a benefit to the initiatives that deliver it — each with
its attribution classification (D-14) — and to the cards it affects.

Benefits are never deleted: they are withdrawn or closed as not realised, so
the register and its history stay complete.

[FORK]
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
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

COST_SAVING = "cost_saving"
COST_AVOIDANCE = "cost_avoidance"
REVENUE = "revenue"
PRODUCTIVITY = "productivity"
NON_FINANCIAL = "non_financial"
FINANCIAL_TYPES = (COST_SAVING, COST_AVOIDANCE, REVENUE)
OUTCOME_TYPES = (PRODUCTIVITY, NON_FINANCIAL)
BENEFIT_TYPES = FINANCIAL_TYPES + OUTCOME_TYPES

MEASUREMENT_FINANCIAL = "financial"
MEASUREMENT_KPI = "kpi"
MEASUREMENT_QUALITATIVE = "qualitative"
MEASUREMENTS = (MEASUREMENT_FINANCIAL, MEASUREMENT_KPI, MEASUREMENT_QUALITATIVE)

STATUS_PLANNED = "planned"
STATUS_VALIDATED = "validated"
STATUS_NOT_REALISED = "not_realised"
STATUS_WITHDRAWN = "withdrawn"
STATUSES = (STATUS_PLANNED, STATUS_VALIDATED, STATUS_NOT_REALISED, STATUS_WITHDRAWN)
CLOSED_STATUSES = (STATUS_NOT_REALISED, STATUS_WITHDRAWN)

ONE_TIME = "one_time"
ANNUAL = "annual"
RECURRENCES = (ONE_TIME, ANNUAL)

#: The governing decision a benefit may name (I-73).
DECISION_ADR = "adr"
DECISION_ARB = "arb"
DECISION_RATIONALIZATION = "rationalization"
DECISION_OPPORTUNITY = "opportunity"
DECISION_KINDS = (DECISION_ADR, DECISION_ARB, DECISION_RATIONALIZATION, DECISION_OPPORTUNITY)

ROLE_INITIATIVE = "initiative"
ROLE_AFFECTED = "affected"
LINK_ROLES = (ROLE_INITIATIVE, ROLE_AFFECTED)

#: D-14 attribution classifications of an initiative link.
DIRECT = "direct"
CONTRIBUTING = "contributing"
NOT_ATTRIBUTABLE = "not_attributable"
CLASSIFICATIONS = (DIRECT, CONTRIBUTING, NOT_ATTRIBUTABLE)
ALLOCATABLE = (DIRECT, CONTRIBUTING)


class Benefit(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "benefits"

    reference: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefit_type: Mapped[str] = mapped_column(String(20), nullable=False)
    measurement: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=STATUS_PLANNED)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Financial basis (financial types only; NULL on every outcome benefit).
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    recurrence: Mapped[str | None] = mapped_column(String(12), nullable=True)
    planned_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    counterfactual_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    counterfactual_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    method_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # The governing decision (I-73): polymorphic, so no foreign key.
    decision_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # The KPI card measuring an outcome benefit (D-43).
    kpi_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Who last set the planned amount (D-29: may not confirm).
    estimated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    validated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "benefit_type IN ('cost_saving', 'cost_avoidance', 'revenue', "
            "'productivity', 'non_financial')",
            name="ck_benefits_type",
        ),
        CheckConstraint(
            "measurement IN ('financial', 'kpi', 'qualitative')", name="ck_benefits_measurement"
        ),
        CheckConstraint(
            "status IN ('planned', 'validated', 'not_realised', 'withdrawn')",
            name="ck_benefits_status",
        ),
        CheckConstraint(
            "decision_kind IS NULL OR decision_kind IN "
            "('adr', 'arb', 'rationalization', 'opportunity')",
            name="ck_benefits_decision_kind",
        ),
        # D-43: an outcome benefit is never monetised.
        CheckConstraint(
            "measurement = 'financial' OR (planned_amount IS NULL AND baseline_amount IS NULL "
            "AND counterfactual_amount IS NULL AND currency IS NULL)",
            name="ck_benefits_outcome_no_amounts",
        ),
        Index("ix_benefits_decision", "decision_kind", "decision_id"),
    )


class BenefitLink(UUIDMixin, Base):
    """An initiative delivering a benefit (with its D-14 classification), or a
    card the benefit affects."""

    __tablename__ = "benefit_links"

    benefit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("benefits.id", ondelete="CASCADE"), nullable=False
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(12), nullable=False)
    classification: Mapped[str | None] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        UniqueConstraint("benefit_id", "card_id", "role", name="uq_benefit_links"),
        CheckConstraint("role IN ('initiative', 'affected')", name="ck_benefit_links_role"),
        CheckConstraint(
            "(role = 'initiative' AND classification IN "
            "('direct', 'contributing', 'not_attributable')) "
            "OR (role = 'affected' AND classification IS NULL)",
            name="ck_benefit_links_classification",
        ),
        Index("ix_benefit_links_card", "card_id"),
    )
