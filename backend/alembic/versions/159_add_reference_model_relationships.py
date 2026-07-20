"""Add reference_model_relationships table (Reference Models §10 — RMPlan).

Typed, cross-cutting item↔item links (supports / consumes / realizes /
depends_on / aligns_with), usually *between* models — e.g. an ARM application
component that realizes a BRM capability. Distinct from the ``parent_id``
hierarchy, which is intra-model composition. [FORK FEATURE]

Revision ID: 159
Revises: 158
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "159"
down_revision = "158"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_model_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(32), nullable=False, server_default="supports"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_item_id"], ["reference_model_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_item_id"], ["reference_model_items.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_item_id",
            "target_item_id",
            "relationship_type",
            name="uq_reference_model_relationships_triple",
        ),
    )
    op.create_index(
        "ix_reference_model_relationships_source",
        "reference_model_relationships",
        ["source_item_id"],
    )
    op.create_index(
        "ix_reference_model_relationships_target",
        "reference_model_relationships",
        ["target_item_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reference_model_relationships_target", table_name="reference_model_relationships"
    )
    op.drop_index(
        "ix_reference_model_relationships_source", table_name="reference_model_relationships"
    )
    op.drop_table("reference_model_relationships")
