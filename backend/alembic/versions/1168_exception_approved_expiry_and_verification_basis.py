"""Original approved expiry on the approval transition; remediation verification basis.

Batch 3.2 corrections (2026-10-26, DECISION_LOG I-29..I-34):

* ``governance_transitions.approved_expiry_date``: the exception's expiry date
  as it stood when the approval was recorded. GOV-04 measures on-time
  remediation against this **original approved expiry**, never against a date
  edited afterwards (I-31).
* ``tech_standard_exceptions.remediation_verification_basis``: how a verified
  remediation was confirmed — ``rule_check`` (the standards scan no longer finds
  the card using the standard) or ``attested`` (not assessable by the scan; the
  verifier recorded what was checked). I-32.

Both nullable with **no server default**: earlier approvals and verifications
carry none, so nothing is invented for the past. Additive; downgrade drops them.

[FORK]

Revision ID: 1168
Revises: 1167
Create Date: 2026-10-26
"""

from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "1168"
down_revision: Union[str, None] = "1167"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "governance_transitions",
        sa.Column("approved_expiry_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "tech_standard_exceptions",
        sa.Column("remediation_verification_basis", sa.String(16), nullable=True),
    )
    op.create_check_constraint(
        "ck_tech_standard_exceptions_verification_basis",
        "tech_standard_exceptions",
        "remediation_verification_basis IS NULL "
        "OR remediation_verification_basis IN ('rule_check', 'attested')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_tech_standard_exceptions_verification_basis",
        "tech_standard_exceptions",
        type_="check",
    )
    op.drop_column("tech_standard_exceptions", "remediation_verification_basis")
    op.drop_column("governance_transitions", "approved_expiry_date")
