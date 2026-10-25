import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import type { ExecutiveDecisionsData, User } from "@/types";

const useApiQuery = vi.fn();
vi.mock("@/hooks/useApiQuery", () => ({ useApiQuery: (path: string) => useApiQuery(path) }));

import { AuthProvider } from "@/hooks/AuthContext";
import ExecutiveDecisions from "./ExecutiveDecisions";

const data: ExecutiveDecisionsData = {
  generated_at: "2026-10-25T08:00:00Z",
  risks: { status: "restricted", group: "executive_escalation", count: 2, items: null, open: 8, mitigated: 1 },
  adrs: {
    status: "ok",
    group: "operational_pipeline",
    count: 1,
    items: [
      {
        kind: "adr",
        id: "a1",
        reference: "ADR-006",
        title: "Consolidate warehouse",
        pending_signatures: 2,
        age_days: 4,
        path: "/ea-delivery/adr/a1/preview",
      },
    ],
  },
  arb: { status: "ok", group: "operational_pipeline", count: 0, items: [] },
  exceptions: { status: "restricted", group: "operational_pipeline", count: 0, items: null },
};

function renderPage(permissions: Record<string, boolean> = {}) {
  const user: User = {
    id: "u1",
    email: "u@test",
    display_name: "U",
    role: "exec",
    is_active: true,
    permissions,
  };
  return render(
    <MemoryRouter>
      <AuthProvider user={user} refreshUser={vi.fn()}>
        <ExecutiveDecisions />
      </AuthProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  useApiQuery.mockReset();
  useApiQuery.mockReturnValue({ data, error: null, loading: false });
});

describe("ExecutiveDecisions (H-3, M-1)", () => {
  it("keeps escalations and the operational pipeline in separate groups", () => {
    renderPage({ "adr.view": true });
    const escalations = screen.getByTestId("group-executive_escalation");
    const pipeline = screen.getByTestId("group-operational_pipeline");
    expect(within(escalations).getByText("Executive-escalated risks")).toBeInTheDocument();
    expect(within(escalations).queryByText("Consolidate warehouse", { exact: false })).not.toBeInTheDocument();
    expect(within(pipeline).getByText("Operational governance pipeline")).toBeInTheDocument();
    expect(within(pipeline).getByText(/not executive escalations/)).toBeInTheDocument();
    expect(within(pipeline).getByText("ADR-006 · Consolidate warehouse")).toBeInTheDocument();
  });

  it("says records are withheld when a count exists, and nothing pending when it does not", () => {
    renderPage();
    const restricted = screen.getAllByTestId("section-restricted");
    // risks: 2 withheld; exceptions: restricted but none pending.
    expect(restricted[0]).toHaveTextContent(/You can see how many there are, but not the records/);
    expect(restricted[1]).toHaveTextContent("Nothing pending.");
  });
});
