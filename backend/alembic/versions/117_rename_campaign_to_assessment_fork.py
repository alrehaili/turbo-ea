"""Rename rationalization "campaign" tables to "assessment".

The Application Rationalization container was renamed from *Campaign* to the
standard APM term *Assessment*. Migration 112 now creates the new names for
fresh installs; this migration renames the tables/columns/indexes on databases
that already applied 112 under the old names. All statements are guarded with
``IF EXISTS`` so this is a safe no-op on fresh installs (where 112 already
created the new names).

[FORK FEATURE]

Revision ID: 117
Revises: 116
Create Date: 2026-06-28
"""

from typing import Union

from alembic import op

revision: str = "117"
down_revision: Union[str, None] = "116"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Rename the FK column + child table first, then the parent, then indexes.
    op.execute(
        "ALTER TABLE IF EXISTS campaign_decisions RENAME COLUMN campaign_id TO assessment_id"
    )
    op.execute("ALTER TABLE IF EXISTS campaign_decisions RENAME TO assessment_decisions")
    op.execute(
        "ALTER TABLE IF EXISTS rationalization_campaigns RENAME TO rationalization_assessments"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_rationalization_campaigns_status "
        "RENAME TO ix_rationalization_assessments_status"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_campaign_decisions_campaign_id "
        "RENAME TO ix_assessment_decisions_assessment_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_campaign_decisions_card_id "
        "RENAME TO ix_assessment_decisions_card_id"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX IF EXISTS ix_assessment_decisions_card_id "
        "RENAME TO ix_campaign_decisions_card_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_assessment_decisions_assessment_id "
        "RENAME TO ix_campaign_decisions_campaign_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS ix_rationalization_assessments_status "
        "RENAME TO ix_rationalization_campaigns_status"
    )
    op.execute(
        "ALTER TABLE IF EXISTS rationalization_assessments RENAME TO rationalization_campaigns"
    )
    op.execute("ALTER TABLE IF EXISTS assessment_decisions RENAME TO campaign_decisions")
    op.execute(
        "ALTER TABLE IF EXISTS campaign_decisions RENAME COLUMN assessment_id TO campaign_id"
    )
