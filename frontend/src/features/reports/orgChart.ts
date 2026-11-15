/**
 * Which card type the Organization Chart draws, and how a node looks.
 *
 * Under NORA the organization is modelled with Organizational Units (the DGA
 * Content Meta Model building block); the generic Organization type is hidden
 * there and is the chart's source only on an install that does not use NORA.
 * The chart draws ONE type, so an install holding both never shows a unit twice.
 */
import type { CardType } from "@/types";

export const ORG_CHART_TYPE_KEYS = ["OrganizationalUnit", "Organization"] as const;

/** The first visible organization type, else the first that exists, else null. */
export function pickOrgChartType(types: CardType[]): CardType | null {
  const candidates = ORG_CHART_TYPE_KEYS.map((key) => types.find((t) => t.key === key)).filter(
    (t): t is CardType => t !== undefined,
  );
  return candidates.find((t) => !t.is_hidden) ?? candidates[0] ?? null;
}

// Organization subtypes and Organizational Unit `unitType` values → icon.
const ORG_NODE_ICONS: Record<string, string> = {
  ministry: "account_balance",
  authority: "account_balance",
  agency: "account_balance",
  sector: "account_balance",
  generalDepartment: "domain",
  publicAdministration: "domain",
  department: "apartment",
  sectionUnit: "work",
};

/** The value that classifies a node: the subtype, or a unit's `unitType`. */
export function orgNodeKind(card: {
  subtype?: string | null;
  attributes?: Record<string, unknown> | null;
}): string | null {
  if (card.subtype) return card.subtype;
  const unitType = card.attributes?.unitType;
  return typeof unitType === "string" && unitType ? unitType : null;
}

export function orgNodeIcon(kind: string | null): string {
  return (kind && ORG_NODE_ICONS[kind]) || "corporate_fare";
}
