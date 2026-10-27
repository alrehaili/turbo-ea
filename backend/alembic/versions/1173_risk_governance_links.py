"""Explicit risk ↔ EA governance-record links (D-42; Batch 3.5).

``risk_governance_links``: a risk linked to an ADR, an ARB review or a
technology-standard exception. A risk is architecture-related only through
such a link; nothing is created for existing risks — no risk is classified
by its category, source or wording.

Additive; downgrade refuses while links exist, since dropping them would erase
recorded relationships.

[FORK]

Revision ID: 1173
Revises: 1172
Create Date: 2026-10-27
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "1173"
down_revision: Union[str, None] = "1172"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "risk_governance_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "risk_id",
            UUID(as_uuid=True),
            sa.ForeignKey("risks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("instrument", sa.String(16), nullable=False),
        sa.Column("record_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "instrument IN ('adr', 'arb', 'exception')", name="ck_risk_governance_links_instrument"
        ),
        sa.UniqueConstraint(
            "risk_id", "instrument", "record_id", name="uq_risk_governance_links_link"
        ),
    )
    op.create_index(
        "ix_risk_governance_links_record", "risk_governance_links", ["instrument", "record_id"]
    )
    op.create_index("ix_risk_governance_links_risk", "risk_governance_links", ["risk_id"])


def downgrade() -> None:
    bind = op.get_bind()
    in_use = bind.execute(sa.text("SELECT count(*) FROM risk_governance_links")).scalar()
    if in_use:
        raise RuntimeError(f"{in_use} risk governance link(s) exist; downgrading would erase them.")
    op.drop_index("ix_risk_governance_links_risk", table_name="risk_governance_links")
    op.drop_index("ix_risk_governance_links_record", table_name="risk_governance_links")
    op.drop_table("risk_governance_links")
