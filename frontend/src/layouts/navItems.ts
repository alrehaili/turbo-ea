/**
 * Nav menu definitions, extracted from `AppLayout` so the route-permission
 * parity test can read them without mounting the whole layout.
 *
 * Core entries that point at a route carry **no** `permission` — it is derived
 * from `ROUTE_PERMISSIONS` (`lib/routePermissions.ts`) instead, so the menu and
 * the router can never disagree about what a page needs. `permission` survives
 * on the type for the two cases that genuinely need their own: the pathless
 * Reports *group*, and nav entries contributed by installed UI extensions,
 * whose permission comes from the extension manifest.
 */
export interface NavItemDef {
  labelKey: string;
  icon: string;
  path?: string;
  children?: {
    labelKey: string;
    icon: string;
    path: string;
    permission?: string | string[];
    /** [FORK] Section heading rendered above this entry in the dropdown. */
    dividerLabel?: string;
  }[];
  permission?: string | string[];
}

// [FORK] NORA navigation (layers, governance, reference models, …). Entries
// carry explicit permissions, which win over the ROUTE_PERMISSIONS lookup.
export const NAV_ITEM_DEFS: NavItemDef[] = [
  { labelKey: "dashboard", icon: "dashboard", path: "/" },
  { labelKey: "inventory", icon: "inventory_2", path: "/inventory", permission: "inventory.view" },
  { labelKey: "viewLibrary", icon: "travel_explore", path: "/view-library" },
  {
    // EA layers — one rich swim-lane overview per architecture layer. Kept
    // as its own top-level tab (not under Reports) so the layered mental
    // model is a first-class navigation concept.
    labelKey: "layers",
    icon: "layers",
    permission: "inventory.view",
    children: [
      { labelKey: "reports.layersOverview", icon: "space_dashboard", path: "/layers/overview", permission: "inventory.view" },
      { labelKey: "reports.traceability", icon: "hub", path: "/layers/traceability", permission: "inventory.view" },
      { labelKey: "reports.businessLayer", icon: "domain", path: "/layers/business", permission: "inventory.view" },
      { labelKey: "reports.businessSummary", icon: "article", path: "/layers/business-summary", permission: "inventory.view" },
      { labelKey: "reports.beneficiaryLayer", icon: "diversity_3", path: "/layers/beneficiary", permission: "inventory.view" },
      { labelKey: "reports.beneficiarySummary", icon: "article", path: "/layers/beneficiary-summary", permission: "inventory.view" },
      { labelKey: "reports.applicationLayer", icon: "apps", path: "/layers/application", permission: "inventory.view" },
      { labelKey: "reports.applicationSummary", icon: "article", path: "/layers/application-summary", permission: "inventory.view" },
      { labelKey: "reports.dataLayer", icon: "database", path: "/layers/data", permission: "inventory.view" },
      { labelKey: "reports.dataSummary", icon: "article", path: "/layers/data-summary", permission: "inventory.view" },
      { labelKey: "reports.technologyLayer", icon: "memory", path: "/layers/technology", permission: "inventory.view" },
      { labelKey: "reports.technologySummary", icon: "article", path: "/layers/technology-summary", permission: "inventory.view" },
      { labelKey: "reports.securityLayer", icon: "security", path: "/layers/security", permission: "risks.view" },
      { labelKey: "reports.securitySummary", icon: "article", path: "/layers/security-summary", permission: "inventory.view" },
    ],
  },
  {
    labelKey: "reports",
    icon: "analytics",
    permission: "reports.ea_dashboard",
    children: [
      // ── EA Delivery ──
      { labelKey: "reports.admWorkspaces", icon: "account_tree", path: "/ea-delivery/adm", permission: "adm.view", dividerLabel: "reports.groupDelivery" },
      // ── Portfolio & Landscape ──
      { labelKey: "reports.portfolio", icon: "dashboard", path: "/reports/portfolio", dividerLabel: "reports.groupLandscape" },
      { labelKey: "reports.flexiblePortfolio", icon: "dashboard_customize", path: "/reports/flexible-portfolio" },
      { labelKey: "reports.capabilityMap", icon: "grid_view", path: "/reports/capability-map" },
      { labelKey: "reports.technologyLandscape", icon: "apartment", path: "/reports/technology-landscape" },
      { labelKey: "reports.appModules", icon: "widgets", path: "/reports/application-modules" },
      { labelKey: "reports.lifecycle", icon: "timeline", path: "/reports/lifecycle" },
      { labelKey: "reports.dependencies", icon: "hub", path: "/reports/dependencies" },
      { labelKey: "reports.changeImpact", icon: "electric_bolt", path: "/reports/impact" },
      // ── Strategy & Transformation (incl. current-vs-target & gap views) ──
      { labelKey: "reports.strategicHouse", icon: "home_work", path: "/reports/strategic-house", dividerLabel: "reports.groupStrategy" },
      { labelKey: "reports.strategyCascade", icon: "account_tree", path: "/reports/strategy-cascade" },
      { labelKey: "reports.strategyMap", icon: "flag", path: "/reports/strategy-map" },
      { labelKey: "reports.valueChain", icon: "linear_scale", path: "/reports/value-chain" },
      { labelKey: "reports.transformationRoadmap", icon: "route", path: "/reports/transformation-roadmap" },
      { labelKey: "reports.transitionRoadmap", icon: "map", path: "/reports/transition-roadmap" },
      { labelKey: "reports.kpiScorecard", icon: "speed", path: "/reports/kpi-scorecard" },
      { labelKey: "reports.currentVsTarget", icon: "compare_arrows", path: "/reports/current-vs-target" },
      { labelKey: "reports.gapAnalysis", icon: "compare_arrows", path: "/reports/gap-analysis" },
      { labelKey: "reports.gapSummary", icon: "difference", path: "/reports/gap-summary" },
      { labelKey: "reports.initiativeGaps", icon: "assignment_turned_in", path: "/reports/initiative-gap-traceability" },
      // ── Business & Services ──
      { labelKey: "reports.orgChart", icon: "corporate_fare", path: "/reports/org-chart", dividerLabel: "reports.groupBusiness" },
      { labelKey: "reports.serviceCatalogue", icon: "assured_workload", path: "/reports/service-catalogue", permission: "inventory.view" },
      { labelKey: "reports.serviceTraceability", icon: "conversion_path", path: "/reports/service-traceability" },
      { labelKey: "reports.processMap", icon: "account_tree", path: "/reports/process-map", permission: "reports.bpm_dashboard" },
      // ── Data & Integration (incl. data-architecture views) ──
      { labelKey: "reports.dataQuality", icon: "verified", path: "/reports/data-quality", dividerLabel: "reports.groupData" },
      { labelKey: "reports.freshness", icon: "fact_check", path: "/reports/freshness" },
      { labelKey: "reports.dataFlow", icon: "schema", path: "/reports/data-flow" },
      { labelKey: "reports.dataRelationships", icon: "mediation", path: "/reports/data-relationships" },
      { labelKey: "reports.dataClassification", icon: "label", path: "/reports/data-classification" },
      { labelKey: "reports.dataDomains", icon: "category", path: "/reports/data-domain" },
      { labelKey: "reports.dataOwnership", icon: "person_check", path: "/reports/data-ownership" },
      { labelKey: "reports.appDataCrud", icon: "grid_3x3", path: "/reports/app-data-crud" },
      { labelKey: "reports.integration", icon: "sync", path: "/reports/integration-status" },
      { labelKey: "reports.interoperability", icon: "lan", path: "/reports/interoperability" },
      { labelKey: "reports.dataExchangeMap", icon: "swap_horiz", path: "/reports/data-exchange-map" },
      { labelKey: "reports.matrix", icon: "table_chart", path: "/reports/matrix" },
      // ── Operations & Cost ──
      { labelKey: "reports.resilience", icon: "health_and_safety", path: "/reports/resilience", dividerLabel: "reports.groupOps" },
      { labelKey: "reports.cost", icon: "payments", path: "/reports/cost", permission: "costs.view" },
      { labelKey: "reports.endOfLife", icon: "update", path: "/reports/eol" },
      { labelKey: "reports.referenceModels", icon: "hub", path: "/reports/reference-models" },
      { labelKey: "reports.cloudAdoption", icon: "cloud", path: "/reports/cloud-adoption", dividerLabel: "reports.phase7" },
      { labelKey: "reports.techPortfolio", icon: "storage", path: "/reports/tech-portfolio" },
      { labelKey: "reports.techStack", icon: "stack", path: "/reports/tech-stack" },
      { labelKey: "reports.exceptionsWaivers", icon: "rule", path: "/reports/exceptions-waivers", dividerLabel: "reports.phase8" },
      { labelKey: "reports.principlesTraceability", icon: "rule_folder", path: "/reports/principles-traceability" },
      { labelKey: "reports.securityControls", icon: "lock", path: "/reports/security-controls" },
      { labelKey: "reports.standardsCompliance", icon: "verified", path: "/reports/standards-matrix" },
      // EA Delivery lives inside /ppm as a tab when PPM is enabled. When PPM
      // is disabled the nav memo below promotes EA Delivery to a top-level
      // nav item (in PPM's old slot) so the surface stays reachable.
      { labelKey: "reports.saved", icon: "bookmarks", path: "/reports/saved" },
    ],
  },
  {
    // Reference Models browse (RMPlan Phase 1) — NORA-only, filtered below.
    // Per-domain children are injected dynamically from the published-model
    // probe so only domains with an active model appear.
    labelKey: "referenceModels",
    icon: "schema",
    permission: "reference_models.view",
    children: [
      {
        labelKey: "referenceModels.all",
        icon: "apps",
        path: "/reference-models",
      },
    ],
  },
  {
    // Change-governance workflow tools (full CRUD), kept distinct from the
    // read-only analytics under Reports.
    labelKey: "governance",
    icon: "account_balance",
    permission: [
      "scenarios.view",
      "rationalization.view",
      "benefits.view",
      "tech_standards.view",
      "arb.view",
      "maturity.view",
    ],
    children: [
      {
        labelKey: "governance.scenarios",
        icon: "account_tree",
        path: "/scenarios",
        permission: "scenarios.view",
      },
      {
        labelKey: "governance.rationalization",
        icon: "recycling",
        path: "/rationalization",
        permission: "rationalization.view",
      },
      {
        labelKey: "governance.benefits",
        icon: "savings",
        path: "/benefits",
        permission: "benefits.view",
      },
      {
        labelKey: "governance.techStandards",
        icon: "radar",
        path: "/tech-standards",
        permission: "tech_standards.view",
      },
      { labelKey: "governance.arb", icon: "gavel", path: "/arb", permission: "arb.view" },
      // NORA-only (filtered out below when the profile isn't "nora").
      {
        labelKey: "governance.maturity",
        icon: "monitoring",
        path: "/maturity",
        permission: "maturity.view",
      },
      {
        labelKey: "governance.referenceModels",
        icon: "schema",
        path: "/reference-models/manage",
        permission: "reference_models.manage",
      },
    ],
  },
  { labelKey: "bpm", icon: "route", path: "/bpm", permission: "bpm.view" },
  { labelKey: "ppm", icon: "view_timeline", path: "/ppm", permission: "ppm.view" },
  { labelKey: "diagrams", icon: "schema", path: "/diagrams", permission: "diagrams.view" },
  // `children` is filled only by extension routes requesting navGroup "grc";
  // with none installed this stays a plain top-level link.
  { labelKey: "grc", icon: "policy", path: "/grc", permission: "grc.view", children: [] },
  { labelKey: "noraProgram", icon: "account_balance", path: "/nora-program", permission: "nora.view" },
  { labelKey: "todos", icon: "checklist", path: "/todos" },
];

/**
 * The nav positions an extension route may name in its `navPlacement`.
 *
 * Deliberately the `labelKey`s above and nothing else: they are stable
 * identifiers core already owns, and an extension naming one is naming a
 * place in the bar rather than a place in an array that renumbers whenever a
 * module toggle changes what is on screen.
 */
export const NAV_ANCHORS = NAV_ITEM_DEFS.map((item) => item.labelKey);

export const DEFAULT_NAV_PLACEMENT = "end";

/**
 * Index at which a contributed nav entry should be inserted.
 *
 * The frontend mirror of `resolve_placement` in
 * `backend/app/services/extensions/field_contributions.py` — same grammar
 * (`start` / `end` / `before:<anchor>` / `after:<anchor>`), same
 * degrade-to-default rule, so an author who has placed a field section
 * already knows how to place a nav entry.
 *
 * An anchor that is not currently in the bar is NOT an error: `bpm`, `ppm`
 * and `grc` come and go with their module flags, so a placement that names
 * one is right on some instances and unresolvable on others. It degrades to
 * the default rather than being dropped — the entry still appears, just where
 * it would have appeared without the hint.
 *
 * `order` is the list of labelKeys as it stands at this moment, which is what
 * makes the module-flag case fall out for free.
 */
export function resolveNavPlacement(order: string[], placement?: string | null): number {
  const spec = (placement || DEFAULT_NAV_PLACEMENT).trim();
  for (const candidate of [spec, DEFAULT_NAV_PLACEMENT]) {
    if (candidate === "start") return 0;
    if (candidate === "end") return order.length;
    const at = candidate.indexOf(":");
    const prefix = at < 0 ? candidate : candidate.slice(0, at);
    const anchorKey = at < 0 ? "" : candidate.slice(at + 1);
    const index = order.indexOf(anchorKey);
    if (index >= 0) return index + (prefix === "after" ? 1 : 0);
  }
  return order.length;
}

export const ADMIN_ITEM_DEFS: NavItemDef[] = [
  { labelKey: "admin.metamodel", icon: "settings_suggest", path: "/admin/metamodel", permission: "admin.metamodel" },
  { labelKey: "admin.usersAndRoles", icon: "group", path: "/admin/users", permission: "admin.users" },
  { labelKey: "admin.surveys", icon: "assignment", path: "/admin/surveys", permission: "surveys.manage" },
  { labelKey: "admin.extensions", icon: "extension", path: "/admin/extensions", permission: "admin.manage_extensions" },
  { labelKey: "admin.settings", icon: "settings", path: "/admin/settings", permission: "admin.settings" },
];
