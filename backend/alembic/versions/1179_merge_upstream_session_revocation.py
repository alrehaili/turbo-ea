"""Merge the fork's history with upstream session revocation and generation.

Both branches descend from upstream revision 165: the fork's 1178 (seven
architecture layers) and upstream's 166 (session revocation ledger) -> 167
(``users.session_generation``). With two heads the backend refused to start
("multiple heads"). This joins the histories without changing the schema; a
database at 1178 runs 166 and 167 on its way here, one at 167 runs 1178.

Revision ID: 1179
Revises: 1178, 167
"""

from collections.abc import Sequence

revision: str = "1179"
down_revision: str | Sequence[str] | None = ("1178", "167")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
