"""Create the ``standards`` and ``standard_principles`` tables.

Architecture Standards are admin-managed specifications that implement one or
more EA principles. The ``standard_principles`` junction is the many-to-many link
between a standard and the principles it realises (Admin → Metamodel → Standards,
GRC → Governance → Standards).

Revision ID: 110
Revises: 109
Create Date: 2026-06-26
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "110"
down_revision: Union[str, None] = "109"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "standards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("implications", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("catalogue_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_standards_catalogue_id", "standards", ["catalogue_id"])

    op.create_table(
        "standard_principles",
        sa.Column(
            "standard_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("standards.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "principle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ea_principles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("standard_principles")
    op.drop_index("ix_standards_catalogue_id", table_name="standards")
    op.drop_table("standards")
