import { describe, expect, it } from "vitest";
import { deliveryTone, formatCompactMoney, pct } from "./executiveFormat";

describe("formatCompactMoney", () => {
  it("formats in the payload's currency, not a hard-coded symbol", () => {
    expect(formatCompactMoney(6_600_000, "USD", "en")).toBe("$6.6M");
    expect(formatCompactMoney(6_600_000, "EUR", "en")).toBe("€6.6M");
  });

  it("keeps SAR as SAR (glyph or code), never another currency", () => {
    const out = formatCompactMoney(1_500_000, "SAR", "en");
    expect(out).toMatch(/1\.5M/);
    expect(out.includes("⃁") || out.includes("SAR")).toBe(true);
    expect(out).not.toContain("$");
  });

  it("falls back to the code beside the number for an unknown currency code", () => {
    expect(formatCompactMoney(1200, "not-a-code", "en")).toBe("1.2K not-a-code");
  });
});

describe("pct", () => {
  it("is null for an unknown value, never 0%", () => {
    expect(pct(null)).toBeNull();
    expect(pct(undefined)).toBeNull();
    expect(pct(0)).toBe("0%");
    expect(pct(66.66)).toBe("66.7%");
  });
});

describe("deliveryTone", () => {
  it("takes the worst state that has initiatives", () => {
    expect(deliveryTone({ onTrack: 3, atRisk: 1, offTrack: 1 })).toBe("offTrack");
    expect(deliveryTone({ onTrack: 3, atRisk: 1, offTrack: 0 })).toBe("atRisk");
    expect(deliveryTone({ onTrack: 3, atRisk: 0, offTrack: 0 })).toBe("onTrack");
  });

  it("does not treat not-reported initiatives as healthy", () => {
    expect(deliveryTone({ onTrack: 0, atRisk: 0, offTrack: 0, notReported: 5 })).toBe("none");
    expect(deliveryTone(undefined)).toBe("none");
  });
});
