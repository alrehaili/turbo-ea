"""Move built-in card types to the NORA 2.0 six-layer category model.

[FORK FEATURE] The four legacy EA layers ("Strategy & Transformation",
"Business Architecture", "Application & Data", "Technical Architecture")
are replaced by the six NORA 2.0 layers: Business, Beneficiary Experience,
Application, Data, Technology, Security.

Each UPDATE is guarded on both the type key and the old default category,
so admin-customised categories (and custom types that reuse the legacy
strings) are never rewritten. Mirrors the guarded Pass 4e in
``nora_profile.py`` (profile v3) — both are idempotent, whichever runs
first wins. Pattern: 072_restore_business_process_color.py.

Revision ID: 137
Revises: 136
Create Date: 2026-07-08
"""

from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "145"
down_revision: Union[str, None] = "144"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None

# (type keys, old default category, new category)
_MOVES: list[tuple[tuple[str, ...], str, str]] = [
    (
        ("Objective", "Platform", "Initiative", "KPI"),
        "Strategy & Transformation",
        "Business",
    ),
    (
        ("Organization", "BusinessCapability", "BusinessContext", "BusinessProcess"),
        "Business Architecture",
        "Business",
    ),
    (("GovService",), "Business Architecture", "Beneficiary Experience"),
    (("Application", "Interface"), "Application & Data", "Application"),
    (("DataObject", "DataExchange"), "Application & Data", "Data"),
    (
        ("ITComponent", "TechCategory", "Provider"),
        "Technical Architecture",
        "Technology",
    ),
]


def upgrade() -> None:
    for keys, old_cat, new_cat in _MOVES:
        op.execute(
            sa.text(
                "UPDATE card_types SET category = :new_cat "
                "WHERE key IN :keys AND category = :old_cat"
            ).bindparams(
                sa.bindparam("new_cat", new_cat),
                sa.bindparam("keys", list(keys), expanding=True),
                sa.bindparam("old_cat", old_cat),
            )
        )


def downgrade() -> None:
    for keys, old_cat, new_cat in _MOVES:
        op.execute(
            sa.text(
                "UPDATE card_types SET category = :old_cat "
                "WHERE key IN :keys AND category = :new_cat"
            ).bindparams(
                sa.bindparam("old_cat", old_cat),
                sa.bindparam("keys", list(keys), expanding=True),
                sa.bindparam("new_cat", new_cat),
            )
        )
