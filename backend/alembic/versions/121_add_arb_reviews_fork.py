"""Create the ``arb_reviews`` table (Architecture Review Board decisions).

[FORK FEATURE]

Revision ID: 115
Revises: 114
Create Date: 2026-06-28
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "115"
down_revision: Union[str, None] = "114"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "arb_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column(
            "subject_card_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="scheduled"),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column(
            "reviewer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_arb_reviews_status", "arb_reviews", ["status"])
    op.create_index("ix_arb_reviews_subject_card_id", "arb_reviews", ["subject_card_id"])


def downgrade() -> None:
    op.drop_index("ix_arb_reviews_subject_card_id", table_name="arb_reviews")
    op.drop_index("ix_arb_reviews_status", table_name="arb_reviews")
    op.drop_table("arb_reviews")
