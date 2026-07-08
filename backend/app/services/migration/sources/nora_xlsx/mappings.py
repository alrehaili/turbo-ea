"""Mapping tables for the NORA/DGA data-collection template adapter.

[FORK FEATURE] — noraPlan.md WP6.6.

The DGA's حصر البيانات templates (one workbook per EA domain: Business,
Applications, Technology, Security, Data, Beneficiary Experience) are the
official data-collection vehicle of the updated National EA Framework
methodology (phase 2.2). This adapter ingests the six workbooks directly.

Native entity-type keys below are invented by this adapter (the templates
have no machine ids); they exist so the generic staging pipeline can route
sheets to Turbo EA card types. Option-value translations come verbatim
from the templates' Lookup sheets.
"""

from __future__ import annotations

# Native (adapter-invented) entity type → Turbo EA card-type key.
TYPE_MAPPING: dict[str, str] = {
    "GovService": "GovService",
    "BusinessProcess": "BusinessProcess",
    "Application": "Application",
    "Interface": "Interface",
    "DataObject": "DataObject",
    # Technology-architecture sheets — all land on ITComponent, the NEA
    # building block is the subtype (profile v2 pass 4d seeds them).
    "PhysicalHost": "ITComponent",
    "VirtualServer": "ITComponent",
    "NetworkDevice": "ITComponent",
    "Storage": "ITComponent",
    "InfraTool": "ITComponent",
    "InfraService": "ITComponent",
    # Security-architecture sheets.
    "SecurityHardware": "ITComponent",
    "SecuritySoftware": "ITComponent",
    "SecurityService": "ITComponent",
}

# ITComponent subtype per native type (goes into SourceEntity.category).
ITC_SUBTYPE_BY_NATIVE_TYPE: dict[str, str] = {
    "PhysicalHost": "physicalHost",
    "VirtualServer": "virtualServer",
    "NetworkDevice": "networkDevice",
    "Storage": "storage",
    "InfraTool": "infraTool",
    "InfraService": "infraService",
    "SecurityHardware": "securityHardware",
    "SecuritySoftware": "securitySoftware",
    "SecurityService": "securityService",
}

# Native relation name → Turbo EA relation-type key. Directions are
# already emitted in TEA convention by the parser, so FLIP_DIRECTION is
# empty.
RELATION_MAPPING: dict[str, str] = {
    # Service row's "التطبيقات المستخدمة لتنفيذ الخدمة" column.
    "serviceToApplication": "relGovServiceToApp",
    # Procedure row's "خدمات ذات علاقة" column (service → process).
    "serviceToProcess": "relGovServiceToProcess",
    # Procedure row's "الأنظمة المستخدمة لتنفيذ الإجراء" column.
    "processToApplication": "relProcessToApp",
    # Integration-point row's consumer / producer columns.
    "applicationToInterface": "relAppToInterface",
}

FLIP_DIRECTION: frozenset[str] = frozenset()

# The templates carry no field-schema sheets — no metamodel extension.
FIELD_TYPE_MAPPING: dict[str, str] = {}

# The stakeholder sheet has names without emails — not importable as
# subscriptions in v1 (documented descope in noraPlan.md WP6.6).
SUBSCRIPTION_ROLE_MAPPING: dict[str, str] = {}

HIERARCHY_RELATIONS: frozenset[str] = frozenset()


# ---------------------------------------------------------------------------
# Option-value translation (Lookup-sheet Arabic/bilingual labels → TEA
# option keys). Matching is normalized containment — template revisions
# vary in spacing/hamza, and the Applications workbook combines both
# languages in one cell ("COTS – كود مصدري جاهز").
# ---------------------------------------------------------------------------

SERVICE_CLASSIFICATION = {"رئيسي": "main", "فرعي": "sub"}
PROCESS_CLASSIFICATION = {"رئيسي": "main", "فرعي": "sub"}
SERVICE_TYPE = {"اداري": "administrative", "محوري": "core", "داعم": "supporting"}
AUTOMATION_LEVEL = {
    "كليا": "fullyAutomated",
    "جزئي": "partiallyAutomated",
    "غير مؤتمت": "manual",
}
# Seed BusinessProcess.automationLevel shares the same option keys.
SERVICE_MATURITY = {
    "معلوماتي": "informational",
    "تفاعلي": "interactive",
    "اجرائي": "transactional",
    "تكاملي": "proactive",
}
FEE_MODEL = {"نعم": "paid", "لا": "free"}
DELIVERY_CHANNEL = {
    "اتصال": "callCenter",
    "الموقع": "portal",
    "موقع": "portal",
    "بوابه": "portal",
    "تطبيق": "mobileApp",
    "مركز خدم": "serviceCenter",
    "فرع": "serviceCenter",
    "كشك": "kiosk",
    "جهاز خدمه ذاتيه": "kiosk",
}
APP_LAYER = {
    "access": "access",
    "الوصول": "access",
    "core": "core",
    "الاساسي": "core",
    "support": "support",
    "الداعم": "support",
    "data": "data",
    "بالبيانات": "data",
    "infrastructure": "infrastructure",
    "التحتيه": "infrastructure",
}
DEVELOPMENT_TYPE = {"cots": "cots", "جاهز": "cots", "bespoke": "bespoke", "مصنوع": "bespoke"}
SOURCE_TYPE = {
    "in-house": "inHouse",
    "داخلي": "inHouse",
    "outsourcing": "outsourced",
    "خارجيه": "outsourced",
    "third party": "managedByThirdParty",
    "طرف ثالث": "managedByThirdParty",
}
CRITICALITY = {
    "حرج": "missionCritical",
    "عالي": "businessCritical",
    "متوسط": "businessOperational",
    "منخفض": "administrativeService",
}
ARCHITECTURE_PATTERN = {
    "n-tier": "nTier",
    "client": "clientServer",
    "microservice": "microservices",
    "event": "eventDriven",
}
# Application status → Turbo EA lifecycle phase (the deliberate WP6.2
# mapping decision: applicationStatus is not a field, lifecycle is).
APP_STATUS_LIFECYCLE = {
    "تحت التطوير": "plan",
    "under development": "plan",
    "اطلق حديثا": "phaseIn",
    "phase in": "phaseIn",
    "نشط": "active",
    "active": "active",
    "مخطط للاقفال": "phaseOut",
    "phase out": "phaseOut",
}
INTEGRATION_SCOPE = {"داخلي": "internal", "خارجي": "external"}
LINK_TYPE = {
    "مباشر": "direct",
    "direct": "direct",
    "منصه التكامل": "integrationPlatform",
    "gsb": "gsb",
    "gsn": "gsn",
}
DATA_CLASSIFICATION = {
    "سري للغايه": "topSecret",
    "سري": "secret",
    "مقيد": "restricted",
    "عام": "public",
}
SUPPORT_CONTRACT_STATUS = {
    "فعال": "active",
    "نشط": "active",
    "active": "active",
    "منتهي": "expired",
    "expire": "expired",
}
OPERATION_TYPE = {
    "فريق داخلي": "internalTeam",
    "internal team": "internalTeam",
    "مزود خدم": "serviceProvider",
    "service provider": "serviceProvider",
    "مختلط": "hybrid",
    "hybrid": "hybrid",
}
ENVIRONMENT = {
    "انتاجي": "production",
    "production": "production",
    "اختباري": "test",
    "test": "test",
    "تجريبي": "staging",
    "staging": "staging",
    "التعافي": "disasterRecovery",
    "dr": "disasterRecovery",
}
YES_NO = {"نعم": True, "yes": True, "لا": False, "no": False}
