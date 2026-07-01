"""Add repository-freshness metadata columns to ``cards``.

``last_confirmed_at`` (when a steward last confirmed the card is accurate),
``source_system`` (system of record the data came from), and ``confidence``
(coarse low/medium/high data-confidence marker) power the Repository Freshness
View (Wave 2 #4). All three are nullable and default NULL on existing rows.

[FORK FEATURE]

Revision ID: 113
Revises: 112
Create Date: 2026-06-27
"""

from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "113"
down_revision: Union[str, None] = "112"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "cards", sa.Column("last_confirmed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("cards", sa.Column("source_system", sa.String(length=200), nullable=True))
    op.add_column("cards", sa.Column("confidence", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("cards", "confidence")
    op.drop_column("cards", "source_system")
    op.drop_column("cards", "last_confirmed_at")
