"""Tell open SSE streams to re-check their session the moment it changes.

An open ``/events/stream`` re-validates its token on a timer
(``STREAM_REVALIDATE_SECONDS``). Without more, a stream would keep delivering
events for up to that long after its session was revoked. This module closes
that window: every committed change that can end or narrow a session marks the
affected streams *stale*, and a stale stream re-checks before it sends the
next message (``api/v1/events.py``).

What marks a stream, detected on the ORM session so no write path can forget:

- a ``users`` row whose ``is_active``, ``role``, ``session_generation``,
  ``access_expires_at`` or ``password_hash`` changed, or that was deleted —
  that user's streams;
- any change to a ``roles`` row, or a bulk ``UPDATE`` / ``DELETE`` on
  ``users`` or ``roles`` — every stream (rare, admin-only operations);
- a logout, which names its ``sid`` through ``note_revoked_sid`` because the
  revocation ledger is written with a core ``INSERT`` — that session's streams.

Marks are collected per transaction and applied only when the outermost
transaction commits — not at a SAVEPOINT release: a stream that re-checked
before that commit would still read the old state. A rolled-back transaction
marks nothing; a rolled-back SAVEPOINT keeps the marks collected around it.

The mark is only a hint to re-check; the check itself (``token_is_revoked``
and friends) stays the authority, so marking too much costs one short query
and never grants anything.

The registry is per process, like the event bus it sits next to.
"""

from __future__ import annotations

import weakref
from dataclasses import dataclass, field

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.user import User

_USER_FIELDS = ("is_active", "role", "session_generation", "access_expires_at", "password_hash")
_BULK_TABLES = frozenset({"users", "roles"})
_PENDING_KEY = "stream_revalidation_pending"
# Execution option naming the one user a bulk ``UPDATE`` on ``users`` touches
# (``revoke_all_sessions``), so it marks that user's streams, not everyone's.
USER_OPTION = "stream_revalidation_user"


@dataclass(eq=False)
class StreamWatch:
    """One open stream. ``stale`` is set when its session may have changed."""

    user_id: str
    sid: str | None
    stale: bool = False


@dataclass
class _Pending:
    user_ids: set[str] = field(default_factory=set)
    sids: set[str] = field(default_factory=set)
    everyone: bool = False


# Weak, so a stream whose response was dropped without running its ``finally``
# cannot leak here.
_watches: weakref.WeakSet[StreamWatch] = weakref.WeakSet()


def watch(user_id: str, sid: str | None) -> StreamWatch:
    """Register an open stream. The caller keeps the returned object alive."""
    w = StreamWatch(user_id=user_id, sid=sid)
    _watches.add(w)
    return w


def unwatch(w: StreamWatch) -> None:
    _watches.discard(w)


def mark_stale(
    *,
    user_ids: set[str] | frozenset[str] = frozenset(),
    sids: set[str] | frozenset[str] = frozenset(),
    everyone: bool = False,
) -> None:
    """Mark matching open streams stale. Synchronous: safe from a session event."""
    for w in list(_watches):
        if everyone or w.user_id in user_ids or (w.sid is not None and w.sid in sids):
            w.stale = True


def _pending(session: Session) -> _Pending:
    pending = session.info.get(_PENDING_KEY)
    if pending is None:
        pending = session.info[_PENDING_KEY] = _Pending()
    return pending


def note_revoked_sid(session: Session, sid: str) -> None:
    """Mark ``sid``'s streams stale once ``session``'s transaction commits."""
    _pending(session).sids.add(sid)


def _user_changed(user: User) -> bool:
    state = inspect(user)
    return any(state.attrs[name].history.has_changes() for name in _USER_FIELDS)


@event.listens_for(Session, "after_flush")
def _collect_flushed(session: Session, flush_context) -> None:
    for obj in session.deleted:
        if isinstance(obj, User):
            _pending(session).user_ids.add(str(obj.id))
        elif isinstance(obj, Role):
            _pending(session).everyone = True
    for obj in session.dirty:
        if isinstance(obj, User) and _user_changed(obj):
            _pending(session).user_ids.add(str(obj.id))
        elif isinstance(obj, Role) and session.is_modified(obj):
            _pending(session).everyone = True
    if any(isinstance(obj, Role) for obj in session.new):
        _pending(session).everyone = True


@event.listens_for(Session, "do_orm_execute")
def _collect_bulk(orm_execute_state) -> None:
    if not (orm_execute_state.is_update or orm_execute_state.is_delete):
        return
    table = getattr(orm_execute_state.statement, "table", None)
    if getattr(table, "name", None) not in _BULK_TABLES:
        return
    named_user = orm_execute_state.execution_options.get(USER_OPTION)
    if named_user:
        _pending(orm_execute_state.session).user_ids.add(str(named_user))
    else:
        _pending(orm_execute_state.session).everyone = True


@event.listens_for(Session, "after_commit")
def _apply_on_commit(session: Session) -> None:
    # SQLAlchemy fires this for a SAVEPOINT release too, while the outermost
    # transaction is still open and its writes are invisible to every other
    # session. Marking then would let a stream re-check against the old state
    # and clear its mark before the real commit; keep the marks for that one.
    root = session.get_transaction()
    if root is not None and root.is_active:
        return
    pending = session.info.pop(_PENDING_KEY, None)
    if pending is not None:
        mark_stale(user_ids=pending.user_ids, sids=pending.sids, everyone=pending.everyone)


@event.listens_for(Session, "after_soft_rollback")
def _discard_on_rollback(session: Session, previous_transaction) -> None:
    # Only the outermost transaction: a SAVEPOINT rolling back must not drop
    # marks collected earlier in the transaction that may still commit.
    if previous_transaction.parent is None:
        session.info.pop(_PENDING_KEY, None)
