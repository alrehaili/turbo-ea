"""Business calendar per fiscal year (D-28, D-38; Executive dashboard Batch 3.3).

``business_calendar_years``: one row per fiscal year with its working week
(ISO weekdays, Sunday–Thursday by default), its official holidays and whether
it is confirmed. No row is created here: a fiscal year without a confirmed row
yields no working-day figure, so nothing is assumed for any year.

Additive; downgrade drops the table.

[FORK]

Revision ID: 1171
Revises: 1170
Create Date: 2026-10-27
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "1171"
down_revision: Union[str, None] = "1170"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "business_calendar_years",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("fiscal_year", sa.Integer(), nullable=False, unique=True),
        sa.Column(
            "working_weekdays",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[7, 1, 2, 3, 4]'::jsonb"),
        ),
        sa.Column("holidays", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "confirmed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("business_calendar_years")
