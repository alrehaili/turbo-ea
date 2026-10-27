import { matchRoutes } from "react-router";

import { hasPermission } from "@/components/RequirePermission";

/**
 * The single source of truth for "which permission does this URL need?".
 *
 * Two consumers share it, which is why it lives here rather than inside either
 * of them:
 *   - `RouteGuard` (`components/RouteGuard.tsx`) wraps the authenticated route
 *     table, so typing a URL is gated exactly like clicking the nav item;
 *   - `SsoCallback` asks, before redirecting a freshly signed-in user to the
 *     page they originally asked for, whether they can actually open it.
 *
 * `AppLayout`'s nav definitions derive their permissions from here too, so the
 * menu and the router can never disagree about what a page needs.
 *
 * A path that is absent from this table is ungated — see
 * `INTENTIONALLY_UNGATED` below, and the parity test in
 * `routePermissions.test.ts` that stops a new route from being added without a
 * decision either way.
 */
export interface RoutePermission {
  /** react-router path pattern — must match the one in `App.tsx` exactly. */
  path: string;
  /** Permission key, or a list any one of which grants access. */
  permission: string | string[];
}

export const ROUTE_PERMISSIONS: RoutePermission[] = [
  // --- Inventory ----------------------------------------------------------
  // Per-card access (stakeholder roles, `GET /cards/{id}/effective-permissions`)
  // is enforced by the backend and by CardDetail itself; the route gate is the
  // app-level permission only.
  { path: "/inventory", permission: "inventory.view" },
  { path: "/cards/:id", permission: "inventory.view" },

  // --- [FORK] TOGAF ADM workspaces --------------------------------------
  { path: "/ea-delivery/adm", permission: "adm.view" },
  { path: "/ea-delivery/adm/:workspaceId", permission: "adm.view" },

  // --- Reports ------------------------------------------------------------
  { path: "/reports/portfolio", permission: "reports.portfolio" },
  { path: "/reports/flexible-portfolio", permission: "reports.portfolio" },
  { path: "/reports/capability-map", permission: "reports.ea_dashboard" },
  { path: "/reports/lifecycle", permission: "reports.ea_dashboard" },
  { path: "/reports/dependencies", permission: "reports.ea_dashboard" },
  // A report that is nothing but costs, so its subject permission is its only
  // gate — matching what the backend now checks.
  { path: "/reports/cost", permission: "costs.view" },
  { path: "/reports/matrix", permission: "reports.ea_dashboard" },
  { path: "/reports/data-quality", permission: "reports.ea_dashboard" },
  { path: "/reports/eol", permission: "reports.ea_dashboard" },
  // Deliberately NOT `saved_reports.create`: the seeded viewer role cannot
  // create saved reports but legitimately reads ones shared with it, and
  // `GET /saved-reports` requires only authentication.
  { path: "/reports/saved", permission: "reports.ea_dashboard" },

  // Fork route audit: card-only views use inventory.view; server-backed
  // reports and module workspaces use their own read authority. Read-only
  // management pages use their nav authority; writes stay separately gated.
  { path: "/layers/overview", permission: "inventory.view" },
  { path: "/layers/traceability", permission: "inventory.view" },
  { path: "/layers/business", permission: "inventory.view" },
  { path: "/layers/beneficiary", permission: "inventory.view" },
  { path: "/layers/application", permission: "inventory.view" },
  { path: "/layers/data", permission: "inventory.view" },
  { path: "/layers/technology", permission: "inventory.view" },
  { path: "/layers/security", permission: "risks.view" },
  { path: "/layers/business-summary", permission: "inventory.view" },
  { path: "/layers/beneficiary-summary", permission: "inventory.view" },
  { path: "/layers/application-summary", permission: "inventory.view" },
  { path: "/layers/data-summary", permission: "inventory.view" },
  { path: "/layers/technology-summary", permission: "inventory.view" },
  { path: "/layers/security-summary", permission: "inventory.view" },
  { path: "/layers/strategy", permission: "inventory.view" },
  { path: "/layers/technical", permission: "inventory.view" },
  { path: "/layers/strategy-summary", permission: "inventory.view" },
  { path: "/layers/technical-summary", permission: "inventory.view" },
  { path: "/reports/application-layer", permission: "inventory.view" },
  { path: "/reports/strategy-layer", permission: "inventory.view" },
  { path: "/reports/business-layer", permission: "inventory.view" },
  { path: "/reports/technology-layer", permission: "inventory.view" },
  { path: "/reports/security-layer", permission: "risks.view" },
  { path: "/reports/application-summary", permission: "inventory.view" },
  { path: "/reports/strategy-summary", permission: "inventory.view" },
  { path: "/reports/business-summary", permission: "inventory.view" },
  { path: "/reports/technology-summary", permission: "inventory.view" },
  { path: "/reports/transformation-roadmap", permission: "reports.ea_dashboard" },
  { path: "/reports/gap-analysis", permission: "reports.ea_dashboard" },
  { path: "/nora-program", permission: "nora.view" },
  { path: "/maturity", permission: "maturity.view" },
  { path: "/reference-models", permission: "reference_models.view" },
  { path: "/reference-models/manage", permission: "reference_models.manage" },
  { path: "/reference-models/:domain", permission: "reference_models.view" },
  { path: "/reports/org-chart", permission: "inventory.view" },
  { path: "/reports/service-traceability", permission: "reports.ea_dashboard" },
  { path: "/reports/kpi-scorecard", permission: "inventory.view" },
  { path: "/reports/service-catalogue", permission: "inventory.view" },
  { path: "/reports/reference-models", permission: "nora.view" },
  { path: "/reports/process-map", permission: "reports.bpm_dashboard" },
  { path: "/reports/interoperability", permission: "reports.ea_dashboard" },
  { path: "/reports/data-exchange-map", permission: "reports.ea_dashboard" },
  { path: "/reports/technology-landscape", permission: "reports.ea_dashboard" },
  { path: "/reports/strategic-house", permission: "reports.ea_dashboard" },
  { path: "/reports/strategy-cascade", permission: "reports.ea_dashboard" },
  { path: "/reports/value-chain", permission: "inventory.view" },
  { path: "/reports/application-modules", permission: "inventory.view" },
  { path: "/reports/impact", permission: "reports.ea_dashboard" },
  { path: "/reports/strategy-map", permission: "reports.ea_dashboard" },
  { path: "/reports/freshness", permission: "reports.ea_dashboard" },
  { path: "/reports/resilience", permission: "reports.ea_dashboard" },
  { path: "/scenarios", permission: "scenarios.view" },
  { path: "/reports/data-flow", permission: "reports.ea_dashboard" },
  { path: "/reports/data-ownership", permission: "inventory.view" },
  { path: "/reports/data-domain", permission: "inventory.view" },
  { path: "/reports/data-classification", permission: "inventory.view" },
  { path: "/reports/app-data-crud", permission: "inventory.view" },
  { path: "/reports/data-relationships", permission: "inventory.view" },
  { path: "/reports/current-vs-target", permission: "inventory.view" },
  { path: "/reports/gap-summary", permission: "inventory.view" },
  { path: "/reports/target-landscape", permission: "inventory.view" },
  { path: "/reports/transition-roadmap", permission: "inventory.view" },
  { path: "/reports/initiative-gap-traceability", permission: "reports.ea_dashboard" },
  { path: "/reports/integration-status", permission: "reports.ea_dashboard" },
  { path: "/reports/tech-portfolio", permission: "inventory.view" },
  { path: "/reports/cloud-adoption", permission: "inventory.view" },
  { path: "/reports/tech-stack", permission: "inventory.view" },
  { path: "/reports/security-controls", permission: "inventory.view" },
  { path: "/reports/standards-matrix", permission: "inventory.view" },
  { path: "/reports/principles-traceability", permission: "inventory.view" },
  { path: "/reports/exceptions-waivers", permission: "tech_standards.view" },
  { path: "/reports/personas", permission: "inventory.view" },
  { path: "/reports/journey-map", permission: "inventory.view" },
  { path: "/reports/touchpoint-matrix", permission: "inventory.view" },
  { path: "/reports/experience-heatmap", permission: "inventory.view" },
  { path: "/reports/beneficiary-landscape", permission: "inventory.view" },
  { path: "/reports/service-touchpoints", permission: "inventory.view" },
  { path: "/reports/persona-beneficiary-mapping", permission: "inventory.view" },
  { path: "/reports/nea-viewpoints", permission: "nora.view" },
  { path: "/reports/strategic-house-nora", permission: "inventory.view" },
  { path: "/reports/journey-map-nora", permission: "inventory.view" },
  { path: "/reports/datacenter-distribution", permission: "inventory.view" },
  { path: "/reports/network-topology", permission: "inventory.view" },
  { path: "/reports/security-deployment", permission: "inventory.view" },

  // --- EA Delivery --------------------------------------------------------
  { path: "/ea-delivery", permission: "soaw.view" },
  { path: "/reports/ea-delivery", permission: "soaw.view" },
  { path: "/ea-delivery/soaw/new", permission: "soaw.manage" },
  { path: "/ea-delivery/soaw/:id/preview", permission: "soaw.view" },
  // The editor opens read-only for a viewer, so `soaw.view` is the right gate.
  { path: "/ea-delivery/soaw/:id", permission: "soaw.view" },
  { path: "/ea-delivery/adr/new", permission: "adr.manage" },
  { path: "/ea-delivery/adr/:id/preview", permission: "adr.view" },
  { path: "/ea-delivery/adr/:id", permission: "adr.view" },

  // --- Modules ------------------------------------------------------------
  // Permission gates the route; `ModuleGate` (inside the route element) gates
  // the render on the module's enabled flag. Outer check first: "you may not
  // see this at all" outranks "this is switched off".
  { path: "/bpm", permission: "bpm.view" },
  { path: "/bpm/processes/:id/flow", permission: "bpm.view" },
  { path: "/ppm", permission: "ppm.view" },
  { path: "/ppm/:id", permission: "ppm.view" },
  { path: "/grc", permission: "grc.view" },
  { path: "/grc/risks/:id", permission: "risks.view" },
  // Executive drill-down targets: the page's own API answers 403 without these,
  // so a link to it must not be offered (or followed by URL) without them.
  { path: "/rationalization", permission: "rationalization.view" },
  // Benefits register (Phase 4, D-12): amounts additionally need costs.view.
  { path: "/benefits", permission: "benefits.view" },
  { path: "/arb", permission: "arb.view" },
  { path: "/tech-standards", permission: "tech_standards.view" },
  { path: "/turbolens", permission: "turbolens.view" },
  { path: "/turbolens/assessments/:id", permission: "turbolens.view" },

  // --- Diagrams -----------------------------------------------------------
  { path: "/diagrams", permission: "diagrams.view" },
  { path: "/diagrams/:id", permission: "diagrams.view" },
  { path: "/diagrams/:id/edit", permission: "diagrams.manage" },

  // --- Surveys ------------------------------------------------------------
  { path: "/surveys/:surveyId/respond/:cardId", permission: "surveys.respond" },

  // --- Reference catalogues -----------------------------------------------
  { path: "/capability-catalogue", permission: "inventory.view" },
  { path: "/process-catalogue", permission: "inventory.view" },
  { path: "/value-stream-catalogue", permission: "inventory.view" },
  // `GET /principles-catalogue` requires `admin.metamodel` server-side.
  { path: "/principles-catalogue", permission: "admin.metamodel" },

  // --- Admin --------------------------------------------------------------
  { path: "/admin/metamodel", permission: "admin.metamodel" },
  { path: "/admin/users", permission: "admin.users" },
  { path: "/admin/settings", permission: "admin.settings" },
  { path: "/admin/eol", permission: "eol.manage" },
  { path: "/admin/web-portals", permission: "web_portals.manage" },
  { path: "/admin/servicenow", permission: "servicenow.manage" },
  { path: "/admin/extensions", permission: "admin.manage_extensions" },
  { path: "/admin/surveys", permission: "surveys.manage" },
  { path: "/admin/surveys/new", permission: "surveys.manage" },
  { path: "/admin/surveys/:id/results", permission: "surveys.manage" },
  { path: "/admin/surveys/:id", permission: "surveys.manage" },
  { path: "/admin/turbolens", permission: "turbolens.manage" },
];

/**
 * Routes that are ungated on purpose. Listed explicitly so the parity test can
 * tell "reviewed and left open" apart from "nobody looked at it".
 */
export const INTENTIONALLY_UNGATED: string[] = [
  // Public viewpoint catalogue metadata only; target pages enforce their own policies.
  "/view-library",
  "/reports/view-library",
  // The universal fallback — for the catch-all, for RequirePermission's and
  // ModuleGate's Back buttons, and for the post-sign-in denial redirect.
  // Gating it would leave some users with no reachable page at all.
  "/",
  // Personal surfaces. `todos.py` has no permission checks by design.
  "/todos",
  "/surveys",
  // Pure <Navigate> redirects: the gate belongs at the destination, otherwise
  // Access denied renders at a URL the user never sees.
  "/ea-delivery/risks",
  "/ea-delivery/risks/:id",
  // `ExtensionRoutesOutlet` already applies RequirePermission per contributed
  // route when the manifest declares one. A table entry here would either
  // double-gate or break permission-less extension pages.
  "/ext/*",
  // The router's own not-found fallback.
  "*",
];


/**
 * The permission a pathname requires, or `undefined` when it is ungated.
 *
 * Uses react-router's own matcher so specificity ranking is identical to
 * `<Routes>` — `/admin/surveys/:id/results` wins over `/admin/surveys/:id`
 * without the table having to be hand-ordered.
 */
export function permissionForPath(pathname: string): string | string[] | undefined {
  // The table entries are route objects themselves, so the match hands back
  // the entry it matched; null when nothing does.
  const matches = matchRoutes(ROUTE_PERMISSIONS, pathname);
  if (!matches) return undefined;
  // matchRoutes ranks best-first for a flat route array.
  return matches[matches.length - 1].route.permission;
}

/**
 * Can this user open this URL? Fail-closed: unknown permissions mean no.
 *
 * Deliberately consults permissions only, never module-enabled flags. Those
 * are async singletons that read `false` until they have loaded, so folding
 * them in here would bounce users off a page purely because a flag had not
 * arrived yet. Modules gate the render (`ModuleGate` shows a spinner, then a
 * friendly disabled card); permissions gate the redirect.
 */
export function canAccessPath(
  perms: Record<string, boolean> | undefined,
  pathname: string,
): boolean {
  const permission = permissionForPath(pathname);
  if (!permission) return true;
  return hasPermission(perms, permission);
}
