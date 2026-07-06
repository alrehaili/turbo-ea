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
