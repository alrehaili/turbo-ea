"""NORA seeds use the NORA building blocks, never the hidden generic twins
([FORK] — NORAreadiness.md B-8).

Under the NORA profile ``Organization`` and ``BeneficiaryPersona`` are hidden:
the DGA Content Meta Model models an organization as Organizational Units and
a beneficiary profile as a Persona. A NORA seed that creates the hidden twin
puts cards on screen through relation panels as "Uncategorized" duplicates.

The fill seeders resolve relation ends **by name only**, so a relation type
must also name the type each end really is — otherwise a unit would be linked
through an Organization relation type. These tests check both, from the seed
data itself (no database).
"""

from __future__ import annotations

import pytest

from app.services import seed_nora_landscape_fill, seed_nora_viewpoint_fill
from app.services.nora_profile import NORA_HIDDEN_TYPE_KEYS, NORA_RELATION_TYPES
from app.services.seed import RELATIONS
from app.services.seed_demo_nora import DEMO_CARDS, DEMO_RELATIONS
from app.services.seed_nora_presets import (
    NORA_PRESETS,
    PRESET_TYPE_RETARGET,
    retarget_preset_config,
)

# The generic types B-8 retired from the NORA seeds, and their NORA twin.
RETIRED = {"Organization": "OrganizationalUnit", "BeneficiaryPersona": "Persona"}

RELATION_ENDS = {
    r["key"]: (r["source_type_key"], r["target_type_key"])
    for r in [*RELATIONS, *NORA_RELATION_TYPES]
}

SEED_RELATIONS = [("seed_demo_nora", key, src, tgt) for key, src, tgt, _ in DEMO_RELATIONS] + [
    (module.__name__.rsplit(".", 1)[-1], key, src, tgt)
    for module in (seed_nora_landscape_fill, seed_nora_viewpoint_fill)
    for key, src, tgt in module.RELATIONS
]


def test_the_retired_types_are_hidden_under_nora():
    assert set(RETIRED) <= set(NORA_HIDDEN_TYPE_KEYS)


def test_the_demo_creates_no_card_on_a_retired_type():
    assert not [c["ref"] for c in DEMO_CARDS if c["type"] in RETIRED]


def test_the_demo_organization_is_a_unit_ladder():
    units = {c["ref"]: c for c in DEMO_CARDS if c["type"] == "OrganizationalUnit"}
    assert units["org_root"]["attributes"]["unitType"] == "ministry"
    assert units["org_dt_it_apps_int"]["parent"] == "org_dt_it_apps"


@pytest.mark.parametrize(
    "seeder,key,src,tgt", SEED_RELATIONS, ids=lambda v: v if isinstance(v, str) else None
)
def test_no_seed_relation_has_a_retired_end(seeder, key, src, tgt):
    ends = RELATION_ENDS.get(key)
    assert ends is not None, f"{seeder}: unknown relation type {key}"
    assert not set(ends) & set(RETIRED), f"{seeder}: {key} {ends} ends on a retired type"


def _named_type() -> dict[str, str]:
    """Seeded card name → type, for the units and personas the fills link by name."""
    names = {c["name"]: c["type"] for c in DEMO_CARDS if c["type"] == "OrganizationalUnit"}
    names.update({name: "Persona" for name, _, _ in seed_nora_viewpoint_fill.PERSONAS})
    return names


def test_name_resolved_relations_name_the_real_end_types():
    named = _named_type()
    wrong = []
    for seeder, key, src, tgt in SEED_RELATIONS:
        src_type, tgt_type = RELATION_ENDS[key]
        for name, declared in ((src, src_type), (tgt, tgt_type)):
            if name in named and named[name] != declared:
                wrong.append(f"{seeder}: {key} names {name!r} as {declared}")
    assert not wrong


def test_viewpoint_fill_personas_are_beneficiary_personas():
    assert {subtype for _, subtype, _ in seed_nora_viewpoint_fill.PERSONAS} == {"beneficiary"}


def test_no_preset_reads_a_retired_type():
    for preset in NORA_PRESETS:
        config = preset["config"]
        assert (config.get("filters") or {}).get("type") not in RETIRED, preset["code"]
        assert config.get("source") not in RETIRED, preset["code"]
        assert config.get("target") not in RETIRED, preset["code"]


def test_preset_retarget_map_matches_the_retired_types():
    assert PRESET_TYPE_RETARGET == RETIRED


class TestRetargetPresetConfig:
    def test_moves_filter_source_and_target(self):
        assert retarget_preset_config(
            {"_noraPreset": "X", "filters": {"type": "Organization", "q": 1}}
        ) == {"_noraPreset": "X", "filters": {"type": "OrganizationalUnit", "q": 1}}
        assert retarget_preset_config(
            {"_noraPreset": "X", "source": "BeneficiaryPersona", "target": "Organization"}
        ) == {"_noraPreset": "X", "source": "Persona", "target": "OrganizationalUnit"}

    def test_leaves_other_reports_and_changed_filters_alone(self):
        assert retarget_preset_config({"filters": {"type": "Organization"}}) is None
        assert retarget_preset_config({"_noraPreset": "X", "filters": {"type": "Server"}}) is None
        assert retarget_preset_config({"_noraPreset": "X", "source": "Application"}) is None
        assert retarget_preset_config({"_noraPreset": "X", "filters": "Organization"}) is None
        assert retarget_preset_config(None) is None
        assert retarget_preset_config({}) is None

    def test_does_not_change_its_input(self):
        config = {"_noraPreset": "X", "filters": {"type": "Organization"}}
        retarget_preset_config(config)
        assert config == {"_noraPreset": "X", "filters": {"type": "Organization"}}
