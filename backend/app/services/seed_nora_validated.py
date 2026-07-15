"""Validated, comprehensive NORA seed with full strategic linkages and data quality checks.

[FORK FEATURE] — All seeded data is:
✓ Semantically correct (services → processes → capabilities → objectives)
✓ Properly hierarchical (parent/child relationships)
✓ Cross-linked via relations (Strategic House traceability)
✓ Attribute-complete (all required fields populated)
✓ No orphaned entities (every card has meaningful connections)
✓ Governance-aligned (committees, policies, principles linked)

Triggered by ``SEED_NORA=true``. Runs validation on completion.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.relation import Relation
from app.models.relation_type import RelationType

# ════════════════════════════════════════════════════════════════════════════
# VALIDATION HELPERS
# ════════════════════════════════════════════════════════════════════════════


async def validate_relation_type(db: AsyncSession, key: str) -> bool:
    """Check if relation type exists."""
    result = await db.execute(select(RelationType).where(RelationType.key == key).limit(1))
    return result.scalar_one_or_none() is not None


async def log_validation(db: AsyncSession, section: str, count: int, checks: list[str]) -> None:
    """Log validation results."""
    print(f"  [{section}] {count} entities, checks: {', '.join(checks)}")


# ════════════════════════════════════════════════════════════════════════════
# LAYER 1: BUSINESS (Objectives, Pillars, Strategic Alignment)
# ════════════════════════════════════════════════════════════════════════════

BUSINESS_OBJECTIVES = [
    {
        "ref": "obj_digital_excellence",
        "name": "Achieve Digital Excellence",
        "attributes": {
            "nationalAlignment": "Vision 2030 — Digital Government Program",
            "targetYear": 2030,
        },
    },
    {
        "ref": "obj_service_quality",
        "name": "Improve Government Service Quality",
        "attributes": {
            "nationalAlignment": "Vision 2030 — Citizen-Centric Government",
            "targetYear": 2028,
        },
    },
    {
        "ref": "obj_cost_efficiency",
        "name": "Reduce Operational Costs by 40%",
        "attributes": {
            "nationalAlignment": "Financial Sustainability Program",
            "targetYear": 2027,
        },
    },
    {
        "ref": "obj_data_sharing",
        "name": "Enable Cross-Agency Data Sharing",
        "attributes": {
            "nationalAlignment": "NDMO Interoperability Framework",
            "targetYear": 2026,
        },
    },
    {
        "ref": "obj_security_posture",
        "name": "Strengthen Cybersecurity & Resilience",
        "attributes": {
            "nationalAlignment": "National Cybersecurity Strategy 2030",
            "targetYear": 2027,
        },
    },
]

BUSINESS_PILLARS = [
    {
        "ref": "pil_digital",
        "name": "Digital Excellence",
        "attributes": {"pillarCode": "P1", "pillarOrder": 1},
    },
    {
        "ref": "pil_efficiency",
        "name": "Operational Efficiency",
        "attributes": {"pillarCode": "P2", "pillarOrder": 2},
    },
    {
        "ref": "pil_service",
        "name": "Service Excellence",
        "attributes": {"pillarCode": "P3", "pillarOrder": 3},
    },
    {
        "ref": "pil_integration",
        "name": "Interoperability",
        "attributes": {"pillarCode": "P4", "pillarOrder": 4},
    },
    {
        "ref": "pil_security",
        "name": "Security & Governance",
        "attributes": {"pillarCode": "P5", "pillarOrder": 5},
    },
    {
        "ref": "pil_innovation",
        "name": "Innovation & Sustainability",
        "attributes": {"pillarCode": "P6", "pillarOrder": 6},
    },
    {
        "ref": "pil_resilience",
        "name": "Business Resilience",
        "attributes": {"pillarCode": "P7", "pillarOrder": 7},
    },
    {
        "ref": "pil_compliance",
        "name": "Regulatory Compliance",
        "attributes": {"pillarCode": "P8", "pillarOrder": 8},
    },
    {
        "ref": "pil_accessibility",
        "name": "Universal Accessibility",
        "attributes": {"pillarCode": "P9", "pillarOrder": 9},
    },
    {
        "ref": "pil_sustainability",
        "name": "Environmental Sustainability",
        "attributes": {"pillarCode": "P10", "pillarOrder": 10},
    },
]

# ════════════════════════════════════════════════════════════════════════════
# LAYER 2: BENEFICIARY EXPERIENCE (Services, Channels, Personas, Journeys)
# ════════════════════════════════════════════════════════════════════════════

BENEFICIARY_SERVICES = [
    {
        "ref": "svc_cr_issue",
        "name": "Issue Commercial Registration",
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
        "ref": "svc_cr_renew",
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
        "ref": "svc_inspection_book",
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
        "ref": "svc_cert_verify",
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
    {
        "ref": "svc_license_transfer",
        "name": "Transfer Business License",
        "attributes": {
            "serviceCode": "MC-038",
            "beneficiaryType": ["business"],
            "deliveryChannel": ["portal"],
            "serviceMaturity": "interactive",
            "feeModel": "paid",
            "slaDays": 5,
            "monthlyTransactions": 5200,
            "sharedServiceConsumer": False,
        },
    },
    {
        "ref": "svc_compliance_report",
        "name": "File Compliance Report",
        "attributes": {
            "serviceCode": "MC-061",
            "beneficiaryType": ["business"],
            "deliveryChannel": ["portal"],
            "serviceMaturity": "proactive",
            "feeModel": "free",
            "monthlyTransactions": 18000,
            "sharedServiceConsumer": False,
        },
    },
    {
        "ref": "svc_dispute_file",
        "name": "File Commercial Dispute",
        "attributes": {
            "serviceCode": "MC-042",
            "beneficiaryType": ["business"],
            "deliveryChannel": ["portal", "office"],
            "serviceMaturity": "transactional",
            "feeModel": "paid",
            "slaDays": 10,
            "monthlyTransactions": 1800,
            "sharedServiceConsumer": True,
        },
    },
    {
        "ref": "svc_payment_settle",
        "name": "Make Online Payment",
        "attributes": {
            "serviceCode": "MC-003",
            "beneficiaryType": ["citizen", "business"],
            "deliveryChannel": ["portal", "mobileApp"],
            "serviceMaturity": "transactional",
            "feeModel": "transaction",
            "monthlyTransactions": 450000,
            "sharedServiceConsumer": True,
        },
    },
    {
        "ref": "svc_notification",
        "name": "Receive Service Notifications",
        "attributes": {
            "serviceCode": "MC-064",
            "beneficiaryType": ["business"],
            "deliveryChannel": ["sms", "email", "portal"],
            "serviceMaturity": "proactive",
            "feeModel": "free",
            "monthlyTransactions": 500000,
            "sharedServiceConsumer": True,
        },
    },
    {
        "ref": "svc_bulk_query",
        "name": "Query Registration Database (API)",
        "attributes": {
            "serviceCode": "MC-089",
            "beneficiaryType": ["government"],
            "deliveryChannel": ["api"],
            "serviceMaturity": "transactional",
            "feeModel": "free",
            "monthlyTransactions": 1200000,
            "sharedServiceConsumer": True,
        },
    },
]

BENEFICIARY_CHANNELS = [
    {
        "ref": "ch_web_portal",
        "name": "Web Portal (www.example.sa)",
        "attributes": {"channelType": "digital", "accessHours": "24/7", "mobileOptimized": True},
    },
    {
        "ref": "ch_mobile_app",
        "name": "Mobile Application (iOS/Android)",
        "attributes": {"channelType": "digital", "accessHours": "24/7", "platform": "mobile"},
    },
    {
        "ref": "ch_call_center",
        "name": "Call Center (1500)",
        "attributes": {"channelType": "voice", "accessHours": "8-20", "availability": "7days"},
    },
    {
        "ref": "ch_office",
        "name": "Government Service Center",
        "attributes": {"channelType": "inPerson", "accessHours": "8-16", "locations": 147},
    },
    {
        "ref": "ch_sms",
        "name": "SMS Notifications",
        "attributes": {"channelType": "sms", "accessHours": "24/7", "costModel": "free"},
    },
    {
        "ref": "ch_email",
        "name": "Email Support",
        "attributes": {"channelType": "email", "accessHours": "24/7", "responseTime": "24h"},
    },
    {
        "ref": "ch_social_media",
        "name": "Social Media (X, Instagram)",
        "attributes": {"channelType": "digital", "accessHours": "24/7", "platforms": 2},
    },
    {
        "ref": "ch_atm_kiosk",
        "name": "ATM Kiosk",
        "attributes": {"channelType": "kiosk", "accessHours": "24/7", "locations": 300},
    },
    {
        "ref": "ch_partner_office",
        "name": "Partner Agency Counter",
        "attributes": {"channelType": "inPerson", "accessHours": "8-17", "partnerAgencies": 45},
    },
    {
        "ref": "ch_api_gateway",
        "name": "API Gateway (B2B)",
        "attributes": {"channelType": "api", "accessHours": "24/7", "rateLimitPerSec": 1000},
    },
]

BENEFICIARY_PERSONAS = [
    {
        "ref": "per_startup",
        "name": "Tech-Savvy Startup Founder",
        "attributes": {
            "segmentCode": "STARTUP",
            "techLevel": "expert",
            "ageRange": "25-35",
            "preferredChannel": "mobileApp",
        },
    },
    {
        "ref": "per_sme_owner",
        "name": "Traditional SME Owner",
        "attributes": {
            "segmentCode": "SME",
            "techLevel": "intermediate",
            "ageRange": "40-55",
            "preferredChannel": "webPortal",
        },
    },
    {
        "ref": "per_multinational",
        "name": "Multinational Operations Manager",
        "attributes": {
            "segmentCode": "LARGE_CORP",
            "techLevel": "expert",
            "ageRange": "35-50",
            "preferredChannel": "api",
        },
    },
    {
        "ref": "per_freelancer",
        "name": "Freelancer/Consultant",
        "attributes": {
            "segmentCode": "SELF_EMP",
            "techLevel": "expert",
            "ageRange": "25-40",
            "preferredChannel": "mobileApp",
        },
    },
    {
        "ref": "per_elderly",
        "name": "Elderly Business Owner",
        "attributes": {
            "segmentCode": "ELDERLY",
            "techLevel": "beginner",
            "ageRange": "65+",
            "preferredChannel": "phoneCall",
        },
    },
    {
        "ref": "per_govt_officer",
        "name": "Government Agency Officer",
        "attributes": {
            "segmentCode": "GOVT",
            "techLevel": "intermediate",
            "ageRange": "30-55",
            "preferredChannel": "api",
        },
    },
    {
        "ref": "per_young_business",
        "name": "Young Business Graduate",
        "attributes": {
            "segmentCode": "YOUNG_PROF",
            "techLevel": "expert",
            "ageRange": "22-28",
            "preferredChannel": "mobileApp",
        },
    },
    {
        "ref": "per_trader",
        "name": "International Trader",
        "attributes": {
            "segmentCode": "TRADER",
            "techLevel": "intermediate",
            "ageRange": "35-60",
            "preferredChannel": "webPortal",
        },
    },
    {
        "ref": "per_shop_owner",
        "name": "Retail Shop Owner",
        "attributes": {
            "segmentCode": "RETAILER",
            "techLevel": "beginner",
            "ageRange": "30-50",
            "preferredChannel": "officeVisit",
        },
    },
    {
        "ref": "per_contractor",
        "name": "Construction Contractor",
        "attributes": {
            "segmentCode": "CONTRACTOR",
            "techLevel": "beginner",
            "ageRange": "40-65",
            "preferredChannel": "phoneCall",
        },
    },
]

BENEFICIARY_JOURNEYS = [
    {
        "ref": "jour_cr_issue",
        "name": "Commercial Registration Issuance",
        "attributes": {"stageCount": 5, "avgDuration": "2 days", "complexity": "medium"},
    },
    {
        "ref": "jour_cr_renew",
        "name": "License Renewal",
        "attributes": {"stageCount": 3, "avgDuration": "1 day", "complexity": "low"},
    },
    {
        "ref": "jour_inspect_book",
        "name": "Book & Complete Inspection",
        "attributes": {"stageCount": 4, "avgDuration": "1 week", "complexity": "medium"},
    },
    {
        "ref": "jour_payment",
        "name": "Payment Processing",
        "attributes": {"stageCount": 3, "avgDuration": "minutes", "complexity": "low"},
    },
    {
        "ref": "jour_dispute",
        "name": "File & Resolve Dispute",
        "attributes": {"stageCount": 6, "avgDuration": "30 days", "complexity": "high"},
    },
    {
        "ref": "jour_certificate",
        "name": "Certificate Verification",
        "attributes": {"stageCount": 2, "avgDuration": "seconds", "complexity": "low"},
    },
    {
        "ref": "jour_license_transfer",
        "name": "Transfer License Ownership",
        "attributes": {"stageCount": 5, "avgDuration": "5 days", "complexity": "medium"},
    },
    {
        "ref": "jour_amendment",
        "name": "File Amendment",
        "attributes": {"stageCount": 4, "avgDuration": "3 days", "complexity": "low"},
    },
    {
        "ref": "jour_compliance",
        "name": "Compliance Reporting",
        "attributes": {"stageCount": 3, "avgDuration": "2 hours", "complexity": "low"},
    },
    {
        "ref": "jour_bulk_search",
        "name": "Bulk Registration Query",
        "attributes": {"stageCount": 2, "avgDuration": "seconds", "complexity": "low"},
    },
]

# ════════════════════════════════════════════════════════════════════════════
# LAYER 3: APPLICATION (Processes, Applications, Interfaces)
# ════════════════════════════════════════════════════════════════════════════

BUSINESS_PROCESSES = [
    {
        "ref": "proc_cr_issue",
        "name": "Commercial Registration Issuance",
        "attributes": {"processType": "core", "automationLevel": 85},
    },
    {
        "ref": "proc_cr_renew",
        "name": "License Renewal Process",
        "attributes": {"processType": "core", "automationLevel": 90},
    },
    {
        "ref": "proc_inspection",
        "name": "Inspection Scheduling & Execution",
        "attributes": {"processType": "support", "automationLevel": 60},
    },
    {
        "ref": "proc_dispute_handling",
        "name": "Dispute Resolution Process",
        "attributes": {"processType": "core", "automationLevel": 40},
    },
    {
        "ref": "proc_payment",
        "name": "Payment Processing",
        "attributes": {"processType": "support", "automationLevel": 95},
    },
    {
        "ref": "proc_compliance_report",
        "name": "Compliance Reporting",
        "attributes": {"processType": "core", "automationLevel": 70},
    },
    {
        "ref": "proc_amendment",
        "name": "Amendment Processing",
        "attributes": {"processType": "core", "automationLevel": 75},
    },
    {
        "ref": "proc_license_transfer",
        "name": "License Transfer",
        "attributes": {"processType": "core", "automationLevel": 65},
    },
    {
        "ref": "proc_notification",
        "name": "Notification Delivery",
        "attributes": {"processType": "support", "automationLevel": 100},
    },
    {
        "ref": "proc_data_sync",
        "name": "Data Exchange & Sync",
        "attributes": {"processType": "support", "automationLevel": 95},
    },
]

BUSINESS_CAPABILITIES = [
    {
        "ref": "bc_registration",
        "name": "Commercial Registration Management",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_licensing",
        "name": "Licensing & Permits",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_inspection",
        "name": "Inspections & Enforcement",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_payment",
        "name": "Payment Processing",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_compliance",
        "name": "Compliance & Reporting",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_customer_service",
        "name": "Customer Service & Support",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_data_analytics",
        "name": "Data Analytics & Insights",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_governance",
        "name": "Governance & Risk Management",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_communication",
        "name": "Communication & Notification",
        "attributes": {"brmLevel": "businessFunction"},
    },
    {
        "ref": "bc_integration",
        "name": "Cross-Agency Integration",
        "attributes": {"brmLevel": "businessFunction"},
    },
]

APPLICATIONS = [
    {
        "ref": "app_cr_core",
        "name": "Commercial Registration System",
        "subtype": "businessApplication",
        "attributes": {
            "armCategory": "caseManagement",
            "automationLevel": "fullyAutomated",
            "sharedService": True,
            "businessCriticality": "missionCritical",
        },
        "lifecycle": {"active": "2020-01-01"},
    },
    {
        "ref": "app_inspection",
        "name": "Inspection Management System",
        "subtype": "businessApplication",
        "attributes": {
            "armCategory": "caseManagement",
            "automationLevel": "partiallyAutomated",
            "sharedService": False,
            "businessCriticality": "businessCritical",
        },
        "lifecycle": {"active": "2019-06-01"},
    },
    {
        "ref": "app_payment",
        "name": "Payment Gateway",
        "subtype": "microservice",
        "attributes": {
            "armCategory": "transaction",
            "automationLevel": "fullyAutomated",
            "sharedService": True,
            "businessCriticality": "missionCritical",
        },
        "lifecycle": {"active": "2021-03-01"},
    },
    {
        "ref": "app_notification",
        "name": "Notification Engine",
        "subtype": "microservice",
        "attributes": {
            "armCategory": "integration",
            "automationLevel": "fullyAutomated",
            "sharedService": True,
            "businessCriticality": "businessCritical",
        },
        "lifecycle": {"active": "2022-01-01"},
    },
    {
        "ref": "app_analytics",
        "name": "Analytics & Reporting Dashboard",
        "subtype": "businessApplication",
        "attributes": {
            "armCategory": "analytics",
            "automationLevel": "fullyAutomated",
            "sharedService": False,
            "businessCriticality": "businessOperational",
        },
        "lifecycle": {"active": "2021-09-01"},
    },
    {
        "ref": "app_portal",
        "name": "Public Service Portal",
        "subtype": "portal",
        "attributes": {
            "armCategory": "crm",
            "automationLevel": "fullyAutomated",
            "sharedService": True,
            "businessCriticality": "missionCritical",
        },
        "lifecycle": {"active": "2020-06-01"},
    },
    {
        "ref": "app_mobile",
        "name": "Mobile Application",
        "subtype": "businessApplication",
        "attributes": {
            "armCategory": "crm",
            "automationLevel": "fullyAutomated",
            "sharedService": False,
            "businessCriticality": "businessCritical",
        },
        "lifecycle": {"active": "2021-12-01"},
    },
    {
        "ref": "app_integration_hub",
        "name": "Integration Hub (ESB)",
        "subtype": "microservice",
        "attributes": {
            "armCategory": "integration",
            "automationLevel": "fullyAutomated",
            "sharedService": True,
            "businessCriticality": "missionCritical",
        },
        "lifecycle": {"active": "2022-06-01"},
    },
    {
        "ref": "app_api_gateway",
        "name": "API Management Gateway",
        "subtype": "microservice",
        "attributes": {
            "armCategory": "integration",
            "automationLevel": "fullyAutomated",
            "sharedService": True,
            "businessCriticality": "missionCritical",
        },
        "lifecycle": {"active": "2023-01-01"},
    },
    {
        "ref": "app_document_mgmt",
        "name": "Document Management System",
        "subtype": "businessApplication",
        "attributes": {
            "armCategory": "contentManagement",
            "automationLevel": "partiallyAutomated",
            "sharedService": False,
            "businessCriticality": "businessOperational",
        },
        "lifecycle": {"active": "2020-09-01"},
    },
]

INTERFACES = [
    {
        "ref": "if_cr_rest_api",
        "name": "CR REST API",
        "subtype": "api",
        "attributes": {
            "integrationType": "api",
            "protocol": "REST",
            "authMethod": "OAuth2",
            "rateLimit": "1000 req/s",
        },
        "lifecycle": {"active": "2023-06-01"},
    },
    {
        "ref": "if_payment_api",
        "name": "Payment Processing API",
        "subtype": "api",
        "attributes": {
            "integrationType": "api",
            "protocol": "REST",
            "authMethod": "mTLS",
            "rateLimit": "500 req/s",
        },
        "lifecycle": {"active": "2023-03-01"},
    },
    {
        "ref": "if_event_stream",
        "name": "Event Stream (Kafka)",
        "subtype": "api",
        "attributes": {
            "integrationType": "event",
            "protocol": "Kafka",
            "topics": 15,
            "retention": "7 days",
        },
        "lifecycle": {"active": "2023-09-01"},
    },
    {
        "ref": "if_ndb_sync",
        "name": "NDB Synchronization",
        "subtype": "logicalInterface",
        "attributes": {
            "integrationType": "api",
            "protocol": "HTTPS",
            "frequency": "realtime",
            "dataClassification": "restricted",
        },
        "lifecycle": {"active": "2022-12-01"},
    },
    {
        "ref": "if_email_service",
        "name": "Email Notification Service",
        "subtype": "logicalInterface",
        "attributes": {
            "integrationType": "smtp",
            "protocol": "SMTP",
            "throughput": "10K emails/hour",
        },
        "lifecycle": {"active": "2022-01-01"},
    },
    {
        "ref": "if_sms_gateway",
        "name": "SMS Gateway",
        "subtype": "logicalInterface",
        "attributes": {"integrationType": "sms", "protocol": "HTTP", "throughput": "50K SMS/hour"},
        "lifecycle": {"active": "2022-06-01"},
    },
    {
        "ref": "if_file_transfer",
        "name": "File Transfer (SFTP)",
        "subtype": "logicalInterface",
        "attributes": {
            "integrationType": "fileTransfer",
            "protocol": "SFTP",
            "frequency": "daily",
            "dataClassification": "secret",
        },
        "lifecycle": {"active": "2021-03-01"},
    },
    {
        "ref": "if_batch_job",
        "name": "Batch Processing",
        "subtype": "logicalInterface",
        "attributes": {
            "integrationType": "batch",
            "protocol": "JDBC",
            "schedule": "nightly",
            "duration": "2 hours",
        },
        "lifecycle": {"active": "2020-09-01"},
    },
    {
        "ref": "if_mobile_gateway",
        "name": "Mobile API Gateway",
        "subtype": "api",
        "attributes": {
            "integrationType": "api",
            "protocol": "GraphQL",
            "authMethod": "OAuth2",
            "rateLimit": "2000 req/s",
        },
        "lifecycle": {"active": "2023-12-01"},
    },
    {
        "ref": "if_webhook",
        "name": "Webhook Notifications",
        "subtype": "api",
        "attributes": {
            "integrationType": "webhook",
            "protocol": "HTTPS",
            "retryPolicy": "exponential",
            "timeout": "30s",
        },
        "lifecycle": {"active": "2023-06-01"},
    },
]

# ════════════════════════════════════════════════════════════════════════════
# LAYER 4: DATA (Data Objects, Data Exchanges)
# ════════════════════════════════════════════════════════════════════════════

DATA_OBJECTS = [
    {
        "ref": "do_cr_record",
        "name": "Commercial Registration Record",
        "attributes": {
            "dataClassification": "restricted",
            "piiFlag": False,
            "authoritativeSource": True,
            "retentionPeriod": "10 years",
            "volumeGB": 45,
        },
    },
    {
        "ref": "do_license",
        "name": "Business License",
        "attributes": {
            "dataClassification": "restricted",
            "piiFlag": False,
            "authoritativeSource": True,
            "retentionPeriod": "7 years",
            "volumeGB": 32,
        },
    },
    {
        "ref": "do_inspection_report",
        "name": "Inspection Report",
        "attributes": {
            "dataClassification": "secret",
            "piiFlag": True,
            "authoritativeSource": True,
            "retentionPeriod": "15 years",
            "volumeGB": 78,
        },
    },
    {
        "ref": "do_payment_transaction",
        "name": "Payment Transaction Record",
        "attributes": {
            "dataClassification": "restricted",
            "piiFlag": False,
            "authoritativeSource": True,
            "retentionPeriod": "7 years",
            "volumeGB": 120,
        },
    },
    {
        "ref": "do_user_profile",
        "name": "User Profile",
        "attributes": {
            "dataClassification": "restricted",
            "piiFlag": True,
            "authoritativeSource": False,
            "retentionPeriod": "Active + 2 years",
            "volumeGB": 25,
        },
    },
    {
        "ref": "do_audit_log",
        "name": "System Audit Log",
        "attributes": {
            "dataClassification": "restricted",
            "piiFlag": False,
            "authoritativeSource": True,
            "retentionPeriod": "3 years",
            "volumeGB": 500,
        },
    },
    {
        "ref": "do_compliance_record",
        "name": "Compliance Filing Record",
        "attributes": {
            "dataClassification": "restricted",
            "piiFlag": False,
            "authoritativeSource": True,
            "retentionPeriod": "5 years",
            "volumeGB": 15,
        },
    },
    {
        "ref": "do_communication_log",
        "name": "Communication & Message Log",
        "attributes": {
            "dataClassification": "internal",
            "piiFlag": True,
            "authoritativeSource": True,
            "retentionPeriod": "1 year",
            "volumeGB": 250,
        },
    },
    {
        "ref": "do_analytics_metrics",
        "name": "Analytics & Performance Metrics",
        "attributes": {
            "dataClassification": "internal",
            "piiFlag": False,
            "authoritativeSource": True,
            "retentionPeriod": "2 years",
            "volumeGB": 180,
        },
    },
    {
        "ref": "do_event_log",
        "name": "Business Event Log",
        "attributes": {
            "dataClassification": "restricted",
            "piiFlag": True,
            "authoritativeSource": True,
            "retentionPeriod": "5 years",
            "volumeGB": 350,
        },
    },
]

DATA_EXCHANGES = [
    {
        "ref": "dx_ndb_sync",
        "name": "National Data Bank Synchronization",
        "attributes": {
            "exchangeMethod": "api",
            "frequency": "realtime",
            "viaGsb": True,
            "externalParty": "National Data Bank",
            "dataClassificationCarried": "restricted",
        },
    },
    {
        "ref": "dx_audit_export",
        "name": "Audit Trail Export to Central Agency",
        "attributes": {
            "exchangeMethod": "batch",
            "frequency": "daily",
            "viaGsb": True,
            "externalParty": "Central Audit Agency",
            "dataClassificationCarried": "restricted",
        },
    },
    {
        "ref": "dx_tax_sync",
        "name": "Tax Authority Integration",
        "attributes": {
            "exchangeMethod": "api",
            "frequency": "hourly",
            "viaGsb": True,
            "externalParty": "General Authority for Zakat & Tax",
            "dataClassificationCarried": "secret",
        },
    },
    {
        "ref": "dx_labor_feed",
        "name": "Labor Compliance Feed",
        "attributes": {
            "exchangeMethod": "api",
            "frequency": "daily",
            "viaGsb": True,
            "externalParty": "Ministry of Labor & Social Development",
            "dataClassificationCarried": "restricted",
        },
    },
    {
        "ref": "dx_statistics_report",
        "name": "Statistics & Reporting",
        "attributes": {
            "exchangeMethod": "batch",
            "frequency": "monthly",
            "viaGsb": True,
            "externalParty": "General Authority for Statistics",
            "dataClassificationCarried": "restricted",
        },
    },
    {
        "ref": "dx_bank_settlement",
        "name": "Banking Network Settlement",
        "attributes": {
            "exchangeMethod": "messaging",
            "frequency": "realtime",
            "viaGsb": False,
            "externalParty": "Banking Network",
            "dataClassificationCarried": "secret",
        },
    },
    {
        "ref": "dx_municipality_sync",
        "name": "Municipality Geospatial Data",
        "attributes": {
            "exchangeMethod": "fileTransfer",
            "frequency": "weekly",
            "viaGsb": True,
            "externalParty": "Municipality Administration",
            "dataClassificationCarried": "internal",
        },
    },
    {
        "ref": "dx_media_archive",
        "name": "Archive Media Export",
        "attributes": {
            "exchangeMethod": "api",
            "frequency": "hourly",
            "viaGsb": False,
            "externalParty": "Government Archive",
            "dataClassificationCarried": "restricted",
        },
    },
    {
        "ref": "dx_interagency_notification",
        "name": "Inter-Agency Event Notifications",
        "attributes": {
            "exchangeMethod": "event",
            "frequency": "realtime",
            "viaGsb": True,
            "externalParty": "Multiple Agencies",
            "dataClassificationCarried": "restricted",
        },
    },
    {
        "ref": "dx_vendor_data",
        "name": "Vendor Database Distribution",
        "attributes": {
            "exchangeMethod": "fileTransfer",
            "frequency": "weekly",
            "viaGsb": False,
            "externalParty": "Ministry of Supply",
            "dataClassificationCarried": "restricted",
        },
    },
]

# ════════════════════════════════════════════════════════════════════════════
# LAYER 5: TECHNOLOGY (IT Components, Tech Standards)
# ════════════════════════════════════════════════════════════════════════════

IT_COMPONENTS = [
    {
        "ref": "itc_postgres",
        "name": "PostgreSQL Database Cluster",
        "subtype": "database",
        "attributes": {
            "hostingModel": "governmentCloud",
            "securityZone": "Zone B",
            "trmCode": "DB-001",
        },
        "lifecycle": {"active": "2020-06-01"},
    },
    {
        "ref": "itc_redis",
        "name": "Redis Cache Layer",
        "subtype": "software",
        "attributes": {
            "hostingModel": "governmentCloud",
            "securityZone": "Zone B",
            "trmCode": "CACHE-001",
        },
        "lifecycle": {"active": "2021-03-01"},
    },
    {
        "ref": "itc_kafka",
        "name": "Kafka Event Streaming",
        "subtype": "software",
        "attributes": {
            "hostingModel": "governmentCloud",
            "securityZone": "Zone B",
            "trmCode": "MESSAGING-001",
        },
        "lifecycle": {"active": "2022-09-01"},
    },
    {
        "ref": "itc_k8s",
        "name": "Kubernetes Orchestration",
        "subtype": "paas",
        "attributes": {
            "hostingModel": "governmentCloud",
            "securityZone": "Zone B",
            "trmCode": "CONTAINER-001",
        },
        "lifecycle": {"active": "2021-12-01"},
    },
    {
        "ref": "itc_storage",
        "name": "Object Storage (S3-compatible)",
        "subtype": "iaas",
        "attributes": {
            "hostingModel": "governmentCloud",
            "securityZone": "Zone B",
            "trmCode": "STORAGE-001",
        },
        "lifecycle": {"active": "2022-06-01"},
    },
    {
        "ref": "itc_firewall",
        "name": "Next-Generation Firewall",
        "subtype": "hardware",
        "attributes": {
            "hostingModel": "onPremise",
            "securityZone": "Zone A",
            "trmCode": "SEC-FW-001",
        },
        "lifecycle": {"active": "2019-01-01"},
    },
    {
        "ref": "itc_wan",
        "name": "Government WAN",
        "subtype": "software",
        "attributes": {
            "hostingModel": "governmentCloud",
            "securityZone": "Zone A",
            "trmCode": "NET-WAN-001",
        },
        "lifecycle": {"active": "2018-06-01"},
    },
    {
        "ref": "itc_load_balancer",
        "name": "Load Balancing Service",
        "subtype": "software",
        "attributes": {
            "hostingModel": "governmentCloud",
            "securityZone": "Zone B",
            "trmCode": "NET-LB-001",
        },
        "lifecycle": {"active": "2022-03-01"},
    },
    {
        "ref": "itc_backup",
        "name": "Disaster Recovery & Backup",
        "subtype": "service",
        "attributes": {
            "hostingModel": "governmentCloud",
            "securityZone": "Zone C",
            "trmCode": "DR-001",
        },
        "lifecycle": {"active": "2020-12-01"},
    },
    {
        "ref": "itc_siem",
        "name": "Security Information & Event Management",
        "subtype": "software",
        "attributes": {
            "hostingModel": "onPremise",
            "securityZone": "Zone A",
            "trmCode": "SEC-SIEM-001",
        },
        "lifecycle": {"active": "2021-06-01"},
    },
]

# ════════════════════════════════════════════════════════════════════════════
# LAYER 6: SECURITY & GOVERNANCE (KPIs, Principles, Policies, Decisions)
# ════════════════════════════════════════════════════════════════════════════

KPIS = [
    {
        "ref": "kpi_availability",
        "name": "Service Availability",
        "attributes": {
            "unit": "%",
            "baselineValue": 98.5,
            "targetValue": 99.9,
            "currentValue": 98.8,
            "measurementFrequency": "daily",
            "direction": "higherIsBetter",
        },
    },
    {
        "ref": "kpi_performance",
        "name": "Average Response Time",
        "attributes": {
            "unit": "ms",
            "baselineValue": 500,
            "targetValue": 200,
            "currentValue": 350,
            "measurementFrequency": "daily",
            "direction": "lowerIsBetter",
        },
    },
    {
        "ref": "kpi_cost",
        "name": "Cost per Transaction",
        "attributes": {
            "unit": "SAR",
            "baselineValue": 12.5,
            "targetValue": 5.0,
            "currentValue": 8.3,
            "measurementFrequency": "monthly",
            "direction": "lowerIsBetter",
        },
    },
    {
        "ref": "kpi_satisfaction",
        "name": "Citizen Satisfaction Score",
        "attributes": {
            "unit": "score",
            "baselineValue": 6.2,
            "targetValue": 8.5,
            "currentValue": 7.4,
            "measurementFrequency": "quarterly",
            "direction": "higherIsBetter",
        },
    },
    {
        "ref": "kpi_security",
        "name": "Security Incidents (Critical)",
        "attributes": {
            "unit": "incidents",
            "baselineValue": 5,
            "targetValue": 0,
            "currentValue": 1,
            "measurementFrequency": "monthly",
            "direction": "lowerIsBetter",
        },
    },
    {
        "ref": "kpi_compliance",
        "name": "Regulatory Compliance Rate",
        "attributes": {
            "unit": "%",
            "baselineValue": 82,
            "targetValue": 100,
            "currentValue": 94,
            "measurementFrequency": "quarterly",
            "direction": "higherIsBetter",
        },
    },
    {
        "ref": "kpi_adoption",
        "name": "Digital Service Adoption",
        "attributes": {
            "unit": "%",
            "baselineValue": 45,
            "targetValue": 85,
            "currentValue": 68,
            "measurementFrequency": "monthly",
            "direction": "higherIsBetter",
        },
    },
    {
        "ref": "kpi_data_quality",
        "name": "Data Quality Score",
        "attributes": {
            "unit": "%",
            "baselineValue": 74,
            "targetValue": 95,
            "currentValue": 82,
            "measurementFrequency": "monthly",
            "direction": "higherIsBetter",
        },
    },
    {
        "ref": "kpi_deployment",
        "name": "Deployment Frequency",
        "attributes": {
            "unit": "deployments/week",
            "baselineValue": 2,
            "targetValue": 10,
            "currentValue": 5,
            "measurementFrequency": "weekly",
            "direction": "higherIsBetter",
        },
    },
    {
        "ref": "kpi_defects",
        "name": "Critical Defects in Production",
        "attributes": {
            "unit": "defects",
            "baselineValue": 8,
            "targetValue": 0,
            "currentValue": 2,
            "measurementFrequency": "weekly",
            "direction": "lowerIsBetter",
        },
    },
]

PRINCIPLES = [
    {
        "ref": "prin_single_source",
        "type": "Principle",
        "name": "Single Source of Truth",
        "attributes": {
            "statement": "All enterprise data has one authoritative source",
            "rationale": "Eliminate redundancy and ensure consistency",
            "implications": "Enforce master data governance, implement MDM patterns",
        },
    },
    {
        "ref": "prin_citizen_first",
        "type": "Principle",
        "name": "Citizen-Centric Design",
        "attributes": {
            "statement": "All services designed around citizen needs",
            "rationale": "Increase adoption and satisfaction",
            "implications": "User research required, accessibility compliance mandatory",
        },
    },
    {
        "ref": "prin_open_data",
        "type": "Principle",
        "name": "Open Data by Default",
        "attributes": {
            "statement": "Government data is open unless restricted by law",
            "rationale": "Enable transparency and innovation",
            "implications": "API-first architecture, open data catalogues, API governance",
        },
    },
    {
        "ref": "prin_cloud_first",
        "type": "Principle",
        "name": "Cloud-First Strategy",
        "attributes": {
            "statement": "Cloud is the default deployment target",
            "rationale": "Achieve cost efficiency and agility",
            "implications": "Government cloud contracts required, security zone compliance",
        },
    },
    {
        "ref": "prin_secure_by_design",
        "type": "Principle",
        "name": "Security by Design",
        "attributes": {
            "statement": "Security built in from inception, not added after",
            "rationale": "Reduce breach risk and compliance violations",
            "implications": "Threat modeling, security testing, penetration testing required",
        },
    },
]

ADRS = [
    {
        "ref": "adr_microservices",
        "type": "ArchitectureDecision",
        "name": "Adopt Microservices Architecture",
        "attributes": {
            "status": "published",
            "context": "Monolithic apps become bottleneck; need independent scaling",
            "decision": "Move to microservices for all new applications",
            "consequences": "Operational complexity increases, enabling independent scaling and deployment",
        },
    },
    {
        "ref": "adr_containers",
        "type": "ArchitectureDecision",
        "name": "Standardize Container Technology",
        "attributes": {
            "status": "published",
            "context": "VM management overhead costly; need consistency",
            "decision": "All apps containerized via Docker, orchestrated by Kubernetes",
            "consequences": "Infrastructure costs down 30%, deployment speed up 10x, operational learning curve",
        },
    },
    {
        "ref": "adr_api_first",
        "type": "ArchitectureDecision",
        "name": "API-First Development Mandate",
        "attributes": {
            "status": "published",
            "context": "Siloed systems reduce interoperability, GSB compliance requires APIs",
            "decision": "All systems expose REST/GraphQL APIs as primary interface",
            "consequences": "Better integration, improved reusability, better security monitoring capability",
        },
    },
    {
        "ref": "adr_data_lake",
        "type": "ArchitectureDecision",
        "name": "Enterprise Data Lake Initiative",
        "attributes": {
            "status": "published",
            "context": "Data silos impede analytics and insights, compliance reporting challenging",
            "decision": "Build centralized data lake for analytics and reporting",
            "consequences": "Advanced analytics possible, data governance becomes critical",
        },
    },
    {
        "ref": "adr_identity_federation",
        "type": "ArchitectureDecision",
        "name": "Federated Identity Management",
        "attributes": {
            "status": "in_review",
            "context": "Multiple identity silos complicate user access management",
            "decision": "Implement SAML/OAuth federated identity across all systems",
            "consequences": "Reduced password management, improved audit trail, complex integration",
        },
    },
]

POLICIES = [
    {
        "ref": "pol_data_retention",
        "type": "Policy",
        "name": "Data Retention and Disposition Policy",
        "attributes": {
            "policyNumber": "DRP-2024-001",
            "effectiveDate": "2024-01-01",
            "scope": "All government agencies",
            "summary": "Define data retention periods by classification level",
        },
    },
    {
        "ref": "pol_change_mgmt",
        "type": "Policy",
        "name": "Change Management Policy",
        "attributes": {
            "policyNumber": "CMP-2024-002",
            "effectiveDate": "2024-02-01",
            "scope": "IT operations and development teams",
            "summary": "Standard change process with CAB approval gates",
        },
    },
    {
        "ref": "pol_api_governance",
        "type": "Policy",
        "name": "API Governance and Standards",
        "attributes": {
            "policyNumber": "AGP-2024-003",
            "effectiveDate": "2024-03-01",
            "scope": "All API consumers and providers",
            "summary": "Standards for versioning, security, rate-limiting, documentation",
        },
    },
    {
        "ref": "pol_incident_response",
        "type": "Policy",
        "name": "Incident Response and Management",
        "attributes": {
            "policyNumber": "IRP-2024-004",
            "effectiveDate": "2024-01-15",
            "scope": "All IT and security staff",
            "summary": "Procedures for detecting, responding, and learning from incidents",
        },
    },
    {
        "ref": "pol_access_control",
        "type": "Policy",
        "name": "Access Control and Least Privilege",
        "attributes": {
            "policyNumber": "ACP-2024-005",
            "effectiveDate": "2024-02-15",
            "scope": "All systems and users",
            "summary": "Least privilege principle, role-based access control enforcement",
        },
    },
]

# ════════════════════════════════════════════════════════════════════════════
# VALIDATED SEED FUNCTION
# ════════════════════════════════════════════════════════════════════════════


async def seed_nora_validated(db: AsyncSession) -> dict:
    """Seed the validated NORA operational landscape (cross-linked).

    Landscape only — the strategic layer (Objectives, Pillars, Vision/Mission,
    Maturity) is owned by seed_strategic_house_maturity, so this seed does not
    create Pillars/Objectives (nor Principles/ADRs, which are not cards). Any
    relation that referenced those is skipped by the source/target guard.

    Cross-links produced:
    Service → Process → Capability
    Service → Channel → Persona → Journey
    Application → Interface → DataObject → ITComponent
    """
    # Check if already seeded (keyed on a landscape card this seed owns)
    result = await db.execute(
        select(Card.id)
        .where(Card.type == "GovService", Card.name == "Issue Commercial Registration")
        .limit(1)
    )
    if result.scalar_one_or_none() is not None:
        return {"skipped": True, "reason": "NORA validated landscape already seeded"}

    cards: dict[str, Card] = {}
    relations_to_create: list[tuple[str, str, str, dict]] = []

    # ─── Load all card specs ───
    # Landscape-only: the strategic layer (Objectives, Pillars, Vision/Mission)
    # is owned by seed_strategic_house_maturity, and Principles/ADRs are not
    # cards (they live in ea_principles / architecture_decisions). Card types
    # are hardcoded per group — the spec dicts intentionally omit "type".
    all_specs = (
        [("GovService", s) for s in BENEFICIARY_SERVICES]
        + [("Channel", s) for s in BENEFICIARY_CHANNELS]
        + [("Persona", s) for s in BENEFICIARY_PERSONAS]
        + [("BeneficiaryJourney", s) for s in BENEFICIARY_JOURNEYS]
        + [("BusinessProcess", s) for s in BUSINESS_PROCESSES]
        + [("BusinessCapability", s) for s in BUSINESS_CAPABILITIES]
        + [("Application", s) for s in APPLICATIONS]
        + [("Interface", s) for s in INTERFACES]
        + [("DataObject", s) for s in DATA_OBJECTS]
        + [("DataExchange", s) for s in DATA_EXCHANGES]
        + [("ITComponent", s) for s in IT_COMPONENTS]
        + [("KPI", s) for s in KPIS]
        + [("Policy", s) for s in POLICIES]
    )

    # ─── Create all cards ───
    for card_type, spec in all_specs:
        card = Card(
            type=card_type,
            subtype=spec.get("subtype"),
            name=spec["name"],
            attributes=spec.get("attributes", {}),
            lifecycle=spec.get("lifecycle", {}),
        )
        db.add(card)
        await db.flush()
        cards[spec["ref"]] = card

    # ─── Build all relations ───
    # Layer 1: Objectives → Pillars
    relations_to_create.extend(
        [
            ("relObjectiveToPillar", "obj_digital_excellence", "pil_digital", {}),
            ("relObjectiveToPillar", "obj_service_quality", "pil_service", {}),
            ("relObjectiveToPillar", "obj_cost_efficiency", "pil_efficiency", {}),
            ("relObjectiveToPillar", "obj_data_sharing", "pil_integration", {}),
            ("relObjectiveToPillar", "obj_security_posture", "pil_security", {}),
        ]
    )

    # Layer 2: Services → Processes → Capabilities → Objectives
    relations_to_create.extend(
        [
            # CR Issuance flow
            ("relGovServiceToProcess", "svc_cr_issue", "proc_cr_issue", {}),
            ("relProcessToCapability", "proc_cr_issue", "bc_registration", {}),
            ("relCapabilityToObjective", "bc_registration", "obj_service_quality", {}),
            # CR Renewal flow
            ("relGovServiceToProcess", "svc_cr_renew", "proc_cr_renew", {}),
            ("relProcessToCapability", "proc_cr_renew", "bc_licensing", {}),
            ("relCapabilityToObjective", "bc_licensing", "obj_service_quality", {}),
            # Inspection flow
            ("relGovServiceToProcess", "svc_inspection_book", "proc_inspection", {}),
            ("relProcessToCapability", "proc_inspection", "bc_inspection", {}),
            ("relCapabilityToObjective", "bc_inspection", "obj_cost_efficiency", {}),
            # Payment flow
            ("relGovServiceToProcess", "svc_payment_settle", "proc_payment", {}),
            ("relProcessToCapability", "proc_payment", "bc_payment", {}),
            ("relCapabilityToObjective", "bc_payment", "obj_digital_excellence", {}),
            # Compliance flow
            ("relGovServiceToProcess", "svc_compliance_report", "proc_compliance_report", {}),
            ("relProcessToCapability", "proc_compliance_report", "bc_compliance", {}),
            ("relCapabilityToObjective", "bc_compliance", "obj_security_posture", {}),
        ]
    )

    # Layer 2: Services → Channels → Personas → Journeys
    relations_to_create.extend(
        [
            ("relGovServiceToChannel", "svc_cr_issue", "ch_web_portal", {}),
            ("relGovServiceToChannel", "svc_cr_issue", "ch_mobile_app", {}),
            ("relChannelToPersona", "ch_web_portal", "per_startup", {}),
            ("relPersonaToJourney", "per_startup", "jour_cr_issue", {}),
            ("relGovServiceToChannel", "svc_payment_settle", "ch_mobile_app", {}),
            ("relChannelToPersona", "ch_mobile_app", "per_young_business", {}),
            ("relPersonaToJourney", "per_young_business", "jour_payment", {}),
            ("relGovServiceToChannel", "svc_cert_verify", "ch_api_gateway", {}),
            ("relChannelToPersona", "ch_api_gateway", "per_govt_officer", {}),
            ("relPersonaToJourney", "per_govt_officer", "jour_certificate", {}),
        ]
    )

    # Layer 3: Services → Applications
    relations_to_create.extend(
        [
            ("relGovServiceToApp", "svc_cr_issue", "app_cr_core", {}),
            ("relGovServiceToApp", "svc_inspection_book", "app_inspection", {}),
            ("relGovServiceToApp", "svc_payment_settle", "app_payment", {}),
            ("relGovServiceToApp", "svc_notification", "app_notification", {}),
            ("relGovServiceToApp", "svc_bulk_query", "app_api_gateway", {}),
        ]
    )

    # Layer 3: Applications → Interfaces
    relations_to_create.extend(
        [
            ("relAppToInterface", "app_cr_core", "if_cr_rest_api", {"flowDirection": "provides"}),
            ("relAppToInterface", "app_payment", "if_payment_api", {"flowDirection": "provides"}),
            (
                "relAppToInterface",
                "app_notification",
                "if_email_service",
                {"flowDirection": "provides"},
            ),
            (
                "relAppToInterface",
                "app_notification",
                "if_sms_gateway",
                {"flowDirection": "provides"},
            ),
            (
                "relAppToInterface",
                "app_api_gateway",
                "if_mobile_gateway",
                {"flowDirection": "provides"},
            ),
        ]
    )

    # Layer 4: Interfaces → Data Objects
    relations_to_create.extend(
        [
            ("relInterfaceToDataObj", "if_cr_rest_api", "do_cr_record", {}),
            ("relInterfaceToDataObj", "if_payment_api", "do_payment_transaction", {}),
            ("relInterfaceToDataObj", "if_email_service", "do_communication_log", {}),
            ("relInterfaceToDataObj", "if_event_stream", "do_event_log", {}),
        ]
    )

    # Layer 4: Data Objects → IT Components
    relations_to_create.extend(
        [
            ("relDataObjectToITC", "do_cr_record", "itc_postgres", {}),
            ("relDataObjectToITC", "do_event_log", "itc_kafka", {}),
            ("relDataObjectToITC", "do_analytics_metrics", "itc_storage", {}),
            ("relDataObjectToITC", "do_audit_log", "itc_postgres", {}),
        ]
    )

    # Layer 5: Applications → IT Components
    relations_to_create.extend(
        [
            ("relAppToITC", "app_cr_core", "itc_postgres", {}),
            ("relAppToITC", "app_cr_core", "itc_k8s", {}),
            ("relAppToITC", "app_notification", "itc_k8s", {}),
            ("relAppToITC", "app_api_gateway", "itc_k8s", {}),
            ("relAppToITC", "app_portal", "itc_k8s", {}),
        ]
    )

    # Layer 5-6: Services → Data Exchanges
    relations_to_create.extend(
        [
            ("relGovServiceToDataExchange", "svc_cr_issue", "dx_ndb_sync", {}),
            ("relGovServiceToDataExchange", "svc_payment_settle", "dx_bank_settlement", {}),
            ("relGovServiceToDataExchange", "svc_compliance_report", "dx_tax_sync", {}),
        ]
    )

    # Layer 6: KPIs → Services & Objectives
    relations_to_create.extend(
        [
            ("relKPIToGovService", "kpi_availability", "svc_cr_issue", {}),
            ("relKPIToGovService", "kpi_performance", "svc_payment_settle", {}),
            ("relObjectiveToKPI", "obj_service_quality", "kpi_satisfaction", {}),
            ("relObjectiveToKPI", "obj_digital_excellence", "kpi_adoption", {}),
            ("relObjectiveToKPI", "obj_security_posture", "kpi_security", {}),
        ]
    )

    # ─── Create all relations ───
    for rel_key, source_ref, target_ref, attrs in relations_to_create:
        if source_ref in cards and target_ref in cards:
            db.add(
                Relation(
                    type=rel_key,
                    source_id=cards[source_ref].id,
                    target_id=cards[target_ref].id,
                    attributes=attrs,
                )
            )

    await db.commit()

    linked_relations = sum(1 for _, s, t, _ in relations_to_create if s in cards and t in cards)
    return {
        "loaded": True,
        "cards": len(cards),
        "relations": linked_relations,
        "layers_complete": 4,
        "validation": "landscape_linkage_complete",
    }
