"""Unit tests for the maturity scoring helpers ([FORK] — noraPlan.md WP5.2).

Pure logic — no database.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.services.maturity import DEFAULT_MATURITY_DIMENSIONS, compute_overall_score


def _score(level, weight=1):
    return SimpleNamespace(level=level, weight=weight)


def test_compute_overall_score_ignores_unassessed():
    # level 0 rows are unassessed and must not drag the score down.
    scores = [_score(4), _score(2), _score(0), _score(0)]
    # (4 + 2) / (5 * 2) * 100 = 60.0
    assert compute_overall_score(scores) == 60.0


def test_compute_overall_score_weighted():
    scores = [_score(5, weight=3), _score(1, weight=1)]
    # (5*3 + 1*1) / (5 * (3+1)) * 100 = 16/20*100 = 80.0
    assert compute_overall_score(scores) == 80.0


def test_compute_overall_score_none_when_nothing_scored():
    assert compute_overall_score([_score(0), _score(0)]) is None
    assert compute_overall_score([]) is None


def test_default_dimensions_are_unique_and_nonempty():
    keys = [k for k, _, _ in DEFAULT_MATURITY_DIMENSIONS]
    assert len(keys) == len(set(keys))
    for key, name, desc in DEFAULT_MATURITY_DIMENSIONS:
        assert key and name and desc


def test_default_dimensions_are_the_eight_dga_domains():
    # DGA-1-2-1-211 §4.5 Table 4, in the guideline's order.
    assert [name for _, name, _ in DEFAULT_MATURITY_DIMENSIONS] == [
        "Strategic Alignment",
        "Corporate Management Support",
        "EA Framework and Deliverables",
        "EA Governance and Management",
        "EA Capability",
        "Architecture Content",
        "EA Role in the Digital Transformation",
        "Value Realization",
    ]


def test_legacy_dimensions_do_not_overlap_the_dga_domains():
    from app.services.maturity import LEGACY_MATURITY_DIMENSION_KEYS

    assert len(LEGACY_MATURITY_DIMENSION_KEYS) == 10
    assert not LEGACY_MATURITY_DIMENSION_KEYS & {k for k, _, _ in DEFAULT_MATURITY_DIMENSIONS}


def test_dga_accreditation_starts_at_functioning():
    from app.services.maturity import DGA_ACCREDITATION_LEVEL

    assert DGA_ACCREDITATION_LEVEL == 3


def test_every_dga_domain_has_indicators_from_known_sources():
    import json
    from pathlib import Path

    from app.services.maturity import LEGACY_MATURITY_DIMENSION_KEYS
    from app.services.maturity_indicators import DGA_DOMAIN_INDICATORS

    labels = json.loads(
        (
            Path(__file__).resolve().parents[3] / "frontend/src/i18n/locales/en/reports.json"
        ).read_text(encoding="utf-8")
    )["maturity"]["indicator"]
    assert set(DGA_DOMAIN_INDICATORS) == {k for k, _, _ in DEFAULT_MATURITY_DIMENSIONS}
    for domain, sources in DGA_DOMAIN_INDICATORS.items():
        assert sources, domain
        for dim_key, indicator_key in sources:
            assert dim_key is None or dim_key in LEGACY_MATURITY_DIMENSION_KEYS, domain
            assert indicator_key in labels, indicator_key


# --------------------------------------------------------------------------- #
# Automated indicators ([FORK] — automated maturity assessment)
# --------------------------------------------------------------------------- #
from app.services.maturity_indicators import (  # noqa: E402
    _adoption,
    _pick,
    _ratio,
    suggest_level,
)


def test_suggest_level_bands():
    assert suggest_level([]) is None
    assert suggest_level([10.0]) == 1
    assert suggest_level([30.0]) == 2
    assert suggest_level([50.0]) == 3
    assert suggest_level([70.0]) == 4
    assert suggest_level([90.0]) == 5
    # Average across indicators: (100 + 40) / 2 = 70 → level 4.
    assert suggest_level([100.0, 40.0]) == 4


def test_ratio_indicator_skips_empty_denominator():
    assert _ratio("x", 1, 0) is None
    r = _ratio("x", 1, 4)
    assert r is not None and r["value"] == 25.0
    assert r["numerator"] == 1 and r["denominator"] == 4


def test_adoption_indicator_caps_at_100():
    assert _adoption("x", 20, 10)["value"] == 100.0
    assert _adoption("x", 5, 10)["value"] == 50.0


def test_pick_reads_one_indicator_by_dimension_and_key():
    found = {"key": "adr_practice", "value": 50.0}
    out = {"governance": {"indicators": [{"key": "principles_defined"}, found]}}
    extra = {"stakeholder_coverage": {"key": "stakeholder_coverage", "value": 10.0}}

    assert _pick(out, extra, ("governance", "adr_practice")) is found
    assert _pick(out, extra, (None, "stakeholder_coverage"))["value"] == 10.0
    # Skipped (empty denominator) or unknown → None, so the domain is not scored on it.
    assert _pick(out, extra, ("governance", "missing")) is None
    assert _pick(out, extra, ("methodology", "adm_adoption")) is None
    assert _pick(out, {"repository_quality": None}, (None, "repository_quality")) is None
