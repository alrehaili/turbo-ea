"""Strategic House foundation + EA Maturity Self-Assessment seeded data.

[FORK FEATURE] — Complete strategic framework:
✓ Vision + Mission (stored as settings — general_settings.noraVision/noraMission,
  exactly what the Strategic House viewpoint reads via GET /settings/strategy-house)
✓ Strategic Pillars (Pillar cards) → Objectives (Objective cards) via the
  relObjectiveToPillar "supports" relation (what GET /reports/strategy-cascade reads)
✓ Strategic Initiatives (Initiative cards, program subtype)
✓ EA Maturity: 5 assessment runs + 50 dimension scores across the 10 built-in
  maturity dimensions, showing an improvement trajectory Q1 2024 → Q1 2025

The Strategic House does NOT model vision/mission as cards — they are agency
settings. Objectives attach to pillars via the relObjectiveToPillar relation
(NOT parent_id), which is what the cascade report actually queries.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSettings
from app.models.card import Card
from app.models.maturity import MaturityAssessment, MaturityDimension, MaturityDimensionScore
from app.models.relation import Relation
from app.services.maturity import compute_overall_score

# ════════════════════════════════════════════════════════════════════════════
# STRATEGIC HOUSE: VISION + MISSION (settings) → PILLARS → OBJECTIVES → INITIATIVES
# ════════════════════════════════════════════════════════════════════════════

# Vision & Mission are stored as agency settings (noraVision / noraMission), the
# "roof" and "band" of the Strategic House — NOT cards.
VISION_TEXT = (
    "Vision 2030: a digital, efficient and citizen-centric government — the "
    "world's leading digital public sector."
)
MISSION_TEXT = (
    "Enable unified, interoperable government services through integrated, "
    "data-driven operations and seamless cross-agency collaboration."
)

# LEVEL 1: Strategic Pillars (the "columns" of the house — no parent)
STRATEGIC_PILLARS_EXTENDED = [
    {
        "ref": "pil_digital_innovation",
        "type": "Pillar",
        "name": "Digital Innovation & Technology",
        "attributes": {
            "pillarCode": "SP-1",
            "focus": "Modernize technology stack, embrace cloud-first, enable AI/automation",
            "keyOutcomes": [
                "Cloud adoption 80%+",
                "API-first architecture",
                "Reduced legacy systems",
            ],
        },
    },
    {
        "ref": "pil_operational_excellence",
        "type": "Pillar",
        "name": "Operational Excellence",
        "attributes": {
            "pillarCode": "SP-2",
            "focus": "Streamline processes, reduce costs, improve efficiency metrics",
            "keyOutcomes": ["40% cost reduction", "Automation 85%+", "Service delivery < 3 days"],
        },
    },
    {
        "ref": "pil_citizen_experience",
        "type": "Pillar",
        "name": "Citizen & Business Experience",
        "attributes": {
            "pillarCode": "SP-3",
            "focus": "Omnichannel service delivery, personalization, accessibility",
            "keyOutcomes": [
                "Digital adoption 90%+",
                "Satisfaction score 8.5+",
                "Zero-touch services",
            ],
        },
    },
    {
        "ref": "pil_data_governance",
        "type": "Pillar",
        "name": "Data as Strategic Asset",
        "attributes": {
            "pillarCode": "SP-4",
            "focus": "Data governance, analytics, cross-agency sharing",
            "keyOutcomes": ["Single data lake", "Real-time insights", "GDPR/PDPA compliance"],
        },
    },
    {
        "ref": "pil_security_resilience",
        "type": "Pillar",
        "name": "Security & Resilience",
        "attributes": {
            "pillarCode": "SP-5",
            "focus": "Cybersecurity maturity, disaster recovery, zero-trust",
            "keyOutcomes": ["Zero critical incidents", "RTO < 4 hours", "Threat detection < 5 min"],
        },
    },
    {
        "ref": "pil_ecosystem_partnership",
        "type": "Pillar",
        "name": "Ecosystem & Partnerships",
        "attributes": {
            "pillarCode": "SP-6",
            "focus": "Developer ecosystem, vendor partnerships, interoperability",
            "keyOutcomes": [
                "100 API consumers",
                "50 partner integrations",
                "Open standards adoption",
            ],
        },
    },
]

# LEVEL 2: Strategic Objectives (3-5 per pillar, linked to pillar parent)
STRATEGIC_OBJECTIVES_BY_PILLAR = {
    "pil_digital_innovation": [
        {
            "ref": "obj_cloud_migration",
            "type": "Objective",
            "name": "Complete Cloud Migration Program",
            "parent": "pil_digital_innovation",
            "attributes": {
                "targetYear": 2026,
                "pillarAlignment": "Digital Innovation",
                "measurableGoal": "80% workloads on government cloud",
                "investmentRequired": "250M SAR",
            },
        },
        {
            "ref": "obj_api_platform",
            "type": "Objective",
            "name": "Establish Enterprise API Platform",
            "parent": "pil_digital_innovation",
            "attributes": {
                "targetYear": 2025,
                "pillarAlignment": "Digital Innovation",
                "measurableGoal": "500+ APIs published, 100+ consuming agencies",
                "investmentRequired": "80M SAR",
            },
        },
        {
            "ref": "obj_ai_automation",
            "type": "Objective",
            "name": "Deploy AI & Intelligent Automation",
            "parent": "pil_digital_innovation",
            "attributes": {
                "targetYear": 2027,
                "pillarAlignment": "Digital Innovation",
                "measurableGoal": "30 automated processes, 10 AI assistants",
                "investmentRequired": "120M SAR",
            },
        },
    ],
    "pil_operational_excellence": [
        {
            "ref": "obj_process_optimization",
            "type": "Objective",
            "name": "Optimize Core Business Processes",
            "parent": "pil_operational_excellence",
            "attributes": {
                "targetYear": 2026,
                "pillarAlignment": "Operational Excellence",
                "measurableGoal": "40% cost reduction, 50% cycle time reduction",
                "investmentRequired": "150M SAR",
            },
        },
        {
            "ref": "obj_automation_increase",
            "type": "Objective",
            "name": "Increase Process Automation to 85%",
            "parent": "pil_operational_excellence",
            "attributes": {
                "targetYear": 2025,
                "pillarAlignment": "Operational Excellence",
                "measurableGoal": "50 automated business processes",
                "investmentRequired": "100M SAR",
            },
        },
        {
            "ref": "obj_service_sla",
            "type": "Objective",
            "name": "Achieve SLA Excellence (99.9% availability)",
            "parent": "pil_operational_excellence",
            "attributes": {
                "targetYear": 2024,
                "pillarAlignment": "Operational Excellence",
                "measurableGoal": "99.9% uptime across all critical services",
                "investmentRequired": "50M SAR",
            },
        },
    ],
    "pil_citizen_experience": [
        {
            "ref": "obj_omnichannel",
            "type": "Objective",
            "name": "Build Omnichannel Service Delivery",
            "parent": "pil_citizen_experience",
            "attributes": {
                "targetYear": 2025,
                "pillarAlignment": "Citizen Experience",
                "measurableGoal": "Seamless experience across web, mobile, voice, office",
                "investmentRequired": "90M SAR",
            },
        },
        {
            "ref": "obj_digital_adoption",
            "type": "Objective",
            "name": "Drive Digital Service Adoption to 90%",
            "parent": "pil_citizen_experience",
            "attributes": {
                "targetYear": 2026,
                "pillarAlignment": "Citizen Experience",
                "measurableGoal": "90% of transactions via digital channels",
                "investmentRequired": "60M SAR",
            },
        },
        {
            "ref": "obj_satisfaction_nps",
            "type": "Objective",
            "name": "Achieve NPS Score of 60+",
            "parent": "pil_citizen_experience",
            "attributes": {
                "targetYear": 2025,
                "pillarAlignment": "Citizen Experience",
                "measurableGoal": "NPS 60+, CSAT 8.5+",
                "investmentRequired": "40M SAR",
            },
        },
    ],
    "pil_data_governance": [
        {
            "ref": "obj_data_lake",
            "type": "Objective",
            "name": "Build Enterprise Data Lake",
            "parent": "pil_data_governance",
            "attributes": {
                "targetYear": 2025,
                "pillarAlignment": "Data Governance",
                "measurableGoal": "Centralized lake with 500B+ records, real-time insights",
                "investmentRequired": "180M SAR",
            },
        },
        {
            "ref": "obj_data_sharing",
            "type": "Objective",
            "name": "Enable Cross-Agency Data Sharing",
            "parent": "pil_data_governance",
            "attributes": {
                "targetYear": 2025,
                "pillarAlignment": "Data Governance",
                "measurableGoal": "50+ agencies sharing data securely",
                "investmentRequired": "70M SAR",
            },
        },
        {
            "ref": "obj_data_quality",
            "type": "Objective",
            "name": "Achieve 95% Data Quality Score",
            "parent": "pil_data_governance",
            "attributes": {
                "targetYear": 2026,
                "pillarAlignment": "Data Governance",
                "measurableGoal": "Completeness, accuracy, consistency all 95%+",
                "investmentRequired": "55M SAR",
            },
        },
    ],
    "pil_security_resilience": [
        {
            "ref": "obj_zero_trust",
            "type": "Objective",
            "name": "Implement Zero Trust Security",
            "parent": "pil_security_resilience",
            "attributes": {
                "targetYear": 2026,
                "pillarAlignment": "Security",
                "measurableGoal": "100% of access requests verified, encrypted end-to-end",
                "investmentRequired": "130M SAR",
            },
        },
        {
            "ref": "obj_threat_detection",
            "type": "Objective",
            "name": "Reduce Threat Detection Time to < 5 min",
            "parent": "pil_security_resilience",
            "attributes": {
                "targetYear": 2025,
                "pillarAlignment": "Security",
                "measurableGoal": "Advanced SIEM + AI-driven threat hunting",
                "investmentRequired": "95M SAR",
            },
        },
        {
            "ref": "obj_disaster_recovery",
            "type": "Objective",
            "name": "Achieve RTO/RPO < 4 hours",
            "parent": "pil_security_resilience",
            "attributes": {
                "targetYear": 2024,
                "pillarAlignment": "Security",
                "measurableGoal": "Redundant datacenters, automated failover",
                "investmentRequired": "110M SAR",
            },
        },
    ],
    "pil_ecosystem_partnership": [
        {
            "ref": "obj_developer_ecosystem",
            "type": "Objective",
            "name": "Build Developer Ecosystem (100+ partners)",
            "parent": "pil_ecosystem_partnership",
            "attributes": {
                "targetYear": 2027,
                "pillarAlignment": "Ecosystem",
                "measurableGoal": "100 API consumers, 50 startups, 20 integrators",
                "investmentRequired": "75M SAR",
            },
        },
        {
            "ref": "obj_vendor_partnerships",
            "type": "Objective",
            "name": "Establish Strategic Vendor Partnerships",
            "parent": "pil_ecosystem_partnership",
            "attributes": {
                "targetYear": 2025,
                "pillarAlignment": "Ecosystem",
                "measurableGoal": "15 Tier-1 vendor partnerships, joint innovation",
                "investmentRequired": "45M SAR",
            },
        },
    ],
}

# LEVEL 3: Strategic Initiatives (Programs) - linked to objectives
STRATEGIC_INITIATIVES = [
    {
        "ref": "init_cloud_migration",
        "type": "Initiative",
        "subtype": "program",
        "name": "Digital Infrastructure Modernization Program (DIMP)",
        "parent": "obj_cloud_migration",
        "attributes": {
            "programCode": "DIMP-2024-001",
            "scope": "Migrate 150+ applications to government cloud",
            "budget": "250M SAR",
            "targetCompletion": "2026-12-31",
            "phases": 3,
        },
    },
    {
        "ref": "init_api_platform",
        "type": "Initiative",
        "subtype": "program",
        "name": "Enterprise API Platform Initiative (EAPI)",
        "parent": "obj_api_platform",
        "attributes": {
            "programCode": "EAPI-2024-002",
            "scope": "Build API platform, publish 500+ APIs, onboard 100 agencies",
            "budget": "80M SAR",
            "targetCompletion": "2025-12-31",
            "phases": 2,
        },
    },
    {
        "ref": "init_data_lake",
        "type": "Initiative",
        "subtype": "program",
        "name": "Enterprise Data Lake Program (EDL)",
        "parent": "obj_data_lake",
        "attributes": {
            "programCode": "EDL-2024-003",
            "scope": "Build data lake, integrate 50+ data sources, enable real-time analytics",
            "budget": "180M SAR",
            "targetCompletion": "2025-12-31",
            "phases": 3,
        },
    },
    {
        "ref": "init_zero_trust",
        "type": "Initiative",
        "subtype": "program",
        "name": "Zero Trust Security Architecture (ZTSA)",
        "parent": "obj_zero_trust",
        "attributes": {
            "programCode": "ZTSA-2024-004",
            "scope": "Implement zero trust across all systems and users",
            "budget": "130M SAR",
            "targetCompletion": "2026-12-31",
            "phases": 4,
        },
    },
    {
        "ref": "init_citizen_experience",
        "type": "Initiative",
        "subtype": "program",
        "name": "Citizen Experience Excellence Program (CEEP)",
        "parent": "obj_omnichannel",
        "attributes": {
            "programCode": "CEEP-2024-005",
            "scope": "Redesign all citizen touchpoints for seamless omnichannel experience",
            "budget": "90M SAR",
            "targetCompletion": "2025-12-31",
            "phases": 2,
        },
    },
]

# ════════════════════════════════════════════════════════════════════════════
# EA MATURITY SELF-ASSESSMENT (Qiyas/CMMI 1-5 Scale)
# ════════════════════════════════════════════════════════════════════════════

# The maturity dimensions themselves are the 10 built-in ones seeded by
# ensure_framework_profile() (app.services.maturity.DEFAULT_MATURITY_DIMENSIONS).
# We do NOT create dimensions here — we score the existing catalogue. Keys must
# match the built-in dimension keys exactly.
BUILTIN_DIMENSION_KEYS = [
    "governance",
    "business_architecture",
    "application_architecture",
    "data_architecture",
    "technology_architecture",
    "security_compliance",
    "methodology",
    "performance",
    "change_transition",
    "national_alignment",
]

# Improvement trajectory per built-in dimension across the 5 assessment runs
# (Q1 2024 → Q1 2025). Each list is [q1'24, q2'24, q3'24, q4'24, q1'25] on the
# CMMI/Qiyas 1–5 scale, telling a credible "climbing the maturity curve" story.
MATURITY_TRAJECTORY = {
    "governance": [2, 2, 3, 3, 4],
    "business_architecture": [1, 2, 2, 3, 3],
    "application_architecture": [1, 2, 2, 3, 4],
    "data_architecture": [1, 2, 3, 3, 4],
    "technology_architecture": [1, 2, 3, 3, 4],
    "security_compliance": [2, 3, 3, 4, 5],
    "methodology": [1, 2, 3, 3, 4],
    "performance": [1, 1, 2, 2, 3],
    "change_transition": [1, 2, 2, 3, 3],
    "national_alignment": [2, 2, 3, 4, 4],
}

# Assessment runs over 12 months (showing improvement trajectory)
MATURITY_ASSESSMENTS = [
    {
        "ref": "assess_baseline_q1",
        "title": "Q1 2024 Baseline Assessment",
        "assessment_date": date(2024, 3, 31),
        "status": "approved",
    },
    {
        "ref": "assess_q2_2024",
        "title": "Q2 2024 Progress Assessment",
        "assessment_date": date(2024, 6, 30),
        "status": "approved",
    },
    {
        "ref": "assess_q3_2024",
        "title": "Q3 2024 Progress Assessment",
        "assessment_date": date(2024, 9, 30),
        "status": "approved",
    },
    {
        "ref": "assess_q4_2024",
        "title": "Q4 2024 Progress Assessment",
        "assessment_date": date(2024, 12, 31),
        "status": "approved",
    },
    {
        "ref": "assess_q1_2025",
        "title": "Q1 2025 Latest Assessment",
        "assessment_date": date(2025, 3, 31),
        "status": "submitted",
    },
]

# Per-assessment score notes keyed by the ordinal level reached (1-5), so the
# audit trail reads sensibly at every maturity stage.
LEVEL_NOTES = {
    1: "Ad-hoc / initial — no repeatable practice yet",
    2: "Developing — framework defined, partial adoption",
    3: "Defined — documented and followed in new work",
    4: "Managed — measured, enforced enterprise-wide",
    5: "Optimized — continuously improved, best-in-class",
}


# ════════════════════════════════════════════════════════════════════════════
# SEED FUNCTION
# ════════════════════════════════════════════════════════════════════════════


async def seed_strategic_house_and_maturity(db: AsyncSession) -> dict:
    """Seed Strategic House + EA Maturity Assessment data.

    Creates:
    - Vision + Mission as agency settings (general_settings.noraVision/noraMission)
    - 6 Strategic Pillars (Pillar cards)
    - 15 Objectives (3-5 per pillar), each linked to its pillar via the
      relObjectiveToPillar "supports" relation — what the cascade report reads
    - 5 Strategic Initiatives (Initiative cards, program subtype)
    - 5 Assessment runs (Q1 2024 → Q1 2025) scored against the 10 built-in
      maturity dimensions → 50 dimension scores (improvement trajectory)

    Idempotent: skips if the seed's signature Pillar already exists. Dimensions
    are NOT created here — they are the built-in catalogue seeded by
    ensure_framework_profile(); we score the existing dimensions.
    """
    # Idempotency: signature Pillar card
    existing = await db.execute(
        select(Card.id)
        .where(Card.type == "Pillar", Card.name == "Digital Innovation & Technology")
        .limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        return {"skipped": True, "reason": "Strategic House & Maturity data already seeded"}

    # ─── PHASE 0: Vision & Mission → settings (the roof + band of the house) ───
    settings_row = (
        await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    ).scalar_one_or_none()
    if settings_row is None:
        settings_row = AppSettings(id="default", email_settings={})
        db.add(settings_row)
        await db.flush()
    general = dict(settings_row.general_settings or {})
    general["noraVision"] = VISION_TEXT
    general["noraMission"] = MISSION_TEXT
    settings_row.general_settings = general

    cards: dict[str, Card] = {}

    # ─── PHASE 1: Pillar cards ───
    for spec in STRATEGIC_PILLARS_EXTENDED:
        card = Card(type=spec["type"], name=spec["name"], attributes=spec.get("attributes", {}))
        db.add(card)
        await db.flush()
        cards[spec["ref"]] = card

    # ─── PHASE 2: Objective cards (parent stays null — pillar link is a relation) ───
    objective_specs = sum(STRATEGIC_OBJECTIVES_BY_PILLAR.values(), [])
    for spec in objective_specs:
        card = Card(type=spec["type"], name=spec["name"], attributes=spec.get("attributes", {}))
        db.add(card)
        await db.flush()
        cards[spec["ref"]] = card

    # ─── PHASE 3: Initiative cards (standalone programs) ───
    for spec in STRATEGIC_INITIATIVES:
        card = Card(
            type=spec["type"],
            subtype=spec.get("subtype"),
            name=spec["name"],
            attributes=spec.get("attributes", {}),
        )
        db.add(card)
        await db.flush()
        cards[spec["ref"]] = card

    # ─── PHASE 4: Objective → Pillar "supports" relations (what the cascade reads) ───
    relation_count = 0
    for pillar_ref, objs in STRATEGIC_OBJECTIVES_BY_PILLAR.items():
        pillar = cards.get(pillar_ref)
        if pillar is None:
            continue
        for obj_spec in objs:
            obj = cards.get(obj_spec["ref"])
            if obj is None:
                continue
            db.add(
                Relation(
                    type="relObjectiveToPillar",
                    source_id=obj.id,
                    target_id=pillar.id,
                    attributes={},
                )
            )
            relation_count += 1

    # ─── PHASE 5: Maturity assessments + scores against the built-in dimensions ───
    dims = (
        (
            await db.execute(
                select(MaturityDimension).where(MaturityDimension.key.in_(BUILTIN_DIMENSION_KEYS))
            )
        )
        .scalars()
        .all()
    )
    dim_by_key = {d.key: d for d in dims}

    assess_by_ref: dict[str, MaturityAssessment] = {}
    for idx, assess_spec in enumerate(MATURITY_ASSESSMENTS):
        assess = MaturityAssessment(
            title=assess_spec["title"],
            assessment_date=assess_spec["assessment_date"],
            status=assess_spec["status"],
            notes=f"Assessment for {assess_spec['assessment_date'].strftime('%B %Y')}",
        )
        db.add(assess)
        await db.flush()
        assess_by_ref[assess_spec["ref"]] = assess

    score_count = 0
    overall_by_ref: dict[str, list[MaturityDimensionScore]] = {}
    for idx, assess_spec in enumerate(MATURITY_ASSESSMENTS):
        assess = assess_by_ref[assess_spec["ref"]]
        run_scores: list[MaturityDimensionScore] = []
        for dim_key in BUILTIN_DIMENSION_KEYS:
            dim = dim_by_key.get(dim_key)
            if dim is None:
                continue  # built-in dimension missing — should not happen post-profile
            level = MATURITY_TRAJECTORY[dim_key][idx]
            score = MaturityDimensionScore(
                assessment_id=assess.id,
                dimension_id=dim.id,
                dimension_key=dim.key,
                dimension_name=dim.name,
                weight=dim.weight,
                sort_order=dim.sort_order,
                level=level,
                target_level=5,
                notes=LEVEL_NOTES.get(level),
            )
            db.add(score)
            run_scores.append(score)
            score_count += 1
        overall_by_ref[assess_spec["ref"]] = run_scores

    # Compute + store the weighted overall score per assessment (0–100).
    for ref, run_scores in overall_by_ref.items():
        assess = assess_by_ref[ref]
        assess.overall_score = compute_overall_score(run_scores)

    await db.commit()

    return {
        "loaded": True,
        "pillars": len(STRATEGIC_PILLARS_EXTENDED),
        "objectives": len(objective_specs),
        "initiatives": len(STRATEGIC_INITIATIVES),
        "strategic_house_cards": len(cards),
        "objective_pillar_relations": relation_count,
        "maturity_dimensions_scored": len(dim_by_key),
        "maturity_assessments": len(MATURITY_ASSESSMENTS),
        "maturity_scores": score_count,
        "validation": "strategic_house_and_maturity_complete",
    }
