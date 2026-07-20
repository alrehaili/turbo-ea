"""Add reference_model_versions table (RMPlan Phase 5 — governance/versioning).

Revision ID: 157
Revises: 156

Preserved snapshots of a reference model's item tree captured at publish time,
so published models are never silently overwritten and any two versions can be
compared. [FORK FEATURE]
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "157"
down_revision = "156"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(32), nullable=False, server_default="1.0"),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["reference_models.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["published_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reference_model_versions_model", "reference_model_versions", ["model_id"])


def downgrade() -> None:
    op.drop_index("ix_reference_model_versions_model", table_name="reference_model_versions")
    op.drop_table("reference_model_versions")
