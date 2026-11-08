import { searchRank } from "@/lib/searchRank";

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
/** A secondary link drawn at the end of a menu row (e.g. a layer's summary). */
export interface NavSecondaryDef {
  labelKey: string;
  icon: string;
  path: string;
  permission?: string | string[];
}

export interface NavChildDef {
  labelKey: string;
  icon: string;
  path: string;
  permission?: string | string[];
  /** [FORK] Section heading rendered above this entry in the dropdown. */
  dividerLabel?: string;
  /** [FORK] Second action on the same row, so a pair of pages costs one row. */
  secondary?: NavSecondaryDef;
  /** [FORK] Listed first, above every section (e.g. Saved Reports). */
  pinned?: boolean;
}

export interface NavItemDef {
  labelKey: string;
  icon: string;
  path?: string;
  children?: NavChildDef[];
  permission?: string | string[];
}

/**
 * [FORK] The bar is seven entries: Dashboard, Inventory, Architecture,
 * Reports, Governance, Projects and Todos. Workspaces that used to be
 * top-level (View Library, Layers, Reference Models, BPM, Diagrams, GRC, NORA
 * Program) are children of the group they belong to, so the bar fits a laptop
 * screen instead of collapsing into the hamburger drawer.
 *
 * A pathless group with no `permission` of its own shows when at least one
 * child survives the permission filter, and disappears otherwise.
 */
const LAYER_ROWS: [key: string, icon: string, permission?: string][] = [
  ["business", "domain"],
  ["beneficiary", "diversity_3"],
  ["application", "apps"],
  ["data", "database"],
  ["technology", "memory"],
  ["security", "security", "risks.view"],
];

export const NAV_ITEM_DEFS: NavItemDef[] = [
  { labelKey: "dashboard", icon: "dashboard", path: "/" },
  { labelKey: "inventory", icon: "inventory_2", path: "/inventory", permission: "inventory.view" },
  {
    // The architecture itself: the layered model, then the modelling
    // workspaces (views, diagrams, processes, reference models).
    labelKey: "architecture",
    icon: "layers",
    children: [
      { labelKey: "reports.layersOverview", icon: "space_dashboard", path: "/layers/overview", permission: "inventory.view", dividerLabel: "architecture.groupLayers" },
      { labelKey: "reports.traceability", icon: "conversion_path", path: "/layers/traceability", permission: "inventory.view" },
      // One row per layer; its summary page is the row's second action.
      ...LAYER_ROWS.map(([key, icon, permission]) => ({
        labelKey: `reports.${key}Layer`,
        icon,
        path: `/layers/${key}`,
        permission: permission ?? "inventory.view",
        secondary: {
          labelKey: `reports.${key}Summary`,
          icon: "article",
          path: `/layers/${key}-summary`,
          permission: "inventory.view",
        },
      })),
      { labelKey: "viewLibrary", icon: "travel_explore", path: "/view-library", dividerLabel: "architecture.groupModelling" },
      { labelKey: "diagrams", icon: "draw", path: "/diagrams", permission: "diagrams.view" },
      { labelKey: "bpm", icon: "route", path: "/bpm", permission: "bpm.view" },
      // Reference Models browse (RMPlan Phase 1) — NORA-only, filtered in
      // AppLayout. Per-domain entries are injected right after this one from
      // the published-model probe, so only domains with an active model show.
      { labelKey: "referenceModels.all", icon: "schema", path: "/reference-models", permission: "reference_models.view", dividerLabel: "referenceModels" },
    ],
  },
  {
    labelKey: "reports",
    icon: "analytics",
    permission: "reports.ea_dashboard",
    children: [
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
      { labelKey: "reports.strategyCascade", icon: "family_history", path: "/reports/strategy-cascade" },
      { labelKey: "reports.strategyMap", icon: "flag", path: "/reports/strategy-map" },
      { labelKey: "reports.valueChain", icon: "linear_scale", path: "/reports/value-chain" },
      { labelKey: "reports.transformationRoadmap", icon: "route", path: "/reports/transformation-roadmap" },
      { labelKey: "reports.transitionRoadmap", icon: "map", path: "/reports/transition-roadmap" },
      { labelKey: "reports.kpiScorecard", icon: "speed", path: "/reports/kpi-scorecard" },
      { labelKey: "reports.currentVsTarget", icon: "compare_arrows", path: "/reports/current-vs-target" },
      { labelKey: "reports.gapAnalysis", icon: "join_inner", path: "/reports/gap-analysis" },
      { labelKey: "reports.gapSummary", icon: "difference", path: "/reports/gap-summary" },
      { labelKey: "reports.initiativeGaps", icon: "assignment_turned_in", path: "/reports/initiative-gap-traceability" },
      // ── Business & Services ──
      { labelKey: "reports.orgChart", icon: "corporate_fare", path: "/reports/org-chart", dividerLabel: "reports.groupBusiness" },
      { labelKey: "reports.serviceCatalogue", icon: "assured_workload", path: "/reports/service-catalogue", permission: "inventory.view" },
      { labelKey: "reports.serviceTraceability", icon: "conversion_path", path: "/reports/service-traceability" },
      { labelKey: "reports.processMap", icon: "flowchart", path: "/reports/process-map", permission: "reports.bpm_dashboard" },
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
      // ── Technology & Cloud ──
      { labelKey: "reports.cloudAdoption", icon: "cloud", path: "/reports/cloud-adoption", dividerLabel: "reports.phase7" },
      { labelKey: "reports.techPortfolio", icon: "storage", path: "/reports/tech-portfolio" },
      { labelKey: "reports.techStack", icon: "stacks", path: "/reports/tech-stack" },
      // ── Security & Standards ──
      { labelKey: "reports.exceptionsWaivers", icon: "rule", path: "/reports/exceptions-waivers", dividerLabel: "reports.phase8" },
      { labelKey: "reports.principlesTraceability", icon: "rule_folder", path: "/reports/principles-traceability" },
      { labelKey: "reports.securityControls", icon: "lock", path: "/reports/security-controls" },
      { labelKey: "reports.standardsCompliance", icon: "approval", path: "/reports/standards-matrix" },
      { labelKey: "reports.referenceModels", icon: "checklist_rtl", path: "/reports/reference-models" },
      // Pinned: rendered first, above every section. Kept last in the data so
      // extension reports (injected before it) still land among the core ones.
      { labelKey: "reports.saved", icon: "bookmarks", path: "/reports/saved", pinned: true },
    ],
  },
  {
    // Change-governance workflow tools (full CRUD), kept distinct from the
    // read-only analytics under Reports, plus the GRC and NORA programmes.
    labelKey: "governance",
    icon: "account_balance",
    children: [
      { labelKey: "governance.arb", icon: "gavel", path: "/arb", permission: "arb.view" },
      { labelKey: "reports.admWorkspaces", icon: "account_tree", path: "/ea-delivery/adm", permission: "adm.view" },
      { labelKey: "governance.scenarios", icon: "alt_route", path: "/scenarios", permission: "scenarios.view" },
      { labelKey: "governance.rationalization", icon: "recycling", path: "/rationalization", permission: "rationalization.view" },
      { labelKey: "governance.benefits", icon: "savings", path: "/benefits", permission: "benefits.view" },
      { labelKey: "governance.techStandards", icon: "radar", path: "/tech-standards", permission: "tech_standards.view" },
      // NORA-only (filtered out in AppLayout when the profile isn't "nora").
      { labelKey: "governance.maturity", icon: "monitoring", path: "/maturity", permission: "maturity.view" },
      { labelKey: "governance.referenceModels", icon: "edit_note", path: "/reference-models/manage", permission: "reference_models.manage" },
      // ── Programmes ── GRC follows its module flag, NORA the profile.
      { labelKey: "grc", icon: "policy", path: "/grc", permission: "grc.view", dividerLabel: "governance.groupPrograms" },
      { labelKey: "noraProgram", icon: "flag_circle", path: "/nora-program", permission: "nora.view" },
    ],
  },
  { labelKey: "ppm", icon: "view_timeline", path: "/ppm", permission: "ppm.view" },
  { labelKey: "todos", icon: "checklist", path: "/todos" },
];

/**
 * [FORK] Where each extension nav group lands now that GRC is a child of
 * Governance: the host top-level item, and the child the group's routes sit
 * directly after (absent: just before the Saved Reports entry, else at the
 * end). A group whose host — or anchor child — is not on screen for this user
 * falls back to top-level entries, exactly as before.
 */
export const EXTENSION_GROUP_HOSTS: Record<string, { host: string; afterPath?: string }> = {
  reports: { host: "reports" },
  grc: { host: "governance", afterPath: "/grc" },
};

/**
 * [FORK] Anchors that used to be top-level entries and now live inside a
 * group. An extension that names one lands next to the group holding that
 * page, rather than falling to the end of the bar.
 */
export const NAV_ANCHOR_ALIASES: Record<string, string> = {
  viewLibrary: "architecture",
  layers: "architecture",
  referenceModels: "architecture",
  bpm: "architecture",
  diagrams: "architecture",
  grc: "governance",
  noraProgram: "governance",
};

/** A dropdown longer than this gets a filter box at the top. */
export const MENU_FILTER_THRESHOLD = 15;

/**
 * [FORK] The rows a dropdown shows for a filter query.
 *
 * Empty query: every entry, pinned ones first. With a query: only entries
 * whose label — or secondary label — matches, ranked with `searchRank`
 * (exact, starts-with, word-start, contains) and stripped of their section
 * headings, since a ranked list no longer follows the sections.
 */
export function menuRowsFor<
  T extends {
    label: string;
    dividerLabel?: string;
    pinned?: boolean;
    secondary?: { label: string };
  },
>(children: T[], query: string): T[] {
  const q = query.trim();
  if (!q) {
    return [...children.filter((c) => c.pinned), ...children.filter((c) => !c.pinned)];
  }
  const rank = (c: T) => {
    const own = searchRank(c.label, q);
    const sec = c.secondary ? searchRank(c.secondary.label, q) : -1;
    if (own < 0) return sec;
    if (sec < 0) return own;
    return Math.min(own, sec);
  };
  return children
    .map((c) => ({ c, r: rank(c) }))
    .filter(({ r }) => r >= 0)
    .sort((a, b) => a.r - b.r || a.c.label.localeCompare(b.c.label))
    .map(({ c }) => ({ ...c, dividerLabel: undefined }));
}

/**
 * The nav positions an extension route may name in its `navPlacement`.
 *
 * Deliberately the `labelKey`s above and nothing else: they are stable
 * identifiers core already owns, and an extension naming one is naming a
 * place in the bar rather than a place in an array that renumbers whenever a
 * module toggle changes what is on screen.
 */
export const NAV_ANCHORS = [
  ...NAV_ITEM_DEFS.map((item) => item.labelKey),
  ...Object.keys(NAV_ANCHOR_ALIASES),
];

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
    const named = at < 0 ? "" : candidate.slice(at + 1);
    // An anchor that moved into a group resolves to that group, unless the
    // bar still carries it under its own key.
    const anchorKey =
      order.includes(named) || !NAV_ANCHOR_ALIASES[named] ? named : NAV_ANCHOR_ALIASES[named];
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
