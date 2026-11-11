"""Sessions signed out before their token expired.

A session token is a stateless JWT, so signing out can only delete the
browser's cookie; a copy of the token would keep working, and could be
refreshed for ever. Each token carries a session id (``sid``) that survives
``/auth/refresh``; logging out records it here and ``get_current_user``
refuses it. A revoked session can no longer be refreshed, so its last token
dies within one token lifetime — ``expires_at`` is when the row can go.

Instance-local session state: never part of a workspace transfer.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RevokedSession(Base):
    __tablename__ = "revoked_sessions"

    sid: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
