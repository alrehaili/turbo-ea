"""Add domain / adoption / source traceability to the EA governance catalog.

[FORK FEATURE] — Backs the authority-level Saudi Government EA catalog:

* ``ea_principles`` gains ``domain`` and ``source_ids`` (authoritative-source
  code list, e.g. ["SA-01", "SA-02"]).
* ``standards`` gains ``domain``, ``adoption`` (proposed adoption status, e.g.
  "Mandatory", "Conditional mandatory", "Preferred"), and ``source_ids``.
* New ``authoritative_sources`` register table — the 55 Saudi + international
  sources (DGA, NCA, SDAIA/NDMO, PDPL, ISO, NIST, IETF, W3C, …) that principles
  and standards trace back to, each with an authority, classification, title,
  URL and note.

Revision ID: 150
Revises: 149
Create Date: 2026-07-15
"""

from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "150"
down_revision: Union[str, None] = "149"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # ── ea_principles ────────────────────────────────────────────────────
    op.add_column("ea_principles", sa.Column("domain", sa.String(length=64), nullable=True))
    op.add_column(
        "ea_principles",
        sa.Column(
            "source_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )

    # ── standards ────────────────────────────────────────────────────────
    op.add_column("standards", sa.Column("domain", sa.String(length=64), nullable=True))
    op.add_column("standards", sa.Column("adoption", sa.String(length=64), nullable=True))
    op.add_column(
        "standards",
        sa.Column(
            "source_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )

    # ── authoritative_sources register ───────────────────────────────────
    op.create_table(
        "authoritative_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("authority", sa.String(length=128), nullable=True),
        sa.Column("classification", sa.String(length=256), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_authoritative_sources_code"),
    )


def downgrade() -> None:
    op.drop_table("authoritative_sources")
    op.drop_column("standards", "source_ids")
    op.drop_column("standards", "adoption")
    op.drop_column("standards", "domain")
    op.drop_column("ea_principles", "source_ids")
    op.drop_column("ea_principles", "domain")
