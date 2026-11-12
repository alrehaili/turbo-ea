"""Per-locale card content (``cards.translations``).

Shape: ``{"ar": {"name": str, "description": str, "alias": str}}``. The plain
``name`` / ``description`` / ``alias`` columns stay the English baseline; a
translation only overrides what it carries, and every read falls back to the
baseline. Pure functions, no database, so the logic carries a mutation score.
"""

from __future__ import annotations

from typing import Any

#: Locales a card may carry content for — the non-English runtime locales.
CONTENT_LOCALES: frozenset[str] = frozenset({"ar"})
#: Translatable card fields and their maximum length (``None`` = unbounded text).
TRANSLATABLE_FIELDS: dict[str, int | None] = {
    "name": 500,
    "description": 50_000,
    "alias": 500,
}


def normalize_translations(value: Any) -> dict[str, dict[str, str]]:
    """Validate and clean an incoming ``translations`` payload.

    Unknown locales or fields, non-string values and over-long strings raise
    ``ValueError``. Blank strings are dropped, and a locale left empty is
    dropped, so clearing a translation is sending it blank.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("translations must be an object")
    out: dict[str, dict[str, str]] = {}
    for locale, fields in value.items():
        if locale not in CONTENT_LOCALES:
            raise ValueError(f"unsupported translation locale: {locale}")
        if not isinstance(fields, dict):
            raise ValueError(f"translations.{locale} must be an object")
        cleaned: dict[str, str] = {}
        for field, text in fields.items():
            if field not in TRANSLATABLE_FIELDS:
                raise ValueError(f"field not translatable: {field}")
            if text is None:
                continue
            if not isinstance(text, str):
                raise ValueError(f"translations.{locale}.{field} must be a string")
            text = text.strip()
            if not text:
                continue
            limit = TRANSLATABLE_FIELDS[field]
            if limit is not None and len(text) > limit:
                raise ValueError(f"translations.{locale}.{field} exceeds {limit} characters")
            cleaned[field] = text
        if cleaned:
            out[locale] = cleaned
    return out


def localized(translations: dict | None, locale: str | None, field: str, base: str | None):
    """``field`` in ``locale`` when the card carries it, else the baseline."""
    if locale and translations:
        value = (translations.get(locale) or {}).get(field)
        if value:
            return value
    return base
