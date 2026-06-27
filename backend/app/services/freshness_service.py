"""Repository Freshness aggregation (Wave 2 #4).

Answers "how trustworthy is the repository?" — who owns each area, when it was
last confirmed, where the data came from, how confident we are, and what is
stale or has open data-quality gaps.

Freshness is derived from three card columns (``last_confirmed_at``,
``source_system``, ``confidence`` — added in migration 113) plus the existing
``data_quality`` score and stakeholder/owner assignments. A card is **stale**
when it has never been confirmed or was last confirmed more than
``stale_days`` ago.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_type import CardType
from app.models.stakeholder import Stakeholder
from app.models.user import User

# data_quality below this (0-100 scale) counts as an open DQ issue.
DQ_ISSUE_THRESHOLD = 50.0


def _is_stale(card: Card, cutoff: datetime) -> bool:
    if card.last_confirmed_at is None:
        return True
    confirmed = card.last_confirmed_at
    if confirmed.tzinfo is None:
        confirmed = confirmed.replace(tzinfo=timezone.utc)
    return confirmed < cutoff


async def gather_freshness(db: AsyncSession, *, stale_days: int = 90) -> dict:
    """Compute the repository-freshness rollup + a stale-record worklist."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=stale_days)

    # Active, non-hidden cards only.
    ct_res = await db.execute(select(CardType.key, CardType.label, CardType.is_hidden))
    type_label: dict[str, str] = {}
    hidden: set[str] = set()
    for key, label, is_hidden in ct_res.all():
        type_label[key] = label
        if is_hidden:
            hidden.add(key)

    cards_res = await db.execute(select(Card).where(Card.status == "ACTIVE"))
    cards = [c for c in cards_res.scalars().all() if c.type not in hidden]

    # Owner display names via the stakeholder table (first stakeholder per card).
    owner_by_card: dict[uuid.UUID, uuid.UUID] = {}
    card_ids = [c.id for c in cards]
    if card_ids:
        sres = await db.execute(
            select(Stakeholder.card_id, Stakeholder.user_id).where(
                Stakeholder.card_id.in_(card_ids)
            )
        )
        for cid, uid in sres.all():
            owner_by_card.setdefault(cid, uid)  # first wins; stable enough for rollup
    user_ids = {u for u in owner_by_card.values() if u}
    name_by_user: dict[uuid.UUID, str] = {}
    if user_ids:
        ures = await db.execute(select(User.id, User.display_name).where(User.id.in_(user_ids)))
        name_by_user = {uid: name for uid, name in ures.all()}

    total = len(cards)
    stale_count = 0
    confirmed_count = 0
    dq_issues = 0
    by_source: dict[str, int] = {}
    by_confidence: dict[str, int] = {}
    by_type: dict[str, dict] = {}
    by_owner: dict[str, dict] = {}
    stale_rows: list[dict] = []

    for c in cards:
        stale = _is_stale(c, cutoff)
        if stale:
            stale_count += 1
        else:
            confirmed_count += 1
        if (c.data_quality or 0) < DQ_ISSUE_THRESHOLD:
            dq_issues += 1

        source = c.source_system or "—"
        by_source[source] = by_source.get(source, 0) + 1
        conf = c.confidence or "unset"
        by_confidence[conf] = by_confidence.get(conf, 0) + 1

        tl = type_label.get(c.type, c.type)
        tbucket = by_type.setdefault(tl, {"type": tl, "total": 0, "stale": 0})
        tbucket["total"] += 1
        if stale:
            tbucket["stale"] += 1

        owner_uid = owner_by_card.get(c.id)
        owner_name = name_by_user.get(owner_uid) if owner_uid else None
        owner_key = owner_name or "Unassigned"
        obucket = by_owner.setdefault(owner_key, {"owner": owner_key, "total": 0, "stale": 0})
        obucket["total"] += 1
        if stale:
            obucket["stale"] += 1

        if stale:
            stale_rows.append(
                {
                    "id": str(c.id),
                    "name": c.name,
                    "type": tl,
                    "owner": owner_name,
                    "last_confirmed_at": (
                        c.last_confirmed_at.isoformat() if c.last_confirmed_at else None
                    ),
                    "source_system": c.source_system,
                    "confidence": c.confidence,
                    "data_quality": c.data_quality,
                }
            )

    # Worst (oldest / never-confirmed) first; never-confirmed sort to the top.
    stale_rows.sort(key=lambda r: (r["last_confirmed_at"] or "", r["name"].lower()))

    return {
        "stale_days": stale_days,
        "summary": {
            "total": total,
            "confirmed": confirmed_count,
            "stale": stale_count,
            "stale_pct": round(100 * stale_count / total, 1) if total else 0.0,
            "dq_issues": dq_issues,
        },
        "by_source": [
            {"source": k, "count": v} for k, v in sorted(by_source.items(), key=lambda kv: -kv[1])
        ],
        "by_confidence": by_confidence,
        "by_type": sorted(by_type.values(), key=lambda r: -r["stale"]),
        "by_owner": sorted(by_owner.values(), key=lambda r: -r["stale"]),
        "stale_records": stale_rows,
    }
