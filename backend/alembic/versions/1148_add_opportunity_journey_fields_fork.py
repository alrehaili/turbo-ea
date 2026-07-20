"""Journey-improvement traceability on ``improvement_opportunities``.

Adds ``journey_card_id`` / ``journey_phase`` / ``feasibility`` so the BX
template's journey-improvement rows (journey, phase, gap, opportunity,
impact, feasibility, priority) land in the registry with full traceability.
noraPlan.md WP6.5. Domain values BX/SEC need no schema change (String(4)
already fits) — validation lives in the model constants.

[FORK FEATURE]

Revision ID: 140
Revises: 139
Create Date: 2026-07-11
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1148"
down_revision: Union[str, None] = "1147"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "improvement_opportunities",
        sa.Column(
            "journey_card_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "improvement_opportunities",
        sa.Column("journey_phase", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "improvement_opportunities",
        sa.Column("feasibility", sa.String(length=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("improvement_opportunities", "feasibility")
    op.drop_column("improvement_opportunities", "journey_phase")
    op.drop_column("improvement_opportunities", "journey_card_id")
