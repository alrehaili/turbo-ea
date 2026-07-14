"""Business rules for the ADM Governance Workspace.

Everything that is not a simple CRUD write lives here so tests can exercise
it without a DB or FastAPI stack.

[FORK FEATURE]
"""

from __future__ import annotations

from typing import Iterable

from app.models.adm import (
    ADM_PHASE_STATUSES,
    AdmPhase,
    AdmPhaseArtefact,
)

# ---------------------------------------------------------------------------
# Phase status state machine
# ---------------------------------------------------------------------------

# Allowed forward and lateral transitions. Skip / reopen are gated on the
# API layer by ``adm.approve_gate``. ``blocked`` is reachable from any state
# except a terminal one; ``approved`` is only reachable from ``ready_for_gate``.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "not_started": {"in_progress", "blocked", "skipped"},
    "in_progress": {"blocked", "ready_for_gate", "skipped"},
    "blocked": {"in_progress", "skipped"},
    "ready_for_gate": {"in_progress", "approved", "blocked", "skipped"},
    "approved": {"in_progress"},  # only reachable via ``reopen``
    "skipped": {"not_started", "in_progress"},
}

MIN_REASON_LEN = 8


class AdmValidationError(ValueError):
    """Raised for a user-facing validation failure. The API layer translates
    this to an HTTP 422 with the message intact."""


def validate_transition(current: str, target: str) -> None:
    """Raise :class:`AdmValidationError` if the transition is not allowed."""
    if target not in ADM_PHASE_STATUSES:
        raise AdmValidationError(f"Unknown phase status: {target}")
    if current == target:
        return
    allowed = _ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise AdmValidationError(f"Cannot transition phase from {current} to {target}")


def outstanding_required_artefacts(
    artefacts: Iterable[AdmPhaseArtefact],
) -> list[AdmPhaseArtefact]:
    """Return artefacts that are required, not waived, and not yet linked.

    A row is considered ``linked`` when either ``ref_id`` is set (soft FK to
    an existing entity) or ``ref_url`` is a non-empty string (for
    ``kind='url'``).
    """
    outstanding: list[AdmPhaseArtefact] = []
    for a in artefacts:
        if not a.is_required or a.is_waived:
            continue
        if a.ref_id is not None:
            continue
        if a.ref_url and a.ref_url.strip():
            continue
        outstanding.append(a)
    return outstanding


def can_mark_ready(
    phase: AdmPhase,
    artefacts: Iterable[AdmPhaseArtefact],
    override: bool = False,
    override_reason: str | None = None,
) -> None:
    """Enforce the readiness gate. Raises :class:`AdmValidationError`
    when the phase cannot be marked ``ready_for_gate``.

    * Continuous phases (Requirements Management) never gate — they are
      always in-flight and cannot be moved to ``ready_for_gate``.
    * Every required artefact must be linked or waived, unless ``override``
      is true and ``override_reason`` is a non-empty string ≥ 8 chars.
    """
    if phase.is_continuous:
        raise AdmValidationError("Continuous phases cannot be marked ready for gate")
    outstanding = outstanding_required_artefacts(artefacts)
    if not outstanding:
        return
    if not override:
        titles = ", ".join(a.title for a in outstanding[:3])
        more = "" if len(outstanding) <= 3 else f" (and {len(outstanding) - 3} more)"
        raise AdmValidationError(
            f"{len(outstanding)} required artefact(s) not linked or waived: {titles}{more}"
        )
    if not override_reason or len(override_reason.strip()) < MIN_REASON_LEN:
        raise AdmValidationError(f"Override reason is required (min {MIN_REASON_LEN} characters)")


def can_approve(phase: AdmPhase) -> None:
    """A phase can be approved only from ``ready_for_gate``."""
    if phase.is_continuous:
        raise AdmValidationError("Continuous phases cannot be approved")
    if phase.status != "ready_for_gate":
        raise AdmValidationError("Only phases marked ready for gate can be approved")


def require_reason(reason: str | None, action: str) -> str:
    """Enforce a non-empty reason for waive / reopen / skip / override."""
    if not reason or len(reason.strip()) < MIN_REASON_LEN:
        raise AdmValidationError(
            f"Reason is required for {action} (min {MIN_REASON_LEN} characters)"
        )
    return reason.strip()


def compute_completion_pct(artefacts: Iterable[AdmPhaseArtefact]) -> int:
    """Percent of required artefacts satisfied (linked or waived).

    Continuous / phases with no required artefacts return 0 — they are
    tracked by status, not by artefact readiness.
    """
    required = [a for a in artefacts if a.is_required]
    if not required:
        return 0
    satisfied = 0
    for a in required:
        if a.is_waived:
            satisfied += 1
        elif a.ref_id is not None:
            satisfied += 1
        elif a.ref_url and a.ref_url.strip():
            satisfied += 1
    return int(round(satisfied * 100 / len(required)))
