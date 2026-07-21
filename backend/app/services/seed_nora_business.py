"""NORA Content Meta Model — Business Architecture building blocks (split types).

[FORK] NORA exact-fidelity metamodel (noraPlanMeta.md, Phase 1B).

The National EA Framework "EA Content Meta Model" document (§5.3.2) treats
**Organizational Unit** (§5.3.2.2.2) and **Service Provider** (§5.3.2.2.3) as
their own independent building blocks. The stock tool overloaded them onto the
generic ``Organization`` / ``Provider`` types. This module restores them as
first-class NORA-native card types.

The generic ``Organization`` / ``Provider`` types are left in place for now and
hidden when the NORA profile is active (Phase 3); NORA-native relations point at
these new keys.

Appended onto ``seed.TYPES``; reuses the i18n helpers from
``seed_nora_technology`` (``_tx`` / ``_field`` / ``_section``).
"""

from __future__ import annotations

from app.services.seed_nora_technology import _field, _section, _tx

# ---------------------------------------------------------------------------
# Select-option constants
# ---------------------------------------------------------------------------

_ORG_UNIT_TYPE_OPTIONS = [
    {
        "key": "ministry",
        "label": "Ministry",
        "translations": _tx(
            de="Ministerium",
            fr="Ministère",
            es="Ministerio",
            it="Ministero",
            pt="Ministério",
            zh="部",
            ru="Министерство",
            da="Ministerium",
            ar="وزارة",
        ),
    },
    {
        "key": "authority",
        "label": "Authority",
        "translations": _tx(
            de="Behörde",
            fr="Autorité",
            es="Autoridad",
            it="Autorità",
            pt="Autoridade",
            zh="管理局",
            ru="Управление",
            da="Myndighed",
            ar="هيئة",
        ),
    },
    {
        "key": "agency",
        "label": "Agency",
        "translations": _tx(
            de="Agentur",
            fr="Agence",
            es="Agencia",
            it="Agenzia",
            pt="Agência",
            zh="机构",
            ru="Агентство",
            da="Agentur",
            ar="وكالة",
        ),
    },
    {
        "key": "sector",
        "label": "Sector",
        "translations": _tx(
            de="Sektor",
            fr="Secteur",
            es="Sector",
            it="Settore",
            pt="Setor",
            zh="部门",
            ru="Сектор",
            da="Sektor",
            ar="قطاع",
        ),
    },
    {
        "key": "publicAdministration",
        "label": "Public Administration",
        "translations": _tx(
            de="Öffentliche Verwaltung",
            fr="Administration publique",
            es="Administración pública",
            it="Pubblica amministrazione",
            pt="Administração pública",
            zh="公共管理",
            ru="Государственное управление",
            da="Offentlig administration",
            ar="إدارة عامة",
        ),
    },
    {
        "key": "department",
        "label": "Department",
        "translations": _tx(
            de="Abteilung",
            fr="Département",
            es="Departamento",
            it="Dipartimento",
            pt="Departamento",
            zh="部门",
            ru="Департамент",
            da="Afdeling",
            ar="إدارة",
        ),
    },
]

_PROVIDER_STATUS_OPTIONS = [
    {
        "key": "active",
        "label": "Active",
        "translations": _tx(
            de="Aktiv",
            fr="Actif",
            es="Activo",
            it="Attivo",
            pt="Ativo",
            zh="活跃",
            ru="Активен",
            da="Aktiv",
            ar="نشط",
        ),
    },
    {
        "key": "inactive",
        "label": "Inactive",
        "translations": _tx(
            de="Inaktiv",
            fr="Inactif",
            es="Inactivo",
            it="Inattivo",
            pt="Inativo",
            zh="非活跃",
            ru="Неактивен",
            da="Inaktiv",
            ar="غير نشط",
        ),
    },
]

_CONTRACT_RELATIONSHIP_OPTIONS = [
    {
        "key": "externalPartner",
        "label": "External Partner",
        "translations": _tx(
            de="Externer Partner",
            fr="Partenaire externe",
            es="Socio externo",
            it="Partner esterno",
            pt="Parceiro externo",
            zh="外部合作伙伴",
            ru="Внешний партнёр",
            da="Ekstern partner",
            ar="شريك خارجي",
        ),
    },
    {
        "key": "authorizedProvider",
        "label": "Authorized Service Provider",
        "translations": _tx(
            de="Autorisierter Dienstleister",
            fr="Prestataire agréé",
            es="Proveedor autorizado",
            it="Fornitore autorizzato",
            pt="Prestador autorizado",
            zh="授权服务提供商",
            ru="Авторизованный поставщик",
            da="Autoriseret udbyder",
            ar="مزود خدمة معتمد",
        ),
    },
    {
        "key": "serviceProvider",
        "label": "Service Provider",
        "translations": _tx(
            de="Dienstleister",
            fr="Prestataire de services",
            es="Proveedor de servicios",
            it="Fornitore di servizi",
            pt="Prestador de serviços",
            zh="服务提供商",
            ru="Поставщик услуг",
            da="Serviceudbyder",
            ar="مزود خدمة",
        ),
    },
    {
        "key": "techProvider",
        "label": "Technical Solutions & Hardware Provider",
        "translations": _tx(
            de="Anbieter technischer Lösungen und Hardware",
            fr="Fournisseur de solutions techniques et matériel",
            es="Proveedor de soluciones técnicas y hardware",
            it="Fornitore di soluzioni tecniche e hardware",
            pt="Fornecedor de soluções técnicas e hardware",
            zh="技术解决方案与硬件提供商",
            ru="Поставщик технических решений и оборудования",
            da="Leverandør af tekniske løsninger og hardware",
            ar="مزود الحلول التقنية والأجهزة",
        ),
    },
    {
        "key": "securityProvider",
        "label": "Security Solutions & Hardware Provider",
        "translations": _tx(
            de="Anbieter von Sicherheitslösungen und Hardware",
            fr="Fournisseur de solutions de sécurité et matériel",
            es="Proveedor de soluciones de seguridad y hardware",
            it="Fornitore di soluzioni di sicurezza e hardware",
            pt="Fornecedor de soluções de segurança e hardware",
            zh="安全解决方案与硬件提供商",
            ru="Поставщик решений безопасности и оборудования",
            da="Leverandør af sikkerhedsløsninger og hardware",
            ar="مزود الحلول الأمنية والأجهزة",
        ),
    },
]

_PROCESS_GROUP_TYPE_OPTIONS = [
    {
        "key": "core",
        "label": "Core",
        "translations": _tx(
            de="Kern",
            fr="Cœur de métier",
            es="Principal",
            it="Principale",
            pt="Principal",
            zh="核心",
            ru="Основной",
            da="Kerne",
            ar="أساسي",
        ),
    },
    {
        "key": "administrative",
        "label": "Administrative",
        "translations": _tx(
            de="Administrativ",
            fr="Administratif",
            es="Administrativo",
            it="Amministrativo",
            pt="Administrativo",
            zh="行政",
            ru="Административный",
            da="Administrativ",
            ar="إداري",
        ),
    },
    {
        "key": "supporting",
        "label": "Supporting",
        "translations": _tx(
            de="Unterstützend",
            fr="De soutien",
            es="De apoyo",
            it="Di supporto",
            pt="De apoio",
            zh="支持",
            ru="Поддерживающий",
            da="Understøttende",
            ar="مساند",
        ),
    },
]

_ROLE_TYPE_OPTIONS = [
    {
        "key": "core",
        "label": "Core Role",
        "translations": _tx(
            de="Kernrolle",
            fr="Rôle principal",
            es="Rol principal",
            it="Ruolo principale",
            pt="Função principal",
            zh="核心角色",
            ru="Основная роль",
            da="Kernerolle",
            ar="دور أساسي",
        ),
    },
    {
        "key": "supporting",
        "label": "Supporting Role",
        "translations": _tx(
            de="Unterstützende Rolle",
            fr="Rôle de soutien",
            es="Rol de apoyo",
            it="Ruolo di supporto",
            pt="Função de apoio",
            zh="支持角色",
            ru="Поддерживающая роль",
            da="Understøttende rolle",
            ar="دور مساند",
        ),
    },
]

_AUTOMATION_LEVEL_OPTIONS = [
    {
        "key": "fullyAutomated",
        "label": "Fully Automated",
        "translations": _tx(
            de="Vollständig automatisiert",
            fr="Entièrement automatisé",
            es="Totalmente automatizado",
            it="Completamente automatizzato",
            pt="Totalmente automatizado",
            zh="完全自动化",
            ru="Полностью автоматизирован",
            da="Fuldt automatiseret",
            ar="مؤتمت بالكامل",
        ),
    },
    {
        "key": "partiallyAutomated",
        "label": "Partially Automated",
        "translations": _tx(
            de="Teilweise automatisiert",
            fr="Partiellement automatisé",
            es="Parcialmente automatizado",
            it="Parzialmente automatizzato",
            pt="Parcialmente automatizado",
            zh="部分自动化",
            ru="Частично автоматизирован",
            da="Delvist automatiseret",
            ar="مؤتمت جزئيًا",
        ),
    },
    {
        "key": "manual",
        "label": "Manual",
        "translations": _tx(
            de="Manuell",
            fr="Manuel",
            es="Manual",
            it="Manuale",
            pt="Manual",
            zh="手动",
            ru="Вручную",
            da="Manuel",
            ar="يدوي",
        ),
    },
]

_PRODUCT_TYPE_OPTIONS = [
    {
        "key": "physical",
        "label": "Physical Product",
        "translations": _tx(
            de="Physisches Produkt",
            fr="Produit physique",
            es="Producto físico",
            it="Prodotto fisico",
            pt="Produto físico",
            zh="实物产品",
            ru="Физический продукт",
            da="Fysisk produkt",
            ar="منتج مادي",
        ),
    },
    {
        "key": "technical",
        "label": "Technical Product",
        "translations": _tx(
            de="Technisches Produkt",
            fr="Produit technique",
            es="Producto técnico",
            it="Prodotto tecnico",
            pt="Produto técnico",
            zh="技术产品",
            ru="Технический продукт",
            da="Teknisk produkt",
            ar="منتج تقني",
        ),
    },
    {
        "key": "document",
        "label": "Document",
        "translations": _tx(
            de="Dokument",
            fr="Document",
            es="Documento",
            it="Documento",
            pt="Documento",
            zh="文档",
            ru="Документ",
            da="Dokument",
            ar="مستند",
        ),
    },
]

# ---------------------------------------------------------------------------
# The split + net-new Business Architecture building blocks
# ---------------------------------------------------------------------------

NORA_BUSINESS_TYPES: list[dict] = [
    # 9 · Organizational Unit ---------------------------------------------
    {
        "key": "OrganizationalUnit",
        "label": "Organizational Unit",
        "description": "Part of the entity's organizational structure with specific mandates; "
        "may consist of sub-organizational units.",
        "icon": "account_tree",
        "color": "#2889ff",
        "category": "Business",
        "has_hierarchy": True,
        "translations": {
            "label": _tx(
                de="Organisationseinheit",
                fr="Unité organisationnelle",
                es="Unidad organizativa",
                it="Unità organizzativa",
                pt="Unidade organizacional",
                zh="组织单元",
                ru="Организационная единица",
                da="Organisatorisk enhed",
                ar="وحدة تنظيمية",
            ),
            "description": _tx(
                de="Teil der Organisationsstruktur der Entität mit spezifischen Mandaten; kann "
                "aus Untereinheiten bestehen.",
                fr="Partie de la structure organisationnelle de l'entité avec des mandats "
                "spécifiques ; peut comprendre des sous-unités.",
                es="Parte de la estructura organizativa de la entidad con mandatos específicos; "
                "puede constar de subunidades.",
                it="Parte della struttura organizzativa dell'ente con mandati specifici; può "
                "essere composta da sotto-unità.",
                pt="Parte da estrutura organizacional da entidade com mandatos específicos; pode "
                "consistir em subunidades.",
                zh="实体组织结构的一部分，具有特定职责；可由子组织单元组成。",
                ru="Часть организационной структуры организации с определёнными полномочиями; "
                "может состоять из подразделений.",
                da="Del af enhedens organisatoriske struktur med specifikke mandater; kan bestå "
                "af underenheder.",
                ar="جزء من الهيكل التنظيمي للجهة له صلاحيات محددة؛ وقد يتكوّن من وحدات فرعية.",
            ),
        },
        "subtypes": [],
        "sort_order": 8,
        "fields_schema": [
            _section(
                "Organizational Unit Details",
                _tx(
                    de="Details der Organisationseinheit",
                    fr="Détails de l'unité organisationnelle",
                    es="Detalles de la unidad organizativa",
                    it="Dettagli dell'unità organizzativa",
                    pt="Detalhes da unidade organizacional",
                    zh="组织单元详情",
                    ru="Сведения об организационной единице",
                    da="Detaljer om organisatorisk enhed",
                    ar="تفاصيل الوحدة التنظيمية",
                ),
                [
                    _field(
                        "unitType",
                        "Type",
                        "single_select",
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
                        options=_ORG_UNIT_TYPE_OPTIONS,
                    ),
                    _field(
                        "organizationalDependency",
                        "Organizational Dependency",
                        "text",
                        1,
                        _tx(
                            de="Organisatorische Zugehörigkeit",
                            fr="Dépendance organisationnelle",
                            es="Dependencia organizativa",
                            it="Dipendenza organizzativa",
                            pt="Dependência organizacional",
                            zh="组织隶属关系",
                            ru="Организационная подчинённость",
                            da="Organisatorisk afhængighed",
                            ar="التبعية التنظيمية",
                        ),
                    ),
                    _field(
                        "mandates",
                        "Mandates",
                        "text",
                        1,
                        _tx(
                            de="Mandate",
                            fr="Mandats",
                            es="Mandatos",
                            it="Mandati",
                            pt="Mandatos",
                            zh="职责",
                            ru="Полномочия",
                            da="Mandater",
                            ar="الصلاحيات",
                        ),
                    ),
                    _field(
                        "geographicLocation",
                        "Geographic Location",
                        "text",
                        1,
                        _tx(
                            de="Geografischer Standort",
                            fr="Emplacement géographique",
                            es="Ubicación geográfica",
                            it="Posizione geografica",
                            pt="Localização geográfica",
                            zh="地理位置",
                            ru="Географическое расположение",
                            da="Geografisk placering",
                            ar="الموقع الجغرافي",
                        ),
                    ),
                ],
            ),
        ],
    },
    # 10 · Service Provider -----------------------------------------------
    {
        "key": "ServiceProvider",
        "label": "Service Provider",
        "description": "External entity or individual participating in the execution of the "
        "entity's business or services under a joint agreement.",
        "icon": "handshake",
        "color": "#ffa31f",
        "category": "Business",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Dienstleister",
                fr="Prestataire de services",
                es="Proveedor de servicios",
                it="Fornitore di servizi",
                pt="Prestador de serviços",
                zh="服务提供商",
                ru="Поставщик услуг",
                da="Serviceudbyder",
                ar="مزود الخدمة",
            ),
            "description": _tx(
                de="Externe Entität oder Person, die an der Ausführung der Geschäfte oder "
                "Dienste der Entität im Rahmen einer gemeinsamen Vereinbarung beteiligt ist.",
                fr="Entité ou personne externe participant à l'exécution des activités ou "
                "services de l'entité dans le cadre d'un accord conjoint.",
                es="Entidad o persona externa que participa en la ejecución del negocio o los "
                "servicios de la entidad bajo un acuerdo conjunto.",
                it="Entità o individuo esterno che partecipa all'esecuzione delle attività o dei "
                "servizi dell'ente nell'ambito di un accordo congiunto.",
                pt="Entidade ou indivíduo externo que participa na execução do negócio ou "
                "serviços da entidade ao abrigo de um acordo conjunto.",
                zh="根据联合协议参与实体业务或服务执行的外部实体或个人。",
                ru="Внешняя организация или лицо, участвующее в выполнении деятельности или услуг "
                "организации в рамках совместного соглашения.",
                da="Ekstern enhed eller person, der deltager i udførelsen af enhedens "
                "forretning eller tjenester under en fælles aftale.",
                ar="جهة أو فرد خارجي يشارك في تنفيذ أعمال الجهة أو خدماتها بموجب اتفاقية مشتركة.",
            ),
        },
        "subtypes": [],
        "sort_order": 9,
        "fields_schema": [
            _section(
                "Service Provider Details",
                _tx(
                    de="Details des Dienstleisters",
                    fr="Détails du prestataire",
                    es="Detalles del proveedor",
                    it="Dettagli del fornitore",
                    pt="Detalhes do prestador",
                    zh="服务提供商详情",
                    ru="Сведения о поставщике",
                    da="Detaljer om serviceudbyder",
                    ar="تفاصيل مزود الخدمة",
                ),
                [
                    _field(
                        "contractualRelationship",
                        "Type of Contractual Relationship",
                        "single_select",
                        3,
                        _tx(
                            de="Art der Vertragsbeziehung",
                            fr="Type de relation contractuelle",
                            es="Tipo de relación contractual",
                            it="Tipo di relazione contrattuale",
                            pt="Tipo de relação contratual",
                            zh="合同关系类型",
                            ru="Тип договорных отношений",
                            da="Type af kontraktforhold",
                            ar="نوع العلاقة التعاقدية",
                        ),
                        options=_CONTRACT_RELATIONSHIP_OPTIONS,
                    ),
                    _field(
                        "servicesProvided",
                        "Services Provided",
                        "text",
                        1,
                        _tx(
                            de="Erbrachte Leistungen",
                            fr="Services fournis",
                            es="Servicios prestados",
                            it="Servizi forniti",
                            pt="Serviços prestados",
                            zh="所提供的服务",
                            ru="Предоставляемые услуги",
                            da="Leverede tjenester",
                            ar="الخدمات المقدَّمة",
                        ),
                    ),
                    _field(
                        "providerStatus",
                        "Service Provider Status",
                        "single_select",
                        1,
                        _tx(
                            de="Status des Dienstleisters",
                            fr="Statut du prestataire",
                            es="Estado del proveedor",
                            it="Stato del fornitore",
                            pt="Estado do prestador",
                            zh="服务提供商状态",
                            ru="Статус поставщика",
                            da="Serviceudbyderstatus",
                            ar="حالة مزود الخدمة",
                        ),
                        options=_PROVIDER_STATUS_OPTIONS,
                    ),
                    _field(
                        "complianceCertifications",
                        "Compliance and Certifications",
                        "text",
                        1,
                        _tx(
                            de="Compliance und Zertifizierungen",
                            fr="Conformité et certifications",
                            es="Cumplimiento y certificaciones",
                            it="Conformità e certificazioni",
                            pt="Conformidade e certificações",
                            zh="合规与认证",
                            ru="Соответствие и сертификаты",
                            da="Overholdelse og certificeringer",
                            ar="الامتثال والشهادات",
                        ),
                    ),
                    _field(
                        "fieldOfActivity",
                        "Field of Activity",
                        "text",
                        1,
                        _tx(
                            de="Tätigkeitsbereich",
                            fr="Domaine d'activité",
                            es="Campo de actividad",
                            it="Campo di attività",
                            pt="Área de atividade",
                            zh="活动领域",
                            ru="Сфера деятельности",
                            da="Aktivitetsområde",
                            ar="مجال النشاط",
                        ),
                    ),
                    _field(
                        "relationshipStatus",
                        "Relationship Status",
                        "text",
                        1,
                        _tx(
                            de="Beziehungsstatus",
                            fr="Statut de la relation",
                            es="Estado de la relación",
                            it="Stato della relazione",
                            pt="Estado da relação",
                            zh="关系状态",
                            ru="Статус отношений",
                            da="Relationsstatus",
                            ar="حالة العلاقة",
                        ),
                    ),
                    _field(
                        "geographicLocation",
                        "Geographic Location",
                        "text",
                        1,
                        _tx(
                            de="Geografischer Standort",
                            fr="Emplacement géographique",
                            es="Ubicación geográfica",
                            it="Posizione geografica",
                            pt="Localização geográfica",
                            zh="地理位置",
                            ru="Географическое расположение",
                            da="Geografisk placering",
                            ar="الموقع الجغرافي",
                        ),
                    ),
                ],
            ),
        ],
    },
    # 12 · Processes Group ------------------------------------------------
    {
        "key": "ProcessesGroup",
        "label": "Processes Group",
        "description": "Logical set of interrelated business processes serving one or more "
        "specific business capabilities.",
        "icon": "account_tree",
        "color": "#028f00",
        "category": "Business",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Prozessgruppe",
                fr="Groupe de processus",
                es="Grupo de procesos",
                it="Gruppo di processi",
                pt="Grupo de processos",
                zh="流程组",
                ru="Группа процессов",
                da="Procesgruppe",
                ar="مجموعة العمليات",
            ),
            "description": _tx(
                de="Logische Gruppe zusammenhängender Geschäftsprozesse, die eine oder mehrere "
                "bestimmte Geschäftsfähigkeiten bedienen.",
                fr="Ensemble logique de processus métier interdépendants servant une ou plusieurs "
                "capacités métier spécifiques.",
                es="Conjunto lógico de procesos de negocio interrelacionados que sirven a una o "
                "más capacidades de negocio específicas.",
                it="Insieme logico di processi aziendali interconnessi al servizio di una o più "
                "capacità aziendali specifiche.",
                pt="Conjunto lógico de processos de negócio inter-relacionados que servem uma ou "
                "mais capacidades de negócio específicas.",
                zh="服务于一个或多个特定业务能力的相互关联业务流程的逻辑集合。",
                ru="Логический набор взаимосвязанных бизнес-процессов, обслуживающих одну или "
                "несколько конкретных бизнес-способностей.",
                da="Logisk sæt af indbyrdes forbundne forretningsprocesser, der betjener en eller "
                "flere specifikke forretningsevner.",
                ar="مجموعة منطقية من عمليات الأعمال المترابطة التي تخدم قدرة أعمال محددة أو أكثر.",
            ),
        },
        "subtypes": [],
        "sort_order": 12,
        "fields_schema": [
            _section(
                "Processes Group Details",
                _tx(
                    de="Details der Prozessgruppe",
                    fr="Détails du groupe de processus",
                    es="Detalles del grupo de procesos",
                    it="Dettagli del gruppo di processi",
                    pt="Detalhes do grupo de processos",
                    zh="流程组详情",
                    ru="Сведения о группе процессов",
                    da="Detaljer om procesgruppe",
                    ar="تفاصيل مجموعة العمليات",
                ),
                [
                    _field(
                        "groupType",
                        "Type",
                        "single_select",
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
                        options=_PROCESS_GROUP_TYPE_OPTIONS,
                    ),
                ],
            ),
        ],
    },
    # 16 · Role -----------------------------------------------------------
    {
        "key": "Role",
        "label": "Role",
        "description": "Behavior a specific position embodies when contributing to a process or "
        "service; a position can hold several roles.",
        "icon": "badge",
        "color": "#2889ff",
        "category": "Business",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
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
            "description": _tx(
                de="Verhalten, das eine bestimmte Position verkörpert, wenn sie zu einem Prozess "
                "oder Dienst beiträgt; eine Position kann mehrere Rollen innehaben.",
                fr="Comportement qu'un poste incarne lorsqu'il contribue à un processus ou un "
                "service ; un poste peut avoir plusieurs rôles.",
                es="Comportamiento que un puesto encarna al contribuir a un proceso o servicio; "
                "un puesto puede tener varios roles.",
                it="Comportamento che una posizione incarna quando contribuisce a un processo o "
                "servizio; una posizione può avere più ruoli.",
                pt="Comportamento que um cargo incorpora ao contribuir para um processo ou "
                "serviço; um cargo pode ter vários papéis.",
                zh="某职位在参与某流程或服务时所体现的行为；一个职位可拥有多个角色。",
                ru="Поведение, которое воплощает конкретная должность при участии в процессе или "
                "услуге; должность может иметь несколько ролей.",
                da="Adfærd, som en bestemt stilling udmønter, når den bidrager til en proces "
                "eller tjeneste; en stilling kan have flere roller.",
                ar="السلوك الذي يجسّده منصب معيّن عند مساهمته في عملية أو خدمة؛ ويمكن أن يحمل "
                "المنصب عدة أدوار.",
            ),
        },
        "subtypes": [],
        "sort_order": 16,
        "fields_schema": [
            _section(
                "Role Details",
                _tx(
                    de="Rollendetails",
                    fr="Détails du rôle",
                    es="Detalles del rol",
                    it="Dettagli del ruolo",
                    pt="Detalhes da função",
                    zh="角色详情",
                    ru="Сведения о роли",
                    da="Rolledetaljer",
                    ar="تفاصيل الدور",
                ),
                [
                    _field(
                        "roleType",
                        "Role Type",
                        "single_select",
                        3,
                        _tx(
                            de="Rollentyp",
                            fr="Type de rôle",
                            es="Tipo de rol",
                            it="Tipo di ruolo",
                            pt="Tipo de função",
                            zh="角色类型",
                            ru="Тип роли",
                            da="Rolletype",
                            ar="نوع الدور",
                        ),
                        options=_ROLE_TYPE_OPTIONS,
                    ),
                ],
            ),
        ],
    },
    # 19 · Activity -------------------------------------------------------
    {
        "key": "Activity",
        "label": "Activity",
        "description": "Details the mechanism for executing a specific business process.",
        "icon": "checklist",
        "color": "#028f00",
        "category": "Business",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Aktivität",
                fr="Activité",
                es="Actividad",
                it="Attività",
                pt="Atividade",
                zh="活动",
                ru="Действие",
                da="Aktivitet",
                ar="نشاط",
            ),
            "description": _tx(
                de="Beschreibt den Mechanismus zur Ausführung eines bestimmten Geschäftsprozesses.",
                fr="Détaille le mécanisme d'exécution d'un processus métier spécifique.",
                es="Detalla el mecanismo para ejecutar un proceso de negocio específico.",
                it="Descrive il meccanismo di esecuzione di uno specifico processo aziendale.",
                pt="Detalha o mecanismo de execução de um processo de negócio específico.",
                zh="详细说明执行特定业务流程的机制。",
                ru="Описывает механизм выполнения конкретного бизнес-процесса.",
                da="Beskriver mekanismen for udførelse af en bestemt forretningsproces.",
                ar="يوضّح آلية تنفيذ عملية أعمال محددة.",
            ),
        },
        "subtypes": [],
        "sort_order": 19,
        "fields_schema": [
            _section(
                "Activity Details",
                _tx(
                    de="Aktivitätsdetails",
                    fr="Détails de l'activité",
                    es="Detalles de la actividad",
                    it="Dettagli dell'attività",
                    pt="Detalhes da atividade",
                    zh="活动详情",
                    ru="Сведения о действии",
                    da="Aktivitetsdetaljer",
                    ar="تفاصيل النشاط",
                ),
                [
                    _field(
                        "timeline",
                        "Agreed Timeline",
                        "text",
                        1,
                        _tx(
                            de="Vereinbarter Zeitrahmen",
                            fr="Délai convenu",
                            es="Plazo acordado",
                            it="Tempistica concordata",
                            pt="Prazo acordado",
                            zh="约定时限",
                            ru="Согласованный срок",
                            da="Aftalt tidsramme",
                            ar="الجدول الزمني المتفق عليه",
                        ),
                    ),
                    _field(
                        "activityInputs",
                        "Activity Inputs",
                        "text",
                        1,
                        _tx(
                            de="Aktivitätseingaben",
                            fr="Intrants de l'activité",
                            es="Entradas de la actividad",
                            it="Input dell'attività",
                            pt="Entradas da atividade",
                            zh="活动输入",
                            ru="Входы действия",
                            da="Aktivitetsinput",
                            ar="مدخلات النشاط",
                        ),
                    ),
                    _field(
                        "activityDeliverables",
                        "Activity Deliverables",
                        "text",
                        1,
                        _tx(
                            de="Aktivitätsergebnisse",
                            fr="Livrables de l'activité",
                            es="Entregables de la actividad",
                            it="Deliverable dell'attività",
                            pt="Entregáveis da atividade",
                            zh="活动交付物",
                            ru="Результаты действия",
                            da="Aktivitetsleverancer",
                            ar="مخرجات النشاط",
                        ),
                    ),
                    _field(
                        "automationLevel",
                        "Automation Level",
                        "single_select",
                        1,
                        _tx(
                            de="Automatisierungsgrad",
                            fr="Niveau d'automatisation",
                            es="Nivel de automatización",
                            it="Livello di automazione",
                            pt="Nível de automação",
                            zh="自动化程度",
                            ru="Уровень автоматизации",
                            da="Automatiseringsniveau",
                            ar="مستوى الأتمتة",
                        ),
                        options=_AUTOMATION_LEVEL_OPTIONS,
                    ),
                ],
            ),
        ],
    },
    # 14 · Product --------------------------------------------------------
    {
        "key": "Product",
        "label": "Product",
        "description": "Final deliverable resulting from successfully executing an activity or "
        "providing a service; may be a tangible or digital commodity.",
        "icon": "inventory_2",
        "color": "#fe6690",
        "category": "Business",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Produkt",
                fr="Produit",
                es="Producto",
                it="Prodotto",
                pt="Produto",
                zh="产品",
                ru="Продукт",
                da="Produkt",
                ar="منتج",
            ),
            "description": _tx(
                de="Endergebnis aus der erfolgreichen Ausführung einer Aktivität oder der "
                "Erbringung eines Dienstes; kann ein materielles oder digitales Gut sein.",
                fr="Livrable final résultant de l'exécution réussie d'une activité ou de la "
                "fourniture d'un service ; peut être un bien matériel ou numérique.",
                es="Entregable final resultante de ejecutar con éxito una actividad o prestar un "
                "servicio; puede ser un bien tangible o digital.",
                it="Deliverable finale risultante dall'esecuzione riuscita di un'attività o "
                "dalla fornitura di un servizio; può essere un bene tangibile o digitale.",
                pt="Entregável final resultante da execução bem-sucedida de uma atividade ou da "
                "prestação de um serviço; pode ser um bem tangível ou digital.",
                zh="成功执行某项活动或提供某项服务所产生的最终交付物；可以是有形或数字化商品。",
                ru="Итоговый результат успешного выполнения действия или предоставления услуги; "
                "может быть материальным или цифровым товаром.",
                da="Endelig leverance som resultat af en vellykket aktivitet eller levering af "
                "en tjeneste; kan være en håndgribelig eller digital vare.",
                ar="المخرَج النهائي الناتج عن تنفيذ نشاط بنجاح أو تقديم خدمة؛ وقد يكون سلعة "
                "ملموسة أو رقمية.",
            ),
        },
        "subtypes": [],
        "sort_order": 14,
        "fields_schema": [
            _section(
                "Product Details",
                _tx(
                    de="Produktdetails",
                    fr="Détails du produit",
                    es="Detalles del producto",
                    it="Dettagli del prodotto",
                    pt="Detalhes do produto",
                    zh="产品详情",
                    ru="Сведения о продукте",
                    da="Produktdetaljer",
                    ar="تفاصيل المنتج",
                ),
                [
                    _field(
                        "productType",
                        "Product Type",
                        "single_select",
                        3,
                        _tx(
                            de="Produkttyp",
                            fr="Type de produit",
                            es="Tipo de producto",
                            it="Tipo di prodotto",
                            pt="Tipo de produto",
                            zh="产品类型",
                            ru="Тип продукта",
                            da="Produkttype",
                            ar="نوع المنتج",
                        ),
                        options=_PRODUCT_TYPE_OPTIONS,
                    ),
                    _field(
                        "productOwner",
                        "Product Owner",
                        "text",
                        1,
                        _tx(
                            de="Produkteigner",
                            fr="Propriétaire du produit",
                            es="Propietario del producto",
                            it="Titolare del prodotto",
                            pt="Proprietário do produto",
                            zh="产品负责人",
                            ru="Владелец продукта",
                            da="Produktejer",
                            ar="مالك المنتج",
                        ),
                    ),
                    _field(
                        "beneficiary",
                        "Beneficiary",
                        "text",
                        1,
                        _tx(
                            de="Begünstigter",
                            fr="Bénéficiaire",
                            es="Beneficiario",
                            it="Beneficiario",
                            pt="Beneficiário",
                            zh="受益人",
                            ru="Бенефициар",
                            da="Modtager",
                            ar="المستفيد",
                        ),
                    ),
                ],
            ),
        ],
    },
]
