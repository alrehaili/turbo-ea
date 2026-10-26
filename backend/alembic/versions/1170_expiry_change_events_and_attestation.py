"""Expiry-change lifecycle events and remediation attestation (DECISION_LOG I-35, I-36).

Approved 2026-10-26 (decisions B and C):

* ``governance_transitions.event_kind``: NULL for a status transition (every
  row so far); ``expiry_changed`` for an authorized change of an approved
  exception's expiry date, which keeps the status and records the previous
  expiry in the new ``previous_expiry_date`` and the new one in
  ``approved_expiry_date``, with actor, time and reason (I-35).
* ``tech_standard_exceptions.remediation_attestation``: the independent
  verifier's explicit attestation for a remediation the standards scan cannot
  assess — what was examined, why it demonstrates remediation, and the
  evidence fingerprints confirmed unchanged at verification (I-36).

All nullable with **no server default**: no expiry change and no attestation
is invented for the past. Additive; downgrade drops them, and refuses while
expiry-change rows exist, since dropping them would erase recorded history.

[FORK]

Revision ID: 1170
Revises: 1169
Create Date: 2026-10-26
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "1170"
down_revision: Union[str, None] = "1169"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column("governance_transitions", sa.Column("event_kind", sa.String(24), nullable=True))
    op.add_column(
        "governance_transitions", sa.Column("previous_expiry_date", sa.Date(), nullable=True)
    )
    op.create_check_constraint(
        "ck_governance_transitions_event_kind",
        "governance_transitions",
        "event_kind IS NULL OR event_kind IN ('expiry_changed')",
    )
    op.add_column(
        "tech_standard_exceptions",
        sa.Column("remediation_attestation", JSONB(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    in_use = bind.execute(
        sa.text("SELECT count(*) FROM governance_transitions WHERE event_kind IS NOT NULL")
    ).scalar()
    if in_use:
        raise RuntimeError(
            f"{in_use} expiry-change event(s) recorded; downgrading would erase that history."
        )
    op.drop_column("tech_standard_exceptions", "remediation_attestation")
    op.drop_constraint(
        "ck_governance_transitions_event_kind", "governance_transitions", type_="check"
    )
    op.drop_column("governance_transitions", "previous_expiry_date")
    op.drop_column("governance_transitions", "event_kind")
