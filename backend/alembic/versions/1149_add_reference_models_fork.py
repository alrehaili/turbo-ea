"""Reference Models — per-domain classification schemes (NEA National RMs).

Two tables: ``reference_models`` (versioned, governable scheme with a domain
discriminator and draft/published/archived lifecycle) and
``reference_model_items`` (hierarchical entries, uniquely coded per model).
noraPlan.md WP100.3.

[FORK FEATURE]

Revision ID: 1149
Revises: 1148
Create Date: 2026-07-14
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1149"
down_revision: Union[str, None] = "1148"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "reference_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("domain", sa.String(length=32), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=True, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_ar", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="agency"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("built_in", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "published_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_reference_models_domain", "reference_models", ["domain"])
    op.create_index("ix_reference_models_status", "reference_models", ["status"])

    op.create_table(
        "reference_model_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reference_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reference_model_items.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_ar", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("model_id", "code", name="uq_reference_model_items_model_code"),
    )
    op.create_index("ix_reference_model_items_model", "reference_model_items", ["model_id"])
    op.create_index("ix_reference_model_items_parent", "reference_model_items", ["parent_id"])


def downgrade() -> None:
    op.drop_table("reference_model_items")
    op.drop_table("reference_models")
