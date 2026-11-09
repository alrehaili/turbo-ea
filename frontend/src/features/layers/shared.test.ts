import { describe, expect, it } from "vitest";
import arNav from "@/i18n/locales/ar/nav.json";
import arReports from "@/i18n/locales/ar/reports.json";
import enNav from "@/i18n/locales/en/nav.json";
import enReports from "@/i18n/locales/en/reports.json";
import { NAV_ITEM_DEFS } from "@/layouts/navItems";
import { CARD_TYPE_CATEGORY_ORDER } from "@/lib/cardTypeOrder";
import { LAYER_COLORS } from "@/theme/tokens";
import { EA_LAYERS, LAYER_SLUG } from "./shared";

describe("the seven architecture layers", () => {
  it("runs Strategy first, then the NORA six", () => {
    expect([...EA_LAYERS]).toEqual([
      "Strategy",
      "Business",
      "Beneficiary Experience",
      "Application",
      "Data",
      "Technology",
      "Security",
    ]);
  });

  it("matches the inventory's fallback layer order", () => {
    expect([...CARD_TYPE_CATEGORY_ORDER]).toEqual([...EA_LAYERS]);
  });

  it.each([...EA_LAYERS])("%s has a slug, a colour, a name and an about text", (layer) => {
    const slug = LAYER_SLUG[layer];
    expect(slug).toMatch(/^[a-z]+$/);
    expect((LAYER_COLORS as Record<string, string>)[layer]).toMatch(/^#[0-9a-f]{6}$/i);
    for (const reports of [enReports, arReports]) {
      const names = reports.layerSwimlane.layerName as Record<string, string>;
      const about = reports.layerOverview.about as Record<string, string>;
      expect(names[slug]).toBeTruthy();
      expect(about[slug]).toBeTruthy();
    }
  });

  it.each([...EA_LAYERS])("%s has its own menu row and summary", (layer) => {
    const slug = LAYER_SLUG[layer];
    const arch = NAV_ITEM_DEFS.find((d) => d.labelKey === "architecture")!.children!;
    const row = arch.find((c) => c.path === `/layers/${slug}`);
    expect(row?.secondary?.path).toBe(`/layers/${slug}-summary`);
    for (const nav of [enNav, arNav] as Record<string, string>[]) {
      expect(nav[row!.labelKey]).toBeTruthy();
      expect(nav[row!.secondary!.labelKey]).toBeTruthy();
    }
  });
});
