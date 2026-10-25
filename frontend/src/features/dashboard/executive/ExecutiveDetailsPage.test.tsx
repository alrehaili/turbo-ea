import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import type { ExecutiveDashboardData, User } from "@/types";

const useApiQuery = vi.fn();
vi.mock("@/hooks/useApiQuery", () => ({ useApiQuery: (path: string) => useApiQuery(path) }));
vi.mock("@/hooks/useMetamodel", () => ({ useMetamodel: () => ({ types: [], relationTypes: [] }) }));

import { AuthProvider } from "@/hooks/AuthContext";
import ExecutiveDetailsPage from "./ExecutiveDetailsPage";

function payload(overrides: Partial<ExecutiveDashboardData> = {}): ExecutiveDashboardData {
  return {
    generated_at: "2026-10-24T08:00:00Z",
    can_view_costs: true,
    currency: "SAR",
    ppm_enabled: true,
    portfolio: {
      status: "ok",
      total_cards: 10,
      data_completeness: 72.5,
      by_type: {},
      approval: { APPROVED: 4, DRAFT: 6 },
      lifecycle: { active: 10 },
      last_updated: "2026-10-20T08:00:00Z",
    },
    delivery: {
      status: "ok",
      source: "ppm_reports",
      staleness_days: null,
      total_initiatives: 6,
      in_flight: 5,
      excluded: { completed: 1, onHold: 0 },
      states: { onTrack: 2, atRisk: 1, offTrack: 0, notReported: 2 },
      on_track_pct: 66.7,
      coverage: {
        status: "ok",
        reported: 3,
        in_flight: 5,
        percentage: 60,
        stale_reports: 0,
        latest_report_date: "2026-10-01",
        oldest_report_date: "2026-08-01",
      },
      dimensions: null,
      budget: {
        status: "ok",
        fiscal_year: 2026,
        fiscal_year_start: 1,
        current_fiscal_year: 2026,
        available_years: [2025, 2026],
        currency: "SAR",
        budget: 1000,
        actual: 500,
        execution_pct: 50,
        undated_cost_lines: 2,
      },
    },
    processes: { status: "disabled" },
    risks: { status: "ok", open: 3, critical_high_open: 1, open_by_level: { high: 1 }, overdue: 0 },
    rationalization: {
      status: "ok",
      decisions: 3,
      applications: 2,
      by_decision: { invest: 3 },
      planned_savings: {
        status: "ok",
        provenance: "forecast",
        currency: "SAR",
        total: 100,
        applications_counted: 1,
        duplicates_merged: 0,
        conflicts: [
          {
            card_id: "c1",
            card_name: "Legacy CRM",
            candidates: [
              { assessment_id: "a1", assessment_name: "Q1 review", amount: 50 },
              { assessment_id: "a2", assessment_name: "Q2 review", amount: 70 },
            ],
          },
        ],
        excluded_range: [50, 70],
        period: { status: "blocked", decision: "D-31" },
      },
      realized_savings: { status: "not_available" },
    },
    ...overrides,
  };
}

function renderTab(url = "/?tab=executive&page=details") {
  const user: User = {
    id: "u1",
    email: "u@test",
    display_name: "U",
    role: "member",
    is_active: true,
    permissions: { "ppm.view": true, "grc.view": true },
  };
  return render(
    <MemoryRouter initialEntries={[url]}>
      <AuthProvider user={user} refreshUser={vi.fn()}>
        <ExecutiveDetailsPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  useApiQuery.mockReset();
});

describe("ExecutiveDetailsPage", () => {
  it("shows health over reporting initiatives and coverage as its own figure", () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    renderTab();
    expect(screen.getByText("66.7%")).toBeInTheDocument();
    expect(screen.getByText("3 / 5")).toBeInTheDocument();
    expect(screen.getByText(/^Unknown \/ not reported:$/)).toBeInTheDocument();
    expect(screen.getByText(/No staleness threshold is set/, { selector: "div" })).toBeInTheDocument();
  });

  it("names the fiscal year of the budget and refetches when another is chosen", async () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    renderTab();
    expect(useApiQuery).toHaveBeenLastCalledWith("/reports/executive");
    expect(screen.getAllByText(/FY 2026/).length).toBeGreaterThan(0);
    await userEvent.click(screen.getByLabelText("Reporting period"));
    await userEvent.click(await screen.findByRole("option", { name: /FY 2025/ }));
    expect(useApiQuery).toHaveBeenLastCalledWith("/reports/executive?fiscal_year=2025");
    // The kept FY 2026 payload is not shown as FY 2025 while the request runs.
    expect(screen.getByTestId("period-loading")).toBeInTheDocument();
    expect(screen.queryByText("Legacy CRM")).not.toBeInTheDocument();
  });

  it("follows the fiscal year of the period chosen on another Executive page", () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    renderTab("/?tab=executive&page=details&period=FY2026-Q3");
    expect(useApiQuery).toHaveBeenLastCalledWith("/reports/executive?fiscal_year=2026");
    expect(screen.queryByTestId("period-loading")).not.toBeInTheDocument();
  });

  it("lists conflicting savings estimates and keeps realised savings unavailable", () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    renderTab();
    expect(screen.getByText("Legacy CRM")).toBeInTheDocument();
    expect(screen.getByText(/Q1 review: .*50.* · Q2 review: .*70/)).toBeInTheDocument();
    expect(screen.getByText("Realised savings")).toBeInTheDocument();
    expect(screen.getAllByText("Not available").length).toBeGreaterThan(0);
  });

  it("shows Restricted, never a zero, without cost access", () => {
    const data = payload({ can_view_costs: false });
    data.delivery.budget = { ...data.delivery.budget!, status: "restricted" };
    delete data.delivery.budget.budget;
    data.rationalization.planned_savings = { status: "restricted", provenance: "forecast" };
    useApiQuery.mockReturnValue({ data, error: null, loading: false });
    renderTab();
    expect(screen.getAllByTestId("restricted-amount").length).toBe(2);
    expect(screen.queryByText("Legacy CRM")).not.toBeInTheDocument();
  });

  it("shows only the conflict count without rationalization access", () => {
    const data = payload();
    data.rationalization.planned_savings = {
      ...data.rationalization.planned_savings,
      conflict_count: 1,
      conflict_detail: "restricted",
      conflicts: null,
      excluded_range: null,
    };
    useApiQuery.mockReturnValue({ data, error: null, loading: false });
    renderTab();
    expect(screen.getByText(/1 application has conflicting savings estimates/)).toBeInTheDocument();
    // The headline caption still counts the conflict from `conflict_count`.
    expect(screen.getByText(/· 1 conflicts? excluded/)).toBeInTheDocument();
    expect(screen.queryByText("Legacy CRM")).not.toBeInTheDocument();
    expect(screen.queryByText(/Q1 review/)).not.toBeInTheDocument();
  });

  it("uses the corrected terminology", () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    renderTab();
    expect(screen.getByText("Data completeness")).toBeInTheDocument();
    expect(screen.getByText("Repository review status")).toBeInTheDocument();
    expect(screen.queryByText(/data quality/i)).not.toBeInTheDocument();
  });
});
