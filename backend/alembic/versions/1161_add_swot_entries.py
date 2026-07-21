"""Structured SWOT entries for Environment-Analysis documents.

Adds the ``swot_entries`` table so the four SWOT quadrants of a NORA
Environment-Analysis governed document can carry structured, promotable rows
(weakness / threat → Improvement Opportunity), mirroring the compliance-finding
→ risk bridge. The rich-text quadrants on the SoAW ``sections`` JSONB are
untouched; this table is additive.

[FORK FEATURE] — noraPlan.md WP3.3.

Revision ID: 1161
Revises: 1160
Create Date: 2026-07-20
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1161"
down_revision: Union[str, None] = "1160"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "swot_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("soaw_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quadrant", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["soaw_id"],
            ["statement_of_architecture_works.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["improvement_opportunities.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_swot_entries_soaw_id", "swot_entries", ["soaw_id"])


def downgrade() -> None:
    op.drop_index("ix_swot_entries_soaw_id", table_name="swot_entries")
    op.drop_table("swot_entries")
