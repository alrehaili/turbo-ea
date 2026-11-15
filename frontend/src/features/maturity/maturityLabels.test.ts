import { describe, expect, it } from "vitest";
import type { TFunction } from "i18next";
import {
  DGA_ACCREDITATION_LEVEL,
  DGA_DOMAIN_DEFAULT_NAMES,
  averageLevel,
  dimensionLabel,
  isAccreditationReady,
} from "./maturityLabels";

const t = ((key: string, opts?: { defaultValue?: string }) =>
  key === "reports:maturity.builtinDimension.dga_capability"
    ? "قدرات البنية المؤسسية"
    : (opts?.defaultValue ?? key)) as unknown as TFunction;

describe("dimensionLabel", () => {
  it("translates a DGA domain that still has its seeded name", () => {
    expect(dimensionLabel("dga_capability", "EA Capability", t)).toBe("قدرات البنية المؤسسية");
  });

  it("keeps a name an admin changed", () => {
    expect(dimensionLabel("dga_capability", "Our EA team", t)).toBe("Our EA team");
  });

  it("keeps custom and legacy dimension names", () => {
    expect(dimensionLabel("cloud", "Cloud Adoption", t)).toBe("Cloud Adoption");
    expect(dimensionLabel("governance", "EA Capability", t)).toBe("EA Capability");
  });

  it("names all eight DGA domains", () => {
    expect(Object.keys(DGA_DOMAIN_DEFAULT_NAMES)).toHaveLength(8);
  });
});

describe("averageLevel", () => {
  it("turns an overall score into the average level", () => {
    expect(averageLevel(60)).toBe(3);
    expect(averageLevel(64)).toBe(3.2);
    expect(averageLevel(100)).toBe(5);
    expect(averageLevel(0)).toBe(0);
  });

  it("is null without a score", () => {
    expect(averageLevel(null)).toBeNull();
    expect(averageLevel(undefined)).toBeNull();
  });
});

describe("isAccreditationReady", () => {
  it("starts at DGA's accreditation level 3", () => {
    expect(DGA_ACCREDITATION_LEVEL).toBe(3);
    expect(isAccreditationReady(60)).toBe(true);
    expect(isAccreditationReady(59)).toBe(false);
    expect(isAccreditationReady(null)).toBe(false);
  });
});
