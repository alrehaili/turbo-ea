"""NORA Content Meta Model — attribute backfill for pre-existing shell types.

[FORK] NORA exact-fidelity metamodel (noraPlanMeta.md, Phase 1 🟡 backfills).

``Datacenter`` (= Data Center, §5.3.6.2.1), ``NetworkCircuit`` (= Network Link,
§5.3.6.2.5) and ``Interface`` (= Technical Integration Interface, §5.3.5.2.4)
already exist inline in ``seed.TYPES`` but as near-empty shells. Rather than
editing the giant inline literals, this module carries their document attribute
sets and a ``apply_nora_attribute_backfills`` patcher that appends the missing
fields (deduped by key) to the matching section after ``seed.TYPES`` is built.

Reuses the field helpers + option constants from ``seed_nora_technology``.
"""

from __future__ import annotations

from app.services.seed_nora_technology import (
    _ENVIRONMENT_OPTIONS,
    _OPERATION_TYPE,
    _cost_fields,
    _field,
    _tx,
)

# ---------------------------------------------------------------------------
# Option constants
# ---------------------------------------------------------------------------

_DC_ROLE_OPTIONS = [
    {
        "key": "primary",
        "label": "Primary Data Center",
        "translations": _tx(
            de="Primäres Rechenzentrum",
            fr="Centre de données principal",
            es="Centro de datos principal",
            it="Data center primario",
            pt="Data center primário",
            zh="主数据中心",
            ru="Основной ЦОД",
            da="Primært datacenter",
            ar="مركز البيانات الرئيسي",
        ),
    },
    {
        "key": "disasterRecovery",
        "label": "Disaster Recovery Center",
        "translations": _tx(
            de="Notfallwiederherstellungszentrum",
            fr="Centre de reprise après sinistre",
            es="Centro de recuperación ante desastres",
            it="Centro di disaster recovery",
            pt="Centro de recuperação de desastres",
            zh="灾备中心",
            ru="Центр аварийного восстановления",
            da="Katastrofeberedskabscenter",
            ar="مركز التعافي من الكوارث",
        ),
    },
]

_CIRCUIT_TECHNOLOGY_OPTIONS = [
    {
        "key": "fiber",
        "label": "Fiber",
        "translations": _tx(
            de="Glasfaser",
            fr="Fibre",
            es="Fibra",
            it="Fibra",
            pt="Fibra",
            zh="光纤",
            ru="Оптоволокно",
            da="Fiber",
            ar="ألياف ضوئية",
        ),
    },
    {
        "key": "copper",
        "label": "Copper",
        "translations": _tx(
            de="Kupfer",
            fr="Cuivre",
            es="Cobre",
            it="Rame",
            pt="Cobre",
            zh="铜缆",
            ru="Медь",
            da="Kobber",
            ar="نحاس",
        ),
    },
    {
        "key": "microwave",
        "label": "Microwave",
        "translations": _tx(
            de="Mikrowelle",
            fr="Micro-ondes",
            es="Microondas",
            it="Microonde",
            pt="Micro-ondas",
            zh="微波",
            ru="Микроволновая связь",
            da="Mikrobølge",
            ar="موجات دقيقة",
        ),
    },
    {
        "key": "satellite",
        "label": "Satellite",
        "translations": _tx(
            de="Satellit",
            fr="Satellite",
            es="Satélite",
            it="Satellite",
            pt="Satélite",
            zh="卫星",
            ru="Спутник",
            da="Satellit",
            ar="قمر صناعي",
        ),
    },
]

_CIRCUIT_ROLE_OPTIONS = [
    {
        "key": "primary",
        "label": "Primary Link",
        "translations": _tx(
            de="Primärverbindung",
            fr="Liaison principale",
            es="Enlace principal",
            it="Collegamento primario",
            pt="Ligação principal",
            zh="主链路",
            ru="Основной канал",
            da="Primært link",
            ar="الوصلة الرئيسية",
        ),
    },
    {
        "key": "backup",
        "label": "Backup Link",
        "translations": _tx(
            de="Backup-Verbindung",
            fr="Liaison de secours",
            es="Enlace de respaldo",
            it="Collegamento di backup",
            pt="Ligação de reserva",
            zh="备份链路",
            ru="Резервный канал",
            da="Backup-link",
            ar="وصلة احتياطية",
        ),
    },
]

_SCOPE_OF_CONNECTION_OPTIONS = [
    {
        "key": "internal",
        "label": "Internal",
        "translations": _tx(
            de="Intern",
            fr="Interne",
            es="Interno",
            it="Interno",
            pt="Interno",
            zh="内部",
            ru="Внутренний",
            da="Intern",
            ar="داخلي",
        ),
    },
    {
        "key": "external",
        "label": "External",
        "translations": _tx(
            de="Extern",
            fr="Externe",
            es="Externo",
            it="Esterno",
            pt="Externo",
            zh="外部",
            ru="Внешний",
            da="Ekstern",
            ar="خارجي",
        ),
    },
]


def _text(key: str, label: str, tx: dict, weight: int = 1) -> dict:
    return _field(key, label, "text", weight, tx)


# ---------------------------------------------------------------------------
# Per-type (section-name, fields-to-append)
# ---------------------------------------------------------------------------

_DATACENTER_FIELDS = [
    _field(
        "role",
        "Role",
        "single_select",
        1,
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
        options=_DC_ROLE_OPTIONS,
    ),
    _text(
        "classificationLevel",
        "Classification Level",
        _tx(
            de="Klassifizierungsstufe",
            fr="Niveau de classification",
            es="Nivel de clasificación",
            it="Livello di classificazione",
            pt="Nível de classificação",
            zh="分级级别",
            ru="Уровень классификации",
            da="Klassifikationsniveau",
            ar="مستوى التصنيف",
        ),
    ),
    _text(
        "location",
        "Location",
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
        "environment",
        "Environment",
        "single_select",
        1,
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
    _OPERATION_TYPE(1),
    *_cost_fields(20),
]

_NETWORK_CIRCUIT_FIELDS = [
    _text(
        "location",
        "Location",
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
        "technology",
        "Technology",
        "single_select",
        1,
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
        options=_CIRCUIT_TECHNOLOGY_OPTIONS,
    ),
    _text(
        "service",
        "Service",
        _tx(
            de="Dienst",
            fr="Service",
            es="Servicio",
            it="Servizio",
            pt="Serviço",
            zh="服务",
            ru="Услуга",
            da="Tjeneste",
            ar="الخدمة",
        ),
    ),
    _field(
        "role",
        "Role",
        "single_select",
        1,
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
        options=_CIRCUIT_ROLE_OPTIONS,
    ),
    _OPERATION_TYPE(1),
    _field(
        "subscriptionFees",
        "Subscription Fees",
        "cost",
        1,
        _tx(
            de="Abonnementgebühren",
            fr="Frais d'abonnement",
            es="Cuotas de suscripción",
            it="Costi di abbonamento",
            pt="Taxas de subscrição",
            zh="订阅费用",
            ru="Абонентская плата",
            da="Abonnementsgebyrer",
            ar="رسوم الاشتراك",
        ),
    ),
    *_cost_fields(20),
]

_INTERFACE_FIELDS = [
    _text(
        "consumer",
        "Consumer",
        _tx(
            de="Verbraucher",
            fr="Consommateur",
            es="Consumidor",
            it="Consumatore",
            pt="Consumidor",
            zh="消费方",
            ru="Потребитель",
            da="Forbruger",
            ar="المستهلك",
        ),
    ),
    _text(
        "producer",
        "Producer",
        _tx(
            de="Erzeuger",
            fr="Producteur",
            es="Productor",
            it="Produttore",
            pt="Produtor",
            zh="生产方",
            ru="Поставщик",
            da="Producent",
            ar="المنتِج",
        ),
    ),
    _text(
        "inputs",
        "Inputs",
        _tx(
            de="Eingaben",
            fr="Entrées",
            es="Entradas",
            it="Input",
            pt="Entradas",
            zh="输入",
            ru="Входы",
            da="Input",
            ar="المدخلات",
        ),
    ),
    _text(
        "deliverables",
        "Deliverables",
        _tx(
            de="Ergebnisse",
            fr="Livrables",
            es="Entregables",
            it="Deliverable",
            pt="Entregáveis",
            zh="交付物",
            ru="Результаты",
            da="Leverancer",
            ar="المخرجات",
        ),
    ),
    _field(
        "scopeOfConnection",
        "Scope of the Connection",
        "single_select",
        1,
        _tx(
            de="Umfang der Verbindung",
            fr="Portée de la connexion",
            es="Alcance de la conexión",
            it="Ambito della connessione",
            pt="Âmbito da ligação",
            zh="连接范围",
            ru="Область соединения",
            da="Forbindelsens omfang",
            ar="نطاق الاتصال",
        ),
        options=_SCOPE_OF_CONNECTION_OPTIONS,
    ),
    _text(
        "integrationPlatform",
        "Integration Platform",
        _tx(
            de="Integrationsplattform",
            fr="Plateforme d'intégration",
            es="Plataforma de integración",
            it="Piattaforma di integrazione",
            pt="Plataforma de integração",
            zh="集成平台",
            ru="Платформа интеграции",
            da="Integrationsplatform",
            ar="منصة التكامل",
        ),
    ),
    _text(
        "connectionPattern",
        "Connection Pattern",
        _tx(
            de="Verbindungsmuster",
            fr="Modèle de connexion",
            es="Patrón de conexión",
            it="Modello di connessione",
            pt="Padrão de ligação",
            zh="连接模式",
            ru="Шаблон соединения",
            da="Forbindelsesmønster",
            ar="نمط الاتصال",
        ),
    ),
    _text(
        "integrationType",
        "Integration Type",
        _tx(
            de="Integrationstyp",
            fr="Type d'intégration",
            es="Tipo de integración",
            it="Tipo di integrazione",
            pt="Tipo de integração",
            zh="集成类型",
            ru="Тип интеграции",
            da="Integrationstype",
            ar="نوع التكامل",
        ),
    ),
]

# (type_key -> (section_name, fields_to_append))
_BACKFILLS: dict[str, tuple[str, list[dict]]] = {
    "Datacenter": ("Datacenter Information", _DATACENTER_FIELDS),
    "NetworkCircuit": ("Circuit Details", _NETWORK_CIRCUIT_FIELDS),
    "Interface": ("Interface Information", _INTERFACE_FIELDS),
}


def apply_nora_attribute_backfills(types: list[dict]) -> None:
    """Append the NORA document attributes to the three shell types in place.

    Idempotent: fields whose key already exists in the target section are
    skipped, so re-running (or an admin who already added the field) is safe.
    """
    by_key = {t["key"]: t for t in types}
    for type_key, (section_name, new_fields) in _BACKFILLS.items():
        type_def = by_key.get(type_key)
        if type_def is None:
            continue
        schema = type_def.setdefault("fields_schema", [])
        section = next((s for s in schema if s.get("section") == section_name), None)
        if section is None:
            continue
        existing_keys = {f["key"] for f in section.get("fields", [])}
        section.setdefault("fields", [])
        for field in new_fields:
            if field["key"] not in existing_keys:
                section["fields"].append(field)
                existing_keys.add(field["key"])
