"""NORA Content Meta Model — Beneficiary Experience building blocks.

[FORK] NORA exact-fidelity metamodel (noraPlanMeta.md, Phase 1C).

The National EA Framework "EA Content Meta Model" document (§5.3.3) defines the
Beneficiary Experience domain. ``Beneficiary``, ``BeneficiaryJourney`` and
``Persona`` already exist in ``seed.TYPES``; this module adds the journey
decomposition blocks:

    Phase (§5.3.3.2.4), Step (§5.3.3.2.5)

Appended onto ``seed.TYPES``; reuses the i18n helpers from
``seed_nora_technology`` (``_tx`` / ``_field`` / ``_section``).
"""

from __future__ import annotations

from app.services.seed_nora_technology import _field, _section, _tx

_COMMUNICATION_CHANNEL_OPTIONS = [
    {
        "key": "digitalPlatform",
        "label": "Digital Platform",
        "translations": _tx(
            de="Digitale Plattform",
            fr="Plateforme numérique",
            es="Plataforma digital",
            it="Piattaforma digitale",
            pt="Plataforma digital",
            zh="数字平台",
            ru="Цифровая платформа",
            da="Digital platform",
            ar="منصة رقمية",
        ),
    },
    {
        "key": "mobileApp",
        "label": "Smartphone App",
        "translations": _tx(
            de="Smartphone-App",
            fr="Application mobile",
            es="Aplicación móvil",
            it="App per smartphone",
            pt="Aplicação móvel",
            zh="智能手机应用",
            ru="Мобильное приложение",
            da="Smartphone-app",
            ar="تطبيق الهاتف الذكي",
        ),
    },
    {
        "key": "socialMedia",
        "label": "Social Media",
        "translations": _tx(
            de="Soziale Medien",
            fr="Réseaux sociaux",
            es="Redes sociales",
            it="Social media",
            pt="Redes sociais",
            zh="社交媒体",
            ru="Социальные сети",
            da="Sociale medier",
            ar="وسائل التواصل الاجتماعي",
        ),
    },
    {
        "key": "traditional",
        "label": "Traditional Channels",
        "translations": _tx(
            de="Traditionelle Kanäle",
            fr="Canaux traditionnels",
            es="Canales tradicionales",
            it="Canali tradizionali",
            pt="Canais tradicionais",
            zh="传统渠道",
            ru="Традиционные каналы",
            da="Traditionelle kanaler",
            ar="القنوات التقليدية",
        ),
    },
]

NORA_BENEFICIARY_TYPES: list[dict] = [
    # 23 · Phase -----------------------------------------------------------
    {
        "key": "Phase",
        "label": "Phase",
        "description": "A set of approved steps within a clear time frame that the beneficiary "
        "goes through to obtain a service or achieve a value.",
        "icon": "linear_scale",
        "color": "#fe6690",
        "category": "Business",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Phase",
                fr="Phase",
                es="Fase",
                it="Fase",
                pt="Fase",
                zh="阶段",
                ru="Этап",
                da="Fase",
                ar="مرحلة",
            ),
            "description": _tx(
                de="Eine Reihe genehmigter Schritte innerhalb eines klaren Zeitrahmens, die der "
                "Begünstigte durchläuft, um eine Leistung oder einen Wert zu erhalten.",
                fr="Un ensemble d'étapes approuvées dans un cadre temporel défini que le "
                "bénéficiaire traverse pour obtenir un service ou une valeur.",
                es="Un conjunto de pasos aprobados dentro de un marco temporal claro que el "
                "beneficiario recorre para obtener un servicio o un valor.",
                it="Un insieme di passaggi approvati entro un chiaro arco temporale che il "
                "beneficiario attraversa per ottenere un servizio o un valore.",
                pt="Um conjunto de passos aprovados dentro de um período claro que o "
                "beneficiário percorre para obter um serviço ou um valor.",
                zh="受益人为获得服务或价值而经历的、处于明确时间范围内的一组既定步骤。",
                ru="Набор утверждённых шагов в чётких временных рамках, которые бенефициар "
                "проходит для получения услуги или ценности.",
                da="Et sæt godkendte trin inden for en klar tidsramme, som modtageren "
                "gennemgår for at opnå en tjeneste eller en værdi.",
                ar="مجموعة من الخطوات المعتمدة ضمن إطار زمني واضح يمر بها المستفيد للحصول على "
                "خدمة أو تحقيق قيمة.",
            ),
        },
        "subtypes": [],
        "sort_order": 23,
        "fields_schema": [],
    },
    # 24 · Step ------------------------------------------------------------
    {
        "key": "Step",
        "label": "Step",
        "description": "A step the beneficiary takes or interacts with during each phase of "
        "their journey with the entity.",
        "icon": "footprint",
        "color": "#fe6690",
        "category": "Business",
        "has_hierarchy": False,
        "translations": {
            "label": _tx(
                de="Schritt",
                fr="Étape",
                es="Paso",
                it="Passaggio",
                pt="Passo",
                zh="步骤",
                ru="Шаг",
                da="Trin",
                ar="خطوة",
            ),
            "description": _tx(
                de="Ein Schritt, den der Begünstigte in jeder Phase seiner Journey mit der "
                "Entität durchführt oder mit dem er interagiert.",
                fr="Une étape que le bénéficiaire effectue ou avec laquelle il interagit à chaque "
                "phase de son parcours avec l'entité.",
                es="Un paso que el beneficiario realiza o con el que interactúa durante cada fase "
                "de su recorrido con la entidad.",
                it="Un passaggio che il beneficiario compie o con cui interagisce durante ogni "
                "fase del suo percorso con l'ente.",
                pt="Um passo que o beneficiário realiza ou com o qual interage durante cada fase "
                "do seu percurso com a entidade.",
                zh="受益人在与实体的旅程各阶段中所采取或交互的步骤。",
                ru="Шаг, который бенефициар выполняет или с которым взаимодействует на каждом "
                "этапе своего пути с организацией.",
                da="Et trin, som modtageren tager eller interagerer med i hver fase af sin rejse "
                "med enheden.",
                ar="خطوة يقوم بها المستفيد أو يتفاعل معها خلال كل مرحلة من رحلته مع الجهة.",
            ),
        },
        "subtypes": [],
        "sort_order": 24,
        "fields_schema": [
            _section(
                "Step Details",
                _tx(
                    de="Schrittdetails",
                    fr="Détails de l'étape",
                    es="Detalles del paso",
                    it="Dettagli del passaggio",
                    pt="Detalhes do passo",
                    zh="步骤详情",
                    ru="Сведения о шаге",
                    da="Trindetaljer",
                    ar="تفاصيل الخطوة",
                ),
                [
                    _field(
                        "associatedGaps",
                        "Associated Gaps",
                        "text",
                        1,
                        _tx(
                            de="Zugehörige Lücken",
                            fr="Écarts associés",
                            es="Brechas asociadas",
                            it="Lacune associate",
                            pt="Lacunas associadas",
                            zh="相关差距",
                            ru="Связанные пробелы",
                            da="Tilknyttede huller",
                            ar="الفجوات المرتبطة",
                        ),
                    ),
                    _field(
                        "opportunitiesForImprovement",
                        "Opportunities for Improvement",
                        "text",
                        1,
                        _tx(
                            de="Verbesserungsmöglichkeiten",
                            fr="Opportunités d'amélioration",
                            es="Oportunidades de mejora",
                            it="Opportunità di miglioramento",
                            pt="Oportunidades de melhoria",
                            zh="改进机会",
                            ru="Возможности для улучшения",
                            da="Muligheder for forbedring",
                            ar="فرص التحسين",
                        ),
                    ),
                    _field(
                        "expectedImpact",
                        "Expected Impact",
                        "text",
                        1,
                        _tx(
                            de="Erwartete Auswirkung",
                            fr="Impact attendu",
                            es="Impacto esperado",
                            it="Impatto atteso",
                            pt="Impacto esperado",
                            zh="预期影响",
                            ru="Ожидаемое влияние",
                            da="Forventet effekt",
                            ar="الأثر المتوقع",
                        ),
                    ),
                    _field(
                        "priority",
                        "Priority",
                        "text",
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
                    ),
                    _field(
                        "communicationChannel",
                        "Communication Channel",
                        "single_select",
                        1,
                        _tx(
                            de="Kommunikationskanal",
                            fr="Canal de communication",
                            es="Canal de comunicación",
                            it="Canale di comunicazione",
                            pt="Canal de comunicação",
                            zh="沟通渠道",
                            ru="Канал связи",
                            da="Kommunikationskanal",
                            ar="قناة التواصل",
                        ),
                        options=_COMMUNICATION_CHANNEL_OPTIONS,
                    ),
                ],
            ),
        ],
    },
]
