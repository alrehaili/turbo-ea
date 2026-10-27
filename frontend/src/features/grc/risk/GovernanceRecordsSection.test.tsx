import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import type { RiskGovernanceLink } from "@/types";

const get = vi.fn();
const post = vi.fn();
const del = vi.fn();
vi.mock("@/api/client", () => ({
  api: {
    get: (...a: unknown[]) => get(...a),
    post: (...a: unknown[]) => post(...a),
    delete: (...a: unknown[]) => del(...a),
  },
  isAbortError: () => false,
}));

import GovernanceRecordsSection from "./GovernanceRecordsSection";
import LinkedRisksList from "./LinkedRisksList";

const link: RiskGovernanceLink = {
  instrument: "adr",
  record_id: "a1",
  label: "ADR-001 — Event bus",
  status: "signed",
  approved: true,
  path: "/ea-delivery/adr/a1/preview",
  linked_at: null,
};

function serve(links: RiskGovernanceLink[]) {
  get.mockImplementation((path: string) => {
    if (path.endsWith("/governance-links")) return Promise.resolve({ links });
    if (path === "/adr") {
      return Promise.resolve([
        { id: "a1", reference_number: "ADR-001", title: "Event bus" },
        { id: "a2", reference_number: "ADR-002", title: "API gateway" },
      ]);
    }
    return Promise.resolve([]);
  });
}

function renderSection(canManage: boolean) {
  return render(
    <MemoryRouter>
      <GovernanceRecordsSection riskId="r1" canManage={canManage} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  get.mockReset();
  post.mockReset().mockResolvedValue({});
  del.mockReset().mockResolvedValue({});
});

describe("GovernanceRecordsSection", () => {
  it("lists the linked records with their type and approval", async () => {
    serve([link]);
    renderSection(false);
    expect(await screen.findByText("ADR-001 — Event bus")).toBeInTheDocument();
    expect(screen.getByText("Decision record")).toBeInTheDocument();
    expect(screen.getByText("Approved")).toBeInTheDocument();
    // Read-only without risks.manage.
    expect(screen.queryByRole("button", { name: "Remove link" })).toBeNull();
  });

  it("says when nothing is linked", async () => {
    serve([]);
    renderSection(false);
    expect(await screen.findByText("No governance record linked.")).toBeInTheDocument();
  });

  it("removes one link at a time", async () => {
    serve([link]);
    renderSection(true);
    fireEvent.click(await screen.findByRole("button", { name: "Remove link" }));
    await waitFor(() => expect(del).toHaveBeenCalledWith("/risks/r1/governance-links/adr/a1"));
  });

  it("links a record picked from the visible ones, without offering linked ones", async () => {
    serve([link]);
    renderSection(true);
    await screen.findByText("ADR-001 — Event bus");
    const input = screen.getByLabelText("Link a governance record");
    fireEvent.mouseDown(input);
    fireEvent.change(input, { target: { value: "ADR" } });
    expect(await screen.findByText("ADR-002 — API gateway")).toBeInTheDocument();
    expect(screen.getAllByText("ADR-001 — Event bus")).toHaveLength(1);
    fireEvent.click(screen.getByText("ADR-002 — API gateway"));
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/risks/r1/governance-links", {
        instrument: "adr",
        record_id: "a2",
      }),
    );
  });
});

describe("LinkedRisksList", () => {
  it("lists the linked risks with escalation", async () => {
    get.mockResolvedValue({
      risks: [
        {
          id: "r1",
          reference: "R-000001",
          title: "Vendor lock-in",
          level: "critical",
          status: "identified",
          escalated: true,
          path: "/grc/risks/r1",
        },
      ],
    });
    render(
      <MemoryRouter>
        <LinkedRisksList kind="adr" recordId="a1" />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Vendor lock-in")).toBeInTheDocument();
    expect(screen.getByText("Escalated")).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("/adr/a1/risks", expect.anything());
  });

  it("renders nothing when the reader may not see risks", async () => {
    get.mockRejectedValue(new Error("403"));
    const { container } = render(
      <MemoryRouter>
        <LinkedRisksList kind="arb" recordId="v1" />
      </MemoryRouter>,
    );
    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });
});
