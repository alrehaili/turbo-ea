"""Add reference_model_mappings table (Reference Models Phase 2 — RMPlan).

Revision ID: 155
Revises: 154

Explicit M:N card↔item mappings with type / status / rationale / confidence /
review metadata. Complements the lightweight card-detail code field, which
still expresses each card's single primary classification. [FORK FEATURE]
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "155"
down_revision = "154"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_model_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mapping_type", sa.String(16), nullable=False, server_default="primary"),
        sa.Column("mapping_status", sa.String(16), nullable=False, server_default="confirmed"),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["reference_models.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["reference_model_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id", "card_id", name="uq_reference_model_mappings_item_card"),
    )
    op.create_index("ix_reference_model_mappings_model", "reference_model_mappings", ["model_id"])
    op.create_index("ix_reference_model_mappings_item", "reference_model_mappings", ["item_id"])
    op.create_index("ix_reference_model_mappings_card", "reference_model_mappings", ["card_id"])


def downgrade() -> None:
    op.drop_index("ix_reference_model_mappings_card", table_name="reference_model_mappings")
    op.drop_index("ix_reference_model_mappings_item", table_name="reference_model_mappings")
    op.drop_index("ix_reference_model_mappings_model", table_name="reference_model_mappings")
    op.drop_table("reference_model_mappings")
