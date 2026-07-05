"""NORA demo dataset — a fictional Saudi government agency landscape.

[FORK FEATURE] — populates every NORA view in one shot so a fresh install
can be evaluated without manual data entry:

* Government Services wired to processes, applications, capabilities and
  data (→ Service Traceability, Service Catalogue)
* NDMO-classified Data Objects + Data Exchanges incl. one **secret exchange
  off-GSB** (→ Interoperability report warning, WP4.4 scanner material)
* A current→target replacement pair + planned retirement (→ Gap Analysis)
* KPIs with green/amber/red values (→ KPI Scorecard)
* Program-tracker progress on Stages 1–3 with evidence links (→ NORA Program)
* An improvement opportunity in transition (→ GRC → Governance → Opportunities)
* A draft EA Project Strategy document (→ NORA governed documents)

Triggered by ``SEED_NORA=true`` (applies the NORA profile first, so it also
works on a fresh database). Idempotent: skips when the marker service
"Issue Commercial Registration" already exists. Names are fictional.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.improvement_opportunity import (
    ImprovementOpportunity,
    ImprovementOpportunityCard,
)
from app.models.nora_program import EaProgramDeliverable
from app.models.relation import Relation
from app.models.soaw import SoAW

MARKER_SERVICE = "Issue Commercial Registration"

# (ref, type, subtype, parent_ref, architecture_state, change_type,
#  successor_ref, attributes)
DEMO_CARDS: list[dict] = [
    # ── Organizations ────────────────────────────────────────────────
    {
        "ref": "org_root",
        "type": "Organization",
        "name": "Demo Ministry of Commerce",
        "attributes": {},
    },
    {
        "ref": "org_dt",
        "type": "Organization",
        "name": "Digital Transformation Deputyship",
        "parent": "org_root",
        "attributes": {},
    },
    {
        "ref": "org_bs",
        "type": "Organization",
        "name": "Business Services Deputyship",
        "parent": "org_root",
        "attributes": {},
    },
    # ── Objectives (PRM anchors) ─────────────────────────────────────
    {
        "ref": "obj_digital",
        "type": "Objective",
        "name": "Raise digital service adoption",
        "attributes": {"nationalAlignment": "Vision 2030 — Digital Government Program"},
    },
    {
        "ref": "obj_consolidate",
        "type": "Objective",
        "name": "Consolidate duplicated licensing systems",
        "attributes": {"nationalAlignment": "National Transformation Program"},
    },
    # ── Business capabilities (BRM levels) ───────────────────────────
    {
        "ref": "bc_business_services",
        "type": "BusinessCapability",
        "name": "Business Services",
        "attributes": {"brmLevel": "lineOfBusiness"},
    },
    {
        "ref": "bc_licensing",
        "type": "BusinessCapability",
        "name": "Licensing & Permits",
        "parent": "bc_business_services",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_inspection",
        "type": "BusinessCapability",
        "name": "Inspections & Enforcement",
        "parent": "bc_business_services",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_customer_engagement",
        "type": "BusinessCapability",
        "name": "Customer Engagement",
        "parent": "bc_business_services",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_data_analytics",
        "type": "BusinessCapability",
        "name": "Data & Analytics",
        "attributes": {"brmLevel": "lineOfBusiness"},
    },
    {
        "ref": "bc_licensing_issuance",
        "type": "BusinessCapability",
        "name": "Licence Issuance",
        "parent": "bc_licensing",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_licensing_renewal",
        "type": "BusinessCapability",
        "name": "Licence Renewal",
        "parent": "bc_licensing",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_case_intake",
        "type": "BusinessCapability",
        "name": "Case Intake",
        "parent": "bc_inspection",
        "attributes": {"brmLevel": "businessFunction"},
    },
    # ── Business processes ───────────────────────────────────────────
    {
        "ref": "proc_issue_cr",
        "type": "BusinessProcess",
        "name": "Commercial Registration Issuance",
        "subtype": "process",
        "attributes": {},
    },
    {
        "ref": "proc_inspection",
        "type": "BusinessProcess",
        "name": "Establishment Inspection",
        "subtype": "process",
        "attributes": {},
    },
    # ── Government services (the NORA Service Catalogue) ─────────────
    {
        "ref": "svc_issue_cr",
        "type": "GovService",
        "name": MARKER_SERVICE,
        "attributes": {
            "serviceCode": "MC-001",
            "beneficiaryType": ["business"],
            "deliveryChannel": ["portal", "mobileApp"],
            "serviceMaturity": "transactional",
            "feeModel": "paid",
            "slaDays": 1,
            "monthlyTransactions": 42000,
            "sharedServiceConsumer": True,
        },
    },
    {
        "ref": "svc_renew_cr",
        "type": "GovService",
        "name": "Renew Commercial Registration",
        "attributes": {
            "serviceCode": "MC-002",
            "beneficiaryType": ["business"],
            "deliveryChannel": ["portal", "mobileApp"],
            "serviceMaturity": "proactive",
            "feeModel": "paid",
            "slaDays": 1,
            "monthlyTransactions": 65000,
            "sharedServiceConsumer": True,
        },
    },
    {
        "ref": "svc_book_inspection",
        "type": "GovService",
        "name": "Book Inspection Appointment",
        "attributes": {
            "serviceCode": "MC-014",
            "beneficiaryType": ["business"],
            "deliveryChannel": ["portal", "callCenter"],
            "serviceMaturity": "interactive",
            "feeModel": "free",
            "slaDays": 3,
            "monthlyTransactions": 8000,
            "sharedServiceConsumer": False,
        },
    },
    {
        "ref": "svc_verify_cert",
        "type": "GovService",
        "name": "Verify Commercial Certificate",
        "attributes": {
            "serviceCode": "MC-020",
            "beneficiaryType": ["citizen", "business", "government"],
            "deliveryChannel": ["portal"],
            "serviceMaturity": "informational",
            "feeModel": "free",
            "monthlyTransactions": 120000,
            "sharedServiceConsumer": False,
        },
    },
    # ── Applications (incl. current → target replacement) ────────────
    {
        "ref": "app_cr_core",
        "type": "Application",
        "name": "CR Core System",
        "subtype": "businessApplication",
        "attributes": {
            "armCategory": "caseManagement",
            "automationLevel": "fullyAutomated",
            "sharedService": False,
            "armCode": "",
        },
    },
    {
        "ref": "app_legacy_licensing",
        "type": "Application",
        "name": "Legacy Licensing System",
        "subtype": "businessApplication",
        "attributes": {
            "armCategory": "caseManagement",
            "automationLevel": "partiallyAutomated",
            "sharedService": False,
        },
    },
    {
        "ref": "app_unified_licensing",
        "type": "Application",
        "name": "Unified Licensing Platform",
        "subtype": "businessApplication",
        "architecture_state": "target",
        "change_type": "replace",
        "successor": "app_legacy_licensing",
        "attributes": {
            "armCategory": "caseManagement",
            "automationLevel": "fullyAutomated",
            "sharedService": True,
        },
    },
    {
        "ref": "app_integration_layer",
        "type": "Application",
        "name": "National Integration Layer",
        "subtype": "microservice",
        "attributes": {
            "armCategory": "integration",
            "automationLevel": "fullyAutomated",
            "sharedService": True,
        },
    },
    {
        "ref": "app_fax_intake",
        "type": "Application",
        "name": "Fax Intake Desk",
        "subtype": "businessApplication",
        "change_type": "retire",
        "attributes": {"armCategory": "other", "automationLevel": "manual", "sharedService": False},
        "lifecycle": {"active": "2015-01-01", "phaseOut": "2026-01-01", "endOfLife": "2027-06-30"},
    },
    {
        "ref": "app_business_portal",
        "type": "Application",
        "name": "Business Services Portal",
        "subtype": "businessApplication",
        "attributes": {
            "armCategory": "crm",
            "automationLevel": "fullyAutomated",
            "sharedService": True,
            "businessCriticality": "missionCritical",
        },
        "lifecycle": {"plan": "2023-01-01", "phaseIn": "2023-06-01", "active": "2024-01-01"},
    },
    {
        "ref": "app_mobile_app",
        "type": "Application",
        "name": "Ministry Mobile App",
        "subtype": "businessApplication",
        "attributes": {
            "armCategory": "crm",
            "automationLevel": "fullyAutomated",
            "sharedService": False,
            "businessCriticality": "businessCritical",
        },
        "lifecycle": {"plan": "2023-06-01", "phaseIn": "2024-01-01", "active": "2024-09-01"},
    },
    {
        "ref": "app_analytics_studio",
        "type": "Application",
        "name": "Regulatory Analytics Studio",
        "subtype": "businessApplication",
        "attributes": {
            "armCategory": "analytics",
            "automationLevel": "partiallyAutomated",
            "sharedService": False,
            "businessCriticality": "businessOperational",
        },
        "lifecycle": {"active": "2022-04-01"},
    },
    {
        "ref": "app_workflow_engine",
        "type": "Application",
        "name": "Enterprise Workflow Engine",
        "subtype": "microservice",
        "attributes": {
            "armCategory": "integration",
            "automationLevel": "fullyAutomated",
            "sharedService": True,
            "businessCriticality": "missionCritical",
        },
        "lifecycle": {"active": "2021-10-01"},
    },
    # ── Interfaces (integration layer) ───────────────────────────────
    {
        "ref": "if_cr_public_api",
        "type": "Interface",
        "name": "CR Public REST API",
        "subtype": "api",
        "attributes": {
            "integrationType": "api",
            "protocol": "REST",
            "authenticationMethod": "OAuth2",
        },
        "lifecycle": {"active": "2024-03-01"},
    },
    {
        "ref": "if_verify_soap",
        "type": "Interface",
        "name": "Certificate Verification SOAP",
        "subtype": "logicalInterface",
        "attributes": {"integrationType": "api", "protocol": "SOAP"},
        "lifecycle": {"active": "2019-06-01", "phaseOut": "2027-01-01"},
    },
    {
        "ref": "if_ndb_events",
        "type": "Interface",
        "name": "NDB Realtime Event Stream",
        "subtype": "api",
        "attributes": {"integrationType": "event", "protocol": "Kafka"},
        "lifecycle": {"active": "2024-06-01"},
    },
    {
        "ref": "if_regulator_sftp",
        "type": "Interface",
        "name": "Regulator SFTP Feed",
        "subtype": "logicalInterface",
        "attributes": {"integrationType": "fileTransfer", "protocol": "SFTP"},
        "lifecycle": {"active": "2018-01-01"},
    },
    {
        "ref": "if_nightly_batch",
        "type": "Interface",
        "name": "Nightly Legacy Batch",
        "subtype": "logicalInterface",
        "attributes": {"integrationType": "batch", "protocol": "JDBC"},
        "lifecycle": {"active": "2016-05-01", "phaseOut": "2026-12-01"},
    },
    {
        "ref": "if_mobile_gateway",
        "type": "Interface",
        "name": "Mobile Gateway API",
        "subtype": "api",
        "attributes": {"integrationType": "api", "protocol": "GraphQL"},
        "lifecycle": {"active": "2024-09-01"},
    },
    # ── Data objects (NDMO classification) ───────────────────────────
    {
        "ref": "do_cr_record",
        "type": "DataObject",
        "name": "Commercial Registration Record",
        "attributes": {
            "dataClassification": "restricted",
            "piiFlag": False,
            "authoritativeSource": True,
            "retentionPeriod": "10 years",
        },
    },
    {
        "ref": "do_establishment",
        "type": "DataObject",
        "name": "Establishment Profile",
        "attributes": {
            "dataClassification": "restricted",
            "piiFlag": True,
            "authoritativeSource": False,
            "retentionPeriod": "10 years",
        },
    },
    {
        "ref": "do_inspection_report",
        "type": "DataObject",
        "name": "Inspection Report",
        "attributes": {
            "dataClassification": "secret",
            "piiFlag": True,
            "authoritativeSource": True,
            "retentionPeriod": "15 years",
        },
    },
    {
        "ref": "do_licence",
        "type": "DataObject",
        "name": "Business Licence",
        "attributes": {
            "dataClassification": "restricted",
            "piiFlag": False,
            "authoritativeSource": True,
            "retentionPeriod": "10 years",
        },
    },
    {
        "ref": "do_inspector",
        "type": "DataObject",
        "name": "Inspector Profile",
        "attributes": {
            "dataClassification": "restricted",
            "piiFlag": True,
            "authoritativeSource": True,
            "retentionPeriod": "5 years",
        },
    },
    {
        "ref": "do_audit_log",
        "type": "DataObject",
        "name": "Regulatory Audit Log",
        "attributes": {
            "dataClassification": "restricted",
            "piiFlag": False,
            "authoritativeSource": True,
            "retentionPeriod": "7 years",
        },
    },
    # ── Data exchanges (one secret exchange off-GSB → interop warning) ─
    {
        "ref": "dx_ndb_sync",
        "type": "DataExchange",
        "name": "CR Status Sync with National Data Bank",
        "attributes": {
            "exchangeMethod": "api",
            "frequency": "realtime",
            "viaGsb": True,
            "externalParty": "National Data Bank",
            "dataClassificationCarried": "restricted",
        },
    },
    {
        "ref": "dx_regulator_feed",
        "type": "DataExchange",
        "name": "Inspection Feed to Sector Regulator",
        "attributes": {
            "exchangeMethod": "fileTransfer",
            "frequency": "daily",
            "viaGsb": False,
            "externalParty": "Sector Regulator",
            "dataClassificationCarried": "secret",
        },
    },
    # ── IT components (incl. Database subtype) ───────────────────────
    {
        "ref": "itc_pg",
        "type": "ITComponent",
        "name": "PostgreSQL Cluster",
        "subtype": "database",
        "attributes": {"hostingModel": "governmentCloud", "securityZone": "Zone B"},
    },
    {
        "ref": "itc_k8s",
        "type": "ITComponent",
        "name": "Container Platform",
        "subtype": "paas",
        "attributes": {"hostingModel": "governmentCloud", "securityZone": "Zone B"},
    },
    {
        "ref": "itc_oracle_forms",
        "type": "ITComponent",
        "name": "Legacy Forms Runtime",
        "subtype": "software",
        "attributes": {"hostingModel": "onPremise", "securityZone": "Zone C"},
        "lifecycle": {"active": "2010-01-01", "phaseOut": "2026-06-01", "endOfLife": "2027-06-01"},
    },
    {
        "ref": "itc_redis",
        "type": "ITComponent",
        "name": "Session & Cache Grid",
        "subtype": "software",
        "attributes": {"hostingModel": "governmentCloud", "securityZone": "Zone B"},
        "lifecycle": {"active": "2023-05-01"},
    },
    {
        "ref": "itc_kafka",
        "type": "ITComponent",
        "name": "Event Streaming Bus",
        "subtype": "software",
        "attributes": {"hostingModel": "governmentCloud", "securityZone": "Zone B"},
        "lifecycle": {"active": "2024-01-01"},
    },
    {
        "ref": "itc_object_store",
        "type": "ITComponent",
        "name": "Regulated Object Storage",
        "subtype": "iaas",
        "attributes": {"hostingModel": "governmentCloud", "securityZone": "Zone B"},
        "lifecycle": {"active": "2022-11-01"},
    },
    # ── KPIs (green / amber / red on the scorecard) ──────────────────
    {
        "ref": "kpi_digital_share",
        "type": "KPI",
        "name": "% transactions via digital channels",
        "attributes": {
            "unit": "%",
            "baselineValue": 55,
            "targetValue": 92,
            "currentValue": 71,
            "measurementFrequency": "quarterly",
            "direction": "higherIsBetter",
        },
    },
    {
        "ref": "kpi_issuance_time",
        "type": "KPI",
        "name": "Average CR issuance time",
        "attributes": {
            "unit": "hours",
            "baselineValue": 48,
            "targetValue": 4,
            "currentValue": 6,
            "measurementFrequency": "monthly",
            "direction": "lowerIsBetter",
        },
    },
    {
        "ref": "kpi_retired_systems",
        "type": "KPI",
        "name": "Duplicated systems retired",
        "attributes": {
            "unit": "systems",
            "baselineValue": 0,
            "targetValue": 6,
            "currentValue": 1,
            "measurementFrequency": "yearly",
            "direction": "higherIsBetter",
        },
    },
    # ── Transition initiative ────────────────────────────────────────
    {
        "ref": "ini_modernization",
        "type": "Initiative",
        "name": "Licensing Modernization 1447H",
        "subtype": "program",
        "attributes": {},
    },
]

# (relation_type_key, source_ref, target_ref, attributes)
DEMO_RELATIONS: list[tuple[str, str, str, dict]] = [
    # Services → processes / apps / capabilities / data / orgs
    ("relGovServiceToProcess", "svc_issue_cr", "proc_issue_cr", {}),
    ("relGovServiceToProcess", "svc_renew_cr", "proc_issue_cr", {}),
    ("relGovServiceToProcess", "svc_book_inspection", "proc_inspection", {}),
    ("relGovServiceToApp", "svc_issue_cr", "app_cr_core", {}),
    ("relGovServiceToApp", "svc_renew_cr", "app_cr_core", {}),
    ("relGovServiceToApp", "svc_book_inspection", "app_legacy_licensing", {}),
    ("relGovServiceToApp", "svc_verify_cert", "app_integration_layer", {}),
    ("relGovServiceToBC", "svc_issue_cr", "bc_licensing", {}),
    ("relGovServiceToBC", "svc_renew_cr", "bc_licensing", {}),
    ("relGovServiceToBC", "svc_book_inspection", "bc_inspection", {}),
    ("relGovServiceToDO", "svc_issue_cr", "do_cr_record", {}),
    ("relOrgToGovService", "org_bs", "svc_issue_cr", {}),
    ("relOrgToGovService", "org_bs", "svc_renew_cr", {}),
    # Processes → applications
    ("relProcessToApp", "proc_issue_cr", "app_cr_core", {}),
    ("relProcessToApp", "proc_inspection", "app_legacy_licensing", {}),
    # Applications → exchanges → data → storage
    ("relAppToDataExchange", "app_cr_core", "dx_ndb_sync", {"direction": "bidirectional"}),
    ("relAppToDataExchange", "app_legacy_licensing", "dx_regulator_feed", {"direction": "sends"}),
    ("relDataExchangeToDO", "dx_ndb_sync", "do_cr_record", {}),
    ("relDataExchangeToDO", "dx_regulator_feed", "do_inspection_report", {}),
    ("relDataObjectToITC", "do_cr_record", "itc_pg", {}),
    ("relDataObjectToITC", "do_inspection_report", "itc_oracle_forms", {}),
    ("relAppToITC", "app_cr_core", "itc_pg", {}),
    ("relAppToITC", "app_cr_core", "itc_k8s", {}),
    ("relAppToITC", "app_legacy_licensing", "itc_oracle_forms", {}),
    # Applications ↔ Interfaces (integration layer)
    ("relAppToInterface", "app_cr_core", "if_cr_public_api", {"flowDirection": "provides"}),
    ("relAppToInterface", "app_business_portal", "if_cr_public_api", {"flowDirection": "consumes"}),
    ("relAppToInterface", "app_mobile_app", "if_mobile_gateway", {"flowDirection": "consumes"}),
    (
        "relAppToInterface",
        "app_workflow_engine",
        "if_mobile_gateway",
        {"flowDirection": "provides"},
    ),
    ("relAppToInterface", "app_cr_core", "if_verify_soap", {"flowDirection": "provides"}),
    ("relAppToInterface", "app_integration_layer", "if_ndb_events", {"flowDirection": "provides"}),
    (
        "relAppToInterface",
        "app_legacy_licensing",
        "if_regulator_sftp",
        {"flowDirection": "provides"},
    ),
    (
        "relAppToInterface",
        "app_legacy_licensing",
        "if_nightly_batch",
        {"flowDirection": "provides"},
    ),
    (
        "relAppToInterface",
        "app_analytics_studio",
        "if_nightly_batch",
        {"flowDirection": "consumes"},
    ),
    # Interfaces ↔ Data Objects
    ("relInterfaceToDataObj", "if_cr_public_api", "do_cr_record", {}),
    ("relInterfaceToDataObj", "if_verify_soap", "do_cr_record", {}),
    ("relInterfaceToDataObj", "if_ndb_events", "do_licence", {}),
    ("relInterfaceToDataObj", "if_regulator_sftp", "do_inspection_report", {}),
    ("relInterfaceToDataObj", "if_nightly_batch", "do_audit_log", {}),
    # Interfaces ↔ IT Components (where they run)
    ("relInterfaceToITC", "if_cr_public_api", "itc_k8s", {}),
    ("relInterfaceToITC", "if_ndb_events", "itc_kafka", {}),
    ("relInterfaceToITC", "if_mobile_gateway", "itc_k8s", {}),
    # Extra Applications → IT Components (fill technology band coverage)
    ("relAppToITC", "app_business_portal", "itc_k8s", {}),
    ("relAppToITC", "app_business_portal", "itc_redis", {}),
    ("relAppToITC", "app_mobile_app", "itc_k8s", {}),
    ("relAppToITC", "app_analytics_studio", "itc_object_store", {}),
    ("relAppToITC", "app_workflow_engine", "itc_k8s", {}),
    ("relAppToITC", "app_workflow_engine", "itc_kafka", {}),
    # Extra Applications → Data Objects (CRUD)
    ("relAppToDataObj", "app_business_portal", "do_licence", {}),
    ("relAppToDataObj", "app_analytics_studio", "do_audit_log", {}),
    ("relAppToDataObj", "app_workflow_engine", "do_licence", {}),
    ("relAppToDataObj", "app_cr_core", "do_establishment", {}),
    # Extra Data Objects → IT Components (storage)
    ("relDataObjectToITC", "do_licence", "itc_pg", {}),
    ("relDataObjectToITC", "do_inspector", "itc_pg", {}),
    ("relDataObjectToITC", "do_audit_log", "itc_object_store", {}),
    # PRM wiring
    ("relObjectiveToKPI", "obj_digital", "kpi_digital_share", {}),
    ("relObjectiveToKPI", "obj_digital", "kpi_issuance_time", {}),
    ("relObjectiveToKPI", "obj_consolidate", "kpi_retired_systems", {}),
    ("relKPIToGovService", "kpi_issuance_time", "svc_issue_cr", {}),
    ("relKPIToGovService", "kpi_digital_share", "svc_renew_cr", {}),
    # Transition initiative (gap-analysis traceability)
    (
        "relInitiativeToApp",
        "ini_modernization",
        "app_unified_licensing",
        {"transitionRole": "introduces"},
    ),
    (
        "relInitiativeToApp",
        "ini_modernization",
        "app_legacy_licensing",
        {"transitionRole": "retires"},
    ),
    ("relInitiativeToApp", "ini_modernization", "app_fax_intake", {"transitionRole": "retires"}),
    ("relInitiativeToObjective", "ini_modernization", "obj_consolidate", {}),
    ("relInitiativeToKPI", "ini_modernization", "kpi_retired_systems", {}),
]

# Program-tracker progress: (deliverable_key, status, evidence)
DEMO_PROGRAM_PROGRESS: list[tuple[str, str, list[dict]]] = [
    ("s1_maturity_assessment", "approved", []),
    (
        "s1_ea_project_strategy",
        "approved",
        [{"kind": "link", "ref": "/ea-delivery", "label": "EA Project Strategy 1447H"}],
    ),
    ("s2_committees_teams", "approved", []),
    ("s2_development_approach", "inReview", []),
    ("s3_ea_requirements", "inProgress", []),
    (
        "s3_swot",
        "inProgress",
        [{"kind": "link", "ref": "/reports/gap-analysis", "label": "Gap analysis input"}],
    ),
]


async def _already_seeded(db: AsyncSession) -> bool:
    result = await db.execute(
        select(Card.id).where(Card.type == "GovService", Card.name == MARKER_SERVICE).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def seed_nora_demo_data(db: AsyncSession) -> dict:
    """Seed the NORA demo landscape. Applies the NORA profile first."""
    from app.services.nora_profile import apply_nora_profile

    if await _already_seeded(db):
        return {"skipped": True, "reason": "NORA demo data already present"}

    # The profile creates the GovService/DataExchange/KPI types, relation
    # types, roles, regulations and the program catalogue (idempotent).
    await apply_nora_profile(db)

    cards: dict[str, Card] = {}
    for spec in DEMO_CARDS:
        card = Card(
            type=spec["type"],
            subtype=spec.get("subtype"),
            name=spec["name"],
            parent_id=cards[spec["parent"]].id if spec.get("parent") else None,
            attributes=spec.get("attributes", {}),
            architecture_state=spec.get("architecture_state", "current"),
            change_type=spec.get("change_type"),
            lifecycle=spec.get("lifecycle", {}),
        )
        db.add(card)
        await db.flush()
        cards[spec["ref"]] = card

    # Successor links (second pass — targets may be created after sources).
    for spec in DEMO_CARDS:
        if spec.get("successor"):
            cards[spec["ref"]].successor_id = cards[spec["successor"]].id

    for rel_key, source_ref, target_ref, attrs in DEMO_RELATIONS:
        db.add(
            Relation(
                type=rel_key,
                source_id=cards[source_ref].id,
                target_id=cards[target_ref].id,
                attributes=attrs,
            )
        )

    # Program-tracker progress.
    for key, status, evidence in DEMO_PROGRAM_PROGRESS:
        row = (
            await db.execute(select(EaProgramDeliverable).where(EaProgramDeliverable.key == key))
        ).scalar_one_or_none()
        if row is not None and row.status == "notStarted":
            row.status = status
            if evidence:
                row.evidence = evidence

    # Improvement opportunity in transition, linked to the initiative.
    opp = ImprovementOpportunity(
        title="Consolidate duplicated licensing systems",
        description=(
            "Three systems overlap on licence issuance; consolidate onto the "
            "Unified Licensing Platform and retire the legacy stack."
        ),
        domain="AA",
        source="manual",
        priority="high",
        status="inTransition",
        initiative_id=cards["ini_modernization"].id,
    )
    db.add(opp)
    await db.flush()
    for ref in ("app_legacy_licensing", "app_fax_intake"):
        db.add(ImprovementOpportunityCard(opportunity_id=opp.id, card_id=cards[ref].id))

    # A draft EA Project Strategy document (NORA governed document).
    db.add(
        SoAW(
            name="EA Project Strategy 1447H",
            doc_type="ea_project_strategy",
            status="draft",
            document_info={"prepared_by": "EA Working Team", "reviewed_by": "", "review_date": ""},
            version_history=[
                {
                    "version": "0.1",
                    "date": "",
                    "revised_by": "EA Working Team",
                    "description": "Initial draft",
                }
            ],
            sections={
                "ea_project_strategy.value": {
                    "content": (
                        "<p>Establish a single source of truth for the agency's "
                        "business and IT landscape, aligned to NORA and the "
                        "national digital transformation plan.</p>"
                    ),
                    "hidden": False,
                },
                "ea_project_strategy.goals": {
                    "content": (
                        "<p>Raise digital service adoption, consolidate duplicated "
                        "licensing systems, and pass the next Qiyas assessment.</p>"
                    ),
                    "hidden": False,
                },
            },
        )
    )

    await db.flush()
    return {
        "skipped": False,
        "cards": len(DEMO_CARDS),
        "relations": len(DEMO_RELATIONS),
        "program_updates": len(DEMO_PROGRAM_PROGRESS),
        "opportunities": 1,
        "documents": 1,
    }


# The improvement opportunity + draft SoAW created by ``seed_nora_demo_data``.
# Kept as module-level constants so the reset routine matches them by natural
# key (name / title) rather than by re-listing them inline.
_NORA_OPPORTUNITY_TITLE = "Consolidate duplicated licensing systems"
_NORA_SOAW_NAME = "EA Project Strategy 1447H"


async def reset_nora_demo_data(db: AsyncSession) -> dict:
    """Delete every row created by :func:`seed_nora_demo_data`, in reverse
    dependency order, so the next boot with ``SEED_NORA=true`` can re-seed
    the enriched landscape.

    Idempotent — safe to call when the demo has already been cleared. Only
    touches rows whose natural key matches the demo dataset; unrelated cards,
    relations, opportunities and SoAWs are untouched.

    The paired ``(name, type)`` tuple is the identity key for cards. Names are
    unique inside the demo set, but keying the delete on both fields prevents
    an accidental collision with a customer-created card that happens to share
    a name with a demo card.
    """
    from sqlalchemy import and_, delete, or_, tuple_
    from sqlalchemy import update as sql_update

    counts = {"cards": 0, "opportunities": 0, "documents": 0, "program_updates": 0}

    # 1. Draft SoAW — no FK dependencies from cards.
    result = await db.execute(delete(SoAW).where(SoAW.name == _NORA_SOAW_NAME))
    counts["documents"] = result.rowcount or 0

    # 2. Improvement opportunity — junction rows (improvement_opportunity_card)
    #    cascade on opportunity delete AND on card delete, so we can delete the
    #    opportunity before or after the cards. Doing it first keeps the card
    #    delete tidy.
    result = await db.execute(
        delete(ImprovementOpportunity).where(
            ImprovementOpportunity.title == _NORA_OPPORTUNITY_TITLE
        )
    )
    counts["opportunities"] = result.rowcount or 0

    # 3. Cards — relations cascade on card delete (FK ondelete=CASCADE), and
    #    improvement_opportunity_card is already gone. We match on
    #    (name, type) tuples so the delete stays scoped.
    #    Some backends dislike large IN-of-tuples; chunk if needed. The NORA
    #    demo tops out around 40 rows so one query is fine.
    demo_keys = [(spec["name"], spec["type"]) for spec in DEMO_CARDS]
    if demo_keys:
        result = await db.execute(delete(Card).where(tuple_(Card.name, Card.type).in_(demo_keys)))
        counts["cards"] = result.rowcount or 0

    # 4. Program-tracker deliverables — reset any that seed_nora advanced back
    #    to "notStarted" and clear evidence, but only for the specific keys the
    #    demo touches (guards against clobbering operator-set progress on
    #    deliverables the demo doesn't own).
    demo_program_keys = [k for k, _, _ in DEMO_PROGRAM_PROGRESS]
    if demo_program_keys:
        result = await db.execute(
            sql_update(EaProgramDeliverable)
            .where(
                and_(
                    EaProgramDeliverable.key.in_(demo_program_keys),
                    or_(
                        EaProgramDeliverable.status != "notStarted",
                        EaProgramDeliverable.evidence != [],
                    ),
                )
            )
            .values(status="notStarted", evidence=[])
        )
        counts["program_updates"] = result.rowcount or 0

    await db.flush()
    return counts
