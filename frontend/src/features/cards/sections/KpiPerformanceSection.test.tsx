import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { KpiMeasurement, KpiPerformance } from "@/types";
import KpiPerformanceSection from "./KpiPerformanceSection";

vi.mock("@/api/client", () => ({ api: { get: vi.fn(), post: vi.fn() } }));
vi.mock("@/hooks/useDateFormat", () => ({
  useDateFormat: () => ({ formatDate: (v: string) => v, formatDateTime: (v: string) => v }),
}));
vi.mock("@/hooks/AuthContext", () => ({
  useOptionalAuthUser: () => ({ id: "me" }),
}));

let performance: KpiPerformance;
vi.mock("@/hooks/useApiQuery", () => ({
  useApiQuery: () => ({ data: performance, error: null, loading: false }),
}));

function row(id: string, recordedBy: string | null): KpiMeasurement {
  return {
    id,
    kind: "period",
    metric_key: null,
    kpi_card_id: "kpi-1",
    period_type: "quarter",
    period_key: "FY2026-Q3",
    period_start: "2026-04-01",
    period_end: "2026-06-30",
    observed_on: null,
    value: 42,
    unit: "%",
    source: recordedBy ? "manual" : "system",
    evidence: null,
    status: "submitted",
    frozen: false,
    recorded_by: recordedBy,
    recorded_at: "2026-07-01T00:00:00Z",
    verified_by: null,
    verified_at: null,
    supersedes_id: null,
    correction_reason: null,
  };
}

function withRows(rows: KpiMeasurement[]): KpiPerformance {
  return {
    card_id: "kpi-1",
    metric_key: null,
    target: {
      status: "none",
      value: null,
      date: null,
      baseline: null,
      unit: null,
      direction: null,
      invalidated: false,
    },
    measurements: rows,
    can_measure: false,
    can_verify: true,
    can_ratify: false,
  };
}

describe("KpiPerformanceSection", () => {
  it("never offers Verify on a value the viewer recorded", () => {
    performance = withRows([row("mine", "me")]);
    render(<KpiPerformanceSection cardId="kpi-1" />);
    expect(screen.queryByRole("button", { name: "Verify" })).toBeNull();
  });

  it("offers Verify on someone else's or the system's submitted value", () => {
    performance = withRows([row("theirs", "someone-else"), row("system", null)]);
    render(<KpiPerformanceSection cardId="kpi-1" />);
    expect(screen.getAllByRole("button", { name: "Verify" })).toHaveLength(2);
  });
});
