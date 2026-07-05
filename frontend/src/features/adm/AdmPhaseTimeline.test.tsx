/**
 * Renders AdmPhaseTimeline with a minimal fixture and asserts the visible
 * tiles + continuous chip + click behaviour.
 *
 * [FORK FEATURE]
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import "@/i18n";
import AdmPhaseTimeline from "./AdmPhaseTimeline";
import type { AdmPhase } from "./types";

function phase(overrides: Partial<AdmPhase>): AdmPhase {
  return {
    id: "id-" + (overrides.phase_key ?? "x"),
    workspace_id: "ws",
    phase_key: overrides.phase_key ?? "phase_a",
    title: overrides.title ?? "Phase A",
    description: null,
    sort_order: overrides.sort_order ?? 1,
    is_continuous: overrides.is_continuous ?? false,
    status: overrides.status ?? "not_started",
    owner_id: null,
    start_date: null,
    due_date: null,
    completed_at: null,
    completion_pct: overrides.completion_pct ?? 0,
    notes: null,
    gate_notes: null,
    approved_by: null,
    approved_at: null,
    approval_comment: null,
    approval_override_reason: null,
    required_count: overrides.required_count ?? 0,
    linked_count: overrides.linked_count ?? 0,
    waived_count: 0,
    artefacts: [],
    ...overrides,
  };
}

describe("AdmPhaseTimeline", () => {
  it("renders sequential phase tiles and continuous chip", () => {
    const phases: AdmPhase[] = [
      phase({ phase_key: "phase_a", title: "Phase A", status: "approved" }),
      phase({ phase_key: "phase_b", title: "Phase B", status: "in_progress" }),
      phase({
        phase_key: "requirements_management",
        title: "Requirements Management",
        is_continuous: true,
        sort_order: 9,
      }),
    ];
    render(<AdmPhaseTimeline phases={phases} onSelectPhase={vi.fn()} />);
    expect(screen.getByText("Phase A")).toBeInTheDocument();
    expect(screen.getByText("Phase B")).toBeInTheDocument();
    // Continuous phase surfaces below the timeline with the label + count.
    expect(screen.getByText(/Requirements Management/)).toBeInTheDocument();
  });

  it("fires onSelectPhase when a tile is clicked", () => {
    const onSelect = vi.fn();
    render(
      <AdmPhaseTimeline
        phases={[phase({ phase_key: "phase_a", title: "Phase A" })]}
        onSelectPhase={onSelect}
      />,
    );
    fireEvent.click(screen.getByText("Phase A"));
    expect(onSelect).toHaveBeenCalledWith("phase_a");
  });
});
