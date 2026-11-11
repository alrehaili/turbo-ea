"""Session generation counter.

``users.session_generation`` replaces the ``sessions_valid_after`` timestamp
as the check that ends every session of an account: each token carries the
generation it was issued under (``gen`` claim) and is refused once the user's
counter has moved past it. A timestamp cutoff could not tell a token issued
earlier in the same second as a password reset from one issued just after it,
because JWT ``iat`` is whole seconds. ``sessions_valid_after`` stays as the
record of when sessions were last ended.

Revision ID: 167
Revises: 166
Create Date: 2026-11-11
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "167"
down_revision: Union[str, None] = "166"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("session_generation", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "session_generation")
