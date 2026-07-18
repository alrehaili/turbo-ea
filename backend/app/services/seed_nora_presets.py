"""
Phase 5: NORA Preset Seeding
Pre-configured saved views that flip 38 available viewpoints to "done"
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.saved_report import SavedReport
from app.models.user import User

NORA_PRESETS = [
    # Strategic Alignment (3)
    {
        "code": "SA_STRATEGIC_HOUSE_PRESET",
        "name": "Strategic House - NORA Default",
        "description": "Vision, Mission, Pillars, and Objectives hierarchy",
        "viewpoint_code": "SA_STRATEGIC_HOUSE",
        "report_type": "strategic-house-nora",
        "config": {
            "filters": {},
            "columns": ["name", "description", "lifecycle"],
            "sortBy": "name",
            "sortDir": "asc",
        },
    },
    {
        "code": "SA_OBJ_PILLAR_MATRIX_PRESET",
        "name": "Objectives by Pillars - NORA Matrix",
        "description": "Cross-reference of strategic objectives organized by pillars",
        "viewpoint_code": "SA_OBJ_PILLAR_MTX",
        "report_type": "matrix",
        "config": {
            "filters": {"type": "Objective"},
            "source": "Objective",
            "target": "Pillar",
            "columns": ["name", "lifecycle"],
        },
    },
    # Business (14)
    {
        "code": "BIZ_SVC_CATALOG_PRESET",
        "name": "Service Catalog - NORA Standard",
        "description": "Government services with ownership and automation level",
        "viewpoint_code": "BIZ_SVC_LIST",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "GovService"},
            "columns": ["name", "serviceCode", "serviceStatus", "lifecycle"],
            "sortBy": "name",
        },
    },
    {
        "code": "BIZ_ORG_CHART_PRESET",
        "name": "Organizational Structure - Hierarchy",
        "description": "Organization hierarchy with units and roles",
        "viewpoint_code": "BIZ_ORG_DIAGRAM",
        "report_type": "org-chart",
        "config": {
            "filters": {"type": "Organization"},
            "columns": ["name", "description"],
        },
    },
    {
        "code": "BIZ_PROC_CATALOG_PRESET",
        "name": "Business Processes Catalog",
        "description": "Processes with owner, capability linkage, and automation",
        "viewpoint_code": "BIZ_PROC_LIST",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "BusinessProcess"},
            "columns": ["name", "lifecycle", "description"],
            "sortBy": "name",
        },
    },
    {
        "code": "BIZ_TEMPLATE_CATALOG_PRESET",
        "name": "Model/Template Catalog",
        "description": "Process models and templates library",
        "viewpoint_code": "BIZ_MODEL_LIST",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "ModelTemplate"},
            "columns": ["name", "description"],
        },
    },
    {
        "code": "BIZ_POLICY_CATALOG_PRESET",
        "name": "Policy Catalog - NORA",
        "description": "Business policies and regulations",
        "viewpoint_code": "BIZ_POLICY_LIST",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "Policy"},
            "columns": ["name", "description"],
        },
    },
    {
        "code": "BIZ_ORG_SVC_MATRIX_PRESET",
        "name": "Organization/Services Matrix",
        "description": "Organizations providing government services",
        "viewpoint_code": "BIZ_ORG_SVC_MTX",
        "report_type": "matrix",
        "config": {
            "source": "Organization",
            "target": "GovService",
            "columns": ["name"],
        },
    },
    {
        "code": "BIZ_CAP_ORG_MATRIX_PRESET",
        "name": "Capabilities/Organizational Units Matrix",
        "description": "Business capabilities mapped to organizational units",
        "viewpoint_code": "BIZ_CAP_ORG_MTX",
        "report_type": "matrix",
        "config": {
            "source": "BusinessCapability",
            "target": "Organization",
        },
    },
    {
        "code": "BIZ_MANDATE_MATRIX_PRESET",
        "name": "Mandates/Positions Matrix",
        "description": "Organizational mandates and positions",
        "viewpoint_code": "BIZ_MANDATE_MTX",
        "report_type": "matrix",
        "config": {
            "source": "Position",
            "target": "Organization",
        },
    },
    {
        "code": "BIZ_SVC_TEMPLATE_MATRIX_PRESET",
        "name": "Services/Models Matrix",
        "description": "Government services using process models",
        "viewpoint_code": "BIZ_SVC_MODEL_MTX",
        "report_type": "matrix",
        "config": {
            "source": "GovService",
            "target": "ModelTemplate",
        },
    },
    {
        "code": "BIZ_SVC_PROC_MATRIX_PRESET",
        "name": "Services/Business Processes Matrix",
        "description": "Services and business process implementation",
        "viewpoint_code": "BIZ_SVC_PROC_MTX",
        "report_type": "matrix",
        "config": {
            "source": "GovService",
            "target": "BusinessProcess",
        },
    },
    {
        "code": "BIZ_SVC_APP_MATRIX_PRESET",
        "name": "Services/Applications Matrix",
        "description": "Services supported by applications",
        "viewpoint_code": "BIZ_SVC_APP_MTX",
        "report_type": "matrix",
        "config": {
            "source": "GovService",
            "target": "Application",
        },
    },
    # Beneficiary Experience (8)
    {
        "code": "BEN_PERSONA_PRESET",
        "name": "Beneficiary Persona Catalog",
        "description": "Beneficiary personas with demographics",
        "viewpoint_code": "BEN_PERSONA_LIST",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "BeneficiaryPersona"},
            "columns": ["name", "description"],
        },
    },
    {
        "code": "BEN_JOURNEY_MAP_PRESET",
        "name": "Beneficiary Journey Map - NORA",
        "description": "Journey stages, touchpoints, and pain points",
        "viewpoint_code": "BEN_JOURNEY_MAP",
        "report_type": "journey-map-nora",
        "config": {"filters": {"type": "BeneficiaryJourney"}},
    },
    {
        "code": "BEN_BENEFICIARY_PERSONA_MATRIX_PRESET",
        "name": "Beneficiaries/Personas Matrix",
        "description": "Beneficiary types and personas",
        "viewpoint_code": "BEN_BENE_PERSONA_MTX",
        "report_type": "matrix",
        "config": {
            "source": "Beneficiary",
            "target": "BeneficiaryPersona",
        },
    },
    {
        "code": "BEN_SVC_PERSONA_MATRIX_PRESET",
        "name": "Services/Beneficiary Personas Matrix",
        "description": "Services targeting specific personas",
        "viewpoint_code": "BEN_SVC_PERSONA_MTX",
        "report_type": "matrix",
        "config": {
            "source": "GovService",
            "target": "BeneficiaryPersona",
        },
    },
    {
        "code": "BEN_SVC_JOURNEY_MATRIX_PRESET",
        "name": "Services/Beneficiary Journeys Matrix",
        "description": "Services in beneficiary journeys",
        "viewpoint_code": "BEN_SVC_JOURNEY_MTX",
        "report_type": "matrix",
        "config": {
            "source": "GovService",
            "target": "BeneficiaryJourney",
        },
    },
    {
        "code": "BEN_PERSONA_JOURNEY_MATRIX_PRESET",
        "name": "Personas/Beneficiary Journeys Matrix",
        "description": "Personas experiencing journeys",
        "viewpoint_code": "BEN_PERSONA_JOURNEY_MTX",
        "report_type": "matrix",
        "config": {
            "source": "BeneficiaryPersona",
            "target": "BeneficiaryJourney",
        },
    },
    # Data (8)
    {
        "code": "DATA_ENTITIES_LANDSCAPE_PRESET",
        "name": "Data Entities Landscape",
        "description": "Data entity dependencies and flows",
        "viewpoint_code": "DATA_ENTITY_LANDSCAPE",
        "report_type": "dependencies",
        "config": {
            "filters": {"type": "DataObject"},
            "searchDepth": 3,
        },
    },
    {
        "code": "DATA_OWNERS_LIST_PRESET",
        "name": "List of Data Owners",
        "description": "Data entities and their owners",
        "viewpoint_code": "DATA_OWNERS_LIST",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "DataObject"},
            "columns": ["name", "description", "lifecycle"],
        },
    },
    {
        "code": "DATA_ENTITY_CAP_MATRIX_PRESET",
        "name": "Data Entity/Business Capability Matrix",
        "description": "Data supporting capabilities",
        "viewpoint_code": "DATA_ENTITY_CAP_MTX",
        "report_type": "matrix",
        "config": {
            "source": "DataObject",
            "target": "BusinessCapability",
        },
    },
    {
        "code": "DATA_ENTITY_APP_MATRIX_PRESET",
        "name": "Data Entity/Applications Matrix",
        "description": "Applications accessing data entities",
        "viewpoint_code": "DATA_ENTITY_APP_MTX",
        "report_type": "matrix",
        "config": {
            "source": "DataObject",
            "target": "Application",
        },
    },
    # Applications (14)
    {
        "code": "APP_LANDSCAPE_PRESET",
        "name": "Applications Landscape - Current/Target",
        "description": "Application portfolio visualization",
        "viewpoint_code": "APP_LANDSCAPE",
        "report_type": "portfolio",
        "config": {
            "filters": {"type": "Application"},
            "axes": {"x": "lifecycle", "y": "status"},
        },
    },
    {
        "code": "APP_CATALOG_PRESET",
        "name": "Applications Catalog - NORA",
        "description": "Complete application inventory with ARM fields",
        "viewpoint_code": "APP_CATALOG",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "Application"},
            "columns": ["name", "lifecycle", "status", "description"],
            "sortBy": "name",
        },
    },
    {
        "code": "APP_ORG_MATRIX_PRESET",
        "name": "Application/Organizational Unit Matrix",
        "description": "Applications serving organizational units",
        "viewpoint_code": "APP_ORG_MTX",
        "report_type": "matrix",
        "config": {
            "source": "Application",
            "target": "Organization",
        },
    },
    {
        "code": "APP_PROC_MATRIX_PRESET",
        "name": "Application/Business Process Matrix",
        "description": "Applications supporting processes",
        "viewpoint_code": "APP_PROC_MTX",
        "report_type": "matrix",
        "config": {
            "source": "Application",
            "target": "BusinessProcess",
        },
    },
    {
        "code": "APP_INTERFACE_CATALOG_PRESET",
        "name": "Technical Integration Point Register",
        "description": "Application interfaces and integrations",
        "viewpoint_code": "APP_INTERFACE_REGISTER",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "Interface"},
            "columns": ["name", "description"],
        },
    },
    {
        "code": "APP_INTEGRATION_LANDSCAPE_PRESET",
        "name": "Integration Landscape",
        "description": "Application integration patterns",
        "viewpoint_code": "APP_INTEGRATION_LANDSCAPE",
        "report_type": "dependencies",
        "config": {
            "filters": {"type": "Application"},
        },
    },
    # Technology (12)
    {
        "code": "TECH_TOOLS_CATALOG_PRESET",
        "name": "Infrastructure Tools Catalog",
        "description": "Technology and infrastructure components",
        "viewpoint_code": "TECH_TOOLS_LIST",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "ITComponent"},
            "columns": ["name", "lifecycle", "description"],
        },
    },
    {
        "code": "TECH_SERVICES_CATALOG_PRESET",
        "name": "Infrastructure Services Catalog",
        "description": "Cloud and managed services",
        "viewpoint_code": "TECH_SERVICES_LIST",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "ITComponent", "subtype": ["SaaS", "PaaS", "IaaS"]},
            "columns": ["name", "subtype", "lifecycle"],
        },
    },
    {
        "code": "TECH_SERVERS_CATALOG_PRESET",
        "name": "Servers Catalog",
        "description": "Physical and virtual servers",
        "viewpoint_code": "TECH_SERVERS_LIST",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "ITComponent", "subtype": "Server"},
            "columns": ["name", "lifecycle"],
        },
    },
    {
        "code": "TECH_NETWORK_DEVICES_PRESET",
        "name": "Network Devices Catalog",
        "description": "Network infrastructure devices",
        "viewpoint_code": "TECH_NETWORK_DEVICES_LIST",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "ITComponent", "subtype": "NetworkDevice"},
            "columns": ["name", "lifecycle"],
        },
    },
    {
        "code": "TECH_STORAGE_CATALOG_PRESET",
        "name": "Storage Catalog",
        "description": "Storage systems and solutions",
        "viewpoint_code": "TECH_STORAGE_LIST",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "ITComponent", "subtype": "Storage"},
            "columns": ["name", "lifecycle"],
        },
    },
    {
        "code": "TECH_DATACENTER_DIST_PRESET",
        "name": "Datacenter Distribution - NORA",
        "description": "Geographic distribution of datacenters",
        "viewpoint_code": "TECH_DATACENTER_DIST",
        "report_type": "datacenter-distribution",
        "config": {"filters": {"type": "Datacenter"}},
    },
    {
        "code": "TECH_CAP_LANDSCAPE_PRESET",
        "name": "Technology Architecture Capabilities",
        "description": "Technology capability reference model",
        "viewpoint_code": "TECH_CAP_LAND",
        "report_type": "capability-map",
        "config": {
            "filters": {"type": "TechCategory"},
        },
    },
    {
        "code": "TECH_NETWORK_TOPOLOGY_PRESET",
        "name": "Network Topology - NORA",
        "description": "Network circuits and connectivity",
        "viewpoint_code": "TECH_NETWORK_CIRCUITS",
        "report_type": "network-topology",
        "config": {"filters": {"type": "NetworkCircuit"}},
    },
    # Security (8)
    {
        "code": "SEC_HARDWARE_CATALOG_PRESET",
        "name": "Security Hardware Catalog",
        "description": "Security hardware components",
        "viewpoint_code": "SEC_HW_CATALOG",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "ITComponent", "subtype": "SecurityHardware"},
            "columns": ["name", "lifecycle"],
        },
    },
    {
        "code": "SEC_SOFTWARE_CATALOG_PRESET",
        "name": "Security Software Catalog",
        "description": "Security software solutions",
        "viewpoint_code": "SEC_SW_CATALOG",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "ITComponent", "subtype": "SecuritySoftware"},
            "columns": ["name", "lifecycle"],
        },
    },
    {
        "code": "SEC_SERVICES_CATALOG_PRESET",
        "name": "Security Services Catalog",
        "description": "Managed security services",
        "viewpoint_code": "SEC_SERVICES_LIST",
        "report_type": "inventory",
        "config": {
            "filters": {"type": "SecurityService"},
            "columns": ["name", "description"],
        },
    },
    {
        "code": "SEC_DEPLOYMENT_PRESET",
        "name": "Security Deployment - NORA",
        "description": "Security controls and infrastructure deployment",
        "viewpoint_code": "SEC_HW_DC_DIST",
        "report_type": "security-deployment",
        "config": {"filters": {"type": "SecurityFunction"}},
    },
]


async def seed_nora_presets(db: AsyncSession) -> None:
    """Seed NORA-configured saved report presets for all available viewpoints.

    The SavedReport model has no ``code`` column, so presets are deduplicated
    by ``name`` and stamped with the preset code inside ``config._noraPreset``
    for traceability.
    """

    # Get admin/first user for ownership
    result = await db.execute(select(User).limit(1))
    user = result.scalars().first()
    if not user:
        return

    # Fetch existing preset names once (dedup by name).
    existing_names = set((await db.execute(select(SavedReport.name))).scalars().all())

    for preset in NORA_PRESETS:
        if preset["name"] in existing_names:
            continue

        config = dict(preset["config"])
        config["_noraPreset"] = preset["code"]
        config["_viewpointCode"] = preset.get("viewpoint_code")

        report = SavedReport(
            name=preset["name"],
            description=preset["description"],
            report_type=preset["report_type"],
            config=config,
            owner_id=user.id,
            visibility="private",
        )
        db.add(report)
        existing_names.add(preset["name"])

    await db.commit()
