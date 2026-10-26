import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import type { ExecutiveGovernanceData, ExecutiveKpi, GovernanceDrilldown, User } from "@/types";

const useApiQuery = vi.fn();
vi.mock("@/hooks/useApiQuery", () => ({ useApiQuery: (path: string | null) => useApiQuery(path) }));

import { AuthProvider } from "@/hooks/AuthContext";
import ExecutiveGovernance from "./ExecutiveGovernance";

const compliance: ExecutiveKpi = {
  key: "GOV-03",
  slot: "governance",
  calculation_version: "GOV-03@1",
  temporal: "period",
  status: "ok",
  value: 84.2,
  unit: "percent",
  target: { status: "not_linked", decision: "D-26" },
  owner: { status: "not_linked", decision: "D-26" },
  previous: { status: "not_available", reason: "no_history", decision: "D-19" },
  period: "FY2026-Q3",
  as_of: "2026-10-25",
  freshness: null,
  confidence: "high",
  provenance: "recorded",
  completeness: { numerator: 5, denominator: 8, percentage: 62.5 },
  reason: null,
  drilldown: null,
  details: {},
};

const data: ExecutiveGovernanceData = {
  generated_at: "2026-10-25T08:00:00Z",
  fiscal_year_start: 1,
  period: {
    key: "FY2026-Q3",
    fiscal_year: 2026,
    quarter: 3,
    start: "2026-07-01",
    end: "2026-09-30",
    as_of: "2026-09-30",
    is_current: false,
  },
  activity: {
    adrs_signed: 3,
    arb: { approved: 2, rejected: 1, deferred: 4, dating: "latest_decision" },
    exceptions: {
      requested: 1,
      approved_active: 2,
      expired: 1,
      rejected: 0,
      temporal: "current_state",
    },
    exception_lifecycle: { status: "not_available", reason: { code: "later_batch", batch: "3.2" } },
  },
  effectiveness: {
    compliance,
    coverage: { status: "ok", assessed: 5, population: 8, percentage: 62.5 },
    exception_resolution: { status: "not_available", reason: { code: "later_batch", batch: "3.2" } },
    decision_implementation: {
      status: "not_available",
      reason: { code: "decision_pending", decisions: ["D-41"], batch: "3.4" },
    },
    turnaround: {
      status: "not_available",
      reason: { code: "decision_pending", decisions: ["D-38", "D-39"], batch: "3.2" },
    },
  },
  impact: {
    architecture_risks: {
      status: "not_available",
      reason: { code: "decision_pending", decisions: ["D-42"], batch: "3.5" },
    },
    governed_delivery: {
      status: "not_available",
      reason: { code: "decision_pending", decisions: ["D-37"], batch: "3.6" },
    },
    business_value: { status: "not_available", reason: { code: "later_phase", phase: 4 } },
  },
};

const drill: GovernanceDrilldown = {
  key: "GOV-03",
  status: "ok",
  assessed: 5,
  compliant: 4,
  rows: [
    {
      card_id: "c1",
      card_name: "Billing",
      card_type: "Application",
      standard_name: "Legacy SOAP",
      standard_status: "prohibited",
      via: "application",
      component_name: "OldMQ",
      path: "/cards/c1",
    },
  ],
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
        <ExecutiveGovernance />
      </AuthProvider>
    </MemoryRouter>,
  );
}

function mockQueries(drilldown: GovernanceDrilldown | null = drill) {
  useApiQuery.mockImplementation((path: string | null) => {
    if (path && path.includes("/drilldown")) {
      return { data: drilldown, error: null, loading: false };
    }
    if (path && path.includes("/reports/executive/governance")) {
      return { data, error: null, loading: false };
    }
    return { data: null, error: null, loading: false };
  });
}

beforeEach(() => {
  useApiQuery.mockReset();
  mockQueries();
});

describe("ExecutiveGovernance (Batch 3.1)", () => {
  it("renders Activity, Effectiveness and Impact as three separate labelled sections", () => {
    renderPage();
    expect(screen.getByText("Activity")).toBeInTheDocument();
    expect(screen.getByText("Effectiveness")).toBeInTheDocument();
    expect(screen.getByText("Impact")).toBeInTheDocument();
  });

  it("labels compliance rule-based, shows coverage as a separate figure, and never says 'architecture compliance'", () => {
    renderPage();
    expect(screen.getByText("Technology standards compliance")).toBeInTheDocument();
    const coverage = screen.getByTestId("assessment-coverage");
    expect(coverage).toHaveTextContent("5 of 8");
    expect(coverage).toHaveTextContent("62.5%");
    // The compliance headline value is shown, not folded into coverage.
    expect(screen.getByText("84.2%")).toBeInTheDocument();
    expect(document.body.textContent?.toLowerCase()).not.toContain("architecture compliance");
  });

  it("counts deferred ARB reviews apart and labels the latest-decision-date basis", () => {
    renderPage();
    expect(screen.getByText("Deferred 4")).toBeInTheDocument();
    expect(screen.getByText("Approved 2")).toBeInTheDocument();
    expect(screen.getByText(/latest decision date/)).toBeInTheDocument();
    expect(screen.getByText(/not yet recorded/)).toBeInTheDocument();
  });

  it("shows every unbuilt indicator as Not available with a reason, never a zero", () => {
    renderPage();
    expect(screen.getByText("Decision implementation")).toBeInTheDocument();
    expect(screen.getByText("Business value of governance")).toBeInTheDocument();
    expect(screen.getByText(/Arrives with the benefits register/)).toBeInTheDocument();
    expect(screen.getAllByText("Not available").length).toBeGreaterThanOrEqual(5);
  });

  it("lists the non-compliant records behind GOV-03 when the standards permission is held", () => {
    renderPage({ "tech_standards.view": true, "inventory.view": true });
    const list = screen.getByTestId("gov03-drilldown");
    expect(within(list).getByText("Billing")).toBeInTheDocument();
    expect(within(list).getByText("Legacy SOAP")).toBeInTheDocument();
    expect(within(list).getByText(/OldMQ/)).toBeInTheDocument();
  });

  it("does not request the drill-down without the standards permission", () => {
    renderPage();
    expect(screen.queryByTestId("gov03-drilldown")).not.toBeInTheDocument();
    const drillCalls = useApiQuery.mock.calls.filter(
      ([p]) => typeof p === "string" && p.includes("/drilldown"),
    );
    // The hook is still called (hooks are unconditional) but with a null path.
    expect(drillCalls).toHaveLength(0);
  });

  it("shows Not available with its reason when compliance cannot be assessed", () => {
    const na: ExecutiveGovernanceData = {
      ...data,
      effectiveness: {
        ...data.effectiveness,
        compliance: {
          ...compliance,
          status: "not_available",
          value: null,
          reason: { code: "no_assessed_population" },
        },
        coverage: { status: "not_available", reason: { code: "no_assessed_population" } },
      },
    };
    useApiQuery.mockImplementation((path: string | null) =>
      path && path.includes("/reports/executive/governance")
        ? { data: na, error: null, loading: false }
        : { data: null, error: null, loading: false },
    );
    renderPage({ "tech_standards.view": true });
    expect(screen.getByTestId("assessment-coverage")).toHaveTextContent("not available");
    expect(screen.getByText(/governed technology standard/)).toBeInTheDocument();
  });
});
