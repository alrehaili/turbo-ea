"""DGA building-block attributes the NORA types were missing ([FORK]).

NORAreadiness.md B-6. Sources: the June 2025 "EA Content Meta Model"
guideline (B1, §5.3.x.2 attribute tables) and DGA's six data-collection
templates (حصر البيانات). Injected by ``apply_nora_profile`` through
``NORA_TYPE_FIELDS`` (pass 4, idempotent by key, zero data-quality weight).

The shared technology fields are literal copies of the seed's own
definitions (support contract status, type of operation, capital / operating
cost, firmware, version, function) so a security device reads the same as a
server; this module cannot import ``seed`` (seed imports the profile).
"""

from __future__ import annotations

from copy import deepcopy


def _tr(de: str, fr: str, es: str, it: str, pt: str, zh: str, ru: str, da: str, ar: str) -> dict:
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


def _text(key: str, label: str, translations: dict, field_type: str = "text") -> dict:
    return {
        "key": key,
        "label": label,
        "type": field_type,
        "weight": 0,
        "translations": translations,
    }


_SEED_FIELDS: dict[str, dict] = {
    "supportContractStatus": {
        "key": "supportContractStatus",
        "label": "Support Contract Status",
        "type": "single_select",
        "weight": 0,
        "translations": {
            "de": "Status des Supportvertrags",
            "fr": "Statut du contrat de support",
            "es": "Estado del contrato de soporte",
            "it": "Stato del contratto di supporto",
            "pt": "Estado do contrato de suporte",
            "zh": "支持合同状态",
            "ru": "Статус договора поддержки",
            "da": "Status for supportkontrakt",
            "ar": "حالة عقد الدعم",
        },
        "options": [
            {
                "key": "active",
                "label": "Active",
                "translations": {
                    "de": "Aktiv",
                    "fr": "Actif",
                    "es": "Activo",
                    "it": "Attivo",
                    "pt": "Ativo",
                    "zh": "有效",
                    "ru": "Активен",
                    "da": "Aktiv",
                    "ar": "نشط",
                },
            },
            {
                "key": "expired",
                "label": "Expired",
                "translations": {
                    "de": "Abgelaufen",
                    "fr": "Expiré",
                    "es": "Expirado",
                    "it": "Scaduto",
                    "pt": "Expirado",
                    "zh": "已过期",
                    "ru": "Истёк",
                    "da": "Udløbet",
                    "ar": "منتهي الصلاحية",
                },
            },
        ],
    },
    "typeOfOperation": {
        "key": "typeOfOperation",
        "label": "Type of Operation",
        "type": "single_select",
        "weight": 0,
        "translations": {
            "de": "Betriebsart",
            "fr": "Type d'exploitation",
            "es": "Tipo de operación",
            "it": "Tipo di operazione",
            "pt": "Tipo de operação",
            "zh": "运营方式",
            "ru": "Тип эксплуатации",
            "da": "Driftstype",
            "ar": "نوع التشغيل",
        },
        "options": [
            {
                "key": "inHouse",
                "label": "In-House Team",
                "translations": {
                    "de": "Internes Team",
                    "fr": "Équipe interne",
                    "es": "Equipo interno",
                    "it": "Team interno",
                    "pt": "Equipa interna",
                    "zh": "内部团队",
                    "ru": "Внутренняя команда",
                    "da": "Internt team",
                    "ar": "فريق داخلي",
                },
            },
            {
                "key": "serviceProvider",
                "label": "Service Provider",
                "translations": {
                    "de": "Dienstleister",
                    "fr": "Prestataire de services",
                    "es": "Proveedor de servicios",
                    "it": "Fornitore di servizi",
                    "pt": "Prestador de serviços",
                    "zh": "服务提供商",
                    "ru": "Поставщик услуг",
                    "da": "Serviceudbyder",
                    "ar": "مزود الخدمة",
                },
            },
            {
                "key": "other",
                "label": "Other",
                "translations": {
                    "de": "Andere",
                    "fr": "Autre",
                    "es": "Otro",
                    "it": "Altro",
                    "pt": "Outro",
                    "zh": "其他",
                    "ru": "Другое",
                    "da": "Andet",
                    "ar": "أخرى",
                },
            },
        ],
    },
    "capitalCost": {
        "key": "capitalCost",
        "label": "Capital Cost",
        "type": "cost",
        "weight": 0,
        "translations": {
            "de": "Kapitalkosten",
            "fr": "Coût d'investissement",
            "es": "Coste de capital",
            "it": "Costo di capitale",
            "pt": "Custo de capital",
            "zh": "资本成本",
            "ru": "Капитальные затраты",
            "da": "Kapitalomkostning",
            "ar": "التكلفة الرأسمالية",
        },
    },
    "operatingCost": {
        "key": "operatingCost",
        "label": "Operating Cost",
        "type": "cost",
        "weight": 0,
        "translations": {
            "de": "Betriebskosten",
            "fr": "Coût d'exploitation",
            "es": "Coste operativo",
            "it": "Costo operativo",
            "pt": "Custo operacional",
            "zh": "运营成本",
            "ru": "Эксплуатационные расходы",
            "da": "Driftsomkostning",
            "ar": "التكلفة التشغيلية",
        },
    },
    "firmwareVersion": {
        "key": "firmwareVersion",
        "label": "Firmware Version",
        "type": "text",
        "weight": 0,
        "translations": {
            "de": "Firmware-Version",
            "fr": "Version du firmware",
            "es": "Versión de firmware",
            "it": "Versione firmware",
            "pt": "Versão de firmware",
            "zh": "固件版本",
            "ru": "Версия прошивки",
            "da": "Firmwareversion",
            "ar": "إصدار البرنامج الثابت",
        },
    },
    "version": {
        "key": "version",
        "label": "Version",
        "type": "text",
        "weight": 0,
        "translations": {
            "de": "Version",
            "fr": "Version",
            "es": "Versión",
            "it": "Versione",
            "pt": "Versão",
            "zh": "版本",
            "ru": "Версия",
            "da": "Version",
            "ar": "الإصدار",
        },
    },
    "function": {
        "key": "function",
        "label": "Function",
        "type": "text",
        "weight": 0,
        "translations": {
            "de": "Funktion",
            "fr": "Fonction",
            "es": "Función",
            "it": "Funzione",
            "pt": "Função",
            "zh": "功能",
            "ru": "Функция",
            "da": "Funktion",
            "ar": "الوظيفة",
        },
    },
    "manufacturer": {
        "key": "manufacturer",
        "label": "Manufacturer",
        "type": "text",
        "weight": 0,
        "translations": {
            "de": "Hersteller",
            "fr": "Fabricant",
            "es": "Fabricante",
            "it": "Produttore",
            "pt": "Fabricante",
            "zh": "制造商",
            "ru": "Производитель",
            "da": "Producent",
            "ar": "الشركة المصنّعة",
        },
    },
    "supportEndDate": {
        "key": "supportEndDate",
        "label": "Support End Date",
        "type": "date",
        "weight": 0,
        "translations": {
            "de": "Support-Enddatum",
            "fr": "Date de fin de support",
            "es": "Fecha de fin de soporte",
            "it": "Data di fine supporto",
            "pt": "Data de fim de suporte",
            "zh": "支持结束日期",
            "ru": "Дата окончания поддержки",
            "da": "Slutdato for support",
            "ar": "تاريخ انتهاء الدعم",
        },
    },
}


def _seed(key: str) -> dict:
    return deepcopy(_SEED_FIELDS[key])


_CODE = _text(
    "code",
    "Code",
    _tr("Code", "Code", "Código", "Codice", "Código", "编码", "Код", "Kode", "الرمز"),
)
_TECH_SUPPORT = ["supportContractStatus", "typeOfOperation", "capitalCost", "operatingCost"]

_MODEL_TYPE = {
    "key": "modelType",
    "label": "Model / Template Type",
    "type": "single_select",
    "weight": 0,
    "translations": _tr(
        "Modell-/Vorlagentyp",
        "Type de modèle",
        "Tipo de modelo / plantilla",
        "Tipo di modello",
        "Tipo de modelo",
        "模板类型",
        "Тип шаблона",
        "Skabelontype",
        "نوع النموذج",
    ),
    "options": [
        {
            "key": "serviceRequestForm",
            "label": "Service request form",
            "translations": _tr(
                "Serviceantragsformular",
                "Formulaire de demande de service",
                "Formulario de solicitud de servicio",
                "Modulo di richiesta servizio",
                "Formulário de pedido de serviço",
                "服务申请表",
                "Форма заявки на услугу",
                "Serviceanmodningsformular",
                "نموذج طلب خدمة",
            ),
        },
        {
            "key": "dataCollectionForm",
            "label": "Data collection form",
            "translations": _tr(
                "Datenerhebungsformular",
                "Formulaire de collecte de données",
                "Formulario de recopilación de datos",
                "Modulo di raccolta dati",
                "Formulário de recolha de dados",
                "数据收集表",
                "Форма сбора данных",
                "Dataindsamlingsformular",
                "نموذج حصر بيانات",
            ),
        },
        {
            "key": "guideTemplate",
            "label": "Guide template",
            "translations": _tr(
                "Leitfadenvorlage",
                "Modèle de guide",
                "Plantilla de guía",
                "Modello di guida",
                "Modelo de guia",
                "指南模板",
                "Шаблон руководства",
                "Vejledningsskabelon",
                "قالب دليل",
            ),
        },
        {
            "key": "policyTemplate",
            "label": "Policy template",
            "translations": _tr(
                "Richtlinienvorlage",
                "Modèle de politique",
                "Plantilla de política",
                "Modello di politica",
                "Modelo de política",
                "政策模板",
                "Шаблон политики",
                "Politikskabelon",
                "قالب سياسة",
            ),
        },
        {
            "key": "other",
            "label": "Other",
            "translations": _tr(
                "Sonstiges", "Autre", "Otro", "Altro", "Outro", "其他", "Другое", "Andet", "أخرى"
            ),
        },
    ],
}

# Type key → the fields to add (B1 attribute tables + the templates).
NORA_DGA_TYPE_FIELDS: dict[str, list[dict]] = {
    # B1 §5.3.9.2.1 / template "أجهزة الأمن".
    "SecurityHardware": [deepcopy(_CODE), _seed("firmwareVersion"), *map(_seed, _TECH_SUPPORT)],
    # B1 §5.3.9.2.2 / template "برمجيات الأمن".
    "SecuritySoftware": [deepcopy(_CODE), _seed("version"), *map(_seed, _TECH_SUPPORT)],
    # B1 §5.3.9.2.3 / template "خدمات الأمن".
    "SecurityService": [deepcopy(_CODE), _seed("function"), *map(_seed, _TECH_SUPPORT)],
    # Template "نقاط الربط التقني": the integration point's number.
    "Interface": [
        _text(
            "integrationPointCode",
            "Integration Point Number",
            _tr(
                "Nummer des Integrationspunkts",
                "Numéro du point d'intégration",
                "Número del punto de integración",
                "Numero del punto di integrazione",
                "Número do ponto de integração",
                "集成点编号",
                "Номер точки интеграции",
                "Integrationspunktnummer",
                "رقم نقطة الربط التقني",
            ),
        )
    ],
    # B1 §5.3.6.2.3 (type, quality rules — the classification is copied from
    # Data Object in nora_profile) + the templates "سمات البيانات" and
    # "فهرس الأعمال".
    "DataAttribute": [
        _text(
            "code",
            "Attribute ID",
            _tr(
                "Attribut-ID",
                "Identifiant de l'attribut",
                "ID del atributo",
                "ID dell'attributo",
                "ID do atributo",
                "属性标识",
                "Идентификатор атрибута",
                "Attribut-id",
                "معرف سمة البيانات",
            ),
        ),
        _text(
            "dataType",
            "Data Type",
            _tr(
                "Datentyp",
                "Type de données",
                "Tipo de dato",
                "Tipo di dato",
                "Tipo de dado",
                "数据类型",
                "Тип данных",
                "Datatype",
                "نوع البيانات",
            ),
        ),
        _text(
            "dataLength",
            "Data Length",
            _tr(
                "Datenlänge",
                "Longueur",
                "Longitud",
                "Lunghezza",
                "Comprimento",
                "数据长度",
                "Длина",
                "Datalængde",
                "طول البيانات",
            ),
            "number",
        ),
        _text(
            "dataFormat",
            "Data Format",
            _tr(
                "Datenformat",
                "Format des données",
                "Formato de datos",
                "Formato dei dati",
                "Formato dos dados",
                "数据格式",
                "Формат данных",
                "Dataformat",
                "تنسيق البيانات",
            ),
        ),
        _text(
            "primaryKey",
            "Primary Key",
            _tr(
                "Primärschlüssel",
                "Clé primaire",
                "Clave primaria",
                "Chiave primaria",
                "Chave primária",
                "主键",
                "Первичный ключ",
                "Primærnøgle",
                "مفتاح أساسي",
            ),
            "boolean",
        ),
        _text(
            "nullable",
            "Accepts Empty Values",
            _tr(
                "Leere Werte erlaubt",
                "Accepte les valeurs vides",
                "Admite valores vacíos",
                "Ammette valori vuoti",
                "Aceita valores vazios",
                "允许空值",
                "Допускает пустые значения",
                "Tillader tomme værdier",
                "إمكانية قبول الفراغ",
            ),
            "boolean",
        ),
        _text(
            "qualityRules",
            "Quality / Business Rules",
            _tr(
                "Qualitäts-/Geschäftsregeln",
                "Règles de qualité / métier",
                "Reglas de calidad / negocio",
                "Regole di qualità / di business",
                "Regras de qualidade / negócio",
                "质量/业务规则",
                "Правила качества / бизнес-правила",
                "Kvalitets-/forretningsregler",
                "قواعد الجودة / قواعد أعمال السمة",
            ),
        ),
        _text(
            "businessScope",
            "Business Scope",
            _tr(
                "Geschäftsbereich",
                "Périmètre métier",
                "Ámbito de negocio",
                "Ambito di business",
                "Âmbito de negócio",
                "业务范围",
                "Бизнес-область",
                "Forretningsområde",
                "نطاق العمل",
            ),
        ),
        _text(
            "dataSource",
            "Data Source",
            _tr(
                "Datenquelle",
                "Source des données",
                "Fuente de datos",
                "Fonte dei dati",
                "Fonte dos dados",
                "数据源",
                "Источник данных",
                "Datakilde",
                "مصدر البيانات",
            ),
        ),
        _text(
            "tableName",
            "Database Table",
            _tr(
                "Datenbanktabelle",
                "Table de base de données",
                "Tabla de base de datos",
                "Tabella del database",
                "Tabela da base de dados",
                "数据库表",
                "Таблица базы данных",
                "Databasetabel",
                "اسم الجدول في قاعدة البيانات",
            ),
        ),
        _text(
            "schemaName",
            "Database Schema",
            _tr(
                "Datenbankschema",
                "Schéma de base de données",
                "Esquema de base de datos",
                "Schema del database",
                "Esquema da base de dados",
                "数据库模式",
                "Схема базы данных",
                "Databaseskema",
                "اسم مخطط قاعدة البيانات",
            ),
        ),
        _text(
            "sampleValues",
            "Sample Values",
            _tr(
                "Beispielwerte",
                "Exemples de valeurs",
                "Valores de ejemplo",
                "Valori di esempio",
                "Valores de exemplo",
                "示例值",
                "Примеры значений",
                "Eksempelværdier",
                "عينة من القيم",
            ),
        ),
        _text(
            "lookupSource",
            "Approved Value List",
            _tr(
                "Freigegebene Werteliste",
                "Liste de valeurs approuvée",
                "Lista de valores aprobada",
                "Elenco di valori approvato",
                "Lista de valores aprovada",
                "批准的值列表",
                "Утверждённый список значений",
                "Godkendt værdiliste",
                "القوائم المعتمدة",
            ),
        ),
        _text(
            "dataOwner",
            "Data Owner",
            _tr(
                "Datenverantwortlicher",
                "Propriétaire des données",
                "Responsable de los datos",
                "Responsabile dei dati",
                "Responsável pelos dados",
                "数据所有者",
                "Владелец данных",
                "Dataejer",
                "ممثل بيانات الأعمال",
            ),
        ),
        _text(
            "dataSteward",
            "Data Steward",
            _tr(
                "Datenverwalter",
                "Gestionnaire des données",
                "Custodio de datos",
                "Data steward",
                "Curador de dados",
                "数据管理员",
                "Распорядитель данных",
                "Dataforvalter",
                "مختص بيانات الأعمال",
            ),
        ),
    ],
    # Template "خدمات التقنية التحتية": the service code.
    "InfrastructureService": [deepcopy(_CODE)],
    # Template "أجهزة المضيف المادي": hypervisor type and version.
    "PhysicalHost": [
        _text(
            "hypervisorType",
            "Hypervisor Type",
            _tr(
                "Hypervisor-Typ",
                "Type d'hyperviseur",
                "Tipo de hipervisor",
                "Tipo di hypervisor",
                "Tipo de hipervisor",
                "虚拟机监控程序类型",
                "Тип гипервизора",
                "Hypervisortype",
                "نوع مراقب الآلة الافتراضي",
            ),
        ),
        _text(
            "hypervisorVersion",
            "Hypervisor Version",
            _tr(
                "Hypervisor-Version",
                "Version de l'hyperviseur",
                "Versión del hipervisor",
                "Versione dell'hypervisor",
                "Versão do hipervisor",
                "虚拟机监控程序版本",
                "Версия гипервизора",
                "Hypervisorversion",
                "إصدار مراقب الآلة الافتراضي",
            ),
        ),
    ],
    # Template "دليل الخوادم الافتراضية": backup and disaster-recovery cover.
    "Server": [
        _text(
            "inBackupPolicy",
            "In Backup Policy",
            _tr(
                "In Sicherungsrichtlinie",
                "Couvert par la sauvegarde",
                "Incluido en la copia de seguridad",
                "Incluso nel backup",
                "Incluído na cópia de segurança",
                "纳入备份策略",
                "Входит в резервное копирование",
                "Omfattet af backup",
                "مشمول بالنسخ الاحتياطي",
            ),
            "boolean",
        ),
        _text(
            "inDrPolicy",
            "In Disaster Recovery Policy",
            _tr(
                "In Notfallwiederherstellung",
                "Couvert par le PRA",
                "Incluido en la recuperación ante desastres",
                "Incluso nel disaster recovery",
                "Incluído na recuperação de desastres",
                "纳入灾难恢复",
                "Входит в аварийное восстановление",
                "Omfattet af katastrofeberedskab",
                "مشمول بالتعافي من الكوارث",
            ),
            "boolean",
        ),
    ],
    # B1 §5.3.3.2.12 / template "دليل النماذج".
    "ModelTemplate": [
        deepcopy(_CODE),
        _MODEL_TYPE,
        _text(
            "modelLink",
            "Link",
            _tr("Link", "Lien", "Enlace", "Link", "Link", "链接", "Ссылка", "Link", "الرابط"),
            "url",
        ),
    ],
    # Template "دليل السياسات": scope and clauses (the other policy attributes
    # land from the Policy type definition, NORA_CARD_TYPE_FIELD_LANDING).
    "Policy": [
        _text(
            "policyScope",
            "Policy Scope",
            _tr(
                "Geltungsbereich",
                "Périmètre de la politique",
                "Alcance de la política",
                "Ambito della politica",
                "Âmbito da política",
                "政策范围",
                "Область действия политики",
                "Politikkens omfang",
                "نطاق السياسة",
            ),
        ),
        _text(
            "policyClauses",
            "Policy Clauses",
            _tr(
                "Richtlinienbestimmungen",
                "Clauses de la politique",
                "Cláusulas de la política",
                "Clausole della politica",
                "Cláusulas da política",
                "政策条款",
                "Положения политики",
                "Politikkens bestemmelser",
                "بنود السياسة",
            ),
        ),
    ],
}
