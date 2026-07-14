"""Compatibility test for the ADM template catalogue.

Follows the pattern used by ``test_seed_demo.py``: the shape and content of
the built-in template are asserted so an accidental rename / reorder / drop
is caught by CI.

[FORK FEATURE]
"""

from __future__ import annotations

import pytest

from app.models.adm import ADM_ARTEFACT_KINDS, ADM_PHASE_KEYS
from app.services.adm_templates import TOGAF_ADM_TEMPLATE, get_template


class TestTogafTemplate:
    def test_ten_phases(self):
        assert len(TOGAF_ADM_TEMPLATE) == 10

    def test_phase_keys_match_registry(self):
        assert tuple(p["phase_key"] for p in TOGAF_ADM_TEMPLATE) == ADM_PHASE_KEYS

    def test_sort_order_is_monotonic(self):
        sort_orders = [p["sort_order"] for p in TOGAF_ADM_TEMPLATE]
        assert sort_orders == sorted(sort_orders)
        assert sort_orders == list(range(len(TOGAF_ADM_TEMPLATE)))

    def test_only_requirements_management_is_continuous(self):
        continuous = [p["phase_key"] for p in TOGAF_ADM_TEMPLATE if p["is_continuous"]]
        assert continuous == ["requirements_management"]

    @pytest.mark.parametrize("phase", TOGAF_ADM_TEMPLATE, ids=lambda p: p["phase_key"])
    def test_required_artefact_kinds_are_valid(self, phase):
        for req in phase["required_artefacts"]:
            assert req["kind"] in ADM_ARTEFACT_KINDS, (
                f"{phase['phase_key']}: unknown artefact kind {req['kind']}"
            )
            assert req["title"], f"{phase['phase_key']}: required artefact has empty title"


class TestGetTemplate:
    def test_default_key(self):
        assert get_template("togaf") == TOGAF_ADM_TEMPLATE

    def test_unknown_key_raises(self):
        with pytest.raises(ValueError):
            get_template("bogus")
