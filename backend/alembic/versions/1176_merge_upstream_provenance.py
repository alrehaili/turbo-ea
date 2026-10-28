"""Merge fork benefits history with upstream provenance and Arabic fixes.

Both branches descend from upstream revision 156 and change independent data.
This joins their histories without changing the schema or existing revisions.

Revision ID: 1176
Revises: 1175, 158
"""

from collections.abc import Sequence

revision: str = "1176"
down_revision: str | Sequence[str] | None = ("1175", "158")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
