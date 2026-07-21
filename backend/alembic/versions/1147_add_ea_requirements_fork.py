"""Create ``ea_requirements`` and ``ea_requirement_cards``.

EA Requirements register — the continuous element (phase 7) of the updated
Dec-2024 National EA Framework methodology. noraPlan.md WP6.1.

[FORK FEATURE]

Revision ID: 1147
Revises: 1146
Create Date: 2026-07-11
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1147"
down_revision: Union[str, None] = "1146"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "ea_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=200), nullable=True),
        sa.Column("domain", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="proposed"),
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_ea_requirements_status", "ea_requirements", ["status"])
    op.create_index("ix_ea_requirements_domain", "ea_requirements", ["domain"])

    op.create_table(
        "ea_requirement_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "requirement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ea_requirements.id", ondelete="CASCADE"),
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
    op.create_index("ix_ea_requirement_cards_req", "ea_requirement_cards", ["requirement_id"])
    op.create_index("ix_ea_requirement_cards_card", "ea_requirement_cards", ["card_id"])


def downgrade() -> None:
    op.drop_table("ea_requirement_cards")
    op.drop_table("ea_requirements")
