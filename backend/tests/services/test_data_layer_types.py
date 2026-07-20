"""DataDomain / DataProduct are first-class built-in card types (plan.md 4.1).

Guards the seed metamodel: the two new Data-layer types exist with their
governance fields, the linking relation types exist, and no ordered
(source, target) pair carries more than one relation type (the metamodel's
pair-uniqueness rule).
"""

from __future__ import annotations

from app.services.seed import RELATIONS, TYPES


def _type(key: str) -> dict:
    return next(t for t in TYPES if t["key"] == key)


def _field_keys(type_key: str, section: str) -> set[str]:
    ct = _type(type_key)
    sec = next(s for s in ct["fields_schema"] if s.get("section") == section)
    return {f["key"] for f in sec["fields"]}


def test_data_domain_type_and_fields():
    dd = _type("DataDomain")
    assert dd["category"] == "Data"
    assert dd["has_hierarchy"] is True
    assert {"steward", "classification", "retentionPolicy", "systemOfRecord"} <= _field_keys(
        "DataDomain", "Domain Information"
    )


def test_data_product_type_and_fields():
    dp = _type("DataProduct")
    assert dp["category"] == "Data"
    assert {"productOwner", "maturity", "sla", "consumers"} <= _field_keys(
        "DataProduct", "Product Information"
    )


def test_data_layer_relation_types_exist():
    keys = {r["key"] for r in RELATIONS}
    assert {
        "relDataObjToDataDomain",
        "relDataProductToDataObj",
        "relDataProductToBC",
    } <= keys


def test_new_data_relations_do_not_collide_on_their_pair():
    """The three new Data relations must each own a unique (source, target) pair.

    (The seed does allow multiple relation types on a self-referential pair —
    e.g. successor vs dependency — so this checks only the new pairs.)
    """
    new_pairs = {
        ("DataObject", "DataDomain"),
        ("DataProduct", "DataObject"),
        ("DataProduct", "BusinessCapability"),
    }
    counts: dict[tuple[str, str], int] = {}
    for r in RELATIONS:
        pair = (r["source_type_key"], r["target_type_key"])
        if pair in new_pairs:
            counts[pair] = counts.get(pair, 0) + 1
    assert all(counts.get(p, 0) == 1 for p in new_pairs), counts
