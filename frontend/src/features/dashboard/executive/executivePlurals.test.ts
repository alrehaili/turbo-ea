import { describe, expect, it } from "vitest";
import i18n from "@/i18n";
import ar from "@/i18n/locales/ar/common.json";

/**
 * Arabic has six plural categories (zero, one, two, few, many, other), and
 * i18next falls back to English for any it cannot find — which is how "4 days
 * old" reached the Arabic executive page. Every counted executive string
 * carries all six.
 */
const AR_FORMS = ["zero", "one", "two", "few", "many", "other"] as const;
const executiveCounted = Object.keys(ar)
  .filter((k) => k.startsWith("dashboard.executive.") && k.endsWith("_other"))
  .map((k) => k.slice(0, -"_other".length));

describe("Arabic plural forms on the executive pages", () => {
  it("covers every counted executive string", () => {
    expect(executiveCounted.length).toBeGreaterThan(10);
    const missing = executiveCounted.flatMap((base) =>
      AR_FORMS.filter((form) => !(`${base}_${form}` in ar)).map((form) => `${base}_${form}`),
    );
    expect(missing).toEqual([]);
  });

  it("resolves counts that used to fall back to English", () => {
    const t = i18n.getFixedT("ar", "common");
    for (const count of [0, 1, 2, 4, 11, 100]) {
      const age = t("dashboard.executive.ceo.age", { count });
      expect(age, `age ${count}`).not.toMatch(/days? old/);
      const open = t("dashboard.executive.decisionsPage.openRisks", { count });
      expect(open, `open ${count}`).not.toMatch(/open/);
    }
    expect(t("dashboard.executive.ceo.age", { count: 4 })).toBe("عمره 4 أيام");
  });
});
