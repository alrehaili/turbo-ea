"""Benefits register (D-12, D-14, D-29, D-43; Phase 4 Batch 4.1).

Six tables: ``benefits``, ``benefit_links`` (initiatives with their D-14
classification, affected cards), ``benefit_actuals`` (reported actuals per
fiscal year, confirmed by Finance), ``benefit_allocations`` (Finance's
attributable amounts), ``benefit_assessments`` (qualitative outcomes) and
``benefit_history`` (append-only). Nothing is created for existing data.

Additive; downgrade refuses while benefits exist, since dropping them would
erase Finance confirmations and their history.

[FORK]

Revision ID: 1175
Revises: 1174
Create Date: 2026-10-27
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "1175"
down_revision: Union[str, None] = "1174"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def _user(name: str) -> sa.Column:
    return sa.Column(
        name, UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "benefits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("reference", sa.String(16), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("benefit_type", sa.String(20), nullable=False),
        sa.Column("measurement", sa.String(12), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="planned"),
        _user("owner_id"),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("recurrence", sa.String(12), nullable=True),
        sa.Column("planned_amount", sa.Float(), nullable=True),
        sa.Column("baseline_amount", sa.Float(), nullable=True),
        sa.Column("counterfactual_amount", sa.Float(), nullable=True),
        sa.Column("counterfactual_note", sa.Text(), nullable=True),
        sa.Column("method_note", sa.Text(), nullable=True),
        sa.Column("expected_fiscal_year", sa.Integer(), nullable=True),
        sa.Column("decision_kind", sa.String(16), nullable=True),
        sa.Column("decision_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "kpi_card_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _user("created_by"),
        _user("estimated_by"),
        _user("validated_by"),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_note", sa.Text(), nullable=True),
        _user("closed_by"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "benefit_type IN ('cost_saving', 'cost_avoidance', 'revenue', "
            "'productivity', 'non_financial')",
            name="ck_benefits_type",
        ),
        sa.CheckConstraint(
            "measurement IN ('financial', 'kpi', 'qualitative')", name="ck_benefits_measurement"
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'validated', 'not_realised', 'withdrawn')",
            name="ck_benefits_status",
        ),
        sa.CheckConstraint(
            "decision_kind IS NULL OR decision_kind IN "
            "('adr', 'arb', 'rationalization', 'opportunity')",
            name="ck_benefits_decision_kind",
        ),
        sa.CheckConstraint(
            "measurement = 'financial' OR (planned_amount IS NULL AND baseline_amount IS NULL "
            "AND counterfactual_amount IS NULL AND currency IS NULL)",
            name="ck_benefits_outcome_no_amounts",
        ),
    )
    op.create_index("ix_benefits_decision", "benefits", ["decision_kind", "decision_id"])

    op.create_table(
        "benefit_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "benefit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("benefits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "card_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(12), nullable=False),
        sa.Column("classification", sa.String(20), nullable=True),
        sa.UniqueConstraint("benefit_id", "card_id", "role", name="uq_benefit_links"),
        sa.CheckConstraint("role IN ('initiative', 'affected')", name="ck_benefit_links_role"),
        sa.CheckConstraint(
            "(role = 'initiative' AND classification IN "
            "('direct', 'contributing', 'not_attributable')) "
            "OR (role = 'affected' AND classification IS NULL)",
            name="ck_benefit_links_classification",
        ),
    )
    op.create_index("ix_benefit_links_card", "benefit_links", ["card_id"])

    op.create_table(
        "benefit_actuals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "benefit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("benefits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="reported"),
        _user("reported_by"),
        sa.Column(
            "reported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("report_note", sa.Text(), nullable=True),
        sa.Column("evidence_refs", JSONB(), nullable=True),
        _user("decided_by"),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finance_reference", sa.String(200), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        _user("reversed_by"),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverse_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('reported', 'confirmed', 'rejected', 'reversed')",
            name="ck_benefit_actuals_status",
        ),
        sa.CheckConstraint("amount >= 0", name="ck_benefit_actuals_amount"),
    )
    op.create_index(
        "uq_benefit_actuals_live",
        "benefit_actuals",
        ["benefit_id", "fiscal_year"],
        unique=True,
        postgresql_where=sa.text("status IN ('reported', 'confirmed')"),
    )

    op.create_table(
        "benefit_allocations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "actual_id",
            UUID(as_uuid=True),
            sa.ForeignKey("benefit_actuals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "card_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("classification", sa.String(20), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "classification IN ('direct', 'contributing')",
            name="ck_benefit_allocations_classification",
        ),
        sa.CheckConstraint("amount > 0", name="ck_benefit_allocations_amount"),
    )
    op.create_index("ix_benefit_allocations_actual", "benefit_allocations", ["actual_id"])

    op.create_table(
        "benefit_assessments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "benefit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("benefits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("evidence_refs", JSONB(), nullable=True),
        _user("assessed_by"),
        sa.Column(
            "assessed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "outcome IN ('achieved', 'partially_achieved', 'not_achieved')",
            name="ck_benefit_assessments_outcome",
        ),
    )
    op.create_index(
        "ix_benefit_assessments_benefit", "benefit_assessments", ["benefit_id", "assessed_at"]
    )

    op.create_table(
        "benefit_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "benefit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("benefits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("from_status", sa.String(16), nullable=True),
        sa.Column("to_status", sa.String(16), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("changes", JSONB(), nullable=True),
        _user("actor_id"),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_benefit_history_benefit", "benefit_history", ["benefit_id", "occurred_at"])


def downgrade() -> None:
    bind = op.get_bind()
    in_use = bind.execute(sa.text("SELECT count(*) FROM benefits")).scalar()
    if in_use:
        raise RuntimeError(f"{in_use} benefit(s) exist; downgrading would erase them.")
    for table in (
        "benefit_history",
        "benefit_assessments",
        "benefit_allocations",
        "benefit_actuals",
        "benefit_links",
        "benefits",
    ):
        op.drop_table(table)
