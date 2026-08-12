"""Pre-deploy safety check: count active cards on the types the NORA profile
hides (noraPlanMeta.md Phase 3). Run on the target instance BEFORE restarting
into the new build, so you know whether any existing data will disappear from
the inventory/pickers when the exact-NORA profile re-applies.

Usage (from the backend/ dir, with the app's DB env vars set):
    python ../scripts/nora_hidden_types_check.py
"""

import asyncio

from sqlalchemy import func, select

from app.database import async_session
from app.models.card import Card
from app.services.nora_profile import NORA_HIDDEN_TYPE_KEYS


async def main() -> None:
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Card.type, func.count(Card.id))
                .where(Card.type.in_(NORA_HIDDEN_TYPE_KEYS), Card.status != "ARCHIVED")
                .group_by(Card.type)
            )
        ).all()
    counts = {t: n for t, n in rows}
    total = sum(counts.values())
    print("Types the NORA profile will hide (active cards):\n")
    for key in NORA_HIDDEN_TYPE_KEYS:
        n = counts.get(key, 0)
        flag = "  <-- HAS DATA" if n else ""
        print(f"  {key:<28} {n:>6}{flag}")
    print(f"\n  {'TOTAL':<28} {total:>6}")
    if total:
        print(
            "\n⚠  These cards will be hidden from inventory/pickers after the profile\n"
            "   re-applies. Nothing is deleted — un-hide any type from the metamodel\n"
            "   admin, or switch to the TOGAF profile to restore them all."
        )
    else:
        print("\n✓  No active cards on any hidden type — safe to deploy.")


if __name__ == "__main__":
    asyncio.run(main())
