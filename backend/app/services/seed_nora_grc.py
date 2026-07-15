"""NORA GRC seed — Risks, Compliance findings, Decisions (ADRs).

[FORK FEATURE] — Populates the GRC page (Governance / Risk / Compliance) with
10 realistic government-EA examples of each, so a fresh ``SEED_NORA=true`` boot
lands users on fully-populated GRC tabs:

* 10 Risks (EA Risk Register — varied category / probability / impact / status)
* 10 Compliance findings (landscape-scoped across the six built-in regulations,
  so they land regardless of which landscape cards are present)
* 10 Architecture Decisions / ADRs (governance)

Principles + Standards are seeded separately from the authoritative Saudi
Government EA catalog — see ``seed_saudi_ea_catalog``.

Each section is independently idempotent (guarded by a marker), so a re-run adds
only what's missing and never duplicates. References (R-NNNNNN, ADR-NNN) are
computed in-memory off the current max so batch inserts stay unique.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.architecture_decision import ArchitectureDecision
from app.models.risk import Risk
from app.models.turbolens import TurboLensAnalysisRun, TurboLensComplianceFinding
from app.models.user import User
from app.services.compliance_scanner import compute_finding_key
from app.services.risk_service import derive_level

# ════════════════════════════════════════════════════════════════════════════
# RISKS (EA Risk Register) — 10 entries
# ════════════════════════════════════════════════════════════════════════════
# category:    security | compliance | operational | technology | financial
#              | reputational | strategic
# probability: very_high | high | medium | low
# impact:      critical | high | medium | low
# status:      identified | analysed | mitigation_planned | in_progress
#              | mitigated | monitoring | accepted | closed
RISKS: list[dict] = [
    {
        "title": "Legacy licensing platform end-of-life",
        "description": (
            "The core commercial-registration licensing platform runs on an "
            "unsupported application server with no vendor security patches, "
            "creating exposure across every dependent government service."
        ),
        "category": "technology",
        "initial_probability": "high",
        "initial_impact": "critical",
        "residual_probability": "medium",
        "residual_impact": "high",
        "status": "in_progress",
        "days_out": 120,
    },
    {
        "title": "Cross-agency data sharing without signed DPAs",
        "description": (
            "Several inter-agency data exchanges operate on informal "
            "agreements, exposing the entity to PDPL non-compliance if "
            "personal data is transferred without a data-processing agreement."
        ),
        "category": "compliance",
        "initial_probability": "high",
        "initial_impact": "high",
        "residual_probability": "medium",
        "residual_impact": "medium",
        "status": "mitigation_planned",
        "days_out": 90,
    },
    {
        "title": "Single point of failure in national identity gateway",
        "description": (
            "The national identity verification gateway has no active-active "
            "redundancy; an outage would halt authentication across all "
            "citizen-facing digital services."
        ),
        "category": "operational",
        "initial_probability": "medium",
        "initial_impact": "critical",
        "residual_probability": "low",
        "residual_impact": "high",
        "status": "monitoring",
        "days_out": 60,
    },
    {
        "title": "Unencrypted PII at rest in reporting warehouse",
        "description": (
            "The analytics reporting warehouse stores beneficiary personal "
            "data without transparent data encryption, breaching the entity's "
            "information-security baseline."
        ),
        "category": "security",
        "initial_probability": "medium",
        "initial_impact": "high",
        "residual_probability": "low",
        "residual_impact": "medium",
        "status": "mitigated",
        "days_out": 30,
    },
    {
        "title": "Cloud migration budget overrun",
        "description": (
            "The government-cloud migration programme is trending 25% over "
            "budget due to unplanned data-egress and re-platforming costs, "
            "threatening delivery of later transformation phases."
        ),
        "category": "financial",
        "initial_probability": "high",
        "initial_impact": "medium",
        "residual_probability": "medium",
        "residual_impact": "medium",
        "status": "analysed",
        "days_out": 180,
    },
    {
        "title": "Shadow AI use in citizen correspondence",
        "description": (
            "Business units are using unapproved generative-AI tools to draft "
            "citizen correspondence, risking EU AI Act transparency breaches "
            "and leakage of confidential case data."
        ),
        "category": "compliance",
        "initial_probability": "high",
        "initial_impact": "high",
        "residual_probability": "medium",
        "residual_impact": "medium",
        "status": "identified",
        "days_out": 45,
    },
    {
        "title": "Vendor concentration on a single hyperscaler",
        "description": (
            "Over 80% of production workloads depend on one cloud provider "
            "with no documented exit strategy, creating strategic lock-in and "
            "DORA third-party-risk exposure."
        ),
        "category": "strategic",
        "initial_probability": "medium",
        "initial_impact": "high",
        "residual_probability": "medium",
        "residual_impact": "medium",
        "status": "mitigation_planned",
        "days_out": 240,
    },
    {
        "title": "Inconsistent service data quality erodes trust",
        "description": (
            "Duplicate and stale records across the service catalogue lead to "
            "incorrect citizen information, risking reputational damage and "
            "increased call-centre load."
        ),
        "category": "reputational",
        "initial_probability": "high",
        "initial_impact": "medium",
        "residual_probability": "medium",
        "residual_impact": "low",
        "status": "in_progress",
        "days_out": 75,
    },
    {
        "title": "Insufficient EA governance over new initiatives",
        "description": (
            "New digital initiatives bypass the architecture review board, "
            "producing point solutions that increase integration debt and "
            "diverge from the target architecture."
        ),
        "category": "operational",
        "initial_probability": "high",
        "initial_impact": "medium",
        "residual_probability": "medium",
        "residual_impact": "medium",
        "status": "accepted",
        "days_out": None,
    },
    {
        "title": "Delayed patching of internet-facing firewalls",
        "description": (
            "Perimeter firewalls protecting public services are running a "
            "known-exploited SSL-VPN vulnerability, exposing the entity to "
            "NIS2-relevant intrusion and service disruption."
        ),
        "category": "security",
        "initial_probability": "very_high",
        "initial_impact": "critical",
        "residual_probability": "medium",
        "residual_impact": "high",
        "status": "in_progress",
        "days_out": 14,
    },
]

# ════════════════════════════════════════════════════════════════════════════
# COMPLIANCE FINDINGS — 10 landscape-scoped entries across all six regulations
# ════════════════════════════════════════════════════════════════════════════
# regulation: eu_ai_act | gdpr | nis2 | dora | soc2 | iso27001
#             | pdpl | nca_ecc | ndmo_dm | dga_policy
# severity:   critical | high | medium | low | info
# status:     non_compliant | partial | compliant | not_applicable | review_needed
# decision:   new | in_review | accepted | mitigated | verified | not_applicable
GRC_COMPLIANCE_FINDINGS: list[dict] = [
    {
        "regulation": "eu_ai_act",
        "regulation_article": "Art. 52",
        "category": "transparency_obligations",
        "severity": "high",
        "status": "non_compliant",
        "decision": "new",
        "ai_detected": True,
        "requirement": (
            "Article 52 requires that natural persons are informed when they "
            "interact with an AI system, unless it is obvious from context."
        ),
        "gap_description": (
            "The citizen chatbot does not disclose that responses are "
            "AI-generated, and no fallback to a human agent is documented."
        ),
        "evidence": "Landscape review of AI-tagged citizen channels, 2025-Q2.",
        "remediation": (
            "Add an explicit AI-disclosure banner to the chatbot and a "
            "documented human-handover path."
        ),
    },
    {
        "regulation": "gdpr",
        "regulation_article": "Art. 5",
        "category": "data_minimisation",
        "severity": "medium",
        "status": "partial",
        "decision": "in_review",
        "requirement": (
            "Article 5(1)(c) requires personal data to be adequate, relevant "
            "and limited to what is necessary (data minimisation)."
        ),
        "gap_description": (
            "Several service intake forms collect national ID copies where a "
            "verified attribute assertion would suffice."
        ),
        "evidence": "Form inventory audit, 2025-Q1.",
        "remediation": (
            "Replace document upload with attribute-based verification via the "
            "national identity gateway."
        ),
    },
    {
        "regulation": "nis2",
        "regulation_article": "Art. 21",
        "category": "supply_chain_security",
        "severity": "high",
        "status": "non_compliant",
        "decision": "new",
        "requirement": (
            "Article 21 requires appropriate supply-chain security measures, "
            "including addressing vulnerabilities of direct suppliers."
        ),
        "gap_description": (
            "No software bill of materials (SBOM) is maintained for critical "
            "citizen-facing applications, so upstream vulnerabilities cannot "
            "be traced."
        ),
        "evidence": "Landscape scan of application dependency inventory.",
        "remediation": (
            "Mandate SBOM generation in the CI pipeline and integrate with the "
            "vulnerability-management process."
        ),
    },
    {
        "regulation": "dora",
        "regulation_article": "Art. 11",
        "category": "business_continuity",
        "severity": "critical",
        "status": "non_compliant",
        "decision": "new",
        "requirement": (
            "Article 11 requires ICT business-continuity and disaster-recovery "
            "plans that are tested at least yearly."
        ),
        "gap_description": (
            "The payment-settlement workload has an untested recovery plan and "
            "no defined RTO/RPO, threatening continuity of revenue services."
        ),
        "evidence": "DR programme review, 2025-Q1.",
        "remediation": (
            "Define RTO/RPO, run an annual failover drill and record the "
            "results in the continuity register."
        ),
    },
    {
        "regulation": "soc2",
        "regulation_article": "CC6.6",
        "category": "boundary_protection",
        "severity": "medium",
        "status": "partial",
        "decision": "new",
        "requirement": (
            "CC6.6: The entity implements logical access controls to protect "
            "against threats from sources outside its system boundaries."
        ),
        "gap_description": (
            "Administrative interfaces of two internal platforms are reachable "
            "from the corporate network without MFA enforcement."
        ),
        "evidence": "Internal access review, 2025-Q2.",
        "remediation": "Enforce MFA and network segmentation for all admin planes.",
    },
    {
        "regulation": "iso27001",
        "regulation_article": "A.8.16",
        "category": "monitoring_activities",
        "severity": "medium",
        "status": "partial",
        "decision": "in_review",
        "requirement": (
            "Annex A.8.16 requires networks, systems and applications to be "
            "monitored for anomalous behaviour."
        ),
        "gap_description": (
            "Central log aggregation covers infrastructure but not the "
            "application layer of several government services."
        ),
        "evidence": "SIEM coverage matrix, 2025-Q1.",
        "remediation": "Onboard application audit logs into the central SIEM.",
    },
    {
        "regulation": "gdpr",
        "regulation_article": "Art. 25",
        "category": "data_protection_by_design",
        "severity": "medium",
        "status": "partial",
        "decision": "new",
        "requirement": (
            "Article 25 requires data protection by design and by default in processing activities."
        ),
        "gap_description": (
            "New services are launched without a privacy-by-design checklist "
            "in the architecture review gate."
        ),
        "evidence": "Architecture review board records, 2025-Q1.",
        "remediation": ("Add a privacy-by-design gate to the initiative approval workflow."),
    },
    {
        "regulation": "eu_ai_act",
        "regulation_article": "Art. 10",
        "category": "data_governance",
        "severity": "medium",
        "status": "review_needed",
        "decision": "in_review",
        "ai_detected": True,
        "requirement": (
            "Article 10 requires high-risk AI systems to be trained on data "
            "governed by appropriate data-management practices."
        ),
        "gap_description": (
            "The eligibility-scoring model lacks documented training-data "
            "lineage and bias-testing evidence."
        ),
        "evidence": "Model registry review, 2025-Q2.",
        "remediation": (
            "Document data lineage, run bias tests and attach the results to the model card."
        ),
    },
    {
        "regulation": "nis2",
        "regulation_article": "Art. 23",
        "category": "incident_reporting",
        "severity": "high",
        "status": "non_compliant",
        "decision": "new",
        "requirement": (
            "Article 23 requires significant incidents to be reported to the "
            "national CSIRT within defined timeframes."
        ),
        "gap_description": (
            "No documented 24-hour early-warning reporting procedure exists "
            "for significant incidents affecting essential services."
        ),
        "evidence": "Incident-response playbook review, 2025-Q1.",
        "remediation": (
            "Establish a 24h/72h reporting runbook aligned to the national "
            "CSIRT template and run a tabletop exercise."
        ),
    },
    {
        "regulation": "soc2",
        "regulation_article": "CC8.1",
        "category": "change_management",
        "severity": "info",
        "status": "compliant",
        "decision": "verified",
        "requirement": (
            "CC8.1: The entity authorises, designs, tests and approves changes "
            "to infrastructure, data and software."
        ),
        "gap_description": (
            "Change-management controls are operating effectively across the "
            "platform estate — retained here as an attestation record."
        ),
        "evidence": "Change advisory board minutes, 2025-Q1; no exceptions.",
        "remediation": "None — control verified as effective.",
    },
    # ── Saudi Government regulations (PDPL, NCA ECC, NDMO, DGA) ──────────────
    {
        "regulation": "pdpl",
        "regulation_article": "Art. 12",
        "category": "lawful_basis",
        "severity": "info",
        "status": "compliant",
        "decision": "verified",
        "requirement": (
            "Article 12 requires a documented legal basis and, where applicable, "
            "the data subject's consent before processing personal data."
        ),
        "gap_description": (
            "A legal basis is recorded per processing activity and consent is "
            "captured where relied upon — retained here as an attestation record."
        ),
        "evidence": "PDPL readiness assessment of citizen-facing services, 2025-Q2; no exceptions.",
        "remediation": "None — control verified as effective.",
    },
    {
        "regulation": "pdpl",
        "regulation_article": "Art. 18",
        "category": "data_subject_rights",
        "severity": "info",
        "status": "compliant",
        "decision": "verified",
        "requirement": (
            "Article 18 grants data subjects the right to access, correct and "
            "request deletion of their personal data."
        ),
        "gap_description": (
            "A data-subject-request procedure with a 30-day SLA is published and "
            "requests are handled through a tracked workflow — attestation record."
        ),
        "evidence": "Data-subject-request log review, 2025-Q1; no exceptions.",
        "remediation": "None — control verified as effective.",
    },
    {
        "regulation": "nca_ecc",
        "regulation_article": "ECC 2-2-3",
        "category": "identity_and_access",
        "severity": "high",
        "status": "non_compliant",
        "decision": "new",
        "requirement": (
            "ECC 2-2-3 requires multi-factor authentication for remote and "
            "privileged access to information assets."
        ),
        "gap_description": (
            "Privileged administrative access to two government platforms relies "
            "on single-factor credentials."
        ),
        "evidence": "Privileged-access review against NCA ECC, 2025-Q2.",
        "remediation": "Enforce MFA on all remote and privileged access paths.",
    },
    {
        "regulation": "nca_ecc",
        "regulation_article": "ECC 2-12-1",
        "category": "resilience",
        "severity": "medium",
        "status": "partial",
        "decision": "in_review",
        "requirement": (
            "ECC 2-12-1 requires cybersecurity resilience requirements to be "
            "embedded in business-continuity management."
        ),
        "gap_description": (
            "Continuity plans exist for infrastructure but do not yet cover "
            "cyber-incident recovery scenarios for essential services."
        ),
        "evidence": "Business-continuity programme review, 2025-Q1.",
        "remediation": (
            "Add cyber-incident recovery playbooks to the continuity plans and test them annually."
        ),
    },
    {
        "regulation": "ndmo_dm",
        "regulation_article": "DG 1.3",
        "category": "data_governance",
        "severity": "medium",
        "status": "partial",
        "decision": "new",
        "requirement": (
            "NDMO Data Governance requires each data domain to have an accountable "
            "data owner and a maintained data catalogue."
        ),
        "gap_description": (
            "Data ownership is assigned for master data but the enterprise data "
            "catalogue is incomplete for operational domains."
        ),
        "evidence": "NDMO data-management maturity assessment, 2025-Q2.",
        "remediation": (
            "Complete the data catalogue for all operational domains and confirm "
            "accountable owners."
        ),
    },
    {
        "regulation": "ndmo_dm",
        "regulation_article": "PDP 2.1",
        "category": "personal_data_protection",
        "severity": "high",
        "status": "non_compliant",
        "decision": "new",
        "requirement": (
            "NDMO Personal Data Protection standards require classification of "
            "personal data and controls proportionate to its sensitivity."
        ),
        "gap_description": (
            "Personal data is not consistently classified, so protection controls "
            "cannot be applied by sensitivity tier."
        ),
        "evidence": "Data-classification coverage review, 2025-Q1.",
        "remediation": (
            "Roll out the national data-classification scheme and tag personal "
            "data stores accordingly."
        ),
    },
    {
        "regulation": "dga_policy",
        "regulation_article": "DGA-INT-01",
        "category": "interoperability",
        "severity": "medium",
        "status": "review_needed",
        "decision": "in_review",
        "requirement": (
            "DGA digital-government policy requires new services to integrate "
            "through the national integration and API platform."
        ),
        "gap_description": (
            "Two recently launched services expose point-to-point integrations "
            "that bypass the national API gateway."
        ),
        "evidence": "DGA policy conformance review, 2025-Q2.",
        "remediation": (
            "Re-platform the integrations onto the national API gateway and "
            "register the APIs in the catalogue."
        ),
    },
    {
        "regulation": "dga_policy",
        "regulation_article": "DGA-OPEN-02",
        "category": "open_data",
        "severity": "info",
        "status": "compliant",
        "decision": "verified",
        "requirement": (
            "DGA policy requires eligible non-sensitive datasets to be published "
            "as open data on the national open-data portal."
        ),
        "gap_description": (
            "Eligible datasets are published on the national open-data portal on "
            "the agreed cadence — retained here as an attestation record."
        ),
        "evidence": "Open-data portal publication log, 2025-Q1; no exceptions.",
        "remediation": "None — control verified as effective.",
    },
]

# ════════════════════════════════════════════════════════════════════════════
# ARCHITECTURE DECISIONS (Governance) — 10 entries
# ════════════════════════════════════════════════════════════════════════════
# status: draft | in_review | signed
GRC_DECISIONS: list[dict] = [
    {
        "title": "Adopt API-first integration for all new services",
        "status": "signed",
        "committee": "Architecture Review Board",
        "context": (
            "Point-to-point integrations have created brittle, undocumented "
            "coupling across the landscape."
        ),
        "decision": (
            "All new inter-system integration must be delivered as versioned, "
            "documented APIs published on the national API gateway."
        ),
        "consequences": (
            "Higher initial design effort, offset by reuse, observability and "
            "reduced integration debt."
        ),
        "alternatives_considered": (
            "Continue with file-based batch exchanges (rejected: opaque, "
            "slow); an enterprise service bus (rejected: central bottleneck)."
        ),
    },
    {
        "title": "Standardise on government cloud as default host",
        "status": "signed",
        "committee": "Architecture Review Board",
        "context": (
            "Fragmented hosting across ageing data centres increases cost and operational risk."
        ),
        "decision": (
            "New and re-platformed workloads target the approved government "
            "cloud unless a justified exception is granted."
        ),
        "consequences": (
            "Requires cloud-skills uplift and landing-zone guardrails; "
            "delivers elasticity and resilience."
        ),
        "alternatives_considered": (
            "Maintain on-premises hosting (rejected: cost, agility); "
            "multi-cloud from day one (deferred: complexity)."
        ),
    },
    {
        "title": "Use the national identity gateway for authentication",
        "status": "signed",
        "committee": "Architecture Review Board",
        "context": (
            "Multiple bespoke authentication implementations increase attack "
            "surface and user friction."
        ),
        "decision": (
            "All citizen-facing services authenticate via the national "
            "identity gateway; local credential stores are prohibited."
        ),
        "consequences": (
            "Consistent, MFA-backed sign-in; a dependency on gateway "
            "availability that must be designed for."
        ),
        "alternatives_considered": (
            "Per-service identity providers (rejected: inconsistent, costly)."
        ),
    },
    {
        "title": "Establish a master-data management domain model",
        "status": "in_review",
        "committee": "Data Governance Council",
        "context": (
            "Conflicting versions of organisation and person data undermine service reliability."
        ),
        "decision": (
            "Adopt a domain-oriented MDM approach with an assigned data owner "
            "and authoritative system of record per domain."
        ),
        "consequences": (
            "Clear ownership and data quality; requires governance effort and consumer migration."
        ),
        "alternatives_considered": (
            "Continue federated ownership (rejected: perpetuates duplication)."
        ),
    },
    {
        "title": "Mandate SBOM generation in delivery pipelines",
        "status": "signed",
        "committee": "Security Architecture Board",
        "context": (
            "Upstream software vulnerabilities cannot be traced without a "
            "software bill of materials."
        ),
        "decision": (
            "Every build pipeline must generate and publish an SBOM consumed "
            "by the vulnerability-management process."
        ),
        "consequences": ("Faster response to supply-chain CVEs; minor pipeline overhead."),
        "alternatives_considered": ("Manual dependency reviews (rejected: not scalable)."),
    },
    {
        "title": "Retire the legacy licensing application server",
        "status": "in_review",
        "committee": "Architecture Review Board",
        "context": (
            "The licensing platform runs on an unsupported application server "
            "with no security patches."
        ),
        "decision": (
            "Re-platform the licensing service onto the supported cloud "
            "runtime within the current fiscal year."
        ),
        "consequences": (
            "Removes a critical vulnerability; requires a migration window and regression testing."
        ),
        "alternatives_considered": (
            "Extend vendor support (rejected: unavailable); accept the risk "
            "(rejected: severity too high)."
        ),
    },
    {
        "title": "Adopt event-driven pattern for cross-agency notifications",
        "status": "draft",
        "committee": "Architecture Review Board",
        "context": ("Synchronous cross-agency calls create tight coupling and cascade failures."),
        "decision": (
            "Use a governed event backbone for asynchronous notifications "
            "between agencies where eventual consistency is acceptable."
        ),
        "consequences": ("Improved resilience and decoupling; requires event-schema governance."),
        "alternatives_considered": (
            "Continue synchronous REST calls (rejected: fragile at scale)."
        ),
    },
    {
        "title": "Require privacy-by-design gate in initiative approval",
        "status": "signed",
        "committee": "Data Governance Council",
        "context": ("Privacy considerations were being addressed too late in delivery."),
        "decision": (
            "Add a mandatory privacy-by-design assessment to the initiative "
            "approval workflow before build commences."
        ),
        "consequences": ("Earlier risk detection; a small addition to the approval lead time."),
        "alternatives_considered": (
            "Post-launch privacy audits only (rejected: too late to fix cheaply)."
        ),
    },
    {
        "title": "Consolidate observability on a single SIEM",
        "status": "signed",
        "committee": "Security Architecture Board",
        "context": ("Fragmented monitoring leaves application-layer blind spots."),
        "decision": (
            "Route all infrastructure and application audit logs into the "
            "central SIEM with quarterly coverage reviews."
        ),
        "consequences": ("Comprehensive threat visibility; ingestion-cost management required."),
        "alternatives_considered": ("Per-team logging tools (rejected: no unified view)."),
    },
    {
        "title": "Define an exit strategy for the primary cloud provider",
        "status": "draft",
        "committee": "Architecture Review Board",
        "context": (
            "Heavy concentration on one hyperscaler creates strategic lock-in "
            "and DORA third-party exposure."
        ),
        "decision": (
            "Document a portability and exit strategy, and design new "
            "workloads to minimise provider-specific coupling."
        ),
        "consequences": ("Reduced lock-in risk; some designs forego provider-native conveniences."),
        "alternatives_considered": (
            "Accept single-provider dependency (rejected: regulatory and resilience concerns)."
        ),
    },
]


# ════════════════════════════════════════════════════════════════════════════
# SEED HELPERS
# ════════════════════════════════════════════════════════════════════════════
async def _seed_risks(db: AsyncSession, owner_id: uuid.UUID | None) -> int:
    """Insert the 10 register risks. Idempotent on the first risk's title."""
    marker = await db.execute(select(Risk.id).where(Risk.title == RISKS[0]["title"]).limit(1))
    if marker.scalar_one_or_none() is not None:
        return 0

    # Compute the starting reference number once, then increment in-memory.
    refs = (await db.execute(select(Risk.reference))).scalars().all()
    highest = 0
    for ref in refs:
        if ref and ref.startswith("R-"):
            try:
                highest = max(highest, int(ref[2:]))
            except ValueError:
                pass

    today = date.today()
    created = 0
    for i, r in enumerate(RISKS, start=1):
        residual_prob = r.get("residual_probability")
        residual_impact = r.get("residual_impact")
        days_out = r.get("days_out")
        db.add(
            Risk(
                reference=f"R-{highest + i:06d}",
                title=r["title"],
                description=r["description"],
                category=r["category"],
                source_type="manual",
                initial_probability=r["initial_probability"],
                initial_impact=r["initial_impact"],
                initial_level=derive_level(r["initial_probability"], r["initial_impact"]),
                residual_probability=residual_prob,
                residual_impact=residual_impact,
                residual_level=derive_level(residual_prob, residual_impact),
                owner_id=owner_id,
                target_resolution_date=(
                    today + timedelta(days=days_out) if days_out is not None else None
                ),
                status=r["status"],
                created_by=owner_id,
            )
        )
        created += 1
    return created


async def _seed_decisions(db: AsyncSession, owner_id: uuid.UUID | None) -> int:
    """Insert the 10 ADRs. Idempotent on the first title."""
    marker = await db.execute(
        select(ArchitectureDecision.id)
        .where(ArchitectureDecision.title == GRC_DECISIONS[0]["title"])
        .limit(1)
    )
    if marker.scalar_one_or_none() is not None:
        return 0

    refs = (await db.execute(select(ArchitectureDecision.reference_number))).scalars().all()
    highest = 0
    for ref in refs:
        if ref and ref.startswith("ADR-"):
            try:
                highest = max(highest, int(ref.replace("ADR-", "")))
            except ValueError:
                pass

    today = date.today()
    created = 0
    for i, d in enumerate(GRC_DECISIONS, start=1):
        db.add(
            ArchitectureDecision(
                reference_number=f"ADR-{highest + i:03d}",
                title=d["title"],
                status=d["status"],
                context=d.get("context"),
                decision=d.get("decision"),
                consequences=d.get("consequences"),
                alternatives_considered=d.get("alternatives_considered"),
                committee=d.get("committee"),
                meeting_date=today - timedelta(days=(len(GRC_DECISIONS) - i) * 14),
                created_by=owner_id,
            )
        )
        created += 1
    return created


async def _seed_compliance(db: AsyncSession) -> int:
    """Insert landscape-scoped compliance findings under one demo run.

    Idempotent per finding_key, so a re-run tops up only the findings that
    aren't already present (e.g. after new regulations are added to the seed)
    and coexists with the NexaTech demo findings from seed_demo_security.
    """
    # Which of the seed's finding_keys already exist? Skip those; add the rest.
    keys = {
        compute_finding_key("landscape", None, f["regulation"], f.get("regulation_article")): f
        for f in GRC_COMPLIANCE_FINDINGS
    }
    existing = await db.execute(
        select(TurboLensComplianceFinding.finding_key).where(
            TurboLensComplianceFinding.finding_key.in_(list(keys.keys()))
        )
    )
    existing_keys = {row[0] for row in existing.all()}
    missing = {k: f for k, f in keys.items() if k not in existing_keys}
    if not missing:
        return 0

    now = datetime.now(timezone.utc)
    run = TurboLensAnalysisRun(
        id=uuid.uuid4(),
        analysis_type="compliance",
        status="completed",
        started_at=now,
        completed_at=now,
        results={
            "demo": True,
            "source": "nora_grc",
            "findings_count": len(missing),
        },
    )
    db.add(run)
    await db.flush()

    created = 0
    for key, f in missing.items():
        article = f.get("regulation_article")
        db.add(
            TurboLensComplianceFinding(
                id=uuid.uuid4(),
                run_id=run.id,
                regulation=f["regulation"],
                regulation_article=article,
                card_id=None,
                scope_type="landscape",
                category=f.get("category", ""),
                requirement=f.get("requirement", ""),
                status=f.get("status", "review_needed"),
                severity=f.get("severity", "info"),
                gap_description=f.get("gap_description", ""),
                evidence=f.get("evidence"),
                remediation=f.get("remediation"),
                ai_detected=f.get("ai_detected", False),
                finding_key=key,
                decision=f.get("decision", "new"),
                last_seen_run_id=run.id,
                auto_resolved=False,
            )
        )
        created += 1
    return created


# ════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════
async def seed_nora_grc(db: AsyncSession) -> dict:
    """Seed 10 examples each of Risks, Compliance findings, ADRs.

    Each section is independently idempotent, so a re-run tops up only what's
    missing. Returns per-section counts (0 = already present).
    """
    # Prefer an admin as owner/author; fall back to any user, then None.
    owner = (
        await db.execute(
            select(User).where(User.role == "admin", User.is_active.is_(True)).limit(1)
        )
    ).scalar_one_or_none()
    if owner is None:
        owner = (await db.execute(select(User).limit(1))).scalar_one_or_none()
    owner_id = owner.id if owner else None

    risks = await _seed_risks(db, owner_id)
    decisions = await _seed_decisions(db, owner_id)
    findings = await _seed_compliance(db)

    await db.commit()

    if not any((risks, decisions, findings)):
        return {"skipped": True, "reason": "GRC examples already seeded"}

    return {
        "loaded": True,
        "risks": risks,
        "compliance_findings": findings,
        "decisions": decisions,
    }
