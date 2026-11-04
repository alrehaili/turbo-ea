"""Merge the fork's history with upstream dashboards, role widening and licence encryption.

Both branches descend from upstream revision 158 (joined in 1176). Upstream's
159 re-widens ``users.role`` to 50, which the fork already did in 1144 — on
PostgreSQL that alter is a no-op. This joins the histories without changing
the schema or existing revisions.

Revision ID: 1177
Revises: 1176, 162
"""

from collections.abc import Sequence

revision: str = "1177"
down_revision: str | Sequence[str] | None = ("1176", "162")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
