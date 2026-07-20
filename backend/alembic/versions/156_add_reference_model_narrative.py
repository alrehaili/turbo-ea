"""Add narrative JSONB to reference_models (poster content — RMPlan Phase 3).

Revision ID: 156
Revises: 155

Editable poster panels (mission / vision / objectives / stakeholders /
principles / KPIs / value …) rendered around the capability map. Generic
JSONB so panels are data, not per-model-type columns. [FORK FEATURE]
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "156"
down_revision = "155"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reference_models",
        sa.Column("narrative", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reference_models", "narrative")
