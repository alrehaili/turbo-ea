/**
 * Per-locale card content (`cards.translations`). The plain `name` /
 * `description` / `alias` stay the English baseline; a translation only
 * overrides what it carries. Mirrors `backend/app/services/card_translations.py`.
 */
import type { CardContentTranslation, CardTranslations } from "@/types";

/** Locales a card can carry content for (the non-English runtime locales). */
export const CONTENT_LOCALES = ["ar"] as const;

export type TranslatableField = keyof CardContentTranslation;

interface TranslatableCard {
  name?: string | null;
  description?: string | null;
  alias?: string | null;
  translations?: CardTranslations | null;
}

/** The primary subtag of an i18next language (`ar-SA` → `ar`). */
export function contentLocale(language: string | undefined | null): string {
  return (language || "en").toLowerCase().split("-")[0];
}

/** `field` of `card` in `language`, falling back to the English baseline. */
export function localizedCardText(
  card: TranslatableCard,
  field: TranslatableField,
  language: string | undefined | null,
): string {
  const loc = contentLocale(language);
  const translated = card.translations?.[loc]?.[field];
  if (translated && translated.trim()) return translated;
  return card[field] ?? "";
}

/** Whether `card` carries any text in `locale`. */
export function hasTranslation(card: TranslatableCard, locale: string): boolean {
  const entry = card.translations?.[locale];
  return !!entry && Object.values(entry).some((v) => !!v && v.trim() !== "");
}

/**
 * `translations` with one field of one locale replaced. A blank value removes
 * the field, and a locale left empty is removed, so the payload matches what
 * the server stores.
 */
export function setTranslation(
  translations: CardTranslations | null | undefined,
  locale: string,
  field: TranslatableField,
  value: string,
): CardTranslations {
  const next: CardTranslations = { ...(translations ?? {}) };
  const entry: CardContentTranslation = { ...(next[locale] ?? {}) };
  if (value.trim()) entry[field] = value;
  else delete entry[field];
  if (Object.keys(entry).length) next[locale] = entry;
  else delete next[locale];
  return next;
}

/** Excel columns carrying Arabic content, with the field each fills. */
export const ARABIC_CONTENT_COLUMNS: ReadonlyArray<readonly [string, TranslatableField]> = [
  ["name_ar", "name"],
  ["description_ar", "description"],
  ["alias_ar", "alias"],
];

/** The Arabic content a sheet row carries, or undefined when its cells are empty. */
export function readArabicContent(
  raw: Record<string, unknown>,
): CardContentTranslation | undefined {
  const out: CardContentTranslation = {};
  for (const [col, field] of ARABIC_CONTENT_COLUMNS) {
    const value = raw[col];
    const text = value == null ? "" : String(value).trim();
    if (text) out[field] = text;
  }
  return Object.keys(out).length ? out : undefined;
}

/**
 * The translations an import should write over `existing`, or null when the
 * row changes nothing. Empty cells leave a stored value alone, the same rule
 * the importer applies to every other column.
 */
export function mergeArabicContent(
  existing: CardTranslations | null | undefined,
  incoming: CardTranslations | undefined,
): CardTranslations | null {
  const ar = incoming?.ar;
  if (!ar) return null;
  const current = existing?.ar ?? {};
  const mergedAr: CardContentTranslation = { ...current, ...ar };
  const changed = (Object.keys(ar) as TranslatableField[]).some(
    (k) => (current[k] ?? "") !== (ar[k] ?? ""),
  );
  if (!changed) return null;
  return { ...(existing ?? {}), ar: mergedAr };
}
