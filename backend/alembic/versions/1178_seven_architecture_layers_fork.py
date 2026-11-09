"""Seven architecture layers: add Strategy, rename the six to "<Layer> Architecture".

[FORK FEATURE] The NORA 2.0 six layers (Business, Beneficiary Experience,
Application, Data, Technology, Security) gain a Strategy layer on top, and every
layer's display name gains "Architecture" ("Business Architecture", …).

Only the registry rows (``card_type_categories``) change here. Their **keys**
stay the bare layer names, so no card type's ``category`` and none of the
layer-ordered reports that key on them change. Which card types move into the
new layer, and the order of types inside each layer, is the NORA profile's
v16 pass (``nora_profile.apply_architecture_layout``), because a fresh install
is stamped at head without running this migration but does apply the profile.

Guarded, as built-in default changes must be
(``072_restore_business_process_color.py``):

* a label is rewritten only while it is still the old default, and only when
  no other row already reads as the new name (``is_duplicate`` in
  ``services/card_type_categories.py`` refuses the same clash for admins);
* a layer's ``sort_order`` moves down one only while it is still its old
  default, so a layer order an admin set is kept;
* the Strategy row is inserted only when no row is keyed or named like it.

The seed (``CARD_TYPE_CATEGORIES`` in ``seed.py``) carries the same values for
fresh installs; ``seed_default_categories`` is insert-only, so the Strategy row
lands there on the next boot even if this migration skipped it.

Revision ID: 1178
Revises: 165
Create Date: 2026-11-09
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "1178"
down_revision: Union[str, None] = "165"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STRATEGY = {
    "key": "Strategy",
    "label": "Strategy Architecture",
    "color": "#c7527d",
    "sort_order": 0,
    "translations": {
        "de": "Strategiearchitektur",
        "fr": "Architecture stratégique",
        "es": "Arquitectura estratégica",
        "it": "Architettura strategica",
        "pt": "Arquitetura estratégica",
        "zh": "战略架构",
        "ru": "Стратегическая архитектура",
        "da": "Strategiarkitektur",
        "ar": "بنية الاستراتيجية",
    },
}

# key → (old sort_order, new label, new sort_order, new translations)
RELABELS: dict[str, tuple[int, str, int, dict[str, str]]] = {
    "Business": (
        0,
        "Business Architecture",
        1,
        {
            "de": "Geschäftsarchitektur",
            "fr": "Architecture métier",
            "es": "Arquitectura de negocio",
            "it": "Architettura di business",
            "pt": "Arquitetura de negócio",
            "zh": "业务架构",
            "ru": "Бизнес-архитектура",
            "da": "Forretningsarkitektur",
            "ar": "بنية الأعمال",
        },
    ),
    "Beneficiary Experience": (
        1,
        "Beneficiary Experience Architecture",
        2,
        {
            "de": "Architektur des Nutzererlebnisses",
            "fr": "Architecture de l’expérience des bénéficiaires",
            "es": "Arquitectura de la experiencia del beneficiario",
            "it": "Architettura dell’esperienza del beneficiario",
            "pt": "Arquitetura da experiência do beneficiário",
            "zh": "受益人体验架构",
            "ru": "Архитектура опыта получателей услуг",
            "da": "Modtageroplevelsesarkitektur",
            "ar": "بنية تجربة المستفيد",
        },
    ),
    "Application": (
        2,
        "Application Architecture",
        3,
        {
            "de": "Anwendungsarchitektur",
            "fr": "Architecture applicative",
            "es": "Arquitectura de aplicaciones",
            "it": "Architettura applicativa",
            "pt": "Arquitetura de aplicações",
            "zh": "应用架构",
            "ru": "Архитектура приложений",
            "da": "Applikationsarkitektur",
            "ar": "بنية التطبيقات",
        },
    ),
    "Data": (
        3,
        "Data Architecture",
        4,
        {
            "de": "Datenarchitektur",
            "fr": "Architecture des données",
            "es": "Arquitectura de datos",
            "it": "Architettura dei dati",
            "pt": "Arquitetura de dados",
            "zh": "数据架构",
            "ru": "Архитектура данных",
            "da": "Dataarkitektur",
            "ar": "بنية البيانات",
        },
    ),
    "Technology": (
        4,
        "Technology Architecture",
        5,
        {
            "de": "Technologiearchitektur",
            "fr": "Architecture technologique",
            "es": "Arquitectura tecnológica",
            "it": "Architettura tecnologica",
            "pt": "Arquitetura tecnológica",
            "zh": "技术架构",
            "ru": "Технологическая архитектура",
            "da": "Teknologiarkitektur",
            "ar": "البنية التقنية",
        },
    ),
    "Security": (
        5,
        "Security Architecture",
        6,
        {
            "de": "Sicherheitsarchitektur",
            "fr": "Architecture de sécurité",
            "es": "Arquitectura de seguridad",
            "it": "Architettura di sicurezza",
            "pt": "Arquitetura de segurança",
            "zh": "安全架构",
            "ru": "Архитектура безопасности",
            "da": "Sikkerhedsarkitektur",
            "ar": "بنية الأمن",
        },
    ),
}


def _fold(value: str) -> str:
    return value.strip().casefold()


def plan(rows: list[dict]) -> dict:
    """What to change, given the registry's rows (``key``, ``label``,
    ``sort_order``). Pure — no database.

    Returns ``{"updates": [{"key", **columns}], "insert_strategy": bool}``.
    """
    names_by_key = {r["key"]: {_fold(r["key"]), _fold(r["label"])} for r in rows}

    def taken_by_other(name: str, own_key: str | None) -> bool:
        folded = _fold(name)
        return any(folded in names for key, names in names_by_key.items() if key != own_key)

    updates: list[dict] = []
    for row in rows:
        spec = RELABELS.get(row["key"])
        if spec is None:
            continue
        old_sort, new_label, new_sort, translations = spec
        change: dict = {}
        if row["label"] == row["key"] and not taken_by_other(new_label, row["key"]):
            change["label"] = new_label
            change["translations"] = translations
        if row["sort_order"] == old_sort:
            change["sort_order"] = new_sort
        if change:
            updates.append({"key": row["key"], **change})

    insert_strategy = not taken_by_other(STRATEGY["key"], None) and not taken_by_other(
        STRATEGY["label"], None
    )
    return {"updates": updates, "insert_strategy": insert_strategy}


def upgrade() -> None:
    bind = op.get_bind()
    rows = [
        {"key": k, "label": lbl, "sort_order": s}
        for k, lbl, s in bind.execute(
            sa.text("SELECT key, label, sort_order FROM card_type_categories")
        ).all()
    ]
    todo = plan(rows)
    for change in todo["updates"]:
        params = {"key": change["key"]}
        sets = []
        for col in ("label", "sort_order"):
            if col in change:
                sets.append(f"{col} = :{col}")
                params[col] = change[col]
        if "translations" in change:
            sets.append("translations = CAST(:translations AS jsonb)")
            params["translations"] = json.dumps(change["translations"], ensure_ascii=False)
        bind.execute(
            sa.text(f"UPDATE card_type_categories SET {', '.join(sets)} WHERE key = :key"),
            params,
        )
    if todo["insert_strategy"]:
        bind.execute(
            sa.text(
                "INSERT INTO card_type_categories "
                "(id, key, label, color, sort_order, built_in, translations) "
                "VALUES (:id, :key, :label, :color, :sort_order, true, "
                "CAST(:translations AS jsonb))"
            ),
            {
                "id": uuid.uuid4(),
                "key": STRATEGY["key"],
                "label": STRATEGY["label"],
                "color": STRATEGY["color"],
                "sort_order": STRATEGY["sort_order"],
                "translations": json.dumps(STRATEGY["translations"], ensure_ascii=False),
            },
        )


def downgrade() -> None:
    # Data-only and guarded: the old labels are not restored, since an admin
    # may not have had the defaults when this ran. The Strategy row stays too —
    # card types may already sit in it.
    pass
