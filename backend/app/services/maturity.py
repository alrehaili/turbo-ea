"""EA maturity self-assessment helpers ([FORK] — noraPlan.md WP5.2).

Pure-ish helpers: the seeded NORA/Qiyas-style dimension catalogue, the
weighted overall-score computation, and serialisers. Kept out of the route
module so they are unit-testable without a request.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.maturity import (
    MATURITY_MAX_LEVEL,
    MaturityAssessment,
    MaturityDimension,
    MaturityDimensionScore,
)

# The DGA EA maturity model's eight domains — "Enterprise Architecture
# Establishment for Government Entities" (DGA-1-2-1-211, Issue 1.0, 2022),
# §4.5 Table 4. Each description lists the domain's criteria from that table.
# Names are stored as data (admin-editable); the frontend shows a translated
# name only while the stored name is still the seeded English one.
DEFAULT_MATURITY_DIMENSIONS: tuple[tuple[str, str, str], ...] = (
    (
        "dga_strategic_alignment",
        "Strategic Alignment",
        "EA objectives and scope; alignment of business and IT with the strategic goals; "
        "use of international best practice and technology trends.",
    ),
    (
        "dga_management_support",
        "Corporate Management Support",
        "Stakeholders' support and involvement; business support; IT support; "
        "EA communication plan with stakeholders; EA awareness.",
    ),
    (
        "dga_framework_deliverables",
        "EA Framework and Deliverables",
        "EA framework; EA meta-modelling.",
    ),
    (
        "dga_governance_management",
        "EA Governance and Management",
        "EA governance structure; EA governance operationalisation; EA processes and KPIs; "
        "EA interaction.",
    ),
    (
        "dga_capability",
        "EA Capability",
        "EA team; EA tools and repository; continuous learning, training and knowledge sharing.",
    ),
    (
        "dga_architecture_content",
        "Architecture Content",
        "EA requirements; EA principles; EA standards and policies; EA deliverables; "
        "EA data documentation.",
    ),
    (
        "dga_digital_transformation",
        "EA Role in the Digital Transformation",
        "Target architecture; transition planning and roadmap; EA compliance and assurance; "
        "architecture change management.",
    ),
    (
        "dga_value_realization",
        "Value Realization",
        "EA continuous improvement; EA reporting.",
    ),
)

# DGA grants its National EA accreditation certificate from level 3
# ("Functioning") upwards (DGA-1-2-1-211 §4.5).
DGA_ACCREDITATION_LEVEL = 3

# The ten dimensions this fork seeded before the DGA model was adopted (NORA
# profile < 17). Kept so `retire_legacy_dimensions` can recognise them and the
# automated indicators can still serve an install that re-activated them.
LEGACY_MATURITY_DIMENSIONS: tuple[tuple[str, str, str], ...] = (
    (
        "governance",
        "EA Governance & Organization",
        "Mandate, committees, roles, decision rights and funding for the EA function.",
    ),
    (
        "business_architecture",
        "Business Architecture",
        "Capability, process, service and organization models and their upkeep.",
    ),
    (
        "application_architecture",
        "Application Architecture",
        "Application portfolio coverage, rationalization and lifecycle management.",
    ),
    (
        "data_architecture",
        "Data Architecture & Management",
        "Data models, classification (NDMO), ownership, quality and exchange governance.",
    ),
    (
        "technology_architecture",
        "Technology Architecture & Standards",
        "Technology portfolio, reference standards (TRM) and conformance governance.",
    ),
    (
        "security_compliance",
        "Security & Compliance",
        "Cyber-security controls (NCA ECC), privacy (PDPL) and regulatory alignment.",
    ),
    (
        "methodology",
        "EA Process & Methodology",
        "Repeatable NORA stage delivery, artifacts, gates and tooling adoption.",
    ),
    (
        "performance",
        "Performance & Value Realization",
        "KPIs, benefits tracking and demonstrable value from architecture work.",
    ),
    (
        "change_transition",
        "Change & Transition Management",
        "Roadmaps, transition planning and disciplined current→target delivery.",
    ),
    (
        "national_alignment",
        "National Alignment",
        "Alignment to NEA reference models, shared services and whole-of-government goals.",
    ),
)


def compute_overall_score(scores: Iterable[MaturityDimensionScore]) -> float | None:
    """Weighted 0–100 overall from per-dimension levels.

    Only dimensions that have actually been assessed (``level`` > 0) count, so
    a half-finished scorecard is not dragged down by unscored rows. Returns
    ``None`` when nothing has been scored yet.
    """
    scored = [s for s in scores if s.level and s.level > 0]
    if not scored:
        return None
    total_weight = sum(max(1, s.weight) for s in scored)
    if total_weight == 0:
        return None
    weighted = sum(s.level * max(1, s.weight) for s in scored)
    return round(100 * weighted / (MATURITY_MAX_LEVEL * total_weight), 1)


async def seed_maturity_dimensions(db: AsyncSession) -> int:
    """Idempotently insert the default dimension catalogue (by key)."""
    existing = {k for (k,) in (await db.execute(select(MaturityDimension.key))).all()}
    created = 0
    for sort_order, (key, name, description) in enumerate(DEFAULT_MATURITY_DIMENSIONS):
        if key in existing:
            continue
        db.add(
            MaturityDimension(
                key=key,
                name=name,
                description=description,
                weight=1,
                sort_order=sort_order,
                is_active=True,
                built_in=True,
            )
        )
        created += 1
    await db.flush()
    return created


LEGACY_MATURITY_DIMENSION_KEYS: frozenset[str] = frozenset(
    key for key, _, _ in LEGACY_MATURITY_DIMENSIONS
)


async def retire_legacy_dimensions(db: AsyncSession) -> list[str]:
    """Deactivate the pre-DGA built-in dimensions, keeping every row.

    Non-destructive: the rows stay (so past assessments keep their
    ``dimension_id`` and the snapshotted name), they simply stop being added
    to new assessments. Custom dimensions are never touched. Returns the keys
    it deactivated. The caller runs this once per install, so an admin who
    re-activates a legacy dimension afterwards keeps it.
    """
    rows = (
        (
            await db.execute(
                select(MaturityDimension).where(
                    MaturityDimension.key.in_(LEGACY_MATURITY_DIMENSION_KEYS),
                    MaturityDimension.built_in.is_(True),
                    MaturityDimension.is_active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        row.is_active = False
    await db.flush()
    return sorted(row.key for row in rows)


def dimension_dict(d: MaturityDimension) -> dict:
    return {
        "id": str(d.id),
        "key": d.key,
        "name": d.name,
        "description": d.description,
        "weight": d.weight,
        "sort_order": d.sort_order,
        "is_active": d.is_active,
        "built_in": d.built_in,
    }


def score_dict(s: MaturityDimensionScore) -> dict:
    return {
        "id": str(s.id),
        "assessment_id": str(s.assessment_id),
        "dimension_id": str(s.dimension_id) if s.dimension_id else None,
        "dimension_key": s.dimension_key,
        "dimension_name": s.dimension_name,
        "weight": s.weight,
        "sort_order": s.sort_order,
        "level": s.level,
        "target_level": s.target_level,
        "suggested_level": s.suggested_level,
        "evidence": s.evidence,
        "notes": s.notes,
    }


def assessment_dict(
    a: MaturityAssessment,
    scores: list[MaturityDimensionScore] | None = None,
    names: dict | None = None,
) -> dict:
    names = names or {}
    out = {
        "id": str(a.id),
        "title": a.title,
        "assessment_date": a.assessment_date.isoformat() if a.assessment_date else None,
        "status": a.status,
        "notes": a.notes,
        "overall_score": a.overall_score,
        "created_by": str(a.created_by) if a.created_by else None,
        "approved_by": str(a.approved_by) if a.approved_by else None,
        "approved_by_display_name": names.get(a.approved_by),
        "approved_at": a.approved_at.isoformat() if a.approved_at else None,
    }
    if scores is not None:
        out["scores"] = [
            score_dict(s) for s in sorted(scores, key=lambda s: (s.sort_order, s.dimension_name))
        ]
    return out
