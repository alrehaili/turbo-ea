"""Remediation evidence references on standard exceptions (DECISION_LOG I-32).

Approved with changes 2026-10-26: where the standards scan cannot assess a
remediation, a verification note alone is not enough — the submission must
carry verifiable supporting evidence. The evidence reuses the existing card
evidence mechanisms: documents (``documents``) and file attachments
(``file_attachments``) on the exception's card. ``remediation_evidence_refs``
holds the references chosen at submission as
``[{"kind": "document" | "attachment", "id": "<uuid>", "name": "<name>"}]``.

Nullable with **no server default**: earlier submissions carry no references,
and none are invented. Additive; downgrade drops the column.

[FORK]

Revision ID: 1169
Revises: 1168
Create Date: 2026-10-26
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "1169"
down_revision: Union[str, None] = "1168"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "tech_standard_exceptions",
        sa.Column("remediation_evidence_refs", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tech_standard_exceptions", "remediation_evidence_refs")
