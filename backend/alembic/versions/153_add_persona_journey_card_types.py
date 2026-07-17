"""Add Persona & Journey card types to seed.

Revision ID: 153
Revises: 152

This migration is documentation-only; the actual Persona & Journey card
types are inserted by seed_metamodel() in seed.py, which checks for
missing keys before adding.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "153"
down_revision = "152"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Persona & Journey card types are seeded via seed.py on startup.

    This migration is documentation-only; the actual types are inserted
    by seed_metamodel() which checks for missing keys before adding.
    """
    pass


def downgrade() -> None:
    """Downgrade is not supported for seed-based changes."""
    pass
