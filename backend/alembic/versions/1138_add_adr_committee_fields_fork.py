"""Add committee-decision fields to ``architecture_decisions``.

NORA committee decision register (noraPlan.md WP3.4): ADRs double as the EA
Governance Committee's decision log — which body decided, in which meeting,
and which NORA stage the decision belongs to.

[FORK FEATURE]

Revision ID: 130
Revises: 129
Create Date: 2026-07-02
"""

from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "1138"
down_revision: Union[str, None] = "1137"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "architecture_decisions", sa.Column("committee", sa.String(length=200), nullable=True)
    )
    op.add_column("architecture_decisions", sa.Column("meeting_date", sa.Date(), nullable=True))
    op.add_column("architecture_decisions", sa.Column("stage_no", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("architecture_decisions", "stage_no")
    op.drop_column("architecture_decisions", "meeting_date")
    op.drop_column("architecture_decisions", "committee")
