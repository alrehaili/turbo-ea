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
      remediation_submitted: 3,
      remediated: 6,
      rejected: 0,
      withdrawn: 2,
      temporal: "current_state",
    },
  },
  effectiveness: {
    compliance,
    coverage: { status: "ok", assessed: 5, population: 8, percentage: 62.5 },
    exception_resolution: {
      status: "ok",
      value: 25,
      unit: "percent",
      eligible: 8,
      outcomes: {
        remediated_on_time: 2,
        remediated_late: 1,
        withdrawn: 2,
        rejected: 0,
        awaiting_verification: 1,
        expired_unresolved: 2,
      },
      not_recorded: 3,
      rejected_requests: 4,
      basis: "verified_by_expiry",
    },
    decision_implementation: {
      status: "not_available",
      reason: { code: "decision_pending", decisions: ["D-41"], batch: "3.4" },
    },
    turnaround: {
      status: "ok",
      measure: "elapsed",
      unit: "calendar_days",
      instruments: {
        adr: {
          status: "ok",
          decisions: 3,
          median_days: 4.5,
          max_days: 12,
          not_recorded: 0,
          basis: "created_to_signed",
        },
        arb: {
          status: "not_available",
          reason: { code: "no_recorded_decisions" },
          decisions: 0,
          not_recorded: 2,
          basis: "created_to_first_decision",
        },
        exception: {
          status: "ok",
          decisions: 1,
          median_days: 2,
          max_days: 2,
          not_recorded: 5,
          basis: "requested_to_first_decision",
          not_recorded_temporal: "current_state",
        },
      },
      processing_time: {
        status: "ok",
        measure: "governance_controlled",
        unit: "calendar_days",
        instruments: {
          adr: {
            status: "not_available",
            reason: { code: "processing_not_computable" },
            decisions: 0,
            not_computable: { delay_unattributed: 3 },
          },
          arb: {
            status: "ok",
            decisions: 1,
            median_days: 1.5,
            max_days: 1.5,
            not_computable: { history_not_recorded: 2 },
          },
          exception: {
            status: "ok",
            decisions: 1,
            median_days: 2,
            max_days: 2,
            not_computable: {},
          },
        },
      },
      working_days: {
        status: "not_available",
        reason: { code: "decision_pending", decisions: ["D-38"], batch: "3.3" },
      },
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
    expect(screen.getByText(/Current state, not this period/)).toBeInTheDocument();
  });

  it("shows every unbuilt indicator as Not available with a reason, never a zero", () => {
    renderPage();
    expect(screen.getByText("Decision implementation")).toBeInTheDocument();
    expect(screen.getByText("Business value of governance")).toBeInTheDocument();
    expect(screen.getByText(/Arrives with the benefits register/)).toBeInTheDocument();
    expect(screen.getAllByText("Not available").length).toBeGreaterThanOrEqual(4);
  });

  it("shows GOV-07 elapsed days per instrument, never pooled, with untimed decisions counted apart", () => {
    renderPage();
    const card = screen.getByTestId("gov07-turnaround");
    const adr = within(card).getByTestId("gov07-created_to_signed");
    expect(adr).toHaveTextContent("Architecture decisions");
    expect(adr).toHaveTextContent("Median: 4.5 calendar days");
    expect(adr).toHaveTextContent("Slowest: 12 calendar days");
    expect(adr).toHaveTextContent("Decisions timed: 3");
    expect(adr).not.toHaveTextContent(/not recorded/i);

    // No recorded ARB decision: Not available, never a zero, and the legacy count shown.
    const arb = within(card).getByTestId("gov07-created_to_first_decision");
    expect(arb).toHaveTextContent("Not available");
    expect(arb).toHaveTextContent("Lifecycle not recorded: 2");
    expect(arb).toHaveTextContent(/deferral is not a decision/);
    expect(arb).not.toHaveTextContent("Median");

    // Exceptions decided before the history are a current-state count.
    const exc = within(card).getByTestId("gov07-requested_to_first_decision");
    expect(exc).toHaveTextContent("Decided before history was kept (current state): 5");
  });

  it("states that governance-controlled time and working days are not available", () => {
    renderPage();
    const card = screen.getByTestId("gov07-turnaround");
    expect(card).toHaveTextContent(/This is elapsed time/);
    expect(card).toHaveTextContent(/Working days: not available/);
    // The old blanket Not-available tile for turnaround is gone.
    expect(screen.queryByText(/decision transition history and a confirmed business calendar/)).toBeNull();
  });

  it("keeps every exception lifecycle state apart in Activity", () => {
    renderPage();
    expect(screen.getByText("Awaiting verification 3")).toBeInTheDocument();
    expect(screen.getByText("Remediated (verified) 6")).toBeInTheDocument();
    expect(screen.getByText("Withdrawn 2")).toBeInTheDocument();
  });

  it("shows GOV-04 as verified remediation only, with every other outcome apart", () => {
    renderPage();
    const card = screen.getByTestId("gov04-resolution");
    expect(card).toHaveTextContent("25%");
    expect(card).toHaveTextContent(/Due exceptions in this period: 8/);
    expect(within(card).getByTestId("gov04-remediated_on_time")).toHaveTextContent(
      "Remediated and verified by expiry: 2",
    );
    expect(within(card).getByTestId("gov04-withdrawn")).toHaveTextContent(
      "Withdrawn (not a remediation): 2",
    );
    expect(within(card).getByTestId("gov04-rejected")).toHaveTextContent(
      "Rejected after approval (not a remediation): 0",
    );
    expect(within(card).getByTestId("gov04-expired_unresolved")).toHaveTextContent(
      "Expired, unresolved: 2",
    );
    expect(card).toHaveTextContent("Approved before the history was kept: 3");
    expect(card).toHaveTextContent("Requests rejected in this period: 4");
    expect(card).toHaveTextContent("Exceptions (each counted once)");
    expect(within(card).queryByTestId("gov04-cycles")).toBeNull();
  });

  it("shows approval-cycle counts apart from the exception counts", () => {
    const withCycles: ExecutiveGovernanceData = {
      ...data,
      effectiveness: {
        ...data.effectiveness,
        exception_resolution: {
          ...data.effectiveness.exception_resolution,
          approval_cycles: {
            unit_of_count: "approval_cycles",
            eligible: 10,
            outcomes: {
              remediated_on_time: 2,
              remediated_late: 1,
              withdrawn: 2,
              rejected: 2,
              awaiting_verification: 1,
              expired_unresolved: 2,
            },
          },
        },
      },
    };
    useApiQuery.mockImplementation((path: string | null) =>
      path && path.includes("/reports/executive/governance")
        ? { data: withCycles, error: null, loading: false }
        : { data: null, error: null, loading: false },
    );
    renderPage();
    const card = screen.getByTestId("gov04-resolution");
    // The exception distribution is unchanged: rejected stays 0 there.
    expect(within(card).getByTestId("gov04-rejected")).toHaveTextContent(
      "Rejected after approval (not a remediation): 0",
    );
    const cycles = within(card).getByTestId("gov04-cycles");
    expect(cycles).toHaveTextContent("Approval cycles due in this period: 10");
    expect(cycles).toHaveTextContent(/never added to them/);
    expect(within(cycles).getByTestId("gov04-cycle-rejected")).toHaveTextContent(
      "Rejected after approval (not a remediation): 2",
    );
  });

  it("shows GOV-04 as Not available, never zero, when nothing fell due", () => {
    const none: ExecutiveGovernanceData = {
      ...data,
      effectiveness: {
        ...data.effectiveness,
        exception_resolution: {
          ...data.effectiveness.exception_resolution,
          status: "not_available",
          value: undefined,
          reason: { code: "no_eligible_exceptions" },
          eligible: 0,
        },
      },
    };
    useApiQuery.mockImplementation((path: string | null) =>
      path && path.includes("/reports/executive/governance")
        ? { data: none, error: null, loading: false }
        : { data: null, error: null, loading: false },
    );
    renderPage();
    const card = screen.getByTestId("gov04-resolution");
    expect(card).toHaveTextContent("Not available");
    expect(card).not.toHaveTextContent("0%");
  });

  it("shows governance-controlled time beside elapsed, with untimed records by cause", () => {
    renderPage();
    const adr = screen.getByTestId("gov07-processing-adr");
    expect(adr).toHaveTextContent("Under governance control: not available");
    expect(adr).toHaveTextContent("No recorded reason for a wait: 3");
    const arb = screen.getByTestId("gov07-processing-arb");
    expect(arb).toHaveTextContent("Under governance control: median 1.5 calendar days");
    expect(arb).toHaveTextContent("History not recorded: 2");
    expect(screen.getByTestId("gov07-processing-exception")).toHaveTextContent(
      "Under governance control: median 2 calendar days",
    );
    expect(screen.getByTestId("gov07-turnaround")).toHaveTextContent(/with a reason/);
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
