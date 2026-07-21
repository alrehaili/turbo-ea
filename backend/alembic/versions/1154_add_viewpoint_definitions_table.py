"""Add viewpoint_definitions table for NORA/DGA EA Viewpoints registry.

Revision ID: 1154
Revises: 1153

The viewpoint_definitions table tracks all 67 NORA viewpoints with metadata:
code, bilingual names, domain, level, type, building blocks, target route, status.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "1154"
down_revision = "1153"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create viewpoint_definitions table."""
    op.create_table(
        "viewpoint_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name_en", sa.String(200), nullable=False),
        sa.Column("name_ar", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("description_en", sa.String(500), nullable=True),
        sa.Column("description_ar", sa.String(500), nullable=True),
        sa.Column(
            "building_blocks", postgresql.JSONB(astext_type=sa.Text()), default=[], nullable=True
        ),
        sa.Column("target_route", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), default="available", nullable=False),
        sa.Column("sort_order", sa.Integer(), default=0, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_viewpoint_definitions_code"),
        "viewpoint_definitions",
        ["code"],
        unique=True,
    )
    op.create_index(
        op.f("ix_viewpoint_definitions_domain"),
        "viewpoint_definitions",
        ["domain"],
    )


def downgrade() -> None:
    """Drop viewpoint_definitions table."""
    op.drop_index(
        op.f("ix_viewpoint_definitions_domain"),
        table_name="viewpoint_definitions",
    )
    op.drop_index(
        op.f("ix_viewpoint_definitions_code"),
        table_name="viewpoint_definitions",
    )
    op.drop_table("viewpoint_definitions")
