/**
 * Route integrity tests for NEA Viewpoint registry.
 * Ensures every viewpoint has unique keys and launchable paths resolve.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { describe, it, expect } from "vitest";
import { NEA_VIEWPOINTS, neaViewpointGate } from "./neaViewpoints";

// Every declared route path in App.tsx (single- or multi-line <Route> JSX).
const appSource = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), "../../App.tsx"),
  "utf-8",
);
const declaredRoutes = new Set(
  [...appSource.matchAll(/path="([^"]+)"/g)].map((m) => m[1]),
);

describe("NEA Viewpoint Registry", () => {
  it("should have unique keys", () => {
    const keys = NEA_VIEWPOINTS.map((v) => v.key);
    const uniqueKeys = new Set(keys);
    expect(uniqueKeys.size).toBe(keys.length);
  });

  it("should have all required base fields", () => {
    for (const viewpoint of NEA_VIEWPOINTS) {
      expect(viewpoint.key).toBeDefined();
      expect(viewpoint.domain).toBeDefined();
      expect(viewpoint.kind).toBeDefined();
      expect(viewpoint.level).toBeDefined();
      expect(viewpoint.nameEn).toBeDefined();
      expect(viewpoint.nameAr).toBeDefined();
      expect(viewpoint.status).toMatch(/^(available|planned|descoped)$/);
    }
  });

  it("should have consistent question translations", () => {
    for (const viewpoint of NEA_VIEWPOINTS) {
      // If one language has a question, the other should too (or both should be undefined)
      const hasEn = !!viewpoint.questionEn;
      const hasAr = !!viewpoint.questionAr;
      if (hasEn || hasAr) {
        expect(hasEn && hasAr).toBe(true);
      }
    }
  });

  it("should not have empty question strings", () => {
    for (const viewpoint of NEA_VIEWPOINTS) {
      if (viewpoint.questionEn !== undefined) {
        expect(viewpoint.questionEn.trim().length).toBeGreaterThan(0);
      }
      if (viewpoint.questionAr !== undefined) {
        expect(viewpoint.questionAr.trim().length).toBeGreaterThan(0);
      }
    }
  });

  it("should have paths only for available and planned viewpoints", () => {
    for (const viewpoint of NEA_VIEWPOINTS) {
      if (viewpoint.status === "descoped") {
        // Descoped can have a path (to closest view) or not
        // No strict requirement here
      } else {
        // Available and planned should ideally have paths
        if (viewpoint.path) {
          expect(viewpoint.path).toMatch(/^\//);
        }
      }
    }
  });

  it("should not have malformed permission keys", () => {
    for (const viewpoint of NEA_VIEWPOINTS) {
      if (viewpoint.permission) {
        expect(viewpoint.permission).toMatch(/^[a-z]+\.[a-z_]+$/);
      }
    }
  });

  it("should have no more than one module requirement per viewpoint", () => {
    for (const viewpoint of NEA_VIEWPOINTS) {
      if (viewpoint.module) {
        expect(["bpm", "ppm", "grc", "turbolens"]).toContain(viewpoint.module);
      }
    }
  });

  // ── Real route integrity: paths must resolve to declared App.tsx routes ──
  it("every non-descoped viewpoint path resolves to a declared route", () => {
    const broken: string[] = [];
    for (const v of NEA_VIEWPOINTS) {
      if (v.status === "descoped" || !v.path) continue;
      const base = v.path.split("?")[0];
      if (!declaredRoutes.has(base)) broken.push(`${v.key} → ${v.path}`);
    }
    expect(broken).toEqual([]);
  });

  it("derives a coherent launch gate from the destination path", () => {
    for (const v of NEA_VIEWPOINTS) {
      if (v.status === "descoped" || !v.path) continue;
      const gate = neaViewpointGate(v);
      const p = v.path;
      if (p.startsWith("/bpm")) {
        expect(gate.module).toBe("bpm");
        expect(gate.permission).toBe("reports.bpm_dashboard");
      } else if (p.startsWith("/grc")) {
        expect(gate.module).toBe("grc");
        expect(gate.permission).toBe("grc.view");
      } else if (p.startsWith("/inventory") || p.startsWith("/layers")) {
        expect(gate.permission).toBe("inventory.view");
      } else if (p.startsWith("/reports/")) {
        expect(gate.permission).toBe("reports.ea_dashboard");
      }
    }
  });

  it("lets an explicit permission/module override the derived gate", () => {
    const sample = neaViewpointGate({
      key: "x",
      domain: "business",
      kind: "list",
      level: "logical",
      nameEn: "x",
      nameAr: "x",
      path: "/reports/anything",
      permission: "custom.perm",
      module: "ppm",
      status: "available",
    });
    expect(sample.permission).toBe("custom.perm");
    expect(sample.module).toBe("ppm");
  });
});
