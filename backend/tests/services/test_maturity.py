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
    assert len(keys) == 10
    for key, name, desc in DEFAULT_MATURITY_DIMENSIONS:
        assert key and name and desc


# --------------------------------------------------------------------------- #
# Automated indicators ([FORK] — automated maturity assessment)
# --------------------------------------------------------------------------- #
from app.services.maturity_indicators import (  # noqa: E402
    _adoption,
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
