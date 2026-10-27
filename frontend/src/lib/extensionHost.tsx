/**
 * Extension host — runtime loader + registry for vendor-signed UI extensions.
 *
 * Extensions are prebuilt ESM bundles served same-origin by the backend
 * (`/api/v1/ext-assets/...`), listed by the authenticated, entitlement-
 * filtered `/extensions/ui-manifest` endpoint. Each bundle calls
 * `window.TurboEA.register(key, plugin)` on import. React/MUI/the API
 * client are provided via `window.TurboEA.sdk` so bundles stay small and
 * share the host's single React instance (the template repo's Vite
 * config externalizes them onto these globals).
 *
 * Eight extension points exist: nav routes (full pages), card-detail tabs,
 * admin panels, custom field types (SDK 1.1 — a renderer/editor for an
 * `ext.{key}.*` field type used inside card attribute sections, plus — SDK 1.5
 * — an optional admin-side config editor for that type's config object), survey
 * templates (SDK 1.2), — SDK 1.3 — ADR panels (a component rendered on
 * the Architecture Decision Record editor/preview, e.g. a custom form
 * writing the ADR `ext.*` attributes bag) and ADR export sections (plain data
 * a plugin contributes into the core ADR DOCX export), and — SDK 1.4 — a
 * headless field-visibility provider (hides specific card fields at render
 * time from the extension's own, possibly async, logic; display-only, never
 * deletes stored values). Since SDK 1.6 extension reports can also participate
 * in Saved Reports: save with report_type "ext:{key}:{routeId}" via
 * `sdk.SaveReportDialog`, load via `sdk.useSavedReport`, and the gallery
 * resolves the namespaced type back to the registered route. Since SDK 1.7 the
 * sdk also carries the report-building kit core reports are made of —
 * `sdk.ReportShell` (frame + save/export/print), `sdk.FilterSelect`
 * (multi-select filter dropdown), and `sdk.CardDetailSidePanel` (card drawer)
 * — ReportShell/CardDetailSidePanel lazy-loaded with Suspense handled
 * internally. Since SDK 1.8 the sdk also carries `useCurrency` (workspace
 * currency formatting), `MetricCard` (KPI tile), `ReportLegend`,
 * `UserMultiSelect` (shared multi-user picker over GET /users), and
 * `loadRecharts` — an async loader returning the recharts module from core's
 * code-split chunk, so extensions never bundle a charting library. Since SDK
 * 1.9 `useChartTheme` returns the theme-aware Recharts chrome (grid stroke,
 * axis ticks, tooltip styling) core reports use, so extension charts match
 * core's look without hand-rolling it. Since SDK 1.11 `useThumbnailCapture`
 * captures a chart container as the PNG preview shown on saved-report cards
 * (html-to-image loads lazily on first capture). Since SDK 1.14
 * `CardScopeDialog` is the shared hierarchy-aware multi-select card picker
 * report scope controls are built on — pick cards and everything beneath them
 * comes with — plus its `dedupeScopeRoots` helper. Since SDK 1.15 the rest of
 * the kit ships too: `CardScopeFilter` (the toolbar chip that opens it),
 * `useCardScope` (scope state, closure, stale-id handling, type-change reset;
 * since SDK 1.31 `setScopeIds(ids, forType)` sets a scope together with the
 * card type it belongs to, so a restore that changes the type keeps it)
 * and `applyScope` (narrow a list to a closure). Since SDK 1.16
 * `integrationPanels` places an extension's integration configuration as a
 * sub-tab of Admin → Settings → Integrations, next to the built-in ServiceNow
 * integration (`adminPanels` is unchanged and still renders on Admin →
 * Extensions). Since SDK 1.21 the sdk carries `loadTimeline` (an async loader
 * resolving the time-travel `TimelineSlider` plus the `timelineRange` helpers
 * and `useTimeline`, so an extension timeline behaves exactly like the core
 * reports'), `loadDependencyView` (a lazy loader resolving the Layered
 * Dependency View renderer + its layout engine from core's code-split chunk —
 * extensions must never substitute another graph library), and the grid
 * filter-sidebar primitives `FilterSectionHeader` / `FilterCheckboxList` /
 * `ColumnFreezeToggle` (the §3.11 building blocks, so an extension's filter
 * sidebar cannot drift from the Inventory anatomy), and `loadReportExport`
 * (core's own XLSX/PPTX report exporters, so an extension never bundles a
 * presentation library and its decks match core's). Since SDK 1.24
 * `CardMultiPicker` is the full card browser — type rail with live counts,
 * hierarchy, subtree-root semantics via `roots`, and a selection that
 * survives re-faceting and re-searching — for anything bigger than the
 * single-type scope control `CardScopeDialog` covers. Since SDK 1.27
 * `CardPicker` is the single-select card picker every core dropdown that
 * selects ONE card is built on — browse on open, rank as you type, page in
 * more as the list scrolls — so an extension dialog that links one card
 * behaves exactly like core's instead of hand-rolling an Autocomplete.
 *
 * Since SDK 1.12 the preferred way to add a plug point is the GENERIC SLOT
 * registry, not a new named extension point. An extension declares
 * `slots: [{ slot, id, component | build, permission?, appliesTo?, order? }]`
 * on its plugin; core exposes a location by dropping `<ExtensionSlot
 * name="..." context={...} />` (component slots) or calling
 * `getExtensionSlots(name)` and rendering the returned `build(ctx)` data
 * itself (data slots — the adrGridColumns/adrExportSections philosophy). This
 * means a NEW plug location no longer needs an SDK type/hook/version change —
 * only a one-line `<ExtensionSlot>` in core with a fresh `slot` string. The
 * named points above are retained for compatibility; new locations should use
 * slots. Every extension-provided component must be rendered inside <ExtensionBoundary> —
 * a crashing extension shows a fallback chip, never a white screen. A field
 * type whose extension is missing, disabled, or unlicensed simply is not in
 * the registry, so core falls back to a read-only text rendering of the
 * stored value (the data is never lost).
 */

import * as mui from "@mui/material";
import React from "react";
import ReactDOM from "react-dom";
import { useTranslation } from "react-i18next";

import { api } from "@/api/client";
import FilterSelect from "@/components/FilterSelect";
import CardMultiPicker from "@/components/CardMultiPicker";
import CardPicker from "@/components/CardPicker";
import LinkifiedText from "@/components/LinkifiedText";
import { sanitizeRichHtml } from "@/lib/richHtml";
import CardScopeDialog, { dedupeScopeRoots } from "@/components/CardScopeDialog";
import CardScopeFilter from "@/components/CardScopeFilter";
import { applyScope, useCardScope } from "@/hooks/useCardScope";
import MaterialSymbol from "@/components/MaterialSymbol";
import UserMultiSelect from "@/components/UserMultiSelect";
import MetricCard from "@/features/reports/MetricCard";
import ReportLegend from "@/features/reports/ReportLegend";
import SaveReportDialog from "@/features/reports/SaveReportDialog";
import type { ReportShellProps } from "@/features/reports/ReportShell";
import { useChartTheme } from "@/hooks/useChartTheme";
import { useThumbnailCapture } from "@/hooks/useThumbnailCapture";
import { useCurrency } from "@/hooks/useCurrency";
import { useSavedReport as useCoreSavedReport } from "@/hooks/useSavedReport";
import * as tokens from "@/theme/tokens";
// SDK 1.19 — choice-field pill rendering + metamodel label resolution, so an
// extension renders a select value exactly like core. All leaf/pure modules:
// no code-split graph, and no cycle back through cardDetailUtils.
import { OptionChip, SELECT_CHIP_BASE, chipWidthForField } from "@/components/OptionChip";
import { readableTextColor } from "@/lib/color";
import { fieldLabel, optionLabel, useFieldLabel, useOptionLabel } from "@/hooks/useResolveLabel";
// SDK 1.20 - the workspace date format, and in-app navigation. Both are things
// an extension can only otherwise approximate: a hand-rolled toLocaleDateString
// ignores Admin -> Settings -> Date format, and an <a href> to a core route
// reloads the whole SPA even though the extension page already renders inside
// core's router.
import { useDateFormat } from "@/hooks/useDateFormat";
import { useNavigate } from "react-router";
// SDK 1.23 — the shared commit-on-blur native date input (focus-protected
// draft), so an extension form gets the same date-entry behaviour as core
// and cannot reintroduce the mid-edit value-clobber bug (#865). MUI-only
// leaf module, so a static import is safe.
import DateField from "@/components/DateField";
// SDK 1.21 — the shared filter-sidebar building blocks (UI_GUIDELINES §3.11).
// MUI-only leaf modules like FilterSelect, so static imports are safe: no
// code-split graph is dragged into the eager bundle and no cycle back here.
import ColumnFreezeToggle from "@/components/grid/ColumnFreezeToggle";
import { FilterCheckboxList, FilterSectionHeader } from "@/components/FilterSidebarSection";
// SDK 1.25 — the card-detail lifecycle line, and gantt dependency-arrow
// routing. `LifecycleSection` is props-driven (it commits through an `onSave`
// callback and makes no API call of its own), so an extension can render a
// card's phases exactly as core does and wire the save to its own writer. It
// takes `PHASES`/`getPhaseLabels` from the leaf `@/lib/lifecyclePhases`
// rather than `cardDetailUtils`, which imports THIS module — a static import
// of the section is only safe because of that lift. `buildGanttArrowPath` is
// pure geometry, so a finish-to-start arrow drawn by an extension is the same
// shape as one drawn by the PPM gantt instead of a second convention.
import LifecycleSection from "@/features/cards/sections/LifecycleSection";
import { PHASES, getPhaseLabels } from "@/lib/lifecyclePhases";
import { buildGanttArrowPath } from "@/features/ppm/ganttArrowPath";
import {
  beginExtensionLoad,
  getRegisteredExtensions,
  recordExtensionLoadError,
  registerExtension,
  setExtensionDisplayName,
  UI_SDK_VERSION,
} from "@/lib/extensionRegistry";
import type { TurboExtensionUI } from "@/lib/extensionRegistry";

// Everything the registry exports stays importable from here, so code and
// tests written against `@/lib/extensionHost` keep working unchanged.
export * from "@/lib/extensionRegistry";

interface UiManifestEntry {
  key: string;
  name: string;
  version: string;
  entry: string;
  entitlement_state: string;
}

/**
 * SDK 1.7 — the report-building kit core reports are made of, so an extension
 * report gets the identical frame/UX with zero reimplementation. All ungated —
 * RBAC stays server-side on whatever the pieces fetch. Exposed on
 * `window.TurboEA.sdk` as `ReportShell`, `FilterSelect`, `CardDetailSidePanel`.
 * All three work on /ext/* routes (they only need the SPA router + the
 * `reports`/`common` i18n namespaces, both always loaded).
 *
 * - ReportShell — the report frame: title, saved-report banner, save button,
 *   export/print, filters toolbar slot, actions slot, thumbnail chart ref.
 * - FilterSelect — the shared multi-select filter dropdown.
 * - CardDetailSidePanel — the self-contained card-detail drawer reports open
 *   on node/row click ({cardId, open, onClose}).
 *
 * ReportShell and CardDetailSidePanel are deliberately LAZY: ReportShell pulls
 * the export engine (xlsx / pptxgenjs / html-to-image) and the panel pulls the
 * whole card-detail graph (CardDetailContent + tabs) — both are code-split
 * behind lazy routes today, and a static import here would drag them into the
 * eager main bundle (the panel would also create a module cycle:
 * CardDetailContent imports this module). Suspense is handled internally so
 * extensions just render the components. FilterSelect is MUI-only and is
 * imported statically.
 */
const LazyCardDetailSidePanel = React.lazy(() => import("@/components/CardDetailSidePanel"));
const LazyReportShell = React.lazy(() => import("@/features/reports/ReportShell"));
const LazyCreateCardDialog = React.lazy(() => import("@/components/CreateCardDialog"));

export function ExtensionCardDetailSidePanel(props: {
  cardId: string | null;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <React.Suspense fallback={null}>
      <LazyCardDetailSidePanel {...props} />
    </React.Suspense>
  );
}

export function ExtensionReportShell(props: ReportShellProps) {
  return (
    <React.Suspense fallback={null}>
      <LazyReportShell {...props} />
    </React.Suspense>
  );
}

/**
 * SDK 1.17 — core's create-card dialog for extension pages. Lazy for the
 * same reason as the side panel (AiSuggestPanel/CardPicker graph). The
 * caller supplies `onCreate` (typically `api.post("/cards", data)` resolving
 * to the new card id); `initialType`/`initialSubtype`/`initialAttributes`
 * open it pre-configured. On success the dialog navigates to the new card.
 */
export function ExtensionCreateCardDialog(props: {
  open: boolean;
  onClose: () => void;
  onCreate: (data: {
    type: string;
    subtype?: string;
    name: string;
    description?: string;
    parent_id?: string;
    attributes?: Record<string, unknown>;
    lifecycle?: Record<string, string>;
  }) => Promise<string>;
  initialType?: string;
  initialSubtype?: string;
  initialAttributes?: Record<string, unknown>;
}) {
  return (
    <React.Suspense fallback={null}>
      <LazyCreateCardDialog {...props} />
    </React.Suspense>
  );
}

/**
 * SDK 1.6 — saved-report participation for extension reports.
 *
 * An extension report saves with `report_type: "ext:{key}:{routeId}"` (the
 * gallery resolves it back to the registered route) and uses this hook to load
 * a saved configuration when opened via `?saved_report_id=`. Returns nulls
 * when the page was opened without a saved report. Exposed on
 * `window.TurboEA.sdk.useSavedReport`; pairs with `sdk.SaveReportDialog` (the
 * core save/share dialog re-exported verbatim: name/description/visibility/
 * share-with-users → POST /saved-reports). Ungated — permissions are the same
 * `saved_reports.*` keys every core report uses, enforced server-side.
 *
 * SDK 1.13 additionally re-exports the core hook's **localStorage
 * auto-persist** layer — `consumeConfig` / `persistConfig` / `resetAll` — so an
 * extension report keeps its filters + selection across a page refresh exactly
 * like a core report (same three-tier priority: URL saved report > localStorage
 * > component defaults). `consumeConfig()` is called once on mount to restore,
 * `persistConfig(config)` on every change to auto-save, and `resetAll()` clears
 * both localStorage and the URL saved report. See any core report
 * (`CostReport.tsx`) for the canonical usage.
 */
export function useExtensionSavedReport(reportType: string): {
  config: Record<string, unknown> | null;
  savedReportId: string | null;
  name: string | null;
  consumeConfig: () => Record<string, unknown> | null;
  persistConfig: (config: Record<string, unknown>) => void;
  resetAll: () => void;
} {
  const saved = useCoreSavedReport(reportType);
  return {
    config: (saved.savedReport?.config as Record<string, unknown> | undefined) ?? null,
    savedReportId: saved.savedReport?.id ?? null,
    name: saved.savedReportName,
    consumeConfig: saved.consumeConfig,
    persistConfig: saved.persistConfig,
    resetAll: saved.resetAll,
  };
}

// ---------------------------------------------------------------------------
// window.TurboEA — the global SDK surface extension bundles compile against
// ---------------------------------------------------------------------------

declare global {
  interface Window {
    TurboEA?: {
      sdk: Record<string, unknown>;
      register: (key: string, plugin: TurboExtensionUI) => void;
    };
  }
}

export function initExtensionHost(): void {
  if (typeof window === "undefined" || window.TurboEA) return;
  window.TurboEA = {
    sdk: {
      React,
      ReactDOM,
      mui,
      api,
      MaterialSymbol,
      useTranslation,
      tokens,
      uiSdkVersion: UI_SDK_VERSION,
      // SDK 1.19 — render a select option the way core does.
      OptionChip,
      SELECT_CHIP_BASE,
      chipWidthForField,
      readableTextColor,
      useOptionLabel,
      useFieldLabel,
      optionLabel,
      fieldLabel,
      // SDK 1.6 — saved-report participation (see useExtensionSavedReport).
      useSavedReport: useExtensionSavedReport,
      SaveReportDialog,
      // SDK 1.7 — report-building kit (ReportShell/CardDetailSidePanel are
      // lazy wrappers; see the doc block above ExtensionCardDetailSidePanel).
      ReportShell: ExtensionReportShell,
      FilterSelect,
      CardDetailSidePanel: ExtensionCardDetailSidePanel,
      // SDK 1.8 — dashboard-building additions: currency formatting, KPI tile,
      // legend, the shared multi-user picker, and a lazy Recharts loader so
      // extension charts reuse core's code-split chunk instead of bundling
      // their own copy (a static import here would drag Recharts into the
      // eager main bundle — same caveat as ReportShell above).
      useCurrency,
      MetricCard,
      ReportLegend,
      UserMultiSelect,
      // SDK 1.20 - `useDateFormat` returns the same bound `formatDate` /
      // `formatDateTime` core renders every date through, so an extension
      // follows the workspace setting instead of inventing a format.
      // `useNavigate` is react-router's, re-exported: an extension page is
      // mounted inside core's router, so it can route without a document
      // reload - but it must not bundle react-router itself.
      useDateFormat,
      useNavigate,
      // SDK 1.23 — the shared native date input (see the import note above).
      DateField,
      LifecycleSection,
      PHASES,
      getPhaseLabels,
      buildGanttArrowPath,
      loadRecharts: () => import("recharts"),
      // SDK 1.9 — theme-aware Recharts chrome (grid/axis/tooltip), the same
      // conventions core reports use, so extension charts cannot drift from
      // core's look in either light or dark mode.
      useChartTheme,
      useThumbnailCapture,
      // SDK 1.14 — the shared card scope picker. An extension report that
      // wants "narrow this to a few cards (and everything under them)" gets
      // core's behaviour — browse-on-open, tree, ancestor-wins dedupe — rather
      // than re-rolling a weaker one. MUI-only, so a static import is fine.
      CardScopeDialog,
      dedupeScopeRoots,
      // SDK 1.24 — the full card browser. `CardScopeDialog` stays the compact
      // control a report toolbar opens over ONE type; this is the one to reach
      // for when the user picks across types, or when the caller doesn't know
      // in advance which type they want. MUI-only leaf, so a static import.
      CardMultiPicker,
      // SDK 1.27 — the single-select card picker (CLAUDE.md: *always use
      // CardPicker*). Same engine as the multi picker, for the dialog that
      // links ONE card. MUI-only leaf, so a static import.
      CardPicker,
      // SDK 1.29 — free text and stored HTML. `LinkifiedText` renders a
      // user-typed string with its http(s) addresses as new-tab links (a
      // fragment, so it sits inside the caller's own Typography);
      // `sanitizeRichHtml` is the one sanitiser for stored rich text — it
      // autolinks bare URLs and stamps every anchor target/rel. An extension
      // that renders a description or a rich-text field must not rebuild
      // either, or its links will behave differently from core's.
      LinkifiedText,
      sanitizeRichHtml,
      // SDK 1.15 — the whole report-scoping kit, so an extension report gets
      // "narrow this to a few cards and everything under them" with the same
      // saved-report round-trip and stale-id handling core reports have.
      CardScopeFilter,
      useCardScope,
      applyScope,
      // SDK 1.17 — data-grid + card-creation reuse. `loadAgGrid` resolves
      // core's code-split AG Grid chunk (module registration + the Theming
      // API themes ride along via agGridSetup) so extension grids share
      // core's grid look without bundling AG Grid; `CreateCardDialog` is
      // core's create-card modal (lazy wrapper), openable pre-configured
      // via initialType/initialSubtype/initialAttributes.
      // Since SDK 1.18 the resolved module also carries the documented grid
      // template hooks (UI_GUIDELINES §3.6) — `useColumnFreeze` and
      // `useColumnOrder` — lazily, so they stay in the code-split grid chunk.
      // Extension components call them off the loaded module; that is safe
      // because the grid component only mounts once the module resolved, so
      // hook call order stays stable.
      // Since SDK 1.22 it also resolves `useCellContextMenu`, so an
      // extension grid offers the same right-click / long-press cell menu
      // core grids have (Show matching · Filter out · Copy, plus
      // page-specific row actions via `extraItems` — the AdrGrid pattern).
      // Since SDK 1.30 it also resolves `useDragFill`, so an extension grid
      // with editable cells offers the Inventory's Excel-style fill-down
      // under the same five invariants (write-then-reload through the page's
      // own per-cell primitive, one wrapper ref borrowed from
      // `useColumnFreeze`, never a bulk endpoint). It rides the same chunk —
      // MUI plus `import type` from ag-grid — so nothing joins the eager
      // bundle.
      loadAgGrid: () =>
        Promise.all([
          import("ag-grid-react"),
          import("@/lib/agGridSetup"),
          import("@/components/grid/useColumnFreeze"),
          import("@/components/grid/useColumnOrder"),
          import("@/components/grid/useCellContextMenu"),
          import("@/components/grid/useDragFill"),
        ]).then(([agReact, setup, freeze, order, cellMenu, dragFill]) => ({
          AgGridReact: agReact.AgGridReact,
          gridThemeLight: setup.gridThemeLight,
          gridThemeDark: setup.gridThemeDark,
          useColumnFreeze: freeze.useColumnFreeze,
          useColumnOrder: order.useColumnOrder,
          useCellContextMenu: cellMenu.useCellContextMenu,
          useDragFill: dragFill.useDragFill,
        })),
      CreateCardDialog: ExtensionCreateCardDialog,
      // SDK 1.21 — timeline + dependency-view + filter-sidebar reuse.
      // `loadTimeline` resolves the time-travel slider and its pure helpers
      // in one call, so an extension timeline shares the exact semantics the
      // core reports have (range computation, arriving/retired classification,
      // milestone clustering, the persisted `timelineDate` convention via
      // `useTimeline`). An async loader, not a static import: the slider only
      // lives in report chunks today and must not join the eager main bundle.
      loadTimeline: () =>
        Promise.all([
          import("@/components/TimelineSlider"),
          import("@/features/reports/timelineRange"),
          import("@/hooks/useTimeline"),
        ]).then(([slider, range, timeline]) => ({
          TimelineSlider: slider.default,
          useTimeline: timeline.useTimeline,
          computeTimelineRange: range.computeTimelineRange,
          classifyTimelineChange: range.classifyTimelineChange,
          isPresentAtDate: range.isPresentAtDate,
          isVisibleAtDate: range.isVisibleAtDate,
          computeTimelineMilestones: range.computeTimelineMilestones,
          cardsChangingBetween: range.cardsChangingBetween,
        })),
      // `loadDependencyView` resolves the house dependency notation (the
      // Layered Dependency View) plus its layout engine from core's own
      // code-split chunk (React Flow + dagre ride along) — the same
      // reuse-over-rebuild posture as `loadRecharts`/`loadAgGrid`, and the
      // §3.10 rule applies: never substitute another graph library. The
      // layout module is handed back as a namespace so its node/edge
      // builders and helpers stay available without re-listing them here.
      loadDependencyView: () =>
        Promise.all([
          import("@/features/reports/LayeredDependencyView"),
          import("@/features/reports/layeredDependencyLayout"),
        ]).then(([view, layout]) => ({
          LayeredDependencyView: view.default,
          layeredDependencyLayout: layout,
        })),
      // The §3.11 filter-sidebar building blocks — section header with icon +
      // count chip, dense checkbox rows with semantic dots/icons and the
      // per-row freeze pin — so an extension grid page's sidebar is built
      // from the same anatomy as the Inventory's instead of a lookalike.
      FilterSectionHeader,
      FilterCheckboxList,
      ColumnFreezeToggle,
      // `loadReportExport` resolves core's own XLSX/PPTX report exporters.
      // An extension that wants a deck must NOT bundle a presentation
      // library: the engine that renders a core report to PowerPoint is the
      // one that should render an extension's, so the decks match and the
      // heavy dependency stays in the one code-split chunk that already
      // carries it. Async for exactly that reason.
      loadReportExport: () =>
        import("@/features/reports/reportExport").then((module) => ({
          exportReportToPptx: module.exportReportToPptx,
          exportReportToXlsx: module.exportReportToXlsx,
          extractSheetsFromDOM: module.extractSheetsFromDOM,
        })),
      // SDK 1.30 — the spreadsheet engine an extension GRID needs, as
      // distinct from the report exporters above: `exportCurrentViewToExcel`
      // / `buildCurrentViewWorkbook` are the Inventory's own WYSIWYG "export
      // what is on screen" (rows and displayed columns read off the grid
      // API), the two readers are the leaf `lib/spreadsheet.ts` lifted out
      // of the card importer, and `xlsx` is the vendored library itself (the
      // `loadRecharts` posture for a bare heavy dependency) so a caller can
      // append its own machine-readable sheet to the workbook core built.
      // An extension must never bundle a spreadsheet library of its own.
      loadSpreadsheet: () =>
        Promise.all([
          import("xlsx"),
          import("@/features/inventory/excelExport"),
          import("@/lib/spreadsheet"),
        ]).then(([xlsx, exp, sheet]) => ({
          xlsx,
          exportCurrentViewToExcel: exp.exportCurrentViewToExcel,
          buildCurrentViewWorkbook: exp.buildCurrentViewWorkbook,
          parseWorkbook: sheet.parseWorkbook,
          readWorkbookSheets: sheet.readWorkbookSheets,
        })),
    },
    register: registerExtension,
  };
}

/**
 * Fetch the entitlement-filtered manifest and import each bundle.
 * Call once after login; per-extension failures are recorded and
 * surfaced, never thrown.
 */
export async function loadUiExtensions(): Promise<void> {
  if (!beginExtensionLoad()) return;
  initExtensionHost();
  let manifest: UiManifestEntry[] = [];
  try {
    manifest = await api.get<UiManifestEntry[]>("/extensions/ui-manifest");
  } catch {
    // Backend older than the extension store, or transient failure — no UI extensions.
    return;
  }
  for (const entry of manifest) {
    if (entry.name) setExtensionDisplayName(entry.key, entry.name);
  }
  await Promise.all(
    manifest.map(async (entry) => {
      try {
        await import(/* @vite-ignore */ entry.entry);
        if (!getRegisteredExtensions().some((r) => r.key === entry.key)) {
          recordExtensionLoadError(
            entry.key,
            "bundle imported but never called TurboEA.register()",
          );
        }
      } catch (e) {
        recordExtensionLoadError(entry.key, e instanceof Error ? e.message : String(e));
      }
    }),
  );
}
