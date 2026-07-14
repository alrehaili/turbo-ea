"""Add ADM Governance Workspace tables.

Three new tables backing the ADM Governance Workspace feature — an execution
and governance layer over a SoAW (or an Initiative card).

* ``adm_workspaces``       — one row per governed architecture engagement
* ``adm_phases``           — 10 rows per workspace (TOGAF ADM + Requirements
                              Management), seeded from a code template
* ``adm_phase_artefacts``  — links to existing artefacts (SoAW, ADR, diagram,
                              risk, card, url, …) — no data duplication

All additive. Downgrade drops the three new tables cleanly. Existing SoAWs
are unaffected; the SoAW model gains no new columns.

[FORK FEATURE]

Revision ID: 132
Revises: 131
Create Date: 2026-07-04
"""

from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "140"
down_revision: Union[str, None] = "139"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "adm_workspaces",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column(
            "soaw_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("statement_of_architecture_works.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "initiative_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_completion", sa.Date(), nullable=True),
        sa.Column(
            "owner_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "soaw_id IS NOT NULL OR initiative_id IS NOT NULL",
            name="ck_adm_workspaces_has_anchor",
        ),
    )
    op.create_index("ix_adm_workspaces_soaw_id", "adm_workspaces", ["soaw_id"])
    op.create_index("ix_adm_workspaces_initiative_id", "adm_workspaces", ["initiative_id"])
    op.create_index("ix_adm_workspaces_status", "adm_workspaces", ["status"])
    # v1 constraint: at most one ADM workspace per SoAW. Enforced as a partial
    # unique index so multiple workspaces without a SoAW remain allowed.
    op.create_index(
        "uq_adm_workspaces_soaw_single",
        "adm_workspaces",
        ["soaw_id"],
        unique=True,
        postgresql_where=sa.text("soaw_id IS NOT NULL"),
    )

    op.create_table(
        "adm_phases",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("adm_workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phase_key", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_continuous", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="not_started"),
        sa.Column(
            "owner_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("gate_notes", sa.Text(), nullable=True),
        sa.Column(
            "approved_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_comment", sa.Text(), nullable=True),
        sa.Column("approval_override_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("workspace_id", "phase_key", name="uq_adm_phases_workspace_phase"),
    )
    op.create_index("ix_adm_phases_workspace_sort", "adm_phases", ["workspace_id", "sort_order"])
    op.create_index("ix_adm_phases_status", "adm_phases", ["status"])
    op.create_index("ix_adm_phases_owner_id", "adm_phases", ["owner_id"])

    op.create_table(
        "adm_phase_artefacts",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "phase_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("adm_phases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("ref_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ref_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_waived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("waived_reason", sa.Text(), nullable=True),
        sa.Column(
            "waived_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("waived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "linked_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_adm_phase_artefacts_phase_id", "adm_phase_artefacts", ["phase_id"])
    op.create_index("ix_adm_phase_artefacts_kind_ref", "adm_phase_artefacts", ["kind", "ref_id"])


def downgrade() -> None:
    op.drop_index("ix_adm_phase_artefacts_kind_ref", table_name="adm_phase_artefacts")
    op.drop_index("ix_adm_phase_artefacts_phase_id", table_name="adm_phase_artefacts")
    op.drop_table("adm_phase_artefacts")
    op.drop_index("ix_adm_phases_owner_id", table_name="adm_phases")
    op.drop_index("ix_adm_phases_status", table_name="adm_phases")
    op.drop_index("ix_adm_phases_workspace_sort", table_name="adm_phases")
    op.drop_table("adm_phases")
    op.drop_index("uq_adm_workspaces_soaw_single", table_name="adm_workspaces")
    op.drop_index("ix_adm_workspaces_status", table_name="adm_workspaces")
    op.drop_index("ix_adm_workspaces_initiative_id", table_name="adm_workspaces")
    op.drop_index("ix_adm_workspaces_soaw_id", table_name="adm_workspaces")
    op.drop_table("adm_workspaces")
