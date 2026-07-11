"""Compatibility tests for the NORA demo dataset ([FORK]).

Mirrors the ``test_seed_demo`` convention: every card type, subtype,
attribute key, select option, relation type and program deliverable used by
``seed_demo_nora`` must exist in the seed metamodel + NORA profile, so a
metamodel change can never silently break the demo.
"""

from __future__ import annotations

import pytest

from app.services.nora_profile import (
    NORA_CARD_TYPES,
    NORA_RELATION_TYPES,
    NORA_TYPE_FIELDS,
    NORA_V2_SUBTYPES,
)
from app.services.seed import RELATIONS, TYPES
from app.services.seed_demo_nora import (
    DEMO_CARDS,
    DEMO_PROGRAM_PROGRESS,
    DEMO_RELATIONS,
)


def _types_by_key() -> dict[str, dict]:
    """Every known card type after the profile applies: seed + NORA types,
    with the NORA Alignment fields merged in."""
    result: dict[str, dict] = {}
    for t in TYPES:
        fields = [f for s in t.get("fields_schema", []) for f in s.get("fields", [])]
        result[t["key"]] = {
            "fields": {f["key"]: f for f in fields},
            "subtypes": {s["key"] for s in t.get("subtypes", [])},
        }
    # NORA-created types must be registered before the field merge — v2 injects
    # profile fields into GovService too (NORA_TYPE_FIELDS["GovService"]).
    for t in NORA_CARD_TYPES:
        fields = [f for s in t.get("fields_schema", []) for f in s.get("fields", [])]
        result[t["key"]] = {
            "fields": {f["key"]: f for f in fields},
            "subtypes": {s["key"] for s in t.get("subtypes", [])},
        }
    for key, extra in NORA_TYPE_FIELDS.items():
        for f in extra:
            result[key]["fields"][f["key"]] = f
    # The profile adds the `database` subtype to ITComponent (pass 4b) and the
    # v2 subtypes (pass 4d).
    result["ITComponent"]["subtypes"].add("database")
    for type_key, subtype_defs in NORA_V2_SUBTYPES.items():
        for sub in subtype_defs:
            result[type_key]["subtypes"].add(sub["key"])
    return result


TYPES_BY_KEY = _types_by_key()
CARDS_BY_REF = {c["ref"]: c for c in DEMO_CARDS}
ALL_RELATION_TYPES = {r["key"]: r for r in RELATIONS} | {r["key"]: r for r in NORA_RELATION_TYPES}


def _card_params():
    return [pytest.param(c, id=c["ref"]) for c in DEMO_CARDS]


class TestDemoCards:
    @pytest.mark.parametrize("card", _card_params())
    def test_type_exists(self, card):
        assert card["type"] in TYPES_BY_KEY, f"unknown type {card['type']}"

    @pytest.mark.parametrize("card", _card_params())
    def test_subtype_valid(self, card):
        if card.get("subtype"):
            assert card["subtype"] in TYPES_BY_KEY[card["type"]]["subtypes"], (
                f"{card['ref']}: subtype {card['subtype']} not on {card['type']}"
            )

    @pytest.mark.parametrize("card", _card_params())
    def test_attribute_keys_and_options_valid(self, card):
        fields = TYPES_BY_KEY[card["type"]]["fields"]
        for key, value in card.get("attributes", {}).items():
            assert key in fields, f"{card['ref']}: unknown attribute {key}"
            field = fields[key]
            options = {o["key"] for o in field.get("options", [])}
            if field.get("type") == "single_select" and value:
                assert value in options, f"{card['ref']}: {key}={value} not an option"
            if field.get("type") == "multiple_select" and value:
                for v in value:
                    assert v in options, f"{card['ref']}: {key} contains invalid {v}"

    @pytest.mark.parametrize("card", _card_params())
    def test_refs_resolve(self, card):
        if card.get("parent"):
            assert card["parent"] in CARDS_BY_REF
        if card.get("successor"):
            assert card["successor"] in CARDS_BY_REF

    def test_refs_unique(self):
        refs = [c["ref"] for c in DEMO_CARDS]
        assert len(refs) == len(set(refs))


class TestDemoRelations:
    @pytest.mark.parametrize(
        "rel", [pytest.param(r, id=f"{r[0]}:{r[1]}->{r[2]}") for r in DEMO_RELATIONS]
    )
    def test_relation_key_and_endpoints(self, rel):
        rel_key, source_ref, target_ref, attrs = rel
        assert rel_key in ALL_RELATION_TYPES, f"unknown relation type {rel_key}"
        rt = ALL_RELATION_TYPES[rel_key]
        assert CARDS_BY_REF[source_ref]["type"] == rt["source_type_key"], (
            f"{rel_key}: source {source_ref} is {CARDS_BY_REF[source_ref]['type']}, "
            f"expected {rt['source_type_key']}"
        )
        assert CARDS_BY_REF[target_ref]["type"] == rt["target_type_key"], (
            f"{rel_key}: target {target_ref} is {CARDS_BY_REF[target_ref]['type']}, "
            f"expected {rt['target_type_key']}"
        )

    def test_transition_roles_valid(self):
        for rel_key, _s, _t, attrs in DEMO_RELATIONS:
            if "transitionRole" in attrs:
                assert attrs["transitionRole"] in ("introduces", "modifies", "retires")
            if "direction" in attrs:
                assert attrs["direction"] in ("sends", "receives", "bidirectional")


class TestDemoProgram:
    def test_deliverable_keys_exist(self):
        # A fresh profile apply seeds the updated 7-phase methodology (WP6.1),
        # so the demo advances v2 catalogue keys.
        from app.services.nora_program import NORA_V2_DELIVERABLE_CATALOGUE

        catalogue_keys = {key for (_stage, key, _title) in NORA_V2_DELIVERABLE_CATALOGUE}
        for key, status, _evidence in DEMO_PROGRAM_PROGRESS:
            assert key in catalogue_keys, f"unknown deliverable {key}"
            assert status in ("notStarted", "inProgress", "inReview", "approved", "descoped")


# ---------------------------------------------------------------------------
# Reset round-trip — proves RESET_NORA_DEMO=true can clear the previously
# seeded landscape so a re-boot with a newer demo dataset lands fresh rows.
# ---------------------------------------------------------------------------


class TestResetRoundTrip:
    @pytest.mark.asyncio
    async def test_seed_reset_reseed(self, db):
        from sqlalchemy import func, select

        from app.models.card import Card
        from app.models.improvement_opportunity import ImprovementOpportunity
        from app.models.nora_program import EaProgramDeliverable
        from app.models.relation import Relation
        from app.models.soaw import SoAW
        from app.services.seed_demo_nora import (
            reset_nora_demo_data,
            seed_nora_demo_data,
        )

        # ── Round 1: seed ─────────────────────────────────────────────
        result = await seed_nora_demo_data(db)
        await db.flush()
        assert not result.get("skipped")
        assert result["cards"] == len(DEMO_CARDS)

        cards_after_seed = (await db.execute(select(func.count()).select_from(Card))).scalar()
        relations_after_seed = (
            await db.execute(select(func.count()).select_from(Relation))
        ).scalar()
        assert cards_after_seed == len(DEMO_CARDS)
        assert relations_after_seed == len(DEMO_RELATIONS)

        soaw_count = (await db.execute(select(func.count()).select_from(SoAW))).scalar()
        opp_count = (
            await db.execute(select(func.count()).select_from(ImprovementOpportunity))
        ).scalar()
        assert soaw_count == 1
        assert opp_count == 1

        advanced_deliverable_keys = {k for k, _s, _e in DEMO_PROGRAM_PROGRESS}
        advanced = (
            await db.execute(
                select(func.count())
                .select_from(EaProgramDeliverable)
                .where(EaProgramDeliverable.key.in_(advanced_deliverable_keys))
                .where(EaProgramDeliverable.status != "notStarted")
            )
        ).scalar()
        assert advanced == len(DEMO_PROGRAM_PROGRESS)

        # ── Round 2: reset ────────────────────────────────────────────
        counts = await reset_nora_demo_data(db)
        await db.flush()
        assert counts["cards"] == len(DEMO_CARDS)
        assert counts["opportunities"] == 1
        assert counts["documents"] == 1
        assert counts["program_updates"] == len(DEMO_PROGRAM_PROGRESS)

        # Cards gone → relations cascade → SoAW + opportunity gone.
        assert (await db.execute(select(func.count()).select_from(Card))).scalar() == 0
        assert (await db.execute(select(func.count()).select_from(Relation))).scalar() == 0
        assert (await db.execute(select(func.count()).select_from(SoAW))).scalar() == 0
        assert (
            await db.execute(select(func.count()).select_from(ImprovementOpportunity))
        ).scalar() == 0

        # Program deliverables the seed advanced are back to notStarted.
        remaining_advanced = (
            await db.execute(
                select(func.count())
                .select_from(EaProgramDeliverable)
                .where(EaProgramDeliverable.key.in_(advanced_deliverable_keys))
                .where(EaProgramDeliverable.status != "notStarted")
            )
        ).scalar()
        assert remaining_advanced == 0

        # ── Round 3: re-seed cleanly on top of an empty landscape ─────
        result2 = await seed_nora_demo_data(db)
        await db.flush()
        assert not result2.get("skipped")
        assert result2["cards"] == len(DEMO_CARDS)
        assert (await db.execute(select(func.count()).select_from(Card))).scalar() == len(
            DEMO_CARDS
        )

    @pytest.mark.asyncio
    async def test_reset_is_idempotent_when_nothing_seeded(self, db):
        """Calling reset on an empty database returns zeroes, not an error."""
        from app.services.seed_demo_nora import reset_nora_demo_data

        counts = await reset_nora_demo_data(db)
        assert counts == {
            "cards": 0,
            "opportunities": 0,
            "documents": 0,
            "program_updates": 0,
        }
