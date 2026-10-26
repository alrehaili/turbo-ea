"""Exception remediation / withdrawal lifecycle and delay reasons (D-39, D-40).

Approved 2026-10-26, Batch 3.2:

* ``tech_standard_exceptions``: ``status`` widened to 32 characters for
  ``remediation_submitted``; new nullable columns for the remediation evidence,
  its submitter and verifier with their times, and the withdrawal actor, time
  and reason. **No server defaults**: every existing row stays NULL, so no
  remediation or withdrawal is invented for the past (D-40).
* ``governance_transitions``: nullable ``reason`` and ``delay_attribution``
  (``governance`` / ``requester`` / ``external``, checked). Existing rows stay
  NULL — an unattributed interval is never treated as excludable (D-39).

Additive. Downgrade drops the columns and restores the 16-character status; it
refuses while any row carries one of the new states, because mapping them back
to an old state would rewrite that exception's history.

[FORK]

Revision ID: 1167
Revises: 1166
Create Date: 2026-10-26
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "1167"
down_revision: Union[str, None] = "1166"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None

NEW_STATES = ("remediation_submitted", "remediated", "withdrawn")


def _user_fk(name: str) -> sa.Column:
    return sa.Column(
        name, UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


def upgrade() -> None:
    op.alter_column(
        "tech_standard_exceptions",
        "status",
        type_=sa.String(32),
        existing_type=sa.String(16),
        existing_nullable=True,
    )
    op.add_column("tech_standard_exceptions", sa.Column("remediation_evidence", sa.Text()))
    op.add_column("tech_standard_exceptions", _user_fk("remediation_submitted_by"))
    op.add_column(
        "tech_standard_exceptions",
        sa.Column("remediation_submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("tech_standard_exceptions", _user_fk("remediation_verified_by"))
    op.add_column(
        "tech_standard_exceptions",
        sa.Column("remediation_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("tech_standard_exceptions", _user_fk("withdrawn_by"))
    op.add_column(
        "tech_standard_exceptions",
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("tech_standard_exceptions", sa.Column("withdrawal_reason", sa.Text()))

    op.add_column("governance_transitions", sa.Column("reason", sa.Text(), nullable=True))
    op.add_column(
        "governance_transitions", sa.Column("delay_attribution", sa.String(16), nullable=True)
    )
    op.create_check_constraint(
        "ck_governance_transitions_delay_attribution",
        "governance_transitions",
        "delay_attribution IS NULL OR delay_attribution IN ('governance', 'requester', 'external')",
    )


def downgrade() -> None:
    bind = op.get_bind()
    in_use = bind.execute(
        sa.text("SELECT count(*) FROM tech_standard_exceptions WHERE status IN :states").bindparams(
            sa.bindparam("states", expanding=True)
        ),
        {"states": list(NEW_STATES)},
    ).scalar()
    if in_use:
        raise RuntimeError(
            f"{in_use} exception(s) are remediation_submitted / remediated / withdrawn; "
            "downgrading would lose their lifecycle. Resolve them first."
        )
    op.drop_constraint(
        "ck_governance_transitions_delay_attribution", "governance_transitions", type_="check"
    )
    op.drop_column("governance_transitions", "delay_attribution")
    op.drop_column("governance_transitions", "reason")
    for column in (
        "withdrawal_reason",
        "withdrawn_at",
        "withdrawn_by",
        "remediation_verified_at",
        "remediation_verified_by",
        "remediation_submitted_at",
        "remediation_submitted_by",
        "remediation_evidence",
    ):
        op.drop_column("tech_standard_exceptions", column)
    op.alter_column(
        "tech_standard_exceptions",
        "status",
        type_=sa.String(16),
        existing_type=sa.String(32),
        existing_nullable=True,
    )
