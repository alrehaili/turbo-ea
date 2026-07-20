"""Promote opportunistic view attributes to first-class metamodel fields.

Three change-governance views (Executive Strategy Map, Resilience / Critical
Service, Data Flow Map) previously read a KPI, RTO/RPO and Data Domain value
*opportunistically* from a card's ``attributes`` JSONB. Those keys are now
first-class fields on the built-in card types:

* ``Objective`` → ``kpi`` (Key Result / KPI)
* ``Application`` → ``rto`` / ``rpo`` / ``recoveryTier``
* ``DataObject`` → ``dataDomain``

``seed.py`` only runs when a card_type row is missing on startup, so a new
field added to the built-in defaults would never reach existing installs
without a migration. This migration appends each field to the matching section
of each type -- but only when the field is not already present, so admin
customisations are preserved and the migration is fully idempotent. The values
already stored under these attribute keys (via the opportunistic reads) are
untouched and simply become editable through the card UI.

The downgrade removes the fields if (and only if) they are still in place.

[FORK FEATURE]

Revision ID: 158
Revises: 157
Create Date: 2026-07-20
"""

import json
from typing import Any, Union

import sqlalchemy as sa

from alembic import op

revision: str = "158"
down_revision: Union[str, None] = "157"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


RECOVERY_TIER_OPTIONS: list[dict[str, Any]] = [
    {
        "key": "tier1",
        "label": "Tier 1 — Mission Critical",
        "color": "#d32f2f",
        "translations": {
            "de": "Stufe 1 – Geschäftskritisch",
            "fr": "Niveau 1 — Critique pour la mission",
            "es": "Nivel 1 — Crítico para la misión",
            "it": "Livello 1 — Critico per la missione",
            "pt": "Nível 1 — Crítico para a missão",
            "zh": "第 1 级 — 关键任务",
            "ru": "Уровень 1 — критически важный",
            "da": "Niveau 1 — Missionskritisk",
            "ar": "المستوى 1 — حَرِج للمهمة",
        },
    },
    {
        "key": "tier2",
        "label": "Tier 2 — Business Critical",
        "color": "#f57c00",
        "translations": {
            "de": "Stufe 2 – Unternehmenskritisch",
            "fr": "Niveau 2 — Critique pour l'entreprise",
            "es": "Nivel 2 — Crítico para el negocio",
            "it": "Livello 2 — Critico per il business",
            "pt": "Nível 2 — Crítico para o negócio",
            "zh": "第 2 级 — 业务关键",
            "ru": "Уровень 2 — критичный для бизнеса",
            "da": "Niveau 2 — Forretningskritisk",
            "ar": "المستوى 2 — حَرِج للأعمال",
        },
    },
    {
        "key": "tier3",
        "label": "Tier 3 — Business Operational",
        "color": "#fbc02d",
        "translations": {
            "de": "Stufe 3 – Geschäftsbetrieb",
            "fr": "Niveau 3 — Opérationnel",
            "es": "Nivel 3 — Operativo",
            "it": "Livello 3 — Operativo",
            "pt": "Nível 3 — Operacional",
            "zh": "第 3 级 — 业务运营",
            "ru": "Уровень 3 — операционный",
            "da": "Niveau 3 — Forretningsoperationel",
            "ar": "المستوى 3 — تشغيلي للأعمال",
        },
    },
    {
        "key": "tier4",
        "label": "Tier 4 — Non-Critical",
        "color": "#9e9e9e",
        "translations": {
            "de": "Stufe 4 – Nicht kritisch",
            "fr": "Niveau 4 — Non critique",
            "es": "Nivel 4 — No crítico",
            "it": "Livello 4 — Non critico",
            "pt": "Nível 4 — Não crítico",
            "zh": "第 4 级 — 非关键",
            "ru": "Уровень 4 — некритичный",
            "da": "Niveau 4 — Ikke-kritisk",
            "ar": "المستوى 4 — غير حَرِج",
        },
    },
]


# (type_key, section_name, [field_dict, ...])
TARGETS: list[tuple[str, str, list[dict[str, Any]]]] = [
    (
        "Objective",
        "Objective Information",
        [
            {
                "key": "kpi",
                "label": "Key Result / KPI",
                "type": "text",
                "weight": 1,
                "translations": {
                    "de": "Schlüsselergebnis / KPI",
                    "fr": "Résultat clé / KPI",
                    "es": "Resultado clave / KPI",
                    "it": "Risultato chiave / KPI",
                    "pt": "Resultado-chave / KPI",
                    "zh": "关键结果 / KPI",
                    "ru": "Ключевой результат / KPI",
                    "da": "Nøgleresultat / KPI",
                    "ar": "النتيجة الرئيسية / مؤشر الأداء",
                },
            },
        ],
    ),
    (
        "Application",
        "Assessment",
        [
            {
                "key": "rto",
                "label": "Recovery Time Objective (RTO)",
                "type": "text",
                "weight": 1,
                "translations": {
                    "de": "Wiederherstellungszeitziel (RTO)",
                    "fr": "Objectif de temps de reprise (RTO)",
                    "es": "Objetivo de tiempo de recuperación (RTO)",
                    "it": "Obiettivo del tempo di ripristino (RTO)",
                    "pt": "Objetivo de tempo de recuperação (RTO)",
                    "zh": "恢复时间目标 (RTO)",
                    "ru": "Целевое время восстановления (RTO)",
                    "da": "Mål for genoprettelsestid (RTO)",
                    "ar": "الهدف الزمني للاسترداد (RTO)",
                },
            },
            {
                "key": "rpo",
                "label": "Recovery Point Objective (RPO)",
                "type": "text",
                "weight": 1,
                "translations": {
                    "de": "Wiederherstellungspunktziel (RPO)",
                    "fr": "Objectif de point de reprise (RPO)",
                    "es": "Objetivo de punto de recuperación (RPO)",
                    "it": "Obiettivo del punto di ripristino (RPO)",
                    "pt": "Objetivo de ponto de recuperação (RPO)",
                    "zh": "恢复点目标 (RPO)",
                    "ru": "Целевая точка восстановления (RPO)",
                    "da": "Mål for genoprettelsespunkt (RPO)",
                    "ar": "الهدف النقطي للاسترداد (RPO)",
                },
            },
            {
                "key": "recoveryTier",
                "label": "Recovery Tier",
                "type": "single_select",
                "options": RECOVERY_TIER_OPTIONS,
                "weight": 1,
                "translations": {
                    "de": "Wiederherstellungsstufe",
                    "fr": "Niveau de reprise",
                    "es": "Nivel de recuperación",
                    "it": "Livello di ripristino",
                    "pt": "Nível de recuperação",
                    "zh": "恢复等级",
                    "ru": "Уровень восстановления",
                    "da": "Genoprettelsesniveau",
                    "ar": "مستوى الاسترداد",
                },
            },
        ],
    ),
    (
        "DataObject",
        "Data Information",
        [
            {
                "key": "dataDomain",
                "label": "Data Domain",
                "type": "text",
                "weight": 1,
                "translations": {
                    "de": "Datendomäne",
                    "fr": "Domaine de données",
                    "es": "Dominio de datos",
                    "it": "Dominio dati",
                    "pt": "Domínio de dados",
                    "zh": "数据域",
                    "ru": "Домен данных",
                    "da": "Datadomæne",
                    "ar": "نطاق البيانات",
                },
            },
        ],
    ),
]


def _ensure_fields(
    fields_schema: list[dict[str, Any]], section_name: str, new_fields: list[dict[str, Any]]
) -> bool:
    """Append each field to the matching section if missing. Returns True if changed."""
    changed = False
    for section in fields_schema or []:
        if not isinstance(section, dict) or section.get("section") != section_name:
            continue
        fields = section.setdefault("fields", [])
        existing = {f.get("key") for f in fields if isinstance(f, dict)}
        for fld in new_fields:
            if fld["key"] in existing:
                continue
            fields.append(json.loads(json.dumps(fld)))
            changed = True
    return changed


def _remove_fields(
    fields_schema: list[dict[str, Any]], section_name: str, new_fields: list[dict[str, Any]]
) -> bool:
    """Remove each field from the matching section if present. Returns True if changed."""
    keys = {f["key"] for f in new_fields}
    changed = False
    for section in fields_schema or []:
        if not isinstance(section, dict) or section.get("section") != section_name:
            continue
        fields = section.get("fields") or []
        kept = [f for f in fields if not (isinstance(f, dict) and f.get("key") in keys)]
        if len(kept) != len(fields):
            section["fields"] = kept
            changed = True
    return changed


def _apply(mutator) -> None:
    conn = op.get_bind()
    for type_key, section_name, new_fields in TARGETS:
        row = conn.execute(
            sa.text("SELECT fields_schema FROM card_types WHERE key = :k"),
            {"k": type_key},
        ).first()
        if row is None:
            continue
        schema = row[0] or []
        if mutator(schema, section_name, new_fields):
            conn.execute(
                sa.text("UPDATE card_types SET fields_schema = CAST(:s AS jsonb) WHERE key = :k"),
                {"s": json.dumps(schema), "k": type_key},
            )


def upgrade() -> None:
    _apply(_ensure_fields)


def downgrade() -> None:
    _apply(_remove_fields)
