"""NORA framework profile — Saudi National Overall Reference Architecture support.

[FORK FEATURE] — see noraPlan.md WP1.1.

Turbo EA stays framework-neutral: one canonical metamodel, one landscape. The
NORA profile is an **additive, idempotent** overlay that injects the NORA/NEA
alignment fields (BRM / ARM / DRM / TRM codes, NDMO data classification, GSB
integration flags, …) into the built-in card types as a dedicated
"NORA Alignment" section. No parallel card types are ever created and nothing
is removed when the profile is applied — a TOGAF-oriented install that never
enables the profile is entirely unaffected.

Activation paths:

* ``SEED_PROFILE=nora`` env var — applied once at startup on installs that have
  no stored profile choice yet (fresh installs).
* ``PATCH /settings/framework-profile`` — admin opt-in at runtime.

The applied profile version is persisted in
``app_settings.general_settings.noraProfileVersion`` so future profile
revisions can upgrade in place (the apply function only ever adds fields that
are missing — admin customisations, moved fields and edited labels survive).

Switching back to the ``togaf`` profile only flips the stored flag; the NORA
fields (and any data captured in them) are intentionally preserved. Removing
them is an explicit admin action in the metamodel editor.

All new fields carry ``weight: 0`` so enabling the profile never degrades
existing data-quality scores; agencies that want the NORA fields to count can
raise the weights per field in the metamodel admin.
"""

from __future__ import annotations

from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import config as app_config
from app.core.permissions import (
    DEFAULT_CARD_PERMISSIONS_BY_ROLE,
    MEMBER_PERMISSIONS,
    VIEWER_PERMISSIONS,
)
from app.models.app_settings import AppSettings
from app.models.card_type import CardType
from app.models.relation_type import RelationType
from app.models.role import Role
from app.models.stakeholder_role_definition import StakeholderRoleDefinition

# v2 (WP6.2): field alignment to the Dec-2024 EA Content Meta Model + the six
# official حصر البيانات data-collection templates (see noraPlan.md Phase 6).
# v3: NORA 2.0 six-layer model — Business / Beneficiary Experience /
# Application / Data / Technology / Security categories + the
# BeneficiaryJourney, Channel and SecurityControl card types.
# v4: GFSA EA Metamodel v3 alignment (agency deck, 2026-07) — Persona + Policy
# card types, journey Phase/Step subtypes + Journey Mapping fields, the
# ITComponent "Technical Specification" section (WP6.3's field half), and the
# remaining building-block attribute gaps on existing types.
# v5: WP6.4 security-domain completion — `usageRole` attribute (protects) on
# the Application → ITComponent relation type and the NCA ECC scanner scope
# extended to flag applications without a linked security component.
# v6: Pillar as a first-class card type (user decision — supersedes the v4
# Objective `pillar` subtype, which stays for backwards compatibility) + the
# Objective → Pillar "supports" relation.
# v7: WP100.2 — Saudi government organizational-hierarchy subtypes on
# Organization (sector / generalDepartment / department / sectionUnit).
# Reconciliation with the v6 `orgUnitType` field: subtype = internal
# hierarchy level of a unit; `orgUnitType` = kind of legal entity the whole
# organization is. The `publicAdministration` option's Arabic label is
# renamed («إدارة عامة» → «جهة إدارية عامة») so it no longer collides with
# the generalDepartment subtype (guarded rewrite — admin-customised labels
# are never overwritten).
# v8: WP100.3 — Reference Models: kit-preview starter RMs seeded (draft,
# national, built_in) + the last two RM code fields (`bxrmCode` on GovService,
# `srmCode` on SecurityControl) so all six domains have a landing field.
NORA_PROFILE_VERSION = 8

# Old→new category rewrites for the v3 six-layer model, keyed by card-type
# key. Guarded: a type is only moved while its category still equals the old
# default, so admin-customised categories are never overwritten. Mirrors
# Alembic migration 137 — both are idempotent, whichever runs first wins.
SIX_LAYER_CATEGORY_MOVES: dict[str, tuple[str, str]] = {
    "Objective": ("Strategy & Transformation", "Business"),
    "Platform": ("Strategy & Transformation", "Business"),
    "Initiative": ("Strategy & Transformation", "Business"),
    "KPI": ("Strategy & Transformation", "Business"),
    "Organization": ("Business Architecture", "Business"),
    "BusinessCapability": ("Business Architecture", "Business"),
    "BusinessContext": ("Business Architecture", "Business"),
    "BusinessProcess": ("Business Architecture", "Business"),
    "GovService": ("Business Architecture", "Beneficiary Experience"),
    "Application": ("Application & Data", "Application"),
    "Interface": ("Application & Data", "Application"),
    "DataObject": ("Application & Data", "Data"),
    "DataExchange": ("Application & Data", "Data"),
    "ITComponent": ("Technical Architecture", "Technology"),
    "TechCategory": ("Technical Architecture", "Technology"),
    "Provider": ("Technical Architecture", "Technology"),
}

FRAMEWORK_PROFILES = ("togaf", "nora")

NORA_SECTION = "NORA Alignment"

# The 9 non-English locales every metamodel translation dict must carry.
_LOCALES = ("de", "fr", "es", "it", "pt", "zh", "ru", "da", "ar")


def _tr(de: str, fr: str, es: str, it: str, pt: str, zh: str, ru: str, da: str, ar: str) -> dict:
    """Compact translations-dict builder (order fixed: de fr es it pt zh ru da ar)."""
    return {
        "de": de,
        "fr": fr,
        "es": es,
        "it": it,
        "pt": pt,
        "zh": zh,
        "ru": ru,
        "da": da,
        "ar": ar,
    }


NORA_SECTION_TRANSLATIONS = _tr(
    "NORA-Ausrichtung",
    "Alignement NORA",
    "Alineación NORA",
    "Allineamento NORA",
    "Alinhamento NORA",
    "NORA 对齐",
    "Соответствие NORA",
    "NORA-tilpasning",
    "مواءمة نورا (NORA)",
)

# ---------------------------------------------------------------------------
# Field definitions per built-in card type.
#
# Codes (brmCode / armCode / drmCode / trmCode) are free text until the NEA
# reference models are imported (noraPlan.md WP5.1); the option lists below are
# deliberately small, generic placeholders that admins (or the future NEA
# catalogue import) can extend via the metamodel editor.
# ---------------------------------------------------------------------------

NORA_TYPE_FIELDS: dict[str, list[dict]] = {
    "BusinessCapability": [
        {
            "key": "brmCode",
            "label": "BRM Code",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "BRM-Code",
                "Code BRM",
                "Código BRM",
                "Codice BRM",
                "Código BRM",
                "BRM 代码",
                "Код BRM",
                "BRM-kode",
                "رمز BRM",
            ),
        },
        {
            "key": "brmLevel",
            "label": "BRM Level",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "BRM-Ebene",
                "Niveau BRM",
                "Nivel BRM",
                "Livello BRM",
                "Nível BRM",
                "BRM 层级",
                "Уровень BRM",
                "BRM-niveau",
                "مستوى BRM",
            ),
            "options": [
                {
                    "key": "businessArea",
                    "label": "Business Area",
                    "color": "#1565c0",
                    "translations": _tr(
                        "Geschäftsbereich",
                        "Domaine d'activité",
                        "Área de negocio",
                        "Area di business",
                        "Área de negócio",
                        "业务领域",
                        "Сфера деятельности",
                        "Forretningsområde",
                        "مجال الأعمال",
                    ),
                },
                {
                    "key": "lineOfBusiness",
                    "label": "Line of Business",
                    "color": "#1e88e5",
                    "translations": _tr(
                        "Geschäftsfeld",
                        "Ligne de métier",
                        "Línea de negocio",
                        "Linea di business",
                        "Linha de negócio",
                        "业务线",
                        "Направление деятельности",
                        "Forretningslinje",
                        "خط الأعمال",
                    ),
                },
                {
                    "key": "businessFunction",
                    "label": "Business Function",
                    "color": "#42a5f5",
                    "translations": _tr(
                        "Geschäftsfunktion",
                        "Fonction métier",
                        "Función de negocio",
                        "Funzione di business",
                        "Função de negócio",
                        "业务职能",
                        "Бизнес-функция",
                        "Forretningsfunktion",
                        "الوظيفة الأعمالية",
                    ),
                },
                {
                    "key": "subBusinessFunction",
                    "label": "Sub-Business Function",
                    "color": "#90caf9",
                    "translations": _tr(
                        "Untergeschäftsfunktion",
                        "Sous-fonction métier",
                        "Subfunción de negocio",
                        "Sottofunzione di business",
                        "Subfunção de negócio",
                        "子业务职能",
                        "Подфункция бизнеса",
                        "Underforretningsfunktion",
                        "الوظيفة الأعمالية الفرعية",
                    ),
                },
            ],
        },
        {
            "key": "neaAlignment",
            "label": "NEA Alignment",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "NEA-Ausrichtung",
                "Alignement NEA",
                "Alineación NEA",
                "Allineamento NEA",
                "Alinhamento NEA",
                "NEA 对齐",
                "Соответствие NEA",
                "NEA-tilpasning",
                "مواءمة البنية المؤسسية الوطنية (NEA)",
            ),
        },
    ],
    "Application": [
        {
            "key": "armCode",
            "label": "ARM Code",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "ARM-Code",
                "Code ARM",
                "Código ARM",
                "Codice ARM",
                "Código ARM",
                "ARM 代码",
                "Код ARM",
                "ARM-kode",
                "رمز ARM",
            ),
        },
        {
            "key": "armCategory",
            "label": "ARM Category",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "ARM-Kategorie",
                "Catégorie ARM",
                "Categoría ARM",
                "Categoria ARM",
                "Categoria ARM",
                "ARM 类别",
                "Категория ARM",
                "ARM-kategori",
                "فئة ARM",
            ),
            "options": [
                {
                    "key": "caseManagement",
                    "label": "Case Management",
                    "translations": _tr(
                        "Fallmanagement",
                        "Gestion de dossiers",
                        "Gestión de casos",
                        "Gestione dei casi",
                        "Gestão de casos",
                        "案件管理",
                        "Управление делами",
                        "Sagsbehandling",
                        "إدارة الحالات",
                    ),
                },
                {
                    "key": "erp",
                    "label": "ERP",
                    "translations": _tr(
                        "ERP",
                        "ERP",
                        "ERP",
                        "ERP",
                        "ERP",
                        "企业资源计划 (ERP)",
                        "ERP",
                        "ERP",
                        "تخطيط موارد المؤسسة (ERP)",
                    ),
                },
                {
                    "key": "crm",
                    "label": "CRM",
                    "translations": _tr(
                        "CRM",
                        "CRM",
                        "CRM",
                        "CRM",
                        "CRM",
                        "客户关系管理 (CRM)",
                        "CRM",
                        "CRM",
                        "إدارة علاقات العملاء (CRM)",
                    ),
                },
                {
                    "key": "portal",
                    "label": "Portal",
                    "translations": _tr(
                        "Portal",
                        "Portail",
                        "Portal",
                        "Portale",
                        "Portal",
                        "门户",
                        "Портал",
                        "Portal",
                        "بوابة إلكترونية",
                    ),
                },
                {
                    "key": "contentManagement",
                    "label": "Content Management",
                    "translations": _tr(
                        "Content-Management",
                        "Gestion de contenu",
                        "Gestión de contenidos",
                        "Gestione dei contenuti",
                        "Gestão de conteúdo",
                        "内容管理",
                        "Управление контентом",
                        "Indholdsstyring",
                        "إدارة المحتوى",
                    ),
                },
                {
                    "key": "analytics",
                    "label": "Analytics & BI",
                    "translations": _tr(
                        "Analytik & BI",
                        "Analytique et BI",
                        "Analítica y BI",
                        "Analisi e BI",
                        "Análise e BI",
                        "分析与商业智能",
                        "Аналитика и BI",
                        "Analyse og BI",
                        "التحليلات وذكاء الأعمال",
                    ),
                },
                {
                    "key": "integration",
                    "label": "Integration",
                    "translations": _tr(
                        "Integration",
                        "Intégration",
                        "Integración",
                        "Integrazione",
                        "Integração",
                        "集成",
                        "Интеграция",
                        "Integration",
                        "التكامل",
                    ),
                },
                {
                    "key": "collaboration",
                    "label": "Collaboration",
                    "translations": _tr(
                        "Zusammenarbeit",
                        "Collaboration",
                        "Colaboración",
                        "Collaborazione",
                        "Colaboração",
                        "协作",
                        "Совместная работа",
                        "Samarbejde",
                        "التعاون",
                    ),
                },
                {
                    "key": "other",
                    "label": "Other",
                    "translations": _tr(
                        "Sonstige",
                        "Autre",
                        "Otro",
                        "Altro",
                        "Outro",
                        "其他",
                        "Другое",
                        "Andet",
                        "أخرى",
                    ),
                },
            ],
        },
        {
            "key": "automationLevel",
            "label": "Automation Level",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Automatisierungsgrad",
                "Niveau d'automatisation",
                "Nivel de automatización",
                "Livello di automazione",
                "Nível de automação",
                "自动化程度",
                "Уровень автоматизации",
                "Automatiseringsniveau",
                "مستوى الأتمتة",
            ),
            "options": [
                {
                    "key": "fullyAutomated",
                    "label": "Fully Automated",
                    "color": "#2e7d32",
                    "translations": _tr(
                        "Vollautomatisiert",
                        "Entièrement automatisé",
                        "Totalmente automatizado",
                        "Completamente automatizzato",
                        "Totalmente automatizado",
                        "全自动化",
                        "Полностью автоматизировано",
                        "Fuldt automatiseret",
                        "مؤتمت بالكامل",
                    ),
                },
                {
                    "key": "partiallyAutomated",
                    "label": "Partially Automated",
                    "color": "#f9a825",
                    "translations": _tr(
                        "Teilautomatisiert",
                        "Partiellement automatisé",
                        "Parcialmente automatizado",
                        "Parzialmente automatizzato",
                        "Parcialmente automatizado",
                        "部分自动化",
                        "Частично автоматизировано",
                        "Delvist automatiseret",
                        "مؤتمت جزئياً",
                    ),
                },
                {
                    "key": "manual",
                    "label": "Manual",
                    "color": "#c62828",
                    "translations": _tr(
                        "Manuell",
                        "Manuel",
                        "Manual",
                        "Manuale",
                        "Manual",
                        "人工",
                        "Вручную",
                        "Manuel",
                        "يدوي",
                    ),
                },
            ],
        },
        {
            "key": "sharedService",
            "label": "National Shared Service",
            "type": "boolean",
            "weight": 0,
            "translations": _tr(
                "Nationaler Shared Service",
                "Service partagé national",
                "Servicio compartido nacional",
                "Servizio condiviso nazionale",
                "Serviço compartilhado nacional",
                "国家共享服务",
                "Национальный общий сервис",
                "National delt tjeneste",
                "خدمة وطنية مشتركة",
            ),
        },
    ],
    "ITComponent": [
        {
            "key": "trmCode",
            "label": "TRM Code",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "TRM-Code",
                "Code TRM",
                "Código TRM",
                "Codice TRM",
                "Código TRM",
                "TRM 代码",
                "Код TRM",
                "TRM-kode",
                "رمز TRM",
            ),
        },
        {
            "key": "hostingModel",
            "label": "Hosting Model",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Hosting-Modell",
                "Modèle d'hébergement",
                "Modelo de alojamiento",
                "Modello di hosting",
                "Modelo de hospedagem",
                "托管模式",
                "Модель размещения",
                "Hostingmodel",
                "نموذج الاستضافة",
            ),
            "options": [
                {
                    "key": "onPremise",
                    "label": "On-Premise",
                    "translations": _tr(
                        "On-Premise",
                        "Sur site",
                        "Local (on-premise)",
                        "On-premise",
                        "Local (on-premise)",
                        "本地部署",
                        "Локально",
                        "On-premise",
                        "محلي (داخل المنشأة)",
                    ),
                },
                {
                    "key": "governmentCloud",
                    "label": "Government Cloud",
                    "translations": _tr(
                        "Regierungs-Cloud",
                        "Cloud gouvernemental",
                        "Nube gubernamental",
                        "Cloud governativo",
                        "Nuvem governamental",
                        "政务云",
                        "Государственное облако",
                        "Statslig cloud",
                        "السحابة الحكومية",
                    ),
                },
                {
                    "key": "publicCloud",
                    "label": "Public Cloud",
                    "translations": _tr(
                        "Public Cloud",
                        "Cloud public",
                        "Nube pública",
                        "Cloud pubblico",
                        "Nuvem pública",
                        "公有云",
                        "Публичное облако",
                        "Offentlig cloud",
                        "السحابة العامة",
                    ),
                },
                {
                    "key": "hybrid",
                    "label": "Hybrid",
                    "translations": _tr(
                        "Hybrid",
                        "Hybride",
                        "Híbrido",
                        "Ibrido",
                        "Híbrido",
                        "混合",
                        "Гибридная",
                        "Hybrid",
                        "هجين",
                    ),
                },
            ],
        },
        {
            "key": "securityZone",
            "label": "Security Zone",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Sicherheitszone",
                "Zone de sécurité",
                "Zona de seguridad",
                "Zona di sicurezza",
                "Zona de segurança",
                "安全区域",
                "Зона безопасности",
                "Sikkerhedszone",
                "المنطقة الأمنية",
            ),
        },
    ],
    "DataObject": [
        {
            "key": "drmCode",
            "label": "DRM Code",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "DRM-Code",
                "Code DRM",
                "Código DRM",
                "Codice DRM",
                "Código DRM",
                "DRM 代码",
                "Код DRM",
                "DRM-kode",
                "رمز DRM",
            ),
        },
        {
            "key": "dataClassification",
            "label": "Data Classification",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Datenklassifizierung",
                "Classification des données",
                "Clasificación de datos",
                "Classificazione dei dati",
                "Classificação de dados",
                "数据分类",
                "Классификация данных",
                "Dataklassifikation",
                "تصنيف البيانات",
            ),
            # Saudi NDMO data-classification levels.
            "options": [
                {
                    "key": "topSecret",
                    "label": "Top Secret",
                    "color": "#b71c1c",
                    "translations": _tr(
                        "Streng geheim",
                        "Très secret",
                        "Alto secreto",
                        "Segretissimo",
                        "Ultrassecreto",
                        "绝密",
                        "Совершенно секретно",
                        "Yderst hemmeligt",
                        "سري للغاية",
                    ),
                },
                {
                    "key": "secret",
                    "label": "Secret",
                    "color": "#e53935",
                    "translations": _tr(
                        "Geheim",
                        "Secret",
                        "Secreto",
                        "Segreto",
                        "Secreto",
                        "机密",
                        "Секретно",
                        "Hemmeligt",
                        "سري",
                    ),
                },
                {
                    "key": "restricted",
                    "label": "Restricted",
                    "color": "#fb8c00",
                    "translations": _tr(
                        "Eingeschränkt",
                        "Restreint",
                        "Restringido",
                        "Riservato",
                        "Restrito",
                        "受限",
                        "Ограниченный доступ",
                        "Begrænset",
                        "مقيد",
                    ),
                },
                {
                    "key": "public",
                    "label": "Public",
                    "color": "#43a047",
                    "translations": _tr(
                        "Öffentlich",
                        "Public",
                        "Público",
                        "Pubblico",
                        "Público",
                        "公开",
                        "Общедоступно",
                        "Offentligt",
                        "عام",
                    ),
                },
            ],
        },
        {
            "key": "piiFlag",
            "label": "Contains Personal Data (PII)",
            "type": "boolean",
            "weight": 0,
            "translations": _tr(
                "Enthält personenbezogene Daten",
                "Contient des données personnelles",
                "Contiene datos personales",
                "Contiene dati personali",
                "Contém dados pessoais",
                "包含个人数据",
                "Содержит персональные данные",
                "Indeholder persondata",
                "يحتوي على بيانات شخصية",
            ),
        },
        {
            "key": "authoritativeSource",
            "label": "Authoritative Source",
            "type": "boolean",
            "weight": 0,
            "translations": _tr(
                "Autoritative Quelle",
                "Source faisant autorité",
                "Fuente autorizada",
                "Fonte autorevole",
                "Fonte autoritativa",
                "权威数据源",
                "Авторитетный источник",
                "Autoritativ kilde",
                "مصدر موثوق معتمد",
            ),
        },
        {
            "key": "retentionPeriod",
            "label": "Retention Period",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Aufbewahrungsfrist",
                "Durée de conservation",
                "Período de retención",
                "Periodo di conservazione",
                "Período de retenção",
                "保留期限",
                "Срок хранения",
                "Opbevaringsperiode",
                "مدة الاحتفاظ",
            ),
        },
    ],
    "Interface": [
        {
            "key": "integrationType",
            "label": "Integration Type",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Integrationstyp",
                "Type d'intégration",
                "Tipo de integración",
                "Tipo di integrazione",
                "Tipo de integração",
                "集成类型",
                "Тип интеграции",
                "Integrationstype",
                "نوع التكامل",
            ),
            "options": [
                {
                    "key": "api",
                    "label": "API",
                    "translations": _tr(
                        "API",
                        "API",
                        "API",
                        "API",
                        "API",
                        "API",
                        "API",
                        "API",
                        "واجهة برمجة التطبيقات (API)",
                    ),
                },
                {
                    "key": "event",
                    "label": "Event",
                    "translations": _tr(
                        "Event",
                        "Événement",
                        "Evento",
                        "Evento",
                        "Evento",
                        "事件",
                        "Событие",
                        "Hændelse",
                        "حدث",
                    ),
                },
                {
                    "key": "fileTransfer",
                    "label": "File Transfer",
                    "translations": _tr(
                        "Dateitransfer",
                        "Transfert de fichiers",
                        "Transferencia de archivos",
                        "Trasferimento file",
                        "Transferência de arquivos",
                        "文件传输",
                        "Передача файлов",
                        "Filoverførsel",
                        "نقل الملفات",
                    ),
                },
                {
                    "key": "batch",
                    "label": "Batch",
                    "translations": _tr(
                        "Batch",
                        "Batch",
                        "Por lotes",
                        "Batch",
                        "Em lote",
                        "批处理",
                        "Пакетная",
                        "Batch",
                        "معالجة دفعية",
                    ),
                },
                {
                    "key": "messaging",
                    "label": "Messaging",
                    "translations": _tr(
                        "Messaging",
                        "Messagerie",
                        "Mensajería",
                        "Messaggistica",
                        "Mensageria",
                        "消息传递",
                        "Обмен сообщениями",
                        "Messaging",
                        "تراسل",
                    ),
                },
            ],
        },
        # NOTE: the built-in Interface type already carries a `protocol` field —
        # NORA's protocol artifact requirement is satisfied by it.
        {
            "key": "authenticationMethod",
            "label": "Authentication Method",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Authentifizierungsmethode",
                "Méthode d'authentification",
                "Método de autenticación",
                "Metodo di autenticazione",
                "Método de autenticação",
                "认证方式",
                "Метод аутентификации",
                "Godkendelsesmetode",
                "طريقة المصادقة",
            ),
        },
        {
            "key": "viaGsb",
            "label": "Via Government Service Bus (GSB)",
            "type": "boolean",
            "weight": 0,
            "translations": _tr(
                "Über Government Service Bus (GSB)",
                "Via le Government Service Bus (GSB)",
                "A través del Government Service Bus (GSB)",
                "Tramite Government Service Bus (GSB)",
                "Via Government Service Bus (GSB)",
                "通过政府服务总线 (GSB)",
                "Через государственную сервисную шину (GSB)",
                "Via Government Service Bus (GSB)",
                "عبر قناة التكامل الحكومية (GSB)",
            ),
        },
    ],
    "Objective": [
        {
            "key": "nationalAlignment",
            "label": "National Strategy Alignment",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Ausrichtung an der nationalen Strategie",
                "Alignement sur la stratégie nationale",
                "Alineación con la estrategia nacional",
                "Allineamento alla strategia nazionale",
                "Alinhamento com a estratégia nacional",
                "国家战略对齐",
                "Соответствие национальной стратегии",
                "National strategitilpasning",
                "المواءمة مع الاستراتيجية الوطنية",
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# Profile v2 field additions (noraPlan.md WP6.2) — alignment to the Dec-2024
# EA Content Meta Model and the official حصر البيانات data-collection
# templates. Option keys/values come verbatim from the templates' Lookup
# sheets (the sanctioned enumerations). Columns that already have a seed
# field are deliberately absent — the template importer (WP6.6) maps them:
#   Application: criticality → businessCriticality · users → numberOfUsers ·
#     operating cost → costTotalAnnual · app status → lifecycle phases
#   Interface: طريقة الربط → protocol · صيغة البيانات → dataFormat
#   ITComponent: جزء الشبكة → securityZone · operating cost → costTotalAnnual
#   BusinessProcess: مستوى الأتمتة → automationLevel (seed)
# Merged into NORA_TYPE_FIELDS below so all passes/tests see one field set.
# ---------------------------------------------------------------------------

_AUTOMATION_LEVEL_OPTIONS_V2 = [
    {
        "key": "fullyAutomated",
        "label": "Fully Automated",
        "color": "#2e7d32",
        "translations": _tr(
            "Vollautomatisiert",
            "Entièrement automatisé",
            "Totalmente automatizado",
            "Completamente automatizzato",
            "Totalmente automatizado",
            "全自动化",
            "Полностью автоматизировано",
            "Fuldt automatiseret",
            "مؤتمت بالكامل",
        ),
    },
    {
        "key": "partiallyAutomated",
        "label": "Partially Automated",
        "color": "#f9a825",
        "translations": _tr(
            "Teilautomatisiert",
            "Partiellement automatisé",
            "Parcialmente automatizado",
            "Parzialmente automatizzato",
            "Parcialmente automatizado",
            "部分自动化",
            "Частично автоматизировано",
            "Delvist automatiseret",
            "مؤتمت جزئياً",
        ),
    },
    {
        "key": "manual",
        "label": "Manual",
        "color": "#c62828",
        "translations": _tr(
            "Manuell",
            "Manuel",
            "Manual",
            "Manuale",
            "Manual",
            "人工",
            "Вручную",
            "Manuel",
            "يدوي",
        ),
    },
]

NORA_V2_TYPE_FIELDS: dict[str, list[dict]] = {
    "GovService": [
        {
            "key": "serviceClassification",
            "label": "Service Classification",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Dienstklassifizierung",
                "Classification du service",
                "Clasificación del servicio",
                "Classificazione del servizio",
                "Classificação do serviço",
                "服务分类",
                "Классификация услуги",
                "Serviceklassifikation",
                "تصنيف الخدمة",
            ),
            "options": [
                {
                    "key": "main",
                    "label": "Main Service",
                    "color": "#00695c",
                    "translations": _tr(
                        "Hauptdienst",
                        "Service principal",
                        "Servicio principal",
                        "Servizio principale",
                        "Serviço principal",
                        "主要服务",
                        "Основная услуга",
                        "Hovedservice",
                        "خدمة رئيسية",
                    ),
                },
                {
                    "key": "sub",
                    "label": "Sub-Service",
                    "color": "#4db6ac",
                    "translations": _tr(
                        "Teildienst",
                        "Sous-service",
                        "Servicio secundario",
                        "Sottoservizio",
                        "Subserviço",
                        "子服务",
                        "Подуслуга",
                        "Underservice",
                        "خدمة فرعية",
                    ),
                },
            ],
        },
        {
            "key": "serviceType",
            "label": "Service Type",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Diensttyp",
                "Type de service",
                "Tipo de servicio",
                "Tipo di servizio",
                "Tipo de serviço",
                "服务类型",
                "Тип услуги",
                "Servicetype",
                "نوع الخدمة",
            ),
            "options": [
                {
                    "key": "administrative",
                    "label": "Administrative",
                    "color": "#8e24aa",
                    "translations": _tr(
                        "Administrativ",
                        "Administratif",
                        "Administrativo",
                        "Amministrativo",
                        "Administrativo",
                        "行政类",
                        "Административная",
                        "Administrativ",
                        "إدارية",
                    ),
                },
                {
                    "key": "core",
                    "label": "Core",
                    "color": "#1565c0",
                    "translations": _tr(
                        "Kern",
                        "Cœur de métier",
                        "Central",
                        "Core",
                        "Essencial",
                        "核心类",
                        "Ключевая",
                        "Kerne",
                        "محورية",
                    ),
                },
                {
                    "key": "supporting",
                    "label": "Supporting",
                    "color": "#6d4c41",
                    "translations": _tr(
                        "Unterstützend",
                        "Support",
                        "De apoyo",
                        "Di supporto",
                        "De apoio",
                        "支持类",
                        "Вспомогательная",
                        "Understøttende",
                        "داعمة",
                    ),
                },
            ],
        },
        {
            "key": "automationLevel",
            "label": "Automation Level",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Automatisierungsgrad",
                "Niveau d'automatisation",
                "Nivel de automatización",
                "Livello di automazione",
                "Nível de automação",
                "自动化程度",
                "Уровень автоматизации",
                "Automatiseringsniveau",
                "مستوى أتمتة الخدمة",
            ),
            "options": _AUTOMATION_LEVEL_OPTIONS_V2,
        },
        {
            "key": "geoCoverage",
            "label": "Geographic Coverage",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Geografische Abdeckung",
                "Couverture géographique",
                "Cobertura geográfica",
                "Copertura geografica",
                "Cobertura geográfica",
                "地理覆盖范围",
                "Географический охват",
                "Geografisk dækning",
                "التغطية الجغرافية للخدمة",
            ),
        },
        {
            "key": "serviceRequirements",
            "label": "Service Requirements",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Servicevoraussetzungen",
                "Conditions d'obtention du service",
                "Requisitos del servicio",
                "Requisiti del servizio",
                "Requisitos do serviço",
                "服务要求",
                "Требования к получению услуги",
                "Servicekrav",
                "متطلبات وشروط الحصول على الخدمة",
            ),
        },
        {
            "key": "serviceInputs",
            "label": "Service Inputs",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Service-Eingaben",
                "Entrées du service",
                "Entradas del servicio",
                "Input del servizio",
                "Entradas do serviço",
                "服务输入",
                "Входные данные услуги",
                "Serviceinput",
                "مدخلات الخدمة",
            ),
        },
        {
            "key": "serviceOutputs",
            "label": "Service Outputs",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Service-Ausgaben",
                "Sorties du service",
                "Salidas del servicio",
                "Output del servizio",
                "Saídas do serviço",
                "服务输出",
                "Результаты услуги",
                "Serviceoutput",
                "مخرجات الخدمة",
            ),
        },
        {
            "key": "participatingEntities",
            "label": "Participating Entities",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Beteiligte Stellen",
                "Entités participantes",
                "Entidades participantes",
                "Enti partecipanti",
                "Entidades participantes",
                "参与机构",
                "Участвующие организации",
                "Deltagende enheder",
                "الجهات المشاركة في تقديم الخدمة",
            ),
        },
        {
            "key": "executionSteps",
            "label": "Execution Steps",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Ausführungsschritte",
                "Étapes d'exécution",
                "Pasos de ejecución",
                "Passaggi di esecuzione",
                "Etapas de execução",
                "执行步骤",
                "Шаги выполнения",
                "Udførelsestrin",
                "خطوات تنفيذ الخدمة",
            ),
        },
    ],
    "BusinessProcess": [
        {
            "key": "processClassification",
            "label": "Process Classification",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Prozessklassifizierung",
                "Classification du processus",
                "Clasificación del proceso",
                "Classificazione del processo",
                "Classificação do processo",
                "流程分类",
                "Классификация процесса",
                "Procesklassifikation",
                "تصنيف الإجراء",
            ),
            "options": [
                {
                    "key": "main",
                    "label": "Main Process",
                    "color": "#2e7d32",
                    "translations": _tr(
                        "Hauptprozess",
                        "Processus principal",
                        "Proceso principal",
                        "Processo principale",
                        "Processo principal",
                        "主要流程",
                        "Основной процесс",
                        "Hovedproces",
                        "إجراء رئيسي",
                    ),
                },
                {
                    "key": "sub",
                    "label": "Sub-Process",
                    "color": "#81c784",
                    "translations": _tr(
                        "Teilprozess",
                        "Sous-processus",
                        "Subproceso",
                        "Sottoprocesso",
                        "Subprocesso",
                        "子流程",
                        "Подпроцесс",
                        "Underproces",
                        "إجراء فرعي",
                    ),
                },
            ],
        },
        {
            "key": "triggerEvent",
            "label": "Trigger Event",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Auslösendes Ereignis",
                "Événement déclencheur",
                "Evento desencadenante",
                "Evento scatenante",
                "Evento acionador",
                "触发事件",
                "Инициирующее событие",
                "Udløsende hændelse",
                "حدث الإطلاق",
            ),
        },
        {
            "key": "businessRules",
            "label": "Business Rules",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Geschäftsregeln",
                "Règles métier",
                "Reglas de negocio",
                "Regole di business",
                "Regras de negócio",
                "业务规则",
                "Бизнес-правила",
                "Forretningsregler",
                "قواعد العمل",
            ),
        },
        {
            "key": "durationDays",
            "label": "Duration (days)",
            "type": "number",
            "weight": 0,
            "translations": _tr(
                "Dauer (Tage)",
                "Durée (jours)",
                "Duración (días)",
                "Durata (giorni)",
                "Duração (dias)",
                "持续时间（天）",
                "Длительность (дни)",
                "Varighed (dage)",
                "مدة التنفيذ (أيام)",
            ),
        },
        {
            "key": "processInputs",
            "label": "Process Inputs",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Prozess-Eingaben",
                "Entrées du processus",
                "Entradas del proceso",
                "Input del processo",
                "Entradas do processo",
                "流程输入",
                "Входные данные процесса",
                "Procesinput",
                "مدخلات الإجراء",
            ),
        },
        {
            "key": "processOutputs",
            "label": "Process Outputs",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Prozess-Ausgaben",
                "Sorties du processus",
                "Salidas del proceso",
                "Output del processo",
                "Saídas do processo",
                "流程输出",
                "Результаты процесса",
                "Procesoutput",
                "مخرجات الإجراء",
            ),
        },
    ],
    "Application": [
        {
            "key": "appLayer",
            "label": "Application Layer",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Anwendungsschicht",
                "Couche applicative",
                "Capa de aplicación",
                "Livello applicativo",
                "Camada de aplicação",
                "应用层级",
                "Уровень приложения",
                "Applikationslag",
                "طبقة التطبيق",
            ),
            "options": [
                {
                    "key": "access",
                    "label": "Access Layer",
                    "color": "#00acc1",
                    "translations": _tr(
                        "Zugriffsschicht",
                        "Couche d'accès",
                        "Capa de acceso",
                        "Livello di accesso",
                        "Camada de acesso",
                        "访问层",
                        "Уровень доступа",
                        "Adgangslag",
                        "طبقة الوصول",
                    ),
                },
                {
                    "key": "core",
                    "label": "Core Application Layer",
                    "color": "#1565c0",
                    "translations": _tr(
                        "Kernanwendungsschicht",
                        "Couche applicative cœur",
                        "Capa de aplicación central",
                        "Livello applicativo core",
                        "Camada de aplicação principal",
                        "核心应用层",
                        "Уровень основных приложений",
                        "Kerneapplikationslag",
                        "طبقة التطبيق الأساسي",
                    ),
                },
                {
                    "key": "support",
                    "label": "Support Application Layer",
                    "color": "#6d4c41",
                    "translations": _tr(
                        "Unterstützungsschicht",
                        "Couche applicative de support",
                        "Capa de aplicación de apoyo",
                        "Livello applicativo di supporto",
                        "Camada de aplicação de apoio",
                        "支持应用层",
                        "Уровень вспомогательных приложений",
                        "Støtteapplikationslag",
                        "طبقة التطبيق الداعمة",
                    ),
                },
                {
                    "key": "data",
                    "label": "Data Application Layer",
                    "color": "#7b1fa2",
                    "translations": _tr(
                        "Datenanwendungsschicht",
                        "Couche applicative de données",
                        "Capa de aplicación de datos",
                        "Livello applicativo dati",
                        "Camada de aplicação de dados",
                        "数据应用层",
                        "Уровень приложений данных",
                        "Dataapplikationslag",
                        "طبقة التطبيقات ذات العلاقة بالبيانات",
                    ),
                },
                {
                    "key": "infrastructure",
                    "label": "Infrastructure Application Layer",
                    "color": "#546e7a",
                    "translations": _tr(
                        "Infrastrukturanwendungsschicht",
                        "Couche applicative d'infrastructure",
                        "Capa de aplicación de infraestructura",
                        "Livello applicativo infrastrutturale",
                        "Camada de aplicação de infraestrutura",
                        "基础设施应用层",
                        "Уровень инфраструктурных приложений",
                        "Infrastrukturapplikationslag",
                        "طبقة التطبيقات ذات العلاقة بالبنية التحتية",
                    ),
                },
            ],
        },
        {
            "key": "developmentType",
            "label": "Development Type",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Entwicklungstyp",
                "Type de développement",
                "Tipo de desarrollo",
                "Tipo di sviluppo",
                "Tipo de desenvolvimento",
                "开发类型",
                "Тип разработки",
                "Udviklingstype",
                "نوع التطوير",
            ),
            "options": [
                {
                    "key": "cots",
                    "label": "COTS (Commercial Off-the-Shelf)",
                    "color": "#1565c0",
                    "translations": _tr(
                        "COTS (Standardsoftware)",
                        "COTS (produit sur étagère)",
                        "COTS (producto comercial)",
                        "COTS (prodotto commerciale)",
                        "COTS (produto de prateleira)",
                        "商用现成软件 (COTS)",
                        "COTS (готовое решение)",
                        "COTS (standardsoftware)",
                        "كود مصدري جاهز (COTS)",
                    ),
                },
                {
                    "key": "bespoke",
                    "label": "Bespoke",
                    "color": "#6a1b9a",
                    "translations": _tr(
                        "Individualentwicklung",
                        "Développement sur mesure",
                        "Desarrollo a medida",
                        "Sviluppo su misura",
                        "Desenvolvimento sob medida",
                        "定制开发",
                        "Заказная разработка",
                        "Skræddersyet",
                        "كود مصدري مصنوع",
                    ),
                },
            ],
        },
        {
            "key": "sourceType",
            "label": "Source Type",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Bezugsart",
                "Type de source",
                "Tipo de origen",
                "Tipo di origine",
                "Tipo de origem",
                "来源类型",
                "Тип источника",
                "Kildetype",
                "نوع المصدر",
            ),
            "options": [
                {
                    "key": "inHouse",
                    "label": "In-House Development",
                    "color": "#2e7d32",
                    "translations": _tr(
                        "Eigenentwicklung",
                        "Développement interne",
                        "Desarrollo interno",
                        "Sviluppo interno",
                        "Desenvolvimento interno",
                        "内部开发",
                        "Внутренняя разработка",
                        "Intern udvikling",
                        "تم التطوير داخلياً",
                    ),
                },
                {
                    "key": "outsourced",
                    "label": "Outsourced Development",
                    "color": "#ef6c00",
                    "translations": _tr(
                        "Ausgelagerte Entwicklung",
                        "Développement externalisé",
                        "Desarrollo externalizado",
                        "Sviluppo esternalizzato",
                        "Desenvolvimento terceirizado",
                        "外包开发",
                        "Аутсорсинговая разработка",
                        "Outsourcet udvikling",
                        "الاستعانة بمصادر خارجية",
                    ),
                },
                {
                    "key": "managedByThirdParty",
                    "label": "Managed by Third Party",
                    "color": "#5e35b1",
                    "translations": _tr(
                        "Von Drittanbieter verwaltet",
                        "Géré par un tiers",
                        "Gestionado por terceros",
                        "Gestito da terzi",
                        "Gerenciado por terceiros",
                        "第三方管理",
                        "Управляется третьей стороной",
                        "Administreret af tredjepart",
                        "تدار من قبل طرف ثالث",
                    ),
                },
            ],
        },
        {
            "key": "contractor",
            "label": "Contractor",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Auftragnehmer",
                "Prestataire",
                "Contratista",
                "Appaltatore",
                "Contratada",
                "承包商",
                "Подрядчик",
                "Leverandør",
                "المقاول",
            ),
        },
        {
            "key": "appUrl",
            "label": "Application URL",
            "type": "url",
            "weight": 0,
            "translations": _tr(
                "Anwendungs-URL",
                "URL de l'application",
                "URL de la aplicación",
                "URL dell'applicazione",
                "URL da aplicação",
                "应用链接",
                "URL приложения",
                "Applikations-URL",
                "رابط التطبيق",
            ),
        },
        {
            "key": "authenticationMethod",
            "label": "Authentication Method",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Authentifizierungsmethode",
                "Méthode d'authentification",
                "Método de autenticación",
                "Metodo di autenticazione",
                "Método de autenticação",
                "认证方式",
                "Метод аутентификации",
                "Godkendelsesmetode",
                "نوع المصادقة",
            ),
        },
        {
            "key": "launchDate",
            "label": "Launch Date",
            "type": "date",
            "weight": 0,
            "translations": _tr(
                "Startdatum",
                "Date de lancement",
                "Fecha de lanzamiento",
                "Data di lancio",
                "Data de lançamento",
                "上线日期",
                "Дата запуска",
                "Lanceringsdato",
                "تاريخ الإطلاق",
            ),
        },
        {
            "key": "architecturePattern",
            "label": "Architecture Pattern",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Architekturmuster",
                "Modèle d'architecture",
                "Patrón de arquitectura",
                "Pattern architetturale",
                "Padrão de arquitetura",
                "架构模式",
                "Архитектурный шаблон",
                "Arkitekturmønster",
                "نمط الهيكلية المعيارية",
            ),
            "options": [
                {
                    "key": "nTier",
                    "label": "N-Tier",
                    "translations": _tr(
                        "N-Tier",
                        "N-Tier",
                        "N-Tier",
                        "N-Tier",
                        "N-Tier",
                        "多层架构 (N-Tier)",
                        "Многоуровневая (N-Tier)",
                        "N-Tier",
                        "معمارية متعددة الطبقات (N-Tier)",
                    ),
                },
                {
                    "key": "clientServer",
                    "label": "Client/Server",
                    "translations": _tr(
                        "Client/Server",
                        "Client/serveur",
                        "Cliente/servidor",
                        "Client/server",
                        "Cliente/servidor",
                        "客户端/服务器",
                        "Клиент-сервер",
                        "Klient/server",
                        "عميل/خادم",
                    ),
                },
                {
                    "key": "microservices",
                    "label": "Microservices",
                    "translations": _tr(
                        "Microservices",
                        "Microservices",
                        "Microservicios",
                        "Microservizi",
                        "Microsserviços",
                        "微服务",
                        "Микросервисы",
                        "Microservices",
                        "الخدمات المصغّرة",
                    ),
                },
                {
                    "key": "eventDriven",
                    "label": "Event-Driven",
                    "translations": _tr(
                        "Ereignisgesteuert",
                        "Piloté par les événements",
                        "Orientado a eventos",
                        "Guidato dagli eventi",
                        "Orientado a eventos",
                        "事件驱动",
                        "Событийно-ориентированная",
                        "Hændelsesdrevet",
                        "قائم على الأحداث",
                    ),
                },
            ],
        },
        {
            "key": "costCapex",
            "label": "Capital Cost",
            "type": "cost",
            "weight": 0,
            "translations": _tr(
                "Investitionskosten",
                "Coût d'investissement",
                "Coste de capital",
                "Costo di capitale",
                "Custo de capital",
                "资本成本",
                "Капитальные затраты",
                "Anlægsomkostninger",
                "التكلفة الرأسمالية",
            ),
        },
    ],
    "Interface": [
        {
            "key": "integrationScope",
            "label": "Integration Scope",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Integrationsbereich",
                "Portée de l'intégration",
                "Alcance de la integración",
                "Ambito di integrazione",
                "Escopo da integração",
                "集成范围",
                "Охват интеграции",
                "Integrationsomfang",
                "نطاق الربط",
            ),
            "options": [
                {
                    "key": "internal",
                    "label": "Internal",
                    "color": "#2e7d32",
                    "translations": _tr(
                        "Intern",
                        "Interne",
                        "Interno",
                        "Interno",
                        "Interno",
                        "内部",
                        "Внутренний",
                        "Intern",
                        "داخلي",
                    ),
                },
                {
                    "key": "external",
                    "label": "External",
                    "color": "#ef6c00",
                    "translations": _tr(
                        "Extern",
                        "Externe",
                        "Externo",
                        "Esterno",
                        "Externo",
                        "外部",
                        "Внешний",
                        "Ekstern",
                        "خارجي",
                    ),
                },
            ],
        },
        {
            "key": "integrationPlatform",
            "label": "Integration Platform",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Integrationsplattform",
                "Plateforme d'intégration",
                "Plataforma de integración",
                "Piattaforma di integrazione",
                "Plataforma de integração",
                "集成平台",
                "Интеграционная платформа",
                "Integrationsplatform",
                "منصة التكامل",
            ),
        },
        {
            "key": "linkType",
            "label": "Link Type",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Verbindungstyp",
                "Type de liaison",
                "Tipo de enlace",
                "Tipo di collegamento",
                "Tipo de ligação",
                "连接类型",
                "Тип связи",
                "Forbindelsestype",
                "نوع الربط",
            ),
            "options": [
                {
                    "key": "direct",
                    "label": "Direct",
                    "translations": _tr(
                        "Direkt",
                        "Directe",
                        "Directo",
                        "Diretto",
                        "Direta",
                        "直连",
                        "Прямая",
                        "Direkte",
                        "مباشر",
                    ),
                },
                {
                    "key": "integrationPlatform",
                    "label": "Via Integration Platform",
                    "translations": _tr(
                        "Über Integrationsplattform",
                        "Via une plateforme d'intégration",
                        "A través de plataforma de integración",
                        "Tramite piattaforma di integrazione",
                        "Via plataforma de integração",
                        "通过集成平台",
                        "Через интеграционную платформу",
                        "Via integrationsplatform",
                        "عبر منصة التكامل",
                    ),
                },
                {
                    "key": "gsb",
                    "label": "GSB (Government Service Bus)",
                    "translations": _tr(
                        "GSB (Government Service Bus)",
                        "GSB (bus de services gouvernemental)",
                        "GSB (bus de servicios gubernamental)",
                        "GSB (bus di servizi governativo)",
                        "GSB (barramento de serviços governamental)",
                        "政府服务总线 (GSB)",
                        "GSB (правительственная сервисная шина)",
                        "GSB (offentlig servicebus)",
                        "قناة التكامل الحكومية (GSB)",
                    ),
                },
                {
                    "key": "gsn",
                    "label": "GSN (Government Secure Network)",
                    "translations": _tr(
                        "GSN (Government Secure Network)",
                        "GSN (réseau gouvernemental sécurisé)",
                        "GSN (red gubernamental segura)",
                        "GSN (rete governativa sicura)",
                        "GSN (rede governamental segura)",
                        "政府安全网络 (GSN)",
                        "GSN (защищённая правительственная сеть)",
                        "GSN (sikkert offentligt netværk)",
                        "الشبكة الحكومية الآمنة (GSN)",
                    ),
                },
            ],
        },
        {
            "key": "interfaceInputs",
            "label": "Interface Inputs",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Schnittstellen-Eingaben",
                "Entrées de l'interface",
                "Entradas de la interfaz",
                "Input dell'interfaccia",
                "Entradas da interface",
                "接口输入",
                "Входные данные интерфейса",
                "Grænsefladeinput",
                "مدخلات نقطة الربط",
            ),
        },
        {
            "key": "interfaceOutputs",
            "label": "Interface Outputs",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Schnittstellen-Ausgaben",
                "Sorties de l'interface",
                "Salidas de la interfaz",
                "Output dell'interfaccia",
                "Saídas da interface",
                "接口输出",
                "Выходные данные интерфейса",
                "Grænsefladeoutput",
                "مخرجات نقطة الربط",
            ),
        },
    ],
    "ITComponent": [
        {
            "key": "supportEndDate",
            "label": "Support End Date",
            "type": "date",
            "weight": 0,
            "translations": _tr(
                "Support-Enddatum",
                "Date de fin de support",
                "Fecha de fin de soporte",
                "Data di fine supporto",
                "Data de fim do suporte",
                "支持结束日期",
                "Дата окончания поддержки",
                "Supportophørsdato",
                "تاريخ انتهاء الدعم",
            ),
        },
        {
            "key": "supportContractStatus",
            "label": "Support Contract Status",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Status des Supportvertrags",
                "Statut du contrat de support",
                "Estado del contrato de soporte",
                "Stato del contratto di supporto",
                "Status do contrato de suporte",
                "支持合同状态",
                "Статус контракта на поддержку",
                "Supportkontraktstatus",
                "حالة عقد الدعم",
            ),
            "options": [
                {
                    "key": "active",
                    "label": "Active",
                    "color": "#2e7d32",
                    "translations": _tr(
                        "Aktiv",
                        "Actif",
                        "Activo",
                        "Attivo",
                        "Ativo",
                        "有效",
                        "Действует",
                        "Aktiv",
                        "فعّال",
                    ),
                },
                {
                    "key": "expired",
                    "label": "Expired",
                    "color": "#c62828",
                    "translations": _tr(
                        "Abgelaufen",
                        "Expiré",
                        "Vencido",
                        "Scaduto",
                        "Expirado",
                        "已到期",
                        "Истёк",
                        "Udløbet",
                        "منتهي",
                    ),
                },
            ],
        },
        {
            "key": "operationType",
            "label": "Operation Type",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Betriebsart",
                "Type d'exploitation",
                "Tipo de operación",
                "Tipo di gestione",
                "Tipo de operação",
                "运维方式",
                "Тип эксплуатации",
                "Driftstype",
                "نوع التشغيل",
            ),
            "options": [
                {
                    "key": "internalTeam",
                    "label": "Internal Team",
                    "color": "#2e7d32",
                    "translations": _tr(
                        "Internes Team",
                        "Équipe interne",
                        "Equipo interno",
                        "Team interno",
                        "Equipe interna",
                        "内部团队",
                        "Внутренняя команда",
                        "Internt team",
                        "فريق داخلي",
                    ),
                },
                {
                    "key": "serviceProvider",
                    "label": "Service Provider",
                    "color": "#ef6c00",
                    "translations": _tr(
                        "Dienstleister",
                        "Prestataire de services",
                        "Proveedor de servicios",
                        "Fornitore di servizi",
                        "Prestador de serviços",
                        "服务提供商",
                        "Поставщик услуг",
                        "Serviceudbyder",
                        "مزود خدمة",
                    ),
                },
                {
                    "key": "hybrid",
                    "label": "Hybrid",
                    "color": "#5e35b1",
                    "translations": _tr(
                        "Hybrid",
                        "Hybride",
                        "Híbrido",
                        "Ibrido",
                        "Híbrido",
                        "混合",
                        "Гибридный",
                        "Hybrid",
                        "مختلط",
                    ),
                },
            ],
        },
        {
            "key": "initialCost",
            "label": "Initial Cost",
            "type": "cost",
            "weight": 0,
            "translations": _tr(
                "Anschaffungskosten",
                "Coût initial",
                "Coste inicial",
                "Costo iniziale",
                "Custo inicial",
                "初始成本",
                "Первоначальная стоимость",
                "Startomkostninger",
                "التكلفة الأولية",
            ),
        },
        {
            "key": "environment",
            "label": "Environment",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Umgebung",
                "Environnement",
                "Entorno",
                "Ambiente",
                "Ambiente",
                "环境",
                "Среда",
                "Miljø",
                "البيئة",
            ),
            "options": [
                {
                    "key": "production",
                    "label": "Production",
                    "color": "#2e7d32",
                    "translations": _tr(
                        "Produktion",
                        "Production",
                        "Producción",
                        "Produzione",
                        "Produção",
                        "生产环境",
                        "Продуктивная",
                        "Produktion",
                        "البيئة الإنتاجية",
                    ),
                },
                {
                    "key": "test",
                    "label": "Test",
                    "color": "#f9a825",
                    "translations": _tr(
                        "Test",
                        "Test",
                        "Pruebas",
                        "Test",
                        "Teste",
                        "测试环境",
                        "Тестовая",
                        "Test",
                        "البيئة الاختبارية",
                    ),
                },
                {
                    "key": "staging",
                    "label": "Staging",
                    "color": "#0288d1",
                    "translations": _tr(
                        "Staging",
                        "Préproduction",
                        "Preproducción",
                        "Staging",
                        "Homologação",
                        "预发布环境",
                        "Предпродуктивная",
                        "Staging",
                        "البيئة التجريبية",
                    ),
                },
                {
                    "key": "disasterRecovery",
                    "label": "Disaster Recovery",
                    "color": "#c62828",
                    "translations": _tr(
                        "Notfallwiederherstellung",
                        "Reprise après sinistre",
                        "Recuperación ante desastres",
                        "Disaster recovery",
                        "Recuperação de desastres",
                        "灾备环境",
                        "Аварийное восстановление",
                        "Katastrofeberedskab",
                        "بيئة التعافي من الكوارث",
                    ),
                },
            ],
        },
        {
            "key": "clusterId",
            "label": "Cluster ID",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Cluster-ID",
                "ID de cluster",
                "ID de clúster",
                "ID cluster",
                "ID do cluster",
                "集群标识",
                "Идентификатор кластера",
                "Cluster-id",
                "معرف الكتلة",
            ),
        },
        {
            "key": "firmwareVersion",
            "label": "Firmware Version",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Firmware-Version",
                "Version du micrologiciel",
                "Versión de firmware",
                "Versione firmware",
                "Versão do firmware",
                "固件版本",
                "Версия прошивки",
                "Firmwareversion",
                "إصدار البرنامج الثابت",
            ),
        },
        {
            "key": "inBackupPolicy",
            "label": "In Backup Policy",
            "type": "boolean",
            "weight": 0,
            "translations": _tr(
                "In Backup-Richtlinie",
                "Inclus dans la politique de sauvegarde",
                "En política de copias de seguridad",
                "Incluso nella politica di backup",
                "Na política de backup",
                "纳入备份策略",
                "Включён в политику резервного копирования",
                "Omfattet af backup-politik",
                "مشمول بالنسخ الاحتياطي",
            ),
        },
        {
            "key": "inDrPolicy",
            "label": "In Disaster Recovery Policy",
            "type": "boolean",
            "weight": 0,
            "translations": _tr(
                "In Notfallwiederherstellungs-Richtlinie",
                "Inclus dans le plan de reprise après sinistre",
                "En política de recuperación ante desastres",
                "Incluso nella politica di disaster recovery",
                "Na política de recuperação de desastres",
                "纳入灾备策略",
                "Включён в план аварийного восстановления",
                "Omfattet af katastrofeberedskab",
                "مشمول بالتعافي من الكوارث",
            ),
        },
        {
            "key": "manufacturer",
            "label": "Manufacturer",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Hersteller",
                "Fabricant",
                "Fabricante",
                "Produttore",
                "Fabricante",
                "制造商",
                "Производитель",
                "Producent",
                "الشركة المصنعة",
            ),
        },
        {
            "key": "modelNumber",
            "label": "Model",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Modell",
                "Modèle",
                "Modelo",
                "Modello",
                "Modelo",
                "型号",
                "Модель",
                "Model",
                "الطراز",
            ),
        },
        {
            "key": "deviceFunction",
            "label": "Function",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Funktion",
                "Fonction",
                "Función",
                "Funzione",
                "Função",
                "功能",
                "Функция",
                "Funktion",
                "الوظيفة",
            ),
        },
    ],
    "DataObject": [
        {
            "key": "dataType",
            "label": "Data Type",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Datentyp",
                "Type de données",
                "Tipo de datos",
                "Tipo di dati",
                "Tipo de dados",
                "数据类型",
                "Тип данных",
                "Datatype",
                "نوع البيانات",
            ),
        },
    ],
}

# Merge the v2 additions into the canonical field map (single source for the
# apply pass and every definition test).
for _type_key, _v2_fields in NORA_V2_TYPE_FIELDS.items():
    NORA_TYPE_FIELDS.setdefault(_type_key, []).extend(_v2_fields)


# ---------------------------------------------------------------------------
# v4 (GFSA EA Metamodel v3): remaining building-block attribute gaps.
#
# Deck attributes that already have a seed/profile home are deliberately NOT
# duplicated here — e.g. capability maturity → seed `maturity`, org location →
# seed `location`, provider compliance → seed `compliance`, objective type →
# seed `objectiveType`, project budget/dates → seed cost/date fields, KPI
# unit/polarity → v1 `unit`/`direction`. All weight 0.
# ---------------------------------------------------------------------------

_PRIORITY_OPTIONS = [
    {
        "key": "high",
        "label": "High",
        "color": "#c62828",
        "translations": _tr(
            "Hoch", "Élevée", "Alta", "Alta", "Alta", "高", "Высокий", "Høj", "عالية"
        ),
    },
    {
        "key": "medium",
        "label": "Medium",
        "color": "#f9a825",
        "translations": _tr(
            "Mittel",
            "Moyenne",
            "Media",
            "Media",
            "Média",
            "中",
            "Средний",
            "Mellem",
            "متوسطة",
        ),
    },
    {
        "key": "low",
        "label": "Low",
        "color": "#2e7d32",
        "translations": _tr(
            "Niedrig", "Faible", "Baja", "Bassa", "Baixa", "低", "Низкий", "Lav", "منخفضة"
        ),
    },
]

NORA_V4_TYPE_FIELDS: dict[str, list[dict]] = {
    "BusinessCapability": [
        {
            "key": "capabilityType",
            "label": "Capability Type",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Fähigkeitstyp",
                "Type de capacité",
                "Tipo de capacidad",
                "Tipo di capacità",
                "Tipo de capacidade",
                "能力类型",
                "Тип способности",
                "Kapabilitetstype",
                "نوع القدرة",
            ),
            "options": [
                {
                    "key": "strategic",
                    "label": "Strategic",
                    "translations": _tr(
                        "Strategisch",
                        "Stratégique",
                        "Estratégica",
                        "Strategica",
                        "Estratégica",
                        "战略",
                        "Стратегическая",
                        "Strategisk",
                        "استراتيجية",
                    ),
                },
                {
                    "key": "operational",
                    "label": "Operational",
                    "translations": _tr(
                        "Operativ",
                        "Opérationnelle",
                        "Operativa",
                        "Operativa",
                        "Operacional",
                        "运营",
                        "Операционная",
                        "Operationel",
                        "تشغيلية",
                    ),
                },
                {
                    "key": "supporting",
                    "label": "Supporting",
                    "translations": _tr(
                        "Unterstützend",
                        "De soutien",
                        "De apoyo",
                        "Di supporto",
                        "De apoio",
                        "支持",
                        "Поддерживающая",
                        "Understøttende",
                        "مساندة",
                    ),
                },
            ],
        },
    ],
    "Organization": [
        {
            "key": "orgUnitType",
            "label": "Administrative Type",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Verwaltungstyp",
                "Type administratif",
                "Tipo administrativo",
                "Tipo amministrativo",
                "Tipo administrativo",
                "行政类型",
                "Административный тип",
                "Administrativ type",
                "النوع الإداري",
            ),
            "options": [
                {
                    "key": "ministry",
                    "label": "Ministry",
                    "translations": _tr(
                        "Ministerium",
                        "Ministère",
                        "Ministerio",
                        "Ministero",
                        "Ministério",
                        "部",
                        "Министерство",
                        "Ministerium",
                        "وزارة",
                    ),
                },
                {
                    "key": "authority",
                    "label": "Authority",
                    "translations": _tr(
                        "Behörde",
                        "Autorité",
                        "Autoridad",
                        "Autorità",
                        "Autoridade",
                        "管理局",
                        "Управление",
                        "Myndighed",
                        "هيئة",
                    ),
                },
                {
                    "key": "agency",
                    "label": "Agency",
                    "translations": _tr(
                        "Agentur",
                        "Agence",
                        "Agencia",
                        "Agenzia",
                        "Agência",
                        "机构",
                        "Агентство",
                        "Styrelse",
                        "وكالة",
                    ),
                },
                {
                    "key": "sector",
                    "label": "Sector",
                    "translations": _tr(
                        "Sektor",
                        "Secteur",
                        "Sector",
                        "Settore",
                        "Setor",
                        "板块",
                        "Сектор",
                        "Sektor",
                        "قطاع",
                    ),
                },
                {
                    # Arabic deliberately NOT «إدارة عامة» — that is the
                    # generalDepartment *subtype* (hierarchy level); this
                    # option is the kind of legal entity (v7 reconciliation).
                    "key": "publicAdministration",
                    "label": "Public Administration",
                    "translations": _tr(
                        "Öffentliche Verwaltung",
                        "Administration publique",
                        "Administración pública",
                        "Amministrazione pubblica",
                        "Administração pública",
                        "公共管理部门",
                        "Государственная администрация",
                        "Offentlig forvaltning",
                        "جهة إدارية عامة",
                    ),
                },
                {
                    "key": "department",
                    "label": "Department",
                    "translations": _tr(
                        "Abteilung",
                        "Département",
                        "Departamento",
                        "Dipartimento",
                        "Departamento",
                        "部门",
                        "Отдел",
                        "Afdeling",
                        "إدارة",
                    ),
                },
            ],
        },
        {
            "key": "mandates",
            "label": "Mandates",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Aufgaben und Zuständigkeiten",
                "Mandats",
                "Mandatos",
                "Mandati",
                "Mandatos",
                "职责范围",
                "Полномочия",
                "Mandater",
                "المهام والاختصاصات",
            ),
        },
    ],
    "Provider": [
        {
            "key": "fieldOfActivity",
            "label": "Field of Activity",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Tätigkeitsfeld",
                "Domaine d'activité",
                "Campo de actividad",
                "Campo di attività",
                "Área de atividade",
                "活动领域",
                "Сфера деятельности",
                "Aktivitetsområde",
                "مجال النشاط",
            ),
            "options": [
                {
                    "key": "technologySolutions",
                    "label": "Technology Solutions",
                    "translations": _tr(
                        "Technologielösungen",
                        "Solutions technologiques",
                        "Soluciones tecnológicas",
                        "Soluzioni tecnologiche",
                        "Soluções tecnológicas",
                        "技术解决方案",
                        "Технологические решения",
                        "Teknologiløsninger",
                        "حلول تقنية",
                    ),
                },
                {
                    "key": "securitySolutions",
                    "label": "Security Solutions",
                    "translations": _tr(
                        "Sicherheitslösungen",
                        "Solutions de sécurité",
                        "Soluciones de seguridad",
                        "Soluzioni di sicurezza",
                        "Soluções de segurança",
                        "安全解决方案",
                        "Решения безопасности",
                        "Sikkerhedsløsninger",
                        "حلول أمنية",
                    ),
                },
                {
                    "key": "hardwareProvider",
                    "label": "Hardware Provider",
                    "translations": _tr(
                        "Hardwareanbieter",
                        "Fournisseur de matériel",
                        "Proveedor de hardware",
                        "Fornitore di hardware",
                        "Fornecedor de hardware",
                        "硬件供应商",
                        "Поставщик оборудования",
                        "Hardwareleverandør",
                        "مزود أجهزة",
                    ),
                },
                {
                    "key": "serviceProvider",
                    "label": "Service Provider",
                    "translations": _tr(
                        "Dienstleister",
                        "Prestataire de services",
                        "Proveedor de servicios",
                        "Fornitore di servizi",
                        "Provedor de serviços",
                        "服务提供商",
                        "Поставщик услуг",
                        "Serviceleverandør",
                        "مزود خدمات",
                    ),
                },
            ],
        },
        {
            "key": "servicesProvided",
            "label": "Services Provided",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Erbrachte Leistungen",
                "Services fournis",
                "Servicios prestados",
                "Servizi forniti",
                "Serviços prestados",
                "提供的服务",
                "Предоставляемые услуги",
                "Leverede services",
                "الخدمات المقدمة",
            ),
        },
        {
            "key": "providerStatus",
            "label": "Provider Status",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Anbieterstatus",
                "Statut du fournisseur",
                "Estado del proveedor",
                "Stato del fornitore",
                "Status do fornecedor",
                "供应商状态",
                "Статус поставщика",
                "Leverandørstatus",
                "حالة مزود الخدمة",
            ),
            "options": [
                {
                    "key": "active",
                    "label": "Active",
                    "color": "#2e7d32",
                    "translations": _tr(
                        "Aktiv",
                        "Actif",
                        "Activo",
                        "Attivo",
                        "Ativo",
                        "活跃",
                        "Активный",
                        "Aktiv",
                        "نشط",
                    ),
                },
                {
                    "key": "inactive",
                    "label": "Inactive",
                    "color": "#9e9e9e",
                    "translations": _tr(
                        "Inaktiv",
                        "Inactif",
                        "Inactivo",
                        "Inattivo",
                        "Inativo",
                        "不活跃",
                        "Неактивный",
                        "Inaktiv",
                        "غير نشط",
                    ),
                },
            ],
        },
        {
            "key": "geoLocation",
            "label": "Geographic Location",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Geografischer Standort",
                "Localisation géographique",
                "Ubicación geográfica",
                "Posizione geografica",
                "Localização geográfica",
                "地理位置",
                "Географическое расположение",
                "Geografisk placering",
                "الموقع الجغرافي",
            ),
        },
    ],
    "BusinessContext": [
        {
            "key": "productType",
            "label": "Product Type",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Produkttyp",
                "Type de produit",
                "Tipo de producto",
                "Tipo di prodotto",
                "Tipo de produto",
                "产品类型",
                "Тип продукта",
                "Produkttype",
                "نوع المنتج",
            ),
            "options": [
                {
                    "key": "physicalProduct",
                    "label": "Physical Product",
                    "translations": _tr(
                        "Physisches Produkt",
                        "Produit physique",
                        "Producto físico",
                        "Prodotto fisico",
                        "Produto físico",
                        "实体产品",
                        "Физический продукт",
                        "Fysisk produkt",
                        "منتج مادي",
                    ),
                },
                {
                    "key": "technicalProduct",
                    "label": "Technical Product",
                    "translations": _tr(
                        "Technisches Produkt",
                        "Produit technique",
                        "Producto técnico",
                        "Prodotto tecnico",
                        "Produto técnico",
                        "技术产品",
                        "Технический продукт",
                        "Teknisk produkt",
                        "منتج تقني",
                    ),
                },
                {
                    "key": "document",
                    "label": "Document",
                    "translations": _tr(
                        "Dokument",
                        "Document",
                        "Documento",
                        "Documento",
                        "Documento",
                        "文档",
                        "Документ",
                        "Dokument",
                        "وثيقة",
                    ),
                },
            ],
        },
        {
            "key": "productOwner",
            "label": "Product Owner",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Produktverantwortlicher",
                "Propriétaire du produit",
                "Propietario del producto",
                "Proprietario del prodotto",
                "Proprietário do produto",
                "产品负责人",
                "Владелец продукта",
                "Produktejer",
                "مالك المنتج",
            ),
        },
        {
            "key": "productBeneficiary",
            "label": "Targeted Beneficiary",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Zielgruppe",
                "Bénéficiaire cible",
                "Beneficiario objetivo",
                "Beneficiario target",
                "Beneficiário-alvo",
                "目标受益人",
                "Целевой получатель",
                "Målgruppe",
                "الفئة المستهدفة",
            ),
        },
    ],
    "Initiative": [
        {
            "key": "projectSponsor",
            "label": "Sponsor",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Sponsor",
                "Sponsor",
                "Patrocinador",
                "Sponsor",
                "Patrocinador",
                "项目发起人",
                "Спонсор",
                "Sponsor",
                "راعي المشروع",
            ),
        },
        {
            "key": "projectManager",
            "label": "Project Manager",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Projektleiter",
                "Chef de projet",
                "Gerente de proyecto",
                "Project manager",
                "Gerente de projeto",
                "项目经理",
                "Руководитель проекта",
                "Projektleder",
                "مدير المشروع",
            ),
        },
        {
            "key": "executionEntity",
            "label": "Execution Entity",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Ausführende Stelle",
                "Entité d'exécution",
                "Entidad ejecutora",
                "Entità esecutrice",
                "Entidade executora",
                "执行主体",
                "Исполнитель",
                "Udførende enhed",
                "جهة التنفيذ",
            ),
            "options": [
                {
                    "key": "inHouse",
                    "label": "In-house",
                    "translations": _tr(
                        "Intern",
                        "En interne",
                        "Interna",
                        "Interna",
                        "Interna",
                        "内部执行",
                        "Собственными силами",
                        "Internt",
                        "تنفيذ داخلي",
                    ),
                },
                {
                    "key": "outsourced",
                    "label": "Outsourced",
                    "translations": _tr(
                        "Extern vergeben",
                        "Externalisée",
                        "Externalizada",
                        "Esternalizzata",
                        "Terceirizada",
                        "外包执行",
                        "На аутсорсинге",
                        "Outsourcet",
                        "تنفيذ خارجي",
                    ),
                },
                {
                    "key": "mixed",
                    "label": "Mixed",
                    "translations": _tr(
                        "Gemischt",
                        "Mixte",
                        "Mixta",
                        "Mista",
                        "Mista",
                        "混合执行",
                        "Смешанный",
                        "Blandet",
                        "تنفيذ مشترك",
                    ),
                },
            ],
        },
        {
            "key": "priorityLevel",
            "label": "Priority",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Priorität",
                "Priorité",
                "Prioridad",
                "Priorità",
                "Prioridade",
                "优先级",
                "Приоритет",
                "Prioritet",
                "الأولوية",
            ),
            "options": deepcopy(_PRIORITY_OPTIONS),
        },
        {
            "key": "projectDeliverables",
            "label": "Deliverables",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Liefergegenstände",
                "Livrables",
                "Entregables",
                "Deliverable",
                "Entregáveis",
                "交付物",
                "Результаты",
                "Leverancer",
                "المخرجات",
            ),
        },
        {
            "key": "scopeOfWork",
            "label": "Scope of Work",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Arbeitsumfang",
                "Périmètre des travaux",
                "Alcance del trabajo",
                "Ambito di lavoro",
                "Escopo do trabalho",
                "工作范围",
                "Объём работ",
                "Arbejdsomfang",
                "نطاق العمل",
            ),
        },
    ],
    "BusinessProcess": [
        {
            "key": "beneficiaryType",
            "label": "Beneficiary Type",
            "type": "multiple_select",
            "weight": 0,
            "translations": _tr(
                "Begünstigtentyp",
                "Type de bénéficiaire",
                "Tipo de beneficiario",
                "Tipo di beneficiario",
                "Tipo de beneficiário",
                "受益人类型",
                "Тип получателя",
                "Modtagertype",
                "نوع المستفيد",
            ),
            "options": [
                {
                    "key": "government",
                    "label": "Government Entity",
                    "translations": _tr(
                        "Behörde",
                        "Entité gouvernementale",
                        "Entidad gubernamental",
                        "Ente governativo",
                        "Órgão governamental",
                        "政府实体",
                        "Государственный орган",
                        "Offentlig myndighed",
                        "جهة حكومية",
                    ),
                },
                {
                    "key": "privateSector",
                    "label": "Private Sector",
                    "translations": _tr(
                        "Privatwirtschaft",
                        "Secteur privé",
                        "Sector privado",
                        "Settore privato",
                        "Setor privado",
                        "私营部门",
                        "Частный сектор",
                        "Privat sektor",
                        "القطاع الخاص",
                    ),
                },
                {
                    "key": "individual",
                    "label": "Individuals",
                    "translations": _tr(
                        "Privatpersonen",
                        "Particuliers",
                        "Personas físicas",
                        "Privati",
                        "Pessoas físicas",
                        "个人",
                        "Физические лица",
                        "Privatpersoner",
                        "أفراد",
                    ),
                },
                {
                    "key": "internal",
                    "label": "Internal Beneficiary",
                    "translations": _tr(
                        "Interner Begünstigter",
                        "Bénéficiaire interne",
                        "Beneficiario interno",
                        "Beneficiario interno",
                        "Beneficiário interno",
                        "内部受益人",
                        "Внутренний получатель",
                        "Intern modtager",
                        "مستفيد داخلي",
                    ),
                },
            ],
        },
        {
            "key": "participatingEntities",
            "label": "Participating Entities",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Beteiligte Stellen",
                "Entités participantes",
                "Entidades participantes",
                "Entità partecipanti",
                "Entidades participantes",
                "参与实体",
                "Участвующие организации",
                "Deltagende enheder",
                "الجهات المشاركة",
            ),
        },
    ],
    "DataObject": [
        {
            "key": "structureClassification",
            "label": "Structure Classification",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Strukturklassifizierung",
                "Classification structurelle",
                "Clasificación estructural",
                "Classificazione strutturale",
                "Classificação estrutural",
                "结构分类",
                "Классификация структуры",
                "Strukturklassifikation",
                "تصنيف الهيكلة",
            ),
            "options": [
                {
                    "key": "structured",
                    "label": "Structured",
                    "translations": _tr(
                        "Strukturiert",
                        "Structurées",
                        "Estructurados",
                        "Strutturati",
                        "Estruturados",
                        "结构化",
                        "Структурированные",
                        "Struktureret",
                        "بيانات مهيكلة",
                    ),
                },
                {
                    "key": "semiStructured",
                    "label": "Semi-structured",
                    "translations": _tr(
                        "Halbstrukturiert",
                        "Semi-structurées",
                        "Semiestructurados",
                        "Semi-strutturati",
                        "Semiestruturados",
                        "半结构化",
                        "Полуструктурированные",
                        "Semistruktureret",
                        "بيانات شبه مهيكلة",
                    ),
                },
                {
                    "key": "unstructured",
                    "label": "Unstructured",
                    "translations": _tr(
                        "Unstrukturiert",
                        "Non structurées",
                        "No estructurados",
                        "Non strutturati",
                        "Não estruturados",
                        "非结构化",
                        "Неструктурированные",
                        "Ustruktureret",
                        "بيانات غير مهيكلة",
                    ),
                },
            ],
        },
        {
            "key": "dataBusinessRules",
            "label": "Data Business Rules",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Daten-Geschäftsregeln",
                "Règles métier des données",
                "Reglas de negocio de los datos",
                "Regole di business dei dati",
                "Regras de negócio dos dados",
                "数据业务规则",
                "Бизнес-правила данных",
                "Forretningsregler for data",
                "قواعد أعمال البيانات",
            ),
        },
        {
            "key": "securityControls",
            "label": "Security Controls",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Sicherheitskontrollen",
                "Contrôles de sécurité",
                "Controles de seguridad",
                "Controlli di sicurezza",
                "Controles de segurança",
                "安全控制措施",
                "Меры безопасности",
                "Sikkerhedskontroller",
                "الضوابط الأمنية",
            ),
        },
    ],
    "Application": [
        {
            "key": "accessChannel",
            "label": "Access Channel",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Zugangskanal",
                "Canal d'accès",
                "Canal de acceso",
                "Canale di accesso",
                "Canal de acesso",
                "访问渠道",
                "Канал доступа",
                "Adgangskanal",
                "قناة الوصول",
            ),
        },
        {
            "key": "developmentTechnology",
            "label": "Development Technology",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Entwicklungstechnologie",
                "Technologie de développement",
                "Tecnología de desarrollo",
                "Tecnologia di sviluppo",
                "Tecnologia de desenvolvimento",
                "开发技术",
                "Технология разработки",
                "Udviklingsteknologi",
                "تقنية التطوير",
            ),
        },
    ],
    "GovService": [
        {
            "key": "serviceFee",
            "label": "Service Fee",
            "type": "cost",
            "weight": 0,
            "translations": _tr(
                "Servicegebühr",
                "Frais de service",
                "Tarifa del servicio",
                "Tariffa del servizio",
                "Taxa do serviço",
                "服务费用",
                "Плата за услугу",
                "Servicegebyr",
                "رسوم الخدمة",
            ),
        },
    ],
    "KPI": [
        {
            "key": "indicatorLevel",
            "label": "Indicator Level",
            "type": "single_select",
            "weight": 0,
            "translations": _tr(
                "Indikatorebene",
                "Niveau de l'indicateur",
                "Nivel del indicador",
                "Livello dell'indicatore",
                "Nível do indicador",
                "指标层级",
                "Уровень показателя",
                "Indikatorniveau",
                "مستوى المؤشر",
            ),
            "options": [
                {
                    "key": "strategic",
                    "label": "Strategic",
                    "translations": _tr(
                        "Strategisch",
                        "Stratégique",
                        "Estratégico",
                        "Strategico",
                        "Estratégico",
                        "战略",
                        "Стратегический",
                        "Strategisk",
                        "استراتيجي",
                    ),
                },
                {
                    "key": "operational",
                    "label": "Operational",
                    "translations": _tr(
                        "Operativ",
                        "Opérationnel",
                        "Operativo",
                        "Operativo",
                        "Operacional",
                        "运营",
                        "Операционный",
                        "Operationel",
                        "تشغيلي",
                    ),
                },
            ],
        },
        {
            "key": "calculationFormula",
            "label": "Calculation Formula",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Berechnungsformel",
                "Formule de calcul",
                "Fórmula de cálculo",
                "Formula di calcolo",
                "Fórmula de cálculo",
                "计算公式",
                "Формула расчёта",
                "Beregningsformel",
                "معادلة الاحتساب",
            ),
        },
        {
            "key": "dataSource",
            "label": "Data Source",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "Datenquelle",
                "Source de données",
                "Fuente de datos",
                "Fonte dati",
                "Fonte de dados",
                "数据来源",
                "Источник данных",
                "Datakilde",
                "مصدر البيانات",
            ),
        },
        {
            "key": "lastMeasuredDate",
            "label": "Last Measurement Date",
            "type": "date",
            "weight": 0,
            "translations": _tr(
                "Datum der letzten Messung",
                "Date de la dernière mesure",
                "Fecha de la última medición",
                "Data dell'ultima misurazione",
                "Data da última medição",
                "最近测量日期",
                "Дата последнего измерения",
                "Seneste målingsdato",
                "تاريخ آخر قياس",
            ),
        },
        {
            "key": "baselineDate",
            "label": "Baseline Date",
            "type": "date",
            "weight": 0,
            "translations": _tr(
                "Basisdatum",
                "Date de référence",
                "Fecha de línea base",
                "Data di riferimento",
                "Data da linha de base",
                "基线日期",
                "Дата базового значения",
                "Basisdato",
                "تاريخ احتساب قيمة الأساس",
            ),
        },
        {
            "key": "targetValueDate",
            "label": "Target Value Date",
            "type": "date",
            "weight": 0,
            "translations": _tr(
                "Zielwertdatum",
                "Date de la valeur cible",
                "Fecha del valor objetivo",
                "Data del valore obiettivo",
                "Data do valor-alvo",
                "目标值日期",
                "Дата целевого значения",
                "Målværdidato",
                "تاريخ تحديد القيمة المستهدفة",
            ),
        },
    ],
}

# Merge the v4 additions into the canonical field map.
for _type_key, _v4_fields in NORA_V4_TYPE_FIELDS.items():
    NORA_TYPE_FIELDS.setdefault(_type_key, []).extend(_v4_fields)


# ---------------------------------------------------------------------------
# v8 (Reference Models, WP100.3): the last two RM code fields so every one of
# the six domains has a landing field for its reference-model classification
# (business/applications/data/technology already have brmCode/armCode/drmCode/
# trmCode from v1). Free text like the others; the card-detail picker offers
# published-RM items when one exists.
# ---------------------------------------------------------------------------

NORA_V8_TYPE_FIELDS: dict[str, list[dict]] = {
    "GovService": [
        {
            "key": "bxrmCode",
            "label": "BXRM Code",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "BXRM-Code",
                "Code BXRM",
                "Código BXRM",
                "Codice BXRM",
                "Código BXRM",
                "BXRM 代码",
                "Код BXRM",
                "BXRM-kode",
                "رمز BXRM",
            ),
        },
    ],
    "SecurityControl": [
        {
            "key": "srmCode",
            "label": "SRM Code",
            "type": "text",
            "weight": 0,
            "translations": _tr(
                "SRM-Code",
                "Code SRM",
                "Código SRM",
                "Codice SRM",
                "Código SRM",
                "SRM 代码",
                "Код SRM",
                "SRM-kode",
                "رمز SRM",
            ),
        },
    ],
}

# Merge the v8 additions into the canonical field map.
for _type_key, _v8_fields in NORA_V8_TYPE_FIELDS.items():
    NORA_TYPE_FIELDS.setdefault(_type_key, []).extend(_v8_fields)


# Subtypes appended by the profile apply (pass 4d). Idempotent by key.
# (v2 originally; v4 adds the BeneficiaryJourney phase/step structure.)
NORA_V2_SUBTYPES: dict[str, list[dict]] = {
    # v4 (GFSA Metamodel): journey Phase/Step are journey-internal structure —
    # modelled as subtypes on the (hierarchical) BeneficiaryJourney type, so a
    # journey ⊃ phase ⊃ step chain rides parent_id with zero custom UI.
    "BeneficiaryJourney": [
        {
            "key": "journeyPhase",
            "label": "Journey Phase",
            "translations": _tr(
                "Reisephase",
                "Phase du parcours",
                "Fase del recorrido",
                "Fase del percorso",
                "Fase da jornada",
                "旅程阶段",
                "Фаза пути",
                "Rejsefase",
                "مرحلة الرحلة",
            ),
        },
        {
            "key": "journeyStep",
            "label": "Journey Step",
            "translations": _tr(
                "Reiseschritt",
                "Étape du parcours",
                "Paso del recorrido",
                "Passo del percorso",
                "Etapa da jornada",
                "旅程步骤",
                "Шаг пути",
                "Rejsetrin",
                "خطوة الرحلة",
            ),
        },
    ],
    # v7 (WP100.2): Saudi government organizational-hierarchy levels —
    # Sector (قطاع) ⊃ General Department (إدارة عامة) ⊃ Department (إدارة) ⊃
    # Section/Unit (قسم/وحدة). Hierarchy itself rides the existing
    # Organization parent_id; the subtype names the level. Distinct from the
    # `orgUnitType` field, which classifies the kind of legal entity.
    "Organization": [
        {
            "key": "sector",
            "label": "Sector",
            "translations": _tr(
                "Sektor",
                "Secteur",
                "Sector",
                "Settore",
                "Setor",
                "板块",
                "Сектор",
                "Sektor",
                "قطاع",
            ),
        },
        {
            "key": "generalDepartment",
            "label": "General Department",
            "translations": _tr(
                "Hauptabteilung",
                "Direction générale",
                "Dirección general",
                "Direzione generale",
                "Direção-geral",
                "总局",
                "Главное управление",
                "Hovedafdeling",
                "إدارة عامة",
            ),
        },
        {
            "key": "department",
            "label": "Department",
            "translations": _tr(
                "Abteilung",
                "Département",
                "Departamento",
                "Dipartimento",
                "Departamento",
                "部门",
                "Управление",
                "Afdeling",
                "إدارة",
            ),
        },
        {
            "key": "sectionUnit",
            "label": "Section / Unit",
            "translations": _tr(
                "Referat/Einheit",
                "Section/Unité",
                "Sección/Unidad",
                "Sezione/Unità",
                "Seção/Unidade",
                "科室/单元",
                "Секция/подразделение",
                "Sektion/Enhed",
                "قسم/وحدة",
            ),
        },
    ],
    "Objective": [
        {
            "key": "pillar",
            "label": "Pillar",
            "translations": _tr(
                "Säule",
                "Pilier",
                "Pilar",
                "Pilastro",
                "Pilar",
                "支柱",
                "Стратегический столп",
                "Søjle",
                "ركيزة",
            ),
        },
    ],
    "ITComponent": [
        {
            "key": "dataVault",
            "label": "Data Vault",
            "translations": _tr(
                "Datentresor",
                "Coffre de données",
                "Bóveda de datos",
                "Vault dei dati",
                "Cofre de dados",
                "数据仓储",
                "Хранилище данных",
                "Databoks",
                "مستودع بيانات",
            ),
        },
        # NEA Technology-Architecture building blocks (Meta Model §5.3.6) —
        # WP6.3's metamodel half, pulled forward because the WP6.6 template
        # importer lands the بنية التقنية sheets onto these subtypes.
        {
            "key": "dataCenter",
            "label": "Data Center",
            "translations": _tr(
                "Rechenzentrum",
                "Centre de données",
                "Centro de datos",
                "Data center",
                "Data center",
                "数据中心",
                "Центр обработки данных",
                "Datacenter",
                "مركز بيانات",
            ),
        },
        {
            "key": "physicalHost",
            "label": "Physical Host",
            "translations": _tr(
                "Physischer Host",
                "Hôte physique",
                "Host físico",
                "Host fisico",
                "Host físico",
                "物理主机",
                "Физический хост",
                "Fysisk vært",
                "مضيف مادي",
            ),
        },
        {
            "key": "virtualServer",
            "label": "Virtual Server",
            "translations": _tr(
                "Virtueller Server",
                "Serveur virtuel",
                "Servidor virtual",
                "Server virtuale",
                "Servidor virtual",
                "虚拟服务器",
                "Виртуальный сервер",
                "Virtuel server",
                "خادم افتراضي",
            ),
        },
        {
            "key": "networkDevice",
            "label": "Network Device",
            "translations": _tr(
                "Netzwerkgerät",
                "Équipement réseau",
                "Dispositivo de red",
                "Dispositivo di rete",
                "Dispositivo de rede",
                "网络设备",
                "Сетевое устройство",
                "Netværksenhed",
                "جهاز شبكي",
            ),
        },
        {
            "key": "storage",
            "label": "Storage",
            "translations": _tr(
                "Speicher",
                "Stockage",
                "Almacenamiento",
                "Storage",
                "Armazenamento",
                "存储",
                "Система хранения",
                "Lager",
                "جهاز تخزين",
            ),
        },
        {
            "key": "infraTool",
            "label": "Infrastructure Tool",
            "translations": _tr(
                "Infrastrukturwerkzeug",
                "Outil d'infrastructure",
                "Herramienta de infraestructura",
                "Strumento infrastrutturale",
                "Ferramenta de infraestrutura",
                "基础设施工具",
                "Инфраструктурный инструмент",
                "Infrastrukturværktøj",
                "أداة تقنية تحتية",
            ),
        },
        {
            "key": "infraService",
            "label": "Infrastructure Service",
            "translations": _tr(
                "Infrastrukturdienst",
                "Service d'infrastructure",
                "Servicio de infraestructura",
                "Servizio infrastrutturale",
                "Serviço de infraestrutura",
                "基础设施服务",
                "Инфраструктурный сервис",
                "Infrastrukturtjeneste",
                "خدمة تقنية تحتية",
            ),
        },
        {
            "key": "license",
            "label": "License",
            "translations": _tr(
                "Lizenz",
                "Licence",
                "Licencia",
                "Licenza",
                "Licença",
                "许可证",
                "Лицензия",
                "Licens",
                "رخصة",
            ),
        },
        {
            "key": "containerEngine",
            "label": "Containerization Engine",
            "translations": _tr(
                "Containerisierungs-Engine",
                "Moteur de conteneurisation",
                "Motor de contenedores",
                "Motore di containerizzazione",
                "Motor de conteinerização",
                "容器化引擎",
                "Движок контейнеризации",
                "Containeriseringsmotor",
                "محرك الاحتواء التقني",
            ),
        },
        {
            "key": "peripheral",
            "label": "Peripheral Device",
            "translations": _tr(
                "Peripheriegerät",
                "Périphérique",
                "Dispositivo periférico",
                "Dispositivo periferico",
                "Dispositivo periférico",
                "外围设备",
                "Периферийное устройство",
                "Perifer enhed",
                "جهاز طرفي",
            ),
        },
        # NEA Security-Architecture building blocks (Meta Model §5.3.7) —
        # WP6.4's metamodel half, same reason: the بنية الأمن sheets land here.
        {
            "key": "securityHardware",
            "label": "Security Hardware",
            "translations": _tr(
                "Sicherheitshardware",
                "Matériel de sécurité",
                "Hardware de seguridad",
                "Hardware di sicurezza",
                "Hardware de segurança",
                "安全硬件",
                "Аппаратные средства безопасности",
                "Sikkerhedshardware",
                "جهاز أمن",
            ),
        },
        {
            "key": "securitySoftware",
            "label": "Security Software",
            "translations": _tr(
                "Sicherheitssoftware",
                "Logiciel de sécurité",
                "Software de seguridad",
                "Software di sicurezza",
                "Software de segurança",
                "安全软件",
                "Программные средства безопасности",
                "Sikkerhedssoftware",
                "برمجية أمن",
            ),
        },
        {
            "key": "securityService",
            "label": "Security Service",
            "translations": _tr(
                "Sicherheitsdienst",
                "Service de sécurité",
                "Servicio de seguridad",
                "Servizio di sicurezza",
                "Serviço de segurança",
                "安全服务",
                "Сервис безопасности",
                "Sikkerhedstjeneste",
                "خدمة أمن",
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# v4: fields that live in their own named section rather than "NORA Alignment"
# — injected by pass 4f with the same idempotency rule as pass 4 (a field key
# that exists anywhere in the type's schema is never duplicated).
# ---------------------------------------------------------------------------

NORA_SECTIONED_FIELDS: dict[str, list[dict]] = {
    # WP6.3's field half: subtype-specific TA specs in one flat, optional
    # section (the metamodel has no subtype-scoped fields — by design).
    "ITComponent": [
        {
            "section": "Technical Specification",
            "translations": _tr(
                "Technische Spezifikation",
                "Spécification technique",
                "Especificación técnica",
                "Specifica tecnica",
                "Especificação técnica",
                "技术规格",
                "Технические характеристики",
                "Teknisk specifikation",
                "المواصفات الفنية",
            ),
            "fields": [
                {
                    "key": "networkSegment",
                    "label": "Network Segment",
                    "type": "single_select",
                    "weight": 0,
                    "translations": _tr(
                        "Netzwerksegment",
                        "Segment réseau",
                        "Segmento de red",
                        "Segmento di rete",
                        "Segmento de rede",
                        "网络分段",
                        "Сегмент сети",
                        "Netværkssegment",
                        "النطاق الشبكي",
                    ),
                    "options": [
                        {
                            "key": "dmz",
                            "label": "DMZ",
                            "translations": _tr(
                                "DMZ", "DMZ", "DMZ", "DMZ", "DMZ", "DMZ", "DMZ", "DMZ", "DMZ"
                            ),
                        },
                        {
                            "key": "extranet",
                            "label": "Extranet",
                            "translations": _tr(
                                "Extranet",
                                "Extranet",
                                "Extranet",
                                "Extranet",
                                "Extranet",
                                "外联网",
                                "Экстранет",
                                "Ekstranet",
                                "الشبكة الخارجية",
                            ),
                        },
                        {
                            "key": "internet",
                            "label": "Internet",
                            "translations": _tr(
                                "Internet",
                                "Internet",
                                "Internet",
                                "Internet",
                                "Internet",
                                "互联网",
                                "Интернет",
                                "Internet",
                                "الإنترنت",
                            ),
                        },
                        {
                            "key": "wan",
                            "label": "WAN",
                            "translations": _tr(
                                "WAN", "WAN", "WAN", "WAN", "WAN", "广域网", "WAN", "WAN", "WAN"
                            ),
                        },
                        {
                            "key": "lan",
                            "label": "LAN",
                            "translations": _tr(
                                "LAN", "LAN", "LAN", "LAN", "LAN", "局域网", "LAN", "LAN", "LAN"
                            ),
                        },
                        {
                            "key": "airGapped",
                            "label": "Air-gapped",
                            "translations": _tr(
                                "Air-gapped",
                                "Isolé (air gap)",
                                "Aislado (air gap)",
                                "Isolato (air gap)",
                                "Isolado (air gap)",
                                "物理隔离",
                                "Физически изолированный",
                                "Air-gapped",
                                "معزول فيزيائياً",
                            ),
                        },
                        {
                            "key": "dataCenterSegment",
                            "label": "Data Center",
                            "translations": _tr(
                                "Rechenzentrum",
                                "Centre de données",
                                "Centro de datos",
                                "Data center",
                                "Data center",
                                "数据中心",
                                "ЦОД",
                                "Datacenter",
                                "مركز البيانات",
                            ),
                        },
                    ],
                },
                {
                    "key": "serverRole",
                    "label": "Server Role",
                    "type": "single_select",
                    "weight": 0,
                    "translations": _tr(
                        "Serverrolle",
                        "Rôle du serveur",
                        "Rol del servidor",
                        "Ruolo del server",
                        "Papel do servidor",
                        "服务器角色",
                        "Роль сервера",
                        "Serverrolle",
                        "دور الخادم",
                    ),
                    "options": [
                        {
                            "key": "webServer",
                            "label": "Web Server",
                            "translations": _tr(
                                "Webserver",
                                "Serveur web",
                                "Servidor web",
                                "Server web",
                                "Servidor web",
                                "Web 服务器",
                                "Веб-сервер",
                                "Webserver",
                                "خادم ويب",
                            ),
                        },
                        {
                            "key": "applicationServer",
                            "label": "Application Server",
                            "translations": _tr(
                                "Anwendungsserver",
                                "Serveur d'applications",
                                "Servidor de aplicaciones",
                                "Server applicativo",
                                "Servidor de aplicações",
                                "应用服务器",
                                "Сервер приложений",
                                "Applikationsserver",
                                "خادم تطبيقات",
                            ),
                        },
                        {
                            "key": "databaseServer",
                            "label": "Database Server",
                            "translations": _tr(
                                "Datenbankserver",
                                "Serveur de base de données",
                                "Servidor de base de datos",
                                "Server di database",
                                "Servidor de banco de dados",
                                "数据库服务器",
                                "Сервер баз данных",
                                "Databaseserver",
                                "خادم قواعد بيانات",
                            ),
                        },
                        {
                            "key": "integrationServer",
                            "label": "Integration Server",
                            "translations": _tr(
                                "Integrationsserver",
                                "Serveur d'intégration",
                                "Servidor de integración",
                                "Server di integrazione",
                                "Servidor de integração",
                                "集成服务器",
                                "Интеграционный сервер",
                                "Integrationsserver",
                                "خادم تكامل",
                            ),
                        },
                        {
                            "key": "infrastructureServer",
                            "label": "Infrastructure Server",
                            "translations": _tr(
                                "Infrastrukturserver",
                                "Serveur d'infrastructure",
                                "Servidor de infraestructura",
                                "Server infrastrutturale",
                                "Servidor de infraestrutura",
                                "基础设施服务器",
                                "Инфраструктурный сервер",
                                "Infrastrukturserver",
                                "خادم بنية تحتية",
                            ),
                        },
                        {
                            "key": "securityServer",
                            "label": "Security Server",
                            "translations": _tr(
                                "Sicherheitsserver",
                                "Serveur de sécurité",
                                "Servidor de seguridad",
                                "Server di sicurezza",
                                "Servidor de segurança",
                                "安全服务器",
                                "Сервер безопасности",
                                "Sikkerhedsserver",
                                "خادم أمني",
                            ),
                        },
                    ],
                },
                {
                    "key": "cpuSpec",
                    "label": "CPU Specification",
                    "type": "text",
                    "weight": 0,
                    "translations": _tr(
                        "CPU-Spezifikation",
                        "Spécification CPU",
                        "Especificación de CPU",
                        "Specifica CPU",
                        "Especificação de CPU",
                        "CPU 规格",
                        "Характеристики ЦП",
                        "CPU-specifikation",
                        "مواصفات المعالج",
                    ),
                },
                {
                    "key": "cpuCores",
                    "label": "CPU Cores",
                    "type": "number",
                    "weight": 0,
                    "translations": _tr(
                        "CPU-Kerne",
                        "Cœurs CPU",
                        "Núcleos de CPU",
                        "Core CPU",
                        "Núcleos de CPU",
                        "CPU 核心数",
                        "Ядра ЦП",
                        "CPU-kerner",
                        "عدد أنوية المعالج",
                    ),
                },
                {
                    "key": "ramGb",
                    "label": "RAM (GB)",
                    "type": "number",
                    "weight": 0,
                    "translations": _tr(
                        "RAM (GB)",
                        "RAM (Go)",
                        "RAM (GB)",
                        "RAM (GB)",
                        "RAM (GB)",
                        "内存 (GB)",
                        "ОЗУ (ГБ)",
                        "RAM (GB)",
                        "الذاكرة العشوائية (جيجابايت)",
                    ),
                },
                {
                    "key": "storageCapacityGb",
                    "label": "Storage Capacity (GB)",
                    "type": "number",
                    "weight": 0,
                    "translations": _tr(
                        "Speicherkapazität (GB)",
                        "Capacité de stockage (Go)",
                        "Capacidad de almacenamiento (GB)",
                        "Capacità di storage (GB)",
                        "Capacidade de armazenamento (GB)",
                        "存储容量 (GB)",
                        "Ёмкость хранилища (ГБ)",
                        "Lagerkapacitet (GB)",
                        "سعة التخزين (جيجابايت)",
                    ),
                },
                {
                    "key": "osType",
                    "label": "Operating System",
                    "type": "text",
                    "weight": 0,
                    "translations": _tr(
                        "Betriebssystem",
                        "Système d'exploitation",
                        "Sistema operativo",
                        "Sistema operativo",
                        "Sistema operacional",
                        "操作系统",
                        "Операционная система",
                        "Styresystem",
                        "نظام التشغيل",
                    ),
                },
                {
                    "key": "osVersion",
                    "label": "OS Version",
                    "type": "text",
                    "weight": 0,
                    "translations": _tr(
                        "Betriebssystemversion",
                        "Version du SE",
                        "Versión del SO",
                        "Versione del SO",
                        "Versão do SO",
                        "操作系统版本",
                        "Версия ОС",
                        "OS-version",
                        "إصدار نظام التشغيل",
                    ),
                },
                {
                    "key": "hypervisorType",
                    "label": "Hypervisor",
                    "type": "text",
                    "weight": 0,
                    "translations": _tr(
                        "Hypervisor",
                        "Hyperviseur",
                        "Hipervisor",
                        "Hypervisor",
                        "Hipervisor",
                        "虚拟机监控器",
                        "Гипервизор",
                        "Hypervisor",
                        "مراقب الأجهزة الافتراضية",
                    ),
                },
                {
                    "key": "hypervisorVersion",
                    "label": "Hypervisor Version",
                    "type": "text",
                    "weight": 0,
                    "translations": _tr(
                        "Hypervisor-Version",
                        "Version de l'hyperviseur",
                        "Versión del hipervisor",
                        "Versione dell'hypervisor",
                        "Versão do hipervisor",
                        "虚拟机监控器版本",
                        "Версия гипервизора",
                        "Hypervisor-version",
                        "إصدار مراقب الأجهزة الافتراضية",
                    ),
                },
                {
                    "key": "dcRole",
                    "label": "Data Center Role",
                    "type": "single_select",
                    "weight": 0,
                    "translations": _tr(
                        "Rechenzentrumsrolle",
                        "Rôle du centre de données",
                        "Rol del centro de datos",
                        "Ruolo del data center",
                        "Papel do data center",
                        "数据中心角色",
                        "Роль ЦОД",
                        "Datacenterrolle",
                        "دور مركز البيانات",
                    ),
                    "options": [
                        {
                            "key": "primary",
                            "label": "Primary",
                            "color": "#1565c0",
                            "translations": _tr(
                                "Primär",
                                "Principal",
                                "Principal",
                                "Primario",
                                "Primário",
                                "主中心",
                                "Основной",
                                "Primær",
                                "مركز رئيسي",
                            ),
                        },
                        {
                            "key": "disasterRecovery",
                            "label": "Disaster Recovery",
                            "color": "#ef6c00",
                            "translations": _tr(
                                "Notfallwiederherstellung",
                                "Reprise après sinistre",
                                "Recuperación ante desastres",
                                "Disaster recovery",
                                "Recuperação de desastres",
                                "灾难恢复中心",
                                "Аварийное восстановление",
                                "Disaster recovery",
                                "مركز التعافي من الكوارث",
                            ),
                        },
                    ],
                },
                {
                    "key": "dcTier",
                    "label": "Data Center Tier",
                    "type": "text",
                    "weight": 0,
                    "translations": _tr(
                        "Rechenzentrums-Tier",
                        "Niveau du centre de données",
                        "Nivel del centro de datos",
                        "Tier del data center",
                        "Tier do data center",
                        "数据中心等级",
                        "Уровень ЦОД",
                        "Datacenter-tier",
                        "مستوى تصنيف مركز البيانات",
                    ),
                },
                {
                    "key": "licenseQuantity",
                    "label": "License Quantity",
                    "type": "number",
                    "weight": 0,
                    "translations": _tr(
                        "Lizenzanzahl",
                        "Nombre de licences",
                        "Cantidad de licencias",
                        "Quantità di licenze",
                        "Quantidade de licenças",
                        "许可证数量",
                        "Количество лицензий",
                        "Licensantal",
                        "عدد الرخص",
                    ),
                },
                {
                    "key": "licenseObtainedDate",
                    "label": "License Obtained",
                    "type": "date",
                    "weight": 0,
                    "translations": _tr(
                        "Lizenz erworben am",
                        "Licence obtenue le",
                        "Licencia obtenida",
                        "Licenza ottenuta il",
                        "Licença obtida em",
                        "许可证获取日期",
                        "Дата получения лицензии",
                        "Licens erhvervet",
                        "تاريخ الحصول على الرخصة",
                    ),
                },
                {
                    "key": "licenseExpiryDate",
                    "label": "License Expiry",
                    "type": "date",
                    "weight": 0,
                    "translations": _tr(
                        "Lizenzablauf",
                        "Expiration de la licence",
                        "Vencimiento de la licencia",
                        "Scadenza della licenza",
                        "Expiração da licença",
                        "许可证到期日期",
                        "Срок действия лицензии",
                        "Licensudløb",
                        "تاريخ انتهاء الرخصة",
                    ),
                },
            ],
        },
    ],
    # v4 journey structure (GFSA Metamodel): code/objective at journey level,
    # gap/opportunity/impact/priority/at step level — flat optional fields, the
    # phase/step subtypes + hierarchy carry the structure.
    "BeneficiaryJourney": [
        {
            "section": "Journey Mapping",
            "translations": _tr(
                "Reise-Mapping",
                "Cartographie du parcours",
                "Mapeo del recorrido",
                "Mappatura del percorso",
                "Mapeamento da jornada",
                "旅程映射",
                "Карта пути",
                "Rejsekortlægning",
                "خريطة الرحلة",
            ),
            "fields": [
                {
                    "key": "journeyCode",
                    "label": "Code",
                    "type": "text",
                    "weight": 0,
                    "translations": _tr(
                        "Code",
                        "Code",
                        "Código",
                        "Codice",
                        "Código",
                        "编码",
                        "Код",
                        "Kode",
                        "الرمز",
                    ),
                },
                {
                    "key": "journeyObjective",
                    "label": "Objective",
                    "type": "text",
                    "weight": 0,
                    "translations": _tr(
                        "Ziel",
                        "Objectif",
                        "Objetivo",
                        "Obiettivo",
                        "Objetivo",
                        "目标",
                        "Цель",
                        "Mål",
                        "الهدف",
                    ),
                },
                {
                    "key": "associatedGaps",
                    "label": "Associated Gaps",
                    "type": "text",
                    "weight": 0,
                    "translations": _tr(
                        "Zugehörige Lücken",
                        "Lacunes associées",
                        "Brechas asociadas",
                        "Gap associati",
                        "Lacunas associadas",
                        "相关差距",
                        "Связанные разрывы",
                        "Tilknyttede huller",
                        "الفجوات المرتبطة",
                    ),
                },
                {
                    "key": "improvementOpportunity",
                    "label": "Improvement Opportunity",
                    "type": "text",
                    "weight": 0,
                    "translations": _tr(
                        "Verbesserungspotenzial",
                        "Opportunité d'amélioration",
                        "Oportunidad de mejora",
                        "Opportunità di miglioramento",
                        "Oportunidade de melhoria",
                        "改进机会",
                        "Возможность улучшения",
                        "Forbedringsmulighed",
                        "فرصة التحسين",
                    ),
                },
                {
                    "key": "expectedImpact",
                    "label": "Expected Impact",
                    "type": "text",
                    "weight": 0,
                    "translations": _tr(
                        "Erwartete Wirkung",
                        "Impact attendu",
                        "Impacto esperado",
                        "Impatto atteso",
                        "Impacto esperado",
                        "预期影响",
                        "Ожидаемый эффект",
                        "Forventet effekt",
                        "الأثر المتوقع",
                    ),
                },
                {
                    "key": "improvementPriority",
                    "label": "Improvement Priority",
                    "type": "single_select",
                    "weight": 0,
                    "translations": _tr(
                        "Verbesserungspriorität",
                        "Priorité d'amélioration",
                        "Prioridad de mejora",
                        "Priorità di miglioramento",
                        "Prioridade de melhoria",
                        "改进优先级",
                        "Приоритет улучшения",
                        "Forbedringsprioritet",
                        "أولوية التحسين",
                    ),
                    "options": deepcopy(_PRIORITY_OPTIONS),
                },
            ],
        },
    ],
}


# ---------------------------------------------------------------------------
# NORA-specific card types (noraPlan.md WP1.2).
#
# Created (never overwritten) when the profile is applied. GovService is the
# NORA BA "Service Catalogue" artifact — the citizen/business/government-facing
# services an agency delivers.
# ---------------------------------------------------------------------------

NORA_CARD_TYPES: list[dict] = [
    {
        "key": "GovService",
        "label": "Government Service",
        "description": (
            "A citizen-, business- or government-facing service delivered by the "
            "agency — the NORA Service Catalogue entry."
        ),
        "icon": "assured_workload",
        "color": "#00838f",
        "category": "Beneficiary Experience",
        # v2 (WP6.2): hierarchy enabled — sub-services (خدمة فرعية) attach to
        # their main service via parent_id.
        "has_hierarchy": True,
        "subtypes": [],
        "sort_order": 20,
        "translations": {
            "label": _tr(
                "Verwaltungsdienstleistung",
                "Service public",
                "Servicio gubernamental",
                "Servizio governativo",
                "Serviço governamental",
                "政府服务",
                "Государственная услуга",
                "Offentlig service",
                "الخدمة الحكومية",
            ),
            "description": _tr(
                "Eine für Bürger, Unternehmen oder Behörden erbrachte Dienstleistung "
                "der Organisation — der Eintrag im NORA-Servicekatalog.",
                "Un service destiné aux citoyens, aux entreprises ou aux administrations, "
                "fourni par l'organisme — l'entrée du catalogue de services NORA.",
                "Un servicio orientado a ciudadanos, empresas o entidades gubernamentales "
                "prestado por la agencia — la entrada del catálogo de servicios NORA.",
                "Un servizio rivolto a cittadini, imprese o enti pubblici erogato "
                "dall'agenzia — la voce del catalogo dei servizi NORA.",
                "Um serviço voltado a cidadãos, empresas ou órgãos governamentais "
                "fornecido pela agência — a entrada do catálogo de serviços NORA.",
                "机构面向公民、企业或政府提供的服务 — NORA 服务目录条目。",
                "Услуга для граждан, бизнеса или государственных органов, "
                "предоставляемая ведомством — запись каталога услуг NORA.",
                "En borger-, virksomheds- eller myndighedsrettet service leveret af "
                "organisationen — posten i NORA-servicekataloget.",
                "خدمة موجهة للمواطنين أو قطاع الأعمال أو الجهات الحكومية تقدمها الجهة — "
                "وهي مدخل سجل الخدمات في نورا.",
            ),
        },
        "stakeholder_roles": [
            {
                "key": "responsible",
                "label": "Responsible",
                "translations": {
                    "label": _tr(
                        "Verantwortlicher",
                        "Responsable",
                        "Responsable",
                        "Responsabile",
                        "Responsável",
                        "负责人",
                        "Ответственный",
                        "Ansvarlig",
                        "المسؤول",
                    ),
                },
            },
            {
                "key": "observer",
                "label": "Observer",
                "translations": {
                    "label": _tr(
                        "Beobachter",
                        "Observateur",
                        "Observador",
                        "Osservatore",
                        "Observador",
                        "观察者",
                        "Наблюдатель",
                        "Observatør",
                        "مراقب",
                    ),
                },
            },
            {
                "key": "service_owner",
                "label": "Service Owner",
                "translations": {
                    "label": _tr(
                        "Serviceverantwortlicher",
                        "Propriétaire du service",
                        "Propietario del servicio",
                        "Proprietario del servizio",
                        "Proprietário do serviço",
                        "服务负责人",
                        "Владелец сервиса",
                        "Serviceejer",
                        "مالك الخدمة",
                    ),
                },
            },
        ],
        "fields_schema": [
            {
                "section": "Service Information",
                "translations": _tr(
                    "Serviceinformationen",
                    "Informations sur le service",
                    "Información del servicio",
                    "Informazioni sul servizio",
                    "Informações do serviço",
                    "服务信息",
                    "Информация об услуге",
                    "Serviceinformation",
                    "معلومات الخدمة",
                ),
                "fields": [
                    {
                        "key": "serviceCode",
                        "label": "Service Code",
                        "type": "text",
                        "weight": 1,
                        "translations": _tr(
                            "Service-Code",
                            "Code du service",
                            "Código del servicio",
                            "Codice del servizio",
                            "Código do serviço",
                            "服务代码",
                            "Код услуги",
                            "Servicekode",
                            "رمز الخدمة",
                        ),
                    },
                    {
                        "key": "beneficiaryType",
                        "label": "Beneficiary Type",
                        "type": "multiple_select",
                        "weight": 1,
                        "translations": _tr(
                            "Begünstigtentyp",
                            "Type de bénéficiaire",
                            "Tipo de beneficiario",
                            "Tipo di beneficiario",
                            "Tipo de beneficiário",
                            "受益人类型",
                            "Тип получателя",
                            "Modtagertype",
                            "نوع المستفيد",
                        ),
                        "options": [
                            {
                                "key": "citizen",
                                "label": "Citizen",
                                "translations": _tr(
                                    "Bürger",
                                    "Citoyen",
                                    "Ciudadano",
                                    "Cittadino",
                                    "Cidadão",
                                    "公民",
                                    "Гражданин",
                                    "Borger",
                                    "مواطن",
                                ),
                            },
                            {
                                "key": "resident",
                                "label": "Resident",
                                "translations": _tr(
                                    "Einwohner",
                                    "Résident",
                                    "Residente",
                                    "Residente",
                                    "Residente",
                                    "居民",
                                    "Резидент",
                                    "Bosiddende",
                                    "مقيم",
                                ),
                            },
                            {
                                "key": "business",
                                "label": "Business",
                                "translations": _tr(
                                    "Unternehmen",
                                    "Entreprise",
                                    "Empresa",
                                    "Impresa",
                                    "Empresa",
                                    "企业",
                                    "Бизнес",
                                    "Virksomhed",
                                    "قطاع الأعمال",
                                ),
                            },
                            {
                                "key": "government",
                                "label": "Government",
                                "translations": _tr(
                                    "Behörde",
                                    "Administration",
                                    "Gobierno",
                                    "Pubblica amministrazione",
                                    "Governo",
                                    "政府",
                                    "Государственный орган",
                                    "Myndighed",
                                    "جهة حكومية",
                                ),
                            },
                            {
                                "key": "visitor",
                                "label": "Visitor",
                                "translations": _tr(
                                    "Besucher",
                                    "Visiteur",
                                    "Visitante",
                                    "Visitatore",
                                    "Visitante",
                                    "访客",
                                    "Посетитель",
                                    "Besøgende",
                                    "زائر",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "deliveryChannel",
                        "label": "Delivery Channels",
                        "type": "multiple_select",
                        "weight": 1,
                        "translations": _tr(
                            "Bereitstellungskanäle",
                            "Canaux de distribution",
                            "Canales de entrega",
                            "Canali di erogazione",
                            "Canais de entrega",
                            "服务渠道",
                            "Каналы предоставления",
                            "Leveringskanaler",
                            "قنوات تقديم الخدمة",
                        ),
                        "options": [
                            {
                                "key": "portal",
                                "label": "Web Portal",
                                "translations": _tr(
                                    "Webportal",
                                    "Portail web",
                                    "Portal web",
                                    "Portale web",
                                    "Portal web",
                                    "网上门户",
                                    "Веб-портал",
                                    "Webportal",
                                    "البوابة الإلكترونية",
                                ),
                            },
                            {
                                "key": "mobileApp",
                                "label": "Mobile App",
                                "translations": _tr(
                                    "Mobile App",
                                    "Application mobile",
                                    "Aplicación móvil",
                                    "App mobile",
                                    "Aplicativo móvel",
                                    "移动应用",
                                    "Мобильное приложение",
                                    "Mobilapp",
                                    "تطبيق الجوال",
                                ),
                            },
                            {
                                "key": "serviceCenter",
                                "label": "Service Center",
                                "translations": _tr(
                                    "Servicecenter",
                                    "Centre de service",
                                    "Centro de servicio",
                                    "Centro servizi",
                                    "Central de atendimento",
                                    "服务中心",
                                    "Центр обслуживания",
                                    "Servicecenter",
                                    "مركز الخدمة",
                                ),
                            },
                            {
                                "key": "callCenter",
                                "label": "Call Center",
                                "translations": _tr(
                                    "Callcenter",
                                    "Centre d'appels",
                                    "Centro de llamadas",
                                    "Call center",
                                    "Central telefônica",
                                    "呼叫中心",
                                    "Колл-центр",
                                    "Callcenter",
                                    "مركز الاتصال",
                                ),
                            },
                            {
                                "key": "kiosk",
                                "label": "Kiosk",
                                "translations": _tr(
                                    "Kiosk",
                                    "Borne",
                                    "Quiosco",
                                    "Chiosco",
                                    "Quiosque",
                                    "自助终端",
                                    "Киоск",
                                    "Kiosk",
                                    "جهاز الخدمة الذاتية",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "serviceMaturity",
                        "label": "Service Maturity",
                        "type": "single_select",
                        "weight": 1,
                        "translations": _tr(
                            "Servicereifegrad",
                            "Maturité du service",
                            "Madurez del servicio",
                            "Maturità del servizio",
                            "Maturidade do serviço",
                            "服务成熟度",
                            "Зрелость услуги",
                            "Servicemodenhed",
                            "نضج الخدمة",
                        ),
                        "options": [
                            {
                                "key": "informational",
                                "label": "Informational",
                                "color": "#9e9e9e",
                                "translations": _tr(
                                    "Informativ",
                                    "Informationnel",
                                    "Informativo",
                                    "Informativo",
                                    "Informativo",
                                    "信息型",
                                    "Информационная",
                                    "Informativ",
                                    "معلوماتية",
                                ),
                            },
                            {
                                "key": "interactive",
                                "label": "Interactive",
                                "color": "#ffb300",
                                "translations": _tr(
                                    "Interaktiv",
                                    "Interactif",
                                    "Interactivo",
                                    "Interattivo",
                                    "Interativo",
                                    "交互型",
                                    "Интерактивная",
                                    "Interaktiv",
                                    "تفاعلية",
                                ),
                            },
                            {
                                "key": "transactional",
                                "label": "Transactional",
                                "color": "#43a047",
                                "translations": _tr(
                                    "Transaktional",
                                    "Transactionnel",
                                    "Transaccional",
                                    "Transazionale",
                                    "Transacional",
                                    "事务型",
                                    "Транзакционная",
                                    "Transaktionel",
                                    "إجرائية",
                                ),
                            },
                            {
                                "key": "proactive",
                                "label": "Proactive",
                                "color": "#1565c0",
                                "translations": _tr(
                                    "Proaktiv",
                                    "Proactif",
                                    "Proactivo",
                                    "Proattivo",
                                    "Proativo",
                                    "主动型",
                                    "Проактивная",
                                    "Proaktiv",
                                    "استباقية",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "feeModel",
                        "label": "Fee Model",
                        "type": "single_select",
                        "weight": 1,
                        "translations": _tr(
                            "Gebührenmodell",
                            "Modèle de tarification",
                            "Modelo de tarifas",
                            "Modello tariffario",
                            "Modelo de tarifação",
                            "收费模式",
                            "Модель оплаты",
                            "Gebyrmodel",
                            "نموذج الرسوم",
                        ),
                        "options": [
                            {
                                "key": "free",
                                "label": "Free",
                                "color": "#43a047",
                                "translations": _tr(
                                    "Kostenlos",
                                    "Gratuit",
                                    "Gratuito",
                                    "Gratuito",
                                    "Gratuito",
                                    "免费",
                                    "Бесплатно",
                                    "Gratis",
                                    "مجانية",
                                ),
                            },
                            {
                                "key": "paid",
                                "label": "Paid",
                                "color": "#fb8c00",
                                "translations": _tr(
                                    "Kostenpflichtig",
                                    "Payant",
                                    "De pago",
                                    "A pagamento",
                                    "Pago",
                                    "收费",
                                    "Платно",
                                    "Betalt",
                                    "مدفوعة",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "slaDays",
                        "label": "SLA (days)",
                        "type": "number",
                        "weight": 1,
                        "translations": _tr(
                            "SLA (Tage)",
                            "SLA (jours)",
                            "SLA (días)",
                            "SLA (giorni)",
                            "SLA (dias)",
                            "服务水平协议（天）",
                            "SLA (дней)",
                            "SLA (dage)",
                            "اتفاقية مستوى الخدمة (أيام)",
                        ),
                    },
                    {
                        "key": "monthlyTransactions",
                        "label": "Monthly Transactions",
                        "type": "number",
                        "weight": 0,
                        "translations": _tr(
                            "Monatliche Transaktionen",
                            "Transactions mensuelles",
                            "Transacciones mensuales",
                            "Transazioni mensili",
                            "Transações mensais",
                            "月交易量",
                            "Транзакций в месяц",
                            "Månedlige transaktioner",
                            "المعاملات الشهرية",
                        ),
                    },
                    {
                        "key": "sharedServiceConsumer",
                        "label": "Uses National Shared Services",
                        "type": "boolean",
                        "weight": 0,
                        "translations": _tr(
                            "Nutzt nationale Shared Services",
                            "Utilise des services partagés nationaux",
                            "Usa servicios compartidos nacionales",
                            "Usa servizi condivisi nazionali",
                            "Usa serviços compartilhados nacionais",
                            "使用国家共享服务",
                            "Использует национальные общие сервисы",
                            "Bruger nationale delte tjenester",
                            "تستخدم الخدمات الوطنية المشتركة",
                        ),
                    },
                ],
            },
        ],
    },
    {
        "key": "DataExchange",
        "label": "Data Exchange",
        "description": (
            "A governed data exchange between applications or with an external "
            "party — the NORA DRM Data Exchange artifact."
        ),
        "icon": "swap_horizontal_circle",
        "color": "#5c6bc0",
        "category": "Data",
        "has_hierarchy": False,
        "subtypes": [],
        "sort_order": 21,
        "translations": {
            "label": _tr(
                "Datenaustausch",
                "Échange de données",
                "Intercambio de datos",
                "Scambio di dati",
                "Troca de dados",
                "数据交换",
                "Обмен данными",
                "Dataudveksling",
                "تبادل البيانات",
            ),
            "description": _tr(
                "Ein gesteuerter Datenaustausch zwischen Anwendungen oder mit externen Parteien — das DRM-Artefakt Datenaustausch in NORA.",  # noqa: E501
                "Un échange de données gouverné entre applications ou avec une partie externe — l'artefact Échange de données du DRM NORA.",  # noqa: E501
                "Un intercambio de datos gobernado entre aplicaciones o con una parte externa — el artefacto de intercambio de datos del DRM de NORA.",  # noqa: E501
                "Uno scambio di dati governato tra applicazioni o con una parte esterna — l'artefatto Scambio di dati del DRM NORA.",  # noqa: E501
                "Uma troca de dados governada entre aplicações ou com uma parte externa — o artefato de troca de dados do DRM NORA.",  # noqa: E501
                "应用之间或与外部机构之间受治理的数据交换——NORA DRM 的数据交换工件。",
                "Управляемый обмен данными между приложениями или с внешней стороной — артефакт DRM NORA.",  # noqa: E501
                "En styret dataudveksling mellem applikationer eller med en ekstern part — NORA DRM-artefaktet Dataudveksling.",  # noqa: E501
                "تبادل بيانات خاضع للحوكمة بين التطبيقات أو مع جهة خارجية — أحد مخرجات النموذج المرجعي للبيانات في نورا.",  # noqa: E501
            ),
        },
        "stakeholder_roles": [
            {
                "key": "responsible",
                "label": "Responsible",
                "translations": {
                    "label": _tr(
                        "Verantwortlicher",
                        "Responsable",
                        "Responsable",
                        "Responsabile",
                        "Responsável",
                        "负责人",
                        "Ответственный",
                        "Ansvarlig",
                        "المسؤول",
                    )
                },
            },
            {
                "key": "observer",
                "label": "Observer",
                "translations": {
                    "label": _tr(
                        "Beobachter",
                        "Observateur",
                        "Observador",
                        "Osservatore",
                        "Observador",
                        "观察者",
                        "Наблюдатель",
                        "Observatør",
                        "مراقب",
                    )
                },
            },
        ],
        "fields_schema": [
            {
                "section": "Exchange Information",
                "translations": _tr(
                    "Austauschinformationen",
                    "Informations sur l'échange",
                    "Información del intercambio",
                    "Informazioni sullo scambio",
                    "Informações da troca",
                    "交换信息",
                    "Информация об обмене",
                    "Udvekslingsinformation",
                    "معلومات التبادل",
                ),
                "fields": [
                    {
                        "key": "exchangeMethod",
                        "label": "Exchange Method",
                        "type": "single_select",
                        "weight": 1,
                        "translations": _tr(
                            "Austauschmethode",
                            "Méthode d'échange",
                            "Método de intercambio",
                            "Metodo di scambio",
                            "Método de troca",
                            "交换方式",
                            "Метод обмена",
                            "Udvekslingsmetode",
                            "طريقة التبادل",
                        ),
                        "options": [
                            {
                                "key": "api",
                                "label": "API",
                                "translations": _tr(
                                    "API",
                                    "API",
                                    "API",
                                    "API",
                                    "API",
                                    "API",
                                    "API",
                                    "API",
                                    "واجهة برمجة التطبيقات (API)",
                                ),
                            },
                            {
                                "key": "fileTransfer",
                                "label": "File Transfer",
                                "translations": _tr(
                                    "Dateitransfer",
                                    "Transfert de fichiers",
                                    "Transferencia de archivos",
                                    "Trasferimento file",
                                    "Transferência de arquivos",
                                    "文件传输",
                                    "Передача файлов",
                                    "Filoverførsel",
                                    "نقل الملفات",
                                ),
                            },
                            {
                                "key": "messaging",
                                "label": "Messaging",
                                "translations": _tr(
                                    "Messaging",
                                    "Messagerie",
                                    "Mensajería",
                                    "Messaggistica",
                                    "Mensageria",
                                    "消息传递",
                                    "Обмен сообщениями",
                                    "Messaging",
                                    "تراسل",
                                ),
                            },
                            {
                                "key": "database",
                                "label": "Database",
                                "translations": _tr(
                                    "Datenbank",
                                    "Base de données",
                                    "Base de datos",
                                    "Database",
                                    "Banco de dados",
                                    "数据库",
                                    "База данных",
                                    "Database",
                                    "قاعدة بيانات",
                                ),
                            },
                            {
                                "key": "manual",
                                "label": "Manual",
                                "translations": _tr(
                                    "Manuell",
                                    "Manuel",
                                    "Manual",
                                    "Manuale",
                                    "Manual",
                                    "人工",
                                    "Вручную",
                                    "Manuel",
                                    "يدوي",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "frequency",
                        "label": "Frequency",
                        "type": "single_select",
                        "weight": 1,
                        "translations": _tr(
                            "Häufigkeit",
                            "Fréquence",
                            "Frecuencia",
                            "Frequenza",
                            "Frequência",
                            "频率",
                            "Периодичность",
                            "Frekvens",
                            "التكرار",
                        ),
                        "options": [
                            {
                                "key": "realtime",
                                "label": "Real-time",
                                "translations": _tr(
                                    "Echtzeit",
                                    "Temps réel",
                                    "Tiempo real",
                                    "Tempo reale",
                                    "Tempo real",
                                    "实时",
                                    "В реальном времени",
                                    "Realtid",
                                    "لحظي",
                                ),
                            },
                            {
                                "key": "daily",
                                "label": "Daily",
                                "translations": _tr(
                                    "Täglich",
                                    "Quotidien",
                                    "Diario",
                                    "Giornaliero",
                                    "Diário",
                                    "每日",
                                    "Ежедневно",
                                    "Dagligt",
                                    "يومي",
                                ),
                            },
                            {
                                "key": "weekly",
                                "label": "Weekly",
                                "translations": _tr(
                                    "Wöchentlich",
                                    "Hebdomadaire",
                                    "Semanal",
                                    "Settimanale",
                                    "Semanal",
                                    "每周",
                                    "Еженедельно",
                                    "Ugentligt",
                                    "أسبوعي",
                                ),
                            },
                            {
                                "key": "monthly",
                                "label": "Monthly",
                                "translations": _tr(
                                    "Monatlich",
                                    "Mensuel",
                                    "Mensual",
                                    "Mensile",
                                    "Mensal",
                                    "每月",
                                    "Ежемесячно",
                                    "Månedligt",
                                    "شهري",
                                ),
                            },
                            {
                                "key": "adhoc",
                                "label": "Ad hoc",
                                "translations": _tr(
                                    "Ad hoc",
                                    "Ponctuel",
                                    "Puntual",
                                    "Ad hoc",
                                    "Sob demanda",
                                    "临时",
                                    "По запросу",
                                    "Ad hoc",
                                    "عند الحاجة",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "externalParty",
                        "label": "External Party",
                        "type": "text",
                        "weight": 0,
                        "translations": _tr(
                            "Externe Partei",
                            "Partie externe",
                            "Parte externa",
                            "Parte esterna",
                            "Parte externa",
                            "外部机构",
                            "Внешняя сторона",
                            "Ekstern part",
                            "الجهة الخارجية",
                        ),
                    },
                    {
                        "key": "viaGsb",
                        "label": "Via Government Service Bus (GSB)",
                        "type": "boolean",
                        "weight": 0,
                        "translations": _tr(
                            "Über Government Service Bus (GSB)",
                            "Via le Government Service Bus (GSB)",
                            "A través del Government Service Bus (GSB)",
                            "Tramite Government Service Bus (GSB)",
                            "Via Government Service Bus (GSB)",
                            "通过政府服务总线 (GSB)",
                            "Через государственную сервисную шину (GSB)",
                            "Via Government Service Bus (GSB)",
                            "عبر قناة التكامل الحكومية (GSB)",
                        ),
                    },
                    {
                        "key": "dataClassificationCarried",
                        "label": "Classification Carried",
                        "type": "single_select",
                        "weight": 1,
                        "translations": _tr(
                            "Transportierte Klassifizierung",
                            "Classification transportée",
                            "Clasificación transportada",
                            "Classificazione trasportata",
                            "Classificação transportada",
                            "承载的数据分级",
                            "Передаваемая классификация",
                            "Transporteret klassifikation",
                            "تصنيف البيانات المنقولة",
                        ),
                        "options": [
                            {
                                "key": "topSecret",
                                "label": "Top Secret",
                                "color": "#b71c1c",
                                "translations": _tr(
                                    "Streng geheim",
                                    "Très secret",
                                    "Alto secreto",
                                    "Segretissimo",
                                    "Ultrassecreto",
                                    "绝密",
                                    "Совершенно секретно",
                                    "Yderst hemmeligt",
                                    "سري للغاية",
                                ),
                            },
                            {
                                "key": "secret",
                                "label": "Secret",
                                "color": "#e53935",
                                "translations": _tr(
                                    "Geheim",
                                    "Secret",
                                    "Secreto",
                                    "Segreto",
                                    "Secreto",
                                    "机密",
                                    "Секретно",
                                    "Hemmeligt",
                                    "سري",
                                ),
                            },
                            {
                                "key": "restricted",
                                "label": "Restricted",
                                "color": "#fb8c00",
                                "translations": _tr(
                                    "Eingeschränkt",
                                    "Restreint",
                                    "Restringido",
                                    "Riservato",
                                    "Restrito",
                                    "受限",
                                    "Ограниченный доступ",
                                    "Begrænset",
                                    "مقيد",
                                ),
                            },
                            {
                                "key": "public",
                                "label": "Public",
                                "color": "#43a047",
                                "translations": _tr(
                                    "Öffentlich",
                                    "Public",
                                    "Público",
                                    "Pubblico",
                                    "Público",
                                    "公开",
                                    "Общедоступно",
                                    "Offentligt",
                                    "عام",
                                ),
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "key": "KPI",
        "label": "KPI",
        "description": (
            "A performance indicator (NORA PRM): baseline, target and current "
            "values measuring objectives, services and initiatives."
        ),
        "icon": "speed",
        "color": "#c2185b",
        "category": "Business",
        "has_hierarchy": False,
        "subtypes": [],
        "sort_order": 22,
        "translations": {
            "label": _tr(
                "KPI", "KPI", "KPI", "KPI", "KPI", "关键绩效指标", "КПЭ", "KPI", "مؤشر أداء رئيسي"
            ),
            "description": _tr(
                "Ein Leistungsindikator (NORA PRM): Basis-, Ziel- und Ist-Werte zur Messung von Zielen, Services und Vorhaben.",  # noqa: E501
                "Un indicateur de performance (PRM NORA) : valeurs de référence, cible et actuelle mesurant objectifs, services et initiatives.",  # noqa: E501
                "Un indicador de rendimiento (PRM de NORA): valores base, objetivo y actual que miden objetivos, servicios e iniciativas.",  # noqa: E501
                "Un indicatore di prestazione (PRM NORA): valori di base, obiettivo e attuali che misurano obiettivi, servizi e iniziative.",  # noqa: E501
                "Um indicador de desempenho (PRM NORA): valores de linha de base, alvo e atual que medem objetivos, serviços e iniciativas.",  # noqa: E501
                "绩效指标(NORA PRM):以基线值、目标值和当前值衡量目标、服务与举措。",
                "Показатель эффективности (PRM NORA): базовое, целевое и текущее значения для целей, услуг и инициатив.",  # noqa: E501
                "En præstationsindikator (NORA PRM): basis-, mål- og aktuelle værdier, der måler mål, services og initiativer.",  # noqa: E501
                "مؤشر أداء (النموذج المرجعي للأداء في نورا): قيم الأساس والمستهدف والحالي لقياس الأهداف والخدمات والمبادرات.",  # noqa: E501
            ),
        },
        "stakeholder_roles": [
            {
                "key": "responsible",
                "label": "Responsible",
                "translations": {
                    "label": _tr(
                        "Verantwortlicher",
                        "Responsable",
                        "Responsable",
                        "Responsabile",
                        "Responsável",
                        "负责人",
                        "Ответственный",
                        "Ansvarlig",
                        "المسؤول",
                    )
                },
            },
            {
                "key": "observer",
                "label": "Observer",
                "translations": {
                    "label": _tr(
                        "Beobachter",
                        "Observateur",
                        "Observador",
                        "Osservatore",
                        "Observador",
                        "观察者",
                        "Наблюдатель",
                        "Observatør",
                        "مراقب",
                    )
                },
            },
        ],
        "fields_schema": [
            {
                "section": "Measurement",
                "translations": _tr(
                    "Messung",
                    "Mesure",
                    "Medición",
                    "Misurazione",
                    "Medição",
                    "测量",
                    "Измерение",
                    "Måling",
                    "القياس",
                ),
                "fields": [
                    {
                        "key": "unit",
                        "label": "Unit",
                        "type": "text",
                        "weight": 1,
                        "translations": _tr(
                            "Einheit",
                            "Unité",
                            "Unidad",
                            "Unità",
                            "Unidade",
                            "单位",
                            "Единица",
                            "Enhed",
                            "الوحدة",
                        ),
                    },
                    {
                        "key": "baselineValue",
                        "label": "Baseline Value",
                        "type": "number",
                        "weight": 1,
                        "translations": _tr(
                            "Basiswert",
                            "Valeur de référence",
                            "Valor base",
                            "Valore di base",
                            "Valor de linha de base",
                            "基线值",
                            "Базовое значение",
                            "Basisværdi",
                            "قيمة الأساس",
                        ),
                    },
                    {
                        "key": "targetValue",
                        "label": "Target Value",
                        "type": "number",
                        "weight": 1,
                        "translations": _tr(
                            "Zielwert",
                            "Valeur cible",
                            "Valor objetivo",
                            "Valore obiettivo",
                            "Valor alvo",
                            "目标值",
                            "Целевое значение",
                            "Målværdi",
                            "القيمة المستهدفة",
                        ),
                    },
                    {
                        "key": "currentValue",
                        "label": "Current Value",
                        "type": "number",
                        "weight": 1,
                        "translations": _tr(
                            "Ist-Wert",
                            "Valeur actuelle",
                            "Valor actual",
                            "Valore attuale",
                            "Valor atual",
                            "当前值",
                            "Текущее значение",
                            "Aktuel værdi",
                            "القيمة الحالية",
                        ),
                    },
                    {
                        "key": "measurementFrequency",
                        "label": "Measurement Frequency",
                        "type": "single_select",
                        "weight": 0,
                        "translations": _tr(
                            "Messhäufigkeit",
                            "Fréquence de mesure",
                            "Frecuencia de medición",
                            "Frequenza di misurazione",
                            "Frequência de medição",
                            "测量频率",
                            "Периодичность измерения",
                            "Målefrekvens",
                            "تكرار القياس",
                        ),
                        "options": [
                            {
                                "key": "monthly",
                                "label": "Monthly",
                                "translations": _tr(
                                    "Monatlich",
                                    "Mensuelle",
                                    "Mensual",
                                    "Mensile",
                                    "Mensal",
                                    "每月",
                                    "Ежемесячно",
                                    "Månedligt",
                                    "شهري",
                                ),
                            },
                            {
                                "key": "quarterly",
                                "label": "Quarterly",
                                "translations": _tr(
                                    "Vierteljährlich",
                                    "Trimestrielle",
                                    "Trimestral",
                                    "Trimestrale",
                                    "Trimestral",
                                    "每季度",
                                    "Ежеквартально",
                                    "Kvartalsvist",
                                    "ربع سنوي",
                                ),
                            },
                            {
                                "key": "yearly",
                                "label": "Yearly",
                                "translations": _tr(
                                    "Jährlich",
                                    "Annuelle",
                                    "Anual",
                                    "Annuale",
                                    "Anual",
                                    "每年",
                                    "Ежегодно",
                                    "Årligt",
                                    "سنوي",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "direction",
                        "label": "Direction",
                        "type": "single_select",
                        "weight": 0,
                        "translations": _tr(
                            "Richtung",
                            "Sens",
                            "Dirección",
                            "Direzione",
                            "Direção",
                            "方向",
                            "Направление",
                            "Retning",
                            "الاتجاه",
                        ),
                        "options": [
                            {
                                "key": "higherIsBetter",
                                "label": "Higher is better",
                                "color": "#2e7d32",
                                "translations": _tr(
                                    "Höher ist besser",
                                    "Plus haut est mieux",
                                    "Cuanto más alto, mejor",
                                    "Più alto è meglio",
                                    "Quanto maior, melhor",
                                    "越高越好",
                                    "Чем выше, тем лучше",
                                    "Højere er bedre",
                                    "الأعلى أفضل",
                                ),
                            },
                            {
                                "key": "lowerIsBetter",
                                "label": "Lower is better",
                                "color": "#1565c0",
                                "translations": _tr(
                                    "Niedriger ist besser",
                                    "Plus bas est mieux",
                                    "Cuanto más bajo, mejor",
                                    "Più basso è meglio",
                                    "Quanto menor, melhor",
                                    "越低越好",
                                    "Чем ниже, тем лучше",
                                    "Lavere er bedre",
                                    "الأدنى أفضل",
                                ),
                            },
                        ],
                    },
                ],
            },
        ],
    },
    # ── v3 (six-layer model): Beneficiary Experience + Security layer types ──
    {
        "key": "BeneficiaryJourney",
        "label": "Beneficiary Journey",
        "description": (
            "An end-to-end journey a citizen, resident or business follows when "
            "consuming government services — the NORA Beneficiary Experience "
            "layer artifact."
        ),
        "icon": "route",
        "color": "#00a3a3",
        "category": "Beneficiary Experience",
        "has_hierarchy": True,
        "subtypes": [],
        "sort_order": 23,
        "translations": {
            "label": _tr(
                "Nutzerreise",
                "Parcours bénéficiaire",
                "Recorrido del beneficiario",
                "Percorso del beneficiario",
                "Jornada do beneficiário",
                "受益人旅程",
                "Путь получателя услуг",
                "Modtagerrejse",
                "رحلة المستفيد",
            ),
            "description": _tr(
                "Eine End-to-End-Reise, die Bürger, Einwohner oder Unternehmen bei der Nutzung von Verwaltungsdienstleistungen durchlaufen — das Artefakt der NORA-Schicht Nutzererlebnis.",  # noqa: E501
                "Un parcours de bout en bout suivi par un citoyen, un résident ou une entreprise lors de la consommation de services publics — l'artefact de la couche Expérience bénéficiaire de NORA.",  # noqa: E501
                "Un recorrido de extremo a extremo que sigue un ciudadano, residente o empresa al consumir servicios gubernamentales — el artefacto de la capa Experiencia del beneficiario de NORA.",  # noqa: E501
                "Un percorso end-to-end che un cittadino, residente o azienda segue nell'utilizzo dei servizi governativi — l'artefatto del livello Esperienza del beneficiario di NORA.",  # noqa: E501
                "Uma jornada de ponta a ponta que um cidadão, residente ou empresa percorre ao consumir serviços governamentais — o artefato da camada Experiência do beneficiário do NORA.",  # noqa: E501
                "公民、居民或企业在使用政府服务时经历的端到端旅程——NORA 受益人体验层的工件。",
                "Сквозной путь гражданина, резидента или бизнеса при получении государственных услуг — артефакт слоя «Опыт получателя» NORA.",  # noqa: E501
                "En end-to-end-rejse, som en borger, bosiddende eller virksomhed følger ved brug af offentlige services — NORA-lagets artefakt for modtageroplevelse.",  # noqa: E501
                "رحلة شاملة يتبعها المواطن أو المقيم أو منشأة الأعمال عند الاستفادة من الخدمات الحكومية — أحد مخرجات طبقة تجربة المستفيد في نورا.",  # noqa: E501
            ),
        },
        "stakeholder_roles": [
            {
                "key": "responsible",
                "label": "Responsible",
                "translations": {
                    "label": _tr(
                        "Verantwortlicher",
                        "Responsable",
                        "Responsable",
                        "Responsabile",
                        "Responsável",
                        "负责人",
                        "Ответственный",
                        "Ansvarlig",
                        "المسؤول",
                    ),
                },
            },
            {
                "key": "observer",
                "label": "Observer",
                "translations": {
                    "label": _tr(
                        "Beobachter",
                        "Observateur",
                        "Observador",
                        "Osservatore",
                        "Observador",
                        "观察者",
                        "Наблюдатель",
                        "Observatør",
                        "مراقب",
                    ),
                },
            },
        ],
        "fields_schema": [
            {
                "section": "Journey Information",
                "translations": _tr(
                    "Reiseinformationen",
                    "Informations sur le parcours",
                    "Información del recorrido",
                    "Informazioni sul percorso",
                    "Informações da jornada",
                    "旅程信息",
                    "Информация о пути",
                    "Rejseinformation",
                    "معلومات الرحلة",
                ),
                "fields": [
                    {
                        "key": "journeyStage",
                        "label": "Journey Stage",
                        "type": "single_select",
                        "weight": 1,
                        "translations": _tr(
                            "Reisephase",
                            "Étape du parcours",
                            "Etapa del recorrido",
                            "Fase del percorso",
                            "Etapa da jornada",
                            "旅程阶段",
                            "Этап пути",
                            "Rejsefase",
                            "مرحلة الرحلة",
                        ),
                        "options": [
                            {
                                "key": "awareness",
                                "label": "Awareness",
                                "translations": _tr(
                                    "Aufmerksamkeit",
                                    "Sensibilisation",
                                    "Conocimiento",
                                    "Consapevolezza",
                                    "Conscientização",
                                    "认知",
                                    "Осведомлённость",
                                    "Opmærksomhed",
                                    "الوعي",
                                ),
                            },
                            {
                                "key": "access",
                                "label": "Access",
                                "translations": _tr(
                                    "Zugang",
                                    "Accès",
                                    "Acceso",
                                    "Accesso",
                                    "Acesso",
                                    "访问",
                                    "Доступ",
                                    "Adgang",
                                    "الوصول",
                                ),
                            },
                            {
                                "key": "service",
                                "label": "Service Delivery",
                                "translations": _tr(
                                    "Leistungserbringung",
                                    "Prestation du service",
                                    "Prestación del servicio",
                                    "Erogazione del servizio",
                                    "Prestação do serviço",
                                    "服务交付",
                                    "Оказание услуги",
                                    "Servicelevering",
                                    "تقديم الخدمة",
                                ),
                            },
                            {
                                "key": "followup",
                                "label": "Follow-up",
                                "translations": _tr(
                                    "Nachverfolgung",
                                    "Suivi",
                                    "Seguimiento",
                                    "Follow-up",
                                    "Acompanhamento",
                                    "跟进",
                                    "Сопровождение",
                                    "Opfølgning",
                                    "المتابعة",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "persona",
                        "label": "Persona",
                        "type": "text",
                        "weight": 1,
                        "translations": _tr(
                            "Persona",
                            "Persona",
                            "Persona",
                            "Persona",
                            "Persona",
                            "用户画像",
                            "Персона",
                            "Persona",
                            "الشخصية النموذجية",
                        ),
                    },
                ],
            },
        ],
    },
    {
        "key": "Channel",
        "label": "Channel",
        "description": (
            "A delivery channel through which beneficiaries access government "
            "services — web portal, mobile app, branch, call centre, partner or "
            "API."
        ),
        "icon": "devices",
        "color": "#26b5a8",
        "category": "Beneficiary Experience",
        "has_hierarchy": False,
        "subtypes": [],
        "sort_order": 24,
        "translations": {
            "label": _tr(
                "Kanal",
                "Canal",
                "Canal",
                "Canale",
                "Canal",
                "渠道",
                "Канал",
                "Kanal",
                "القناة",
            ),
            "description": _tr(
                "Ein Bereitstellungskanal, über den Begünstigte auf Verwaltungsdienstleistungen zugreifen — Webportal, Mobile App, Filiale, Callcenter, Partner oder API.",  # noqa: E501
                "Un canal de prestation par lequel les bénéficiaires accèdent aux services publics — portail web, application mobile, agence, centre d'appels, partenaire ou API.",  # noqa: E501
                "Un canal de prestación a través del cual los beneficiarios acceden a los servicios gubernamentales — portal web, aplicación móvil, sucursal, centro de llamadas, socio o API.",  # noqa: E501
                "Un canale di erogazione attraverso cui i beneficiari accedono ai servizi governativi — portale web, app mobile, filiale, call center, partner o API.",  # noqa: E501
                "Um canal de entrega pelo qual os beneficiários acessam os serviços governamentais — portal web, aplicativo móvel, agência, central de atendimento, parceiro ou API.",  # noqa: E501
                "受益人访问政府服务的交付渠道——门户网站、移动应用、网点、呼叫中心、合作伙伴或 API。",  # noqa: E501
                "Канал предоставления, через который получатели пользуются государственными услугами — веб-портал, мобильное приложение, офис, кол-центр, партнёр или API.",  # noqa: E501
                "En leveringskanal, hvorigennem modtagere får adgang til offentlige services — webportal, mobilapp, filial, callcenter, partner eller API.",  # noqa: E501
                "قناة تقديم يصل من خلالها المستفيدون إلى الخدمات الحكومية — بوابة إلكترونية أو تطبيق جوال أو فرع أو مركز اتصال أو شريك أو واجهة برمجية.",  # noqa: E501
            ),
        },
        "stakeholder_roles": [
            {
                "key": "responsible",
                "label": "Responsible",
                "translations": {
                    "label": _tr(
                        "Verantwortlicher",
                        "Responsable",
                        "Responsable",
                        "Responsabile",
                        "Responsável",
                        "负责人",
                        "Ответственный",
                        "Ansvarlig",
                        "المسؤول",
                    ),
                },
            },
            {
                "key": "observer",
                "label": "Observer",
                "translations": {
                    "label": _tr(
                        "Beobachter",
                        "Observateur",
                        "Observador",
                        "Osservatore",
                        "Observador",
                        "观察者",
                        "Наблюдатель",
                        "Observatør",
                        "مراقب",
                    ),
                },
            },
        ],
        "fields_schema": [
            {
                "section": "Channel Information",
                "translations": _tr(
                    "Kanalinformationen",
                    "Informations sur le canal",
                    "Información del canal",
                    "Informazioni sul canale",
                    "Informações do canal",
                    "渠道信息",
                    "Информация о канале",
                    "Kanalinformation",
                    "معلومات القناة",
                ),
                "fields": [
                    {
                        "key": "channelType",
                        "label": "Channel Type",
                        "type": "single_select",
                        "weight": 1,
                        "translations": _tr(
                            "Kanaltyp",
                            "Type de canal",
                            "Tipo de canal",
                            "Tipo di canale",
                            "Tipo de canal",
                            "渠道类型",
                            "Тип канала",
                            "Kanaltype",
                            "نوع القناة",
                        ),
                        "options": [
                            {
                                "key": "web",
                                "label": "Web Portal",
                                "translations": _tr(
                                    "Webportal",
                                    "Portail web",
                                    "Portal web",
                                    "Portale web",
                                    "Portal web",
                                    "门户网站",
                                    "Веб-портал",
                                    "Webportal",
                                    "البوابة الإلكترونية",
                                ),
                            },
                            {
                                "key": "mobile",
                                "label": "Mobile App",
                                "translations": _tr(
                                    "Mobile App",
                                    "Application mobile",
                                    "Aplicación móvil",
                                    "App mobile",
                                    "Aplicativo móvel",
                                    "移动应用",
                                    "Мобильное приложение",
                                    "Mobilapp",
                                    "تطبيق الجوال",
                                ),
                            },
                            {
                                "key": "branch",
                                "label": "Branch / Office",
                                "translations": _tr(
                                    "Filiale / Büro",
                                    "Agence / Bureau",
                                    "Sucursal / Oficina",
                                    "Filiale / Ufficio",
                                    "Agência / Escritório",
                                    "网点/办事处",
                                    "Офис / Отделение",
                                    "Filial / Kontor",
                                    "الفرع / المكتب",
                                ),
                            },
                            {
                                "key": "callCenter",
                                "label": "Call Centre",
                                "translations": _tr(
                                    "Callcenter",
                                    "Centre d'appels",
                                    "Centro de llamadas",
                                    "Call center",
                                    "Central de atendimento",
                                    "呼叫中心",
                                    "Кол-центр",
                                    "Callcenter",
                                    "مركز الاتصال",
                                ),
                            },
                            {
                                "key": "partner",
                                "label": "Partner",
                                "translations": _tr(
                                    "Partner",
                                    "Partenaire",
                                    "Socio",
                                    "Partner",
                                    "Parceiro",
                                    "合作伙伴",
                                    "Партнёр",
                                    "Partner",
                                    "الشريك",
                                ),
                            },
                            {
                                "key": "api",
                                "label": "API",
                                "translations": _tr(
                                    "API",
                                    "API",
                                    "API",
                                    "API",
                                    "API",
                                    "应用程序接口",
                                    "API",
                                    "API",
                                    "واجهة برمجة التطبيقات",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "channelMaturity",
                        "label": "Maturity",
                        "type": "single_select",
                        "weight": 1,
                        "translations": _tr(
                            "Reifegrad",
                            "Maturité",
                            "Madurez",
                            "Maturità",
                            "Maturidade",
                            "成熟度",
                            "Зрелость",
                            "Modenhed",
                            "النضج",
                        ),
                        "options": [
                            {
                                "key": "basic",
                                "label": "Basic",
                                "translations": _tr(
                                    "Grundlegend",
                                    "Basique",
                                    "Básico",
                                    "Base",
                                    "Básico",
                                    "基础",
                                    "Базовый",
                                    "Grundlæggende",
                                    "أساسي",
                                ),
                            },
                            {
                                "key": "enhanced",
                                "label": "Enhanced",
                                "translations": _tr(
                                    "Erweitert",
                                    "Amélioré",
                                    "Mejorado",
                                    "Avanzato",
                                    "Aprimorado",
                                    "增强",
                                    "Расширенный",
                                    "Udvidet",
                                    "محسّن",
                                ),
                            },
                            {
                                "key": "transactional",
                                "label": "Transactional",
                                "translations": _tr(
                                    "Transaktional",
                                    "Transactionnel",
                                    "Transaccional",
                                    "Transazionale",
                                    "Transacional",
                                    "交易型",
                                    "Транзакционный",
                                    "Transaktionel",
                                    "تعاملي",
                                ),
                            },
                            {
                                "key": "proactive",
                                "label": "Proactive",
                                "translations": _tr(
                                    "Proaktiv",
                                    "Proactif",
                                    "Proactivo",
                                    "Proattivo",
                                    "Proativo",
                                    "主动型",
                                    "Проактивный",
                                    "Proaktiv",
                                    "استباقي",
                                ),
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "key": "SecurityControl",
        "label": "Security Control",
        "description": (
            "A security or data-protection control safeguarding the "
            "architecture — the NORA Security Architecture layer artifact "
            "(e.g. an NCA ECC control implementation)."
        ),
        "icon": "shield",
        "color": "#c62828",
        "category": "Security",
        "has_hierarchy": True,
        "subtypes": [],
        "sort_order": 25,
        "translations": {
            "label": _tr(
                "Sicherheitskontrolle",
                "Contrôle de sécurité",
                "Control de seguridad",
                "Controllo di sicurezza",
                "Controle de segurança",
                "安全控制",
                "Мера безопасности",
                "Sikkerhedskontrol",
                "ضابط أمني",
            ),
            "description": _tr(
                "Eine Sicherheits- oder Datenschutzkontrolle zum Schutz der Architektur — das Artefakt der NORA-Schicht Sicherheitsarchitektur (z. B. eine NCA-ECC-Kontrollumsetzung).",  # noqa: E501
                "Un contrôle de sécurité ou de protection des données protégeant l'architecture — l'artefact de la couche Architecture de sécurité de NORA (p. ex. la mise en œuvre d'un contrôle NCA ECC).",  # noqa: E501
                "Un control de seguridad o de protección de datos que salvaguarda la arquitectura — el artefacto de la capa Arquitectura de seguridad de NORA (p. ej., la implementación de un control NCA ECC).",  # noqa: E501
                "Un controllo di sicurezza o di protezione dei dati che salvaguarda l'architettura — l'artefatto del livello Architettura di sicurezza di NORA (ad es. l'implementazione di un controllo NCA ECC).",  # noqa: E501
                "Um controle de segurança ou de proteção de dados que protege a arquitetura — o artefato da camada Arquitetura de segurança do NORA (por exemplo, a implementação de um controle NCA ECC).",  # noqa: E501
                "保护架构的安全或数据保护控制——NORA 安全架构层的工件(例如 NCA ECC 控制的实施)。",
                "Мера безопасности или защиты данных, охраняющая архитектуру — артефакт слоя «Архитектура безопасности» NORA (например, реализация контроля NCA ECC).",  # noqa: E501
                "En sikkerheds- eller databeskyttelseskontrol, der beskytter arkitekturen — NORA-lagets artefakt for sikkerhedsarkitektur (f.eks. en NCA ECC-kontrolimplementering).",  # noqa: E501
                "ضابط أمني أو ضابط لحماية البيانات يحمي البنية المؤسسية — أحد مخرجات طبقة البنية الأمنية في نورا (مثل تطبيق أحد ضوابط الأمن السيبراني الأساسية من الهيئة الوطنية للأمن السيبراني).",  # noqa: E501
            ),
        },
        "stakeholder_roles": [
            {
                "key": "responsible",
                "label": "Responsible",
                "translations": {
                    "label": _tr(
                        "Verantwortlicher",
                        "Responsable",
                        "Responsable",
                        "Responsabile",
                        "Responsável",
                        "负责人",
                        "Ответственный",
                        "Ansvarlig",
                        "المسؤول",
                    ),
                },
            },
            {
                "key": "observer",
                "label": "Observer",
                "translations": {
                    "label": _tr(
                        "Beobachter",
                        "Observateur",
                        "Observador",
                        "Osservatore",
                        "Observador",
                        "观察者",
                        "Наблюдатель",
                        "Observatør",
                        "مراقب",
                    ),
                },
            },
        ],
        "fields_schema": [
            {
                "section": "Control Information",
                "translations": _tr(
                    "Kontrollinformationen",
                    "Informations sur le contrôle",
                    "Información del control",
                    "Informazioni sul controllo",
                    "Informações do controle",
                    "控制信息",
                    "Информация о мере",
                    "Kontrolinformation",
                    "معلومات الضابط",
                ),
                "fields": [
                    {
                        "key": "controlDomain",
                        "label": "Control Domain",
                        "type": "single_select",
                        "weight": 1,
                        "translations": _tr(
                            "Kontrollbereich",
                            "Domaine de contrôle",
                            "Dominio de control",
                            "Dominio di controllo",
                            "Domínio de controle",
                            "控制领域",
                            "Домен контроля",
                            "Kontroldomæne",
                            "مجال الضابط",
                        ),
                        "options": [
                            {
                                "key": "governance",
                                "label": "Governance",
                                "translations": _tr(
                                    "Governance",
                                    "Gouvernance",
                                    "Gobernanza",
                                    "Governance",
                                    "Governança",
                                    "治理",
                                    "Управление",
                                    "Governance",
                                    "الحوكمة",
                                ),
                            },
                            {
                                "key": "dataProtection",
                                "label": "Data Protection",
                                "translations": _tr(
                                    "Datenschutz",
                                    "Protection des données",
                                    "Protección de datos",
                                    "Protezione dei dati",
                                    "Proteção de dados",
                                    "数据保护",
                                    "Защита данных",
                                    "Databeskyttelse",
                                    "حماية البيانات",
                                ),
                            },
                            {
                                "key": "iam",
                                "label": "Identity & Access",
                                "translations": _tr(
                                    "Identität & Zugriff",
                                    "Identité et accès",
                                    "Identidad y acceso",
                                    "Identità e accesso",
                                    "Identidade e acesso",
                                    "身份与访问",
                                    "Идентификация и доступ",
                                    "Identitet & adgang",
                                    "الهوية والوصول",
                                ),
                            },
                            {
                                "key": "network",
                                "label": "Network Security",
                                "translations": _tr(
                                    "Netzwerksicherheit",
                                    "Sécurité réseau",
                                    "Seguridad de red",
                                    "Sicurezza di rete",
                                    "Segurança de rede",
                                    "网络安全",
                                    "Сетевая безопасность",
                                    "Netværkssikkerhed",
                                    "أمن الشبكات",
                                ),
                            },
                            {
                                "key": "appSec",
                                "label": "Application Security",
                                "translations": _tr(
                                    "Anwendungssicherheit",
                                    "Sécurité applicative",
                                    "Seguridad de aplicaciones",
                                    "Sicurezza applicativa",
                                    "Segurança de aplicações",
                                    "应用安全",
                                    "Безопасность приложений",
                                    "Applikationssikkerhed",
                                    "أمن التطبيقات",
                                ),
                            },
                            {
                                "key": "ops",
                                "label": "Security Operations",
                                "translations": _tr(
                                    "Sicherheitsbetrieb",
                                    "Opérations de sécurité",
                                    "Operaciones de seguridad",
                                    "Operazioni di sicurezza",
                                    "Operações de segurança",
                                    "安全运营",
                                    "Операционная безопасность",
                                    "Sikkerhedsdrift",
                                    "العمليات الأمنية",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "implementationStatus",
                        "label": "Implementation Status",
                        "type": "single_select",
                        "weight": 1,
                        "translations": _tr(
                            "Umsetzungsstatus",
                            "État de mise en œuvre",
                            "Estado de implementación",
                            "Stato di implementazione",
                            "Status de implementação",
                            "实施状态",
                            "Статус внедрения",
                            "Implementeringsstatus",
                            "حالة التطبيق",
                        ),
                        "options": [
                            {
                                "key": "planned",
                                "label": "Planned",
                                "translations": _tr(
                                    "Geplant",
                                    "Planifié",
                                    "Planificado",
                                    "Pianificato",
                                    "Planejado",
                                    "已规划",
                                    "Запланировано",
                                    "Planlagt",
                                    "مخطط",
                                ),
                            },
                            {
                                "key": "partial",
                                "label": "Partially Implemented",
                                "translations": _tr(
                                    "Teilweise umgesetzt",
                                    "Partiellement mis en œuvre",
                                    "Parcialmente implementado",
                                    "Parzialmente implementato",
                                    "Parcialmente implementado",
                                    "部分实施",
                                    "Частично внедрено",
                                    "Delvist implementeret",
                                    "مطبق جزئياً",
                                ),
                            },
                            {
                                "key": "implemented",
                                "label": "Implemented",
                                "translations": _tr(
                                    "Umgesetzt",
                                    "Mis en œuvre",
                                    "Implementado",
                                    "Implementato",
                                    "Implementado",
                                    "已实施",
                                    "Внедрено",
                                    "Implementeret",
                                    "مطبق",
                                ),
                            },
                            {
                                "key": "verified",
                                "label": "Verified",
                                "translations": _tr(
                                    "Verifiziert",
                                    "Vérifié",
                                    "Verificado",
                                    "Verificato",
                                    "Verificado",
                                    "已验证",
                                    "Проверено",
                                    "Verificeret",
                                    "متحقق منه",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "controlFramework",
                        "label": "Framework Reference",
                        "type": "text",
                        "weight": 1,
                        "translations": _tr(
                            "Framework-Referenz",
                            "Référence du référentiel",
                            "Referencia del marco",
                            "Riferimento del framework",
                            "Referência do framework",
                            "框架引用",
                            "Ссылка на фреймворк",
                            "Rammeværksreference",
                            "مرجع الإطار",
                        ),
                    },
                ],
            },
        ],
    },
    # v4 (GFSA Metamodel §5.3.3): Persona — representative beneficiary segment.
    {
        "key": "Persona",
        "label": "Persona",
        "description": (
            "A representative sample of a beneficiary group or segment sharing "
            "common objectives, needs, experiences and behaviors — the NORA "
            "Beneficiary Experience persona building block."
        ),
        "icon": "person_pin",
        "color": "#00897b",
        "category": "Beneficiary Experience",
        "has_hierarchy": False,
        "subtypes": [],
        "sort_order": 24,
        "translations": {
            "label": _tr(
                "Persona",
                "Persona",
                "Persona",
                "Persona",
                "Persona",
                "用户画像",
                "Персона",
                "Persona",
                "الشخصية النموذجية",
            ),
            "description": _tr(
                "Eine repräsentative Stichprobe einer Begünstigtengruppe mit gemeinsamen Zielen, Bedürfnissen, Erfahrungen und Verhaltensweisen — der Persona-Baustein der NORA-Schicht Nutzererlebnis.",  # noqa: E501
                "Un échantillon représentatif d'un groupe ou segment de bénéficiaires partageant des objectifs, besoins, expériences et comportements communs — le bloc Persona de la couche Expérience bénéficiaire de NORA.",  # noqa: E501
                "Una muestra representativa de un grupo o segmento de beneficiarios que comparten objetivos, necesidades, experiencias y comportamientos comunes — el bloque Persona de la capa Experiencia del beneficiario de NORA.",  # noqa: E501
                "Un campione rappresentativo di un gruppo o segmento di beneficiari che condividono obiettivi, bisogni, esperienze e comportamenti comuni — il blocco Persona del livello Esperienza del beneficiario di NORA.",  # noqa: E501
                "Uma amostra representativa de um grupo ou segmento de beneficiários que compartilham objetivos, necessidades, experiências e comportamentos comuns — o bloco Persona da camada Experiência do beneficiário do NORA.",  # noqa: E501
                "代表具有共同目标、需求、经验和行为的受益人群体或细分的样本——NORA 受益人体验层的用户画像构建块。",  # noqa: E501
                "Репрезентативный образ группы или сегмента получателей услуг с общими целями, потребностями, опытом и поведением — строительный блок «Персона» слоя «Опыт получателя» NORA.",  # noqa: E501
                "En repræsentativ stikprøve af en modtagergruppe eller et segment med fælles mål, behov, erfaringer og adfærd — persona-byggeblokken i NORA-laget for modtageroplevelse.",  # noqa: E501
                "عينة تمثيلية لمجموعة أو شريحة من المستفيدين يتشاركون أهدافاً واحتياجات وتجارب وسلوكيات مشتركة — وحدة بناء الشخصية النموذجية في طبقة تجربة المستفيد في نورا.",  # noqa: E501
            ),
        },
        "stakeholder_roles": [
            {
                "key": "responsible",
                "label": "Responsible",
                "translations": {
                    "label": _tr(
                        "Verantwortlicher",
                        "Responsable",
                        "Responsable",
                        "Responsabile",
                        "Responsável",
                        "负责人",
                        "Ответственный",
                        "Ansvarlig",
                        "المسؤول",
                    ),
                },
            },
            {
                "key": "observer",
                "label": "Observer",
                "translations": {
                    "label": _tr(
                        "Beobachter",
                        "Observateur",
                        "Observador",
                        "Osservatore",
                        "Observador",
                        "观察者",
                        "Наблюдатель",
                        "Observatør",
                        "مراقب",
                    ),
                },
            },
        ],
        "fields_schema": [
            {
                "section": "Persona Profile",
                "translations": _tr(
                    "Persona-Profil",
                    "Profil de la persona",
                    "Perfil de la persona",
                    "Profilo della persona",
                    "Perfil da persona",
                    "画像档案",
                    "Профиль персоны",
                    "Personaprofil",
                    "ملف الشخصية النموذجية",
                ),
                "fields": [
                    {
                        "key": "personaCode",
                        "label": "Code",
                        "type": "text",
                        "weight": 0,
                        "translations": _tr(
                            "Code",
                            "Code",
                            "Código",
                            "Codice",
                            "Código",
                            "编码",
                            "Код",
                            "Kode",
                            "الرمز",
                        ),
                    },
                    {
                        "key": "personaGoals",
                        "label": "Objectives",
                        "type": "text",
                        "weight": 1,
                        "translations": _tr(
                            "Ziele",
                            "Objectifs",
                            "Objetivos",
                            "Obiettivi",
                            "Objetivos",
                            "目标",
                            "Цели",
                            "Mål",
                            "الأهداف",
                        ),
                    },
                    {
                        "key": "demographicInfo",
                        "label": "Demographic Information",
                        "type": "text",
                        "weight": 1,
                        "translations": _tr(
                            "Demografische Informationen",
                            "Informations démographiques",
                            "Información demográfica",
                            "Informazioni demografiche",
                            "Informações demográficas",
                            "人口统计信息",
                            "Демографические сведения",
                            "Demografisk information",
                            "المعلومات الديموغرافية",
                        ),
                    },
                    {
                        "key": "painPoints",
                        "label": "Pain Points",
                        "type": "text",
                        "weight": 0,
                        "translations": _tr(
                            "Schmerzpunkte",
                            "Points de douleur",
                            "Puntos de dolor",
                            "Punti critici",
                            "Pontos de dor",
                            "痛点",
                            "Болевые точки",
                            "Smertepunkter",
                            "نقاط الضعف والتحديات",
                        ),
                    },
                ],
            },
        ],
    },
    # v4 (GFSA Metamodel §5.3.2): Policy — governable rules and regulations.
    {
        "key": "Policy",
        "label": "Policy",
        "description": (
            "Principles, guidelines, rules or regulations established by the "
            "entity to direct decision-making and govern behavior across "
            "business activities, processes and operations."
        ),
        "icon": "gavel",
        "color": "#6d4c41",
        "category": "Business",
        "has_hierarchy": False,
        "subtypes": [],
        "sort_order": 25,
        "translations": {
            "label": _tr(
                "Richtlinie",
                "Politique",
                "Política",
                "Politica",
                "Política",
                "政策",
                "Политика",
                "Politik",
                "السياسة",
            ),
            "description": _tr(
                "Grundsätze, Leitlinien, Regeln oder Vorschriften der Organisation zur Steuerung von Entscheidungen und Verhalten in Geschäftsaktivitäten, Prozessen und Abläufen.",  # noqa: E501
                "Principes, lignes directrices, règles ou réglementations établis par l'organisme pour orienter la prise de décision et gouverner les comportements dans les activités, processus et opérations métier.",  # noqa: E501
                "Principios, directrices, reglas o regulaciones establecidos por la entidad para dirigir la toma de decisiones y gobernar el comportamiento en las actividades, procesos y operaciones de negocio.",  # noqa: E501
                "Principi, linee guida, regole o regolamenti stabiliti dall'ente per orientare le decisioni e governare i comportamenti nelle attività, nei processi e nelle operazioni di business.",  # noqa: E501
                "Princípios, diretrizes, regras ou regulamentos estabelecidos pela entidade para direcionar a tomada de decisões e governar o comportamento nas atividades, processos e operações de negócio.",  # noqa: E501
                "实体为指导决策并规范业务活动、流程和运营行为而制定的原则、准则、规则或法规。",
                "Принципы, руководящие указания, правила или нормативы, установленные организацией для управления решениями и поведением в бизнес-деятельности, процессах и операциях.",  # noqa: E501
                "Principper, retningslinjer, regler eller forskrifter fastlagt af organisationen til at styre beslutningstagning og adfærd i forretningsaktiviteter, processer og drift.",  # noqa: E501
                "مبادئ أو إرشادات أو قواعد أو لوائح تعتمدها الجهة لتوجيه اتخاذ القرار وحوكمة السلوك في مختلف أنشطة الأعمال والإجراءات والعمليات.",  # noqa: E501
            ),
        },
        "stakeholder_roles": [
            {
                "key": "responsible",
                "label": "Responsible",
                "translations": {
                    "label": _tr(
                        "Verantwortlicher",
                        "Responsable",
                        "Responsable",
                        "Responsabile",
                        "Responsável",
                        "负责人",
                        "Ответственный",
                        "Ansvarlig",
                        "المسؤول",
                    ),
                },
            },
            {
                "key": "observer",
                "label": "Observer",
                "translations": {
                    "label": _tr(
                        "Beobachter",
                        "Observateur",
                        "Observador",
                        "Osservatore",
                        "Observador",
                        "观察者",
                        "Наблюдатель",
                        "Observatør",
                        "مراقب",
                    ),
                },
            },
        ],
        "fields_schema": [
            {
                "section": "Policy Information",
                "translations": _tr(
                    "Richtlinieninformationen",
                    "Informations sur la politique",
                    "Información de la política",
                    "Informazioni sulla politica",
                    "Informações da política",
                    "政策信息",
                    "Сведения о политике",
                    "Politikinformation",
                    "معلومات السياسة",
                ),
                "fields": [
                    {
                        "key": "policyCode",
                        "label": "Code",
                        "type": "text",
                        "weight": 0,
                        "translations": _tr(
                            "Code",
                            "Code",
                            "Código",
                            "Codice",
                            "Código",
                            "编码",
                            "Код",
                            "Kode",
                            "الرمز",
                        ),
                    },
                    {
                        "key": "policyType",
                        "label": "Policy Type",
                        "type": "single_select",
                        "weight": 1,
                        "translations": _tr(
                            "Richtlinientyp",
                            "Type de politique",
                            "Tipo de política",
                            "Tipo di politica",
                            "Tipo de política",
                            "政策类型",
                            "Тип политики",
                            "Politiktype",
                            "نوع السياسة",
                        ),
                        "options": [
                            {
                                "key": "internal",
                                "label": "Internal",
                                "translations": _tr(
                                    "Intern",
                                    "Interne",
                                    "Interna",
                                    "Interna",
                                    "Interna",
                                    "内部",
                                    "Внутренняя",
                                    "Intern",
                                    "داخلية",
                                ),
                            },
                            {
                                "key": "external",
                                "label": "External (Governmental)",
                                "translations": _tr(
                                    "Extern (behördlich)",
                                    "Externe (gouvernementale)",
                                    "Externa (gubernamental)",
                                    "Esterna (governativa)",
                                    "Externa (governamental)",
                                    "外部(政府)",
                                    "Внешняя (государственная)",
                                    "Ekstern (statslig)",
                                    "خارجية (حكومية)",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "policyStatus",
                        "label": "Status",
                        "type": "single_select",
                        "weight": 1,
                        "translations": _tr(
                            "Status",
                            "Statut",
                            "Estado",
                            "Stato",
                            "Status",
                            "状态",
                            "Статус",
                            "Status",
                            "الحالة",
                        ),
                        "options": [
                            {
                                "key": "active",
                                "label": "Activated",
                                "color": "#2e7d32",
                                "translations": _tr(
                                    "Aktiviert",
                                    "Activée",
                                    "Activada",
                                    "Attivata",
                                    "Ativada",
                                    "已生效",
                                    "Действует",
                                    "Aktiveret",
                                    "مفعّلة",
                                ),
                            },
                            {
                                "key": "suspended",
                                "label": "Suspended",
                                "color": "#f9a825",
                                "translations": _tr(
                                    "Ausgesetzt",
                                    "Suspendue",
                                    "Suspendida",
                                    "Sospesa",
                                    "Suspensa",
                                    "已暂停",
                                    "Приостановлена",
                                    "Suspenderet",
                                    "معلّقة",
                                ),
                            },
                            {
                                "key": "cancelled",
                                "label": "Cancelled",
                                "color": "#c62828",
                                "translations": _tr(
                                    "Aufgehoben",
                                    "Annulée",
                                    "Cancelada",
                                    "Annullata",
                                    "Cancelada",
                                    "已废止",
                                    "Отменена",
                                    "Annulleret",
                                    "ملغاة",
                                ),
                            },
                        ],
                    },
                    {
                        "key": "activationDate",
                        "label": "Effective Date",
                        "type": "date",
                        "weight": 0,
                        "translations": _tr(
                            "Inkrafttreten",
                            "Date d'entrée en vigueur",
                            "Fecha de entrada en vigor",
                            "Data di entrata in vigore",
                            "Data de vigência",
                            "生效日期",
                            "Дата вступления в силу",
                            "Ikrafttrædelsesdato",
                            "تاريخ سريان السياسة",
                        ),
                    },
                    {
                        "key": "policyLink",
                        "label": "Policy Link",
                        "type": "url",
                        "weight": 0,
                        "translations": _tr(
                            "Richtlinien-Link",
                            "Lien vers la politique",
                            "Enlace de la política",
                            "Link della politica",
                            "Link da política",
                            "政策链接",
                            "Ссылка на политику",
                            "Politiklink",
                            "رابط ملف السياسة",
                        ),
                    },
                ],
            },
        ],
    },
    # ── Pillar (profile v6 — the Strategic-Alignment building block as a
    # first-class card type per user decision; supersedes the v4 Objective
    # `pillar` subtype, which stays for backwards compatibility) ────────────
    {
        "key": "Pillar",
        "label": "Strategic Pillar",
        "description": (
            "A top-level strategic pillar of the agency strategy. Strategic "
            "objectives support pillars; programs, initiatives and projects "
            "deliver the objectives — the Strategic-Alignment pillar "
            "building block."
        ),
        "icon": "foundation",
        "color": "#7b1fa2",
        "category": "Business",
        "has_hierarchy": False,
        "subtypes": [],
        "sort_order": 26,
        "translations": {
            "label": _tr(
                "Strategische Säule",
                "Pilier stratégique",
                "Pilar estratégico",
                "Pilastro strategico",
                "Pilar estratégico",
                "战略支柱",
                "Стратегическая опора",
                "Strategisk søjle",
                "الركيزة الاستراتيجية",
            ),
            "description": _tr(
                "Eine strategische Säule der Behördenstrategie auf oberster Ebene. Strategische Ziele stützen Säulen; Programme, Initiativen und Projekte liefern die Ziele — der Säulen-Baustein der strategischen Ausrichtung.",  # noqa: E501
                "Un pilier stratégique de premier niveau de la stratégie de l'entité. Les objectifs stratégiques soutiennent les piliers ; les programmes, initiatives et projets réalisent les objectifs — le bloc Pilier de l'alignement stratégique.",  # noqa: E501
                "Un pilar estratégico de primer nivel de la estrategia de la entidad. Los objetivos estratégicos apoyan los pilares; los programas, iniciativas y proyectos entregan los objetivos — el bloque Pilar de la alineación estratégica.",  # noqa: E501
                "Un pilastro strategico di primo livello della strategia dell'ente. Gli obiettivi strategici sostengono i pilastri; programmi, iniziative e progetti realizzano gli obiettivi — il blocco Pilastro dell'allineamento strategico.",  # noqa: E501
                "Um pilar estratégico de primeiro nível da estratégia da entidade. Os objetivos estratégicos apoiam os pilares; programas, iniciativas e projetos entregam os objetivos — o bloco Pilar do alinhamento estratégico.",  # noqa: E501
                "机构战略的顶层战略支柱。战略目标支撑支柱；计划、举措和项目交付目标——战略对齐的支柱构建块。",  # noqa: E501
                "Стратегическая опора верхнего уровня стратегии ведомства. Стратегические цели поддерживают опоры; программы, инициативы и проекты реализуют цели — строительный блок «Опора» стратегического согласования.",  # noqa: E501
                "En strategisk søjle på øverste niveau i myndighedens strategi. Strategiske mål understøtter søjler; programmer, initiativer og projekter leverer målene — søjle-byggeblokken i den strategiske tilpasning.",  # noqa: E501
                "ركيزة استراتيجية عليا في استراتيجية الجهة. تدعم الأهداف الاستراتيجية الركائز، وتنفذ البرامج والمبادرات والمشاريع الأهداف — وحدة بناء الركيزة في التوافق الاستراتيجي.",  # noqa: E501
            ),
        },
        "stakeholder_roles": [
            {
                "key": "responsible",
                "label": "Responsible",
                "translations": {
                    "label": _tr(
                        "Verantwortlicher",
                        "Responsable",
                        "Responsable",
                        "Responsabile",
                        "Responsável",
                        "负责人",
                        "Ответственный",
                        "Ansvarlig",
                        "المسؤول",
                    ),
                },
            },
            {
                "key": "observer",
                "label": "Observer",
                "translations": {
                    "label": _tr(
                        "Beobachter",
                        "Observateur",
                        "Observador",
                        "Osservatore",
                        "Observador",
                        "观察者",
                        "Наблюдатель",
                        "Observatør",
                        "مراقب",
                    ),
                },
            },
        ],
        "fields_schema": [
            {
                "section": "Pillar Details",
                "translations": _tr(
                    "Säulendetails",
                    "Détails du pilier",
                    "Detalles del pilar",
                    "Dettagli del pilastro",
                    "Detalhes do pilar",
                    "支柱详情",
                    "Сведения об опоре",
                    "Søjledetaljer",
                    "تفاصيل الركيزة",
                ),
                "fields": [
                    {
                        "key": "pillarCode",
                        "label": "Code",
                        "type": "text",
                        "weight": 0,
                        "translations": _tr(
                            "Code",
                            "Code",
                            "Código",
                            "Codice",
                            "Código",
                            "编码",
                            "Код",
                            "Kode",
                            "الرمز",
                        ),
                    },
                    {
                        "key": "pillarOrder",
                        "label": "Display Order",
                        "type": "number",
                        "weight": 0,
                        "translations": _tr(
                            "Anzeigereihenfolge",
                            "Ordre d'affichage",
                            "Orden de visualización",
                            "Ordine di visualizzazione",
                            "Ordem de exibição",
                            "显示顺序",
                            "Порядок отображения",
                            "Visningsrækkefølge",
                            "ترتيب العرض",
                        ),
                    },
                ],
            },
        ],
    },
]

# Relation attribute injected on every Initiative relation type so transition
# projects declare what they do to each linked card (noraPlan.md WP2.4).
TRANSITION_ROLE_ATTRIBUTE: dict = {
    "key": "transitionRole",
    "label": "Transition Role",
    "type": "single_select",
    "translations": _tr(
        "Transitionsrolle",
        "Rôle de transition",
        "Rol de transición",
        "Ruolo di transizione",
        "Papel na transição",
        "转型角色",
        "Роль в переходе",
        "Transitionsrolle",
        "الدور في خطة التحول",
    ),
    "options": [
        {
            "key": "introduces",
            "label": "Introduces",
            "color": "#2e7d32",
            "translations": _tr(
                "führt ein",
                "introduit",
                "introduce",
                "introduce",
                "introduz",
                "引入",
                "вводит",
                "introducerer",
                "يستحدث",
            ),
        },
        {
            "key": "modifies",
            "label": "Modifies",
            "color": "#f9a825",
            "translations": _tr(
                "ändert",
                "modifie",
                "modifica",
                "modifica",
                "modifica",
                "变更",
                "изменяет",
                "ændrer",
                "يعدّل",
            ),
        },
        {
            "key": "retires",
            "label": "Retires",
            "color": "#c62828",
            "translations": _tr(
                "löst ab",
                "retire",
                "retira",
                "dismette",
                "desativa",
                "退役",
                "выводит из эксплуатации",
                "udfaser",
                "يسحب من الخدمة",
            ),
        },
    ],
}

# WP6.4 — the security-protection semantics on the existing Application →
# ITComponent "uses" relation. A second relation type on the pair is forbidden
# by the one-per-pair rule, so protection is a `usageRole` attribute instead.
USAGE_ROLE_ATTRIBUTE: dict = {
    "key": "usageRole",
    "label": "Usage Role",
    "type": "single_select",
    "translations": _tr(
        "Nutzungsrolle",
        "Rôle d'utilisation",
        "Rol de uso",
        "Ruolo d'uso",
        "Papel de uso",
        "使用角色",
        "Роль использования",
        "Anvendelsesrolle",
        "دور الاستخدام",
    ),
    "options": [
        {
            "key": "uses",
            "label": "Uses",
            "color": "#546e7a",
            "translations": _tr(
                "nutzt",
                "utilise",
                "usa",
                "usa",
                "usa",
                "使用",
                "использует",
                "bruger",
                "يستخدم",
            ),
        },
        {
            "key": "protects",
            "label": "Is protected by",
            "color": "#c62828",
            "translations": _tr(
                "wird geschützt durch",
                "est protégé par",
                "está protegido por",
                "è protetto da",
                "é protegido por",
                "受保护于",
                "защищается",
                "beskyttes af",
                "تحميه",
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Saudi compliance regulation pack (noraPlan.md WP4.4). Each ``description``
# is the assessment-scope text the compliance scanner composes into its
# dynamic prompt — the rules reference the NORA profile fields so the scan can
# key on NDMO classification, GSB flags, BRM linkage and standards status.
# ---------------------------------------------------------------------------

# Pre-v5 NCA ECC scanner scope — kept verbatim so the v5 upgrade pass can
# recognise (and only then rewrite) an untouched default description (WP6.4).
_NCA_ECC_DESCRIPTION_V4 = (
    "Assess alignment with the Saudi National Cybersecurity Authority's "
    "Essential Cybersecurity Controls. Flag applications and IT components "
    "without a defined hosting model or security zone, internet-facing "
    "systems lacking hardening evidence in their descriptions, IT "
    "components on declining or retired technology standards, and "
    "landscape gaps such as missing cybersecurity ownership roles or "
    "absent incident-response capability."
)

SAUDI_REGULATION_PACK: list[dict] = [
    {
        "key": "nca_ecc",
        "label": "NCA Essential Cybersecurity Controls (ECC)",
        "description": (
            _NCA_ECC_DESCRIPTION_V4 + " Also flag in-scope applications with no linked security "
            "component (security hardware, software or service subtype on "
            "IT Component) protecting or serving them."
        ),
        "sort_order": 110,
    },
    {
        "key": "ndmo_dm",
        "label": "NDMO Data Management & Personal Data Protection Standards",
        "description": (
            "Assess alignment with the Saudi National Data Management Office "
            "standards. Flag Data Objects without an NDMO data classification "
            "(topSecret / secret / restricted / public), classified data objects "
            "with no owning Organization relation, secret-or-above data carried "
            "by exchanges not routed through the Government Service Bus "
            "(viaGsb = false), and missing data-steward assignments."
        ),
        "sort_order": 120,
    },
    {
        "key": "pdpl",
        "label": "PDPL (Saudi Personal Data Protection Law)",
        "description": (
            "Assess PDPL compliance. Flag Data Objects marked as containing "
            "personal data (piiFlag) that lack a documented lawful basis or "
            "retention period, applications processing personal data without a "
            "responsible owner, and cross-border or external-party exchanges of "
            "personal data without documented safeguards."
        ),
        "sort_order": 130,
    },
    {
        "key": "dga_policy",
        "label": "DGA Digital Government Policy Checks",
        "description": (
            "Assess alignment with Digital Government Authority expectations. "
            "Flag government services without a digital delivery channel, "
            "applications lacking a BRM business-function linkage or ARM "
            "category, services without a service owner, and shared-service "
            "candidates (duplicated capability coverage) not marked as national "
            "shared services."
        ),
        "sort_order": 140,
    },
]

# The Service Owner can do what a Responsible can — reuse that permission set.
# Domain Owner / Data Steward (WP2.3 remainder, profile v5) likewise.
_NORA_SRD_PERMISSION_FALLBACK = {
    "service_owner": DEFAULT_CARD_PERMISSIONS_BY_ROLE.get("responsible", {}),
    "domain_owner": DEFAULT_CARD_PERMISSIONS_BY_ROLE.get("responsible", {}),
    "data_steward": DEFAULT_CARD_PERMISSIONS_BY_ROLE.get("responsible", {}),
}

# WP2.3 remainder (profile v5): data-governance stakeholder roles on existing
# built-in types — a Domain Owner per capability domain and a Data Steward per
# data entity (the NDMO-aligned ownership WP4.1's classification fields imply).
NORA_EXTRA_STAKEHOLDER_ROLES: dict[str, list[dict]] = {
    "BusinessCapability": [
        {
            "key": "domain_owner",
            "label": "Domain Owner",
            "translations": _tr(
                "Domänenverantwortlicher",
                "Propriétaire de domaine",
                "Propietario del dominio",
                "Proprietario del dominio",
                "Proprietário do domínio",
                "领域负责人",
                "Владелец домена",
                "Domæneejer",
                "مالك النطاق",
            ),
        }
    ],
    "DataObject": [
        {
            "key": "data_steward",
            "label": "Data Steward",
            "translations": _tr(
                "Datenverantwortlicher",
                "Intendant des données",
                "Responsable de datos",
                "Steward dei dati",
                "Curador de dados",
                "数据管家",
                "Куратор данных",
                "Dataforvalter",
                "مسؤول البيانات",
            ),
        }
    ],
}

# One relation type per ordered (source, target) pair — the apply function
# checks pair occupancy before inserting, per the metamodel invariant.
NORA_RELATION_TYPES: list[dict] = [
    {
        "key": "relGovServiceToProcess",
        "label": "is realized by",
        "reverse_label": "realizes",
        "source_type_key": "GovService",
        "target_type_key": "BusinessProcess",
        "cardinality": "n:m",
        "sort_order": 200,
        "translations": {
            "label": _tr(
                "wird realisiert durch",
                "est réalisé par",
                "se realiza mediante",
                "è realizzato da",
                "é realizado por",
                "由…实现",
                "реализуется через",
                "realiseres af",
                "يتحقق بواسطة",
            ),
            "reverse_label": _tr(
                "realisiert",
                "réalise",
                "realiza",
                "realizza",
                "realiza",
                "实现",
                "реализует",
                "realiserer",
                "يُحقِّق",
            ),
        },
    },
    {
        "key": "relGovServiceToApp",
        "label": "is delivered by",
        "reverse_label": "delivers",
        "source_type_key": "GovService",
        "target_type_key": "Application",
        "cardinality": "n:m",
        "sort_order": 201,
        "translations": {
            "label": _tr(
                "wird bereitgestellt durch",
                "est fourni par",
                "es prestado por",
                "è erogato da",
                "é fornecido por",
                "由…交付",
                "предоставляется через",
                "leveres af",
                "تُقدَّم بواسطة",
            ),
            "reverse_label": _tr(
                "stellt bereit",
                "fournit",
                "presta",
                "eroga",
                "fornece",
                "交付",
                "предоставляет",
                "leverer",
                "يُقدِّم",
            ),
        },
    },
    {
        "key": "relOrgToGovService",
        "label": "provides",
        "reverse_label": "is provided by",
        "source_type_key": "Organization",
        "target_type_key": "GovService",
        "cardinality": "n:m",
        "sort_order": 202,
        "translations": {
            "label": _tr(
                "bietet an",
                "fournit",
                "provee",
                "fornisce",
                "provê",
                "提供",
                "предоставляет",
                "udbyder",
                "توفِّر",
            ),
            "reverse_label": _tr(
                "wird angeboten von",
                "est fourni par",
                "es provisto por",
                "è fornito da",
                "é provido por",
                "由…提供",
                "предоставляется",
                "udbydes af",
                "تُوفَّر بواسطة",
            ),
        },
    },
    {
        "key": "relGovServiceToBC",
        "label": "supports",
        "reverse_label": "is supported by",
        "source_type_key": "GovService",
        "target_type_key": "BusinessCapability",
        "cardinality": "n:m",
        "sort_order": 203,
        "translations": {
            "label": _tr(
                "unterstützt",
                "soutient",
                "apoya",
                "supporta",
                "apoia",
                "支持",
                "поддерживает",
                "understøtter",
                "تدعم",
            ),
            "reverse_label": _tr(
                "wird unterstützt durch",
                "est soutenu par",
                "es apoyado por",
                "è supportato da",
                "é apoiado por",
                "由…支持",
                "поддерживается",
                "understøttes af",
                "تُدعَم بواسطة",
            ),
        },
    },
    {
        "key": "relGovServiceToDO",
        "label": "uses",
        "reverse_label": "is used by",
        "source_type_key": "GovService",
        "target_type_key": "DataObject",
        "cardinality": "n:m",
        "sort_order": 204,
        "translations": {
            "label": _tr(
                "verwendet",
                "utilise",
                "usa",
                "utilizza",
                "usa",
                "使用",
                "использует",
                "bruger",
                "تستخدم",
            ),
            "reverse_label": _tr(
                "wird verwendet von",
                "est utilisé par",
                "es usado por",
                "è utilizzato da",
                "é usado por",
                "被…使用",
                "используется",
                "bruges af",
                "تُستخدَم بواسطة",
            ),
        },
    },
    {
        "key": "relAppToDataExchange",
        "label": "exchanges via",
        "reverse_label": "connects",
        "source_type_key": "Application",
        "target_type_key": "DataExchange",
        "cardinality": "n:m",
        "sort_order": 205,
        "attributes_schema": [
            {
                "key": "direction",
                "label": "Direction",
                "type": "single_select",
                "translations": _tr(
                    "Richtung",
                    "Sens",
                    "Dirección",
                    "Direzione",
                    "Direção",
                    "方向",
                    "Направление",
                    "Retning",
                    "الاتجاه",
                ),
                "options": [
                    {
                        "key": "sends",
                        "label": "Sends",
                        "translations": _tr(
                            "Sendet",
                            "Envoie",
                            "Envía",
                            "Invia",
                            "Envia",
                            "发送",
                            "Отправляет",
                            "Sender",
                            "يرسل",
                        ),
                    },
                    {
                        "key": "receives",
                        "label": "Receives",
                        "translations": _tr(
                            "Empfängt",
                            "Reçoit",
                            "Recibe",
                            "Riceve",
                            "Recebe",
                            "接收",
                            "Получает",
                            "Modtager",
                            "يستقبل",
                        ),
                    },
                    {
                        "key": "bidirectional",
                        "label": "Bidirectional",
                        "translations": _tr(
                            "Bidirektional",
                            "Bidirectionnel",
                            "Bidireccional",
                            "Bidirezionale",
                            "Bidirecional",
                            "双向",
                            "Двунаправленный",
                            "Tovejs",
                            "ثنائي الاتجاه",
                        ),
                    },
                ],
            },
        ],
        "translations": {
            "label": _tr(
                "tauscht aus über",
                "échange via",
                "intercambia mediante",
                "scambia tramite",
                "troca via",
                "通过…交换",
                "обменивается через",
                "udveksler via",
                "يتبادل عبر",
            ),
            "reverse_label": _tr(
                "verbindet",
                "connecte",
                "conecta",
                "collega",
                "conecta",
                "连接",
                "связывает",
                "forbinder",
                "يربط",
            ),
        },
    },
    {
        "key": "relDataExchangeToDO",
        "label": "carries",
        "reverse_label": "is carried by",
        "source_type_key": "DataExchange",
        "target_type_key": "DataObject",
        "cardinality": "n:m",
        "sort_order": 206,
        "translations": {
            "label": _tr(
                "transportiert",
                "transporte",
                "transporta",
                "trasporta",
                "transporta",
                "承载",
                "переносит",
                "transporterer",
                "ينقل",
            ),
            "reverse_label": _tr(
                "wird transportiert von",
                "est transporté par",
                "es transportado por",
                "è trasportato da",
                "é transportado por",
                "由…承载",
                "переносится",
                "transporteres af",
                "يُنقل بواسطة",
            ),
        },
    },
    {
        "key": "relDataObjectToITC",
        "label": "is stored in",
        "reverse_label": "stores",
        "source_type_key": "DataObject",
        "target_type_key": "ITComponent",
        "cardinality": "n:m",
        "sort_order": 207,
        "translations": {
            "label": _tr(
                "wird gespeichert in",
                "est stocké dans",
                "se almacena en",
                "è memorizzato in",
                "é armazenado em",
                "存储于",
                "хранится в",
                "lagres i",
                "يُخزَّن في",
            ),
            "reverse_label": _tr(
                "speichert",
                "stocke",
                "almacena",
                "memorizza",
                "armazena",
                "存储",
                "хранит",
                "lagrer",
                "يخزِّن",
            ),
        },
    },
    {
        "key": "relObjectiveToKPI",
        "label": "is measured by",
        "reverse_label": "measures",
        "source_type_key": "Objective",
        "target_type_key": "KPI",
        "cardinality": "n:m",
        "sort_order": 208,
        "translations": {
            "label": _tr(
                "wird gemessen durch",
                "est mesuré par",
                "se mide mediante",
                "è misurato da",
                "é medido por",
                "由…衡量",
                "измеряется",
                "måles af",
                "يُقاس بواسطة",
            ),
            "reverse_label": _tr(
                "misst", "mesure", "mide", "misura", "mede", "衡量", "измеряет", "måler", "يقيس"
            ),
        },
    },
    {
        "key": "relKPIToGovService",
        "label": "measures",
        "reverse_label": "is measured by",
        "source_type_key": "KPI",
        "target_type_key": "GovService",
        "cardinality": "n:m",
        "sort_order": 209,
        "translations": {
            "label": _tr(
                "misst", "mesure", "mide", "misura", "mede", "衡量", "измеряет", "måler", "يقيس"
            ),
            "reverse_label": _tr(
                "wird gemessen durch",
                "est mesuré par",
                "se mide mediante",
                "è misurato da",
                "é medido por",
                "由…衡量",
                "измеряется",
                "måles af",
                "يُقاس بواسطة",
            ),
        },
    },
    {
        "key": "relInitiativeToKPI",
        "label": "improves",
        "reverse_label": "is improved by",
        "source_type_key": "Initiative",
        "target_type_key": "KPI",
        "cardinality": "n:m",
        "sort_order": 210,
        "translations": {
            "label": _tr(
                "verbessert",
                "améliore",
                "mejora",
                "migliora",
                "melhora",
                "改进",
                "улучшает",
                "forbedrer",
                "يُحسِّن",
            ),
            "reverse_label": _tr(
                "wird verbessert durch",
                "est amélioré par",
                "es mejorado por",
                "è migliorato da",
                "é melhorado por",
                "被改进",
                "улучшается",
                "forbedres af",
                "يُحسَّن بواسطة",
            ),
        },
    },
    # ── v4 (GFSA Metamodel): Persona / Journey / Policy connections ────────
    {
        "key": "relPersonaToGovService",
        "label": "uses",
        "reverse_label": "is used by",
        "source_type_key": "Persona",
        "target_type_key": "GovService",
        "cardinality": "n:m",
        "sort_order": 211,
        "translations": {
            "label": _tr(
                "nutzt",
                "utilise",
                "usa",
                "usa",
                "usa",
                "使用",
                "использует",
                "bruger",
                "يستخدم",
            ),
            "reverse_label": _tr(
                "wird genutzt von",
                "est utilisé par",
                "es usado por",
                "è usato da",
                "é usado por",
                "被使用",
                "используется",
                "bruges af",
                "يُستخدم بواسطة",
            ),
        },
    },
    {
        "key": "relPersonaToJourney",
        "label": "experiences",
        "reverse_label": "is experienced by",
        "source_type_key": "Persona",
        "target_type_key": "BeneficiaryJourney",
        "cardinality": "n:m",
        "sort_order": 212,
        "translations": {
            "label": _tr(
                "durchläuft",
                "vit",
                "experimenta",
                "vive",
                "vivencia",
                "经历",
                "проходит",
                "oplever",
                "يخوض",
            ),
            "reverse_label": _tr(
                "wird durchlaufen von",
                "est vécu par",
                "es experimentado por",
                "è vissuto da",
                "é vivenciado por",
                "被经历",
                "проходится",
                "opleves af",
                "يُخاض بواسطة",
            ),
        },
    },
    {
        "key": "relJourneyToGovService",
        "label": "covers",
        "reverse_label": "is covered by",
        "source_type_key": "BeneficiaryJourney",
        "target_type_key": "GovService",
        "cardinality": "n:m",
        "sort_order": 213,
        "translations": {
            "label": _tr(
                "deckt ab",
                "couvre",
                "cubre",
                "copre",
                "cobre",
                "覆盖",
                "охватывает",
                "dækker",
                "تغطي",
            ),
            "reverse_label": _tr(
                "wird abgedeckt von",
                "est couvert par",
                "es cubierto por",
                "è coperto da",
                "é coberto por",
                "被覆盖",
                "охватывается",
                "dækkes af",
                "تُغطى بواسطة",
            ),
        },
    },
    {
        "key": "relJourneyToChannel",
        "label": "uses channel",
        "reverse_label": "is used by journey",
        "source_type_key": "BeneficiaryJourney",
        "target_type_key": "Channel",
        "cardinality": "n:m",
        "sort_order": 214,
        "translations": {
            "label": _tr(
                "nutzt Kanal",
                "utilise le canal",
                "usa el canal",
                "usa il canale",
                "usa o canal",
                "使用渠道",
                "использует канал",
                "bruger kanal",
                "تستخدم القناة",
            ),
            "reverse_label": _tr(
                "wird genutzt von Reise",
                "est utilisé par le parcours",
                "es usado por el recorrido",
                "è usato dal percorso",
                "é usado pela jornada",
                "被旅程使用",
                "используется путём",
                "bruges af rejse",
                "تُستخدم بواسطة الرحلة",
            ),
        },
    },
    {
        "key": "relPolicyToBC",
        "label": "governs",
        "reverse_label": "is governed by",
        "source_type_key": "Policy",
        "target_type_key": "BusinessCapability",
        "cardinality": "n:m",
        "sort_order": 215,
        "translations": {
            "label": _tr(
                "regelt",
                "régit",
                "rige",
                "governa",
                "rege",
                "治理",
                "регулирует",
                "styrer",
                "تحكم",
            ),
            "reverse_label": _tr(
                "wird geregelt durch",
                "est régi par",
                "se rige por",
                "è governato da",
                "é regido por",
                "受治理",
                "регулируется",
                "styres af",
                "تُحكم بواسطة",
            ),
        },
    },
    {
        "key": "relPolicyToGovService",
        "label": "governs",
        "reverse_label": "is governed by",
        "source_type_key": "Policy",
        "target_type_key": "GovService",
        "cardinality": "n:m",
        "sort_order": 216,
        "translations": {
            "label": _tr(
                "regelt",
                "régit",
                "rige",
                "governa",
                "rege",
                "治理",
                "регулирует",
                "styrer",
                "تحكم",
            ),
            "reverse_label": _tr(
                "wird geregelt durch",
                "est régi par",
                "se rige por",
                "è governato da",
                "é regido por",
                "受治理",
                "регулируется",
                "styres af",
                "تُحكم بواسطة",
            ),
        },
    },
    {
        "key": "relPolicyToProcess",
        "label": "governs",
        "reverse_label": "is governed by",
        "source_type_key": "Policy",
        "target_type_key": "BusinessProcess",
        "cardinality": "n:m",
        "sort_order": 217,
        "translations": {
            "label": _tr(
                "regelt",
                "régit",
                "rige",
                "governa",
                "rege",
                "治理",
                "регулирует",
                "styrer",
                "تحكم",
            ),
            "reverse_label": _tr(
                "wird geregelt durch",
                "est régi par",
                "se rige por",
                "è governato da",
                "é regido por",
                "受治理",
                "регулируется",
                "styres af",
                "تُحكم بواسطة",
            ),
        },
    },
    # ── Strategy cascade (profile v6): objectives support pillars ──────────
    {
        "key": "relObjectiveToPillar",
        "label": "supports",
        "reverse_label": "is supported by",
        "source_type_key": "Objective",
        "target_type_key": "Pillar",
        "cardinality": "n:m",
        "sort_order": 230,
        "translations": {
            "label": _tr(
                "stützt",
                "soutient",
                "apoya",
                "sostiene",
                "apoia",
                "支撑",
                "поддерживает",
                "understøtter",
                "يدعم",
            ),
            "reverse_label": _tr(
                "wird gestützt von",
                "est soutenu par",
                "es apoyado por",
                "è sostenuto da",
                "é apoiado por",
                "由…支撑",
                "поддерживается",
                "understøttes af",
                "يُدعم بواسطة",
            ),
        },
    },
]


# ---------------------------------------------------------------------------
# NORA governance role pack (noraPlan.md WP2.3).
#
# Seeded (never overwritten) when the profile is applied. Committee members
# review and approve; the working team drafts but can never approve its own
# work; the Chief Architect sits between the two (first chain step).
# ---------------------------------------------------------------------------


def _nora_governance_roles() -> list[dict]:
    working_team = {
        k: v for k, v in MEMBER_PERMISSIONS.items() if k not in ("inventory.approval_status",)
    }
    working_team.update(
        {
            "nora.view": True,
            "nora.manage": True,
            "maturity.view": True,
            "maturity.manage": True,
            "reference_models.view": True,
            "reference_models.manage": True,
        }
    )
    chief_architect = {
        **MEMBER_PERMISSIONS,
        "governance.approve_step": True,
        "nora.view": True,
        "nora.manage": True,
        "maturity.view": True,
        "maturity.manage": True,
        "reference_models.view": True,
        "reference_models.manage": True,
    }
    committee = {
        **VIEWER_PERMISSIONS,
        "inventory.approval_status": True,
        "governance.approve_step": True,
        "nora.view": True,
    }
    return [
        {
            "key": "ea_working_team",
            "label": "EA Working Team",
            "description": (
                "NORA EA working team — drafts and maintains architecture "
                "content but cannot approve deliverables."
            ),
            "color": "#0288d1",
            "permissions": working_team,
            "sort_order": 10,
        },
        {
            "key": "chief_architect",
            "label": "Chief Architect",
            "description": (
                "NORA Chief Architect — full authoring rights plus the first "
                "review step of the governance chain."
            ),
            "color": "#6a1b9a",
            "permissions": chief_architect,
            "sort_order": 11,
        },
        {
            "key": "ea_governance_committee",
            "label": "EA Governance Committee",
            "description": (
                "NORA EA Governance Committee — read access across the "
                "landscape plus final approval of stage deliverables."
            ),
            "color": "#c62828",
            "permissions": committee,
            "sort_order": 12,
        },
    ]


async def _get_or_create_settings_row(db: AsyncSession) -> AppSettings:
    result = await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    row = result.scalar_one_or_none()
    if row is None:
        row = AppSettings(id="default", email_settings={})
        db.add(row)
        await db.flush()
    return row


async def get_framework_profile(db: AsyncSession) -> dict:
    """Return the stored framework profile.

    Falls back to whatever ``SEED_PROFILE`` names when no explicit choice has
    been persisted yet — this fork ships with ``SEED_PROFILE=nora`` by default
    so a plain install reports ``nora`` even before the first startup hook
    finishes applying it. ([FORK] noraPlan.md WP1.1)
    """
    result = await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    row = result.scalar_one_or_none()
    general = (row.general_settings if row else None) or {}
    default_profile = (app_config.settings.SEED_PROFILE or "togaf").strip().lower()
    if default_profile not in FRAMEWORK_PROFILES:
        default_profile = "togaf"
    return {
        "profile": general.get("frameworkProfile", default_profile),
        "nora_profile_version": general.get("noraProfileVersion"),
    }


async def apply_nora_profile(db: AsyncSession) -> dict:
    """Idempotently inject the NORA Alignment fields into the built-in card types.

    Only fields whose key does not exist anywhere in the type's ``fields_schema``
    are added (so an admin who moved or customised a NORA field keeps their
    version). Commits the transaction and stamps the profile flag + version into
    the settings row.
    """
    summary: dict = {
        "types_updated": [],
        "fields_added": 0,
        "card_types_created": [],
        "relation_types_created": [],
        "relation_types_skipped": [],
        "roles_created": [],
    }

    # ── Pass 0: governance role pack (WP2.3) ───────────────────────────────
    role_rows = await db.execute(select(Role.key))
    existing_role_keys = {r for (r,) in role_rows.all()}
    for role_def in _nora_governance_roles():
        if role_def["key"] in existing_role_keys:
            continue
        db.add(Role(**role_def, is_system=False, is_default=False))
        summary["roles_created"].append(role_def["key"])

    # ── Pass 1: create NORA-specific card types (GovService, …) ────────────
    for type_def in NORA_CARD_TYPES:
        result = await db.execute(select(CardType).where(CardType.key == type_def["key"]))
        if result.scalar_one_or_none() is not None:
            continue
        db.add(
            CardType(
                key=type_def["key"],
                label=type_def["label"],
                description=type_def.get("description"),
                icon=type_def.get("icon", "category"),
                color=type_def.get("color", "#1976d2"),
                category=type_def.get("category"),
                has_hierarchy=type_def.get("has_hierarchy", False),
                subtypes=deepcopy(type_def.get("subtypes", [])),
                fields_schema=deepcopy(type_def.get("fields_schema", [])),
                stakeholder_roles=deepcopy(type_def.get("stakeholder_roles", [])),
                built_in=True,
                is_hidden=False,
                sort_order=type_def.get("sort_order", 99),
                translations=deepcopy(type_def.get("translations", {})),
            )
        )
        summary["card_types_created"].append(type_def["key"])

    # Flush so new card_types rows satisfy the FK on stakeholder_role_definitions
    # and are visible to the relation-type pass below.
    await db.flush()

    # ── Pass 2: stakeholder role definitions for the new types ─────────────
    for type_def in NORA_CARD_TYPES:
        srd_result = await db.execute(
            select(StakeholderRoleDefinition).where(
                StakeholderRoleDefinition.card_type_key == type_def["key"]
            )
        )
        existing_srd_keys = {s.key for s in srd_result.scalars().all()}
        for idx, sr in enumerate(type_def.get("stakeholder_roles", [])):
            if sr["key"] in existing_srd_keys:
                continue
            permissions = DEFAULT_CARD_PERMISSIONS_BY_ROLE.get(
                sr["key"], _NORA_SRD_PERMISSION_FALLBACK.get(sr["key"], {})
            )
            db.add(
                StakeholderRoleDefinition(
                    card_type_key=type_def["key"],
                    key=sr["key"],
                    label=sr["label"],
                    permissions=permissions,
                    sort_order=idx,
                    translations=deepcopy(sr.get("translations", {})),
                )
            )

    # ── Pass 2b (profile v5): data-governance stakeholder roles on existing
    # built-in types (WP2.3 remainder) — idempotent by (type, key); skipped
    # when the target card type doesn't exist on this install (FK).
    for type_key, role_defs in NORA_EXTRA_STAKEHOLDER_ROLES.items():
        type_exists = (
            await db.execute(select(CardType.key).where(CardType.key == type_key))
        ).scalar_one_or_none()
        if type_exists is None:
            continue
        srd_result = await db.execute(
            select(StakeholderRoleDefinition).where(
                StakeholderRoleDefinition.card_type_key == type_key
            )
        )
        existing_srd_keys = {s.key for s in srd_result.scalars().all()}
        for idx, sr in enumerate(role_defs):
            if sr["key"] in existing_srd_keys:
                continue
            db.add(
                StakeholderRoleDefinition(
                    card_type_key=type_key,
                    key=sr["key"],
                    label=sr["label"],
                    permissions=_NORA_SRD_PERMISSION_FALLBACK.get(sr["key"], {}),
                    sort_order=100 + idx,
                    translations=deepcopy(sr.get("translations", {})),
                )
            )
            summary.setdefault("stakeholder_roles_created", []).append(f"{type_key}.{sr['key']}")

    # ── Pass 3: relation types — respect one-relation-type-per-pair ────────
    rel_result = await db.execute(select(RelationType))
    all_rels = rel_result.scalars().all()
    existing_rel_keys = {r.key for r in all_rels}
    occupied_pairs = {(r.source_type_key, r.target_type_key) for r in all_rels if not r.is_hidden}

    for rel_def in NORA_RELATION_TYPES:
        pair = (rel_def["source_type_key"], rel_def["target_type_key"])
        if rel_def["key"] in existing_rel_keys:
            continue
        if pair in occupied_pairs:
            # An admin already modelled this pair — never create a second
            # relation type for it (inventory/report invariants depend on this).
            summary["relation_types_skipped"].append(rel_def["key"])
            continue
        db.add(
            RelationType(
                key=rel_def["key"],
                label=rel_def["label"],
                reverse_label=rel_def.get("reverse_label"),
                source_type_key=rel_def["source_type_key"],
                target_type_key=rel_def["target_type_key"],
                cardinality=rel_def.get("cardinality", "n:m"),
                attributes_schema=[],
                built_in=True,
                is_hidden=False,
                sort_order=rel_def.get("sort_order", 200),
                translations=deepcopy(rel_def.get("translations", {})),
            )
        )
        occupied_pairs.add(pair)
        summary["relation_types_created"].append(rel_def["key"])

    # ── Pass 3b: transitionRole attribute on Initiative relation types ─────
    # Every relation type touching Initiative gets a `transitionRole`
    # single_select attribute so transition projects declare what they do to
    # each linked card (introduces / modifies / retires) — WP2.4. Idempotent:
    # skipped when the key already exists (admin customisations survive).
    rel_result = await db.execute(
        select(RelationType).where(
            (RelationType.source_type_key == "Initiative")
            | (RelationType.target_type_key == "Initiative")
        )
    )
    for rel_type in rel_result.scalars().all():
        attrs = list(rel_type.attributes_schema or [])
        if any(a.get("key") == "transitionRole" for a in attrs):
            continue
        attrs.append(deepcopy(TRANSITION_ROLE_ATTRIBUTE))
        rel_type.attributes_schema = attrs
        summary.setdefault("relation_types_updated", []).append(rel_type.key)

    # ── Pass 3c (profile v5): usageRole attribute on Application → ITComponent
    # (WP6.4) — protection semantics without a second relation type on the
    # pair. Idempotent: skipped when the key already exists.
    app_itc = (
        await db.execute(select(RelationType).where(RelationType.key == "relAppToITC"))
    ).scalar_one_or_none()
    if app_itc is not None:
        attrs = list(app_itc.attributes_schema or [])
        if not any(a.get("key") == "usageRole" for a in attrs):
            attrs.append(deepcopy(USAGE_ROLE_ATTRIBUTE))
            app_itc.attributes_schema = attrs
            summary.setdefault("relation_types_updated", []).append(app_itc.key)

    # ── Pass 4: inject NORA fields into the existing built-in types ────────
    for type_key, fields in NORA_TYPE_FIELDS.items():
        result = await db.execute(select(CardType).where(CardType.key == type_key))
        card_type = result.scalar_one_or_none()
        if card_type is None:
            continue

        schema = [dict(section) for section in (card_type.fields_schema or [])]
        existing_keys = {
            field.get("key") for section in schema for field in (section.get("fields") or [])
        }
        missing = [f for f in fields if f["key"] not in existing_keys]
        if not missing:
            continue

        nora_section = next((s for s in schema if s.get("section") == NORA_SECTION), None)
        if nora_section is None:
            nora_section = {
                "section": NORA_SECTION,
                "translations": deepcopy(NORA_SECTION_TRANSLATIONS),
                "fields": [],
            }
            schema.append(nora_section)
        else:
            nora_section["fields"] = list(nora_section.get("fields") or [])

        nora_section["fields"].extend(deepcopy(missing))
        card_type.fields_schema = schema
        summary["types_updated"].append(type_key)
        summary["fields_added"] += len(missing)

    # ── Pass 4f (profile v4): sectioned field injection — fields that live in
    # their own named section rather than "NORA Alignment" (ITComponent
    # Technical Specification, BeneficiaryJourney Journey Mapping). Same
    # idempotency rule as pass 4: a field key that exists anywhere in the
    # type's schema is never duplicated or overwritten.
    for type_key, section_defs in NORA_SECTIONED_FIELDS.items():
        result = await db.execute(select(CardType).where(CardType.key == type_key))
        card_type = result.scalar_one_or_none()
        if card_type is None:
            continue
        schema = [dict(section) for section in (card_type.fields_schema or [])]
        existing_keys = {
            field.get("key") for section in schema for field in (section.get("fields") or [])
        }
        changed = False
        for section_def in section_defs:
            missing = [f for f in section_def["fields"] if f["key"] not in existing_keys]
            if not missing:
                continue
            target = next((s for s in schema if s.get("section") == section_def["section"]), None)
            if target is None:
                target = {
                    "section": section_def["section"],
                    "translations": deepcopy(section_def.get("translations", {})),
                    "fields": [],
                }
                schema.append(target)
            else:
                target["fields"] = list(target.get("fields") or [])
            target["fields"].extend(deepcopy(missing))
            summary["fields_added"] += len(missing)
            changed = True
        if changed:
            card_type.fields_schema = schema
            if type_key not in summary["types_updated"]:
                summary["types_updated"].append(type_key)

    # ── Pass 4b: Database subtype on ITComponent (WP4.1 — DRM database
    # portfolio). Idempotent; admin-added subtypes survive.
    itc = (
        await db.execute(select(CardType).where(CardType.key == "ITComponent"))
    ).scalar_one_or_none()
    if itc is not None:
        subtypes = list(itc.subtypes or [])
        if not any(s.get("key") == "database" for s in subtypes):
            subtypes.append(
                {
                    "key": "database",
                    "label": "Database",
                    "translations": _tr(
                        "Datenbank",
                        "Base de données",
                        "Base de datos",
                        "Database",
                        "Banco de dados",
                        "数据库",
                        "База данных",
                        "Database",
                        "قاعدة بيانات",
                    ),
                }
            )
            itc.subtypes = subtypes
            summary["subtypes_added"] = ["ITComponent.database"]

    # ── Pass 4d (profile v2, WP6.2): additional subtypes + GovService
    # hierarchy. Subtype appends are idempotent by key; enabling hierarchy on
    # GovService is additive (sub-services link to their main service via
    # parent_id — the template's "الخدمة الأساسية" column).
    for type_key, subtype_defs in NORA_V2_SUBTYPES.items():
        ct = (
            await db.execute(select(CardType).where(CardType.key == type_key))
        ).scalar_one_or_none()
        if ct is None:
            continue
        subtypes = list(ct.subtypes or [])
        existing_sub_keys = {s.get("key") for s in subtypes}
        added = False
        for sub in subtype_defs:
            if sub["key"] in existing_sub_keys:
                continue
            subtypes.append(deepcopy(sub))
            summary.setdefault("subtypes_added", []).append(f"{type_key}.{sub['key']}")
            added = True
        if added:
            ct.subtypes = subtypes

    # ── Pass 4g (profile v7, WP100.2): Arabic-label fix on the existing
    # `orgUnitType.publicAdministration` option — «إدارة عامة» now names the
    # generalDepartment subtype, so the option is renamed to
    # «جهة إدارية عامة». Guarded: only rewritten while the stored label still
    # equals the drifted-from value, so admin customisations survive.
    org_ct = (
        await db.execute(select(CardType).where(CardType.key == "Organization"))
    ).scalar_one_or_none()
    if org_ct is not None:
        schema = [dict(section) for section in (org_ct.fields_schema or [])]
        changed = False
        for section in schema:
            for field in section.get("fields") or []:
                if field.get("key") != "orgUnitType":
                    continue
                for opt in field.get("options") or []:
                    if (
                        opt.get("key") == "publicAdministration"
                        and (opt.get("translations") or {}).get("ar") == "إدارة عامة"
                    ):
                        opt["translations"]["ar"] = "جهة إدارية عامة"
                        changed = True
        if changed:
            org_ct.fields_schema = schema
            summary.setdefault("options_relabelled", []).append(
                "Organization.orgUnitType.publicAdministration.ar"
            )

    gov = (
        await db.execute(select(CardType).where(CardType.key == "GovService"))
    ).scalar_one_or_none()
    # Only upgrade the profile-created (built-in) type — an admin-created type
    # that happens to be keyed GovService is never touched (WP1.2 guarantee).
    if gov is not None and gov.built_in and not gov.has_hierarchy:
        gov.has_hierarchy = True
        summary["gov_service_hierarchy_enabled"] = True

    # Profile v5: enable hierarchy on Objective so pillar-subtype objectives
    # can parent their strategic objectives — the Strategic House viewpoint
    # (WP6.7) reads that tree. Guarded to the built-in type, like GovService.
    obj = (
        await db.execute(select(CardType).where(CardType.key == "Objective"))
    ).scalar_one_or_none()
    if obj is not None and obj.built_in and not obj.has_hierarchy:
        obj.has_hierarchy = True
        summary["objective_hierarchy_enabled"] = True

    # ── Pass 4c: Saudi compliance regulation pack (WP4.4). Idempotent by
    # key; follows the built-in regulation precedent (label + scanner-scope
    # description, no translations — labels are proper names).
    from app.models.compliance_regulation import ComplianceRegulation

    reg_rows = await db.execute(select(ComplianceRegulation.key))
    existing_regs = {k for (k,) in reg_rows.all()}
    for reg in SAUDI_REGULATION_PACK:
        if reg["key"] in existing_regs:
            continue
        db.add(ComplianceRegulation(**reg, built_in=False, is_enabled=True))
        summary.setdefault("regulations_created", []).append(reg["key"])

    # Profile v5 (WP6.4): extend the NCA ECC scanner scope with the
    # missing-security-component rule. Guarded — only rewrites while the
    # stored description still equals the pre-v5 default, so an admin who
    # edited the regulation text keeps their wording.
    nca = (
        await db.execute(select(ComplianceRegulation).where(ComplianceRegulation.key == "nca_ecc"))
    ).scalar_one_or_none()
    if nca is not None and nca.description == _NCA_ECC_DESCRIPTION_V4:
        nca.description = SAUDI_REGULATION_PACK[0]["description"]
        summary.setdefault("regulations_updated", []).append("nca_ecc")

    # ── Pass 4e (profile v3): six-layer category moves. Guarded per type —
    # only rewrites while the category still equals the old default, so an
    # admin who re-categorised a type keeps their choice. Belt-and-braces
    # with Alembic migration 137 (idempotent in either order).
    for type_key, (old_cat, new_cat) in SIX_LAYER_CATEGORY_MOVES.items():
        ct = (
            await db.execute(select(CardType).where(CardType.key == type_key))
        ).scalar_one_or_none()
        if ct is not None and ct.category == old_cat:
            ct.category = new_cat
            summary.setdefault("categories_moved", []).append(f"{type_key} → {new_cat}")

    # ── Pass 5: seed the EA Program deliverable catalogue (WP3.1 + WP6.1) ──
    # Methodology resolution: an explicit stored version wins; otherwise an
    # install that already carries deliverable rows is a pre-WP6.1 v1
    # program (never silently rewritten), and a fresh install starts on the
    # updated 7-phase methodology (v2).
    from app.models.nora_program import EaProgramDeliverable
    from app.services.nora_program import (
        NORA_METHODOLOGY_VERSIONS,
        seed_nora_program,
    )

    settings_row = await _get_or_create_settings_row(db)
    general_pre = dict(settings_row.general_settings or {})
    methodology = general_pre.get("noraMethodologyVersion")
    if methodology not in NORA_METHODOLOGY_VERSIONS:
        has_rows = (
            await db.execute(select(EaProgramDeliverable.id).limit(1))
        ).scalar_one_or_none() is not None
        methodology = "v1" if has_rows else "v2"
    summary["methodology"] = methodology
    summary["program_deliverables_created"] = await seed_nora_program(db, methodology=methodology)

    # WP6.8 — the pre-methodology practice-establishment checklist (the
    # Practice Guideline's ten operating-model artifacts), idempotent by key.
    from app.services.nora_program import seed_practice_checklist

    summary["practice_checklist_created"] = await seed_practice_checklist(db)

    # ── Pass 6: seed the EA maturity dimension catalogue (WP5.2) ───────────
    from app.services.maturity import seed_maturity_dimensions

    summary["maturity_dimensions_created"] = await seed_maturity_dimensions(db)

    # ── Pass 7: seed the kit-preview reference-model starters (WP100.3) ────
    from app.services.reference_models import seed_reference_model_starters

    summary["reference_models_created"] = await seed_reference_model_starters(db)

    row = await _get_or_create_settings_row(db)
    general = dict(row.general_settings or {})
    general["frameworkProfile"] = "nora"
    general["noraProfileVersion"] = NORA_PROFILE_VERSION
    general["noraMethodologyVersion"] = methodology
    row.general_settings = general

    await db.commit()
    return summary


async def set_togaf_profile(db: AsyncSession) -> None:
    """Switch the stored profile back to ``togaf``.

    Intentionally preserves the NORA fields and any data captured in them —
    removing metamodel fields is an explicit admin action, never a side effect.
    """
    row = await _get_or_create_settings_row(db)
    general = dict(row.general_settings or {})
    general["frameworkProfile"] = "togaf"
    row.general_settings = general
    await db.commit()


async def ensure_framework_profile(db: AsyncSession) -> None:
    """Startup hook — apply/upgrade the NORA profile when appropriate.

    * Fresh install (no stored profile) + ``SEED_PROFILE=nora`` → apply.
    * Existing ``togaf`` install + ``SEED_PROFILE=nora`` → apply (this fork
      defaults to nora, so a plain-TOGAF fork install gets promoted to NORA
      on next boot unless the operator explicitly set ``SEED_PROFILE=togaf``).
    * Stored ``nora`` profile at an older ``noraProfileVersion`` → re-apply
      (idempotent upgrade that only adds newly introduced fields).
    """
    result = await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    row = result.scalar_one_or_none()
    general = (row.general_settings if row else None) or {}
    profile = general.get("frameworkProfile")

    seed_profile = (app_config.settings.SEED_PROFILE or "").strip().lower()
    if profile in (None, "togaf") and seed_profile == "nora":
        summary = await apply_nora_profile(db)
        origin = "fresh install" if profile is None else "TOGAF → NORA upgrade"
        print(
            f"[nora_profile] Applied NORA profile ({origin}) — "
            f"{summary['fields_added']} fields across {len(summary['types_updated'])} types"
        )
    elif profile == "nora" and (general.get("noraProfileVersion") or 0) < NORA_PROFILE_VERSION:
        summary = await apply_nora_profile(db)
        print(
            f"[nora_profile] Upgraded NORA profile to v{NORA_PROFILE_VERSION} "
            f"({summary['fields_added']} fields added)"
        )
