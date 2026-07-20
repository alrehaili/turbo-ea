"""Widen ``users.role`` from VARCHAR(20) to VARCHAR(50).

Role keys are admin-definable and ``roles.key`` is already String(50), but
``users.role`` was still String(20) — assigning a user any role whose key is
longer than 20 characters (e.g. the NORA governance pack's
``ea_governance_committee``, 23 chars) failed with a right-truncation error.

[FORK FEATURE] — noraPlan.md WP2.3 defect, surfaced by the WP6.2 test run.

Revision ID: 136
Revises: 135
Create Date: 2026-07-07
"""

from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "1144"
down_revision: Union[str, None] = "1143"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=20),
        type_=sa.String(length=50),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Only safe if no role key longer than 20 chars is assigned; matches the
    # pre-136 state.
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=50),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
