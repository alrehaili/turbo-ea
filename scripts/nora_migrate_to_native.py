"""Migrate cards on hidden generic types to their NORA-native equivalents.

[FORK] NORA exact-fidelity metamodel (noraPlanMeta.md Phase 5, opt-in migration).

The exact-NORA profile hides the generic tool types (Organization, Provider,
ITComponent, SecurityFunction, Journey, BeneficiaryPersona, …). This one-shot
tool re-types the cards on them to the NORA-native building blocks so existing
data stays visible under the exact model.

SAFETY
------
* **Dry-run by default** — prints the full plan and changes NOTHING. Pass
  ``--apply`` to execute (inside a single transaction).
* **Non-lossy** — attribute values are never deleted. The tool only *adds* the
  mapped NORA attribute keys; old keys stay on the card (hidden under the new
  type's schema) so the change is reversible and nothing is destroyed.
* **Relations are reported, not remapped** — re-typing a card leaves its existing
  relations valid-by-id but "legacy-typed" (their relation-type still declares
  the old endpoint type). The tool reports how many are affected so you can
  decide; it does not silently rewrite relation types.

MAPPINGS
--------
Clean 1:1:  Organization→OrganizationalUnit, Provider→ServiceProvider,
            Journey→BeneficiaryJourney, BeneficiaryPersona→Persona.
Heuristic:  ITComponent→ by subtype (hardware→Server, software→
            InfrastructureManagementTool, saas/paas/iaas/service/aiModel→
            InfrastructureService, none→Server); SecurityFunction→SecuritySoftware.
            Heuristic rows are FLAGGED — expect to hand-correct some.

Usage (from backend/ with the app's DB env vars set):
    python ../scripts/nora_migrate_to_native.py            # dry-run
    python ../scripts/nora_migrate_to_native.py --apply    # execute
    python ../scripts/nora_migrate_to_native.py --only Organization,Provider
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import func, or_, select
from sqlalchemy.orm.attributes import flag_modified

from app.database import async_session
from app.models.card import Card
from app.models.relation import Relation

# Organization.subtype -> OrganizationalUnit.unitType option (where it maps).
_UNIT_TYPE = {
    "ministry": "ministry",
    "authority": "authority",
    "agency": "agency",
    "sector": "sector",
    "department": "department",
    "generalDepartment": "department",
    "sectionUnit": "department",
}

# ITComponent.subtype -> NORA tech type (best-guess heuristic).
_ITC_BY_SUBTYPE = {
    "hardware": ("Server", "physical"),
    "software": ("InfrastructureManagementTool", None),
    "saas": ("InfrastructureService", None),
    "paas": ("InfrastructureService", None),
    "iaas": ("InfrastructureService", None),
    "service": ("InfrastructureService", None),
    "aiModel": ("InfrastructureService", None),  # no true NORA home — flagged
}


class Plan:
    """The resolved change for one card."""

    def __init__(self, card, new_type, new_subtype, added, flags):
        self.card = card
        self.new_type = new_type
        self.new_subtype = new_subtype
        self.added = added  # {attr_key: value} to merge in (non-lossy)
        self.flags = flags  # list[str] warnings


def _resolve(card) -> Plan:
    attrs = card.attributes or {}
    t, st = card.type, card.subtype
    added: dict = {}
    flags: list[str] = []

    if t == "Organization":
        new_type, new_st = "OrganizationalUnit", None
        if st in _UNIT_TYPE:
            added["unitType"] = _UNIT_TYPE[st]
        elif st:
            flags.append(f"subtype '{st}' has no unitType — left unset")
        if attrs.get("location") and not attrs.get("geographicLocation"):
            added["geographicLocation"] = attrs["location"]
        if attrs.get("headCount"):
            flags.append("headCount has no NORA field (kept, hidden)")
        return Plan(card, new_type, new_st, added, flags)

    if t == "Provider":
        for k in ("website", "contractEnd", "providerType"):
            if attrs.get(k):
                flags.append(f"{k} has no NORA field (kept, hidden)")
        return Plan(card, "ServiceProvider", None, added, flags)

    if t == "Journey":
        if st:
            flags.append(f"subtype '{st}' dropped (kept, hidden)")
        return Plan(card, "BeneficiaryJourney", None, added, flags)

    if t == "BeneficiaryPersona":
        if attrs.get("age") and not attrs.get("demographics"):
            added["demographics"] = f"Age: {attrs['age']}"
        return Plan(card, "Persona", "beneficiary", added, flags)

    if t == "ITComponent":
        new_type, new_st = _ITC_BY_SUBTYPE.get(st, ("Server", None))
        flags.append(f"HEURISTIC: subtype '{st or '(none)'}' → {new_type} — verify/hand-correct")
        if st == "aiModel":
            flags.append(
                "AI Model has no NORA tech building block — placed in InfrastructureService"
            )
        return Plan(card, new_type, new_st, added, flags)

    if t == "SecurityFunction":
        flags.append("HEURISTIC: SecurityFunction → SecuritySoftware — verify (may be hardware)")
        return Plan(card, "SecuritySoftware", None, added, flags)

    # Not a migratable type.
    return Plan(card, t, st, added, ["no mapping — skipped"])


MIGRATABLE = [
    "Organization",
    "Provider",
    "Journey",
    "BeneficiaryPersona",
    "ITComponent",
    "SecurityFunction",
]


async def main() -> None:
    ap = argparse.ArgumentParser(description="Migrate hidden generic cards to NORA-native types.")
    ap.add_argument("--apply", action="store_true", help="execute (default: dry-run)")
    ap.add_argument("--only", help="comma-separated old types to migrate (default: all)")
    args = ap.parse_args()

    targets = [x.strip() for x in args.only.split(",")] if args.only else MIGRATABLE
    targets = [t for t in targets if t in MIGRATABLE]

    async with async_session() as db:
        cards = (
            (
                await db.execute(
                    select(Card).where(Card.type.in_(targets), Card.status != "ARCHIVED")
                )
            )
            .scalars()
            .all()
        )
        if not cards:
            print("No active cards on the selected types — nothing to migrate.")
            return

        plans = [_resolve(c) for c in cards]
        card_ids = [c.id for c in cards]
        rel_count = (
            await db.execute(
                select(func.count(Relation.id)).where(
                    or_(Relation.source_id.in_(card_ids), Relation.target_id.in_(card_ids))
                )
            )
        ).scalar() or 0

        # ── Report ────────────────────────────────────────────────────────
        by_pair: dict[tuple[str, str], int] = {}
        for p in plans:
            by_pair[(p.card.type, p.new_type)] = by_pair.get((p.card.type, p.new_type), 0) + 1

        print(
            f"\n{'DRY-RUN — no changes will be made' if not args.apply else 'APPLYING CHANGES'}\n"
        )
        print(f"Cards to migrate: {len(plans)}\n")
        print("By type:")
        for (old, new), n in sorted(by_pair.items()):
            print(f"  {old:<20} → {new:<28} {n:>5}")

        print("\nPer-card detail:")
        for p in plans:
            line = f"  [{p.card.type}] {p.card.name[:48]!r} → {p.new_type}"
            if p.new_subtype:
                line += f" ({p.new_subtype})"
            print(line)
            for k, v in p.added.items():
                print(f"        + {k} = {v!r}")
            for f in p.flags:
                print(f"        ! {f}")

        print(
            f"\nRelations touching these cards: {rel_count}. Re-typing keeps them as "
            "valid links,\nbut their relation-type still declares the OLD endpoint type "
            "(legacy-typed).\nThey are NOT rewritten by this tool."
        )

        if not args.apply:
            print("\nRe-run with --apply to execute. Nothing was changed.")
            return

        # ── Apply ─────────────────────────────────────────────────────────
        for p in plans:
            if p.new_type == p.card.type and p.new_subtype == p.card.subtype and not p.added:
                continue
            p.card.type = p.new_type
            p.card.subtype = p.new_subtype
            if p.added:
                merged = dict(p.card.attributes or {})
                merged.update(p.added)
                p.card.attributes = merged
                flag_modified(p.card, "attributes")
        await db.commit()
        print(f"\n✓ Applied. Migrated {len(plans)} cards.")
        print(
            "  Note: data-quality scores are now stale for migrated cards — they refresh\n"
            "  when a card is next saved. Review HEURISTIC-flagged cards and hand-correct."
        )


if __name__ == "__main__":
    asyncio.run(main())
