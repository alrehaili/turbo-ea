"""Unit tests for ``app.services.adm_service``.

Exercised without a DB or FastAPI stack; the service is designed as a set of
pure functions that operate on ORM objects held in memory. This lets us
cover the state machine and gate-readiness rules quickly and without the
integration test-DB fixture.

[FORK FEATURE]
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import adm_service


def _phase(**kwargs):
    """Build a lightweight AdmPhase stand-in that has the attributes the
    service reads. Using SimpleNamespace keeps the test independent of the
    ORM constructor's validation rules."""
    defaults = {
        "id": None,
        "status": "not_started",
        "is_continuous": False,
        "phase_key": "phase_a",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _artefact(**kwargs):
    defaults = {
        "id": None,
        "kind": "soaw",
        "ref_id": None,
        "ref_url": None,
        "title": "Test artefact",
        "is_required": False,
        "is_waived": False,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# validate_transition
# ---------------------------------------------------------------------------


class TestValidateTransition:
    @pytest.mark.parametrize(
        "current,target",
        [
            ("not_started", "in_progress"),
            ("in_progress", "ready_for_gate"),
            ("ready_for_gate", "approved"),
            ("in_progress", "blocked"),
            ("blocked", "in_progress"),
            ("approved", "in_progress"),  # reopen
            ("ready_for_gate", "in_progress"),
        ],
    )
    def test_allowed(self, current, target):
        adm_service.validate_transition(current, target)  # no raise

    @pytest.mark.parametrize(
        "current,target",
        [
            ("not_started", "approved"),  # must go through ready_for_gate
            ("not_started", "ready_for_gate"),
            ("in_progress", "approved"),  # must go through ready_for_gate
            ("blocked", "ready_for_gate"),  # blocked → in_progress first
            ("approved", "blocked"),  # terminal → must be reopened first
        ],
    )
    def test_rejected(self, current, target):
        with pytest.raises(adm_service.AdmValidationError):
            adm_service.validate_transition(current, target)

    def test_unknown_target(self):
        with pytest.raises(adm_service.AdmValidationError):
            adm_service.validate_transition("in_progress", "bogus_state")

    def test_same_state_is_noop(self):
        adm_service.validate_transition("in_progress", "in_progress")


# ---------------------------------------------------------------------------
# outstanding_required_artefacts
# ---------------------------------------------------------------------------


class TestOutstanding:
    def test_returns_only_unlinked_required(self):
        arts = [
            _artefact(is_required=True, ref_id=None),  # outstanding
            _artefact(is_required=True, ref_id="uuid"),  # linked
            _artefact(is_required=True, is_waived=True),  # waived
            _artefact(is_required=False),  # not required
            _artefact(is_required=True, ref_url="  "),  # blank url counts as unlinked
            _artefact(is_required=True, ref_url="https://example.com"),  # url counts
        ]
        outstanding = adm_service.outstanding_required_artefacts(arts)
        assert len(outstanding) == 2  # the None-ref one and the whitespace-url one


# ---------------------------------------------------------------------------
# can_mark_ready
# ---------------------------------------------------------------------------


class TestCanMarkReady:
    def test_continuous_phase_always_rejected(self):
        with pytest.raises(adm_service.AdmValidationError):
            adm_service.can_mark_ready(_phase(is_continuous=True), [])

    def test_all_satisfied(self):
        arts = [_artefact(is_required=True, ref_id="uuid")]
        adm_service.can_mark_ready(_phase(), arts)  # no raise

    def test_outstanding_without_override(self):
        arts = [_artefact(is_required=True, title="Missing")]
        with pytest.raises(adm_service.AdmValidationError):
            adm_service.can_mark_ready(_phase(), arts)

    def test_override_requires_reason(self):
        arts = [_artefact(is_required=True, title="Missing")]
        with pytest.raises(adm_service.AdmValidationError):
            adm_service.can_mark_ready(_phase(), arts, override=True, override_reason="short")

    def test_override_with_reason_ok(self):
        arts = [_artefact(is_required=True, title="Missing")]
        adm_service.can_mark_ready(
            _phase(),
            arts,
            override=True,
            override_reason="Board approved deferral until Q3",
        )


# ---------------------------------------------------------------------------
# can_approve
# ---------------------------------------------------------------------------


class TestCanApprove:
    def test_from_ready_ok(self):
        adm_service.can_approve(_phase(status="ready_for_gate"))

    def test_from_in_progress_rejected(self):
        with pytest.raises(adm_service.AdmValidationError):
            adm_service.can_approve(_phase(status="in_progress"))

    def test_continuous_rejected(self):
        with pytest.raises(adm_service.AdmValidationError):
            adm_service.can_approve(_phase(status="ready_for_gate", is_continuous=True))


# ---------------------------------------------------------------------------
# require_reason
# ---------------------------------------------------------------------------


class TestRequireReason:
    def test_empty(self):
        with pytest.raises(adm_service.AdmValidationError):
            adm_service.require_reason(None, "waive")

    def test_too_short(self):
        with pytest.raises(adm_service.AdmValidationError):
            adm_service.require_reason("short", "waive")

    def test_ok(self):
        assert adm_service.require_reason("Long enough reason", "waive") == "Long enough reason"

    def test_trims(self):
        assert adm_service.require_reason("   Padded reason   ", "waive") == "Padded reason"


# ---------------------------------------------------------------------------
# compute_completion_pct
# ---------------------------------------------------------------------------


class TestCompletionPct:
    def test_empty(self):
        assert adm_service.compute_completion_pct([]) == 0

    def test_no_required(self):
        arts = [_artefact(is_required=False)]
        assert adm_service.compute_completion_pct(arts) == 0

    def test_half(self):
        arts = [
            _artefact(is_required=True, ref_id="uuid"),
            _artefact(is_required=True),
        ]
        assert adm_service.compute_completion_pct(arts) == 50

    def test_all_satisfied(self):
        arts = [
            _artefact(is_required=True, ref_id="uuid"),
            _artefact(is_required=True, is_waived=True),
            _artefact(is_required=True, ref_url="https://example.com"),
        ]
        assert adm_service.compute_completion_pct(arts) == 100
