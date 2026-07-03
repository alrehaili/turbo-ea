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

NORA_PROFILE_VERSION = 1

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
        "category": "Business Architecture",
        "has_hierarchy": False,
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
        "category": "Application & Data",
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
        "category": "Strategy & Transformation",
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

# ---------------------------------------------------------------------------
# Saudi compliance regulation pack (noraPlan.md WP4.4). Each ``description``
# is the assessment-scope text the compliance scanner composes into its
# dynamic prompt — the rules reference the NORA profile fields so the scan can
# key on NDMO classification, GSB flags, BRM linkage and standards status.
# ---------------------------------------------------------------------------

SAUDI_REGULATION_PACK: list[dict] = [
    {
        "key": "nca_ecc",
        "label": "NCA Essential Cybersecurity Controls (ECC)",
        "description": (
            "Assess alignment with the Saudi National Cybersecurity Authority's "
            "Essential Cybersecurity Controls. Flag applications and IT components "
            "without a defined hosting model or security zone, internet-facing "
            "systems lacking hardening evidence in their descriptions, IT "
            "components on declining or retired technology standards, and "
            "landscape gaps such as missing cybersecurity ownership roles or "
            "absent incident-response capability."
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
_NORA_SRD_PERMISSION_FALLBACK = {
    "service_owner": DEFAULT_CARD_PERMISSIONS_BY_ROLE.get("responsible", {}),
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
    working_team.update({"nora.view": True, "nora.manage": True})
    chief_architect = {
        **MEMBER_PERMISSIONS,
        "governance.approve_step": True,
        "nora.view": True,
        "nora.manage": True,
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

    # ── Pass 5: seed the EA Program deliverable catalogue (WP3.1) ──────────
    from app.services.nora_program import seed_nora_program

    summary["program_deliverables_created"] = await seed_nora_program(db)

    row = await _get_or_create_settings_row(db)
    general = dict(row.general_settings or {})
    general["frameworkProfile"] = "nora"
    general["noraProfileVersion"] = NORA_PROFILE_VERSION
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
