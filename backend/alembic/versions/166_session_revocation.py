"""Server-side session revocation.

``users.sessions_valid_after`` refuses every token issued before a password
was set or replaced; ``revoked_sessions`` holds the session ids signed out at
logout until their last token has expired.

Revision ID: 166
Revises: 165
Create Date: 2026-11-11
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "166"
down_revision: Union[str, None] = "165"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("sessions_valid_after", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "revoked_sessions",
        sa.Column("sid", sa.String(64), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_revoked_sessions_expires_at", "revoked_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_revoked_sessions_expires_at", table_name="revoked_sessions")
    op.drop_table("revoked_sessions")
    op.drop_column("users", "sessions_valid_after")
