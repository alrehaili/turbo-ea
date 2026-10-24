"""Widen ``scenario_changes.op`` to fit the relation ops.

Migration 1130 created the column as ``VARCHAR(8)``, which holds ``add``,
``modify`` and ``retire`` but not ``add_relation`` (12) or ``remove_relation``
(15), so every relation scenario change failed on insert with a string
truncation error. Widening a ``VARCHAR`` is a metadata-only change in
PostgreSQL: no row is rewritten and existing values are unaffected.

[FORK FIX]

Revision ID: 1162
Revises: 154
Create Date: 2026-10-24
"""

from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "1162"
down_revision: Union[str, None] = "154"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.alter_column(
        "scenario_changes",
        "op",
        existing_type=sa.String(length=8),
        type_=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Fails (and changes nothing) while relation changes exist: narrowing
    # must never silently drop or truncate scenario data.
    op.alter_column(
        "scenario_changes",
        "op",
        existing_type=sa.String(length=32),
        type_=sa.String(length=8),
        existing_nullable=False,
    )
