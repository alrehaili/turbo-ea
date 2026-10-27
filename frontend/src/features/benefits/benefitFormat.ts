import type { BenefitStatus, BenefitActualStatus } from "@/types";

/**
 * An amount in its own currency, exact to the cent. Benefits are never
 * converted (D-05), so the currency always travels with the number. An unknown
 * ISO code falls back to "1,234.00 XYZ" rather than throwing.
 */
export function formatMoney(value: number, currency: string, locale: string): string {
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value)} ${currency}`;
  }
}

export const BENEFIT_STATUS_COLOR: Record<BenefitStatus, "default" | "info" | "success" | "warning"> = {
  planned: "default",
  validated: "info",
  not_realised: "warning",
  withdrawn: "default",
};

export const ACTUAL_STATUS_COLOR: Record<BenefitActualStatus, "default" | "info" | "success" | "error"> = {
  reported: "info",
  confirmed: "success",
  rejected: "error",
  reversed: "default",
};

/** Evidence references from free text: one reference per non-empty line (I-69). */
export function referencesFromText(text: string): { kind: "reference"; text: string }[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => ({ kind: "reference" as const, text: line.slice(0, 500) }));
}
