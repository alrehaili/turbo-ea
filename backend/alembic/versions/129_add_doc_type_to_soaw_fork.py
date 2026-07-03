"""Add ``doc_type`` to ``statement_of_architecture_works``.

NORA governed document artifacts (noraPlan.md WP3.2): the SoAW machinery
(sections, revision chain, signatories, DOCX export) now also carries the
NORA Stage 1/2/3/9 documents — EA Project Strategy, EA Project Plan,
Environment Analysis / SWOT, EA Usage Plan, EA Management Plan —
discriminated by ``doc_type`` (default ``soaw``).

[FORK FEATURE]

Revision ID: 129
Revises: 128
Create Date: 2026-07-02
"""

from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "129"
down_revision: Union[str, None] = "128"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "statement_of_architecture_works",
        sa.Column("doc_type", sa.String(length=32), nullable=False, server_default="soaw"),
    )
    op.create_index("ix_soaw_doc_type", "statement_of_architecture_works", ["doc_type"])


def downgrade() -> None:
    op.drop_index("ix_soaw_doc_type", table_name="statement_of_architecture_works")
    op.drop_column("statement_of_architecture_works", "doc_type")
