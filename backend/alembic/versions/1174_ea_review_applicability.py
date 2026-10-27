"""EA governance applicability assessments (D-37; Batch 3.6).

``ea_review_applicability_assessments``: append-only decisions that an
Initiative does or does not require EA governance review, with the criteria
applied, a justification, the actor and the time. Nothing is created for
existing initiatives: every initiative stays Undetermined until assessed.

Additive; downgrade refuses while assessments exist, since dropping them would
erase recorded decisions.

[FORK]

Revision ID: 1174
Revises: 1173
Create Date: 2026-10-27
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "1174"
down_revision: Union[str, None] = "1173"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "ea_review_applicability_assessments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "card_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("criteria_reference", sa.String(300), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column(
            "decided_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "decided_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "decision IN ('required', 'not_required')",
            name="ck_ea_review_applicability_decision",
        ),
    )
    op.create_index(
        "ix_ea_review_applicability_card",
        "ea_review_applicability_assessments",
        ["card_id", "decided_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    in_use = bind.execute(
        sa.text("SELECT count(*) FROM ea_review_applicability_assessments")
    ).scalar()
    if in_use:
        raise RuntimeError(
            f"{in_use} applicability assessment(s) exist; downgrading would erase them."
        )
    op.drop_index(
        "ix_ea_review_applicability_card", table_name="ea_review_applicability_assessments"
    )
    op.drop_table("ea_review_applicability_assessments")
