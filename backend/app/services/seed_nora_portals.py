"""NORA web-portals seed — one public catalogue portal per visible card type,
plus a Strategic House hub portal.

Data-driven: the catalogue portals are generated from whatever visible
(non-hidden) card types exist at seed time, so the set stays in sync with the
metamodel (22 built-in types today → 22 catalogue portals, + 1 Strategic House
hub = 23). Idempotent per slug, so a re-run only tops up portals that are
missing (e.g. after a new card type is added).

[FORK FEATURE] — NORA.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_type import CardType
from app.models.user import User
from app.models.web_portal import WebPortal


def _slugify(value: str) -> str:
    """lower-kebab slug from a card-type key (e.g. ``BusinessCapability`` →
    ``business-capability``)."""
    # Split camelCase / PascalCase into words, then kebab-case.
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    slug = re.sub(r"[^a-z0-9]+", "-", spaced.lower()).strip("-")
    return slug or value.lower()


# Strategic House hub — a curated landing page linking to the Strategic House
# viewpoint and its supporting strategy views.
STRATEGIC_HOUSE_SLUG = "strategic-house"


async def seed_nora_portals(db: AsyncSession) -> dict:
    """Create a published catalogue portal per visible card type + the
    Strategic House hub. Idempotent per slug."""
    admin = (
        await db.execute(
            select(User).where(User.role == "admin", User.is_active.is_(True)).limit(1)
        )
    ).scalar_one_or_none()
    if admin is None:
        admin = (await db.execute(select(User).limit(1))).scalar_one_or_none()
    admin_id = admin.id if admin else None

    existing = set((await db.execute(select(WebPortal.slug))).scalars().all())

    types = (
        (
            await db.execute(
                select(CardType).where(CardType.is_hidden.is_(False)).order_by(CardType.sort_order)
            )
        )
        .scalars()
        .all()
    )

    created = 0

    # ── Catalogue portal per card type ──────────────────────────────────────
    for ct in types:
        slug = _slugify(ct.key)
        if slug == STRATEGIC_HOUSE_SLUG or slug in existing:
            continue
        db.add(
            WebPortal(
                name=ct.label,
                slug=slug,
                description=ct.description or f"Explore all {ct.label} records.",
                kind="catalogue",
                card_type=ct.key,
                is_published=True,
                created_by=admin_id,
            )
        )
        existing.add(slug)
        created += 1

    # ── Strategic House hub ─────────────────────────────────────────────────
    if STRATEGIC_HOUSE_SLUG not in existing:
        db.add(
            WebPortal(
                name="Strategic House",
                slug=STRATEGIC_HOUSE_SLUG,
                description=(
                    "Vision, mission, strategic pillars and their supporting "
                    "objectives at a glance."
                ),
                kind="hub",
                card_type=None,
                tiles=[
                    {
                        "title": "Strategic Alignment",
                        "tiles": [
                            {
                                "icon": "temple_buddhist",
                                "label": "Strategic House",
                                "description": ("Vision, mission, pillars and objectives"),
                                "target": "/reports/strategic-house",
                            },
                            {
                                "icon": "flag",
                                "label": "Objectives",
                                "description": "Strategic objectives catalogue",
                                "target": "/inventory?type=Objective",
                            },
                            {
                                "icon": "view_column",
                                "label": "Strategic Pillars",
                                "description": "The pillars of the strategy",
                                "target": "/inventory?type=Pillar",
                            },
                        ],
                    },
                ],
                is_published=True,
                created_by=admin_id,
            )
        )
        existing.add(STRATEGIC_HOUSE_SLUG)
        created += 1

    await db.commit()

    if created == 0:
        return {"skipped": True, "reason": "Web portals already seeded"}
    return {"loaded": True, "portals": created}
