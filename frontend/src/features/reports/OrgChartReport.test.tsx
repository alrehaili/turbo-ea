import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import type { Card, CardType } from "@/types";

vi.mock("@/api/client", () => import("@/test/apiMock").then((m) => m.apiClientModule()));
vi.mock("@/hooks/useMetamodel", () => import("@/test/hooks").then((m) => m.useMetamodelModule()));

import { mockApi } from "@/test/apiMock";
import { hookState, withMetamodel } from "@/test/hooks";
import { renderWithProviders } from "@/test/render";
import OrgChartReport from "./OrgChartReport";

const unitType = {
  key: "OrganizationalUnit",
  label: "Organizational Unit",
  is_hidden: false,
  subtypes: [],
  fields_schema: [
    {
      section: "Details",
      fields: [
        {
          key: "unitType",
          label: "Type",
          type: "single_select",
          options: [
            { key: "ministry", label: "Ministry" },
            { key: "department", label: "Department" },
          ],
        },
      ],
    },
  ],
} as unknown as CardType;
const orgType = {
  key: "Organization",
  label: "Organization",
  is_hidden: true,
  subtypes: [{ key: "sector", label: "Sector" }],
  fields_schema: [],
} as unknown as CardType;

const card = (id: string, name: string, extra: Partial<Card> = {}) =>
  ({ id, name, type: "OrganizationalUnit", parent_id: null, attributes: {}, ...extra }) as Card;

beforeEach(() => {
  mockApi.reset();
  hookState.reset();
});

describe("OrgChartReport", () => {
  it("draws the Organizational Unit tree under NORA, with each unit's type", async () => {
    withMetamodel([orgType, unitType]);
    mockApi.on("get", "/cards?type=OrganizationalUnit&page_size=10000", {
      items: [
        card("root", "Demo Ministry", { attributes: { unitType: "ministry" } }),
        card("it", "IT Department", { parent_id: "root", attributes: { unitType: "department" } }),
      ],
    });

    renderWithProviders(<OrgChartReport />);

    expect(await screen.findByRole("link", { name: "Demo Ministry" })).toHaveAttribute(
      "href",
      "/cards/root",
    );
    expect(screen.getByRole("link", { name: "IT Department" })).toBeInTheDocument();
    expect(screen.getByText("Ministry")).toBeInTheDocument();
    expect(screen.getByText("Department")).toBeInTheDocument();
    expect(mockApi.calls.map((c) => c.path)).not.toContain(
      "/cards?type=Organization&page_size=10000",
    );
  });

  it("falls back to Organization cards and their subtypes without NORA", async () => {
    withMetamodel([{ ...orgType, is_hidden: false } as CardType]);
    mockApi.on("get", "/cards?type=Organization&page_size=10000", {
      items: [card("s", "Business Sector", { type: "Organization", subtype: "sector" })],
    });

    renderWithProviders(<OrgChartReport />);

    expect(await screen.findByRole("link", { name: "Business Sector" })).toBeInTheDocument();
    expect(screen.getByText("Sector")).toBeInTheDocument();
  });

  it("says so when there is nothing to draw", async () => {
    withMetamodel([unitType]);
    mockApi.on("get", "/cards?type=OrganizationalUnit&page_size=10000", { items: [] });

    renderWithProviders(<OrgChartReport />);

    expect(await screen.findByText("No organizational units yet.")).toBeInTheDocument();
  });

  it("shows the empty message when the request fails", async () => {
    withMetamodel([unitType]);
    mockApi.fail("get", "/cards?type=OrganizationalUnit&page_size=10000");

    renderWithProviders(<OrgChartReport />);

    expect(await screen.findByText("No organizational units yet.")).toBeInTheDocument();
  });
});
