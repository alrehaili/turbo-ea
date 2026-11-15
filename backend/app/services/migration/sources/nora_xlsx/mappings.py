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
    "Policy": "Policy",
    "ModelTemplate": "ModelTemplate",
    "DataAttribute": "DataAttribute",
    # Technology-architecture sheets land on the NORA technology building
    # blocks (DGA Content Meta Model §5.3.8) — never on the generic
    # ITComponent, which the NORA profile hides (NORAreadiness.md B-6).
    "PhysicalHost": "PhysicalHost",
    "VirtualServer": "Server",
    "NetworkDevice": "NetworkDevice",
    "Storage": "Storage",
    "InfraTool": "InfrastructureManagementTool",
    "InfraService": "InfrastructureService",
    # Security-architecture sheets (§5.3.9).
    "SecurityHardware": "SecurityHardware",
    "SecuritySoftware": "SecuritySoftware",
    "SecurityService": "SecurityService",
}

# Subtype per native type (goes into SourceEntity.category): a virtual-server
# row is a Server of the ``virtual`` subtype; the other sheets are a type of
# their own.
SUBTYPE_BY_NATIVE_TYPE: dict[str, str] = {"VirtualServer": "virtual"}

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
    # Policy row's related services / procedures columns.
    "policyToService": "relPolicyToGovService",
    "policyToProcess": "relPolicyToProcess",
    # Model/template row's related services / procedures columns.
    "serviceToModel": "relGovServiceToTemplate",
    "processToModel": "relNora2BusinessProcessModelTemplate",
    # Data-attribute rows name their data entity.
    "dataObjectToAttribute": "relDataObjectToAttribute",
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
# NORA technology fields (the template's "جزء/قطاع الشبكة", "نوع التشغيل" and
# "البيئة" columns → the native types' option keys).
NETWORK_SEGMENT = {
    "dmz": "dmz",
    "extranet": "extranet",
    "internet": "internet",
    "wan": "wan",
    "lan": "lan",
    "air gapped": "airGapped",
    "airgapped": "airGapped",
    "data center": "dataCenter",
    "datacenter": "dataCenter",
    "مركز البيانات": "dataCenter",
}
TYPE_OF_OPERATION = {
    "فريق داخلي": "inHouse",
    "internal team": "inHouse",
    "in-house": "inHouse",
    "مزود خدم": "serviceProvider",
    "service provider": "serviceProvider",
    "مختلط": "other",
    "hybrid": "other",
}
SERVER_ENVIRONMENT = {
    "انتاج": "production",
    "production": "production",
    "تطوير": "development",
    "development": "development",
    "اختبار": "testing",
    "test": "testing",
    "تجريبي": "testing",
    "staging": "testing",
}
# Policy, model/template and data-attribute sheets (NORAreadiness.md B-6).
POLICY_TYPE = {"داخلي": "internal", "خارجي": "external", "حكومي": "external"}
POLICY_STATUS = {"مفعل": "active", "موقوف": "suspended", "ملغي": "cancelled"}
MODEL_TYPE = {
    "طلب خدمه": "serviceRequestForm",
    "حصر بيانات": "dataCollectionForm",
    "قالب دليل": "guideTemplate",
    "قالب سياسه": "policyTemplate",
    "اخري": "other",
}
# "Y" / "N" (the data-attribute sheets) match only on their own: a longer
# value that merely starts with "n" is not read as "no".
YES_NO = {"نعم": True, "yes": True, "y": True, "لا": False, "no": False, "n": False}
