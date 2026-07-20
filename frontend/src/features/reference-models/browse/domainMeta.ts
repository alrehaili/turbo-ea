/**
 * Shared per-domain presentation metadata for the Reference Model browse
 * pages (RMPlan Phase 1). Colors come from the six-layer design tokens so
 * the browse UI matches the Layers views for the same domain.
 *
 * [FORK FEATURE] — Reference Models browse (RMPlan/rmPlan.md).
 */
import { LAYER_COLORS } from "@/theme";
import type { ReferenceModelDomain } from "@/types";

export interface RmDomainMeta {
  /** Short model code shown on chips (always LTR). */
  code: string;
  icon: string;
  color: string;
}

export const RM_DOMAIN_ORDER: ReferenceModelDomain[] = [
  "business",
  "beneficiaryExperience",
  "applications",
  "data",
  "technology",
  "security",
];

export const RM_DOMAIN_META: Record<ReferenceModelDomain, RmDomainMeta> = {
  business: { code: "BRM", icon: "domain", color: LAYER_COLORS.Business },
  beneficiaryExperience: {
    code: "BXRM",
    icon: "diversity_3",
    color: LAYER_COLORS["Beneficiary Experience"],
  },
  applications: { code: "ARM", icon: "apps", color: LAYER_COLORS.Application },
  data: { code: "DRM", icon: "database", color: LAYER_COLORS.Data },
  technology: { code: "TRM", icon: "memory", color: LAYER_COLORS.Technology },
  security: { code: "SRM", icon: "security", color: LAYER_COLORS.Security },
};

export function isRmDomain(value: string | undefined): value is ReferenceModelDomain {
  return !!value && value in RM_DOMAIN_META;
}

/**
 * Column palette for the visual capability-map view (RMPlan Phase 3 / §18).
 * Mirrors the reference-image poster: each top-level column gets its own hue,
 * cycling if a model has more columns than colours.
 */
export const RM_MAP_PALETTE = [
  "#4f7a3a", // green
  "#2f6f6a", // teal
  "#2f5c8f", // blue
  "#3f6f7a", // steel
  "#6a4a8f", // purple
  "#a8792f", // gold
  "#8f3f5c", // magenta
  "#3a5a7a", // slate
] as const;

