"""Add scenario_changes.baseline + support relation-level scenario changes.

Baseline-drift detection: ``baseline`` snapshots the live values of the fields a
``modify`` / ``remove_relation`` change touches, captured when the change is
added. At merge/diff the live value is compared against it — a field that has
since moved is flagged as a **drift** conflict instead of silently clobbering a
concurrent edit. Relation-level ops (add_relation / remove_relation) need no new
column — they ride in the existing ``payload`` JSONB. (Scenario Planning
plan.md 3.1.1.)

[FORK FEATURE]

Revision ID: 160
Revises: 159
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "160"
down_revision = "159"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scenario_changes",
        sa.Column("baseline", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scenario_changes", "baseline")
