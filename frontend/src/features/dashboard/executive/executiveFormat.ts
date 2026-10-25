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
import { isRtlLocale } from "@/i18n";
import { currencySymbolOverride } from "@/lib/currency";
import { fiscalYearLabel } from "@/lib/fiscalYear";
import type { ExecutiveKpi } from "@/types";

/** Left-to-right isolate around a currency code or sign (LRI … PDI). */
const LRI = String.fromCharCode(0x2066);
const PDI = String.fromCharCode(0x2069);
const LTR_ISOLATE = (text: string) => `${LRI}${text}${PDI}`;

/**
 * Compact money, e.g. "$6.6M" in English or the locale's own placement.
 *
 * In a right-to-left locale the currency part ("US$", "SAR") is isolated as a
 * left-to-right run: its "$" is a neutral character that would otherwise take
 * the paragraph's direction and display as "$US".
 */
export function formatCompactMoney(value: number, currency: string, locale: string): string {
  const rtl = isRtlLocale(locale);
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
    return `${plain.format(value)} ${rtl ? LTR_ISOLATE(currency) : currency}`;
  }
  const override = currencySymbolOverride(currency);
  if (!override && !rtl) return fmt.format(value);
  return fmt
    .formatToParts(value)
    .map((p) => {
      if (p.type !== "currency") return p.value;
      const symbol = override ?? p.value;
      return rtl ? LTR_ISOLATE(symbol) : symbol;
    })
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

/**
 * Why a KPI is not shown, in words an executive can act on. The payload still
 * names the open decisions and the delivery phase (for the project records);
 * the screen says what has to be agreed or confirmed instead of citing "D-21"
 * or "phase 3".
 */
export function unavailableReason(kpi: Pick<ExecutiveKpi, "slot" | "reason">, t: TFunction): string {
  const fallback = t("common:dashboard.executive.ceo.unavailableBecause.default");
  const code = kpi.reason?.code;
  if (code === "decision_pending" || code === "later_phase") {
    return t(`common:dashboard.executive.ceo.unavailableBecause.${kpi.slot}`, { defaultValue: fallback });
  }
  return t(`common:dashboard.executive.reason.${code}`, { defaultValue: fallback });
}
