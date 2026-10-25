"""The one rule for a KPI card's ``metricKey`` (decision D-26).

``metricKey`` links a KPI card to a registered executive calculation, so the
card's target, baseline, owner and direction stand beside the computed value
on the CEO overview. Every path that writes card attributes calls
:func:`validate_metric_key` — card create and update (REST, extensions, survey
apply), bulk create (the Excel importer), bulk update, restore and workspace
import — and a partial unique index (``uq_cards_kpi_metric_key``) backs the
uniqueness in the database. Three checks:

1. **Registered.** The value must name a calculation in
   ``executive.registry.METRICS``.
2. **Unique.** No other ACTIVE KPI card carries it.
3. **Authorized.** Setting, changing or clearing it changes what the CEO sees,
   so it needs ``admin.metamodel`` as well as the card edit right that brought
   the caller here. An extension can never change it. System paths with no
   user (workspace import) are already admin-gated and skip this check only.

``external_id`` is untouched: it stays with imports and integrations.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import KPI_CARD_TYPE, Card
from app.models.user import User
from app.services.executive.registry import is_registered
from app.services.permission_service import PermissionService

FIELD = "metricKey"
#: The permission that, on top of the card edit right, may change the linkage.
LINK_PERMISSION = "admin.metamodel"


def normalise(value: Any) -> str | None:
    """The key as stored: a trimmed string, or ``None`` for absent / empty."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def metric_key_of(attributes: dict | None) -> str | None:
    return normalise((attributes or {}).get(FIELD))


async def holder_of(
    db: AsyncSession, key: str, *, exclude: uuid.UUID | None = None
) -> uuid.UUID | None:
    """The ACTIVE KPI card already linked to ``key``, other than ``exclude``."""
    stmt = select(Card.id).where(
        Card.type == KPI_CARD_TYPE,
        Card.status == "ACTIVE",
        Card.attributes[FIELD].astext == key,
    )
    if exclude is not None:
        stmt = stmt.where(Card.id != exclude)
    return (await db.execute(stmt.limit(1))).scalar_one_or_none()


async def validate_metric_key(
    db: AsyncSession,
    *,
    card_type: str,
    new_attributes: dict | None,
    old_attributes: dict | None = None,
    card_id: uuid.UUID | None = None,
    user: User | None = None,
    ext_key: str | None = None,
    check_authority: bool = True,
) -> None:
    """Refuse an invalid, duplicate or unauthorized ``metricKey`` change.

    Only a *change* is judged: re-sending the stored value is always accepted,
    so an unrelated edit of a linked card never needs the extra authority.
    Writes the normalised value back into ``new_attributes`` (or drops an
    empty one), so the index and the readers always see the same form.
    """
    if card_type != KPI_CARD_TYPE or new_attributes is None:
        return
    new = metric_key_of(new_attributes)
    if new is None:
        new_attributes.pop(FIELD, None)
    else:
        new_attributes[FIELD] = new
    old = metric_key_of(old_attributes)
    if new == old:
        return
    if check_authority:
        if ext_key is not None:
            raise HTTPException(403, "An extension cannot change a KPI card's metric link")
        if user is not None and not await PermissionService.has_app_permission(
            db, user, LINK_PERMISSION
        ):
            raise HTTPException(
                403, "Changing a KPI card's metric link needs metamodel administration"
            )
    if new is None:
        return
    if not is_registered(new):
        raise HTTPException(422, f"'{new}' is not a registered KPI calculation")
    if await holder_of(db, new, exclude=card_id) is not None:
        raise HTTPException(409, f"Another active KPI card is already linked to '{new}'")


async def restore_conflict(db: AsyncSession, card: Card) -> str | None:
    """The metric key that would collide if ``card`` were restored, if any."""
    if card.type != KPI_CARD_TYPE:
        return None
    key = metric_key_of(card.attributes)
    if key is None:
        return None
    return key if await holder_of(db, key, exclude=card.id) is not None else None
