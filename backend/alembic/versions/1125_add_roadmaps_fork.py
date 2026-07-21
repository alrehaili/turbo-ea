"""Create the ``roadmaps`` and ``roadmap_milestones`` tables.

The Transformation Roadmap is a saved, scoped lifecycle-timeline view. A roadmap
stores only its view configuration (swimlane grouping, card type, time window,
filters) in ``config``; the timeline bars are computed on demand from each card's
``lifecycle`` JSONB. Milestones are dated markers optionally tied to an Initiative
card driving the change.

[FORK FEATURE]

Revision ID: 1125
Revises: 124
Create Date: 2026-06-27
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1125"
down_revision: Union[str, None] = "124"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "roadmaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "owner_id",
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

    op.create_table(
        "roadmap_milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roadmaps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=300), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column(
            "initiative_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_roadmap_milestones_roadmap_id", "roadmap_milestones", ["roadmap_id"])


def downgrade() -> None:
    op.drop_index("ix_roadmap_milestones_roadmap_id", table_name="roadmap_milestones")
    op.drop_table("roadmap_milestones")
    op.drop_table("roadmaps")
