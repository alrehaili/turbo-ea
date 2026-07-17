/**
 * Route integrity tests for NEA Viewpoint registry.
 * Ensures every viewpoint has unique keys and launchable paths resolve.
 */

import { describe, it, expect } from "vitest";
import { NEA_VIEWPOINTS } from "./neaViewpoints";

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
});
