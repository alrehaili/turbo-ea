/**
 * ADM Governance Workspace client types. Mirrors the shape returned by
 * ``backend/app/api/v1/adm.py``. See ``backend/app/models/adm.py`` for the
 * corresponding SQL definitions.
 *
 * [FORK FEATURE]
 */

export type AdmPhaseStatus =
  | "not_started"
  | "in_progress"
  | "blocked"
  | "ready_for_gate"
  | "approved"
  | "skipped";

export type AdmWorkspaceStatus =
  | "draft"
  | "active"
  | "on_hold"
  | "completed"
  | "archived";

export type AdmArtefactKind =
  | "soaw"
  | "adr"
  | "arb_review"
  | "diagram"
  | "roadmap"
  | "risk"
  | "compliance_finding"
  | "tech_standard"
  | "standard_exception"
  | "rationalization_assessment"
  | "card"
  | "url"
  | "document"
  | "file_attachment"
  | "requirement";

export interface AdmArtefact {
  id: string;
  phase_id: string;
  kind: AdmArtefactKind;
  ref_id: string | null;
  ref_url: string | null;
  title: string;
  is_required: boolean;
  is_waived: boolean;
  waived_reason: string | null;
  waived_by: string | null;
  waived_at: string | null;
  linked_by: string | null;
  notes: string | null;
  sort_order: number;
  is_linked: boolean;
}

export interface AdmPhase {
  id: string;
  workspace_id: string;
  phase_key: string;
  title: string;
  description: string | null;
  sort_order: number;
  is_continuous: boolean;
  status: AdmPhaseStatus;
  owner_id: string | null;
  start_date: string | null;
  due_date: string | null;
  completed_at: string | null;
  completion_pct: number;
  notes: string | null;
  gate_notes: string | null;
  approved_by: string | null;
  approved_at: string | null;
  approval_comment: string | null;
  approval_override_reason: string | null;
  required_count: number;
  linked_count: number;
  waived_count: number;
  artefacts: AdmArtefact[];
}

export interface AdmActivePhase {
  phase_key: string;
  title: string;
  status: AdmPhaseStatus;
  due_date: string | null;
}

export interface AdmWorkspace {
  id: string;
  name: string;
  soaw_id: string | null;
  initiative_id: string | null;
  status: AdmWorkspaceStatus;
  description: string | null;
  target_completion: string | null;
  owner_id: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  phases?: AdmPhase[];
  phase_count?: number;
  approved_count?: number;
  blocked_count?: number;
  overdue_count?: number;
  active_phase?: AdmActivePhase | null;
  completion_pct?: number;
}

export interface AdmMyActions {
  pending_gate: Array<{
    id: string;
    workspace_id: string;
    phase_key: string;
    title: string;
    status: AdmPhaseStatus;
    due_date: string | null;
  }>;
  blocked: Array<{
    id: string;
    workspace_id: string;
    phase_key: string;
    title: string;
    status: AdmPhaseStatus;
    due_date: string | null;
  }>;
  overdue: Array<{
    id: string;
    workspace_id: string;
    phase_key: string;
    title: string;
    status: AdmPhaseStatus;
    due_date: string | null;
  }>;
}
