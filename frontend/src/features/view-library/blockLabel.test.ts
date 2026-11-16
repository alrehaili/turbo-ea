import { describe, expect, it } from "vitest";
import type { CardType } from "@/types";
import { blockLabel, humanizeBlockKey } from "./blockLabel";

const type = (key: string, label: string, ar?: string) =>
  ({ key, label, translations: ar ? { label: { ar } } : {} }) as unknown as CardType;

const TYPES = [
  type("GovService", "Government Service", "خدمة حكومية"),
  type("OrganizationalUnit", "Organizational Unit", "وحدة تنظيمية"),
  type("Organization", "Organization", "منظمة"),
  type("Persona", "Persona"),
];

describe("blockLabel", () => {
  it("shows the card type's translated name, not its key", () => {
    expect(blockLabel("GovService", TYPES, "ar")).toBe("خدمة حكومية");
    expect(blockLabel("GovService", TYPES, "en")).toBe("Government Service");
  });

  it("shows the visible type that replaces a hidden one", () => {
    expect(blockLabel("Organization", TYPES, "ar")).toBe("وحدة تنظيمية");
    expect(blockLabel("BeneficiaryPersona", TYPES, "en")).toBe("Persona");
  });

  it("falls back to the hidden type itself when its replacement is absent", () => {
    expect(blockLabel("Organization", [TYPES[2]], "en")).toBe("Organization");
  });

  it("splits a key that names no card type into words", () => {
    expect(blockLabel("DataTerm", TYPES, "en")).toBe("Data Term");
    expect(humanizeBlockKey("Location")).toBe("Location");
  });
});
