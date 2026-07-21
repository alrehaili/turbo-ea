"""Create the ``rationalization_assessments`` and ``assessment_decisions`` tables.

Application Rationalization Assessments package the TIME-framework portfolio
decision workflow (Tolerate / Invest / Migrate / Eliminate) over a set of
applications, tracking successor, annual cost, planned savings, the delivering
initiative, and progress per application.

[FORK FEATURE]

Revision ID: 1126
Revises: 1125
Create Date: 2026-06-27
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1126"
down_revision: Union[str, None] = "1125"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "rationalization_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("target_savings", sa.Float(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_rationalization_assessments_status", "rationalization_assessments", ["status"]
    )

    op.create_table(
        "assessment_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "assessment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rationalization_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "card_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "time_decision", sa.String(length=16), nullable=False, server_default="undecided"
        ),
        sa.Column(
            "successor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "initiative_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("annual_cost", sa.Float(), nullable=True),
        sa.Column("planned_savings", sa.Float(), nullable=True),
        sa.Column("risk_note", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_assessment_decisions_assessment_id", "assessment_decisions", ["assessment_id"]
    )
    op.create_index("ix_assessment_decisions_card_id", "assessment_decisions", ["card_id"])


def downgrade() -> None:
    op.drop_index("ix_assessment_decisions_card_id", table_name="assessment_decisions")
    op.drop_index("ix_assessment_decisions_assessment_id", table_name="assessment_decisions")
    op.drop_table("assessment_decisions")
    op.drop_index("ix_rationalization_assessments_status", table_name="rationalization_assessments")
    op.drop_table("rationalization_assessments")
