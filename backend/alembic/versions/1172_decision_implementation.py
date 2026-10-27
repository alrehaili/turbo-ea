"""Decision actions and implementation verification (D-13, D-32, D-41; Batch 3.4).

* ``todos``: ``source_kind`` / ``source_id`` link a todo to the ADR or ARB review
  it implements (a **decision action**); ``completion_note``,
  ``evidence_refs``, ``completed_by`` and ``completed_at`` record how it was
  completed and on what evidence.
* ``decision_implementations``: one row per decision — implementation deadline
  (original and in force), submission and independent verification.
* ``governance_transitions``: instruments ``adr_impl`` / ``arb_impl`` for the
  implementation lifecycle, event kinds ``due_date_set`` / ``due_date_changed``
  and the ``due_date`` / ``previous_due_date`` they carry.

Everything new on existing tables is nullable with **no server default**: no
earlier todo becomes a decision action, and no deadline, completion or
verification is manufactured for the past. Downgrade refuses while any
decision action or implementation record exists, since dropping them would
erase recorded history.

[FORK]

Revision ID: 1172
Revises: 1171
Create Date: 2026-10-27
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "1172"
down_revision: Union[str, None] = "1171"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None

_OLD_INSTRUMENTS = "instrument IN ('adr', 'arb', 'exception')"
_NEW_INSTRUMENTS = "instrument IN ('adr', 'arb', 'exception', 'adr_impl', 'arb_impl')"
_OLD_EVENTS = "event_kind IS NULL OR event_kind IN ('expiry_changed')"
_NEW_EVENTS = (
    "event_kind IS NULL OR event_kind IN ('expiry_changed', 'due_date_set', 'due_date_changed')"
)


def upgrade() -> None:
    op.add_column("todos", sa.Column("source_kind", sa.String(8), nullable=True))
    op.add_column("todos", sa.Column("source_id", UUID(as_uuid=True), nullable=True))
    op.add_column("todos", sa.Column("completion_note", sa.Text(), nullable=True))
    op.add_column("todos", sa.Column("evidence_refs", JSONB(), nullable=True))
    op.add_column(
        "todos",
        sa.Column(
            "completed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("todos", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_todos_source", "todos", ["source_kind", "source_id"])

    op.create_table(
        "decision_implementations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("decision_kind", sa.String(8), nullable=False),
        sa.Column("decision_id", UUID(as_uuid=True), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("original_due_date", sa.Date(), nullable=True),
        sa.Column("due_date_basis", sa.String(24), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column(
            "submitted_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submission_note", sa.Text(), nullable=True),
        sa.Column(
            "verified_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attestation", JSONB(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "decision_kind IN ('adr', 'arb')", name="ck_decision_implementations_kind"
        ),
        sa.CheckConstraint(
            "status IN ('open', 'submitted', 'verified')",
            name="ck_decision_implementations_status",
        ),
        sa.UniqueConstraint(
            "decision_kind", "decision_id", name="uq_decision_implementations_decision"
        ),
    )

    op.add_column("governance_transitions", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column(
        "governance_transitions", sa.Column("previous_due_date", sa.Date(), nullable=True)
    )
    op.drop_constraint(
        "ck_governance_transitions_instrument", "governance_transitions", type_="check"
    )
    op.create_check_constraint(
        "ck_governance_transitions_instrument", "governance_transitions", _NEW_INSTRUMENTS
    )
    op.drop_constraint(
        "ck_governance_transitions_event_kind", "governance_transitions", type_="check"
    )
    op.create_check_constraint(
        "ck_governance_transitions_event_kind", "governance_transitions", _NEW_EVENTS
    )


def downgrade() -> None:
    bind = op.get_bind()
    in_use = bind.execute(
        sa.text(
            "SELECT (SELECT count(*) FROM todos WHERE source_kind IS NOT NULL)"
            " + (SELECT count(*) FROM decision_implementations)"
            " + (SELECT count(*) FROM governance_transitions"
            "    WHERE instrument IN ('adr_impl', 'arb_impl'))"
        )
    ).scalar()
    if in_use:
        raise RuntimeError(
            f"{in_use} decision action / implementation record(s) exist; "
            "downgrading would erase that history."
        )
    op.drop_constraint(
        "ck_governance_transitions_event_kind", "governance_transitions", type_="check"
    )
    op.create_check_constraint(
        "ck_governance_transitions_event_kind", "governance_transitions", _OLD_EVENTS
    )
    op.drop_constraint(
        "ck_governance_transitions_instrument", "governance_transitions", type_="check"
    )
    op.create_check_constraint(
        "ck_governance_transitions_instrument", "governance_transitions", _OLD_INSTRUMENTS
    )
    op.drop_column("governance_transitions", "previous_due_date")
    op.drop_column("governance_transitions", "due_date")
    op.drop_table("decision_implementations")
    op.drop_index("ix_todos_source", table_name="todos")
    for column in (
        "completed_at",
        "completed_by",
        "evidence_refs",
        "completion_note",
        "source_id",
        "source_kind",
    ):
        op.drop_column("todos", column)
