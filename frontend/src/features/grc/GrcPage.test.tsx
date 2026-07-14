import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/hooks/AuthContext";
import type { User } from "@/types";

vi.mock("@/api/client", () => ({
  api: { get: vi.fn(), post: vi.fn() },
}));

// Risk register pulls a lot of state — stub it.
vi.mock("@/features/grc/risk/RiskRegisterPage", () => ({
  default: () => <div data-testid="risk-register" />,
}));

vi.mock("@/features/grc/compliance/ComplianceScanner", () => ({
  default: () => <div data-testid="compliance-scanner" />,
}));

// ComplianceTab wraps ComplianceScanner. Stub the wrapper directly so this
// smoke test doesn't depend on useAiStatus's network call; the gate is
// exercised by ComplianceTab.test.tsx.
vi.mock("./compliance/ComplianceTab", () => ({
  default: () => <div data-testid="compliance-scanner" />,
}));

import { api } from "@/api/client";
import GrcPage from "./GrcPage";

beforeEach(() => {
  vi.clearAllMocks();
  // /metamodel/principles, /adr → empty arrays.
  vi.mocked(api.get).mockResolvedValue([]);
});

// The governance panels (Principles / Decisions) read the current user from
// AuthContext to gate their admin CRUD affordances. A plain member without
// admin.metamodel keeps this smoke test on the read-only branch.
const memberUser: User = {
  id: "u1",
  email: "u@example.com",
  display_name: "U",
  role: "member",
  is_active: true,
  permissions: {},
};

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider user={memberUser} refreshUser={async () => {}}>
        <Routes>
          <Route path="/grc" element={<GrcPage />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("GrcPage", () => {
  it("renders the GRC page title and three top-level tabs", async () => {
    renderAt("/grc");
    expect(await screen.findByRole("heading", { name: /GRC/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Governance/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Risk/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Compliance/i })).toBeInTheDocument();
  });

  it("defaults to the Governance tab and lands on the Principles sub-tab", async () => {
    renderAt("/grc");
    // With no principles seeded, the panel renders its empty-state copy.
    // Two nested lazy() boundaries (GovernanceTab → PrinciplesPanel) resolve
    // slowly under full-suite worker contention — allow more than the 1s default.
    expect(
      await screen.findByText(/No active principles yet/i, undefined, { timeout: 5000 }),
    ).toBeInTheDocument();
  });

  it("renders the embedded Risk Register when ?tab=risk", async () => {
    renderAt("/grc?tab=risk");
    await waitFor(() =>
      expect(screen.getByTestId("risk-register")).toBeInTheDocument(),
    );
  });

  it("renders the embedded Compliance scanner when ?tab=compliance", async () => {
    renderAt("/grc?tab=compliance");
    await waitFor(() =>
      expect(screen.getByTestId("compliance-scanner")).toBeInTheDocument(),
    );
  });
});
