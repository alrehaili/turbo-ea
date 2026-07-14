"""Automated maturity assessment: suggested level + evidence on scores.

[FORK FEATURE] The EA maturity self-assessment gains repository-derived
evidence: each dimension score carries an advisory ``suggested_level``
(banded from live coverage/adoption/quality indicators) and the ``evidence``
JSONB snapshot of the indicators it was derived from. The assessor always
confirms the actual ``level`` — the suggestion is never binding.

Revision ID: 138
Revises: 137
Create Date: 2026-07-09
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "146"
down_revision: Union[str, None] = "145"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "maturity_dimension_scores",
        sa.Column("suggested_level", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "maturity_dimension_scores",
        sa.Column("evidence", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("maturity_dimension_scores", "evidence")
    op.drop_column("maturity_dimension_scores", "suggested_level")
