"""Add ``rationale`` column to ``assessment_decisions``.

Rationalization decisions on the Application Portfolio Review board used to
carry only ``notes`` (how to execute) and ``risk_note`` (what could go wrong).
The strategic *why* — the reason a board took the decision — was captured in
the seed data but never persisted, so a decision like "Tableau → Power BI
migrate" showed no supporting rationale in the UI.

This migration adds a nullable ``rationale`` Text column for the strategic
reasoning, distinct from ``notes`` and ``risk_note``. Backfill happens in
the seed on the next boot; existing decisions get ``NULL`` (safe, editable).

Revision ID: 131
Revises: 130
Create Date: 2026-07-04
"""

from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "1139"
down_revision: Union[str, None] = "1138"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("assessment_decisions", sa.Column("rationale", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("assessment_decisions", "rationale")
