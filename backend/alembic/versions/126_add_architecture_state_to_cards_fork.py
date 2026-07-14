"""Add the architecture-state dimension to ``cards``.

NORA Stages 6/7 (current vs target architecture) / TOGAF baseline-target —
noraPlan.md WP2.1. Three columns:

* ``architecture_state`` — which blueprint the card belongs to
  (``current`` default | ``transition`` | ``target``). Orthogonal to
  lifecycle: lifecycle says *when a real asset lives*, architecture state
  says *which landscape slice the card describes*.
* ``change_type`` — typed target-change semantics
  (``create`` | ``modify`` | ``replace`` | ``retire`` | ``consolidate``).
  A target card *is* the change; ``retire`` may also sit on a current-state
  card to mark a planned retirement with no successor.
* ``successor_id`` — for ``replace``/``consolidate``: the card this one
  supersedes points here (target card → the current card it replaces).

[FORK FEATURE]

Revision ID: 126
Revises: 125
Create Date: 2026-07-02
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "126"
down_revision: Union[str, None] = "125"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "cards",
        sa.Column(
            "architecture_state", sa.String(length=16), nullable=False, server_default="current"
        ),
    )
    op.add_column("cards", sa.Column("change_type", sa.String(length=16), nullable=True))
    op.add_column(
        "cards",
        sa.Column(
            "successor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_cards_architecture_state", "cards", ["architecture_state"])
    op.create_index("ix_cards_successor_id", "cards", ["successor_id"])


def downgrade() -> None:
    op.drop_index("ix_cards_successor_id", table_name="cards")
    op.drop_index("ix_cards_architecture_state", table_name="cards")
    op.drop_column("cards", "successor_id")
    op.drop_column("cards", "change_type")
    op.drop_column("cards", "architecture_state")
