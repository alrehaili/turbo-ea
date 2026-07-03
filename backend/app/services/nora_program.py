"""NORA EA Program deliverable catalogue + seeding.

[FORK FEATURE] — noraPlan.md WP3.1. The catalogue mirrors the deliverable
tables of the NORA guideline (Stages 1–10 + continuous governance; see
NORA.md §1.3–1.4). Titles are data (admin-editable after seeding); stage
names are i18n keys on the frontend.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.nora_program import EaProgramDeliverable

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


async def seed_nora_program(db: AsyncSession) -> int:
    """Idempotently insert the catalogue rows that are missing (by key)."""
    existing = {k for (k,) in (await db.execute(select(EaProgramDeliverable.key))).all()}
    created = 0
    for sort_order, (stage_no, key, title) in enumerate(NORA_DELIVERABLE_CATALOGUE):
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
