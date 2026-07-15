"""NORA landscape top-up seed — fills the card types that the earlier NORA
seeds left empty (or thin) so every visible card type has a meaningful set of
cross-linked cards.

Creates at least 5 cards each for: Platform, Provider, TechCategory, Channel,
Persona, BeneficiaryJourney, Policy, SecurityControl, BusinessContext, and 5
BusinessProcess cards *with BPMN process flows*. Every card is wired to the
existing landscape via the current metamodel relation types (verified against
relation_types at author time).

Idempotent: keyed on a sentinel card this seed owns. All relations are guarded
so a missing source/target simply skips that edge rather than failing.

[FORK FEATURE] — NORA.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.process_diagram import ProcessDiagram
from app.models.process_flow_version import ProcessFlowVersion
from app.models.relation import Relation
from app.models.relation_type import RelationType

# ════════════════════════════════════════════════════════════════════════════
# CARD SPECS  (ref, name, subtype, attributes)
# ════════════════════════════════════════════════════════════════════════════

PLATFORMS = [
    ("plat_dgov", "National Digital Government Platform", "digital", {"platformType": "digital"}),
    ("plat_cloud", "Government Cloud Platform", "technical", {"platformType": "technical"}),
    (
        "plat_integration",
        "National Integration Platform",
        "technical",
        {"platformType": "technical"},
    ),
    ("plat_cx", "Citizen Experience Platform", "digital", {"platformType": "digital"}),
    ("plat_data", "Data & Analytics Platform", "digital", {"platformType": "digital"}),
]

PROVIDERS = [
    (
        "prov_stc",
        "STC Solutions",
        None,
        {
            "providerType": "vendor",
            "fieldOfActivity": "technologySolutions",
            "providerStatus": "active",
            "website": "stc.com.sa",
            "geoLocation": "Riyadh, KSA",
        },
    ),
    (
        "prov_elm",
        "Elm Company",
        None,
        {
            "providerType": "partner",
            "fieldOfActivity": "serviceProvider",
            "providerStatus": "active",
            "website": "elm.sa",
            "geoLocation": "Riyadh, KSA",
        },
    ),
    (
        "prov_thales",
        "Thales Saudi Arabia",
        None,
        {
            "providerType": "vendor",
            "fieldOfActivity": "securitySolutions",
            "providerStatus": "active",
            "geoLocation": "Riyadh, KSA",
        },
    ),
    (
        "prov_oracle",
        "Oracle Saudi Arabia",
        None,
        {
            "providerType": "vendor",
            "fieldOfActivity": "technologySolutions",
            "providerStatus": "active",
            "website": "oracle.com",
        },
    ),
    (
        "prov_lenovo",
        "Lenovo KSA",
        None,
        {
            "providerType": "vendor",
            "fieldOfActivity": "hardwareProvider",
            "providerStatus": "active",
        },
    ),
]

TECH_CATEGORIES = [
    ("tc_cloud", "Cloud Infrastructure", None, {"hierarchyLevel": 1}),
    ("tc_integration", "Integration & Middleware", None, {"hierarchyLevel": 1}),
    ("tc_data", "Data & Storage", None, {"hierarchyLevel": 1}),
    ("tc_security", "Security & Identity", None, {"hierarchyLevel": 1}),
    ("tc_euc", "End-User Computing", None, {"hierarchyLevel": 1}),
]

CHANNELS = [
    (
        "ch_portal",
        "National Web Portal",
        None,
        {"channelType": "web", "channelMaturity": "transactional"},
    ),
    (
        "ch_mobile",
        "Government Mobile App",
        None,
        {"channelType": "mobile", "channelMaturity": "proactive"},
    ),
    ("ch_center", "Service Center", None, {"channelType": "branch", "channelMaturity": "enhanced"}),
    (
        "ch_contact",
        "Contact Center",
        None,
        {"channelType": "callCenter", "channelMaturity": "enhanced"},
    ),
    (
        "ch_api",
        "Open API Gateway",
        None,
        {"channelType": "api", "channelMaturity": "transactional"},
    ),
]

PERSONAS = [
    (
        "per_founder",
        "Startup Founder",
        None,
        {
            "personaCode": "P-01",
            "personaGoals": "Register and launch a new business quickly.",
            "demographicInfo": "25-40, first-time entrepreneur.",
            "painPoints": "Complex paperwork and unclear requirements.",
        },
    ),
    (
        "per_owner",
        "Established Business Owner",
        None,
        {
            "personaCode": "P-02",
            "personaGoals": "Renew licences and stay compliant with minimal effort.",
            "demographicInfo": "35-60, SME owner.",
            "painPoints": "Repetitive renewals and multiple portals.",
        },
    ),
    (
        "per_officer",
        "Government Officer",
        None,
        {
            "personaCode": "P-03",
            "personaGoals": "Verify records and process cases efficiently.",
            "demographicInfo": "Public-sector employee.",
            "painPoints": "Manual verification across disconnected systems.",
        },
    ),
    (
        "per_investor",
        "Foreign Investor",
        None,
        {
            "personaCode": "P-04",
            "personaGoals": "Establish a presence and obtain investor licences.",
            "demographicInfo": "International business, non-Arabic speaker.",
            "painPoints": "Language barriers and unfamiliar processes.",
        },
    ),
    (
        "per_citizen",
        "Individual Citizen",
        None,
        {
            "personaCode": "P-05",
            "personaGoals": "Access government services from home.",
            "demographicInfo": "General public.",
            "painPoints": "In-person visits and long wait times.",
        },
    ),
]

JOURNEYS = [
    (
        "jour_register",
        "Register a New Business",
        "journeyPhase",
        {
            "journeyStage": "awareness",
            "journeyCode": "J-01",
            "improvementPriority": "high",
            "journeyObjective": "Enable end-to-end online business registration.",
        },
    ),
    (
        "jour_renew",
        "Renew Commercial Registration",
        "journeyPhase",
        {
            "journeyStage": "service",
            "journeyCode": "J-02",
            "improvementPriority": "medium",
            "journeyObjective": "One-click renewal with proactive reminders.",
        },
    ),
    (
        "jour_inspect",
        "Book & Complete Inspection",
        "journeyPhase",
        {
            "journeyStage": "service",
            "journeyCode": "J-03",
            "improvementPriority": "medium",
            "journeyObjective": "Self-service scheduling and digital inspection reports.",
        },
    ),
    (
        "jour_verify",
        "Verify a Certificate",
        "journeyPhase",
        {
            "journeyStage": "access",
            "journeyCode": "J-04",
            "improvementPriority": "low",
            "journeyObjective": "Instant, trusted certificate verification.",
        },
    ),
    (
        "jour_pay",
        "Pay Government Fees",
        "journeyPhase",
        {
            "journeyStage": "service",
            "journeyCode": "J-05",
            "improvementPriority": "high",
            "journeyObjective": "Unified, secure payment across all services.",
        },
    ),
]

POLICIES = [
    (
        "pol_dataclass",
        "Data Classification Policy",
        None,
        {"policyCode": "POL-01", "policyType": "internal", "policyStatus": "active"},
    ),
    (
        "pol_cloudfirst",
        "Cloud First Policy",
        None,
        {"policyCode": "POL-02", "policyType": "external", "policyStatus": "active"},
    ),
    (
        "pol_identity",
        "Digital Identity Policy",
        None,
        {"policyCode": "POL-03", "policyType": "external", "policyStatus": "active"},
    ),
    (
        "pol_infosec",
        "Information Security Policy",
        None,
        {"policyCode": "POL-04", "policyType": "internal", "policyStatus": "active"},
    ),
    (
        "pol_opendata",
        "Open Data Policy",
        None,
        {"policyCode": "POL-05", "policyType": "external", "policyStatus": "active"},
    ),
]

SECURITY_CONTROLS = [
    (
        "sc_iam",
        "Identity & Access Management",
        None,
        {
            "controlDomain": "iam",
            "implementationStatus": "implemented",
            "controlFramework": "NCA ECC",
            "srmCode": "SRM-IAM-01",
        },
    ),
    (
        "sc_encrypt",
        "Data Encryption at Rest & in Transit",
        None,
        {
            "controlDomain": "dataProtection",
            "implementationStatus": "implemented",
            "controlFramework": "NCA ECC",
            "srmCode": "SRM-DP-01",
        },
    ),
    (
        "sc_network",
        "Network Segmentation",
        None,
        {
            "controlDomain": "network",
            "implementationStatus": "partial",
            "controlFramework": "NCA ECC",
            "srmCode": "SRM-NET-01",
        },
    ),
    (
        "sc_logging",
        "Security Logging & Monitoring",
        None,
        {
            "controlDomain": "ops",
            "implementationStatus": "implemented",
            "controlFramework": "ISO 27001",
            "srmCode": "SRM-OPS-01",
        },
    ),
    (
        "sc_sdlc",
        "Secure SDLC",
        None,
        {
            "controlDomain": "appSec",
            "implementationStatus": "planned",
            "controlFramework": "OWASP SAMM",
            "srmCode": "SRM-APP-01",
        },
    ),
]

BUSINESS_CONTEXTS = [
    (
        "bctx_registration",
        "Business Registration Value Stream",
        "valueStream",
        {"maturity": "defined", "hierarchyLevel": 1},
    ),
    (
        "bctx_licensing",
        "Licensing & Permits Value Stream",
        "valueStream",
        {"maturity": "managed", "hierarchyLevel": 1},
    ),
    (
        "bctx_certificate",
        "Commercial Certificate",
        "businessProduct",
        {"maturity": "defined", "hierarchyLevel": 1, "productType": "document"},
    ),
    (
        "bctx_inspection",
        "Inspection & Compliance",
        "process",
        {"maturity": "defined", "hierarchyLevel": 1},
    ),
    (
        "bctx_esg",
        "Sustainable Government Services",
        "esgCapability",
        {"maturity": "initial", "hierarchyLevel": 1},
    ),
]

# BusinessProcess: (ref, name, attrs, [bpmn task names])
BUSINESS_PROCESSES = [
    (
        "proc_cr_renew",
        "Commercial Registration Renewal",
        {
            "processType": "core",
            "maturity": "defined",
            "automationLevel": "partiallyAutomated",
            "riskLevel": "medium",
            "frequency": "monthly",
            "processClassification": "main",
        },
        [
            "Submit Renewal Request",
            "Validate Records",
            "Calculate Fees",
            "Collect Payment",
            "Issue Renewed CR",
        ],
    ),
    (
        "proc_inspection",
        "Inspection Scheduling & Execution",
        {
            "processType": "core",
            "maturity": "managed",
            "automationLevel": "partiallyAutomated",
            "riskLevel": "high",
            "frequency": "weekly",
            "processClassification": "main",
        },
        [
            "Request Inspection",
            "Assign Inspector",
            "Conduct Inspection",
            "Record Findings",
            "Publish Report",
        ],
    ),
    (
        "proc_payment",
        "Fee Payment & Settlement",
        {
            "processType": "support",
            "maturity": "measured",
            "automationLevel": "fullyAutomated",
            "riskLevel": "medium",
            "frequency": "daily",
            "processClassification": "main",
        },
        ["Initiate Payment", "Authorise Transaction", "Settle Funds", "Confirm Receipt"],
    ),
    (
        "proc_verify",
        "Certificate Verification",
        {
            "processType": "core",
            "maturity": "defined",
            "automationLevel": "fullyAutomated",
            "riskLevel": "low",
            "frequency": "continuous",
            "processClassification": "main",
        },
        [
            "Receive Verification Request",
            "Look Up Record",
            "Validate Authenticity",
            "Return Result",
        ],
    ),
    (
        "proc_compliance",
        "Compliance Reporting",
        {
            "processType": "management",
            "maturity": "managed",
            "automationLevel": "partiallyAutomated",
            "riskLevel": "high",
            "frequency": "quarterly",
            "processClassification": "main",
        },
        [
            "Collect Compliance Data",
            "Assess Against Regulations",
            "Prepare Report",
            "Review & Approve",
            "Submit to Regulator",
        ],
    ),
]


# ════════════════════════════════════════════════════════════════════════════
# RELATIONS  (relation_type_key, source_name, target_name)
# Source/target are card *names* — resolved across newly-created + existing
# cards. A missing endpoint (or relation type) is skipped, not fatal.
# ════════════════════════════════════════════════════════════════════════════

RELATIONS: list[tuple[str, str, str]] = [
    # Platform → Objective / Application / ITComponent
    (
        "relPlatformToObjective",
        "National Digital Government Platform",
        "Establish Enterprise API Platform",
    ),
    ("relPlatformToObjective", "Data & Analytics Platform", "Build Enterprise Data Lake"),
    ("relPlatformToObjective", "Government Cloud Platform", "Complete Cloud Migration Program"),
    ("relPlatformToApp", "National Integration Platform", "National Integration Layer"),
    ("relPlatformToApp", "Citizen Experience Platform", "Business Services Portal"),
    ("relPlatformToApp", "Data & Analytics Platform", "Regulatory Analytics Studio"),
    ("relPlatformToITC", "Government Cloud Platform", "Container Platform"),
    ("relPlatformToITC", "National Integration Platform", "Event Streaming Bus"),
    ("relITCToPlatform", "PostgreSQL Cluster", "Government Cloud Platform"),
    (
        "relInitiativeToPlatform",
        "Enterprise API Platform Initiative (EAPI)",
        "National Integration Platform",
    ),
    (
        "relInitiativeToPlatform",
        "Digital Infrastructure Modernization Program (DIMP)",
        "Government Cloud Platform",
    ),
    # Provider → Application / ITComponent / Initiative
    ("relProviderToApp", "Elm Company", "Business Services Portal"),
    ("relProviderToApp", "Oracle Saudi Arabia", "CR Core System"),
    ("relProviderToITC", "Oracle Saudi Arabia", "PostgreSQL Cluster"),
    ("relProviderToITC", "STC Solutions", "Container Platform"),
    ("relProviderToITC", "Lenovo KSA", "Regulated Object Storage"),
    ("relProviderToITC", "Thales Saudi Arabia", "Session & Cache Grid"),
    (
        "relProviderToInitiative",
        "STC Solutions",
        "Digital Infrastructure Modernization Program (DIMP)",
    ),
    ("relProviderToInitiative", "Elm Company", "Licensing Portal Relaunch"),
    ("relProviderToInitiative", "Thales Saudi Arabia", "Zero Trust Security Architecture (ZTSA)"),
    # ITComponent → TechCategory
    ("relITCToTechCat", "Container Platform", "Cloud Infrastructure"),
    ("relITCToTechCat", "Event Streaming Bus", "Integration & Middleware"),
    ("relITCToTechCat", "PostgreSQL Cluster", "Data & Storage"),
    ("relITCToTechCat", "Regulated Object Storage", "Data & Storage"),
    ("relITCToTechCat", "Session & Cache Grid", "Security & Identity"),
    ("relITCToTechCat", "Legacy Forms Runtime", "End-User Computing"),
    # Persona → GovService / Journey
    ("relPersonaToGovService", "Startup Founder", "Issue Commercial Registration"),
    ("relPersonaToGovService", "Established Business Owner", "Renew Commercial Registration"),
    ("relPersonaToGovService", "Government Officer", "Verify Commercial Certificate"),
    ("relPersonaToGovService", "Established Business Owner", "Book Inspection Appointment"),
    ("relPersonaToJourney", "Startup Founder", "Register a New Business"),
    ("relPersonaToJourney", "Established Business Owner", "Renew Commercial Registration"),
    ("relPersonaToJourney", "Government Officer", "Verify a Certificate"),
    ("relPersonaToJourney", "Individual Citizen", "Pay Government Fees"),
    ("relPersonaToJourney", "Foreign Investor", "Register a New Business"),
    # BeneficiaryJourney → GovService / Channel
    ("relJourneyToGovService", "Register a New Business", "Issue Commercial Registration"),
    ("relJourneyToGovService", "Renew Commercial Registration", "Renew Commercial Registration"),
    ("relJourneyToGovService", "Book & Complete Inspection", "Book Inspection Appointment"),
    ("relJourneyToGovService", "Verify a Certificate", "Verify Commercial Certificate"),
    ("relJourneyToChannel", "Register a New Business", "National Web Portal"),
    ("relJourneyToChannel", "Renew Commercial Registration", "Government Mobile App"),
    ("relJourneyToChannel", "Book & Complete Inspection", "Service Center"),
    ("relJourneyToChannel", "Verify a Certificate", "Open API Gateway"),
    ("relJourneyToChannel", "Pay Government Fees", "Government Mobile App"),
    # Policy → BusinessCapability / GovService / BusinessProcess
    ("relPolicyToBC", "Data Classification Policy", "Data & Analytics"),
    ("relPolicyToBC", "Open Data Policy", "Data & Analytics"),
    ("relPolicyToBC", "Digital Identity Policy", "Customer Engagement"),
    ("relPolicyToGovService", "Digital Identity Policy", "Issue Commercial Registration"),
    ("relPolicyToGovService", "Information Security Policy", "Verify Commercial Certificate"),
    ("relPolicyToProcess", "Information Security Policy", "Certificate Verification"),
    ("relPolicyToProcess", "Cloud First Policy", "Fee Payment & Settlement"),
    ("relPolicyToProcess", "Data Classification Policy", "Compliance Reporting"),
    # SecurityControl → Application / DataObject / ITComponent (protects/secures)
    ("relSecCtrlToApp", "Identity & Access Management", "Business Services Portal"),
    ("relSecCtrlToApp", "Identity & Access Management", "CR Core System"),
    ("relSecCtrlToApp", "Secure SDLC", "Regulatory Analytics Studio"),
    ("relSecCtrlToData", "Data Encryption at Rest & in Transit", "Commercial Registration Record"),
    ("relSecCtrlToData", "Data Encryption at Rest & in Transit", "Business Licence"),
    ("relSecCtrlToData", "Security Logging & Monitoring", "Regulatory Audit Log"),
    ("relSecCtrlToITC", "Network Segmentation", "Container Platform"),
    ("relSecCtrlToITC", "Network Segmentation", "Event Streaming Bus"),
    ("relSecCtrlToITC", "Data Encryption at Rest & in Transit", "Regulated Object Storage"),
    ("relSecCtrlToITC", "Security Logging & Monitoring", "PostgreSQL Cluster"),
    # BusinessContext → BusinessCapability, and Org/App → BusinessContext
    ("relBizCtxToBC", "Business Registration Value Stream", "Licence Issuance"),
    ("relBizCtxToBC", "Licensing & Permits Value Stream", "Licensing & Permits"),
    ("relBizCtxToBC", "Inspection & Compliance", "Inspections & Enforcement"),
    ("relOrgToBizCtx", "Business Services Sector", "Business Registration Value Stream"),
    ("relOrgToBizCtx", "Business Services Sector", "Licensing & Permits Value Stream"),
    ("relAppToBizCtx", "Unified Licensing Platform", "Licensing & Permits Value Stream"),
    ("relAppToBizCtx", "CR Core System", "Business Registration Value Stream"),
    # BusinessProcess → BusinessCapability / Application / DataObject / Org / Objective / BusinessContext
    ("relProcessToBC", "Commercial Registration Renewal", "Licence Renewal"),
    ("relProcessToBC", "Inspection Scheduling & Execution", "Inspections & Enforcement"),
    ("relProcessToBC", "Certificate Verification", "Business Services"),
    ("relProcessToApp", "Commercial Registration Renewal", "CR Core System"),
    ("relProcessToApp", "Fee Payment & Settlement", "National Integration Layer"),
    ("relProcessToApp", "Certificate Verification", "Business Services Portal"),
    ("relProcessToDataObj", "Commercial Registration Renewal", "Commercial Registration Record"),
    ("relProcessToDataObj", "Inspection Scheduling & Execution", "Inspection Report"),
    ("relProcessToDataObj", "Certificate Verification", "Business Licence"),
    ("relProcessToOrg", "Commercial Registration Renewal", "Business Services Sector"),
    ("relProcessToOrg", "Compliance Reporting", "Digital Transformation Sector"),
    ("relProcessToObjective", "Fee Payment & Settlement", "Increase Process Automation to 85%"),
    ("relProcessToObjective", "Certificate Verification", "Optimize Core Business Processes"),
    ("relProcessToBizCtx", "Commercial Registration Renewal", "Business Registration Value Stream"),
    ("relProcessToBizCtx", "Inspection Scheduling & Execution", "Inspection & Compliance"),
    # GovService → BusinessProcess
    ("relGovServiceToProcess", "Renew Commercial Registration", "Commercial Registration Renewal"),
    ("relGovServiceToProcess", "Book Inspection Appointment", "Inspection Scheduling & Execution"),
    ("relGovServiceToProcess", "Verify Commercial Certificate", "Certificate Verification"),
]


# ════════════════════════════════════════════════════════════════════════════
# BPMN — minimal linear diagram generator with DI layout so it renders.
# ════════════════════════════════════════════════════════════════════════════


def _linear_bpmn(process_name: str, tasks: list[str]) -> str:
    """Build a valid, laid-out BPMN 2.0 string: start → tasks → end."""

    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        )

    # XML-safe identifier (letters/digits/underscore only) derived from the name.
    ident = "".join(c if c.isalnum() else "_" for c in process_name)
    proc_id = f"Process_{ident}"

    x = 160
    y = 120
    gap_task = 150
    task_w, task_h = 110, 80
    ev = 36

    nodes: list[str] = []
    shapes: list[str] = []
    edges: list[str] = []
    di_edges: list[str] = []

    # Start event
    nodes.append(
        '<bpmn:startEvent id="Start" name="Start"><bpmn:outgoing>f0</bpmn:outgoing></bpmn:startEvent>'
    )
    sx = x
    shapes.append(
        f'<bpmndi:BPMNShape id="Start_di" bpmnElement="Start">'
        f'<dc:Bounds x="{sx}" y="{y + (task_h - ev) // 2}" width="{ev}" height="{ev}" /></bpmndi:BPMNShape>'
    )
    prev_id = "Start"
    prev_right = sx + ev
    prev_cy = y + task_h // 2

    cursor = sx + ev + gap_task
    for i, tname in enumerate(tasks):
        tid = f"Task_{i}"
        incoming = f"f{i}"
        outgoing = f"f{i + 1}"
        nodes.append(
            f'<bpmn:task id="{tid}" name="{esc(tname)}">'
            f"<bpmn:incoming>{incoming}</bpmn:incoming>"
            f"<bpmn:outgoing>{outgoing}</bpmn:outgoing></bpmn:task>"
        )
        shapes.append(
            f'<bpmndi:BPMNShape id="{tid}_di" bpmnElement="{tid}">'
            f'<dc:Bounds x="{cursor}" y="{y}" width="{task_w}" height="{task_h}" /></bpmndi:BPMNShape>'
        )
        edges.append(
            f'<bpmn:sequenceFlow id="{incoming}" sourceRef="{prev_id}" targetRef="{tid}" />'
        )
        di_edges.append(
            f'<bpmndi:BPMNEdge id="{incoming}_di" bpmnElement="{incoming}">'
            f'<di:waypoint x="{prev_right}" y="{prev_cy}" />'
            f'<di:waypoint x="{cursor}" y="{y + task_h // 2}" /></bpmndi:BPMNEdge>'
        )
        prev_id = tid
        prev_right = cursor + task_w
        prev_cy = y + task_h // 2
        cursor += task_w + gap_task

    # End event
    end_out = f"f{len(tasks)}"
    nodes.append(
        f'<bpmn:endEvent id="End" name="End"><bpmn:incoming>{end_out}</bpmn:incoming></bpmn:endEvent>'
    )
    shapes.append(
        f'<bpmndi:BPMNShape id="End_di" bpmnElement="End">'
        f'<dc:Bounds x="{cursor}" y="{y + (task_h - ev) // 2}" width="{ev}" height="{ev}" /></bpmndi:BPMNShape>'
    )
    edges.append(f'<bpmn:sequenceFlow id="{end_out}" sourceRef="{prev_id}" targetRef="End" />')
    di_edges.append(
        f'<bpmndi:BPMNEdge id="{end_out}_di" bpmnElement="{end_out}">'
        f'<di:waypoint x="{prev_right}" y="{prev_cy}" />'
        f'<di:waypoint x="{cursor}" y="{y + task_h // 2}" /></bpmndi:BPMNEdge>'
    )

    body = "\n    ".join(nodes + edges)
    di = "\n    ".join(shapes + di_edges)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
        'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
        'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
        'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" '
        f'id="Defs_{ident}" targetNamespace="http://turboea/bpmn">\n'
        f'  <bpmn:process id="{proc_id}" name="{esc(process_name)}" isExecutable="false">\n'
        f"    {body}\n"
        "  </bpmn:process>\n"
        f'  <bpmndi:BPMNDiagram id="Diag_1"><bpmndi:BPMNPlane id="Plane_1" bpmnElement="{proc_id}">\n'
        f"    {di}\n"
        "  </bpmndi:BPMNPlane></bpmndi:BPMNDiagram>\n"
        "</bpmn:definitions>\n"
    )


# ════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

_SENTINEL = ("Platform", "National Digital Government Platform")


async def seed_nora_landscape_fill(db: AsyncSession) -> dict:
    """Top-up the empty/thin card types with 5+ cross-linked cards each."""
    # Idempotency sentinel.
    exists = await db.execute(
        select(Card.id).where(Card.type == _SENTINEL[0], Card.name == _SENTINEL[1]).limit(1)
    )
    if exists.scalar_one_or_none() is not None:
        return {"skipped": True, "reason": "NORA landscape fill already seeded"}

    # Valid relation-type keys (skip any edge whose type isn't in the metamodel).
    valid_rel_keys = set((await db.execute(select(RelationType.key))).scalars().all())

    groups: list[tuple[str, list[tuple]]] = [
        ("Platform", PLATFORMS),
        ("Provider", PROVIDERS),
        ("TechCategory", TECH_CATEGORIES),
        ("Channel", CHANNELS),
        ("Persona", PERSONAS),
        ("BeneficiaryJourney", JOURNEYS),
        ("Policy", POLICIES),
        ("SecurityControl", SECURITY_CONTROLS),
        ("BusinessContext", BUSINESS_CONTEXTS),
    ]

    # name → id map (new + existing cards), for relation resolution.
    name_to_id: dict[str, str] = {}
    created_cards = 0

    for card_type, specs in groups:
        for _ref, name, subtype, attrs in specs:
            card = Card(
                type=card_type,
                subtype=subtype,
                name=name,
                attributes=attrs,
                lifecycle={"active": "2024-01-01"},
            )
            db.add(card)
            await db.flush()
            name_to_id[name] = str(card.id)
            created_cards += 1

    # BusinessProcess cards + BPMN process flows.
    diagrams = 0
    for _ref, name, attrs, tasks in BUSINESS_PROCESSES:
        card = Card(
            type="BusinessProcess",
            subtype="process",
            name=name,
            attributes=attrs,
            lifecycle={"active": "2024-01-01"},
        )
        db.add(card)
        await db.flush()
        name_to_id[name] = str(card.id)
        created_cards += 1

        xml = _linear_bpmn(name, tasks)
        db.add(ProcessDiagram(process_id=card.id, bpmn_xml=xml, version=1))
        db.add(ProcessFlowVersion(process_id=card.id, status="published", revision=1, bpmn_xml=xml))
        diagrams += 1

    await db.flush()

    # Fill in existing-card ids referenced by relations (any name not yet mapped).
    referenced = {n for _, s, t in RELATIONS for n in (s, t)}
    missing = [n for n in referenced if n not in name_to_id]
    if missing:
        rows = (await db.execute(select(Card.id, Card.name).where(Card.name.in_(missing)))).all()
        for cid, nm in rows:
            name_to_id.setdefault(nm, str(cid))

    # Create relations (guarded).
    created_relations = 0
    skipped_relations = 0
    for rel_key, src_name, tgt_name in RELATIONS:
        src = name_to_id.get(src_name)
        tgt = name_to_id.get(tgt_name)
        if rel_key not in valid_rel_keys or src is None or tgt is None:
            skipped_relations += 1
            continue
        db.add(Relation(type=rel_key, source_id=src, target_id=tgt, attributes={}))
        created_relations += 1

    await db.commit()

    return {
        "loaded": True,
        "cards": created_cards,
        "process_flows": diagrams,
        "relations": created_relations,
        "relations_skipped": skipped_relations,
    }
