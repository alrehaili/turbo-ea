import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { ADMIN_ITEM_DEFS, NAV_ITEM_DEFS } from "@/layouts/navItems";
import { itSourceScan } from "@/test/sourceScan";

import {
  INTENTIONALLY_UNGATED,
  ROUTE_PERMISSIONS,
  canAccessPath,
  permissionForPath,
} from "./routePermissions";

// Read the canonical backend registry rather than a hand-kept subset that
// silently goes stale when fork modules add permissions (e.g. adm.view).
const permissionSource = fs.readFileSync(
  path.resolve(__dirname, "../../../backend/app/core/permissions.py"), "utf-8",
);
const appRegistry = permissionSource.slice(
  permissionSource.indexOf("APP_PERMISSIONS:"),
  permissionSource.indexOf("ALL_APP_PERMISSION_KEYS:"),
);
const KNOWN_PERMISSIONS = new Set(
  [...appRegistry.matchAll(/"([a-z_]+\.[a-z_]+)"\s*:/g)].map((m) => m[1]),
);

describe("permissionForPath", () => {
  it("is undefined for a path the table does not gate", () => {
    expect(permissionForPath("/todos")).toBeUndefined();
    expect(permissionForPath("/no/such/page")).toBeUndefined();
  });

  it("resolves a concrete path", () => {
    expect(permissionForPath("/ppm")).toBe("ppm.view");
    expect(permissionForPath("/ppm/abc-123")).toBe("ppm.view");
  });

  it("prefers the more specific pattern", () => {
    expect(permissionForPath("/diagrams/abc")).toBe("diagrams.view");
    expect(permissionForPath("/diagrams/abc/edit")).toBe("diagrams.manage");
    expect(permissionForPath("/admin/surveys/abc")).toBe("surveys.manage");
    expect(permissionForPath("/admin/surveys/abc/results")).toBe("surveys.manage");
    expect(permissionForPath("/ea-delivery/soaw/abc")).toBe("soaw.view");
    expect(permissionForPath("/ea-delivery/soaw/new")).toBe("soaw.manage");
  });

  it("returns undefined for an ungated path", () => {
    expect(permissionForPath("/")).toBeUndefined();
    expect(permissionForPath("/todos")).toBeUndefined();
    expect(permissionForPath("/ext/acme/board")).toBeUndefined();
    expect(permissionForPath("/nonsense")).toBeUndefined();
  });
});

describe("canAccessPath", () => {
  it("is fail-closed on missing permissions", () => {
    expect(canAccessPath(undefined, "/ppm")).toBe(false);
    expect(canAccessPath({}, "/ppm")).toBe(false);
  });

  it("still allows ungated paths without any permissions", () => {
    expect(canAccessPath(undefined, "/")).toBe(true);
    expect(canAccessPath({}, "/todos")).toBe(true);
  });

  it("honours the admin wildcard", () => {
    expect(canAccessPath({ "*": true }, "/admin/users")).toBe(true);
    expect(canAccessPath({ "*": true }, "/principles-catalogue")).toBe(true);
  });

  it("grants exactly what the user holds", () => {
    expect(canAccessPath({ "ppm.view": true }, "/ppm")).toBe(true);
    expect(canAccessPath({ "ppm.view": true }, "/bpm")).toBe(false);
  });

});

describe("parity", () => {
  it("keeps fork workspace and report reads fail-closed", () => {
    const policies = [
      ["/ea-delivery/adm", "adm.view"],
      ["/reference-models/manage", "reference_models.manage"],
      ["/reference-models/business", "reference_models.view"],
      ["/nora-program", "nora.view"],
      ["/maturity", "maturity.view"],
      ["/scenarios", "scenarios.view"],
      ["/reports/process-map", "reports.bpm_dashboard"],
      ["/reports/exceptions-waivers", "tech_standards.view"],
      ["/reports/strategy-map", "reports.ea_dashboard"],
      ["/layers/business", "inventory.view"],
      ["/layers/security", "risks.view"],
    ];
    for (const [route, permission] of policies) {
      expect(permissionForPath(route)).toBe(permission);
      expect(canAccessPath({}, route)).toBe(false);
      expect(canAccessPath({ [permission]: true }, route)).toBe(true);
    }
  });


  /**
   * Every route declared in the authenticated table has to be either gated or
   * explicitly listed as ungated. A new route added without a decision fails
   * here rather than shipping silently open.
   */
  itSourceScan("covers every route in App.tsx", () => {
    const source = fs.readFileSync(
      path.resolve(__dirname, "../App.tsx"),
      "utf-8",
    );
    // The authenticated table is the second <Routes> block — everything after
    // the AppLayout wrapper opens.
    const start = source.indexOf("<AppLayout");
    expect(start).toBeGreaterThan(-1);
    const declared = [
      ...source.slice(start).matchAll(/<Route\s+path="([^"]+)"/g),
    ].map((m) => m[1]);

    expect(declared.length).toBeGreaterThan(40);

    const known = new Set([
      ...ROUTE_PERMISSIONS.map((r) => r.path),
      ...INTENTIONALLY_UNGATED,
    ]);
    const unreviewed = declared.filter((p) => !known.has(p));
    expect(unreviewed).toEqual([]);
  });

  itSourceScan("has no stale entries pointing at routes that no longer exist", () => {
    const source = fs.readFileSync(
      path.resolve(__dirname, "../App.tsx"),
      "utf-8",
    );
    const declared = new Set(
      [...source.matchAll(/<Route\s+path="([^"]+)"/g)].map((m) => m[1]),
    );
    const stale = ROUTE_PERMISSIONS.map((r) => r.path).filter(
      (p) => !declared.has(p),
    );
    expect(stale).toEqual([]);
  });

  it("resolves a permission for every nav item that points at a route", () => {
    const withPath = [...NAV_ITEM_DEFS, ...ADMIN_ITEM_DEFS].flatMap((def) => [
      ...(def.path ? [def.path] : []),
      ...(def.children ?? []).map((c) => c.path),
    ]);
    const ungated = new Set(INTENTIONALLY_UNGATED);
    for (const p of withPath) {
      if (ungated.has(p)) continue;
      expect(
        permissionForPath(p),
        `nav item ${p} has no entry in ROUTE_PERMISSIONS`,
      ).toBeDefined();
    }
  });

  it("only names permissions the backend actually defines", () => {
    for (const { path: routePath, permission } of ROUTE_PERMISSIONS) {
      const keys = Array.isArray(permission) ? permission : [permission];
      for (const key of keys) {
        expect(
          KNOWN_PERMISSIONS.has(key),
          `${routePath} names unknown permission "${key}"`,
        ).toBe(true);
      }
    }
  });
});
