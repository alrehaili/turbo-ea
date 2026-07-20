"""Create the ``scenarios`` and ``scenario_changes`` tables.

Scenario Planning / Transition Architecture — a copy-on-write overlay where a
scenario stores only its add/modify/retire deltas against the live baseline.

[FORK FEATURE]

Revision ID: 116
Revises: 115
Create Date: 2026-06-28
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1130"
down_revision: Union[str, None] = "1129"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "merged_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_scenarios_status", "scenarios", ["status"])

    op.create_table(
        "scenario_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "scenario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scenarios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("op", sa.String(length=8), nullable=False),
        sa.Column("card_type", sa.String(length=100), nullable=True),
        sa.Column(
            "target_card_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=500), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("merge_status", sa.String(length=16), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_scenario_changes_scenario_id", "scenario_changes", ["scenario_id"])
    op.create_index("ix_scenario_changes_target_card_id", "scenario_changes", ["target_card_id"])


def downgrade() -> None:
    op.drop_index("ix_scenario_changes_target_card_id", table_name="scenario_changes")
    op.drop_index("ix_scenario_changes_scenario_id", table_name="scenario_changes")
    op.drop_table("scenario_changes")
    op.drop_index("ix_scenarios_status", table_name="scenarios")
    op.drop_table("scenarios")
