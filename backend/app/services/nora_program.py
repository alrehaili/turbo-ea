"""NORA EA Program deliverable catalogues + seeding.

[FORK FEATURE] — noraPlan.md WP3.1 + WP6.1.

Two methodology catalogues coexist:

* **v1** — the classic 10-stage NORA guideline (stage 0 = continuous
  governance; see NORA.md §1.3–1.4).
* **v2** — the updated Dec-2024 National EA Framework: 7 phases, with
  phases 2 and 4 executed per domain across the six NORA 2.0 domains
  (Business, Beneficiary Experience, Applications, Data, Technology,
  Security). Phase 7 (EA requirements management) is the continuous
  element.

The active methodology is ``app_settings.general_settings.
noraMethodologyVersion`` (``v1`` | ``v2``). Fresh NORA applies default to
v2; installs that already carry v1 deliverable rows stay on v1 until an
admin opts in via ``POST /nora-program/methodology`` — a live program is
never silently rewritten. Both catalogues share the one
``ea_program_deliverables`` table; membership is derived from the key
prefix (v2 built-ins are ``p{1-7}_…``, v2 customs ``custom_v2_…``), so no
schema change was needed.

Titles are data (admin-editable after seeding); stage/phase names and
domain labels are i18n keys on the frontend.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.nora_program import EaProgramDeliverable

NORA_METHODOLOGY_VERSIONS = ("v1", "v2")
# v2 phases are 1–7 (phase 7 = continuous EA requirements management).
NORA_V2_PHASE_NUMBERS = tuple(range(1, 8))

# (key slug, English title fragment) — order matches the NORA 2.0 layer set.
NORA_V2_DOMAINS: tuple[tuple[str, str], ...] = (
    ("business", "Business"),
    ("beneficiary_experience", "Beneficiary Experience"),
    ("applications", "Applications"),
    ("data", "Data"),
    ("technology", "Technology"),
    ("security", "Security"),
)

# key-slug → camelCase domain token used by the frontend i18n keys.
_DOMAIN_CAMEL = {
    "business": "business",
    "beneficiary_experience": "beneficiaryExperience",
    "applications": "applications",
    "data": "data",
    "technology": "technology",
    "security": "security",
}

# (stage_no, key, title)
NORA_DELIVERABLE_CATALOGUE: list[tuple[int, str, str]] = [
    # Stage 1 — Develop EA Project Strategy
    (1, "s1_maturity_assessment", "e-Transformation maturity & IT alignment assessment"),
    (1, "s1_ea_project_strategy", "Approved EA Project Strategy"),
    # Stage 2 — Develop EA Project Plan
    (2, "s2_committees_teams", "EA Governance Committee and working teams established"),
    (2, "s2_development_approach", "Approved EA development approach (scope, budget, sourcing)"),
    (2, "s2_ea_project_plan", "Approved EA Project Plan"),
    # Continuous Governance (stage 0)
    (0, "cg_program_management", "Program management — schedule, budget and progress reporting"),
    (0, "cg_change_management", "Change management — EA awareness and promotion"),
    (0, "cg_capability_management", "Capability management — training, tools and org changes"),
    (0, "cg_policy_management", "Policy management — EA policies and regulations"),
    (0, "cg_performance_management", "Performance management — EA metrics and KPIs"),
    # Stage 3 — Analyze Current State
    (3, "s3_ea_requirements", "EA requirements register"),
    (3, "s3_environment_analysis", "Environment analysis report (internal + external)"),
    (3, "s3_swot", "SWOT analysis report"),
    # Stage 4 — Develop EA Framework
    (4, "s4_vision_mission", "EA vision, mission and architecture objectives"),
    (4, "s4_principles", "Architecture principles"),
    (4, "s4_framework", "EA framework structure and model"),
    (4, "s4_documentation_standard", "EA documentation standard"),
    (4, "s4_artifact_process", "EA artifact review and approval process"),
    # Stage 5 — Build Reference Models
    (5, "s5_prm", "Performance Reference Model (PRM)"),
    (5, "s5_brm", "Business Reference Model (BRM)"),
    (5, "s5_arm", "Application Reference Model (ARM)"),
    (5, "s5_drm", "Data Reference Model (DRM)"),
    (5, "s5_trm", "Technology Reference Model (TRM)"),
    # Stage 6 — Build Current Architecture
    (6, "s6_current_data", "Current business and IT data captured and verified"),
    (6, "s6_current_ba", "Current Business Architecture"),
    (6, "s6_current_aa", "Current Application Architecture"),
    (6, "s6_current_da", "Current Data Architecture"),
    (6, "s6_current_ta", "Current Technology Architecture"),
    (6, "s6_improvements", "Summary of improvement opportunities"),
    # Stage 7 — Build Target Architecture
    (7, "s7_directions", "Target architecture directions"),
    (7, "s7_target_ba", "Target Business Architecture"),
    (7, "s7_target_aa", "Target Application Architecture"),
    (7, "s7_target_da", "Target Data Architecture"),
    (7, "s7_target_ta", "Target Technology Architecture"),
    # Stage 8 — Develop Transition Plan
    (8, "s8_project_list", "Transition project list"),
    (8, "s8_prioritized_list", "Prioritized transition project list"),
    (8, "s8_roadmap", "Transition roadmap"),
    (8, "s8_resource_plan", "Transition resource plan"),
    # Stage 9 — Develop Management Plan
    (9, "s9_usage_plan", "EA usage plan"),
    (9, "s9_management_plan", "EA management plan"),
    # Stage 10 — Execute and Maintain
    (10, "s10_execution", "EA execution and maintenance operating"),
    (10, "s10_maturity", "EA maturity assessment cycle"),
]


def _build_v2_catalogue() -> list[tuple[int, str, str]]:
    """The updated-methodology deliverable catalogue (WP6.1).

    Phase 2 runs its four steps per domain (×6); phase 4 details the target
    per domain after a single cycle-level target concept. Everything else is
    cycle-level. 44 deliverables in total.
    """
    cat: list[tuple[int, str, str]] = [
        # Phase 1 — Define development-cycle scope
        (1, "p1_study_requirements", "Study and assess EA development requirements"),
        (1, "p1_frame_scope", "Frame the development-cycle scope"),
        (1, "p1_approve_scope", "Approved cycle requirements and scope"),
    ]
    # Phase 2 — Current-state diagnosis, executed per domain
    for slug, label in NORA_V2_DOMAINS:
        cat += [
            (2, f"p2_{slug}_scope", f"{label} — approved domain scope"),
            (2, f"p2_{slug}_data_collection", f"{label} — data collection (حصر البيانات)"),
            (
                2,
                f"p2_{slug}_documentation",
                f"{label} — current building blocks and viewpoints documented",
            ),
            (2, f"p2_{slug}_analysis", f"{label} — current-state analysis and recommendations"),
        ]
    cat += [
        # Phase 3 — Study future trends
        (3, "p3_review_results", "Current-state results reviewed"),
        (3, "p3_comparable_practices", "Comparable-practices study"),
        (3, "p3_design_directions", "Approved future design directions"),
        # Phase 4 — Target-state design (concept once, detail per domain)
        (4, "p4_target_concept", "Initial target-architecture concept"),
    ]
    for slug, label in NORA_V2_DOMAINS:
        cat.append(
            (
                4,
                f"p4_{slug}_target_detail",
                f"{label} — target building blocks and viewpoints detailed",
            )
        )
    cat += [
        # Phase 5 — Gap analysis
        (5, "p5_gap_analysis", "Gaps identified and analyzed"),
        (5, "p5_gap_solutions", "Approved gap solutions"),
        # Phase 6 — Roadmap development
        (6, "p6_initiative_list", "Approved EA initiative list"),
        (6, "p6_roadmap", "EA roadmap"),
        # Phase 7 — EA requirements management (continuous)
        (7, "p7_requirements_approval", "EA requirements approval process operating"),
        (7, "p7_requirements_tracking", "Requirement status tracking operating"),
        (7, "p7_change_impact", "Requirement change-impact assessment operating"),
    ]
    return cat


NORA_V2_DELIVERABLE_CATALOGUE: list[tuple[int, str, str]] = _build_v2_catalogue()

_V2_KEY_RE = re.compile(r"^p[1-7]_")


def is_v2_deliverable_key(key: str) -> bool:
    """Whether a deliverable row belongs to the v2 (7-phase) methodology."""
    return bool(_V2_KEY_RE.match(key)) or key.startswith("custom_v2_")


def deliverable_domain(key: str) -> str | None:
    """The camelCase domain token of a per-domain v2 deliverable, or None."""
    m = re.match(r"^p[24]_(.+)$", key)
    if not m:
        return None
    rest = m.group(1)
    for slug, _label in NORA_V2_DOMAINS:
        if rest.startswith(slug + "_"):
            return _DOMAIN_CAMEL[slug]
    return None


async def get_active_methodology(db: AsyncSession) -> str:
    """The stored methodology version, defaulting to v1 (pre-WP6.1 installs)."""
    from app.models.app_settings import AppSettings

    row = (
        await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    ).scalar_one_or_none()
    general = (row.general_settings if row else None) or {}
    version = general.get("noraMethodologyVersion")
    return version if version in NORA_METHODOLOGY_VERSIONS else "v1"


# Practice-establishment checklist (WP6.8) — the Establishing EA Practice
# Guideline's ten operating-model artifacts (§4.1–4.10). These are
# *pre-methodology* (the practice is established once, then cycles run), so
# they live outside the stage/phase numbering under the sentinel stage -1 and
# are surfaced as a separate checklist section on /nora-program.
PRACTICE_STAGE_NO = -1
PRACTICE_CHECKLIST_CATALOGUE: list[tuple[str, str]] = [
    ("practice_ea_strategy", "EA Strategy"),
    ("practice_mandates", "EA Mandates"),
    ("practice_services", "EA Services (practice service catalogue)"),
    ("practice_org_structure", "EA Organizational Structure"),
    ("practice_governance_model", "EA Governance Model"),
    ("practice_processes", "EA Processes"),
    ("practice_interaction_model", "EA Interaction Model"),
    ("practice_kpis", "EA KPIs"),
    ("practice_vocabulary", "EA Vocabulary"),
    ("practice_tools", "EA Tools"),
]


def is_practice_key(key: str) -> bool:
    return key.startswith("practice_")


async def seed_practice_checklist(db: AsyncSession) -> int:
    """Idempotently insert the practice-establishment rows (by key)."""
    existing = {k for (k,) in (await db.execute(select(EaProgramDeliverable.key))).all()}
    created = 0
    for sort_order, (key, title) in enumerate(PRACTICE_CHECKLIST_CATALOGUE):
        if key in existing:
            continue
        db.add(
            EaProgramDeliverable(
                stage_no=PRACTICE_STAGE_NO,
                key=key,
                title=title,
                built_in=True,
                sort_order=sort_order,
            )
        )
        created += 1
    await db.flush()
    return created


async def seed_nora_program(db: AsyncSession, methodology: str = "v1") -> int:
    """Idempotently insert the catalogue rows that are missing (by key)."""
    catalogue = NORA_V2_DELIVERABLE_CATALOGUE if methodology == "v2" else NORA_DELIVERABLE_CATALOGUE
    existing = {k for (k,) in (await db.execute(select(EaProgramDeliverable.key))).all()}
    created = 0
    for sort_order, (stage_no, key, title) in enumerate(catalogue):
        if key in existing:
            continue
        db.add(
            EaProgramDeliverable(
                stage_no=stage_no,
                key=key,
                title=title,
                built_in=True,
                sort_order=sort_order,
            )
        )
        created += 1
    await db.flush()
    return created
