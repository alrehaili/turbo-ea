"""NORA demo governance cycle (NORAreadiness.md D5) — the pure state split."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.services.governance_service import DEFAULT_GOVERNANCE_CHAIN
from app.services.seed_nora_governance import (
    APPROVED_TYPES,
    IN_REVIEW,
    REJECTED,
    REVIEWERS,
    plan_states,
)


def _cards(type_key: str, *names: str) -> list:
    return [SimpleNamespace(id=uuid.uuid4(), type=type_key, name=n) for n in sorted(names)]


def test_last_cards_by_name_stay_in_review_or_rejected_the_rest_are_approved():
    by_type = {
        "Application": _cards("Application", "A", "B", "C", "D"),
        "GovService": _cards("GovService", "S1", "S2"),
        "Policy": _cards("Policy", "P1", "P2"),
        "Pillar": _cards("Pillar", "X"),
    }
    plan = plan_states(by_type)
    assert [c.name for c in plan["in_review"]] == ["C", "D", "S2"]
    assert [c.name for c in plan["rejected"]] == ["P2"]
    assert sorted(c.name for c in plan["approved"]) == ["A", "B", "P1", "S1", "X"]


def test_no_card_is_in_two_states_and_none_is_lost():
    by_type = {t: _cards(t, f"{t}-1", f"{t}-2", f"{t}-3") for t in APPROVED_TYPES}
    plan = plan_states(by_type)
    ids = [c.id for group in plan.values() for c in group]
    assert len(ids) == len(set(ids))
    assert set(ids) == {c.id for cards in by_type.values() for c in cards}


def test_a_type_with_too_few_cards_is_still_split_without_errors():
    plan = plan_states({"Application": _cards("Application", "Only"), "Policy": []})
    assert [c.name for c in plan["in_review"]] == ["Only"]
    assert plan["approved"] == [] and plan["rejected"] == []


def test_every_state_type_is_an_approved_type_and_every_chain_role_has_a_reviewer():
    assert {t for t, _ in IN_REVIEW} <= set(APPROVED_TYPES)
    assert {t for t, _ in REJECTED} <= set(APPROVED_TYPES)
    assert set(DEFAULT_GOVERNANCE_CHAIN) <= set(REVIEWERS)
