/**
 * Shared constants + colour tokens for the ADM feature.
 *
 * [FORK FEATURE]
 */

import { STATUS_COLORS, SEVERITY_COLORS } from "@/theme/tokens";
import type { AdmPhaseStatus } from "./types";

export const PHASE_STATUS_COLORS: Record<AdmPhaseStatus, string> = {
  not_started: STATUS_COLORS.neutral,
  in_progress: STATUS_COLORS.info,
  blocked: STATUS_COLORS.error,
  ready_for_gate: SEVERITY_COLORS.medium,
  approved: STATUS_COLORS.success,
  skipped: STATUS_COLORS.neutral,
};

export const PHASE_STATUS_ICONS: Record<AdmPhaseStatus, string> = {
  not_started: "radio_button_unchecked",
  in_progress: "pending",
  blocked: "block",
  ready_for_gate: "how_to_reg",
  approved: "check_circle",
  skipped: "skip_next",
};

// Icon shown on each phase tile in the timeline. Uses standard Material
// Symbols; phase_key is the source of truth on the row.
export const PHASE_ICONS: Record<string, string> = {
  preliminary: "flag",
  phase_a: "visibility",
  phase_b: "domain",
  phase_c: "apps",
  phase_d: "memory",
  phase_e: "engineering",
  phase_f: "route",
  phase_g: "gavel",
  phase_h: "sync_problem",
  requirements_management: "assignment",
};

export const ADM_PHASE_STATUSES: AdmPhaseStatus[] = [
  "not_started",
  "in_progress",
  "blocked",
  "ready_for_gate",
  "approved",
  "skipped",
];
