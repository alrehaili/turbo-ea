/**
 * DGA maturity model helpers for the maturity page.
 *
 * The eight built-in domains come from DGA's "Enterprise Architecture
 * Establishment for Government Entities" (DGA-1-2-1-211 §4.5). Their names are
 * data (admin-editable), so a translated name is shown only while the stored
 * name is still the seeded English one — an admin's rename always wins.
 */
import type { TFunction } from "i18next";

/** The fixed 1–5 scale; 0 is "not assessed". */
export const MATURITY_MAX_LEVEL = 5;

/** DGA grants its National EA accreditation from level 3 ("Functioning"). */
export const DGA_ACCREDITATION_LEVEL = 3;

/** The seeded English name of each DGA domain (backend `DEFAULT_MATURITY_DIMENSIONS`). */
export const DGA_DOMAIN_DEFAULT_NAMES: Readonly<Record<string, string>> = {
  dga_strategic_alignment: "Strategic Alignment",
  dga_management_support: "Corporate Management Support",
  dga_framework_deliverables: "EA Framework and Deliverables",
  dga_governance_management: "EA Governance and Management",
  dga_capability: "EA Capability",
  dga_architecture_content: "Architecture Content",
  dga_digital_transformation: "EA Role in the Digital Transformation",
  dga_value_realization: "Value Realization",
};

/** The name to show for a dimension in the interface language. */
export function dimensionLabel(key: string, storedName: string, t: TFunction): string {
  if (DGA_DOMAIN_DEFAULT_NAMES[key] !== storedName) return storedName;
  return t(`reports:maturity.builtinDimension.${key}`, { defaultValue: storedName });
}

/**
 * The average level (one decimal) behind an overall score: the score is the
 * weighted level average as a share of the top level, so 60% is level 3.0.
 */
export function averageLevel(overallScore: number | null | undefined): number | null {
  if (overallScore == null) return null;
  return Math.round((overallScore / 100) * MATURITY_MAX_LEVEL * 10) / 10;
}

/** Whether an overall score reaches DGA's accreditation level. */
export function isAccreditationReady(overallScore: number | null | undefined): boolean {
  const level = averageLevel(overallScore);
  return level != null && level >= DGA_ACCREDITATION_LEVEL;
}
