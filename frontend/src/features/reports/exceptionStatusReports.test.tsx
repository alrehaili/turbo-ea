import type { ReactNode } from "react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const get = vi.fn();
vi.mock("@/api/client", () => ({ api: { get: (path: string) => get(path) } }));
vi.mock("./ReportShell", () => ({
  default: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

import ExceptionWaiverMatrix from "./ExceptionWaiverMatrix";
import StandardsComplianceMatrix from "./StandardsComplianceMatrix";

const standards = [{ id: "s1", name: "Legacy SOAP", mandate: "mandatory" }];
const future = "2099-01-01";

function exc(id: string, status: string, card: string, extra: Record<string, unknown> = {}) {
  return { id, standard_id: "s1", status, expiry_date: future, card: { id: card, name: `App ${id}` }, ...extra };
}

/**
 * Both report pages read the exception register (D-40). A remediated or
 * withdrawn exception is closed and no longer a waiver; a submitted but
 * unverified remediation still waives until its expiry.
 */
describe("exception register consumers (D-40 states)", () => {
  beforeEach(() => get.mockReset());

  it("ExceptionWaiverMatrix lists only open waivers and keeps a submitted remediation approved", async () => {
    const register = [
      exc("open", "approved", "c1"),
      exc("pending", "remediation_submitted", "c2"),
      exc("closed", "remediated", "c3"),
      exc("gone", "withdrawn", "c4"),
    ];
    get.mockImplementation((path: string) =>
      Promise.resolve(path === "/tech-standards" ? standards : register),
    );
    render(<ExceptionWaiverMatrix />);
    expect(await screen.findByText("App open")).toBeInTheDocument();
    expect(screen.getByText("App pending")).toBeInTheDocument();
    expect(screen.queryByText("App closed")).toBeNull();
    expect(screen.queryByText("App gone")).toBeNull();
    expect(screen.queryByText("pending")).toBeNull(); // the submitted one reads approved
    expect(screen.getAllByText("approved")).toHaveLength(2);
  });

  it("StandardsComplianceMatrix counts only live waivers against an app", async () => {
    const apps = [
      { id: "a-live", name: "Live waiver" },
      { id: "a-sub", name: "Awaiting verification" },
      { id: "a-done", name: "Remediated" },
      { id: "a-wd", name: "Withdrawn" },
      { id: "a-late", name: "Past expiry" },
    ];
    const register = [
      exc("1", "approved", "a-live"),
      exc("2", "remediation_submitted", "a-sub"),
      exc("3", "remediated", "a-done"),
      exc("4", "withdrawn", "a-wd"),
      exc("5", "remediation_submitted", "a-late", { past_expiry: true }),
    ];
    get.mockImplementation((path?: string) => {
      if (path?.startsWith("/cards")) return Promise.resolve({ items: apps });
      if (path === "/tech-standards") return Promise.resolve(standards);
      return Promise.resolve(register);
    });
    render(<StandardsComplianceMatrix />);
    await screen.findByText("Live waiver");
    const rate = (name: string) => screen.getByText(name).closest("tr")?.textContent ?? "";
    // One column: a live waiver makes the app non-compliant with it (0 %).
    expect(rate("Live waiver")).not.toContain("100%");
    expect(rate("Live waiver")).toMatch(/(^|\D)0%/);
    expect(rate("Awaiting verification")).not.toContain("100%");
    expect(rate("Remediated")).toContain("100%");
    expect(rate("Withdrawn")).toContain("100%");
    expect(rate("Past expiry")).toContain("100%");
  });
});
