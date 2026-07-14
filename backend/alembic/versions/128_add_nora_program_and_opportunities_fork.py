"""Create ``ea_program_deliverables``, ``improvement_opportunities`` and
``improvement_opportunity_cards``.

NORA EA Program tracker (WP3.1) + Improvement Opportunity registry (WP3.3).

[FORK FEATURE]

Revision ID: 128
Revises: 127
Create Date: 2026-07-02
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "128"
down_revision: Union[str, None] = "127"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "ea_program_deliverables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stage_no", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False, unique=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="notStarted"),
        sa.Column("built_in", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
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
    op.create_index("ix_ea_program_deliverables_stage_no", "ea_program_deliverables", ["stage_no"])

    op.create_table(
        "improvement_opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain", sa.String(length=4), nullable=False, server_default="AA"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("priority", sa.String(length=8), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="proposed"),
        sa.Column(
            "initiative_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
    op.create_index("ix_improvement_opportunities_status", "improvement_opportunities", ["status"])
    op.create_index("ix_improvement_opportunities_domain", "improvement_opportunities", ["domain"])

    op.create_table(
        "improvement_opportunity_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("improvement_opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "card_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_improvement_opportunity_cards_opp", "improvement_opportunity_cards", ["opportunity_id"]
    )
    op.create_index(
        "ix_improvement_opportunity_cards_card", "improvement_opportunity_cards", ["card_id"]
    )


def downgrade() -> None:
    op.drop_table("improvement_opportunity_cards")
    op.drop_table("improvement_opportunities")
    op.drop_table("ea_program_deliverables")
