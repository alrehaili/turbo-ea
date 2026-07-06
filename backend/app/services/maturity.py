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

# NORA/Qiyas-style default EA maturity dimensions. Names are stored as data
# (admin-editable, like card names) — the frontend translates only the fixed
# 1–5 level labels, not these. Ten dimensions spanning governance, the four
# architecture domains, security, methodology, performance, change, and
# national alignment.
DEFAULT_MATURITY_DIMENSIONS: tuple[tuple[str, str, str], ...] = (
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
