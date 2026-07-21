"""Create the Technology Standards catalogue + exception register.

``tech_standards`` holds technology/cloud/integration/data/security standards on
the radar adoption scale (preferred / allowed / tolerated / sunset / prohibited),
each optionally nominating a replacement standard. ``tech_standard_exceptions``
is the time-boxed, approver-gated waiver register linking a standard to the
application/initiative that deviates from it.

This is a clean, separate catalogue distinct from the principle-linked
``standards`` table added in migration 110.

[FORK FEATURE]

Revision ID: 1128
Revises: 1127
Create Date: 2026-06-28
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1128"
down_revision: Union[str, None] = "1127"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "tech_standards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("category", sa.String(length=24), nullable=False, server_default="technology"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="allowed"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "replacement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tech_standards.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_tech_standards_category", "tech_standards", ["category"])
    op.create_index("ix_tech_standards_status", "tech_standards", ["status"])

    op.create_table(
        "tech_standard_exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "standard_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tech_standards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "card_id",
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
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("compensating_controls", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="requested"),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column(
            "approver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
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
    op.create_index(
        "ix_tech_standard_exceptions_standard_id", "tech_standard_exceptions", ["standard_id"]
    )
    op.create_index("ix_tech_standard_exceptions_card_id", "tech_standard_exceptions", ["card_id"])
    op.create_index("ix_tech_standard_exceptions_status", "tech_standard_exceptions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_tech_standard_exceptions_status", table_name="tech_standard_exceptions")
    op.drop_index("ix_tech_standard_exceptions_card_id", table_name="tech_standard_exceptions")
    op.drop_index("ix_tech_standard_exceptions_standard_id", table_name="tech_standard_exceptions")
    op.drop_table("tech_standard_exceptions")
    op.drop_index("ix_tech_standards_status", table_name="tech_standards")
    op.drop_index("ix_tech_standards_category", table_name="tech_standards")
    op.drop_table("tech_standards")
