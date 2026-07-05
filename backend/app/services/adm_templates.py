"""ADM Governance Workspace — phase template catalogue.

Kept in code (not the DB) — mirrors how the NORA program deliverable
catalogue works. When a workspace is created, one row per template entry is
inserted into ``adm_phases`` and can then be independently edited (title,
description, required artefacts) without affecting the catalogue.

[FORK FEATURE]
"""

from __future__ import annotations

from typing import TypedDict


class ArtefactRequirement(TypedDict):
    """A pre-defined required-artefact placeholder seeded into every workspace.

    The ``kind`` maps to :data:`app.models.adm.ADM_ARTEFACT_KINDS`. Rows are
    created as un-linked (``ref_id`` NULL, ``is_required=True``) so the phase
    starts in a "Ready-for-Gate blocked" state until an artefact is linked
    or the requirement is explicitly waived.
    """

    kind: str
    title: str  # human-facing label shown until the requirement is linked


class PhaseTemplate(TypedDict):
    phase_key: str
    title: str
    description: str
    sort_order: int
    is_continuous: bool
    required_artefacts: list[ArtefactRequirement]


# Canonical TOGAF ADM template. Titles and descriptions are English source
# strings; the frontend re-labels via i18n keys and shows the phase_key
# under the resolved translation.
TOGAF_ADM_TEMPLATE: list[PhaseTemplate] = [
    {
        "phase_key": "preliminary",
        "title": "Preliminary",
        "description": (
            "Establish the architecture capability, principles, tailored ADM "
            "process and governance framework for the engagement."
        ),
        "sort_order": 0,
        "is_continuous": False,
        "required_artefacts": [
            {"kind": "card", "title": "Architecture principles"},
            {"kind": "soaw", "title": "Statement of Architecture Work (charter)"},
        ],
    },
    {
        "phase_key": "phase_a",
        "title": "Phase A — Architecture Vision",
        "description": (
            "Articulate the vision, scope, objectives, stakeholders and "
            "business drivers for the engagement."
        ),
        "sort_order": 1,
        "is_continuous": False,
        "required_artefacts": [
            {"kind": "soaw", "title": "Approved SoAW / engagement charter"},
            {"kind": "diagram", "title": "Vision / value-chain diagram"},
        ],
    },
    {
        "phase_key": "phase_b",
        "title": "Phase B — Business Architecture",
        "description": (
            "Baseline and target Business Architecture — capability maps, "
            "processes, organisation, value streams."
        ),
        "sort_order": 2,
        "is_continuous": False,
        "required_artefacts": [
            {"kind": "diagram", "title": "Capability map"},
            {"kind": "card", "title": "Key business processes"},
        ],
    },
    {
        "phase_key": "phase_c",
        "title": "Phase C — Information Systems Architecture",
        "description": (
            "Baseline and target Application and Data Architecture — "
            "landscape, integrations, data entities and flows."
        ),
        "sort_order": 3,
        "is_continuous": False,
        "required_artefacts": [
            {"kind": "diagram", "title": "Application landscape"},
            {"kind": "diagram", "title": "Data architecture / flow"},
        ],
    },
    {
        "phase_key": "phase_d",
        "title": "Phase D — Technology Architecture",
        "description": (
            "Baseline and target Technology Architecture — infrastructure, "
            "platforms, technology standards and security views."
        ),
        "sort_order": 4,
        "is_continuous": False,
        "required_artefacts": [
            {"kind": "tech_standard", "title": "Technology standards"},
            {"kind": "diagram", "title": "Technology / infrastructure view"},
        ],
    },
    {
        "phase_key": "phase_e",
        "title": "Phase E — Opportunities and Solutions",
        "description": (
            "Identify major work packages, solution options and their "
            "rationale. Anchor Architecture Decision Records here."
        ),
        "sort_order": 5,
        "is_continuous": False,
        "required_artefacts": [
            {"kind": "adr", "title": "Architecture Decision Record"},
        ],
    },
    {
        "phase_key": "phase_f",
        "title": "Phase F — Migration Planning",
        "description": (
            "Sequence the work packages into transition architectures and "
            "migration waves; identify dependencies and roadmap."
        ),
        "sort_order": 6,
        "is_continuous": False,
        "required_artefacts": [
            {"kind": "roadmap", "title": "Transition roadmap"},
        ],
    },
    {
        "phase_key": "phase_g",
        "title": "Phase G — Implementation Governance",
        "description": (
            "Govern the implementation: compliance reviews, deviations, "
            "risks arising during delivery."
        ),
        "sort_order": 7,
        "is_continuous": False,
        "required_artefacts": [
            {"kind": "risk", "title": "Implementation risk"},
        ],
    },
    {
        "phase_key": "phase_h",
        "title": "Phase H — Architecture Change Management",
        "description": (
            "Monitor changes to the business and technology environment "
            "and manage requested architecture changes."
        ),
        "sort_order": 8,
        "is_continuous": False,
        "required_artefacts": [],
    },
    {
        "phase_key": "requirements_management",
        "title": "Requirements Management",
        "description": (
            "Continuous management of architecture requirements — recorded, "
            "traced and reviewed across every phase, never sequential."
        ),
        "sort_order": 9,
        "is_continuous": True,
        "required_artefacts": [
            {"kind": "requirement", "title": "Architecture requirement"},
        ],
    },
]


def get_template(key: str = "togaf") -> list[PhaseTemplate]:
    """Return the phase template by key. Only ``togaf`` is bundled today."""
    if key != "togaf":
        raise ValueError(f"Unknown ADM template: {key}")
    return TOGAF_ADM_TEMPLATE
