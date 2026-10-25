import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import type { ExecutiveKpi, ExecutiveOverviewData, User } from "@/types";

const useApiQuery = vi.fn();
vi.mock("@/hooks/useApiQuery", () => ({ useApiQuery: (path: string) => useApiQuery(path) }));

import { AuthProvider } from "@/hooks/AuthContext";
import ExecutiveOverview from "./ExecutiveOverview";

function tile(slot: ExecutiveKpi["slot"], overrides: Partial<ExecutiveKpi> = {}): ExecutiveKpi {
  return {
    key: slot,
    slot,
    calculation_version: `${slot}@1`,
    temporal: "period",
    status: "not_available",
    value: null,
    unit: null,
    target: { status: "not_linked" },
    owner: { status: "not_linked" },
    previous: { status: "not_available", reason: "no_history" },
    period: "FY2026-Q4",
    as_of: "2026-10-25",
    freshness: null,
    confidence: null,
    provenance: null,
    completeness: null,
    reason: { code: "decision_pending", decisions: ["D-21"] },
    drilldown: null,
    details: {},
    ...overrides,
  };
}

const delivery = tile("delivery", {
  status: "ok",
  value: 83.3,
  unit: "percent",
  reason: null,
  confidence: "low",
  provenance: "reported",
  freshness: "2026-03-03",
  previous: { status: "not_available", reason: "historical_unavailable", period: "FY2026-Q3" },
  completeness: { numerator: 6, denominator: 17, percentage: 35.3 },
  drilldown: { api: "TR-03", path: "/ppm" },
  details: {
    source: "ppm_reports",
    states: { onTrack: 5, atRisk: 0, offTrack: 1, notReported: 11 },
    excluded: { completed: 2, onHold: 1 },
    staleness_days: null,
    stale_reports: 0,
    oldest_report_date: "2025-12-01",
  },
});

const decisions = tile("decisions", {
  temporal: "current_state",
  period: null,
  status: "ok",
  value: 1,
  unit: "count",
  reason: null,
  confidence: "high",
  provenance: "recorded",
  drilldown: { api: "DEC-01", path: "/?tab=executive&page=decisions" },
  details: { open_risks: 8, mitigated_risks: 1, operational_pipeline: { adrs: 1, arb: 2, exceptions: 1 } },
});

const value = tile("value", {
  reason: { code: "later_phase", phase: 4 },
  drilldown: { path: "/rationalization" },
  details: { forecast: { status: "restricted", provenance: "forecast", temporal: "current_state" } },
});

function payload(overrides: Partial<ExecutiveOverviewData> = {}): ExecutiveOverviewData {
  const period = {
    key: "FY2026-Q4",
    fiscal_year: 2026,
    quarter: 4,
    start: "2026-10-01",
    end: "2026-12-31",
    as_of: "2026-10-25",
    is_current: true,
  };
  return {
    generated_at: "2026-10-25T08:00:00Z",
    period,
    previous_period: { ...period, key: "FY2026-Q3", quarter: 3, is_current: false },
    available_periods: ["FY2026", "FY2026-Q4", "FY2026-Q3"],
    fiscal_year_start: 1,
    currency: "USD",
    kpis: [tile("strategy"), tile("governance"), delivery, tile("services"), value, decisions],
    escalations_panel: { status: "ok", count: 0, items: [], more: 0 },
    ...overrides,
  };
}

function renderPage(permissions: Record<string, boolean> = {}, url = "/?tab=executive&page=overview") {
  const user: User = {
    id: "u1",
    email: "u@test",
    display_name: "U",
    role: "exec",
    is_active: true,
    permissions,
  };
  return render(
    <MemoryRouter initialEntries={[url]}>
      <AuthProvider user={user} refreshUser={vi.fn()}>
        <ExecutiveOverview />
      </AuthProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  useApiQuery.mockReset();
});

describe("ExecutiveOverview — escalations panel (H-3, M-1)", () => {
  it("shows the count and why records are withheld, never 'nothing needs attention'", () => {
    useApiQuery.mockReturnValue({
      data: payload({ escalations_panel: { status: "restricted", count: 3, items: [], more: 0 } }),
      error: null,
      loading: false,
    });
    renderPage();
    const restricted = screen.getByTestId("escalations-restricted");
    expect(within(restricted).getByText("3 escalated risks")).toBeInTheDocument();
    expect(within(restricted).getByText(/needs permission to view the risk register/)).toBeInTheDocument();
    expect(screen.queryByText(/No risk currently meets/)).not.toBeInTheDocument();
  });

  it("says no risk meets the criteria only when the count is zero", () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    renderPage();
    expect(screen.getByText("No risk currently meets the executive-escalation criteria.")).toBeInTheDocument();
  });

  it("lists escalations under the executive title and points to the rest", () => {
    useApiQuery.mockReturnValue({
      data: payload({
        escalations_panel: {
          status: "ok",
          count: 6,
          more: 1,
          items: [
            {
              kind: "risk",
              id: "r1",
              reference: "R-000004",
              title: "Plain-text credentials",
              level: "high",
              age_days: 4,
              path: "/grc/risks/r1",
            },
          ],
        },
      }),
      error: null,
      loading: false,
    });
    renderPage({ "risks.view": true });
    expect(screen.getByText("Executive escalations")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "R-000004 · Plain-text credentials" })).toHaveAttribute(
      "href",
      "/grc/risks/r1",
    );
    expect(screen.getByText("and 1 more on the Decisions page")).toBeInTheDocument();
  });
});

describe("ExecutiveOverview — period consistency (H-1, H-2)", () => {
  it("labels current-state tiles as such instead of the selected period", () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    renderPage();
    const tileEl = screen.getByTestId("executive-kpi-decisions");
    expect(within(tileEl).getByTestId("current-state-chip")).toBeInTheDocument();
    expect(within(tileEl).getByText(/^Current state · as of/)).toBeInTheDocument();
    expect(within(tileEl).queryByText(/Q4 · FY 2026/)).not.toBeInTheDocument();
    expect(within(tileEl).getByText("Operational governance pipeline: 4 items, not escalated")).toBeInTheDocument();
    // A period tile keeps the period.
    expect(within(screen.getByTestId("executive-kpi-delivery")).getByText(/Q4 · FY 2026/)).toBeInTheDocument();
  });

  it("shows historical data unavailable for a finished period and says why", () => {
    const pastPeriod = {
      key: "FY2024",
      fiscal_year: 2024,
      quarter: null,
      start: "2024-01-01",
      end: "2024-12-31",
      as_of: "2024-12-31",
      is_current: false,
    };
    useApiQuery.mockReturnValue({
      data: payload({
        period: pastPeriod,
        kpis: [
          tile("strategy"),
          tile("governance"),
          tile("delivery", {
            period: "FY2024",
            reason: { code: "historical_unavailable" },
            previous: { status: "not_available", reason: "historical_unavailable", period: "FY2023" },
          }),
          tile("services"),
          value,
          decisions,
        ],
      }),
      error: null,
      loading: false,
    });
    renderPage();
    expect(screen.getByTestId("past-period-notice")).toHaveTextContent(/has ended/);
    const tileEl = screen.getByTestId("executive-kpi-delivery");
    expect(within(tileEl).getAllByText("Historical data unavailable").length).toBe(2); // value + previous
    expect(within(tileEl).queryByText(/on track/)).not.toBeInTheDocument();
  });
});

describe("ExecutiveOverview — delivery confidence (M-3)", () => {
  it("puts coverage beside health and states the shortfall and the unset threshold", () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    renderPage();
    expect(screen.getByTestId("delivery-coverage")).toHaveTextContent(
      "Reporting coverage 35.3%: 6 of 17 in-flight initiatives",
    );
    const warnings = screen.getByTestId("delivery-warnings");
    expect(warnings).toHaveTextContent("11 of 17 in-flight initiatives have no current status report");
    expect(warnings).toHaveTextContent("No report staleness threshold is configured");
  });

  it("raises no warning when every in-flight initiative reported within a set threshold", () => {
    const full = {
      ...delivery,
      completeness: { numerator: 4, denominator: 4, percentage: 100 },
      details: { ...delivery.details, staleness_days: 90 },
    };
    useApiQuery.mockReturnValue({
      data: payload({ kpis: [tile("strategy"), tile("governance"), full, tile("services"), value, decisions] }),
      error: null,
      loading: false,
    });
    renderPage();
    expect(screen.queryByTestId("delivery-warnings")).not.toBeInTheDocument();
  });
});

describe("ExecutiveOverview — drill-down permissions (M-5)", () => {
  it("offers a module's records only to a holder of that module's view permission", () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    const { unmount } = renderPage();
    expect(within(screen.getByTestId("executive-kpi-value")).queryByText("View records")).not.toBeInTheDocument();
    expect(within(screen.getByTestId("executive-kpi-delivery")).queryByText("View records")).not.toBeInTheDocument();
    unmount();
    renderPage({ "rationalization.view": true, "ppm.view": true });
    expect(within(screen.getByTestId("executive-kpi-value")).getByText("View records")).toBeInTheDocument();
    expect(within(screen.getByTestId("executive-kpi-delivery")).getByText("View records")).toBeInTheDocument();
  });
});

describe("ExecutiveOverview — executive wording (M-2)", () => {
  it("explains unavailable figures in plain words, with no decision IDs or phases", () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    const { container } = renderPage();
    expect(
      within(screen.getByTestId("executive-kpi-strategy")).getByText(
        "Shown once strategic KPIs have ratified targets and verified measurements.",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("executive-kpi-value")).getByText("Shown once realised benefits are confirmed by Finance."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("No approved target yet").length).toBe(6);
    expect(container.textContent).not.toMatch(/\bD-\d+\b|\bphase \d/i);
    expect(container.textContent).not.toMatch(/FY\d{4}-Q\d/); // no raw period keys
  });
});

describe("ExecutiveOverview — period in the URL (M-4)", () => {
  it("requests the period named in the URL", () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    renderPage({}, "/?tab=executive&page=overview&period=FY2026-Q4");
    expect(useApiQuery).toHaveBeenLastCalledWith("/reports/executive/overview?period=FY2026-Q4");
  });

  it("shows no figure from the previous period while the next one loads", () => {
    // The kept payload is FY2026-Q4; the URL asks for FY2026-Q3.
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: true });
    renderPage({}, "/?tab=executive&page=overview&period=FY2026-Q3");
    expect(screen.getByTestId("period-loading")).toHaveTextContent("Loading the figures for Q3 · FY 2026");
    expect(screen.queryByTestId("executive-kpi-delivery")).not.toBeInTheDocument();
    expect(screen.queryByTestId("escalations-panel")).not.toBeInTheDocument();
    expect(screen.queryByText("83.3% on track")).not.toBeInTheDocument();
  });

  it("writes a newly chosen period to the URL and requests it", async () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    renderPage();
    await userEvent.click(screen.getByLabelText("Reporting period"));
    await userEvent.click(await screen.findByRole("option", { name: "Q3 · FY 2026" }));
    expect(useApiQuery).toHaveBeenLastCalledWith("/reports/executive/overview?period=FY2026-Q3");
  });

  it("offers the way back when the URL names a period the page cannot show", async () => {
    useApiQuery.mockImplementation((path: string) =>
      path.includes("period=")
        ? { data: undefined, error: new Error("period has not started yet"), loading: false }
        : { data: payload(), error: null, loading: false },
    );
    renderPage({}, "/?tab=executive&page=overview&period=FY2027");
    await userEvent.click(screen.getByRole("button", { name: "Show the current period" }));
    expect(useApiQuery).toHaveBeenLastCalledWith("/reports/executive/overview");
    expect(screen.getByTestId("executive-kpi-delivery")).toBeInTheDocument();
  });

  it("carries the period into the link to the Decisions page", () => {
    useApiQuery.mockReturnValue({ data: payload(), error: null, loading: false });
    renderPage({}, "/?tab=executive&page=overview&period=FY2026-Q4");
    expect(screen.getByRole("link", { name: "All decisions and escalations" })).toHaveAttribute(
      "href",
      "/?tab=executive&page=decisions&period=FY2026-Q4",
    );
  });
});

describe("ExecutiveOverview — mobile and RTL titles (M-7)", () => {
  it("wraps record titles instead of truncating them", () => {
    useApiQuery.mockReturnValue({
      data: payload({
        escalations_panel: {
          status: "ok",
          count: 1,
          more: 0,
          items: [
            {
              kind: "risk",
              id: "r1",
              reference: "R-000004",
              title: "Overdue: Jenkins credentials stored in plain-text config",
              level: "high",
              age_days: 4,
              path: "/grc/risks/r1",
            },
          ],
        },
      }),
      error: null,
      loading: false,
    });
    renderPage({ "risks.view": true });
    const link = screen.getByRole("link", { name: /R-000004/ });
    expect(link.className).not.toMatch(/noWrap/);
    expect(link).toHaveAttribute("dir", "auto");
  });
});
