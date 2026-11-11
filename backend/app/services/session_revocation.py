"""Server-side revocation of session tokens.

Two mechanisms, because they answer different questions:

- **Every session of a user** — ``users.session_generation``. Bumped whenever
  the account's password is set or replaced; every token carries the
  generation it was issued under (``gen`` claim) and is refused once the
  counter has moved on. A counter, not a timestamp: JWT ``iat`` is whole
  seconds, so a time cutoff cannot refuse a token issued earlier in the same
  second as the reset without also refusing the one issued just after it.
- **One session** — a ``revoked_sessions`` row keyed by the token's ``sid``
  claim, written at logout. ``sid`` and ``gen`` are carried through
  ``/auth/refresh`` and impersonation, so a copy of the token that was
  refreshed elsewhere is the same session and dies with it.

A token without ``sid`` or ``gen`` was issued before this scheme existed and
can be revoked by neither mechanism, so it is refused outright: such a user
signs in once more after the upgrade.

Every place that turns a token into a user must ask ``token_is_revoked``:
``get_current_user`` (``api/deps.py``) and the SSE stream (``api/v1/events.py``,
at open and again periodically while it runs). None of these helpers commit —
the caller owns the transaction.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.revoked_session import RevokedSession
from app.models.user import User


def token_generation(payload: dict) -> int | None:
    """The ``gen`` claim, or None when the token has none (or a non-integer)."""
    gen = payload.get("gen")
    # ``bool`` is an ``int``; a token claiming ``gen: true`` is not a generation.
    if isinstance(gen, bool) or not isinstance(gen, int):
        return None
    return gen


def is_stale_generation(user: User, payload: dict) -> bool:
    """True when the token was issued before the user's sessions were last ended."""
    gen = token_generation(payload)
    return gen is None or gen != (user.session_generation or 0)


async def token_is_revoked(db: AsyncSession, user: User, payload: dict) -> bool:
    """Whether this token's session was revoked, for the user or on its own."""
    if is_stale_generation(user, payload):
        return True
    sid = payload.get("sid")
    if not isinstance(sid, str) or not sid:
        # Pre-upgrade token: logout could never revoke it, so refuse it now.
        return True
    hit = await db.execute(select(RevokedSession.sid).where(RevokedSession.sid == sid))
    return hit.first() is not None


def revoke_all_sessions(user: User) -> None:
    """Refuse every token issued to ``user`` so far. Call when a password is set.

    Tokens minted afterwards must pass ``generation=user.session_generation``.
    """
    user.session_generation = (user.session_generation or 0) + 1
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
