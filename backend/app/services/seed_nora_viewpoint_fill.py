"""NORA viewpoint top-up seed — fills the card types added for the 67-viewpoint
completion (Phases 2/3/6 of viewsPlan.md) that ship empty, so every viewpoint
in the View Library renders real data:

Beneficiary, BeneficiaryPersona, ModelTemplate, Position, Mandate,
JourneyImprovement, DataDictionary, DataTerm, DataAttribute, DataVault,
Location, Datacenter, NetworkCircuit, SecurityService, SecurityFunction.

Every card is cross-linked to the existing NORA demo landscape (GovServices,
Organizations, Applications, DataObjects, Capabilities, Journeys, Providers,
IT Components) through the metamodel relation types so the matrix viewpoints
show real intersections.

Also creates one **ADM Governance Workspace** anchored to the seeded SoAW
("EA Project Strategy 1447H") with the full TOGAF phase template, so the
ADM Workspaces page has a working example.

Idempotent: keyed on a sentinel card this seed owns. All relations are
guarded — a missing source/target or relation type skips that edge rather
than failing.

[FORK FEATURE] — NORA.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adm import AdmPhase, AdmPhaseArtefact, AdmWorkspace
from app.models.card import Card
from app.models.relation import Relation
from app.models.relation_type import RelationType
from app.models.soaw import SoAW
from app.models.user import User
from app.services.adm_templates import get_template

# ════════════════════════════════════════════════════════════════════════════
# CARD SPECS  (name, subtype, attributes)
# ════════════════════════════════════════════════════════════════════════════

BENEFICIARIES: list[tuple[str, str | None, dict]] = [
    ("Citizens", "citizen", {}),
    ("Private Sector Establishments", "business", {}),
    ("Government Entities", "government", {}),
]

PERSONAS: list[tuple[str, str | None, dict]] = [
    (
        "Abu Salem — SME Owner",
        None,
        {
            "demographics": "35-55, owner of a small trading establishment",
            "goals": "Renew CR quickly, track inspections, avoid branch visits",
            "painPoints": "Repeated document uploads, unclear rejection reasons",
            "preferredChannels": "Mobile app, WhatsApp notifications",
        },
    ),
    (
        "Sara — New Entrepreneur",
        None,
        {
            "demographics": "25-35, first-time business founder",
            "goals": "Register a new business in one session",
            "painPoints": "Too many prerequisite services, jargon-heavy forms",
            "preferredChannels": "Web portal, live chat",
        },
    ),
    (
        "Khalid — Compliance Officer",
        None,
        {
            "demographics": "30-50, corporate compliance department",
            "goals": "Verify certificates in bulk, download audit evidence",
            "painPoints": "No bulk verification API, manual re-checks",
            "preferredChannels": "API integration, email digests",
        },
    ),
    (
        "Norah — Field Inspector",
        None,
        {
            "demographics": "28-45, ministry field workforce",
            "goals": "Complete inspection reports on-site from a tablet",
            "painPoints": "Offline gaps in coverage areas, duplicate data entry",
            "preferredChannels": "Mobile app, internal portal",
        },
    ),
    (
        "Um Faisal — Retired Citizen",
        None,
        {
            "demographics": "60+, low digital literacy",
            "goals": "Verify a contractor's certificate before hiring",
            "painPoints": "Small fonts, English-only error messages",
            "preferredChannels": "Call center, service center visit",
        },
    ),
]

MODEL_TEMPLATES: list[tuple[str, str | None, dict]] = [
    ("Government Service Design Template", "template", {}),
    ("BPMN 2.0 Process Modelling Standard", "processModel", {}),
    ("Service Level Agreement Template", "template", {}),
    ("Digital Channel Onboarding Model", "processModel", {}),
]

POSITIONS: list[tuple[str, str | None, dict]] = [
    ("Chief Executive Officer", "executive", {}),
    ("Chief Information Officer", "executive", {}),
    ("Director of Digital Transformation", "manager", {}),
    ("Enterprise Architecture Manager", "manager", {}),
    ("Data Management Specialist", "specialist", {}),
]

MANDATES: list[tuple[str, str | None, dict]] = [
    ("Digital Government Authority Mandate", None, {}),
    ("National Data Governance Mandate", None, {}),
    ("Cybersecurity Regulatory Mandate", None, {}),
    ("Service Delivery Excellence Mandate", None, {}),
]

JOURNEY_IMPROVEMENTS: list[tuple[str, str | None, dict]] = [
    ("Unified Login Across Services", None, {}),
    ("Proactive Renewal Notifications", None, {}),
    ("Reduce Required Documents to Zero", None, {}),
    ("Arabic Voice Assistant Support", None, {}),
    ("One-Visit Inspection Completion", None, {}),
]

DATA_DICTIONARIES: list[tuple[str, str | None, dict]] = [
    ("National Core Data Dictionary", None, {}),
    ("Commercial Registration Data Dictionary", None, {}),
]

DATA_TERMS: list[tuple[str, str | None, dict]] = [
    (
        "Beneficiary",
        None,
        {"businessMeaning": "Any person or entity consuming a government service"},
    ),
    ("Establishment", None, {"businessMeaning": "A registered commercial entity"}),
    (
        "Commercial Registration",
        None,
        {"businessMeaning": "The legal registration record of an establishment"},
    ),
    (
        "Service Request",
        None,
        {"businessMeaning": "A beneficiary's application for a government service"},
    ),
    ("Inspection", None, {"businessMeaning": "A scheduled compliance visit to an establishment"}),
]

DATA_ATTRIBUTES: list[tuple[str, str | None, dict]] = [
    ("National ID Number", None, {"dataFormat": "10-digit numeric"}),
    ("CR Number", None, {"dataFormat": "10-digit numeric"}),
    ("Establishment Name (Arabic)", None, {"dataFormat": "UTF-8 text"}),
    ("Establishment Name (English)", None, {"dataFormat": "Latin text"}),
    ("Request Status", None, {"dataFormat": "Coded value list"}),
    ("Inspection Date", None, {"dataFormat": "ISO 8601 date"}),
]

DATA_VAULTS: list[tuple[str, str | None, dict]] = [
    ("Core Registration Database", "database", {}),
    ("National Data Lake", "dataLake", {}),
    ("Regulatory Analytics Warehouse", "warehouse", {}),
    ("Document Evidence Store", "database", {}),
]

LOCATIONS: list[tuple[str, str | None, dict]] = [
    ("Riyadh Region", None, {}),
    ("Riyadh HQ Campus", None, {}),
    ("Dammam DR Site", None, {}),
    ("Jeddah Branch Office", None, {}),
    ("Gov Cloud Region KSA-1", None, {}),
]

DATACENTERS: list[tuple[str, str | None, dict]] = [
    ("Primary Datacenter — Riyadh", "onPremise", {}),
    ("DR Datacenter — Dammam", "onPremise", {}),
    ("Gov Cloud Region A", "cloudRegion", {}),
    ("Edge Node — Jeddah", "edgeLocation", {}),
]

NETWORK_CIRCUITS: list[tuple[str, str | None, dict]] = [
    ("Government Service Bus Backbone", "mpls", {"bandwidth": "10 Gbps"}),
    ("Riyadh–Dammam DR Circuit", "leased", {"bandwidth": "1 Gbps"}),
    ("Internet Gateway Circuit", "internet", {"bandwidth": "5 Gbps"}),
    ("Jeddah Branch MPLS Link", "mpls", {"bandwidth": "500 Mbps"}),
]

SECURITY_SERVICES: list[tuple[str, str | None, dict]] = [
    ("Managed SOC Service", "soc", {}),
    ("Managed Firewall Service", "managedSecurity", {}),
    ("Penetration Testing Service", "consulting", {}),
    ("Security Awareness Program", "consulting", {}),
]

SECURITY_FUNCTIONS: list[tuple[str, str | None, dict]] = [
    ("Identity & Access Management", "preventive", {}),
    ("Network Intrusion Detection", "detective", {}),
    ("Endpoint Protection", "preventive", {}),
    ("Incident Response", "corrective", {}),
    ("Data Loss Prevention", "preventive", {}),
]

# ════════════════════════════════════════════════════════════════════════════
# RELATIONS  (relation_type_key, source card name, target card name)
# Existing-landscape names verified against the NORA demo seeds.
# ════════════════════════════════════════════════════════════════════════════

RELATIONS: list[tuple[str, str, str]] = [
    # Beneficiary ↔ Persona
    ("relBeneficiaryToPersona", "Private Sector Establishments", "Abu Salem — SME Owner"),
    ("relBeneficiaryToPersona", "Private Sector Establishments", "Sara — New Entrepreneur"),
    ("relBeneficiaryToPersona", "Private Sector Establishments", "Khalid — Compliance Officer"),
    ("relBeneficiaryToPersona", "Citizens", "Um Faisal — Retired Citizen"),
    ("relBeneficiaryToPersona", "Government Entities", "Norah — Field Inspector"),
    # GovService ↔ Persona
    ("relGovServiceToPersona", "Issue Commercial Registration", "Sara — New Entrepreneur"),
    ("relGovServiceToPersona", "Renew Commercial Registration", "Abu Salem — SME Owner"),
    ("relGovServiceToPersona", "Verify Commercial Certificate", "Khalid — Compliance Officer"),
    ("relGovServiceToPersona", "Verify Commercial Certificate", "Um Faisal — Retired Citizen"),
    ("relGovServiceToPersona", "Book Inspection Appointment", "Norah — Field Inspector"),
    # GovService ↔ Journey (existing journeys)
    ("relGovServiceToJourney", "Issue Commercial Registration", "Register a New Business"),
    ("relGovServiceToJourney", "Renew Commercial Registration", "Renew Commercial Registration"),
    ("relGovServiceToJourney", "Verify Commercial Certificate", "Verify a Certificate"),
    ("relGovServiceToJourney", "Book Inspection Appointment", "Book & Complete Inspection"),
    # Persona ↔ Journey
    ("relPersonaToJourney", "Sara — New Entrepreneur", "Register a New Business"),
    ("relPersonaToJourney", "Abu Salem — SME Owner", "Renew Commercial Registration"),
    ("relPersonaToJourney", "Abu Salem — SME Owner", "Pay Government Fees"),
    ("relPersonaToJourney", "Khalid — Compliance Officer", "Verify a Certificate"),
    ("relPersonaToJourney", "Um Faisal — Retired Citizen", "Verify a Certificate"),
    ("relPersonaToJourney", "Norah — Field Inspector", "Book & Complete Inspection"),
    # Journey ↔ Improvement
    ("relJourneyToImprovement", "Register a New Business", "Unified Login Across Services"),
    ("relJourneyToImprovement", "Register a New Business", "Reduce Required Documents to Zero"),
    ("relJourneyToImprovement", "Renew Commercial Registration", "Proactive Renewal Notifications"),
    ("relJourneyToImprovement", "Verify a Certificate", "Arabic Voice Assistant Support"),
    ("relJourneyToImprovement", "Book & Complete Inspection", "One-Visit Inspection Completion"),
    # GovService ↔ ModelTemplate
    (
        "relGovServiceToTemplate",
        "Issue Commercial Registration",
        "Government Service Design Template",
    ),
    (
        "relGovServiceToTemplate",
        "Renew Commercial Registration",
        "Government Service Design Template",
    ),
    (
        "relGovServiceToTemplate",
        "Renew Commercial Registration",
        "Service Level Agreement Template",
    ),
    (
        "relGovServiceToTemplate",
        "Book Inspection Appointment",
        "BPMN 2.0 Process Modelling Standard",
    ),
    (
        "relGovServiceToTemplate",
        "Verify Commercial Certificate",
        "Digital Channel Onboarding Model",
    ),
    # Application ↔ Beneficiary
    ("relAppToBeneficiary", "Business Services Portal", "Private Sector Establishments"),
    ("relAppToBeneficiary", "Ministry Mobile App", "Citizens"),
    ("relAppToBeneficiary", "Unified Licensing Platform", "Private Sector Establishments"),
    ("relAppToBeneficiary", "National Integration Layer", "Government Entities"),
    # Organization ↔ Position
    ("relOrgToPosition", "Demo Ministry of Commerce", "Chief Executive Officer"),
    (
        "relOrgToPosition",
        "General Department of Information Technology",
        "Chief Information Officer",
    ),
    ("relOrgToPosition", "Digital Transformation Sector", "Director of Digital Transformation"),
    (
        "relOrgToPosition",
        "General Department of Information Technology",
        "Enterprise Architecture Manager",
    ),
    ("relOrgToPosition", "Applications Department", "Data Management Specialist"),
    # Position ↔ Mandate
    ("relPositionToMandate", "Chief Executive Officer", "Service Delivery Excellence Mandate"),
    ("relPositionToMandate", "Chief Information Officer", "Digital Government Authority Mandate"),
    ("relPositionToMandate", "Chief Information Officer", "Cybersecurity Regulatory Mandate"),
    (
        "relPositionToMandate",
        "Director of Digital Transformation",
        "Digital Government Authority Mandate",
    ),
    ("relPositionToMandate", "Data Management Specialist", "National Data Governance Mandate"),
    # Organization ↔ Mandate
    ("relOrgToMandate", "Demo Ministry of Commerce", "Service Delivery Excellence Mandate"),
    (
        "relOrgToMandate",
        "General Department of Information Technology",
        "Cybersecurity Regulatory Mandate",
    ),
    ("relOrgToMandate", "Digital Transformation Sector", "Digital Government Authority Mandate"),
    # DataDictionary ↔ DataTerm
    ("relDataDictToTerm", "National Core Data Dictionary", "Beneficiary"),
    ("relDataDictToTerm", "National Core Data Dictionary", "Establishment"),
    ("relDataDictToTerm", "Commercial Registration Data Dictionary", "Commercial Registration"),
    ("relDataDictToTerm", "Commercial Registration Data Dictionary", "Service Request"),
    ("relDataDictToTerm", "Commercial Registration Data Dictionary", "Inspection"),
    # DataTerm ↔ DataAttribute
    ("relDataTermToAttribute", "Beneficiary", "National ID Number"),
    ("relDataTermToAttribute", "Establishment", "CR Number"),
    ("relDataTermToAttribute", "Establishment", "Establishment Name (Arabic)"),
    ("relDataTermToAttribute", "Establishment", "Establishment Name (English)"),
    ("relDataTermToAttribute", "Service Request", "Request Status"),
    ("relDataTermToAttribute", "Inspection", "Inspection Date"),
    # DataObject ↔ DataAttribute (DAT_ENTITY_ATTR_MTX)
    ("relDataObjectToAttribute", "Commercial Registration Record", "CR Number"),
    ("relDataObjectToAttribute", "Commercial Registration Record", "Establishment Name (Arabic)"),
    ("relDataObjectToAttribute", "Establishment Profile", "Establishment Name (English)"),
    ("relDataObjectToAttribute", "Establishment Profile", "National ID Number"),
    ("relDataObjectToAttribute", "Inspection Report", "Inspection Date"),
    ("relDataObjectToAttribute", "Business Licence", "Request Status"),
    # DataObject ↔ BusinessCapability (DAT_ENTITY_CAP_MTX)
    ("relDataObjectToCapability", "Commercial Registration Record", "Business Services"),
    ("relDataObjectToCapability", "Business Licence", "Licence Issuance"),
    ("relDataObjectToCapability", "Inspection Report", "Inspections & Enforcement"),
    ("relDataObjectToCapability", "Establishment Profile", "Customer Engagement"),
    ("relDataObjectToCapability", "Regulatory Audit Log", "Data & Analytics"),
    # DataVault ↔ DataObject (DAT_ENTITY_VAULT_MTX)
    ("relDataVaultToDomain", "Core Registration Database", "Commercial Registration Record"),
    ("relDataVaultToDomain", "Core Registration Database", "Establishment Profile"),
    ("relDataVaultToDomain", "National Data Lake", "Regulatory Audit Log"),
    ("relDataVaultToDomain", "Regulatory Analytics Warehouse", "Inspection Report"),
    ("relDataVaultToDomain", "Document Evidence Store", "Business Licence"),
    # Application ↔ DataVault
    ("relAppToDataVault", "CR Core System", "Core Registration Database"),
    ("relAppToDataVault", "Regulatory Analytics Studio", "Regulatory Analytics Warehouse"),
    ("relAppToDataVault", "Unified Licensing Platform", "Document Evidence Store"),
    ("relAppToDataVault", "National Integration Layer", "National Data Lake"),
    # DataVault ↔ Location
    ("relDataVaultToLocation", "Core Registration Database", "Riyadh HQ Campus"),
    ("relDataVaultToLocation", "National Data Lake", "Gov Cloud Region KSA-1"),
    ("relDataVaultToLocation", "Regulatory Analytics Warehouse", "Gov Cloud Region KSA-1"),
    ("relDataVaultToLocation", "Document Evidence Store", "Dammam DR Site"),
    # Datacenter ↔ Location
    ("relDatacenterToLocation", "Primary Datacenter — Riyadh", "Riyadh HQ Campus"),
    ("relDatacenterToLocation", "DR Datacenter — Dammam", "Dammam DR Site"),
    ("relDatacenterToLocation", "Gov Cloud Region A", "Gov Cloud Region KSA-1"),
    ("relDatacenterToLocation", "Edge Node — Jeddah", "Jeddah Branch Office"),
    # Datacenter ↔ Provider (TECH_DC_PROVIDER_MTX)
    ("relDatacenterToProvider", "Primary Datacenter — Riyadh", "STC Solutions"),
    ("relDatacenterToProvider", "DR Datacenter — Dammam", "STC Solutions"),
    ("relDatacenterToProvider", "Gov Cloud Region A", "Oracle Saudi Arabia"),
    ("relDatacenterToProvider", "Edge Node — Jeddah", "Elm Company"),
    # Datacenter ↔ Application (TECH_DC_APP_MTX)
    ("relDatacenterToApp", "Primary Datacenter — Riyadh", "CR Core System"),
    ("relDatacenterToApp", "Primary Datacenter — Riyadh", "Unified Licensing Platform"),
    ("relDatacenterToApp", "DR Datacenter — Dammam", "CR Core System"),
    ("relDatacenterToApp", "Gov Cloud Region A", "Regulatory Analytics Studio"),
    ("relDatacenterToApp", "Gov Cloud Region A", "Business Services Portal"),
    # NetworkCircuit ↔ Datacenter
    (
        "relNetworkCircuitToDatacenter",
        "Government Service Bus Backbone",
        "Primary Datacenter — Riyadh",
    ),
    ("relNetworkCircuitToDatacenter", "Riyadh–Dammam DR Circuit", "DR Datacenter — Dammam"),
    ("relNetworkCircuitToDatacenter", "Internet Gateway Circuit", "Primary Datacenter — Riyadh"),
    ("relNetworkCircuitToDatacenter", "Jeddah Branch MPLS Link", "Edge Node — Jeddah"),
    # Application ↔ NetworkCircuit
    ("relAppToNetworkCircuit", "National Integration Layer", "Government Service Bus Backbone"),
    ("relAppToNetworkCircuit", "Business Services Portal", "Internet Gateway Circuit"),
    ("relAppToNetworkCircuit", "CR Core System", "Riyadh–Dammam DR Circuit"),
    # ITComponent ↔ Location
    ("relITComponentToLocation", "PostgreSQL Cluster", "Riyadh HQ Campus"),
    ("relITComponentToLocation", "Container Platform", "Gov Cloud Region KSA-1"),
    ("relITComponentToLocation", "Regulated Object Storage", "Dammam DR Site"),
    # SecurityService ↔ Provider (SEC_SERVICE_PROVIDER_MTX)
    ("relSecurityServiceToProvider", "Managed SOC Service", "Thales Saudi Arabia"),
    ("relSecurityServiceToProvider", "Managed Firewall Service", "STC Solutions"),
    ("relSecurityServiceToProvider", "Penetration Testing Service", "Thales Saudi Arabia"),
    ("relSecurityServiceToProvider", "Security Awareness Program", "Elm Company"),
    # SecurityFunction ↔ Application (SEC_HW_SW_FUNC_APPS_MTX)
    ("relSecurityFunctionToApp", "Identity & Access Management", "Business Services Portal"),
    ("relSecurityFunctionToApp", "Identity & Access Management", "Ministry Mobile App"),
    ("relSecurityFunctionToApp", "Data Loss Prevention", "CR Core System"),
    ("relSecurityFunctionToApp", "Endpoint Protection", "Unified Licensing Platform"),
    ("relSecurityFunctionToApp", "Network Intrusion Detection", "National Integration Layer"),
    # SecurityFunction ↔ ITComponent
    ("relSecurityFunctionToITComponent", "Network Intrusion Detection", "Event Streaming Bus"),
    ("relSecurityFunctionToITComponent", "Data Loss Prevention", "Regulated Object Storage"),
    ("relSecurityFunctionToITComponent", "Endpoint Protection", "Container Platform"),
    # SecurityFunction ↔ Location (SEC_HW_SW_FUNC_LOCATIONS_MTX)
    ("relSecurityFunctionToLocation", "Identity & Access Management", "Riyadh HQ Campus"),
    ("relSecurityFunctionToLocation", "Network Intrusion Detection", "Riyadh HQ Campus"),
    ("relSecurityFunctionToLocation", "Incident Response", "Dammam DR Site"),
    ("relSecurityFunctionToLocation", "Endpoint Protection", "Gov Cloud Region KSA-1"),
]

# ════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

_SENTINEL = ("Beneficiary", "Private Sector Establishments")


async def seed_nora_viewpoint_fill(db: AsyncSession) -> dict:
    """Fill the empty viewpoint building-block types + one ADM workspace."""
    exists = await db.execute(
        select(Card.id).where(Card.type == _SENTINEL[0], Card.name == _SENTINEL[1]).limit(1)
    )
    if exists.scalar_one_or_none() is not None:
        return {"skipped": True, "reason": "NORA viewpoint fill already seeded"}

    valid_rel_keys = set((await db.execute(select(RelationType.key))).scalars().all())

    groups: list[tuple[str, list[tuple[str, str | None, dict]]]] = [
        ("Beneficiary", BENEFICIARIES),
        ("BeneficiaryPersona", PERSONAS),
        ("ModelTemplate", MODEL_TEMPLATES),
        ("Position", POSITIONS),
        ("Mandate", MANDATES),
        ("JourneyImprovement", JOURNEY_IMPROVEMENTS),
        ("DataDictionary", DATA_DICTIONARIES),
        ("DataTerm", DATA_TERMS),
        ("DataAttribute", DATA_ATTRIBUTES),
        ("DataVault", DATA_VAULTS),
        ("Location", LOCATIONS),
        ("Datacenter", DATACENTERS),
        ("NetworkCircuit", NETWORK_CIRCUITS),
        ("SecurityService", SECURITY_SERVICES),
        ("SecurityFunction", SECURITY_FUNCTIONS),
    ]

    # (type, name) → id map. Seeded names are unique per type; relation
    # lookups below key by name only (all seed names are globally unique
    # except "Renew Commercial Registration", disambiguated by relation
    # type source/target types at render time — duplicates are fine for
    # the demo landscape).
    name_to_id: dict[str, str] = {}
    created_cards = 0

    for card_type, specs in groups:
        # Skip a type that already has cards (partial installs).
        existing_count = (
            await db.execute(select(Card.id).where(Card.type == card_type).limit(1))
        ).scalar_one_or_none()
        if existing_count is not None:
            continue
        for name, subtype, attrs in specs:
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

    # Resolve existing-card names referenced by relations.
    referenced = {n for _, s, t in RELATIONS for n in (s, t)}
    missing = [n for n in referenced if n not in name_to_id]
    if missing:
        rows = (await db.execute(select(Card.id, Card.name).where(Card.name.in_(missing)))).all()
        for cid, nm in rows:
            name_to_id.setdefault(nm, str(cid))

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

    # ── ADM Governance Workspace ────────────────────────────────────────
    workspace_created = False
    ws_exists = (await db.execute(select(AdmWorkspace.id).limit(1))).scalar_one_or_none()
    if ws_exists is None:
        soaw_row = (
            await db.execute(select(SoAW.id, SoAW.name).order_by(SoAW.created_at).limit(1))
        ).first()
        initiative_row = (
            await db.execute(
                select(Card.id)
                .where(Card.type == "Initiative", Card.name == "Licensing Modernization 1447H")
                .limit(1)
            )
        ).scalar_one_or_none()
        owner = (
            await db.execute(select(User.id).order_by(User.created_at).limit(1))
        ).scalar_one_or_none()

        if soaw_row is not None or initiative_row is not None:
            ws = AdmWorkspace(
                name=(soaw_row[1] if soaw_row else "Licensing Modernization 1447H")
                + " — ADM Governance",
                soaw_id=soaw_row[0] if soaw_row else None,
                initiative_id=initiative_row,
                description=(
                    "TOGAF ADM governance workspace for the 1447H licensing "
                    "modernization engagement. Seeded example — phases follow "
                    "the bundled TOGAF template."
                ),
                status="active",
                owner_id=owner,
                created_by=owner,
                target_completion=date(2026, 12, 31),
            )
            db.add(ws)
            await db.flush()

            for phase_spec in get_template("togaf"):
                phase = AdmPhase(
                    workspace_id=ws.id,
                    phase_key=phase_spec["phase_key"],
                    title=phase_spec["title"],
                    description=phase_spec["description"],
                    sort_order=phase_spec["sort_order"],
                    is_continuous=phase_spec["is_continuous"],
                    status=(
                        "in_progress"
                        if phase_spec["phase_key"] in ("preliminary", "requirements_management")
                        else "not_started"
                    ),
                    start_date=(
                        date(2026, 1, 15) if phase_spec["phase_key"] == "preliminary" else None
                    ),
                )
                db.add(phase)
                await db.flush()
                for i, req in enumerate(phase_spec["required_artefacts"]):
                    # Link the SoAW requirement of the Preliminary phase to
                    # the actual seeded SoAW so the workspace starts with one
                    # satisfied artefact.
                    linked_ref = (
                        soaw_row[0]
                        if (
                            soaw_row is not None
                            and phase_spec["phase_key"] == "preliminary"
                            and req["kind"] == "soaw"
                        )
                        else None
                    )
                    db.add(
                        AdmPhaseArtefact(
                            phase_id=phase.id,
                            kind=req["kind"],
                            title=req["title"],
                            ref_id=linked_ref,
                            is_required=True,
                            sort_order=i,
                        )
                    )
            workspace_created = True

    await db.commit()

    return {
        "loaded": True,
        "cards": created_cards,
        "relations": created_relations,
        "relations_skipped": skipped_relations,
        "adm_workspace": workspace_created,
    }
