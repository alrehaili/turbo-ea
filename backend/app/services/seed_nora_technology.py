"""NORA Content Meta Model — Technology Architecture building blocks.

[FORK] NORA exact-fidelity metamodel (noraPlanMeta.md, Phase 1F).

The National EA Framework "EA Content Meta Model" document (§5.3.6) defines the
Technology Architecture domain as 11 **independent** building blocks. The stock
tool collapsed most of them into a single ``ITComponent`` type with subtypes.
This module restores them as first-class card types so the seeded metamodel is a
faithful 1:1 realisation of the document.

Two of the 11 already exist as standalone types in ``seed.TYPES``
(``Datacenter`` = Data Center, ``NetworkCircuit`` = Network Link), so this module
adds the remaining **nine**:

    Server, PhysicalHost, NetworkDevice, Storage, ContainerizationEngine,
    InfrastructureService, InfrastructureManagementTool, PeripheralDevice, License

The list is appended onto ``seed.TYPES`` (``TYPES += NORA_TECHNOLOGY_TYPES``) so
the standard ``seed_metamodel`` insert/merge loop and the ``test_i18n_seed``
completeness check both see them with zero extra wiring.

Every type / section / field / option carries translations for all nine
non-English locales (de, fr, es, it, pt, zh, ru, da, ar) per project i18n rules.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Shared select-option constants (kept local to avoid a circular import with
# seed.py, which imports this module).
# ---------------------------------------------------------------------------

# "Type of Operation" — in-house team vs service provider (doc: recurring attr)
_OPERATION_TYPE_OPTIONS = [
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
]

# "Support Contract Status" — active vs expired (doc: recurring attr)
_SUPPORT_STATUS_OPTIONS = [
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
]

# "Network Segment" — shared across host/server/network/storage/security (doc)
_NETWORK_SEGMENT_OPTIONS = [
    {
        "key": "dmz",
        "label": "DMZ",
        "translations": {
            "de": "DMZ",
            "fr": "DMZ",
            "es": "DMZ",
            "it": "DMZ",
            "pt": "DMZ",
            "zh": "隔离区 (DMZ)",
            "ru": "DMZ",
            "da": "DMZ",
            "ar": "المنطقة منزوعة السلاح (DMZ)",
        },
    },
    {
        "key": "extranet",
        "label": "Extranet",
        "translations": {
            "de": "Extranet",
            "fr": "Extranet",
            "es": "Extranet",
            "it": "Extranet",
            "pt": "Extranet",
            "zh": "外联网",
            "ru": "Экстранет",
            "da": "Extranet",
            "ar": "الشبكة الخارجية",
        },
    },
    {
        "key": "internet",
        "label": "Internet",
        "translations": {
            "de": "Internet",
            "fr": "Internet",
            "es": "Internet",
            "it": "Internet",
            "pt": "Internet",
            "zh": "互联网",
            "ru": "Интернет",
            "da": "Internet",
            "ar": "الإنترنت",
        },
    },
    {
        "key": "wan",
        "label": "WAN",
        "translations": {
            "de": "WAN",
            "fr": "WAN",
            "es": "WAN",
            "it": "WAN",
            "pt": "WAN",
            "zh": "广域网",
            "ru": "WAN",
            "da": "WAN",
            "ar": "الشبكة الواسعة (WAN)",
        },
    },
    {
        "key": "lan",
        "label": "LAN",
        "translations": {
            "de": "LAN",
            "fr": "LAN",
            "es": "LAN",
            "it": "LAN",
            "pt": "LAN",
            "zh": "局域网",
            "ru": "LAN",
            "da": "LAN",
            "ar": "الشبكة المحلية (LAN)",
        },
    },
    {
        "key": "airGapped",
        "label": "Air Gapped",
        "translations": {
            "de": "Air-Gapped",
            "fr": "Isolé (air gap)",
            "es": "Aislado (air gap)",
            "it": "Isolato (air gap)",
            "pt": "Isolado (air gap)",
            "zh": "物理隔离",
            "ru": "Изолированная сеть",
            "da": "Air gapped",
            "ar": "معزول تمامًا",
        },
    },
    {
        "key": "dataCenter",
        "label": "Data Center",
        "translations": {
            "de": "Rechenzentrum",
            "fr": "Centre de données",
            "es": "Centro de datos",
            "it": "Data center",
            "pt": "Data center",
            "zh": "数据中心",
            "ru": "Центр обработки данных",
            "da": "Datacenter",
            "ar": "مركز البيانات",
        },
    },
]

# "Environment" — production / development / testing (doc: recurring attr)
_ENVIRONMENT_OPTIONS = [
    {
        "key": "production",
        "label": "Production",
        "translations": {
            "de": "Produktion",
            "fr": "Production",
            "es": "Producción",
            "it": "Produzione",
            "pt": "Produção",
            "zh": "生产环境",
            "ru": "Продуктивная среда",
            "da": "Produktion",
            "ar": "بيئة الإنتاج",
        },
    },
    {
        "key": "development",
        "label": "Development",
        "translations": {
            "de": "Entwicklung",
            "fr": "Développement",
            "es": "Desarrollo",
            "it": "Sviluppo",
            "pt": "Desenvolvimento",
            "zh": "开发环境",
            "ru": "Среда разработки",
            "da": "Udvikling",
            "ar": "بيئة التطوير",
        },
    },
    {
        "key": "testing",
        "label": "Testing",
        "translations": {
            "de": "Test",
            "fr": "Test",
            "es": "Pruebas",
            "it": "Test",
            "pt": "Teste",
            "zh": "测试环境",
            "ru": "Тестовая среда",
            "da": "Test",
            "ar": "بيئة الاختبار",
        },
    },
]


# ---------------------------------------------------------------------------
# Reusable field builders (all documented attributes carry a `capitalCost` /
# `operatingCost` cost pair + a support/operation block, so factor them out).
# ---------------------------------------------------------------------------


def _tx(**kw: str) -> dict:
    """Assemble a 9-locale translation dict (all keys required)."""
    return {loc: kw[loc] for loc in ("de", "fr", "es", "it", "pt", "zh", "ru", "da", "ar")}


def _cost_fields(weight_start: int = 20) -> list[dict]:
    """Capital Cost + Operating Cost — present on every technology block."""
    return [
        {
            "key": "capitalCost",
            "label": "Capital Cost",
            "type": "cost",
            "weight": weight_start,
            "translations": _tx(
                de="Kapitalkosten",
                fr="Coût d'investissement",
                es="Coste de capital",
                it="Costo di capitale",
                pt="Custo de capital",
                zh="资本成本",
                ru="Капитальные затраты",
                da="Kapitalomkostning",
                ar="التكلفة الرأسمالية",
            ),
        },
        {
            "key": "operatingCost",
            "label": "Operating Cost",
            "type": "cost",
            "weight": weight_start + 1,
            "translations": _tx(
                de="Betriebskosten",
                fr="Coût d'exploitation",
                es="Coste operativo",
                it="Costo operativo",
                pt="Custo operacional",
                zh="运营成本",
                ru="Эксплуатационные расходы",
                da="Driftsomkostning",
                ar="التكلفة التشغيلية",
            ),
        },
    ]


def _field(key: str, label: str, ftype: str, weight: int, tx: dict, options=None) -> dict:
    f = {"key": key, "label": label, "type": ftype, "weight": weight, "translations": tx}
    if options is not None:
        f["options"] = options
    return f


_MANUFACTURER = lambda w: _field(  # noqa: E731
    "manufacturer",
    "Manufacturer",
    "text",
    w,
    _tx(
        de="Hersteller",
        fr="Fabricant",
        es="Fabricante",
        it="Produttore",
        pt="Fabricante",
        zh="制造商",
        ru="Производитель",
        da="Producent",
        ar="الشركة المصنّعة",
    ),
)

_MODEL = lambda w: _field(  # noqa: E731
    "model",
    "Model",
    "text",
    w,
    _tx(
        de="Modell",
        fr="Modèle",
        es="Modelo",
        it="Modello",
        pt="Modelo",
        zh="型号",
        ru="Модель",
        da="Model",
        ar="الطراز",
    ),
)

_SUPPORT_END = lambda w: _field(  # noqa: E731
    "supportEndDate",
    "Support End Date",
    "date",
    w,
    _tx(
        de="Support-Enddatum",
        fr="Date de fin de support",
        es="Fecha de fin de soporte",
        it="Data di fine supporto",
        pt="Data de fim de suporte",
        zh="支持结束日期",
        ru="Дата окончания поддержки",
        da="Slutdato for support",
        ar="تاريخ انتهاء الدعم",
    ),
)

_SUPPORT_STATUS = lambda w: _field(  # noqa: E731
    "supportContractStatus",
    "Support Contract Status",
    "single_select",
    w,
    _tx(
        de="Status des Supportvertrags",
        fr="Statut du contrat de support",
        es="Estado del contrato de soporte",
        it="Stato del contratto di supporto",
        pt="Estado do contrato de suporte",
        zh="支持合同状态",
        ru="Статус договора поддержки",
        da="Status for supportkontrakt",
        ar="حالة عقد الدعم",
    ),
    options=_SUPPORT_STATUS_OPTIONS,
)

_OPERATION_TYPE = lambda w: _field(  # noqa: E731
    "typeOfOperation",
    "Type of Operation",
    "single_select",
    w,
    _tx(
        de="Betriebsart",
        fr="Type d'exploitation",
        es="Tipo de operación",
        it="Tipo di operazione",
        pt="Tipo de operação",
        zh="运营方式",
        ru="Тип эксплуатации",
        da="Driftstype",
        ar="نوع التشغيل",
    ),
    options=_OPERATION_TYPE_OPTIONS,
)

_NETWORK_SEGMENT = lambda w: _field(  # noqa: E731
    "networkSegment",
    "Network Segment",
    "single_select",
    w,
    _tx(
        de="Netzwerksegment",
        fr="Segment réseau",
        es="Segmento de red",
        it="Segmento di rete",
        pt="Segmento de rede",
        zh="网络分段",
        ru="Сегмент сети",
        da="Netværkssegment",
        ar="مقطع الشبكة",
    ),
    options=_NETWORK_SEGMENT_OPTIONS,
)


def _section(name: str, tx: dict, fields: list[dict]) -> dict:
    return {"section": name, "translations": tx, "fields": fields}


def _details_section_tx() -> dict:
    return _tx(
        de="Technische Details",
        fr="Détails techniques",
        es="Detalles técnicos",
        it="Dettagli tecnici",
        pt="Detalhes técnicos",
        zh="技术详情",
        ru="Технические сведения",
        da="Tekniske detaljer",
        ar="التفاصيل التقنية",
    )


# ---------------------------------------------------------------------------
# The nine Technology-domain building blocks
# ---------------------------------------------------------------------------

NORA_TECHNOLOGY_TYPES: list[dict] = [
    # 34 · Server ----------------------------------------------------------
    {
        "key": "Server",
        "label": "Server",
        "description": "Physical or virtual servers hosting systems, applications, "
        "services, and databases.",
        "icon": "dns",
        "color": "#d29270",
        "category": "Technology",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Server",
                fr="Serveur",
                es="Servidor",
                it="Server",
                pt="Servidor",
                zh="服务器",
                ru="Сервер",
                da="Server",
                ar="خادم",
            ),
            "description": _tx(
                de="Physische oder virtuelle Server, die Systeme, Anwendungen, Dienste und "
                "Datenbanken hosten.",
                fr="Serveurs physiques ou virtuels hébergeant systèmes, applications, services "
                "et bases de données.",
                es="Servidores físicos o virtuales que alojan sistemas, aplicaciones, servicios "
                "y bases de datos.",
                it="Server fisici o virtuali che ospitano sistemi, applicazioni, servizi e "
                "database.",
                pt="Servidores físicos ou virtuais que alojam sistemas, aplicações, serviços e "
                "bases de dados.",
                zh="托管系统、应用、服务和数据库的物理或虚拟服务器。",
                ru="Физические или виртуальные серверы, размещающие системы, приложения, службы "
                "и базы данных.",
                da="Fysiske eller virtuelle servere, der hoster systemer, applikationer, "
                "tjenester og databaser.",
                ar="خوادم مادية أو افتراضية تستضيف الأنظمة والتطبيقات والخدمات وقواعد البيانات.",
            ),
        },
        "subtypes": [
            {
                "key": "physical",
                "label": "Physical Server",
                "translations": _tx(
                    de="Physischer Server",
                    fr="Serveur physique",
                    es="Servidor físico",
                    it="Server fisico",
                    pt="Servidor físico",
                    zh="物理服务器",
                    ru="Физический сервер",
                    da="Fysisk server",
                    ar="خادم مادي",
                ),
                "hidden_fields": [],
            },
            {
                "key": "virtual",
                "label": "Virtual Server",
                "translations": _tx(
                    de="Virtueller Server",
                    fr="Serveur virtuel",
                    es="Servidor virtual",
                    it="Server virtuale",
                    pt="Servidor virtual",
                    zh="虚拟服务器",
                    ru="Виртуальный сервер",
                    da="Virtuel server",
                    ar="خادم افتراضي",
                ),
                "hidden_fields": [],
            },
        ],
        "sort_order": 20,
        "fields_schema": [
            _section(
                "Server Details",
                _details_section_tx(),
                [
                    _field(
                        "operatingSystemType",
                        "Operating System Type",
                        "text",
                        1,
                        _tx(
                            de="Betriebssystemtyp",
                            fr="Type de système d'exploitation",
                            es="Tipo de sistema operativo",
                            it="Tipo di sistema operativo",
                            pt="Tipo de sistema operativo",
                            zh="操作系统类型",
                            ru="Тип операционной системы",
                            da="Operativsystemtype",
                            ar="نوع نظام التشغيل",
                        ),
                    ),
                    _field(
                        "operatingSystemVersion",
                        "Operating System Version",
                        "text",
                        2,
                        _tx(
                            de="Betriebssystemversion",
                            fr="Version du système d'exploitation",
                            es="Versión del sistema operativo",
                            it="Versione del sistema operativo",
                            pt="Versão do sistema operativo",
                            zh="操作系统版本",
                            ru="Версия операционной системы",
                            da="Operativsystemversion",
                            ar="إصدار نظام التشغيل",
                        ),
                    ),
                    _field(
                        "clusterId",
                        "Cluster ID",
                        "text",
                        3,
                        _tx(
                            de="Cluster-ID",
                            fr="ID de cluster",
                            es="ID de clúster",
                            it="ID cluster",
                            pt="ID de cluster",
                            zh="集群 ID",
                            ru="ID кластера",
                            da="Cluster-ID",
                            ar="معرّف العنقود",
                        ),
                    ),
                    _NETWORK_SEGMENT(4),
                    _field(
                        "centralProcessingUnits",
                        "Central Processing Units",
                        "number",
                        5,
                        _tx(
                            de="Zentrale Recheneinheiten (CPU)",
                            fr="Unités centrales de traitement",
                            es="Unidades centrales de procesamiento",
                            it="Unità di elaborazione centrale",
                            pt="Unidades centrais de processamento",
                            zh="中央处理器数量",
                            ru="Центральные процессоры",
                            da="Centrale processorenheder",
                            ar="وحدات المعالجة المركزية",
                        ),
                    ),
                    _field(
                        "ram",
                        "Random Access Memory (GB)",
                        "number",
                        6,
                        _tx(
                            de="Arbeitsspeicher (GB)",
                            fr="Mémoire vive (Go)",
                            es="Memoria RAM (GB)",
                            it="Memoria RAM (GB)",
                            pt="Memória RAM (GB)",
                            zh="内存 (GB)",
                            ru="Оперативная память (ГБ)",
                            da="RAM (GB)",
                            ar="ذاكرة الوصول العشوائي (غيغابايت)",
                        ),
                    ),
                    _field(
                        "disk",
                        "Disk Capacity (GB)",
                        "number",
                        7,
                        _tx(
                            de="Festplattenkapazität (GB)",
                            fr="Capacité disque (Go)",
                            es="Capacidad de disco (GB)",
                            it="Capacità disco (GB)",
                            pt="Capacidade de disco (GB)",
                            zh="磁盘容量 (GB)",
                            ru="Ёмкость диска (ГБ)",
                            da="Diskkapacitet (GB)",
                            ar="سعة القرص (غيغابايت)",
                        ),
                    ),
                    _field(
                        "role",
                        "Role",
                        "text",
                        8,
                        _tx(
                            de="Rolle",
                            fr="Rôle",
                            es="Rol",
                            it="Ruolo",
                            pt="Função",
                            zh="角色",
                            ru="Роль",
                            da="Rolle",
                            ar="الدور",
                        ),
                    ),
                    _field(
                        "environment",
                        "Environment",
                        "single_select",
                        9,
                        _tx(
                            de="Umgebung",
                            fr="Environnement",
                            es="Entorno",
                            it="Ambiente",
                            pt="Ambiente",
                            zh="环境",
                            ru="Среда",
                            da="Miljø",
                            ar="البيئة",
                        ),
                        options=_ENVIRONMENT_OPTIONS,
                    ),
                    _SUPPORT_END(10),
                    _SUPPORT_STATUS(11),
                    _OPERATION_TYPE(12),
                    *_cost_fields(20),
                ],
            ),
        ],
    },
    # 33 · Physical Host ---------------------------------------------------
    {
        "key": "PhysicalHost",
        "label": "Physical Host",
        "description": "Physical host hardware owned by the entity, used to host virtual "
        "servers (stand-alone, racked, blade, or HCI).",
        "icon": "memory",
        "color": "#d29270",
        "category": "Technology",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Physischer Host",
                fr="Hôte physique",
                es="Host físico",
                it="Host fisico",
                pt="Host físico",
                zh="物理主机",
                ru="Физический хост",
                da="Fysisk vært",
                ar="المضيف المادي",
            ),
            "description": _tx(
                de="Physische Host-Hardware der Organisation zum Hosten virtueller Server "
                "(eigenständig, im Rack, Blade oder HCI).",
                fr="Matériel hôte physique de l'entité, utilisé pour héberger des serveurs "
                "virtuels (autonome, en rack, lame ou HCI).",
                es="Hardware host físico de la entidad, usado para alojar servidores virtuales "
                "(independiente, en rack, blade o HCI).",
                it="Hardware host fisico dell'ente, usato per ospitare server virtuali "
                "(stand-alone, rack, blade o HCI).",
                pt="Hardware de host físico da entidade, usado para alojar servidores virtuais "
                "(autónomo, em rack, blade ou HCI).",
                zh="实体拥有的物理主机硬件，用于托管虚拟服务器（独立式、机架式、刀片式或超融合）。",
                ru="Физическое хост-оборудование организации для размещения виртуальных серверов "
                "(автономное, стоечное, блейд или HCI).",
                da="Fysisk værtshardware ejet af enheden, brugt til at hoste virtuelle servere "
                "(stand-alone, rack, blade eller HCI).",
                ar="عتاد المضيف المادي المملوك للجهة، يُستخدم لاستضافة الخوادم الافتراضية "
                "(مستقل أو في حامل أو نصلي أو بنية فائقة التقارب).",
            ),
        },
        "subtypes": [],
        "sort_order": 21,
        "fields_schema": [
            _section(
                "Physical Host Details",
                _details_section_tx(),
                [
                    _MANUFACTURER(1),
                    _MODEL(2),
                    _field(
                        "technology",
                        "Technology",
                        "text",
                        3,
                        _tx(
                            de="Technologie",
                            fr="Technologie",
                            es="Tecnología",
                            it="Tecnologia",
                            pt="Tecnologia",
                            zh="技术",
                            ru="Технология",
                            da="Teknologi",
                            ar="التقنية",
                        ),
                    ),
                    _field(
                        "clusterId",
                        "Cluster ID",
                        "text",
                        4,
                        _tx(
                            de="Cluster-ID",
                            fr="ID de cluster",
                            es="ID de clúster",
                            it="ID cluster",
                            pt="ID de cluster",
                            zh="集群 ID",
                            ru="ID кластера",
                            da="Cluster-ID",
                            ar="معرّف العنقود",
                        ),
                    ),
                    _NETWORK_SEGMENT(5),
                    _field(
                        "centralProcessingUnit",
                        "Central Processing Unit",
                        "text",
                        6,
                        _tx(
                            de="Zentrale Recheneinheit (CPU)",
                            fr="Unité centrale de traitement",
                            es="Unidad central de procesamiento",
                            it="Unità di elaborazione centrale",
                            pt="Unidade central de processamento",
                            zh="中央处理器",
                            ru="Центральный процессор",
                            da="Central processorenhed",
                            ar="وحدة المعالجة المركزية",
                        ),
                    ),
                    _field(
                        "physicalCpuCores",
                        "Total Physical CPU Cores",
                        "number",
                        7,
                        _tx(
                            de="Physische CPU-Kerne insgesamt",
                            fr="Nombre total de cœurs CPU physiques",
                            es="Núcleos físicos de CPU totales",
                            it="Core CPU fisici totali",
                            pt="Núcleos físicos de CPU totais",
                            zh="物理 CPU 核心总数",
                            ru="Всего физических ядер ЦП",
                            da="Fysiske CPU-kerner i alt",
                            ar="إجمالي أنوية المعالج المادية",
                        ),
                    ),
                    _field(
                        "physicalRam",
                        "Physical RAM (GB)",
                        "number",
                        8,
                        _tx(
                            de="Physischer Arbeitsspeicher (GB)",
                            fr="Mémoire vive physique (Go)",
                            es="Memoria RAM física (GB)",
                            it="RAM fisica (GB)",
                            pt="RAM física (GB)",
                            zh="物理内存 (GB)",
                            ru="Физическая ОЗУ (ГБ)",
                            da="Fysisk RAM (GB)",
                            ar="ذاكرة الوصول العشوائي المادية (غيغابايت)",
                        ),
                    ),
                    _field(
                        "localStorageCapacity",
                        "Local Storage Capacity (GB)",
                        "number",
                        9,
                        _tx(
                            de="Lokale Speicherkapazität (GB)",
                            fr="Capacité de stockage local (Go)",
                            es="Capacidad de almacenamiento local (GB)",
                            it="Capacità di archiviazione locale (GB)",
                            pt="Capacidade de armazenamento local (GB)",
                            zh="本地存储容量 (GB)",
                            ru="Локальная ёмкость хранения (ГБ)",
                            da="Lokal lagerkapacitet (GB)",
                            ar="سعة التخزين المحلية (غيغابايت)",
                        ),
                    ),
                    _SUPPORT_END(10),
                    _SUPPORT_STATUS(11),
                    _OPERATION_TYPE(12),
                    *_cost_fields(20),
                ],
            ),
        ],
    },
    # 36 · Network Device --------------------------------------------------
    {
        "key": "NetworkDevice",
        "label": "Network Device",
        "description": "Network devices of various types (routers, switches, access points, "
        "controllers) used across the entity's locations and data centers.",
        "icon": "router",
        "color": "#d29270",
        "category": "Technology",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Netzwerkgerät",
                fr="Équipement réseau",
                es="Dispositivo de red",
                it="Dispositivo di rete",
                pt="Dispositivo de rede",
                zh="网络设备",
                ru="Сетевое устройство",
                da="Netværksenhed",
                ar="جهاز شبكة",
            ),
            "description": _tx(
                de="Netzwerkgeräte verschiedener Art (Router, Switches, Access Points, "
                "Controller) an den Standorten und in den Rechenzentren der Organisation.",
                fr="Équipements réseau de divers types (routeurs, commutateurs, points d'accès, "
                "contrôleurs) utilisés sur les sites et centres de données de l'entité.",
                es="Dispositivos de red de varios tipos (routers, switches, puntos de acceso, "
                "controladores) usados en las ubicaciones y centros de datos de la entidad.",
                it="Dispositivi di rete di vario tipo (router, switch, access point, controller) "
                "usati nelle sedi e nei data center dell'ente.",
                pt="Dispositivos de rede de vários tipos (routers, switches, pontos de acesso, "
                "controladores) usados nas localizações e data centers da entidade.",
                zh="实体各地点和数据中心使用的各类网络设备（路由器、交换机、接入点、控制器）。",
                ru="Сетевые устройства различных типов (маршрутизаторы, коммутаторы, точки "
                "доступа, контроллеры), используемые в помещениях и ЦОД организации.",
                da="Netværksenheder af forskellig art (routere, switches, access points, "
                "controllere) brugt på enhedens lokationer og datacentre.",
                ar="أجهزة شبكة من أنواع مختلفة (موجّهات، مبدّلات، نقاط وصول، متحكمات) تُستخدم في "
                "مواقع الجهة ومراكز بياناتها.",
            ),
        },
        "subtypes": [],
        "sort_order": 22,
        "fields_schema": [
            _section(
                "Network Device Details",
                _details_section_tx(),
                [
                    _MANUFACTURER(1),
                    _MODEL(2),
                    _field(
                        "location",
                        "Location",
                        "text",
                        3,
                        _tx(
                            de="Standort",
                            fr="Emplacement",
                            es="Ubicación",
                            it="Posizione",
                            pt="Localização",
                            zh="位置",
                            ru="Местоположение",
                            da="Placering",
                            ar="الموقع",
                        ),
                    ),
                    _NETWORK_SEGMENT(4),
                    _field(
                        "deviceType",
                        "Type",
                        "text",
                        5,
                        _tx(
                            de="Typ",
                            fr="Type",
                            es="Tipo",
                            it="Tipo",
                            pt="Tipo",
                            zh="类型",
                            ru="Тип",
                            da="Type",
                            ar="النوع",
                        ),
                    ),
                    _field(
                        "function",
                        "Function",
                        "text",
                        6,
                        _tx(
                            de="Funktion",
                            fr="Fonction",
                            es="Función",
                            it="Funzione",
                            pt="Função",
                            zh="功能",
                            ru="Функция",
                            da="Funktion",
                            ar="الوظيفة",
                        ),
                    ),
                    _field(
                        "firmwareVersion",
                        "Firmware Version",
                        "text",
                        7,
                        _tx(
                            de="Firmware-Version",
                            fr="Version du firmware",
                            es="Versión de firmware",
                            it="Versione firmware",
                            pt="Versão de firmware",
                            zh="固件版本",
                            ru="Версия прошивки",
                            da="Firmwareversion",
                            ar="إصدار البرنامج الثابت",
                        ),
                    ),
                    _SUPPORT_END(8),
                    _SUPPORT_STATUS(9),
                    _OPERATION_TYPE(10),
                    *_cost_fields(20),
                ],
            ),
        ],
    },
    # 38 · Storage ---------------------------------------------------------
    {
        "key": "Storage",
        "label": "Storage",
        "description": "Devices and tools used to store the entity's systems, software, and data.",
        "icon": "storage",
        "color": "#d29270",
        "category": "Technology",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Speicher",
                fr="Stockage",
                es="Almacenamiento",
                it="Archiviazione",
                pt="Armazenamento",
                zh="存储",
                ru="Хранилище",
                da="Lagring",
                ar="التخزين",
            ),
            "description": _tx(
                de="Geräte und Werkzeuge zur Speicherung der Systeme, Software und Daten der "
                "Organisation.",
                fr="Dispositifs et outils utilisés pour stocker les systèmes, logiciels et "
                "données de l'entité.",
                es="Dispositivos y herramientas usados para almacenar los sistemas, software y "
                "datos de la entidad.",
                it="Dispositivi e strumenti usati per archiviare sistemi, software e dati "
                "dell'ente.",
                pt="Dispositivos e ferramentas usados para armazenar os sistemas, software e "
                "dados da entidade.",
                zh="用于存储实体系统、软件和数据的设备与工具。",
                ru="Устройства и средства для хранения систем, программного обеспечения и данных "
                "организации.",
                da="Enheder og værktøjer til lagring af enhedens systemer, software og data.",
                ar="الأجهزة والأدوات المستخدمة لتخزين أنظمة الجهة وبرمجياتها وبياناتها.",
            ),
        },
        "subtypes": [],
        "sort_order": 23,
        "fields_schema": [
            _section(
                "Storage Details",
                _details_section_tx(),
                [
                    _MANUFACTURER(1),
                    _MODEL(2),
                    _field(
                        "firmwareVersion",
                        "Firmware Version",
                        "text",
                        3,
                        _tx(
                            de="Firmware-Version",
                            fr="Version du firmware",
                            es="Versión de firmware",
                            it="Versione firmware",
                            pt="Versão de firmware",
                            zh="固件版本",
                            ru="Версия прошивки",
                            da="Firmwareversion",
                            ar="إصدار البرنامج الثابت",
                        ),
                    ),
                    _NETWORK_SEGMENT(4),
                    _field(
                        "storageCapacity",
                        "Storage Capacity (GB)",
                        "number",
                        5,
                        _tx(
                            de="Speicherkapazität (GB)",
                            fr="Capacité de stockage (Go)",
                            es="Capacidad de almacenamiento (GB)",
                            it="Capacità di archiviazione (GB)",
                            pt="Capacidade de armazenamento (GB)",
                            zh="存储容量 (GB)",
                            ru="Ёмкость хранения (ГБ)",
                            da="Lagerkapacitet (GB)",
                            ar="سعة التخزين (غيغابايت)",
                        ),
                    ),
                    _SUPPORT_END(6),
                    _SUPPORT_STATUS(7),
                    _OPERATION_TYPE(8),
                    *_cost_fields(20),
                ],
            ),
        ],
    },
    # 35 · Containerization Engine ----------------------------------------
    {
        "key": "ContainerizationEngine",
        "label": "Containerization Engine",
        "description": "Containerization engines used by the entity, including data center, "
        "manufacturer, network location, environment, and support end date.",
        "icon": "deployed_code",
        "color": "#d29270",
        "category": "Technology",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Containerisierungs-Engine",
                fr="Moteur de conteneurisation",
                es="Motor de contenedores",
                it="Motore di containerizzazione",
                pt="Motor de contentorização",
                zh="容器化引擎",
                ru="Движок контейнеризации",
                da="Containeriseringsmotor",
                ar="محرّك الحاويات",
            ),
            "description": _tx(
                de="Von der Organisation genutzte Containerisierungs-Engines, inkl. "
                "Rechenzentrum, Hersteller, Netzwerkstandort, Umgebung und Support-Enddatum.",
                fr="Moteurs de conteneurisation utilisés par l'entité, incluant centre de "
                "données, fabricant, emplacement réseau, environnement et fin de support.",
                es="Motores de contenedores usados por la entidad, incluyendo centro de datos, "
                "fabricante, ubicación de red, entorno y fin de soporte.",
                it="Motori di containerizzazione usati dall'ente, inclusi data center, "
                "produttore, posizione di rete, ambiente e fine supporto.",
                pt="Motores de contentorização usados pela entidade, incluindo data center, "
                "fabricante, localização de rede, ambiente e fim de suporte.",
                zh="实体使用的容器化引擎，包括数据中心、制造商、网络位置、环境和支持结束日期。",
                ru="Используемые организацией движки контейнеризации, включая ЦОД, "
                "производителя, сетевое расположение, среду и дату окончания поддержки.",
                da="Containeriseringsmotorer brugt af enheden, inkl. datacenter, producent, "
                "netværksplacering, miljø og slutdato for support.",
                ar="محرّكات الحاويات التي تستخدمها الجهة، شاملةً مركز البيانات والشركة المصنّعة "
                "وموقع الشبكة والبيئة وتاريخ انتهاء الدعم.",
            ),
        },
        "subtypes": [],
        "sort_order": 24,
        "fields_schema": [
            _section(
                "Containerization Engine Details",
                _details_section_tx(),
                [
                    _MANUFACTURER(1),
                    _MODEL(2),
                    _NETWORK_SEGMENT(3),
                    _field(
                        "environment",
                        "Environment",
                        "single_select",
                        4,
                        _tx(
                            de="Umgebung",
                            fr="Environnement",
                            es="Entorno",
                            it="Ambiente",
                            pt="Ambiente",
                            zh="环境",
                            ru="Среда",
                            da="Miljø",
                            ar="البيئة",
                        ),
                        options=_ENVIRONMENT_OPTIONS,
                    ),
                    _SUPPORT_END(5),
                    _SUPPORT_STATUS(6),
                    _OPERATION_TYPE(7),
                    *_cost_fields(20),
                ],
            ),
        ],
    },
    # 39 · Infrastructure Service -----------------------------------------
    {
        "key": "InfrastructureService",
        "label": "Infrastructure Service",
        "description": "Basic services provided by the technical infrastructure (DNS, directory, "
        "DHCP, messaging/collaboration, backup, etc.).",
        "icon": "lan",
        "color": "#d29270",
        "category": "Technology",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Infrastrukturdienst",
                fr="Service d'infrastructure",
                es="Servicio de infraestructura",
                it="Servizio di infrastruttura",
                pt="Serviço de infraestrutura",
                zh="基础设施服务",
                ru="Инфраструктурная служба",
                da="Infrastrukturtjeneste",
                ar="خدمة البنية التحتية",
            ),
            "description": _tx(
                de="Grundlegende Dienste der technischen Infrastruktur (DNS, Verzeichnis, DHCP, "
                "Messaging/Kollaboration, Backup usw.).",
                fr="Services de base fournis par l'infrastructure technique (DNS, annuaire, DHCP, "
                "messagerie/collaboration, sauvegarde, etc.).",
                es="Servicios básicos de la infraestructura técnica (DNS, directorio, DHCP, "
                "mensajería/colaboración, copia de seguridad, etc.).",
                it="Servizi di base forniti dall'infrastruttura tecnica (DNS, directory, DHCP, "
                "messaggistica/collaborazione, backup, ecc.).",
                pt="Serviços básicos fornecidos pela infraestrutura técnica (DNS, diretório, "
                "DHCP, mensagens/colaboração, backup, etc.).",
                zh="技术基础设施提供的基础服务（DNS、目录、DHCP、消息/协作、备份等）。",
                ru="Базовые службы технической инфраструктуры (DNS, каталог, DHCP, "
                "обмен сообщениями/совместная работа, резервное копирование и т. д.).",
                da="Grundlæggende tjenester leveret af den tekniske infrastruktur (DNS, katalog, "
                "DHCP, meddelelser/samarbejde, backup osv.).",
                ar="الخدمات الأساسية التي توفّرها البنية التحتية التقنية (DNS، دليل، DHCP، "
                "المراسلة/التعاون، النسخ الاحتياطي، إلخ).",
            ),
        },
        "subtypes": [],
        "sort_order": 25,
        "fields_schema": [
            _section(
                "Infrastructure Service Details",
                _details_section_tx(),
                [
                    _MANUFACTURER(1),
                    _field(
                        "version",
                        "Version",
                        "text",
                        2,
                        _tx(
                            de="Version",
                            fr="Version",
                            es="Versión",
                            it="Versione",
                            pt="Versão",
                            zh="版本",
                            ru="Версия",
                            da="Version",
                            ar="الإصدار",
                        ),
                    ),
                    _field(
                        "function",
                        "Function",
                        "text",
                        3,
                        _tx(
                            de="Funktion",
                            fr="Fonction",
                            es="Función",
                            it="Funzione",
                            pt="Função",
                            zh="功能",
                            ru="Функция",
                            da="Funktion",
                            ar="الوظيفة",
                        ),
                    ),
                    _SUPPORT_END(4),
                    _SUPPORT_STATUS(5),
                    _OPERATION_TYPE(6),
                    *_cost_fields(20),
                ],
            ),
        ],
    },
    # 40 · Infrastructure Management Tool ---------------------------------
    {
        "key": "InfrastructureManagementTool",
        "label": "Infrastructure Management Tool",
        "description": "Tools or software used to manage, monitor, operate, or support technical "
        "infrastructure artifacts.",
        "icon": "monitoring",
        "color": "#d29270",
        "category": "Technology",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Infrastruktur-Management-Tool",
                fr="Outil de gestion d'infrastructure",
                es="Herramienta de gestión de infraestructura",
                it="Strumento di gestione dell'infrastruttura",
                pt="Ferramenta de gestão de infraestrutura",
                zh="基础设施管理工具",
                ru="Инструмент управления инфраструктурой",
                da="Værktøj til infrastrukturstyring",
                ar="أداة إدارة البنية التحتية",
            ),
            "description": _tx(
                de="Tools oder Software zum Verwalten, Überwachen, Betreiben oder Unterstützen "
                "von Artefakten der technischen Infrastruktur.",
                fr="Outils ou logiciels utilisés pour gérer, surveiller, exploiter ou soutenir "
                "les artefacts de l'infrastructure technique.",
                es="Herramientas o software usados para gestionar, supervisar, operar o dar "
                "soporte a los artefactos de la infraestructura técnica.",
                it="Strumenti o software usati per gestire, monitorare, operare o supportare gli "
                "artefatti dell'infrastruttura tecnica.",
                pt="Ferramentas ou software usados para gerir, monitorizar, operar ou apoiar os "
                "artefactos da infraestrutura técnica.",
                zh="用于管理、监控、运营或支持技术基础设施构件的工具或软件。",
                ru="Инструменты или ПО для управления, мониторинга, эксплуатации или поддержки "
                "артефактов технической инфраструктуры.",
                da="Værktøjer eller software til at administrere, overvåge, drive eller "
                "understøtte artefakter i den tekniske infrastruktur.",
                ar="أدوات أو برمجيات تُستخدم لإدارة أو مراقبة أو تشغيل أو دعم مكوّنات البنية "
                "التحتية التقنية.",
            ),
        },
        "subtypes": [],
        "sort_order": 26,
        "fields_schema": [
            _section(
                "Management Tool Details",
                _details_section_tx(),
                [
                    _MANUFACTURER(1),
                    _field(
                        "version",
                        "Version",
                        "text",
                        2,
                        _tx(
                            de="Version",
                            fr="Version",
                            es="Versión",
                            it="Versione",
                            pt="Versão",
                            zh="版本",
                            ru="Версия",
                            da="Version",
                            ar="الإصدار",
                        ),
                    ),
                    _field(
                        "function",
                        "Function",
                        "text",
                        3,
                        _tx(
                            de="Funktion",
                            fr="Fonction",
                            es="Función",
                            it="Funzione",
                            pt="Função",
                            zh="功能",
                            ru="Функция",
                            da="Funktion",
                            ar="الوظيفة",
                        ),
                    ),
                    _SUPPORT_END(4),
                    _SUPPORT_STATUS(5),
                    _OPERATION_TYPE(6),
                    *_cost_fields(20),
                ],
            ),
        ],
    },
    # 41 · Peripheral Device ----------------------------------------------
    {
        "key": "PeripheralDevice",
        "label": "Peripheral Device",
        "description": "Peripheral devices used at the entity, such as desktops, laptops, "
        "printers, and scanners.",
        "icon": "print",
        "color": "#d29270",
        "category": "Technology",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Peripheriegerät",
                fr="Périphérique",
                es="Dispositivo periférico",
                it="Dispositivo periferico",
                pt="Dispositivo periférico",
                zh="外围设备",
                ru="Периферийное устройство",
                da="Perifer enhed",
                ar="جهاز طرفي",
            ),
            "description": _tx(
                de="Peripheriegeräte der Organisation wie Desktops, Laptops, Drucker und Scanner.",
                fr="Périphériques utilisés par l'entité, tels qu'ordinateurs de bureau, portables, "
                "imprimantes et scanners.",
                es="Dispositivos periféricos usados en la entidad, como equipos de escritorio, "
                "portátiles, impresoras y escáneres.",
                it="Dispositivi periferici usati nell'ente, come desktop, laptop, stampanti e "
                "scanner.",
                pt="Dispositivos periféricos usados na entidade, como computadores de secretária, "
                "portáteis, impressoras e scanners.",
                zh="实体使用的外围设备，例如台式机、笔记本电脑、打印机和扫描仪。",
                ru="Периферийные устройства организации, такие как настольные компьютеры, "
                "ноутбуки, принтеры и сканеры.",
                da="Perifere enheder brugt hos enheden, såsom stationære pc'er, bærbare, "
                "printere og scannere.",
                ar="الأجهزة الطرفية المستخدمة في الجهة، مثل الحواسيب المكتبية والمحمولة "
                "والطابعات والماسحات الضوئية.",
            ),
        },
        "subtypes": [],
        "sort_order": 27,
        "fields_schema": [
            _section(
                "Peripheral Device Details",
                _details_section_tx(),
                [
                    _MANUFACTURER(1),
                    _MODEL(2),
                    _field(
                        "location",
                        "Location",
                        "text",
                        3,
                        _tx(
                            de="Standort",
                            fr="Emplacement",
                            es="Ubicación",
                            it="Posizione",
                            pt="Localização",
                            zh="位置",
                            ru="Местоположение",
                            da="Placering",
                            ar="الموقع",
                        ),
                    ),
                    _field(
                        "function",
                        "Function",
                        "text",
                        4,
                        _tx(
                            de="Funktion",
                            fr="Fonction",
                            es="Función",
                            it="Funzione",
                            pt="Função",
                            zh="功能",
                            ru="Функция",
                            da="Funktion",
                            ar="الوظيفة",
                        ),
                    ),
                    _field(
                        "operatingSystemOrFirmware",
                        "Operating System or Firmware",
                        "text",
                        5,
                        _tx(
                            de="Betriebssystem oder Firmware",
                            fr="Système d'exploitation ou firmware",
                            es="Sistema operativo o firmware",
                            it="Sistema operativo o firmware",
                            pt="Sistema operativo ou firmware",
                            zh="操作系统或固件",
                            ru="Операционная система или прошивка",
                            da="Operativsystem eller firmware",
                            ar="نظام التشغيل أو البرنامج الثابت",
                        ),
                    ),
                    _SUPPORT_END(6),
                    _SUPPORT_STATUS(7),
                    _OPERATION_TYPE(8),
                    *_cost_fields(20),
                ],
            ),
        ],
    },
    # 42 · License ---------------------------------------------------------
    {
        "key": "License",
        "label": "License",
        "description": "Usage agreements for hardware or software purchased from suppliers or "
        "manufacturers (permanent licenses and subscriptions).",
        "icon": "receipt_long",
        "color": "#d29270",
        "category": "Technology",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Lizenz",
                fr="Licence",
                es="Licencia",
                it="Licenza",
                pt="Licença",
                zh="许可证",
                ru="Лицензия",
                da="Licens",
                ar="ترخيص",
            ),
            "description": _tx(
                de="Nutzungsvereinbarungen für Hardware oder Software von Lieferanten oder "
                "Herstellern (Dauerlizenzen und Abonnements).",
                fr="Accords d'utilisation de matériel ou de logiciel achetés auprès de "
                "fournisseurs ou fabricants (licences permanentes et abonnements).",
                es="Acuerdos de uso de hardware o software adquiridos a proveedores o fabricantes "
                "(licencias permanentes y suscripciones).",
                it="Accordi di utilizzo per hardware o software acquistati da fornitori o "
                "produttori (licenze permanenti e abbonamenti).",
                pt="Acordos de utilização de hardware ou software adquiridos a fornecedores ou "
                "fabricantes (licenças permanentes e subscrições).",
                zh="从供应商或制造商购买的硬件或软件使用协议（永久许可证和订阅）。",
                ru="Соглашения об использовании оборудования или ПО, приобретённых у поставщиков "
                "или производителей (постоянные лицензии и подписки).",
                da="Brugsaftaler for hardware eller software købt fra leverandører eller "
                "producenter (permanente licenser og abonnementer).",
                ar="اتفاقيات استخدام للعتاد أو البرمجيات المُشتراة من المورّدين أو المصنّعين "
                "(تراخيص دائمة واشتراكات).",
            ),
        },
        "subtypes": [],
        "sort_order": 28,
        "fields_schema": [
            _section(
                "License Details",
                _details_section_tx(),
                [
                    _MANUFACTURER(1),
                    _field(
                        "quantity",
                        "Quantity",
                        "number",
                        2,
                        _tx(
                            de="Anzahl",
                            fr="Quantité",
                            es="Cantidad",
                            it="Quantità",
                            pt="Quantidade",
                            zh="数量",
                            ru="Количество",
                            da="Antal",
                            ar="الكمية",
                        ),
                    ),
                    _field(
                        "licenseType",
                        "Type",
                        "text",
                        3,
                        _tx(
                            de="Typ",
                            fr="Type",
                            es="Tipo",
                            it="Tipo",
                            pt="Tipo",
                            zh="类型",
                            ru="Тип",
                            da="Type",
                            ar="النوع",
                        ),
                    ),
                    _field(
                        "dateOfObtaining",
                        "Date of Obtaining",
                        "date",
                        4,
                        _tx(
                            de="Erwerbsdatum",
                            fr="Date d'obtention",
                            es="Fecha de obtención",
                            it="Data di acquisizione",
                            pt="Data de obtenção",
                            zh="获得日期",
                            ru="Дата получения",
                            da="Anskaffelsesdato",
                            ar="تاريخ الحصول",
                        ),
                    ),
                    _field(
                        "expiryDate",
                        "Expiry Date",
                        "date",
                        5,
                        _tx(
                            de="Ablaufdatum",
                            fr="Date d'expiration",
                            es="Fecha de caducidad",
                            it="Data di scadenza",
                            pt="Data de validade",
                            zh="到期日期",
                            ru="Дата окончания срока",
                            da="Udløbsdato",
                            ar="تاريخ الانتهاء",
                        ),
                    ),
                    *_cost_fields(20),
                ],
            ),
        ],
    },
]
