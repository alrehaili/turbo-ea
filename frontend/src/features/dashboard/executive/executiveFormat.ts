/**
 * Pure presentation helpers for the Executive tab.
 *
 * Money is formatted in the currency the payload names (decision D-05): the
 * amounts are recorded in the instance currency and are never converted or
 * relabelled here. Symbol placement follows the locale through
 * `Intl.NumberFormat`, and the override glyph (e.g. the Saudi Riyal sign) is
 * swapped in exactly as `useCurrency` does.
 */
import type { TFunction } from "i18next";
import { currencySymbolOverride } from "@/lib/currency";
import { fiscalYearLabel } from "@/lib/fiscalYear";

/** Compact money, e.g. "$6.6M" in English or the locale's own placement. */
export function formatCompactMoney(value: number, currency: string, locale: string): string {
  let fmt: Intl.NumberFormat;
  try {
    fmt = new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      notation: "compact",
      maximumFractionDigits: 1,
    });
  } catch {
    // An unknown code must not take the page down: show the code beside the number.
    const plain = new Intl.NumberFormat(locale, { notation: "compact", maximumFractionDigits: 1 });
    return `${plain.format(value)} ${currency}`;
  }
  const override = currencySymbolOverride(currency);
  if (!override) return fmt.format(value);
  return fmt
    .formatToParts(value)
    .map((p) => (p.type === "currency" ? override : p.value))
    .join("");
}

/** A percentage with one decimal, or `null` (unknown, never zero). */
export function pct(value: number | null | undefined): string | null {
  return value === null || value === undefined ? null : `${Math.round(value * 10) / 10}%`;
}

/** The worst delivery state that has at least one initiative, for the tile colour. */
export function deliveryTone(
  states: Record<string, number> | undefined,
): "offTrack" | "atRisk" | "onTrack" | "none" {
  if (!states) return "none";
  if ((states.offTrack ?? 0) > 0) return "offTrack";
  if ((states.atRisk ?? 0) > 0) return "atRisk";
  if ((states.onTrack ?? 0) > 0) return "onTrack";
  return "none";
}

/**
 * How a period key (`FY2027` or `FY2027-Q2`) reads on screen: the fiscal year
 * named by the shared `fiscalYearLabel`, plus the quarter when there is one.
 */
export function periodLabel(key: string, startMonth: number, t: TFunction): string {
  const m = /^FY(\d{4})(?:-Q([1-4]))?$/.exec(key);
  if (!m) return key;
  const fy = fiscalYearLabel(Number(m[1]), startMonth, t);
  return m[2] ? t("common:dashboard.executive.quarterOf", { quarter: m[2], year: fy }) : fy;
}
