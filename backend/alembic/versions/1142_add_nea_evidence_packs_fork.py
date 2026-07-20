"""Create ``nea_evidence_packs``.

NEA alignment / evidence-pack export — noraPlan.md WP5.3.

[FORK FEATURE]

Revision ID: 134
Revises: 133
Create Date: 2026-07-06
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1142"
down_revision: Union[str, None] = "1141"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "nea_evidence_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="generating"),
        sa.Column("filename", sa.String(length=500), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("summary", postgresql.JSONB(), nullable=True, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "generated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("nea_evidence_packs")
