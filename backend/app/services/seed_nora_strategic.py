"""NORA Content Meta Model — Strategic Alignment building blocks.

[FORK] NORA exact-fidelity metamodel (noraPlanMeta.md, Phase 1A).

The National EA Framework "EA Content Meta Model" document (§5.3.1) defines the
Strategic Alignment domain as 7 **independent** building blocks:

    Vision, Mission, Objective, Pillar, Initiative, Project, Key Performance Indicator

Already present in the seeded metamodel: ``Objective``, ``Pillar``, ``Initiative``
(``seed.TYPES``) and ``KPI`` (created by ``nora_profile`` on profile activation).
This module adds the remaining three as first-class card types:

    Vision, Mission, Project

Appended onto ``seed.TYPES`` so the standard seed insert/merge loop and
``test_i18n_seed`` pick them up. Reuses the i18n helpers from
``seed_nora_technology`` (``_tx`` / ``_field`` / ``_section``).
"""

from __future__ import annotations

from app.services.seed_nora_technology import _field, _section, _tx

# ---------------------------------------------------------------------------
# Select-option constants (Project predefined lists, doc §5.3.1.2.6)
# ---------------------------------------------------------------------------

_PROJECT_STATUS_OPTIONS = [
    {
        "key": "scheduled",
        "label": "Scheduled",
        "translations": _tx(
            de="Geplant",
            fr="Planifié",
            es="Programado",
            it="Pianificato",
            pt="Agendado",
            zh="已计划",
            ru="Запланирован",
            da="Planlagt",
            ar="مجدول",
        ),
    },
    {
        "key": "active",
        "label": "Active",
        "translations": _tx(
            de="Aktiv",
            fr="Actif",
            es="Activo",
            it="Attivo",
            pt="Ativo",
            zh="进行中",
            ru="Активен",
            da="Aktiv",
            ar="نشط",
        ),
    },
    {
        "key": "suspended",
        "label": "Suspended",
        "translations": _tx(
            de="Ausgesetzt",
            fr="Suspendu",
            es="Suspendido",
            it="Sospeso",
            pt="Suspenso",
            zh="已暂停",
            ru="Приостановлен",
            da="Suspenderet",
            ar="معلّق",
        ),
    },
    {
        "key": "cancelled",
        "label": "Cancelled",
        "translations": _tx(
            de="Abgebrochen",
            fr="Annulé",
            es="Cancelado",
            it="Annullato",
            pt="Cancelado",
            zh="已取消",
            ru="Отменён",
            da="Annulleret",
            ar="ملغى",
        ),
    },
]

_EXECUTION_ENTITY_OPTIONS = [
    {
        "key": "inHouse",
        "label": "In-House Execution",
        "translations": _tx(
            de="Interne Ausführung",
            fr="Exécution interne",
            es="Ejecución interna",
            it="Esecuzione interna",
            pt="Execução interna",
            zh="内部执行",
            ru="Внутреннее исполнение",
            da="Intern udførelse",
            ar="تنفيذ داخلي",
        ),
    },
    {
        "key": "outsourced",
        "label": "Outsourced Execution",
        "translations": _tx(
            de="Ausgelagerte Ausführung",
            fr="Exécution externalisée",
            es="Ejecución externalizada",
            it="Esecuzione esternalizzata",
            pt="Execução externalizada",
            zh="外包执行",
            ru="Внешнее исполнение",
            da="Outsourcet udførelse",
            ar="تنفيذ خارجي",
        ),
    },
]

_PRIORITY_OPTIONS = [
    {
        "key": "high",
        "label": "High Priority",
        "translations": _tx(
            de="Hohe Priorität",
            fr="Priorité élevée",
            es="Prioridad alta",
            it="Priorità alta",
            pt="Prioridade alta",
            zh="高优先级",
            ru="Высокий приоритет",
            da="Høj prioritet",
            ar="أولوية عالية",
        ),
    },
    {
        "key": "medium",
        "label": "Medium Priority",
        "translations": _tx(
            de="Mittlere Priorität",
            fr="Priorité moyenne",
            es="Prioridad media",
            it="Priorità media",
            pt="Prioridade média",
            zh="中优先级",
            ru="Средний приоритет",
            da="Mellem prioritet",
            ar="أولوية متوسطة",
        ),
    },
    {
        "key": "low",
        "label": "Low Priority",
        "translations": _tx(
            de="Niedrige Priorität",
            fr="Priorité faible",
            es="Prioridad baja",
            it="Priorità bassa",
            pt="Prioridade baixa",
            zh="低优先级",
            ru="Низкий приоритет",
            da="Lav prioritet",
            ar="أولوية منخفضة",
        ),
    },
]

_CURRENCY_OPTIONS = [
    {
        "key": "sar",
        "label": "Saudi Riyal (SAR)",
        "translations": _tx(
            de="Saudi-Riyal (SAR)",
            fr="Riyal saoudien (SAR)",
            es="Riyal saudí (SAR)",
            it="Riyal saudita (SAR)",
            pt="Rial saudita (SAR)",
            zh="沙特里亚尔 (SAR)",
            ru="Саудовский риял (SAR)",
            da="Saudiarabisk riyal (SAR)",
            ar="ريال سعودي (SAR)",
        ),
    },
    {
        "key": "usd",
        "label": "US Dollar (USD)",
        "translations": _tx(
            de="US-Dollar (USD)",
            fr="Dollar américain (USD)",
            es="Dólar estadounidense (USD)",
            it="Dollaro USA (USD)",
            pt="Dólar americano (USD)",
            zh="美元 (USD)",
            ru="Доллар США (USD)",
            da="Amerikansk dollar (USD)",
            ar="دولار أمريكي (USD)",
        ),
    },
]

# ---------------------------------------------------------------------------
# The three new Strategic Alignment building blocks
# ---------------------------------------------------------------------------

NORA_STRATEGIC_TYPES: list[dict] = [
    # 1 · Vision -----------------------------------------------------------
    {
        "key": "Vision",
        "label": "Vision",
        "description": "Long-term objective the entity seeks to achieve — a future state or "
        "benefit reflecting the entity's ambition.",
        "icon": "visibility",
        "color": "#c7527d",
        "category": "Business",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Vision",
                fr="Vision",
                es="Visión",
                it="Visione",
                pt="Visão",
                zh="愿景",
                ru="Видение",
                da="Vision",
                ar="الرؤية",
            ),
            "description": _tx(
                de="Langfristiges Ziel der Organisation — ein Zukunftszustand oder Nutzen, der "
                "die Ambition der Organisation widerspiegelt.",
                fr="Objectif à long terme visé par l'entité — un état futur ou un bénéfice "
                "reflétant l'ambition de l'entité.",
                es="Objetivo a largo plazo que la entidad busca alcanzar — un estado futuro o "
                "beneficio que refleja la ambición de la entidad.",
                it="Obiettivo a lungo termine che l'ente intende raggiungere — uno stato futuro "
                "o beneficio che riflette l'ambizione dell'ente.",
                pt="Objetivo de longo prazo que a entidade procura alcançar — um estado futuro "
                "ou benefício que reflete a ambição da entidade.",
                zh="实体寻求实现的长期目标——反映实体抱负的未来状态或收益。",
                ru="Долгосрочная цель организации — будущее состояние или выгода, отражающая "
                "амбиции организации.",
                da="Langsigtet mål, som enheden søger at opnå — en fremtidig tilstand eller "
                "fordel, der afspejler enhedens ambition.",
                ar="هدف طويل المدى تسعى الجهة لتحقيقه — حالة مستقبلية أو منفعة تعكس طموح الجهة.",
            ),
        },
        "subtypes": [],
        "sort_order": 1,
        "fields_schema": [
            _section(
                "Vision Details",
                _tx(
                    de="Vision-Details",
                    fr="Détails de la vision",
                    es="Detalles de la visión",
                    it="Dettagli della visione",
                    pt="Detalhes da visão",
                    zh="愿景详情",
                    ru="Детали видения",
                    da="Visionsdetaljer",
                    ar="تفاصيل الرؤية",
                ),
                [
                    _field(
                        "visionStatement",
                        "Vision Statement",
                        "text",
                        3,
                        _tx(
                            de="Vision-Statement",
                            fr="Énoncé de vision",
                            es="Declaración de visión",
                            it="Dichiarazione di visione",
                            pt="Declaração de visão",
                            zh="愿景陈述",
                            ru="Формулировка видения",
                            da="Visionserklæring",
                            ar="نص الرؤية",
                        ),
                    ),
                    _field(
                        "scopeOfVision",
                        "Scope of the Vision",
                        "text",
                        1,
                        _tx(
                            de="Geltungsbereich der Vision",
                            fr="Portée de la vision",
                            es="Alcance de la visión",
                            it="Ambito della visione",
                            pt="Âmbito da visão",
                            zh="愿景范围",
                            ru="Область видения",
                            da="Visionens omfang",
                            ar="نطاق الرؤية",
                        ),
                    ),
                ],
            ),
        ],
    },
    # 2 · Mission ----------------------------------------------------------
    {
        "key": "Mission",
        "label": "Mission",
        "description": "Main purpose and reason for the entity's existence, plus the core values "
        "and activities that help realize the vision.",
        "icon": "assignment",
        "color": "#c7527d",
        "category": "Business",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Mission",
                fr="Mission",
                es="Misión",
                it="Missione",
                pt="Missão",
                zh="使命",
                ru="Миссия",
                da="Mission",
                ar="الرسالة",
            ),
            "description": _tx(
                de="Hauptzweck und Daseinsgrund der Organisation sowie die Kernwerte und "
                "Aktivitäten zur Verwirklichung der Vision.",
                fr="Objet principal et raison d'être de l'entité, ainsi que les valeurs et "
                "activités clés qui aident à réaliser la vision.",
                es="Propósito principal y razón de ser de la entidad, además de los valores y "
                "actividades clave que ayudan a realizar la visión.",
                it="Scopo principale e ragione d'essere dell'ente, oltre ai valori e alle "
                "attività chiave che aiutano a realizzare la visione.",
                pt="Propósito principal e razão de existência da entidade, além dos valores e "
                "atividades essenciais que ajudam a realizar a visão.",
                zh="实体存在的主要目的和理由，以及有助于实现愿景的核心价值观和活动。",
                ru="Основное назначение и причина существования организации, а также ключевые "
                "ценности и виды деятельности, помогающие реализовать видение.",
                da="Hovedformål og eksistensgrundlag for enheden samt de kerneværdier og "
                "aktiviteter, der hjælper med at realisere visionen.",
                ar="الغرض الرئيسي وسبب وجود الجهة، إضافةً إلى القيم والأنشطة الأساسية التي تسهم "
                "في تحقيق الرؤية.",
            ),
        },
        "subtypes": [],
        "sort_order": 2,
        "fields_schema": [
            _section(
                "Mission Details",
                _tx(
                    de="Mission-Details",
                    fr="Détails de la mission",
                    es="Detalles de la misión",
                    it="Dettagli della missione",
                    pt="Detalhes da missão",
                    zh="使命详情",
                    ru="Детали миссии",
                    da="Missionsdetaljer",
                    ar="تفاصيل الرسالة",
                ),
                [
                    _field(
                        "missionStatement",
                        "Mission Statement",
                        "text",
                        3,
                        _tx(
                            de="Mission-Statement",
                            fr="Énoncé de mission",
                            es="Declaración de misión",
                            it="Dichiarazione di missione",
                            pt="Declaração de missão",
                            zh="使命陈述",
                            ru="Формулировка миссии",
                            da="Missionserklæring",
                            ar="نص الرسالة",
                        ),
                    ),
                    _field(
                        "scopeOfMission",
                        "Scope of the Mission",
                        "text",
                        1,
                        _tx(
                            de="Geltungsbereich der Mission",
                            fr="Portée de la mission",
                            es="Alcance de la misión",
                            it="Ambito della missione",
                            pt="Âmbito da missão",
                            zh="使命范围",
                            ru="Область миссии",
                            da="Missionens omfang",
                            ar="نطاق الرسالة",
                        ),
                    ),
                ],
            ),
        ],
    },
    # 6 · Project ----------------------------------------------------------
    {
        "key": "Project",
        "label": "Project",
        "description": "A set of activities and tasks executed over a defined period using "
        "specific resources to achieve a specific objective.",
        "icon": "assignment_turned_in",
        "color": "#33cc58",
        "category": "Business",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Projekt",
                fr="Projet",
                es="Proyecto",
                it="Progetto",
                pt="Projeto",
                zh="项目",
                ru="Проект",
                da="Projekt",
                ar="مشروع",
            ),
            "description": _tx(
                de="Eine Reihe von Aktivitäten und Aufgaben, die in einem definierten Zeitraum "
                "mit bestimmten Ressourcen zur Erreichung eines konkreten Ziels ausgeführt "
                "werden.",
                fr="Ensemble d'activités et de tâches exécutées sur une période définie avec des "
                "ressources spécifiques pour atteindre un objectif précis.",
                es="Conjunto de actividades y tareas ejecutadas durante un periodo definido con "
                "recursos específicos para lograr un objetivo concreto.",
                it="Insieme di attività e compiti eseguiti in un periodo definito con risorse "
                "specifiche per raggiungere un obiettivo preciso.",
                pt="Conjunto de atividades e tarefas executadas num período definido com "
                "recursos específicos para alcançar um objetivo concreto.",
                zh="在特定时间内使用特定资源执行的一组活动和任务，以实现特定目标。",
                ru="Набор действий и задач, выполняемых в течение определённого периода с "
                "использованием конкретных ресурсов для достижения определённой цели.",
                da="Et sæt aktiviteter og opgaver, der udføres over en defineret periode med "
                "bestemte ressourcer for at nå et bestemt mål.",
                ar="مجموعة من الأنشطة والمهام تُنفَّذ خلال فترة محددة باستخدام موارد معيّنة "
                "لتحقيق هدف محدد.",
            ),
        },
        "subtypes": [],
        "sort_order": 6,
        "fields_schema": [
            _section(
                "Project Details",
                _tx(
                    de="Projektdetails",
                    fr="Détails du projet",
                    es="Detalles del proyecto",
                    it="Dettagli del progetto",
                    pt="Detalhes do projeto",
                    zh="项目详情",
                    ru="Детали проекта",
                    da="Projektdetaljer",
                    ar="تفاصيل المشروع",
                ),
                [
                    _field(
                        "scopeOfWork",
                        "Project Scope of Work",
                        "text",
                        1,
                        _tx(
                            de="Projektleistungsumfang",
                            fr="Périmètre du projet",
                            es="Alcance del trabajo del proyecto",
                            it="Ambito di lavoro del progetto",
                            pt="Âmbito de trabalho do projeto",
                            zh="项目工作范围",
                            ru="Объём работ проекта",
                            da="Projektets arbejdsomfang",
                            ar="نطاق عمل المشروع",
                        ),
                    ),
                    _field(
                        "sponsor",
                        "Project Sponsor",
                        "text",
                        1,
                        _tx(
                            de="Projektsponsor",
                            fr="Commanditaire du projet",
                            es="Patrocinador del proyecto",
                            it="Sponsor del progetto",
                            pt="Patrocinador do projeto",
                            zh="项目发起人",
                            ru="Спонсор проекта",
                            da="Projektsponsor",
                            ar="راعي المشروع",
                        ),
                    ),
                    _field(
                        "owner",
                        "Project Owner",
                        "text",
                        1,
                        _tx(
                            de="Projekteigner",
                            fr="Propriétaire du projet",
                            es="Propietario del proyecto",
                            it="Titolare del progetto",
                            pt="Proprietário do projeto",
                            zh="项目负责人",
                            ru="Владелец проекта",
                            da="Projektejer",
                            ar="مالك المشروع",
                        ),
                    ),
                    _field(
                        "manager",
                        "Project Manager",
                        "text",
                        1,
                        _tx(
                            de="Projektmanager",
                            fr="Chef de projet",
                            es="Gerente del proyecto",
                            it="Project manager",
                            pt="Gestor do projeto",
                            zh="项目经理",
                            ru="Руководитель проекта",
                            da="Projektleder",
                            ar="مدير المشروع",
                        ),
                    ),
                    _field(
                        "deliverables",
                        "Project Deliverables",
                        "text",
                        1,
                        _tx(
                            de="Projektergebnisse",
                            fr="Livrables du projet",
                            es="Entregables del proyecto",
                            it="Deliverable del progetto",
                            pt="Entregáveis do projeto",
                            zh="项目交付物",
                            ru="Результаты проекта",
                            da="Projektleverancer",
                            ar="مخرجات المشروع",
                        ),
                    ),
                    _field(
                        "status",
                        "Status of the Project",
                        "single_select",
                        1,
                        _tx(
                            de="Projektstatus",
                            fr="Statut du projet",
                            es="Estado del proyecto",
                            it="Stato del progetto",
                            pt="Estado do projeto",
                            zh="项目状态",
                            ru="Статус проекта",
                            da="Projektstatus",
                            ar="حالة المشروع",
                        ),
                        options=_PROJECT_STATUS_OPTIONS,
                    ),
                    _field(
                        "executionEntity",
                        "Entity in Charge of Execution",
                        "single_select",
                        1,
                        _tx(
                            de="Ausführungsverantwortliche Stelle",
                            fr="Entité chargée de l'exécution",
                            es="Entidad a cargo de la ejecución",
                            it="Ente responsabile dell'esecuzione",
                            pt="Entidade responsável pela execução",
                            zh="负责执行的实体",
                            ru="Организация, отвечающая за исполнение",
                            da="Enhed ansvarlig for udførelsen",
                            ar="الجهة المسؤولة عن التنفيذ",
                        ),
                        options=_EXECUTION_ENTITY_OPTIONS,
                    ),
                    _field(
                        "startDate",
                        "Start Date",
                        "date",
                        1,
                        _tx(
                            de="Startdatum",
                            fr="Date de début",
                            es="Fecha de inicio",
                            it="Data di inizio",
                            pt="Data de início",
                            zh="开始日期",
                            ru="Дата начала",
                            da="Startdato",
                            ar="تاريخ البدء",
                        ),
                    ),
                    _field(
                        "completionDate",
                        "Completion Date",
                        "date",
                        1,
                        _tx(
                            de="Abschlussdatum",
                            fr="Date d'achèvement",
                            es="Fecha de finalización",
                            it="Data di completamento",
                            pt="Data de conclusão",
                            zh="完成日期",
                            ru="Дата завершения",
                            da="Afslutningsdato",
                            ar="تاريخ الإنجاز",
                        ),
                    ),
                    _field(
                        "budget",
                        "Budget",
                        "cost",
                        1,
                        _tx(
                            de="Budget",
                            fr="Budget",
                            es="Presupuesto",
                            it="Budget",
                            pt="Orçamento",
                            zh="预算",
                            ru="Бюджет",
                            da="Budget",
                            ar="الميزانية",
                        ),
                    ),
                    _field(
                        "currency",
                        "Currency",
                        "single_select",
                        1,
                        _tx(
                            de="Währung",
                            fr="Devise",
                            es="Moneda",
                            it="Valuta",
                            pt="Moeda",
                            zh="货币",
                            ru="Валюта",
                            da="Valuta",
                            ar="العملة",
                        ),
                        options=_CURRENCY_OPTIONS,
                    ),
                    _field(
                        "priority",
                        "Priority",
                        "single_select",
                        1,
                        _tx(
                            de="Priorität",
                            fr="Priorité",
                            es="Prioridad",
                            it="Priorità",
                            pt="Prioridade",
                            zh="优先级",
                            ru="Приоритет",
                            da="Prioritet",
                            ar="الأولوية",
                        ),
                        options=_PRIORITY_OPTIONS,
                    ),
                ],
            ),
        ],
    },
]
