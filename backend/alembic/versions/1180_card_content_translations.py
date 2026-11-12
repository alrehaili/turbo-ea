"""Per-locale card content: ``cards.translations``.

Holds ``{"ar": {"name", "description", "alias"}}``; the plain columns stay the
English baseline (``services/card_translations.py``).

Revision ID: 1180
Revises: 1179
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "1180"
down_revision: str | Sequence[str] | None = "1179"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cards",
        sa.Column(
            "translations",
            JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("cards", "translations")
