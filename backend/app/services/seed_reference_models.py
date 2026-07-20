"""Reference Models seed data — one published starter RM per NEA domain.

[FORK FEATURE] — Complete Reference Model catalogue:
✓ BRM (Business Reference Model) — 8 items (root + 7 business areas)
✓ ARM (Applications Reference Model) — 16 items (3 groups × applications)
✓ DRM (Data Reference Model) — 9 items (root + 8 data domains)
✓ TRM (Technology Reference Model) — 9 items (root + 8 technology services)
✓ BXRM (Beneficiary Experience RM) — 10 items
✓ SRM (Security Reference Model) — 10 items

BRM/ARM/DRM/TRM follow the RMPlan example hierarchies (generic-enterprise
theme), bilingual (English + Arabic). All hierarchical with parent links.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.card_type import CardType
from app.models.reference_model import ReferenceModel, ReferenceModelItem

# ════════════════════════════════════════════════════════════════════════════
# BRM — Business Reference Model (banded capability map: band → category →
# capability). Renders as the dark capability-map poster. Bilingual.
# ════════════════════════════════════════════════════════════════════════════

# Nested definition: (band_code, band_en, band_ar, [ (cat_en, cat_ar,
# [ (cap_en, cap_ar), ... ]) ... ]). Flattened into the standard
# {code: {name, name_ar, parent}} dict below (codes: BRM-A / BRM-A.1 / BRM-A.1.1).
_BRM_BANDS = [
    (
        "A",
        "Administrative & Regulatory Capabilities",
        "القدرات الإدارية والتنظيمية",
        [
            (
                "Strategy",
                "الاستراتيجية",
                [
                    ("Strategic Planning", "التخطيط الاستراتيجي"),
                    ("Enterprise Performance Management", "إدارة الأداء المؤسسي"),
                    ("Change Management", "إدارة التغيير"),
                ],
            ),
            (
                "Relations, Media & Communication",
                "العلاقات والإعلام والاتصال",
                [
                    ("Corporate Communication & Media", "الاتصال المؤسسي والإعلام"),
                    ("Content Management", "إدارة المحتوى"),
                    ("Internal Communication", "التواصل الداخلي"),
                    ("Brand Management", "إدارة العلامة التجارية"),
                ],
            ),
            (
                "Companies & Investment Management",
                "الشركات وإدارة الاستثمار",
                [
                    ("Investment Management", "إدارة الاستثمارات"),
                    ("Partnership Management", "إدارة الشراكات"),
                    ("Contracts & Procurement", "العقود والمشتريات"),
                    ("Investment", "الاستثمار"),
                ],
            ),
            (
                "Enterprise Projects",
                "المشاريع المؤسسية",
                [
                    ("Portfolio & Project Management", "إدارة المحافظ والمشاريع"),
                    ("Project Governance", "حوكمة المشاريع"),
                    ("Administrative Governance", "الحوكمة الإدارية"),
                ],
            ),
            (
                "Human Resources",
                "الموارد البشرية",
                [
                    ("Human Resources Management", "إدارة الموارد البشرية"),
                    ("Learning & Development", "التعلم والتطوير"),
                    ("Corporate Culture", "الثقافة المؤسسية"),
                ],
            ),
            (
                "Legal Affairs",
                "الشؤون القانونية",
                [
                    ("Legal Support", "الدعم القانوني"),
                    ("Compliance & Governance", "الامتثال والحوكمة"),
                    ("Regulatory Relations", "العلاقات التنظيمية"),
                ],
            ),
            (
                "President's Office",
                "مكتب الرئيس",
                [
                    ("International Meetings & Relations", "اللقاءات والاتصالات الدولية"),
                    ("Correspondence", "المراسلات"),
                    ("Archives", "المحفوظات"),
                ],
            ),
            (
                "Quality, Risk & Compliance",
                "الجودة والمخاطر والامتثال",
                [
                    ("Quality Management", "إدارة الجودة"),
                    ("Risk Management", "إدارة المخاطر"),
                    ("Compliance", "الامتثال"),
                    ("Business Continuity", "استمرارية الأعمال"),
                    ("Internal Audit", "المراجعة الداخلية"),
                ],
            ),
        ],
    ),
    (
        "B",
        "Core Business Capabilities",
        "قدرات الأعمال المحورية",
        [
            (
                "Enterprise Organization",
                "التنظيم المؤسسي",
                [
                    ("Policies & Regulations", "السياسات واللوائح"),
                    ("Transformation & Development Programs", "برامج التحول والتطوير"),
                    ("Corporate Governance", "الحوكمة المؤسسية"),
                ],
            ),
            (
                "Sustainability & Innovation",
                "الاستدامة والابتكار",
                [
                    ("Sustainability Management", "إدارة الاستدامة"),
                    ("Corporate Innovation", "الابتكار المؤسسي"),
                ],
            ),
            (
                "Customer Management",
                "إدارة العملاء",
                [
                    ("Customer Experience Management", "إدارة تجربة العملاء"),
                    ("Customer Service", "خدمة العملاء"),
                ],
            ),
            (
                "Risk Management",
                "إدارة المخاطر",
                [
                    ("Monitoring & Control", "المراقبة والسيطرة"),
                    ("Risk Assessment", "تقييم المخاطر"),
                    ("Risk Treatment", "معالجة المخاطر"),
                ],
            ),
            (
                "Performance Management",
                "إدارة الأداء",
                [
                    ("Performance Measurement", "قياس الأداء"),
                    ("Performance Improvement", "تحسين الأداء"),
                    ("Risk Identification", "تحديد المخاطر"),
                ],
            ),
        ],
    ),
    (
        "C",
        "Operational Capabilities",
        "القدرات التشغيلية",
        [
            (
                "Financial Resources",
                "الموارد المالية",
                [
                    ("Budget Management", "إدارة الميزانية"),
                    ("Accounting & Payments", "المحاسبة والدفعات"),
                    ("Asset Management", "إدارة الأصول"),
                ],
            ),
            (
                "Supply Chain Management",
                "إدارة سلسلة الإمداد",
                [
                    ("Procurement", "المشتريات"),
                    ("Supplier Management", "إدارة الموردين"),
                    ("Inventory Management", "إدارة المخزون"),
                    ("Logistics", "اللوجستيات"),
                ],
            ),
            (
                "Production & Services",
                "الإنتاج والخدمات",
                [
                    ("Product & Service Design", "تصميم المنتجات والخدمات"),
                    ("Operations Management", "إدارة العمليات"),
                    ("Quality & Safety", "الجودة والسلامة"),
                ],
            ),
            (
                "Marketing & Sales",
                "التسويق والمبيعات",
                [
                    ("Market Research", "أبحاث السوق"),
                    ("Product Development", "تطوير المنتجات"),
                    ("Sales", "المبيعات"),
                    ("Customer Relationship Management", "إدارة علاقات العملاء"),
                ],
            ),
            (
                "Operations & Services",
                "التشغيل والخدمات",
                [
                    ("Service Delivery", "تقديم الخدمات"),
                    ("Customer Support", "دعم العملاء"),
                    ("Facilities Management", "إدارة المرافق"),
                    ("After-sales Service", "خدمة ما بعد البيع"),
                ],
            ),
            (
                "Information Technology",
                "تقنية المعلومات",
                [
                    ("Infrastructure Management", "إدارة البنية التحتية"),
                    ("Application Development", "تطوير التطبيقات"),
                    ("Technical Support Services", "خدمات الدعم الفني"),
                    ("Data Management", "إدارة البيانات"),
                ],
            ),
        ],
    ),
    (
        "D",
        "Enabling Capabilities",
        "القدرات التمكينية",
        [
            (
                "Human Resources",
                "الموارد البشرية",
                [
                    ("Talent Management", "إدارة المواهب"),
                    ("Training & Development", "التدريب والتطوير"),
                    ("Knowledge Management", "إدارة المعرفة"),
                ],
            ),
            (
                "Information Technology",
                "تقنية المعلومات",
                [
                    ("Technical Governance", "الحوكمة التقنية"),
                    ("Data Management", "إدارة البيانات"),
                    ("Information Security", "أمن المعلومات"),
                    ("Systems Operation", "تشغيل الأنظمة"),
                ],
            ),
            (
                "Facilities & Support Services",
                "المرافق والخدمات المساندة",
                [
                    ("Facilities Management", "إدارة المرافق"),
                    ("Maintenance & Operation", "الصيانة والتشغيل"),
                    ("Support Services", "خدمات الدعم المساندة"),
                ],
            ),
            (
                "Corporate Support",
                "الدعم المؤسسي",
                [
                    ("Document Management", "إدارة الوثائق"),
                    ("Administrative Correspondence", "المراسلات الإدارية"),
                    ("Records Archiving", "أرشفة السجلات"),
                ],
            ),
            (
                "Financial Affairs",
                "الشؤون المالية",
                [
                    ("Revenue Management", "إدارة الإيرادات"),
                    ("Payments", "المدفوعات"),
                    ("Financial Reporting", "التقارير المالية"),
                ],
            ),
        ],
    ),
]


def _build_banded(prefix: str, bands: list) -> dict:
    """Flatten a nested (band → category → capability) definition into the
    standard {code: {name, name_ar, parent}} dict (codes: X-A / X-A.1 / X-A.1.1)."""
    out: dict = {}
    for band_code, band_en, band_ar, cats in bands:
        b = f"{prefix}-{band_code}"
        out[b] = {"name": band_en, "name_ar": band_ar, "parent": None}
        for ci, (cat_en, cat_ar, caps) in enumerate(cats, start=1):
            c = f"{b}.{ci}"
            out[c] = {"name": cat_en, "name_ar": cat_ar, "parent": b}
            for pi, (cap_en, cap_ar) in enumerate(caps, start=1):
                out[f"{c}.{pi}"] = {"name": cap_en, "name_ar": cap_ar, "parent": c}
    return out


BRM_HIERARCHY = _build_banded("BRM", _BRM_BANDS)

# Leaf capability codes that demo BusinessCapability cards map to (brmCode), so
# the capability map shows real coverage. A representative spread across bands.
BRM_DEMO_CARD_CODES: list[tuple[str, str, str]] = [
    # (brmCode, card name EN, card name AR)
    ("BRM-A.1.1", "Corporate Strategy Office", "مكتب الاستراتيجية المؤسسية"),
    ("BRM-A.1.2", "Enterprise Performance Platform", "منصة الأداء المؤسسي"),
    ("BRM-A.2.1", "Corporate Communications Hub", "مركز الاتصال المؤسسي"),
    ("BRM-A.5.1", "HR Management System", "نظام إدارة الموارد البشرية"),
    ("BRM-A.6.2", "Compliance & Governance Suite", "منظومة الامتثال والحوكمة"),
    ("BRM-A.8.2", "Enterprise Risk Register", "سجل المخاطر المؤسسي"),
    ("BRM-B.1.1", "Policy & Regulation Library", "مكتبة السياسات واللوائح"),
    ("BRM-B.3.1", "Customer Experience Platform", "منصة تجربة العملاء"),
    ("BRM-C.1.1", "Budgeting & Planning System", "نظام الميزانية والتخطيط"),
    ("BRM-C.2.2", "Supplier Management Portal", "بوابة إدارة الموردين"),
    ("BRM-C.6.4", "Enterprise Data Platform", "منصة بيانات المنشأة"),
    ("BRM-D.2.3", "Information Security Center", "مركز أمن المعلومات"),
    ("BRM-D.4.1", "Document Management System", "نظام إدارة الوثائق"),
]

# Per-domain demo inventory cards mapped (via the domain's code field) to leaf
# items of the published model, so every reference-model map shows real
# coverage. Only seeded when the target card type exists (guarded). One card is
# deliberately marked retiring (phaseOut) per domain to exercise gap analysis.
# domain → (card_type, code_field, [(code, name_en, name_ar, retiring?), ...])
DEMO_INVENTORY_CARDS: dict[str, tuple[str, str, list[tuple]]] = {
    "applications": (
        "Application",
        "armCode",
        [
            ("ARM-1.1.1", "Operations Monitoring Suite", "منظومة مراقبة العمليات", False),
            ("ARM-1.1.2", "Strategic Resource Planner", "مخطط الموارد الاستراتيجية", False),
            ("ARM-1.1.4", "Distribution Tracker", "متتبع التوزيع", True),
            ("ARM-1.2.1", "Case Management System", "نظام إدارة الحالات", False),
            ("ARM-1.2.3", "Document Management Platform", "منصة إدارة الوثائق", False),
            ("ARM-1.3.1", "Enterprise ERP", "نظام تخطيط الموارد المؤسسية", False),
            ("ARM-1.3.2", "HR Information System", "نظام معلومات الموارد البشرية", False),
        ],
    ),
    "data": (
        "DataObject",
        "drmCode",
        [
            ("DRM-A.1.1", "Organization Registry", "سجل المنظمة", False),
            ("DRM-A.1.3", "Beneficiary Master", "بيانات المستفيدين الرئيسية", False),
            ("DRM-A.2.1", "Service Catalogue Store", "مخزن كتالوج الخدمات", False),
            ("DRM-B.1.1", "Operations Datastore", "مخزن بيانات العمليات", False),
            ("DRM-B.2.1", "Transactions Ledger", "سجل المعاملات", False),
            ("DRM-C.1.1", "KPI Data Mart", "سوق بيانات المؤشرات", False),
            ("DRM-C.2.3", "Data Classification Registry", "سجل تصنيف البيانات", True),
        ],
    ),
    "technology": (
        "ITComponent",
        "trmCode",
        [
            ("TRM-A.1.1", "Private Cloud Platform", "منصة السحابة الخاصة", False),
            ("TRM-A.1.3", "Enterprise Storage Array", "مصفوفة التخزين المؤسسية", False),
            ("TRM-A.2.1", "Core Network Fabric", "نسيج الشبكة الأساسي", False),
            ("TRM-B.1.1", "Relational Database Cluster", "عنقود قواعد البيانات العلائقية", False),
            ("TRM-B.2.1", "Integration Bus", "ناقل التكامل", False),
            ("TRM-C.1.1", "Observability Stack", "منصة الرصد", False),
            ("TRM-C.2.1", "Identity Provider", "مزود الهوية", True),
        ],
    ),
    "beneficiaryExperience": (
        "GovService",
        "bxrmCode",
        [
            ("BXRM-A.1.1", "Unified Service Portal", "بوابة الخدمات الموحدة", False),
            ("BXRM-A.1.2", "Accessible Mobile App", "التطبيق المتنقل الميسّر", False),
            ("BXRM-A.2.1", "Self-Service Experience", "تجربة الخدمة الذاتية", False),
            ("BXRM-B.1.1", "Service Availability Monitor", "مراقب توافر الخدمة", False),
            ("BXRM-B.2.1", "Feedback & Support Center", "مركز التغذية الراجعة والدعم", False),
        ],
    ),
    "security": (
        "SecurityControl",
        "srmCode",
        [
            ("SRM-A.1.2", "MFA Service", "خدمة التحقق متعدد العوامل", False),
            ("SRM-A.2.1", "RBAC Authorization Service", "خدمة التخويل حسب الدور", False),
            ("SRM-B.1.1", "Encryption Gateway", "بوابة التشفير", False),
            ("SRM-B.2.2", "Vulnerability Scanner", "ماسح الثغرات", False),
            ("SRM-C.1.1", "SIEM Platform", "منصة إدارة الأحداث الأمنية", False),
            ("SRM-C.2.1", "Incident Response Runbook", "دليل الاستجابة للحوادث", True),
        ],
    ),
}

# ════════════════════════════════════════════════════════════════════════════
# ARM — Applications Reference Model (10 items)
# ════════════════════════════════════════════════════════════════════════════

ARM_HIERARCHY = {
    "ARM-1.0": {
        "name": "Enterprise Applications",
        "name_ar": "تطبيقات المنشأة",
        "parent": None,
    },
    "ARM-1.1": {
        "name": "Core Mission Applications",
        "name_ar": "التطبيقات الأساسية للمهام",
        "parent": "ARM-1.0",
    },
    "ARM-1.1.1": {
        "name": "Operations Monitoring",
        "name_ar": "مراقبة العمليات",
        "parent": "ARM-1.1",
    },
    "ARM-1.1.2": {
        "name": "Strategic Resource Management",
        "name_ar": "إدارة الموارد الاستراتيجية",
        "parent": "ARM-1.1",
    },
    "ARM-1.1.3": {
        "name": "Transactions Monitoring",
        "name_ar": "مراقبة المعاملات",
        "parent": "ARM-1.1",
    },
    "ARM-1.1.4": {
        "name": "Distribution Monitoring",
        "name_ar": "مراقبة التوزيع",
        "parent": "ARM-1.1",
    },
    "ARM-1.1.5": {
        "name": "Early Warning & Alerts",
        "name_ar": "الإنذار المبكر والتنبيهات",
        "parent": "ARM-1.1",
    },
    "ARM-1.2": {
        "name": "Shared Business Applications",
        "name_ar": "تطبيقات الأعمال المشتركة",
        "parent": "ARM-1.0",
    },
    "ARM-1.2.1": {
        "name": "Case Management",
        "name_ar": "إدارة الحالات",
        "parent": "ARM-1.2",
    },
    "ARM-1.2.2": {
        "name": "Workflow Management",
        "name_ar": "إدارة سير العمل",
        "parent": "ARM-1.2",
    },
    "ARM-1.2.3": {
        "name": "Document Management",
        "name_ar": "إدارة الوثائق",
        "parent": "ARM-1.2",
    },
    "ARM-1.2.4": {
        "name": "Reporting & Analytics",
        "name_ar": "التقارير والتحليلات",
        "parent": "ARM-1.2",
    },
    "ARM-1.3": {
        "name": "Corporate Applications",
        "name_ar": "التطبيقات المؤسسية",
        "parent": "ARM-1.0",
    },
    "ARM-1.3.1": {
        "name": "Enterprise Resource Planning (ERP)",
        "name_ar": "تخطيط موارد المؤسسة",
        "parent": "ARM-1.3",
    },
    "ARM-1.3.2": {
        "name": "Human Resources",
        "name_ar": "الموارد البشرية",
        "parent": "ARM-1.3",
    },
    "ARM-1.3.3": {
        "name": "Procurement",
        "name_ar": "المشتريات",
        "parent": "ARM-1.3",
    },
}

# ════════════════════════════════════════════════════════════════════════════
# DRM — Data Reference Model (banded: band → subject area → data entity)
# ════════════════════════════════════════════════════════════════════════════

_DRM_BANDS = [
    (
        "A",
        "Master & Reference Data",
        "البيانات الرئيسية والمرجعية",
        [
            (
                "Organization & People",
                "المنظمة والأشخاص",
                [
                    ("Organization Data", "بيانات المنظمة"),
                    ("Employee Data", "بيانات الموظفين"),
                    ("Beneficiary Data", "بيانات المستفيدين"),
                ],
            ),
            (
                "Products & Services",
                "المنتجات والخدمات",
                [
                    ("Service Catalogue Data", "بيانات كتالوج الخدمات"),
                    ("Product Data", "بيانات المنتجات"),
                ],
            ),
            (
                "Reference & Code Sets",
                "البيانات المرجعية والرموز",
                [
                    ("Classification Codes", "رموز التصنيف"),
                    ("Geospatial & Location Data", "البيانات الجغرافية والمكانية"),
                ],
            ),
        ],
    ),
    (
        "B",
        "Operational & Transactional Data",
        "البيانات التشغيلية والمعاملات",
        [
            (
                "Operations",
                "العمليات",
                [
                    ("Operations Data", "بيانات العمليات"),
                    ("Supply Chain Data", "بيانات سلسلة الإمداد"),
                    ("Case & Request Data", "بيانات الحالات والطلبات"),
                ],
            ),
            (
                "Finance & Commerce",
                "المالية والتجارة",
                [
                    ("Transaction Data", "بيانات المعاملات"),
                    ("Market & Price Data", "بيانات السوق والأسعار"),
                ],
            ),
        ],
    ),
    (
        "C",
        "Analytical & Governance Data",
        "بيانات التحليل والحوكمة",
        [
            (
                "Analytics",
                "التحليلات",
                [
                    ("Reporting & KPI Data", "بيانات التقارير والمؤشرات"),
                    ("Risk & Forecast Data", "بيانات المخاطر والتنبؤ"),
                ],
            ),
            (
                "Data Governance",
                "حوكمة البيانات",
                [
                    ("Metadata & Catalogue", "البيانات الوصفية والكتالوج"),
                    ("Data Quality Data", "بيانات جودة البيانات"),
                    ("Data Classification & Privacy", "تصنيف البيانات والخصوصية"),
                ],
            ),
        ],
    ),
]
DRM_HIERARCHY = _build_banded("DRM", _DRM_BANDS)

# ════════════════════════════════════════════════════════════════════════════
# TRM — Technology Reference Model (banded: band → domain → technology service)
# ════════════════════════════════════════════════════════════════════════════

_TRM_BANDS = [
    (
        "A",
        "Platform & Infrastructure",
        "المنصات والبنية التحتية",
        [
            (
                "Hosting & Compute",
                "الاستضافة والحوسبة",
                [
                    ("Hosting & Cloud", "الاستضافة والحوسبة السحابية"),
                    ("Compute & Containers", "الحوسبة والحاويات"),
                    ("Storage", "التخزين"),
                ],
            ),
            (
                "Network",
                "الشبكات",
                [
                    ("Network Services", "خدمات الشبكات"),
                    ("Connectivity & Edge", "الاتصال والحافة"),
                ],
            ),
        ],
    ),
    (
        "B",
        "Data & Integration",
        "البيانات والتكامل",
        [
            (
                "Data Platform",
                "منصة البيانات",
                [
                    ("Databases", "قواعد البيانات"),
                    ("Data Warehouse & Lake", "مستودع وبحيرة البيانات"),
                ],
            ),
            (
                "Integration",
                "التكامل",
                [
                    ("Integration Platform", "منصة التكامل"),
                    ("API Gateway", "بوابة الواجهات البرمجية"),
                    ("Event & Messaging", "الأحداث والمراسلة"),
                ],
            ),
        ],
    ),
    (
        "C",
        "Operations & Security",
        "التشغيل والأمن",
        [
            (
                "Operations",
                "التشغيل",
                [
                    ("Monitoring & Observability", "المراقبة والرصد"),
                    ("End-user Computing", "حوسبة المستخدم النهائي"),
                ],
            ),
            (
                "Security Technology",
                "تقنيات الأمن",
                [
                    ("Identity & Access Management", "إدارة الهوية والصلاحيات"),
                    ("Security Technology Services", "خدمات تقنيات الأمن"),
                ],
            ),
        ],
    ),
]
TRM_HIERARCHY = _build_banded("TRM", _TRM_BANDS)

# ════════════════════════════════════════════════════════════════════════════
# BXRM — Beneficiary Experience Reference Model (banded, bilingual)
# ════════════════════════════════════════════════════════════════════════════

_BXRM_BANDS = [
    (
        "A",
        "Access & Channels",
        "الوصول والقنوات",
        [
            (
                "Accessibility",
                "إتاحة الوصول",
                [
                    ("Multi-Channel Availability", "التوافر متعدد القنوات"),
                    ("Digital Accessibility (WCAG)", "الوصول الرقمي (WCAG)"),
                ],
            ),
            (
                "Experience & Usability",
                "التجربة وسهولة الاستخدام",
                [
                    ("Usability & Interface Design", "سهولة الاستخدام وتصميم الواجهة"),
                    ("Personalization & Preferences", "التخصيص والتفضيلات"),
                ],
            ),
        ],
    ),
    (
        "B",
        "Service Quality & Trust",
        "جودة الخدمة والثقة",
        [
            (
                "Quality & Performance",
                "الجودة والأداء",
                [
                    ("Response Time & Reliability", "زمن الاستجابة والموثوقية"),
                    ("Service Continuity", "استمرارية الخدمة"),
                ],
            ),
            (
                "Feedback & Trust",
                "التغذية الراجعة والثقة",
                [
                    ("Feedback & Support", "التغذية الراجعة والدعم"),
                    ("Privacy & Trust", "الخصوصية والثقة"),
                ],
            ),
        ],
    ),
]
BXRM_HIERARCHY = _build_banded("BXRM", _BXRM_BANDS)

# ════════════════════════════════════════════════════════════════════════════
# SRM — Security Reference Model (banded, bilingual)
# ════════════════════════════════════════════════════════════════════════════

_SRM_BANDS = [
    (
        "A",
        "Identity & Access",
        "الهوية والوصول",
        [
            (
                "Authentication",
                "التوثيق",
                [
                    ("User Authentication Methods", "طرق توثيق المستخدم"),
                    ("Multi-Factor Authentication (MFA)", "التحقق متعدد العوامل"),
                ],
            ),
            (
                "Authorization",
                "التخويل",
                [
                    ("Role-Based Access Control (RBAC)", "التحكم في الوصول حسب الدور"),
                    ("Privileged Access Management", "إدارة الوصول المتميز"),
                ],
            ),
        ],
    ),
    (
        "B",
        "Data & Application Protection",
        "حماية البيانات والتطبيقات",
        [
            (
                "Data Protection",
                "حماية البيانات",
                [
                    (
                        "Data Encryption (At-Rest & In-Transit)",
                        "تشفير البيانات (الساكنة والمنقولة)",
                    ),
                    ("Key Management", "إدارة المفاتيح"),
                ],
            ),
            (
                "Application Security",
                "أمن التطبيقات",
                [
                    ("Secure Development", "التطوير الآمن"),
                    ("Vulnerability Management", "إدارة الثغرات"),
                ],
            ),
        ],
    ),
    (
        "C",
        "Detection & Response",
        "الكشف والاستجابة",
        [
            (
                "Monitoring",
                "المراقبة",
                [
                    ("Security Monitoring & Detection", "المراقبة والكشف الأمني"),
                    ("Threat Intelligence", "الاستخبارات حول التهديدات"),
                ],
            ),
            (
                "Response & Recovery",
                "الاستجابة والتعافي",
                [
                    ("Incident Response & Recovery", "الاستجابة للحوادث والتعافي"),
                    ("Business Continuity & DR", "استمرارية الأعمال والتعافي من الكوارث"),
                ],
            ),
        ],
    ),
]
SRM_HIERARCHY = _build_banded("SRM", _SRM_BANDS)

# ════════════════════════════════════════════════════════════════════════════
# SEED FUNCTION
# ════════════════════════════════════════════════════════════════════════════


async def seed_reference_models(db: AsyncSession) -> dict:
    """Seed 6 published Reference Models (one per NORA domain) with hierarchies.

    Idempotent **per key** — each model carries a stable ``key`` so re-running
    is a no-op and this coexists with the NORA profile's built-in "kit preview"
    starters (which use their own ``nea_*_preview`` keys). We publish these so
    they become the active RM per domain (publishing supersedes any prior
    published RM of the same domain; the draft kit previews are untouched).

    Creates up to 60 ReferenceModelItems across 6 domains.
    """
    # key, domain, name, description, hierarchy
    rm_data = [
        (
            "nora_kit_business",
            "business",
            "Business Reference Model (BRM)",
            "Business architecture framework",
            BRM_HIERARCHY,
        ),
        (
            "nora_kit_applications",
            "applications",
            "Applications Reference Model (ARM)",
            "Application categorization",
            ARM_HIERARCHY,
        ),
        (
            "nora_kit_data",
            "data",
            "Data Reference Model (DRM)",
            "Data classification framework",
            DRM_HIERARCHY,
        ),
        (
            "nora_kit_technology",
            "technology",
            "Technology Reference Model (TRM)",
            "Technology standards",
            TRM_HIERARCHY,
        ),
        (
            "nora_kit_beneficiary",
            "beneficiaryExperience",
            "Beneficiary Experience RM (BXRM)",
            "User experience standards",
            BXRM_HIERARCHY,
        ),
        (
            "nora_kit_security",
            "security",
            "Security Reference Model (SRM)",
            "Security standards",
            SRM_HIERARCHY,
        ),
    ]

    # Which of our keys already exist? Skip those (idempotent per key).
    keys = [k for (k, *_rest) in rm_data]
    existing_keys = {
        k
        for (k,) in (
            await db.execute(select(ReferenceModel.key).where(ReferenceModel.key.in_(keys)))
        ).all()
    }

    now = datetime.now(timezone.utc)
    total_items = 0
    models_created = 0
    domains_seeded: list[str] = []

    for key, domain, name, description, hierarchy in rm_data:
        if key in existing_keys:
            continue

        # Publishing supersedes: demote any currently-published RM of this domain.
        published = (
            (
                await db.execute(
                    select(ReferenceModel).where(
                        ReferenceModel.domain == domain,
                        ReferenceModel.status == "published",
                    )
                )
            )
            .scalars()
            .all()
        )
        for prev in published:
            prev.status = "archived"

        model = ReferenceModel(
            key=key,
            domain=domain,
            name=name,
            description=description,
            version="1.0",
            source="national",
            status="published",  # active RM for the domain
            built_in=True,
            published_at=now,
        )
        db.add(model)
        await db.flush()
        models_created += 1
        domains_seeded.append(domain)

        # Items with parent relationships (parents precede children in dict order).
        item_map: dict[str, ReferenceModelItem] = {}
        codes = list(hierarchy.keys())
        for code, spec in hierarchy.items():
            parent_id = None
            if spec["parent"]:
                parent_id = item_map[spec["parent"]].id
            item = ReferenceModelItem(
                model_id=model.id,
                parent_id=parent_id,
                code=code,
                name=spec["name"],
                name_ar=spec.get("name_ar"),
                sort_order=codes.index(code),
            )
            db.add(item)
            await db.flush()
            item_map[code] = item
            total_items += 1

    # Demo inventory cards mapped to each model's leaves via the domain code
    # field, so every capability map shows real coverage. Per domain: only when
    # the target card type exists and the demo cards aren't already present
    # (idempotent by name); skipped silently otherwise. One card per domain is
    # marked retiring (phaseOut) to exercise gap analysis.
    # (domain, card_type, code_field, rows[(code, en, ar, retiring)])
    demo_plan: list[tuple[str, str, str, list[tuple]]] = [
        (
            "business",
            "BusinessCapability",
            "brmCode",
            [(c, en, ar, False) for (c, en, ar) in BRM_DEMO_CARD_CODES],
        )
    ]
    for dom, (ct, field, rows) in DEMO_INVENTORY_CARDS.items():
        demo_plan.append((dom, ct, field, rows))

    cards_created = 0
    for dom, card_type, code_field, rows in demo_plan:
        if dom not in domains_seeded:
            continue
        ct_exists = (
            await db.execute(select(CardType.key).where(CardType.key == card_type))
        ).first()
        if ct_exists is None:
            continue
        row_names = [en for (_c, en, _ar, _r) in rows]
        existing_names = {
            n
            for (n,) in (
                await db.execute(
                    select(Card.name).where(Card.type == card_type, Card.name.in_(row_names))
                )
            ).all()
        }
        for code, name, name_ar, retiring in rows:
            if name in existing_names:
                continue
            lifecycle = (
                {"active": "2020-01-01", "phaseOut": "2024-06-01"}
                if retiring
                else {"active": "2024-01-01"}
            )
            db.add(
                Card(
                    type=card_type,
                    name=name,
                    attributes={code_field: code, "nameAr": name_ar},
                    lifecycle=lifecycle,
                )
            )
            cards_created += 1

    await db.commit()

    if models_created == 0 and cards_created == 0:
        return {"skipped": True, "reason": "Reference Models already seeded (all keys present)"}

    return {
        "loaded": True,
        "reference_models": models_created,
        "reference_model_items": total_items,
        "demo_inventory_cards": cards_created,
        "domains": domains_seeded,
        "status": "published",
        "validation": "hierarchy_complete_with_parent_links",
    }
