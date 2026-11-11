"""Server-side revocation of session tokens.

Two mechanisms, because they answer different questions:

- **Every session of a user** — ``users.sessions_valid_after``. Set whenever
  the account's password is set or replaced; a token issued before that moment
  is refused. This is what makes a password reset actually evict whoever held
  a stolen token.
- **One session** — a ``revoked_sessions`` row keyed by the token's ``sid``
  claim, written at logout. ``sid`` is carried through ``/auth/refresh`` and
  impersonation, so a copy of the token that was refreshed elsewhere is the
  same session and dies with it.

Every place that turns a token into a user must ask ``token_is_revoked``:
``get_current_user`` (``api/deps.py``) and the SSE stream (``api/v1/events.py``).
None of these helpers commit — the caller owns the transaction.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.revoked_session import RevokedSession
from app.models.user import User


def _issued_at(payload: dict) -> int | None:
    iat = payload.get("iat")
    # ``bool`` is an ``int``; a token claiming ``iat: true`` is not a timestamp.
    if isinstance(iat, bool) or not isinstance(iat, (int, float)):
        return None
    return int(iat)


def issued_before_cutoff(user: User, payload: dict) -> bool:
    """True when the token predates the user's ``sessions_valid_after``."""
    cutoff = user.sessions_valid_after
    if cutoff is None:
        return False
    iat = _issued_at(payload)
    if iat is None:
        return True
    # ``iat`` is whole seconds, so compare against the cutoff's own second:
    # the token minted right after a password change must stay valid.
    return iat < int(cutoff.timestamp())


async def token_is_revoked(db: AsyncSession, user: User, payload: dict) -> bool:
    """Whether this token's session was revoked, for the user or on its own."""
    if issued_before_cutoff(user, payload):
        return True
    sid = payload.get("sid")
    if not isinstance(sid, str) or not sid:
        # Issued before sessions carried an id; only the cutoff can revoke it.
        return False
    hit = await db.execute(select(RevokedSession.sid).where(RevokedSession.sid == sid))
    return hit.first() is not None


def revoke_all_sessions(user: User) -> None:
    """Refuse every token issued to ``user`` so far. Call when a password is set."""
    user.sessions_valid_after = datetime.now(timezone.utc)


async def revoke_session(db: AsyncSession, payload: dict | None) -> None:
    """Revoke the one session ``payload`` belongs to (logout)."""
    now = datetime.now(timezone.utc)
    # Rows past their date revoke nothing any more; clear them while here.
    await db.execute(delete(RevokedSession).where(RevokedSession.expires_at < now))
    sid = (payload or {}).get("sid")
    if not isinstance(sid, str) or not sid:
        return
    await db.execute(
        pg_insert(RevokedSession)
        .values(
            sid=sid[:64],
            expires_at=now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        .on_conflict_do_nothing(index_elements=[RevokedSession.sid])
    )
