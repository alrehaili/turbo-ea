"""Repair timestamp defaults omitted by fork migrations 1154/1155/1157/1159.

Only missing defaults are installed; existing values and custom defaults are
preserved. Historical migrations remain unchanged. No workspace-transfer
columns or bundle format change. Downgrade retains this additive repair so it
does not reintroduce broken inserts.

Revision ID: 1165
Revises: 1164
"""

import sqlalchemy as sa

from alembic import op

revision = "1165"
down_revision = "1164"
branch_labels = None
depends_on = None

REPAIRED_MIGRATIONS = {
    "1154_add_viewpoint_definitions_table.py": "viewpoint_definitions",
    "1155_add_reference_model_mappings.py": "reference_model_mappings",
    "1157_add_reference_model_versions.py": "reference_model_versions",
    "1159_add_reference_model_relationships.py": "reference_model_relationships",
}
TIMESTAMP_COLUMNS = ("created_at", "updated_at")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in REPAIRED_MIGRATIONS.values():
        if not inspector.has_table(table):
            continue
        for column in inspector.get_columns(table):
            if column["name"] in TIMESTAMP_COLUMNS and not column.get("default"):
                op.alter_column(
                    table,
                    column["name"],
                    server_default=sa.func.now(),
                    existing_type=column["type"],
                    existing_nullable=column["nullable"],
                )


def downgrade() -> None:
    # Retain the repair, as migration 151 does; no rows or columns were added.
    pass
