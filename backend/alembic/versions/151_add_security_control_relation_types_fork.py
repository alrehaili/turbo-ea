"""Add the built-in SecurityControl relation types (protects Application /
DataObject, secures ITComponent) for existing installs.

``seed.py`` only inserts a relation type when its key is missing on startup, so
adding these three built-ins to the seed has no effect on databases that were
already seeded. This migration inserts them (skipping any that already exist, so
it's idempotent and won't clash with an admin-created key).

[FORK FEATURE] — NORA.

Revision ID: 151
Revises: 150
Create Date: 2026-07-16
"""

import json
import uuid
from typing import Sequence, Union

from sqlalchemy.sql import text

from alembic import op

revision: str = "151"
down_revision: Union[str, None] = "150"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PROTECT_TRANS = {
    "label": {
        "de": "schützt",
        "fr": "protège",
        "es": "protege",
        "it": "protegge",
        "pt": "protege",
        "zh": "保护",
        "ru": "защищает",
        "da": "beskytter",
        "ar": "يحمي",
    },
    "reverse_label": {
        "de": "wird geschützt von",
        "fr": "est protégé par",
        "es": "está protegido por",
        "it": "è protetto da",
        "pt": "é protegido por",
        "zh": "受保护于",
        "ru": "защищён",
        "da": "beskyttes af",
        "ar": "محمي بواسطة",
    },
}
_SECURE_TRANS = {
    "label": {
        "de": "sichert",
        "fr": "sécurise",
        "es": "asegura",
        "it": "protegge",
        "pt": "protege",
        "zh": "保障",
        "ru": "обеспечивает безопасность",
        "da": "sikrer",
        "ar": "يؤمّن",
    },
    "reverse_label": {
        "de": "wird gesichert von",
        "fr": "est sécurisé par",
        "es": "está asegurado por",
        "it": "è protetto da",
        "pt": "é protegido por",
        "zh": "受保障于",
        "ru": "защищён",
        "da": "sikres af",
        "ar": "مؤمَّن بواسطة",
    },
}

_NEW_TYPES = [
    (
        "relSecCtrlToApp",
        "protects",
        "is protected by",
        "SecurityControl",
        "Application",
        80,
        _PROTECT_TRANS,
    ),
    (
        "relSecCtrlToData",
        "protects",
        "is protected by",
        "SecurityControl",
        "DataObject",
        81,
        _PROTECT_TRANS,
    ),
    (
        "relSecCtrlToITC",
        "secures",
        "is secured by",
        "SecurityControl",
        "ITComponent",
        82,
        _SECURE_TRANS,
    ),
]


def upgrade() -> None:
    conn = op.get_bind()
    for key, label, rev_label, src, tgt, sort_order, trans in _NEW_TYPES:
        exists = conn.execute(
            text("SELECT 1 FROM relation_types WHERE key = :key LIMIT 1"), {"key": key}
        ).first()
        if exists:
            continue
        conn.execute(
            text(
                "INSERT INTO relation_types "
                "(id, key, label, reverse_label, source_type_key, target_type_key, "
                "cardinality, attributes_schema, built_in, is_hidden, sort_order, translations) "
                "VALUES "
                "(:id, :key, :label, :reverse_label, :src, :tgt, 'n:m', "
                "CAST(:attrs AS jsonb), true, false, :sort_order, CAST(:trans AS jsonb))"
            ),
            {
                "id": str(uuid.uuid4()),
                "key": key,
                "label": label,
                "reverse_label": rev_label,
                "src": src,
                "tgt": tgt,
                "attrs": json.dumps([]),
                "sort_order": sort_order,
                "trans": json.dumps(trans),
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    for key, *_ in _NEW_TYPES:
        conn.execute(text("DELETE FROM relation_types WHERE key = :key"), {"key": key})
