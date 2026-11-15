import { describe, expect, it } from "vitest";
import type { CardType } from "@/types";
import { orgNodeIcon, orgNodeKind, pickOrgChartType } from "./orgChart";

const type = (key: string, is_hidden = false) => ({ key, is_hidden }) as CardType;

describe("pickOrgChartType", () => {
  it("uses Organizational Units when they are visible (NORA)", () => {
    expect(pickOrgChartType([type("Organization", true), type("OrganizationalUnit")])?.key).toBe(
      "OrganizationalUnit",
    );
  });

  it("falls back to Organization when units are hidden or absent (TOGAF)", () => {
    expect(pickOrgChartType([type("Organization"), type("OrganizationalUnit", true)])?.key).toBe(
      "Organization",
    );
    expect(pickOrgChartType([type("Organization")])?.key).toBe("Organization");
  });

  it("prefers units when both are visible, so nothing is drawn twice", () => {
    expect(pickOrgChartType([type("Organization"), type("OrganizationalUnit")])?.key).toBe(
      "OrganizationalUnit",
    );
  });

  it("uses a hidden type rather than nothing, and null without either", () => {
    expect(pickOrgChartType([type("Organization", true)])?.key).toBe("Organization");
    expect(pickOrgChartType([type("Application")])).toBeNull();
  });
});

describe("orgNodeKind / orgNodeIcon", () => {
  it("reads the subtype first, then a unit's unitType", () => {
    expect(orgNodeKind({ subtype: "sector", attributes: { unitType: "department" } })).toBe("sector");
    expect(orgNodeKind({ subtype: null, attributes: { unitType: "department" } })).toBe("department");
    expect(orgNodeKind({ attributes: { unitType: "" } })).toBeNull();
    expect(orgNodeKind({ attributes: { unitType: 3 } })).toBeNull();
    expect(orgNodeKind({})).toBeNull();
  });

  it("maps each level to its icon, with a default", () => {
    expect(orgNodeIcon("ministry")).toBe("account_balance");
    expect(orgNodeIcon("publicAdministration")).toBe("domain");
    expect(orgNodeIcon("department")).toBe("apartment");
    expect(orgNodeIcon("sectionUnit")).toBe("work");
    expect(orgNodeIcon("unknown")).toBe("corporate_fare");
    expect(orgNodeIcon(null)).toBe("corporate_fare");
  });
});
