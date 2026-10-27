"""EA governance applicability, review coverage and governed delivery (D-37, D-20).

No database needed: the states, GOV-01 figures and the GOV-09 suppression and
comparison rules are pure functions over assessments, reviews and the
existing delivery-health summary.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.models.ea_review_applicability import EaReviewApplicability
from app.services import ea_applicability as ea
from app.services.governance_transitions import LifecycleError


def _assessment(decision: str) -> EaReviewApplicability:
    return EaReviewApplicability(
        card_id=uuid.uuid4(), decision=decision, criteria_reference="v1 §2", justification="x"
    )


def _review(status: str) -> SimpleNamespace:
    return SimpleNamespace(status=status)


# ── States (D-37, I-58) ─────────────────────────────────────────────────


def test_unassessed_is_unknown_never_exempt_or_compliant():
    assert ea.state_of(None, [_review("approved")]) == ea.UNKNOWN


def test_not_required_is_exempt_whatever_reviews_exist():
    assert ea.state_of(_assessment("not_required"), []) == ea.EXEMPT


@pytest.mark.parametrize("status", ["rejected", "deferred", "scheduled"])
def test_only_an_approved_subject_review_completes_a_required_review(status):
    assert ea.state_of(_assessment("required"), [_review(status)]) == ea.UNGOVERNED
    assert ea.state_of(_assessment("required"), [_review(status), _review("approved")]) == (
        ea.GOVERNED
    )


def test_review_in_progress_is_scheduled_or_deferred():
    assert ea.review_in_progress([_review("scheduled")])
    assert ea.review_in_progress([_review("deferred")])
    assert not ea.review_in_progress([_review("rejected")])


# ── GOV-01 figures (I-59) ───────────────────────────────────────────────


def test_coverage_is_completed_over_requiring_with_every_group_apart():
    ids = [uuid.uuid4() for _ in range(6)]
    states = {
        ids[0]: ea.GOVERNED,
        ids[1]: ea.GOVERNED,
        ids[2]: ea.UNGOVERNED,
        ids[3]: ea.UNGOVERNED,
        ids[4]: ea.EXEMPT,
        ids[5]: ea.UNKNOWN,
    }
    reviews = {ids[2]: [_review("scheduled")]}
    out = ea.coverage_figures(states, reviews)
    assert out["status"] == "ok" and out["value"] == 50.0
    assert (out["requiring_review"], out["review_completed"], out["awaiting_review"]) == (4, 2, 2)
    assert out["review_in_progress"] == 1
    assert (out["exempt"], out["undetermined"], out["population"]) == (1, 1, 6)
    assert out["assessment_coverage"] == {"assessed": 5, "population": 6, "percentage": 83.3}


def test_coverage_is_not_available_when_nothing_requires_review():
    states = {uuid.uuid4(): ea.EXEMPT, uuid.uuid4(): ea.UNKNOWN}
    out = ea.coverage_figures(states, {})
    assert out["status"] == "not_available"
    assert out["reason"] == {"code": "no_required_reviews"}
    assert "value" not in out
    assert out["assessment_coverage"]["assessed"] == 1


# ── GOV-09 suppression and comparison (D-20, I-61) ──────────────────────


def _summary(reported: int, in_flight: int, on_track_pct: float | None) -> dict:
    return {
        "in_flight": in_flight,
        "on_track_pct": on_track_pct,
        "states": {},
        "coverage": {"reported": reported, "percentage": 100.0 if in_flight else None},
    }


def test_a_group_rate_needs_five_reporting_initiatives():
    shown = ea.group_figure(_summary(5, 6, 60.0), 7)
    hidden = ea.group_figure(_summary(4, 9, 75.0), 9)
    assert shown["on_track_pct"] == 60.0 and not shown["suppressed"]
    assert hidden["on_track_pct"] is None and hidden["suppressed"]
    # Counts stay visible when the rate is suppressed.
    assert (hidden["in_flight"], hidden["reported"]) == (9, 4)


def test_difference_only_when_both_compared_groups_are_shown():
    groups = {
        ea.GOVERNED: ea.group_figure(_summary(6, 6, 80.0), 6),
        ea.UNGOVERNED: ea.group_figure(_summary(5, 5, 60.0), 5),
        ea.EXEMPT: ea.group_figure(_summary(1, 1, 100.0), 1),
        ea.UNKNOWN: ea.group_figure(_summary(2, 2, 0.0), 2),
    }
    out = ea.comparison(groups)
    assert out == {
        "status": "ok",
        "difference_pct_points": 20.0,
        "interpretation": "association_not_causation",
        "minimum_group_size": 5,
    }
    groups[ea.UNGOVERNED] = ea.group_figure(_summary(3, 8, 10.0), 8)
    assert ea.comparison(groups)["status"] == "suppressed"


# ── Recording an assessment (D-37) ──────────────────────────────────────


class _Session:
    def __init__(self):
        self.added: list = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def commit(self):  # pragma: no cover - would fail the test if reached
        raise AssertionError("a helper must not commit")


def _initiative(**kw):
    return SimpleNamespace(
        id=uuid.uuid4(), type=kw.get("type", "Initiative"), status=kw.get("status", "ACTIVE")
    )


@pytest.mark.parametrize(
    ("card", "decision", "criteria", "why", "code"),
    [
        (_initiative(type="Application"), "required", "v1", "x", "not_an_initiative"),
        (_initiative(status="ARCHIVED"), "required", "v1", "x", "not_an_initiative"),
        (_initiative(), "maybe", "v1", "x", "invalid_decision"),
        (_initiative(), "required", " ", "x", "criteria_required"),
        (_initiative(), "required", "x" * 301, "x", "criteria_required"),
        (_initiative(), "not_required", "v1", " ", "justification_required"),
    ],
)
async def test_an_assessment_needs_every_field(card, decision, criteria, why, code):
    with pytest.raises(LifecycleError) as err:
        await ea.record_assessment(_Session(), card, decision, criteria, why, uuid.uuid4())
    assert (err.value.status, err.value.code) == (422, code)


async def test_an_assessment_is_appended_and_published(monkeypatch):
    published = []

    async def no_previous(db, ids):
        return {}

    async def publish(event, data, **kw):
        published.append((event, data, kw.get("card_id")))

    monkeypatch.setattr(ea, "latest_assessments", no_previous)
    monkeypatch.setattr(ea.event_bus, "publish", publish)
    db = _Session()
    card = _initiative()
    actor = uuid.uuid4()
    row = await ea.record_assessment(db, card, "not_required", " v1 §2 ", " Small change ", actor)
    assert db.added == [row]
    assert (row.decision, row.criteria_reference, row.justification, row.decided_by) == (
        "not_required",
        "v1 §2",
        "Small change",
        actor,
    )
    assert published == [
        (
            "ea_applicability.assessed",
            {"decision": "not_required", "previous_decision": None, "criteria_reference": "v1 §2"},
            card.id,
        )
    ]
