"""Merge the fork's 1162 head with upstream's 156 head.

Fork migration 1162 (widen ``scenario_changes.op``) was written on top of 154.
The upstream v2.165.0..v2.178.0 merge then brought 155 and 156, also on top of
154, which left two heads and stopped startup (``get_current_head`` refuses a
branched script directory). This revision joins them. It changes no schema: the
two branches touch unrelated tables, so they apply in either order.

A merge revision rather than re-parenting 1162 onto 156: a database that has
already applied 1162 keeps a valid history either way.

[FORK FIX]

Revision ID: 1163
Revises: 1162, 156
Create Date: 2026-10-24
"""

from typing import Sequence, Union

revision: str = "1163"
down_revision: Union[str, Sequence[str], None] = ("1162", "156")
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
