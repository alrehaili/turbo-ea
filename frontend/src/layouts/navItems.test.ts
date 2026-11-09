/**
 * [FORK] The grouped top bar: seven entries, the pages that used to be
 * top-level living in the group they belong to, and the dropdown filter.
 */
import { describe, expect, it } from "vitest";
import {
  NAV_ANCHORS,
  NAV_ANCHOR_ALIASES,
  NAV_ITEM_DEFS,
  menuRowsFor,
  resolveNavPlacement,
} from "./navItems";

const childPaths = (key: string) =>
  NAV_ITEM_DEFS.find((d) => d.labelKey === key)?.children?.map((c) => c.path) ?? [];

describe("NAV_ITEM_DEFS — the grouped bar", () => {
  it("is seven top-level entries", () => {
    expect(NAV_ITEM_DEFS.map((d) => d.labelKey)).toEqual([
      "dashboard",
      "inventory",
      "architecture",
      "reports",
      "governance",
      "ppm",
      "todos",
    ]);
  });

  it("lists every page exactly once across the whole menu", () => {
    const all = NAV_ITEM_DEFS.flatMap((d) => [
      ...(d.path ? [d.path] : []),
      ...(d.children ?? []).flatMap((c) => [c.path, ...(c.secondary ? [c.secondary.path] : [])]),
    ]);
    expect(all.filter((p, i) => all.indexOf(p) !== i)).toEqual([]);
  });

  it("puts the modelling workspaces under Architecture and the programmes under Governance", () => {
    expect(childPaths("architecture")).toEqual(
      expect.arrayContaining(["/view-library", "/diagrams", "/bpm", "/reference-models"]),
    );
    expect(childPaths("governance")).toEqual(
      expect.arrayContaining(["/ea-delivery/adm", "/grc", "/nora-program"]),
    );
    // ADM is a governance workspace, not a report.
    expect(childPaths("reports")).not.toContain("/ea-delivery/adm");
  });

  it("folds each layer's summary into the layer's row", () => {
    const arch = NAV_ITEM_DEFS.find((d) => d.labelKey === "architecture")!.children!;
    const layers = arch.filter((c) => c.secondary);
    expect(layers.map((c) => [c.path, c.secondary!.path])).toEqual([
      ["/layers/strategy", "/layers/strategy-summary"],
      ["/layers/business", "/layers/business-summary"],
      ["/layers/beneficiary", "/layers/beneficiary-summary"],
      ["/layers/application", "/layers/application-summary"],
      ["/layers/data", "/layers/data-summary"],
      ["/layers/technology", "/layers/technology-summary"],
      ["/layers/security", "/layers/security-summary"],
    ]);
    // The security layer page needs risks.view; its summary does not.
    const security = layers.find((c) => c.path === "/layers/security")!;
    expect(security.permission).toBe("risks.view");
    expect(security.secondary!.permission).toBe("inventory.view");
  });

  it("pins Saved Reports, kept last in the data so extension reports land before it", () => {
    const reports = NAV_ITEM_DEFS.find((d) => d.labelKey === "reports")!.children!;
    expect(reports.filter((c) => c.pinned).map((c) => c.path)).toEqual(["/reports/saved"]);
    expect(reports[reports.length - 1].path).toBe("/reports/saved");
  });

  it("gives every report its own icon", () => {
    const icons = NAV_ITEM_DEFS.find((d) => d.labelKey === "reports")!.children!.map(
      (c) => c.icon,
    );
    expect(icons.filter((icon, i) => icons.indexOf(icon) !== i)).toEqual([]);
  });
});

describe("menuRowsFor", () => {
  const rows = [
    { label: "Application Portfolio", dividerLabel: "landscape" },
    { label: "Data Flow", dividerLabel: "data" },
    { label: "Data Quality" },
    { label: "Business Layer", secondary: { label: "Business Summary" } },
    { label: "Saved Reports", pinned: true },
  ];

  it("lists pinned rows first and keeps the sections when there is no query", () => {
    expect(menuRowsFor(rows, "  ").map((r) => r.label)).toEqual([
      "Saved Reports",
      "Application Portfolio",
      "Data Flow",
      "Data Quality",
      "Business Layer",
    ]);
    expect(menuRowsFor(rows, "")[1].dividerLabel).toBe("landscape");
  });

  it("keeps only matches, ranked, without section headings", () => {
    const hits = menuRowsFor(rows, "data");
    expect(hits.map((r) => r.label)).toEqual(["Data Flow", "Data Quality"]);
    expect(hits.every((r) => r.dividerLabel === undefined)).toBe(true);
    // A word-start match outranks a plain substring match.
    expect(menuRowsFor(rows, "port").map((r) => r.label)).toEqual([
      "Application Portfolio",
      "Saved Reports",
    ]);
  });

  it("matches a row on its secondary action's label", () => {
    expect(menuRowsFor(rows, "summary").map((r) => r.label)).toEqual(["Business Layer"]);
  });

  it("returns nothing when nothing matches", () => {
    expect(menuRowsFor(rows, "zzz")).toEqual([]);
  });
});

describe("retired anchors", () => {
  const BAR = ["dashboard", "inventory", "architecture", "reports", "governance", "ppm", "todos"];

  it("still accepts every anchor an extension could have named before", () => {
    for (const old of ["viewLibrary", "layers", "referenceModels", "bpm", "diagrams", "grc", "noraProgram"]) {
      expect(NAV_ANCHORS).toContain(old);
    }
  });

  it("places an entry next to the group that now holds the named page", () => {
    expect(resolveNavPlacement(BAR, "after:bpm")).toBe(BAR.indexOf("architecture") + 1);
    expect(resolveNavPlacement(BAR, "before:grc")).toBe(BAR.indexOf("governance"));
    for (const [, group] of Object.entries(NAV_ANCHOR_ALIASES)) {
      expect(BAR).toContain(group);
    }
  });

  it("prefers the key itself when the bar still carries it", () => {
    const legacy = ["dashboard", "bpm", "architecture"];
    expect(resolveNavPlacement(legacy, "before:bpm")).toBe(1);
  });
});
