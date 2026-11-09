"""Unit tests for migration 1178 (seven architecture layers).

The migration renames the six built-in layers to "<Layer> Architecture", moves
each down one place and inserts the Strategy layer on top — each step only
while the row still holds its old default and no other layer already reads as
the new name. These exercise the pure ``plan`` helper — no DB.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from app.services.seed import CARD_TYPE_CATEGORIES

_MIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "1178_seven_architecture_layers_fork.py"
)
_spec = importlib.util.spec_from_file_location("mig1178", _MIG_PATH)
mig = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(mig)

_OLD_DEFAULTS = [
    ("Business", 0),
    ("Beneficiary Experience", 1),
    ("Application", 2),
    ("Data", 3),
    ("Technology", 4),
    ("Security", 5),
]


def _rows(**overrides) -> list[dict]:
    rows = [{"key": k, "label": k, "sort_order": s} for k, s in _OLD_DEFAULTS]
    for row in rows:
        row.update(overrides.get(row["key"], {}))
    return rows


def test_revision_chain():
    assert mig.revision == "1178"
    assert mig.down_revision == "165"


def test_the_migration_lands_on_what_the_seed_holds():
    # A fresh install (seed) and an upgraded one (migration) must agree.
    seed = {c["key"]: c for c in CARD_TYPE_CATEGORIES}
    assert mig.STRATEGY == seed["Strategy"]
    for key, (_, label, sort_order, translations) in mig.RELABELS.items():
        assert (label, sort_order, translations) == (
            seed[key]["label"],
            seed[key]["sort_order"],
            seed[key]["translations"],
        ), key


def test_defaults_are_renamed_moved_down_and_strategy_is_inserted():
    out = mig.plan(_rows())
    assert out["insert_strategy"] is True
    by_key = {u["key"]: u for u in out["updates"]}
    assert by_key["Business"]["label"] == "Business Architecture"
    assert by_key["Business"]["sort_order"] == 1
    assert by_key["Security"]["sort_order"] == 6
    assert by_key["Data"]["translations"]["ar"] == "بنية البيانات"
    assert len(out["updates"]) == 6


def test_a_label_an_admin_changed_is_kept():
    out = mig.plan(_rows(Business={"label": "Core Business"}))
    business = next(u for u in out["updates"] if u["key"] == "Business")
    assert "label" not in business
    assert "translations" not in business
    assert business["sort_order"] == 1


def test_a_layer_order_an_admin_set_is_kept():
    out = mig.plan(_rows(Data={"sort_order": 9}))
    data = next(u for u in out["updates"] if u["key"] == "Data")
    assert "sort_order" not in data
    assert data["label"] == "Data Architecture"


def test_a_row_untouched_on_both_counts_is_not_updated():
    out = mig.plan(_rows(Data={"label": "Info", "sort_order": 9}))
    assert all(u["key"] != "Data" for u in out["updates"])


def test_no_rename_onto_a_name_another_layer_already_uses():
    # An upgraded install may hold upstream's legacy "Business Architecture".
    rows = _rows() + [
        {"key": "Business Architecture", "label": "Business Architecture", "sort_order": 100}
    ]
    business = next(u for u in mig.plan(rows)["updates"] if u["key"] == "Business")
    assert "label" not in business


def test_the_name_clash_check_ignores_case_and_matches_labels():
    rows = _rows() + [{"key": "Legacy", "label": "data architecture", "sort_order": 100}]
    data = next(u for u in mig.plan(rows)["updates"] if u["key"] == "Data")
    assert "label" not in data


def test_strategy_is_not_inserted_twice():
    rows = _rows() + [{"key": "Strategy", "label": "Strategy", "sort_order": 50}]
    assert mig.plan(rows)["insert_strategy"] is False


def test_strategy_is_not_inserted_over_a_layer_named_like_it():
    rows = _rows() + [{"key": "Strat", "label": "Strategy Architecture", "sort_order": 50}]
    assert mig.plan(rows)["insert_strategy"] is False


def test_an_empty_registry_only_gets_strategy():
    # Pre-seed install: the seed inserts the rest on boot.
    assert mig.plan([]) == {"updates": [], "insert_strategy": True}


def test_custom_layers_are_never_touched():
    rows = [{"key": "Integration", "label": "Integration", "sort_order": 0}]
    assert mig.plan(rows)["updates"] == []
