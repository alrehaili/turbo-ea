"""Saudi Government EA Principles & Standards catalog seed.

[FORK FEATURE] — Loads the authority-level, NORA-aligned catalog authored in
``Saudi_Government_EA_Principles_and_Standards.md`` into the GRC → Governance
tab:

* 22 EA principles (P-01 … P-22) → ``ea_principles`` (read by
  ``GET /metamodel/principles`` / the Principles panel).
* 36 enterprise standards (S-01 … S-36) → ``standards`` (read by
  ``GET /metamodel/standards`` / the Standards panel), each linked to its
  supporting principles via the ``standard_principles`` M:N junction — the
  "Linked principles" the panel renders.

Content lives in the bundled ``data/saudi_ea_catalog.json`` (generated from the
source markdown) so this module stays data-driven and small. Idempotent by
``catalogue_id`` (``P-01`` / ``S-01`` …): a re-run tops up only what's missing
and never duplicates, and it links standards to principles that already exist.
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.authoritative_source import AuthoritativeSource
from app.models.ea_principle import EAPrinciple
from app.models.standard import Standard, StandardPrinciple

_DATA_FILE = Path(__file__).parent / "data" / "saudi_ea_catalog.json"


def _load_catalog() -> dict:
    return json.loads(_DATA_FILE.read_text(encoding="utf-8"))


async def seed_saudi_ea_catalog(db: AsyncSession) -> dict:
    """Seed the 22 principles + 36 standards + their principle links + the
    55-entry authoritative-source register.

    Idempotent by ``catalogue_id`` / source ``code``. Returns per-section counts
    (0 = already present / nothing to add). Domain, adoption status and
    authoritative-source codes are stored as first-class fields.
    """
    catalog = _load_catalog()
    principles = catalog["principles"]
    standards = catalog["standards"]
    sources = catalog.get("sources", [])

    # ── Existing catalogue ids (for idempotency + link resolution) ──────────
    existing_principle_ids = {
        cid
        for (cid,) in (
            await db.execute(
                select(EAPrinciple.catalogue_id).where(EAPrinciple.catalogue_id.isnot(None))
            )
        ).all()
    }
    existing_standard_ids = {
        cid
        for (cid,) in (
            await db.execute(select(Standard.catalogue_id).where(Standard.catalogue_id.isnot(None)))
        ).all()
    }

    # ── Principles ──────────────────────────────────────────────────────────
    base_p = (
        await db.execute(select(func.coalesce(func.max(EAPrinciple.sort_order), 0)))
    ).scalar() or 0
    principles_added = 0
    for idx, p in enumerate(principles, start=1):
        if p["id"] in existing_principle_ids:
            continue
        db.add(
            EAPrinciple(
                title=p["title"],
                description=p.get("statement", ""),
                rationale=p.get("rationale", ""),
                implications=p.get("implications", ""),
                is_active=True,
                sort_order=base_p + idx,
                catalogue_id=p["id"],
                domain=p.get("domain"),
                source_ids=p.get("sources", []),
            )
        )
        principles_added += 1

    # ── Standards ───────────────────────────────────────────────────────────
    base_s = (
        await db.execute(select(func.coalesce(func.max(Standard.sort_order), 0)))
    ).scalar() or 0
    standards_added = 0
    for idx, s in enumerate(standards, start=1):
        if s["id"] in existing_standard_ids:
            continue
        db.add(
            Standard(
                title=s["title"],
                description=s.get("statement", ""),
                rationale=s.get("rationale", ""),
                implications=s.get("implications", ""),
                is_active=True,
                sort_order=base_s + idx,
                catalogue_id=s["id"],
                domain=s.get("domain"),
                adoption=s.get("adoption"),
                source_ids=s.get("sources", []),
            )
        )
        standards_added += 1

    # Flush so newly-added rows get ids for the link pass below.
    await db.flush()

    # ── Principle ↔ Standard links (standard_principles junction) ───────────
    principle_by_cid = {
        cid: pid
        for pid, cid in (
            await db.execute(
                select(EAPrinciple.id, EAPrinciple.catalogue_id).where(
                    EAPrinciple.catalogue_id.isnot(None)
                )
            )
        ).all()
    }
    standard_by_cid = {
        cid: sid
        for sid, cid in (
            await db.execute(
                select(Standard.id, Standard.catalogue_id).where(Standard.catalogue_id.isnot(None))
            )
        ).all()
    }
    existing_links = {
        (sid, pid)
        for sid, pid in (
            await db.execute(select(StandardPrinciple.standard_id, StandardPrinciple.principle_id))
        ).all()
    }

    links_added = 0
    for s in standards:
        sid = standard_by_cid.get(s["id"])
        if sid is None:
            continue
        for pcid in s.get("linked_principles", []):
            pid = principle_by_cid.get(pcid)
            if pid is None or (sid, pid) in existing_links:
                continue
            db.add(StandardPrinciple(standard_id=sid, principle_id=pid))
            existing_links.add((sid, pid))
            links_added += 1

    # ── Authoritative-source register (idempotent by code) ──────────────────
    existing_source_codes = {
        code for (code,) in (await db.execute(select(AuthoritativeSource.code))).all()
    }
    sources_added = 0
    for idx, src in enumerate(sources, start=1):
        if src["code"] in existing_source_codes:
            continue
        db.add(
            AuthoritativeSource(
                code=src["code"],
                authority=src.get("authority"),
                classification=src.get("classification"),
                title=src.get("title", ""),
                url=src.get("url"),
                note=src.get("note"),
                sort_order=idx,
            )
        )
        sources_added += 1

    await db.commit()

    if not any((principles_added, standards_added, links_added, sources_added)):
        return {"skipped": True, "reason": "Saudi EA catalog already seeded"}

    return {
        "loaded": True,
        "principles": principles_added,
        "standards": standards_added,
        "principle_standard_links": links_added,
        "authoritative_sources": sources_added,
    }
