"""Governance transition history and the exception decision timestamp.

Decisions D-34 and D-35 (approved 2026-10-25), Batch 3.2:

* ``governance_transitions``: one append-only row per status change of an ADR,
  an ARB review or a technology-standard exception. Created **empty**: no
  history is manufactured for records decided before this migration, which
  read "lifecycle not recorded" (D-34). ``occurred_at`` / ``created_at`` /
  ``updated_at`` carry ``server_default=now()``.
* ``tech_standard_exceptions.decided_at``: when the latest approve / reject
  decision was recorded. Deliberately **nullable with no server default** — a
  default would date every existing decision to the day of the upgrade, which
  is exactly the invented history D-34 forbids. Existing rows stay NULL.

Withdrawal and remediation columns are not added: their workflow waits on
D-40. Additive only; downgrade drops what upgrade created.

[FORK]

Revision ID: 1166
Revises: 1165
Create Date: 2026-10-26
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "1166"
down_revision: Union[str, None] = "1165"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "governance_transitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("instrument", sa.String(16), nullable=False),
        sa.Column("record_id", UUID(as_uuid=True), nullable=False),
        sa.Column("from_status", sa.String(50), nullable=True),
        sa.Column("to_status", sa.String(50), nullable=False),
        sa.Column(
            "actor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "instrument IN ('adr', 'arb', 'exception')",
            name="ck_governance_transitions_instrument",
        ),
    )
    op.create_index(
        "ix_governance_transitions_record",
        "governance_transitions",
        ["instrument", "record_id"],
    )
    op.create_index(
        "ix_governance_transitions_occurred_at", "governance_transitions", ["occurred_at"]
    )
    op.add_column(
        "tech_standard_exceptions",
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tech_standard_exceptions", "decided_at")
    op.drop_index("ix_governance_transitions_occurred_at", table_name="governance_transitions")
    op.drop_index("ix_governance_transitions_record", table_name="governance_transitions")
    op.drop_table("governance_transitions")
