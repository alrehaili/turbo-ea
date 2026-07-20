"""Create ``maturity_dimensions``, ``maturity_assessments`` and
``maturity_dimension_scores``.

EA maturity self-assessment (Qiyas-style) — noraPlan.md WP5.2.

[FORK FEATURE]

Revision ID: 133
Revises: 132
Create Date: 2026-07-06
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1141"
down_revision: Union[str, None] = "1140"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "maturity_dimensions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(length=100), nullable=False, unique=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("built_in", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_maturity_dimensions_active", "maturity_dimensions", ["is_active"])

    op.create_table(
        "maturity_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("assessment_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_maturity_assessments_date", "maturity_assessments", ["assessment_date"])

    op.create_table(
        "maturity_dimension_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("maturity_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dimension_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("maturity_dimensions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("dimension_key", sa.String(length=100), nullable=False),
        sa.Column("dimension_name", sa.String(length=200), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("assessment_id", "dimension_id", name="uq_maturity_score_assess_dim"),
    )
    op.create_index(
        "ix_maturity_dimension_scores_assessment", "maturity_dimension_scores", ["assessment_id"]
    )


def downgrade() -> None:
    op.drop_table("maturity_dimension_scores")
    op.drop_table("maturity_assessments")
    op.drop_table("maturity_dimensions")
