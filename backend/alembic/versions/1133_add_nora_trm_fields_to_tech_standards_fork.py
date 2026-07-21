"""Add NORA TRM metadata columns to ``tech_standards``.

NORA (Saudi National Overall Reference Architecture) TRM "Service Standard"
alignment — noraPlan.md WP1.3: issuing body, mandate level, review date,
specification URL, TRM code, and an optional link to a TechCategory card
(the TRM Service Area / Category tree).

[FORK FEATURE]

Revision ID: 1133
Revises: 1132
Create Date: 2026-07-02
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "1133"
down_revision: Union[str, None] = "1132"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "tech_standards", sa.Column("standard_body", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "tech_standards",
        sa.Column("mandate", sa.String(length=16), nullable=False, server_default="recommended"),
    )
    op.add_column("tech_standards", sa.Column("review_date", sa.Date(), nullable=True))
    op.add_column("tech_standards", sa.Column("spec_url", sa.String(length=500), nullable=True))
    op.add_column("tech_standards", sa.Column("trm_code", sa.String(length=50), nullable=True))
    op.add_column(
        "tech_standards",
        sa.Column(
            "tech_category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_tech_standards_tech_category_id", "tech_standards", ["tech_category_id"])


def downgrade() -> None:
    op.drop_index("ix_tech_standards_tech_category_id", table_name="tech_standards")
    op.drop_column("tech_standards", "tech_category_id")
    op.drop_column("tech_standards", "trm_code")
    op.drop_column("tech_standards", "spec_url")
    op.drop_column("tech_standards", "review_date")
    op.drop_column("tech_standards", "mandate")
    op.drop_column("tech_standards", "standard_body")
