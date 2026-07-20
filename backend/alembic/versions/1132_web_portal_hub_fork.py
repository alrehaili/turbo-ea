"""Add hub-portal support to web_portals.

Adds ``kind`` ("catalogue" | "hub") and ``tiles`` (hub layout) and relaxes
``card_type`` to nullable so a hub portal (a curated landing page of tiles) does
not need to be bound to a single card type. Existing portals default to
``kind = 'catalogue'`` and keep their card_type, so behaviour is unchanged.

[FORK FEATURE]

Revision ID: 118
Revises: 117
Create Date: 2026-06-28
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1132"
down_revision: Union[str, None] = "1131"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "web_portals",
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="catalogue"),
    )
    op.add_column("web_portals", sa.Column("tiles", postgresql.JSONB(), nullable=True))
    op.alter_column("web_portals", "card_type", existing_type=sa.String(length=100), nullable=True)


def downgrade() -> None:
    op.alter_column("web_portals", "card_type", existing_type=sa.String(length=100), nullable=False)
    op.drop_column("web_portals", "tiles")
    op.drop_column("web_portals", "kind")
