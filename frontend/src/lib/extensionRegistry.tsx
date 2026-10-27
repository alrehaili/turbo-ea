/**
 * Extension registry — the light half of the extension host.
 *
 * Holds what the always-loaded app needs from extensions: the contribution
 * types, the registry store, the hooks and getters mount points read, the
 * `ExtensionSlot` / `ExtensionBoundary` components and the route helpers. It
 * imports nothing heavy, so the main bundle stays small.
 *
 * The SDK surface extension bundles compile against (`window.TurboEA`), the
 * SDK-only components and the bundle loader live in `extensionHost.tsx`, which
 * re-exports everything here and is loaded only when extensions are loaded
 * (dynamically after sign-in) or by the pages that need the SDK itself.
 */

import { Alert } from "@mui/material";
import React, { useSyncExternalStore } from "react";

import { hasPermission } from "@/components/RequirePermission";
import { useAuthContext } from "@/hooks/AuthContext";
import type { ArchitectureDecision, Card } from "@/types";

export const UI_SDK_VERSION = "1.31";

/**
 * Core nav groups an extension route may request placement into (instead of the
 * default top-level nav entry). Whitelisted on purpose so an extension can only
 * land in sanctioned menus, never an arbitrary one; extend deliberately.
 *
 * `reports` and `grc` are top-bar dropdowns. `admin` (UI SDK 1.28) is the
 * Admin section of the user menu and the mobile drawer — the home for an
 * extension page that configures something rather than showing it, so it sits
 * beside Metamodel and Settings instead of claiming a top-bar icon every user
 * sees. It is gated by the route's own `permission` only: an extension decides
 * who may open its page, core decides where the entry lives.
 */
export const EXTENSION_NAV_GROUPS = ["reports", "grc", "admin"] as const;
export type ExtensionNavGroup = (typeof EXTENSION_NAV_GROUPS)[number];

export interface ExtensionRouteContribution {
  id: string;
  path: string; // mounted under /ext/{key}/... in the SPA router
  label: string;
  icon: string;
  permission?: string;
  component: React.ComponentType;
  // Optional placement hint: render this route's nav entry inside a core menu
  // group (e.g. "reports", or "admin" for the user menu's Admin section) rather
  // than as a top-level item. The route path and rendering are unchanged — only
  // where the menu entry appears. Omit for the current top-level behaviour. An
  // unrecognised value shows nowhere in the nav.
  navGroup?: ExtensionNavGroup;
  // Optional placement hint for a TOP-LEVEL entry: where in the bar it sits.
  // `start` / `end` / `before:<anchor>` / `after:<anchor>`, anchors being the
  // core nav keys in `NAV_ANCHORS` — the same grammar a manifest field section
  // uses to place itself on a card type. Defaults to `end`, which is the
  // behaviour every extension had before this existed, and an anchor not
  // currently in the bar (a module switched off) degrades to that default
  // rather than dropping the entry.
  //
  // Ignored when `navGroup` is set: the entry is then a child of that group,
  // and where the group itself sits is core's business.
  navPlacement?: string;
}

export interface ExtensionCardTabContribution {
  id: string;
  label: string;
  permission?: string;
  appliesTo?: string[]; // card-type keys; omit = all types
  component: React.ComponentType<{ cardId: string; cardType: string }>;
}

export interface ExtensionAdminPanelContribution {
  id: string;
  label: string;
  component: React.ComponentType;
}

/**
 * A panel rendered as a sub-tab of Admin → Settings → Integrations (SDK 1.16),
 * alongside the built-in ServiceNow integration and with the same chrome — the
 * sanctioned home for an extension that connects Turbo EA to an external
 * system (its connection settings, sync configuration, logs). A typed named
 * point rather than a generic slot because the hub needs display metadata
 * (label + icon) to build the sub-tab list before mounting anything.
 * `permission` hides the entry silently from users who lack it. `adminPanels`
 * is unchanged and still renders on Admin → Extensions; an integration opts
 * into the Integrations tab explicitly with this point.
 */
export interface ExtensionIntegrationPanelContribution {
  id: string;
  label: string; // sub-tab text — the extension localizes it at registration time
  icon?: string; // Material Symbols name shown next to the label
  permission?: string;
  component: React.ComponentType;
}

/** Props handed to an extension field type's read-only display component. */
export interface ExtensionFieldDisplayProps {
  field: { key: string; label: string; type: string; config?: Record<string, unknown> };
  value: unknown;
  config?: Record<string, unknown>;
}

/** Props handed to an extension field type's inline editor component. */
export interface ExtensionFieldEditorProps extends ExtensionFieldDisplayProps {
  onChange: (value: unknown) => void;
  error?: string;
}

/**
 * A custom field type an extension contributes to card attribute editing.
 * `type` MUST be namespaced `ext.{extensionKey}.*` (enforced at aggregation) so
 * two extensions can never collide and core can tell a custom type from an
 * unknown one. `config` is the per-field settings object (e.g. `{min,max}` for a
 * rating), sourced from the field's `config` in the metamodel.
 */
export interface ExtensionFieldTypeContribution {
  type: string;
  label: string;
  display?: React.ComponentType<ExtensionFieldDisplayProps>;
  editor?: React.ComponentType<ExtensionFieldEditorProps>;
  defaultConfig?: Record<string, unknown>;
  // Optional admin-side editor for this type's `config` object (SDK 1.5). When
  // present, the metamodel field editor mounts it (inside ExtensionBoundary)
  // instead of the generic type-aware config editor — so an extension can offer
  // a proper per-locale rubric/question editor. Falls back to the generic editor
  // when absent.
  configEditor?: React.ComponentType<{
    config: Record<string, unknown>;
    onChange: (config: Record<string, unknown>) => void;
  }>;
}

/** The payload an extension survey template posts to `POST /surveys`. */
export interface ExtensionSurveyTemplatePayload {
  name: string;
  description?: string;
  message?: string;
  target_type_key: string;
  target_filters?: Record<string, unknown>;
  target_roles?: string[];
  fields?: Array<Record<string, unknown>>;
}

/**
 * A "New from template" shortcut on the Surveys admin page. Clicking it mints a
 * fresh **draft** survey from `build()`'s payload (POST /surveys always creates
 * a draft) and opens it in the builder for the admin to review and send —
 * `build()` runs at click time so it may compute dynamic values (dates, etc.).
 */
export interface ExtensionSurveyTemplateContribution {
  id: string;
  label: string;
  icon?: string;
  build: () => ExtensionSurveyTemplatePayload;
}

/** Props every ADR panel component receives (SDK 1.3). */
export interface ExtensionAdrPanelProps {
  adrId: string;
  status: string; // draft | in_review | signed
  signed: boolean; // convenience: status === "signed" (attributes are frozen)
  // The panel must not allow edits when true: it is either a signed (frozen)
  // ADR or the read-only preview page. Editing is only offered on the editor
  // page for an unsigned ADR.
  readOnly: boolean;
}

/**
 * A panel rendered on the ADR editor and preview pages (SDK 1.3). ADRs are not
 * cards, so this is the sanctioned place to attach ADR-scoped UI — e.g. a
 * custom form that reads/writes the ADR `ext.*` attributes bag via
 * `PATCH /adr/{id}`. `appliesTo` has no analogue (there is only one ADR
 * "type"); gate with `permission` if needed. Rendered read-only-friendly: the
 * component should respect `signed` to disable editing once frozen.
 */
export interface ExtensionAdrPanelContribution {
  id: string;
  permission?: string;
  component: React.ComponentType<ExtensionAdrPanelProps>;
}

/** A section a plugin contributes into the core ADR DOCX export (SDK 1.3). */
export interface AdrExportSection {
  heading: string;
  paragraphs?: string[];
  table?: { headers: string[]; rows: string[][] };
}

/**
 * Contributes extra sections to the core ADR DOCX export (SDK 1.3). `build()`
 * receives the full ADR (including its `attributes` bag) and returns plain data
 * — core renders it with the document's own styles, so the plugin never touches
 * the `docx` library. Runs at export time inside a guard; a throw is skipped.
 */
export interface ExtensionAdrExportContribution {
  id: string;
  build: (adr: Record<string, unknown>) => AdrExportSection[];
}

/**
 * A plain-data column appended to the shared ADR grid (SDK 1.10) — the list
 * used by EA Delivery → Decisions and GRC → Governance → Decisions. Core
 * builds a native AG Grid ColDef from it, so the column is indistinguishable
 * from the built-in ones (theme, sorting, quick filter, resize, dark mode) and
 * a broken extension can never take the grid down: `value()`/`sortValue()`
 * run inside a guard — a throw yields an empty cell. `value()` returns the
 * display text (the ADR list summaries already carry the `attributes` bag, so
 * a column over `ext.*` data costs zero extra requests); `sortValue()`
 * optionally supplies the raw sortable value (e.g. a number behind a
 * currency-formatted string). Deliberately NOT a component — extensions
 * contribute data, core owns the rendering, same philosophy as
 * `adrExportSections`.
 */
export interface ExtensionAdrGridColumnContribution {
  id: string;
  label: string; // header text — the extension localizes it at registration time
  align?: "left" | "right";
  // Optional sizing hints for the AG Grid column (px). Default 150 / 120 when
  // omitted. The user can still resize; these set the initial width.
  width?: number;
  minWidth?: number;
  value: (adr: ArchitectureDecision) => string | null;
  sortValue?: (adr: ArchitectureDecision) => number | string | null;
}

/** Props a headless field-visibility provider receives (SDK 1.4). */
export interface ExtensionFieldVisibilityProps {
  card: Card;
  // Report which of the extension's own card fields to hide right now. Call on
  // mount and whenever the provider's (possibly async) logic resolves or
  // changes; reporting `[]` shows everything. `extKey` keys the report so
  // multiple providers' hidden sets union without clobbering each other — pass
  // the extension's own key (the same one it registered with).
  report: (extKey: string, hiddenKeys: string[]) => void;
}

/**
 * A generic slot contribution (SDK 1.12) — the forward path for adding plug
 * points without an SDK edit per location. `slot` is the location id an
 * extension targets (e.g. "card.detail.header", "risk.detail.panel"); core
 * exposes each location once via `<ExtensionSlot name="..." />` (component
 * slots) or `getExtensionSlots(name)` (data slots). A contribution supplies
 * exactly ONE of `component` (rendered by core inside an ExtensionBoundary,
 * receiving the slot's `context` as props) or `build` (returns plain data core
 * renders itself). `permission` hides the slot from users who lack it (silently
 * — never an access-denied page, unlike a full route); `appliesTo` optionally
 * filters on the context's `cardType`/`type`; `order` sorts within a slot
 * (default 0, ties keep registration order).
 *
 * Slot locations core exposes today:
 *   - `card.detail.header`  (component) — CardDetailContent. Core renders the
 *     contributions as ONE wrapping flex row (8px gap, hidden when empty), so
 *     contribute an inline item (a Chip) with no outer margins of its own; a
 *     contribution that needs its own line sets `flexBasis: "100%"`, and
 *     `order` decides where it sits in the row. The row ZEROES a contribution's
 *     own margins rather than trusting it not to set any: `align-items: center`
 *     centres a flex item's margin box, so a bundle built before this row —
 *     which spaces its own band — would otherwise render off the row's centre
 *     line.
 *   - `risk.detail.panel`   (component) — RiskDetailPage
 *   - `adr.header`, `adr.signature.footer` (component) — ADREditor/ADRPreview
 *   - `notification.preferences.channels` (data) — one column per
 *     extension-delivered notification channel. `build({channelKey})` returns
 *     `{label, order?}`; the column only renders when the BACKEND also reports
 *     the channel as live, so a UI-only bundle cannot conjure a column whose
 *     PATCH the backend would ignore.
 *   - `notification.preferences.footer` (component) — below the preferences
 *     table, context `{userId}`; where a channel shows its per-user link state.
 *   - `notification.detail` (component) — inside the bell's notification
 *     details dialog (opened for a notification sent with `detail=True` on the
 *     backend notify bridge), context `{id, type, title, message, link, data,
 *     cardId, createdAt}`. Rendered with `ownerExtKey = data.ext`, so only the
 *     extension that SENT the notification contributes; target your own
 *     declared type with `appliesTo` and never gate it with `permission` — the
 *     recipients are ordinary users.
 */
export interface ExtensionSlotContribution {
  slot: string;
  id: string;
  permission?: string;
  appliesTo?: string[];
  component?: React.ComponentType<Record<string, unknown>>;
  build?: (context: Record<string, unknown>) => unknown;
  order?: number;
}

export interface TurboExtensionUI {
  key: string;
  sdkVersion: string;
  routes?: ExtensionRouteContribution[];
  cardTabs?: ExtensionCardTabContribution[];
  adminPanels?: ExtensionAdminPanelContribution[];
  integrationPanels?: ExtensionIntegrationPanelContribution[];
  fieldTypes?: ExtensionFieldTypeContribution[];
  surveyTemplates?: ExtensionSurveyTemplateContribution[];
  adrPanels?: ExtensionAdrPanelContribution[];
  adrExportSections?: ExtensionAdrExportContribution[];
  adrGridColumns?: ExtensionAdrGridColumnContribution[];
  // Generic slot contributions (SDK 1.12) — the preferred way to attach to any
  // core-exposed location without a per-feature SDK extension point.
  slots?: ExtensionSlotContribution[];
  // Headless provider (renders null) that hides specific card fields at render
  // time — display-only, ungated, never deletes stored values. Degrades to
  // "show everything" when absent.
  fieldVisibility?: React.ComponentType<ExtensionFieldVisibilityProps>;
}

export interface RegisteredFieldType {
  extKey: string;
  contribution: ExtensionFieldTypeContribution;
}

export interface RegisteredSlot {
  extKey: string;
  contribution: ExtensionSlotContribution;
}

export interface RegisteredIntegrationPanel {
  extKey: string;
  contribution: ExtensionIntegrationPanelContribution;
}

export interface RegisteredSurveyTemplate {
  extKey: string;
  contribution: ExtensionSurveyTemplateContribution;
}

export interface RegisteredAdrPanel {
  extKey: string;
  contribution: ExtensionAdrPanelContribution;
}

export interface RegisteredAdrExport {
  extKey: string;
  contribution: ExtensionAdrExportContribution;
}

export interface RegisteredAdrGridColumn {
  extKey: string;
  contribution: ExtensionAdrGridColumnContribution;
}

export interface RegisteredFieldVisibility {
  extKey: string;
  provider: React.ComponentType<ExtensionFieldVisibilityProps>;
}

export interface RegisteredExtension {
  key: string;
  plugin: TurboExtensionUI;
}


// ---------------------------------------------------------------------------
// Registry store (useSyncExternalStore-backed so mount points re-render)
// ---------------------------------------------------------------------------

let _registered: RegisteredExtension[] = [];
let _loadErrors: Record<string, string> = {};
// Display names from the UI manifest, keyed by extension key — so the bell
// can say who sent a notification without a second request.
let _displayNames: Record<string, string> = {};
const _listeners = new Set<() => void>();
let _loadStarted = false;
// Cached, stable snapshots — recomputed lazily and invalidated on every
// notify() so useSyncExternalStore never loops.
let _fieldTypesCache: Record<string, RegisteredFieldType> | null = null;
let _surveyTemplatesCache: RegisteredSurveyTemplate[] | null = null;
let _adrExportCache: RegisteredAdrExport[] | null = null;
let _adrGridColumnsCache: RegisteredAdrGridColumn[] | null = null;
let _fieldVisibilityCache: RegisteredFieldVisibility[] | null = null;
// Generic slots are cached per slot name — one stable snapshot array per name so
// each `getExtensionSlots(name)` is safe as a useSyncExternalStore snapshot.
let _slotsCache: Map<string, RegisteredSlot[]> | null = null;
let _integrationPanelsCache: RegisteredIntegrationPanel[] | null = null;

function notify() {
  _fieldTypesCache = null;
  _surveyTemplatesCache = null;
  _adrExportCache = null;
  _adrGridColumnsCache = null;
  _fieldVisibilityCache = null;
  _slotsCache = null;
  _integrationPanelsCache = null;
  _listeners.forEach((fn) => fn());
}

function subscribe(fn: () => void): () => void {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}

function sdkMajor(v: string): number {
  return Number.parseInt(String(v).split(".", 1)[0] ?? "", 10);
}

export function registerExtension(key: string, plugin: TurboExtensionUI): void {
  if (!plugin || plugin.key !== key) {
    _loadErrors = { ..._loadErrors, [key]: `register() key mismatch (${plugin?.key})` };
    notify();
    return;
  }
  if (sdkMajor(plugin.sdkVersion) !== sdkMajor(UI_SDK_VERSION)) {
    _loadErrors = {
      ..._loadErrors,
      [key]: `built for UI SDK ${plugin.sdkVersion}, host provides ${UI_SDK_VERSION}`,
    };
    notify();
    return;
  }
  _registered = [..._registered.filter((r) => r.key !== key), { key, plugin }];
  notify();
}

/**
 * Mark the one-time bundle load as started. False when it already was, so
 * `loadUiExtensions` (in the SDK module) runs once per session.
 */
export function beginExtensionLoad(): boolean {
  if (_loadStarted) return false;
  _loadStarted = true;
  return true;
}

/** Record why an extension bundle failed to load or register. */
export function recordExtensionLoadError(key: string, message: string): void {
  _loadErrors = { ..._loadErrors, [key]: message };
  notify();
}

export function getRegisteredExtensions(): RegisteredExtension[] {
  return _registered;
}

export function getExtensionLoadErrors(): Record<string, string> {
  return _loadErrors;
}

export function useExtensionUI(): RegisteredExtension[] {
  return useSyncExternalStore(subscribe, getRegisteredExtensions, getRegisteredExtensions);
}

/**
 * Map of every registered custom field type (`ext.{key}.*` → contribution).
 * A contribution whose `type` is not namespaced under its own extension key is
 * dropped (defence against collisions). The result is cached and only changes
 * when the registry does, so it is safe as a useSyncExternalStore snapshot.
 */
export function getExtensionFieldTypes(): Record<string, RegisteredFieldType> {
  if (_fieldTypesCache) return _fieldTypesCache;
  const out: Record<string, RegisteredFieldType> = {};
  for (const { key, plugin } of _registered) {
    for (const ft of plugin.fieldTypes ?? []) {
      if (!ft?.type || !ft.type.startsWith(`ext.${key}.`)) {
        console.warn(
          `[extension:${key}] field type "${ft?.type}" must be namespaced ext.${key}.* — ignored`,
        );
        continue;
      }
      out[ft.type] = { extKey: key, contribution: ft };
    }
  }
  _fieldTypesCache = out;
  return out;
}

export function useExtensionFieldTypes(): Record<string, RegisteredFieldType> {
  return useSyncExternalStore(subscribe, getExtensionFieldTypes, getExtensionFieldTypes);
}

/**
 * Survey templates contributed by registered extensions, in registration order.
 * A contribution missing `id`/`label`/`build` is dropped. Cached (stable
 * reference) so it is safe as a useSyncExternalStore snapshot.
 */
export function getExtensionSurveyTemplates(): RegisteredSurveyTemplate[] {
  if (_surveyTemplatesCache) return _surveyTemplatesCache;
  const out: RegisteredSurveyTemplate[] = [];
  for (const { key, plugin } of _registered) {
    for (const tpl of plugin.surveyTemplates ?? []) {
      if (!tpl?.id || !tpl.label || typeof tpl.build !== "function") {
        console.warn(`[extension:${key}] invalid survey template — ignored`, tpl);
        continue;
      }
      out.push({ extKey: key, contribution: tpl });
    }
  }
  _surveyTemplatesCache = out;
  return out;
}

export function useExtensionSurveyTemplates(): RegisteredSurveyTemplate[] {
  return useSyncExternalStore(
    subscribe,
    getExtensionSurveyTemplates,
    getExtensionSurveyTemplates,
  );
}

/**
 * Headless field-visibility providers contributed by registered extensions, in
 * registration order (one per extension at most). A non-function `fieldVisibility`
 * is dropped. Cached (stable reference) so the mount point can render a fixed
 * list of provider slots — each provider keeps its own hook order across
 * re-renders — and so it is safe as a useSyncExternalStore snapshot.
 */
export function getExtensionFieldVisibilityProviders(): RegisteredFieldVisibility[] {
  if (_fieldVisibilityCache) return _fieldVisibilityCache;
  const out: RegisteredFieldVisibility[] = [];
  for (const { key, plugin } of _registered) {
    const provider = plugin.fieldVisibility;
    if (provider === undefined) continue;
    if (typeof provider !== "function") {
      console.warn(`[extension:${key}] invalid fieldVisibility provider — ignored`, provider);
      continue;
    }
    out.push({ extKey: key, provider });
  }
  _fieldVisibilityCache = out;
  return out;
}

export function useExtensionFieldVisibilityProviders(): RegisteredFieldVisibility[] {
  return useSyncExternalStore(
    subscribe,
    getExtensionFieldVisibilityProviders,
    getExtensionFieldVisibilityProviders,
  );
}

/**
 * ADR panels contributed by registered extensions, in registration order.
 * Consumed via `useExtensionUI()` at the mount points (ADR editor/preview); a
 * contribution missing `id`/`component` is dropped. Not cached — the caller
 * already re-renders off `useExtensionUI`.
 */
export function getExtensionAdrPanels(): RegisteredAdrPanel[] {
  const out: RegisteredAdrPanel[] = [];
  for (const { key, plugin } of _registered) {
    for (const panel of plugin.adrPanels ?? []) {
      if (!panel?.id || typeof panel.component !== "function") {
        console.warn(`[extension:${key}] invalid ADR panel — ignored`, panel);
        continue;
      }
      out.push({ extKey: key, contribution: panel });
    }
  }
  return out;
}

export function useExtensionAdrPanels(): RegisteredAdrPanel[] {
  // Depend on the registry snapshot so mounts re-render on (un)register.
  useSyncExternalStore(subscribe, getRegisteredExtensions, getRegisteredExtensions);
  return getExtensionAdrPanels();
}

/**
 * ADR DOCX export contributions, in registration order. A contribution missing
 * `id`/`build` is dropped. Cached (stable reference) so the non-React exporter
 * (`adrExport.ts`) can call it directly.
 */
export function getExtensionAdrExportSections(): RegisteredAdrExport[] {
  if (_adrExportCache) return _adrExportCache;
  const out: RegisteredAdrExport[] = [];
  for (const { key, plugin } of _registered) {
    for (const contribution of plugin.adrExportSections ?? []) {
      if (!contribution?.id || typeof contribution.build !== "function") {
        console.warn(`[extension:${key}] invalid ADR export contribution — ignored`, contribution);
        continue;
      }
      out.push({ extKey: key, contribution });
    }
  }
  _adrExportCache = out;
  return out;
}

/**
 * ADR grid column contributions (SDK 1.10), in registration order. A
 * contribution missing `id`/`label`/`value` is dropped. Cached (stable
 * reference) so it is safe as a useSyncExternalStore snapshot — the grid's
 * memoized columnDefs only rebuild when the registry actually changes.
 */
export function getExtensionAdrGridColumns(): RegisteredAdrGridColumn[] {
  if (_adrGridColumnsCache) return _adrGridColumnsCache;
  const out: RegisteredAdrGridColumn[] = [];
  for (const { key, plugin } of _registered) {
    for (const contribution of plugin.adrGridColumns ?? []) {
      if (!contribution?.id || !contribution.label || typeof contribution.value !== "function") {
        console.warn(`[extension:${key}] invalid ADR grid column — ignored`, contribution);
        continue;
      }
      out.push({ extKey: key, contribution });
    }
  }
  _adrGridColumnsCache = out;
  return out;
}

export function useExtensionAdrGridColumns(): RegisteredAdrGridColumn[] {
  return useSyncExternalStore(subscribe, getExtensionAdrGridColumns, getExtensionAdrGridColumns);
}

/**
 * Integration panels contributed by registered extensions (SDK 1.16), in
 * registration order. Rendered as sub-tabs of Admin → Settings → Integrations
 * next to the built-in ServiceNow integration; the hub filters `permission`
 * itself so a hidden entry never even shows a tab. A contribution missing
 * `id`/`label`/`component` is dropped. Cached (stable reference) so it is safe
 * as a useSyncExternalStore snapshot.
 */
export function getExtensionIntegrationPanels(): RegisteredIntegrationPanel[] {
  if (_integrationPanelsCache) return _integrationPanelsCache;
  const out: RegisteredIntegrationPanel[] = [];
  for (const { key, plugin } of _registered) {
    for (const panel of plugin.integrationPanels ?? []) {
      if (!panel?.id || !panel.label || typeof panel.component !== "function") {
        console.warn(`[extension:${key}] invalid integration panel — ignored`, panel);
        continue;
      }
      out.push({ extKey: key, contribution: panel });
    }
  }
  _integrationPanelsCache = out;
  return out;
}

export function useExtensionIntegrationPanels(): RegisteredIntegrationPanel[] {
  return useSyncExternalStore(
    subscribe,
    getExtensionIntegrationPanels,
    getExtensionIntegrationPanels,
  );
}

/**
 * Generic slot contributions for a given `slot` name (SDK 1.12), in `order`
 * then registration order. A contribution without an `id`, or that does not
 * supply exactly one of `component`/`build`, is dropped with a warning. Cached
 * per slot name (stable array reference until the registry changes) so it is
 * safe both as a useSyncExternalStore snapshot and for non-React data-slot
 * consumers to call directly.
 */
export function getExtensionSlots(slot: string): RegisteredSlot[] {
  if (!_slotsCache) _slotsCache = new Map();
  const cached = _slotsCache.get(slot);
  if (cached) return cached;
  const out: RegisteredSlot[] = [];
  for (const { key, plugin } of _registered) {
    for (const contribution of plugin.slots ?? []) {
      if (contribution?.slot !== slot) continue;
      const hasComponent = typeof contribution.component === "function";
      const hasBuild = typeof contribution.build === "function";
      // Require an id and EXACTLY one of component/build (XOR).
      if (!contribution.id || hasComponent === hasBuild) {
        console.warn(
          `[extension:${key}] invalid slot contribution for "${slot}" ` +
            `(needs id + exactly one of component/build) — ignored`,
          contribution,
        );
        continue;
      }
      out.push({ extKey: key, contribution });
    }
  }
  out.sort((a, b) => (a.contribution.order ?? 0) - (b.contribution.order ?? 0));
  _slotsCache.set(slot, out);
  return out;
}

export function useExtensionSlots(slot: string): RegisteredSlot[] {
  const getSnapshot = React.useCallback(() => getExtensionSlots(slot), [slot]);
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

/**
 * Renders every component slot registered for `name`, each inside an
 * ExtensionBoundary, passing `context` as props. Core exposes a new pluggable
 * location by dropping this once — no SDK type/hook/version change. A slot with
 * a `permission` the viewer lacks is hidden silently (not an access-denied
 * page); `appliesTo` filters on `context.cardType`/`context.type`. Data slots
 * (a `build` instead of a `component`) are not rendered here — their core
 * consumer calls `getExtensionSlots(name)` and renders the data itself.
 */
export function ExtensionSlot({
  name,
  context,
  ownerExtKey,
}: {
  name: string;
  context?: Record<string, unknown>;
  /** When set, only this extension's contributions render — for a location
   *  that belongs to one extension's own data (its notification's details),
   *  where a second extension must not inject into the first's content. */
  ownerExtKey?: string;
}) {
  const slots = useExtensionSlots(name);
  const { user } = useAuthContext();
  const typeKey = context?.cardType ?? context?.type;
  return (
    <>
      {slots.map(({ extKey, contribution }) => {
        const Component = contribution.component;
        if (!Component) return null; // data slot — rendered by its own core consumer
        if (ownerExtKey !== undefined && extKey !== ownerExtKey) return null;
        if (
          contribution.permission &&
          !hasPermission(user?.permissions, contribution.permission)
        ) {
          return null;
        }
        if (
          contribution.appliesTo &&
          !(typeof typeKey === "string" && contribution.appliesTo.includes(typeKey))
        ) {
          return null;
        }
        return (
          <ExtensionBoundary key={`${extKey}:${contribution.id}`} extensionKey={extKey}>
            <Component {...(context ?? {})} />
          </ExtensionBoundary>
        );
      })}
    </>
  );
}

/** Test helper — wipe the registry between tests. */
export function resetExtensionHost(): void {
  _registered = [];
  _loadErrors = {};
  _displayNames = {};
  _loadStarted = false;
  _fieldTypesCache = null;
  _slotsCache = null;
  _integrationPanelsCache = null;
  notify();
}

// ---------------------------------------------------------------------------
// Route outlet — one wildcard SPA route renders all extension pages
// ---------------------------------------------------------------------------

/** All route contributions across registered extensions. */
export function getExtensionRoutes(): { extKey: string; route: ExtensionRouteContribution }[] {
  return _registered.flatMap(({ key, plugin }) =>
    (plugin.routes ?? []).map((route) => ({ extKey: key, route })),
  );
}

/** Extension routes that requested placement into a given core nav group. */
export function getExtensionRoutesForGroup(
  group: ExtensionNavGroup,
): { extKey: string; route: ExtensionRouteContribution }[] {
  return _registered.flatMap(({ key, plugin }) =>
    (plugin.routes ?? [])
      .filter((r) => r.navGroup === group)
      .map((route) => ({ extKey: key, route })),
  );
}

/**
 * The display name the UI manifest reported for an extension, or its key when
 * the manifest carried none (a backend older than 2.128.0, or a bundle that
 * never loaded). Test helper `setExtensionDisplayName` seeds it.
 */
export function getExtensionDisplayName(key: string): string {
  return _displayNames[key] ?? key;
}

/** Test helper — what `loadUiExtensions` records from the manifest. */
export function setExtensionDisplayName(key: string, name: string): void {
  _displayNames = { ..._displayNames, [key]: name };
}

/**
 * Whether the viewer may open an extension page at `path` (an `/ext/<key>/…`
 * link a notification or a todo carries). Fails CLOSED: no registered route
 * matches ⇒ false — the bundle is not loaded or not entitled, so the page
 * would be "not found" — and a route that declares a `permission` needs the
 * viewer to hold it. Query string and hash are ignored; a route matches its
 * own path or a `/`-boundary prefix of it (`/ext/x` covers `/ext/x/runs`).
 */
export function canOpenExtensionPath(
  path: string,
  perms: Record<string, boolean> | undefined,
): boolean {
  const pathname = path.split(/[?#]/, 1)[0] ?? "";
  if (!pathname.startsWith("/ext/")) return false;
  for (const { route } of getExtensionRoutes()) {
    const base = route.path.replace(/\/+$/, "");
    if (pathname !== base && !pathname.startsWith(`${base}/`)) continue;
    return route.permission ? hasPermission(perms, route.permission) : true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// Error boundary — wraps every extension-provided component
// ---------------------------------------------------------------------------

interface BoundaryProps {
  extensionKey: string;
  children: React.ReactNode;
}

interface BoundaryState {
  error: string | null;
}

export class ExtensionBoundary extends React.Component<BoundaryProps, BoundaryState> {
  state: BoundaryState = { error: null };

  static getDerivedStateFromError(error: unknown): BoundaryState {
    return { error: error instanceof Error ? error.message : String(error) };
  }

  componentDidCatch(error: unknown) {
    console.error(`[extension:${this.props.extensionKey}]`, error);
  }

  render() {
    if (this.state.error) {
      return (
        <Alert severity="error" variant="outlined" sx={{ m: 1 }}>
          Extension “{this.props.extensionKey}” failed to render: {this.state.error}
        </Alert>
      );
    }
    return this.props.children;
  }
}
