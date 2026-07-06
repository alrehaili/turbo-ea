import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Breadcrumbs from "@mui/material/Breadcrumbs";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Skeleton from "@mui/material/Skeleton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import MetricCard from "@/features/reports/MetricCard";
import { getCurrentPhase } from "@/components/LifecycleBadge";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useTypeLabel, useSubtypeLabel } from "@/hooks/useResolveLabel";
import {
  CARD_TYPE_COLORS,
  DATA_QUALITY_COLORS,
  LAYER_COLORS,
  STATUS_COLORS,
} from "@/theme/tokens";
import type { Card, CardListResponse, CardType, SubtypeDef } from "@/types";

interface CountsResponse {
  by_type: { type: string; count: number }[];
}

interface LayerData {
  apps: Card[];
  capabilities: Card[];
  dataObjects: Card[];
  interfaces: Card[];
  technology: Card[];
  counts: Map<string, number>;
}

interface Segment {
  label: string;
  value: number;
  color: string;
}

interface AppBucket {
  key: string;
  label: string;
  cards: Card[];
}

const EMPTY_DATA: LayerData = {
  apps: [],
  capabilities: [],
  dataObjects: [],
  interfaces: [],
  technology: [],
  counts: new Map(),
};

const TOP_N = 12;

/**
 * Lifecycle phase → segment color for the stacked-bar. Mirrors the semantic
 * intent of `LifecycleBadge` (default/primary/success/warning/error) so the
 * bar reads the same way as the chip on the card detail page.
 */
const LIFECYCLE_PHASE_COLORS: Record<string, string> = {
  plan: STATUS_COLORS.neutral,
  phaseIn: STATUS_COLORS.info,
  active: STATUS_COLORS.success,
  phaseOut: STATUS_COLORS.warning,
  endOfLife: STATUS_COLORS.error,
  notSet: "#cbd5e1",
};
const LIFECYCLE_PHASES = ["plan", "phaseIn", "active", "phaseOut", "endOfLife", "notSet"] as const;

/**
 * 4-tier data-quality color. Matches the Dashboard's data-quality histogram
 * (`DATA_QUALITY_COLORS`) so a Critical Apps bar reads consistently across
 * views: red/warning/info/success as quality climbs.
 */
function qualityColor(q: number): string {
  if (q < 25) return DATA_QUALITY_COLORS["0-25"];
  if (q < 50) return DATA_QUALITY_COLORS["25-50"];
  if (q < 75) return DATA_QUALITY_COLORS["50-75"];
  return DATA_QUALITY_COLORS["75-100"];
}

function attr(card: Card, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = card.attributes?.[key];
    if (typeof value === "string" && value.trim()) return value;
    if (typeof value === "number") return String(value);
  }
  return undefined;
}

function containsAny(value: string | undefined, words: string[]) {
  const text = (value ?? "").toLowerCase();
  return words.some((word) => text.includes(word));
}

function criticality(card: Card) {
  return attr(card, ["businessCriticality", "criticality", "criticalityLevel", "importance"]);
}

function isCritical(card: Card) {
  return containsAny(criticality(card), ["critical", "high", "mission", "strategic"]);
}

function healthBucket(card: Card): "healthy" | "atRisk" | "retired" | "unknown" {
  const phase = getCurrentPhase(card.lifecycle);
  if (phase === "endOfLife") return "retired";
  if (phase === "phaseOut") return "atRisk";
  if ((card.data_quality ?? 0) < 60) return "atRisk";
  if (phase === "active" || phase === "phaseIn") return "healthy";
  return "unknown";
}

function healthSegments(apps: Card[], labels: Record<string, string>): Segment[] {
  const buckets: Record<string, number> = { healthy: 0, atRisk: 0, retired: 0, unknown: 0 };
  for (const app of apps) buckets[healthBucket(app)] += 1;
  return [
    { label: labels.healthy, value: buckets.healthy, color: STATUS_COLORS.success },
    { label: labels.atRisk, value: buckets.atRisk, color: STATUS_COLORS.warning },
    { label: labels.retired, value: buckets.retired, color: STATUS_COLORS.neutral },
    { label: labels.unknown, value: buckets.unknown, color: "#cbd5e1" },
  ].filter((s) => s.value > 0);
}

function portfolioSegments(apps: Card[], subtypeLabels: Map<string, string>, unclassified: string): Segment[] {
  const counts = new Map<string, number>();
  for (const app of apps) {
    const key = app.subtype ?? "";
    const label = subtypeLabels.get(key) ?? unclassified;
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  const palette = [
    CARD_TYPE_COLORS.Application,
    CARD_TYPE_COLORS.Interface,
    CARD_TYPE_COLORS.DataObject,
    CARD_TYPE_COLORS.ITComponent,
    STATUS_COLORS.neutral,
  ];
  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([label, value], index) => ({ label, value, color: palette[index] ?? STATUS_COLORS.neutral }));
}

function ownerCount(apps: Card[]) {
  const owners = new Set<string>();
  for (const app of apps) {
    for (const stakeholder of app.stakeholders ?? []) {
      owners.add(stakeholder.user_id || stakeholder.user_email || stakeholder.user_display_name || stakeholder.id);
    }
  }
  return owners.size;
}

/**
 * Bucket applications by their subtype (metamodel-driven, not English keywords).
 * We show the top 3 subtypes by app count as bands; anything else is folded
 * into an "Other" bucket if non-empty.
 */
function bucketAppsBySubtype(
  apps: Card[],
  subtypes: SubtypeDef[],
  subtypeLabel: (s: SubtypeDef | null) => string,
  otherLabel: string,
): AppBucket[] {
  const byKey = new Map<string, Card[]>();
  for (const app of apps) {
    const k = app.subtype ?? "";
    if (!byKey.has(k)) byKey.set(k, []);
    byKey.get(k)!.push(app);
  }
  const known = new Map(subtypes.map((s) => [s.key, s]));
  const entries: AppBucket[] = [];
  for (const [key, cards] of byKey.entries()) {
    if (!key) continue;
    const def = known.get(key);
    entries.push({ key, label: subtypeLabel(def ?? null) || key, cards });
  }
  entries.sort((a, b) => b.cards.length - a.cards.length);
  const top = entries.slice(0, 3);
  const rest = entries.slice(3).flatMap((e) => e.cards);
  const unclassified = byKey.get("") ?? [];
  const other = [...rest, ...unclassified];
  if (other.length > 0) top.push({ key: "__other", label: otherLabel, cards: other });
  return top;
}

function percent(value: number, total: number) {
  if (!total) return 0;
  return Math.round((value / total) * 100);
}

interface CapabilityNode {
  card: Card;
  children: Card[];
}

/**
 * Build a shallow parent-child tree from the fetched capability page. A card
 * whose parent isn't in the fetched set is treated as a root — this keeps
 * the tree well-defined even when the page cuts across the hierarchy. Roots
 * are alphabetical; children keep the API's return order.
 *
 * Depth is intentionally capped at one level — the goal is to show BRM
 * grouping (Line of Business → Function, or Function → Capability) at a
 * glance, not a full tree. Deeper drill-down belongs on the Capability Map.
 */
function buildCapabilityTree(cards: Card[]): CapabilityNode[] {
  const byId = new Map(cards.map((c) => [c.id, c]));
  const roots: CapabilityNode[] = [];
  const childrenByParent = new Map<string, Card[]>();
  for (const card of cards) {
    const isRoot = !card.parent_id || !byId.has(card.parent_id);
    if (isRoot) {
      roots.push({ card, children: [] });
    } else {
      const list = childrenByParent.get(card.parent_id!) ?? [];
      list.push(card);
      childrenByParent.set(card.parent_id!, list);
    }
  }
  for (const root of roots) {
    root.children = childrenByParent.get(root.card.id) ?? [];
  }
  return roots.sort((a, b) => a.card.name.localeCompare(b.card.name));
}

function withAlpha(hex: string, alpha: string) {
  return `${hex}${alpha}`;
}

function Donut({
  segments,
  total,
  totalLabel,
  size = 132,
  ariaLabel,
}: {
  segments: Segment[];
  total: number;
  totalLabel: string;
  size?: number;
  /** Textual alternative for screen readers — the visual is a CSS gradient. */
  ariaLabel?: string;
}) {
  let start = 0;
  const stops = segments.map((segment) => {
    const size = total ? (segment.value / total) * 100 : 0;
    const stop = `${segment.color} ${start}% ${start + size}%`;
    start += size;
    return stop;
  });
  const inner = Math.round(size * 0.62);
  return (
    <Box
      role="img"
      aria-label={ariaLabel}
      sx={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: `conic-gradient(${stops.join(", ") || "#e2e8f0 0 100%"})`,
        display: "grid",
        placeItems: "center",
        flexShrink: 0,
      }}
    >
      <Box
        sx={{
          width: inner,
          height: inner,
          borderRadius: "50%",
          bgcolor: "background.paper",
          display: "grid",
          placeItems: "center",
          textAlign: "center",
          boxShadow: "inset 0 0 0 1px rgba(15, 23, 42, 0.08)",
        }}
      >
        <Typography variant={size >= 130 ? "h5" : "h6"} sx={{ fontWeight: 800 }}>
          {total}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {totalLabel}
        </Typography>
      </Box>
    </Box>
  );
}

function MiniCard({
  card,
  icon,
  color,
  subtypeText,
}: {
  card: Pick<Card, "id" | "name" | "subtype">;
  icon: string;
  color: string;
  /**
   * Localized subtype label to render as the caption. Callers resolve this via
   * `useSubtypeLabel()` at the parent level so this component doesn't need to
   * know about the metamodel — and doesn't leak the raw `subtype` key
   * (`businessApplication`, `logicalInterface`, …) into the UI.
   */
  subtypeText?: string;
}) {
  return (
    <Box
      component={RouterLink}
      to={`/cards/${card.id}`}
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        minHeight: 52,
        p: 1,
        border: "1px solid",
        borderColor: withAlpha(color, "33"),
        borderRadius: 1,
        color: "text.primary",
        textDecoration: "none",
        bgcolor: "background.paper",
        "&:hover": { borderColor: color, boxShadow: 1 },
      }}
    >
      <Box
        sx={{
          width: 34,
          height: 34,
          borderRadius: 1,
          bgcolor: withAlpha(color, "12"),
          color,
          display: "grid",
          placeItems: "center",
          flexShrink: 0,
        }}
      >
        <MaterialSymbol icon={icon} size={21} color="inherit" />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="body2" sx={{ fontWeight: 750 }} noWrap>
          {card.name}
        </Typography>
        {subtypeText && (
          <Typography variant="caption" color="text.secondary" noWrap display="block">
            {subtypeText}
          </Typography>
        )}
      </Box>
    </Box>
  );
}

/**
 * Soft divider between swim-lane bands. Replaces the previous vertical
 * `more_vert` triple-dot icon (which read like a "click to expand"
 * affordance that did nothing).
 */
function BandDivider() {
  return (
    <Box aria-hidden sx={{ py: 1, display: "flex", justifyContent: "center" }}>
      <Box sx={{ width: "40%", borderTop: "1px dashed", borderColor: "divider" }} />
    </Box>
  );
}

/**
 * Horizontal stacked bar of app-count per lifecycle phase. Renders as one
 * bar with colored segments proportional to bucket size + a compact legend
 * beneath. Empty when no apps have a resolvable phase.
 */
function LifecycleStackedBar({
  buckets,
  total,
  labels,
  emptyLabel,
}: {
  buckets: Record<string, number>;
  total: number;
  labels: Record<string, string>;
  emptyLabel: string;
}) {
  if (!total) {
    return (
      <Typography variant="body2" color="text.secondary">
        {emptyLabel}
      </Typography>
    );
  }
  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          height: 14,
          borderRadius: 1,
          overflow: "hidden",
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        {LIFECYCLE_PHASES.map((phase) => {
          const value = buckets[phase] ?? 0;
          if (!value) return null;
          const pct = (value / total) * 100;
          return (
            <Tooltip key={phase} title={`${labels[phase]}: ${value}`}>
              <Box
                sx={{
                  width: `${pct}%`,
                  bgcolor: LIFECYCLE_PHASE_COLORS[phase],
                  transition: "width 200ms",
                }}
              />
            </Tooltip>
          );
        })}
      </Box>
      <Box
        sx={{
          mt: 1,
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 0.5,
        }}
      >
        {LIFECYCLE_PHASES.map((phase) => {
          const value = buckets[phase] ?? 0;
          if (!value) return null;
          return (
            <Box key={phase} sx={{ display: "flex", alignItems: "center", gap: 0.75, minWidth: 0 }}>
              <Box
                sx={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  bgcolor: LIFECYCLE_PHASE_COLORS[phase],
                  flexShrink: 0,
                }}
              />
              <Typography variant="caption" color="text.secondary" noWrap>
                {labels[phase]}
              </Typography>
              <Typography variant="caption" sx={{ fontWeight: 800, ml: "auto" }}>
                {value}
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

/**
 * Skeleton state matching the real layout — 4 metric tiles up top, a tall
 * band-stack in the main column, and a right rail of Paper blocks. Reduces
 * perceived load time vs a lonely spinner in an empty viewport.
 */
function LoadingSkeleton() {
  return (
    <Box sx={{ maxWidth: 1500, mx: "auto" }}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1fr) 620px" },
          gap: 2,
          mb: 2,
        }}
      >
        <Box>
          <Skeleton variant="text" width={320} height={44} />
          <Skeleton variant="text" width={480} height={22} />
        </Box>
        <Box sx={{ display: "flex", gap: 1.25, flexWrap: "wrap" }}>
          {[0, 1, 2, 3].map((i) => (
            <Skeleton
              key={i}
              variant="rounded"
              sx={{ flex: "1 1 150px", minWidth: 150, height: 90 }}
            />
          ))}
        </Box>
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1fr) 360px" },
          gap: 2,
        }}
      >
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          <Skeleton variant="rounded" height={640} />
          <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1.35fr 1.35fr", gap: 1.5 }}>
            <Skeleton variant="rounded" height={160} />
            <Skeleton variant="rounded" height={160} />
            <Skeleton variant="rounded" height={160} />
          </Box>
        </Box>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          <Skeleton variant="rounded" height={210} />
          <Skeleton variant="rounded" height={210} />
          <Skeleton variant="rounded" height={200} />
        </Box>
      </Box>
    </Box>
  );
}

function MoreChip({ count, to, label }: { count: number; to: string; label: string }) {
  if (count <= 0) return null;
  return (
    <Chip
      component={RouterLink}
      to={to}
      clickable
      variant="outlined"
      size="small"
      label={label}
      sx={{ alignSelf: "start" }}
    />
  );
}

function LayerBand({
  title,
  subtitle,
  color,
  emphasized,
  children,
}: {
  title: string;
  subtitle: string;
  color: string;
  /**
   * Emphasise this band as the anchor of the swim-lane. Renders with a
   * 3px left accent border in the band color so users' eyes land on the
   * primary layer first (used on the Application band).
   */
  emphasized?: boolean;
  children: ReactNode;
}) {
  return (
    <Box
      sx={{
        border: "1px solid",
        borderColor: withAlpha(color, "33"),
        borderLeft: emphasized ? `3px solid ${color}` : undefined,
        bgcolor: withAlpha(color, "08"),
        borderRadius: 1,
        p: 1.5,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "baseline", gap: 0.75, mb: 1.25, flexWrap: "wrap" }}>
        <Typography variant="subtitle1" sx={{ color, fontWeight: 850 }}>
          {title}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {subtitle}
        </Typography>
      </Box>
      {children}
    </Box>
  );
}

/**
 * Resolve a metamodel-driven type descriptor: the CardType (or null if the
 * admin has renamed/removed the key), plus safe fallbacks for icon/color and
 * a localized label. Prevents the report from disappearing when a type key
 * doesn't exist in this tenant's metamodel.
 */
function useResolvedType(
  types: CardType[],
  key: string,
  fallbackIcon: string,
  fallbackColor: string,
) {
  const typeLabelFn = useTypeLabel();
  return useMemo(() => {
    const type = types.find((t) => t.key === key) ?? null;
    return {
      type,
      key,
      label: type ? typeLabelFn(type) : key,
      icon: type?.icon || fallbackIcon,
      color: type?.color || fallbackColor,
    };
  }, [types, key, fallbackIcon, fallbackColor, typeLabelFn]);
}

export default function ApplicationLayerOverviewReport() {
  const { t } = useTranslation(["reports", "common"]);
  const { types } = useMetamodel();
  const subtypeLabel = useSubtypeLabel();
  const theme = useTheme();
  // On xs, the view stacks to a single column and every band becomes
  // enormously tall. Clip each band to a top-3 slice on phone so the whole
  // dashboard fits without a marathon scroll; the "+N more" chip still links
  // out to the filtered inventory.
  const isXs = useMediaQuery(theme.breakpoints.down("sm"));
  const cap = (n: number) => (isXs ? Math.min(n, 3) : n);

  const [data, setData] = useState<LayerData>(EMPTY_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const appType = useResolvedType(types, "Application", "apps", CARD_TYPE_COLORS.Application);
  const capType = useResolvedType(types, "BusinessCapability", "account_tree", CARD_TYPE_COLORS.BusinessCapability);
  const dataType = useResolvedType(types, "DataObject", "database", CARD_TYPE_COLORS.DataObject);
  const interfaceType = useResolvedType(types, "Interface", "sync_alt", CARD_TYPE_COLORS.Interface);
  const techType = useResolvedType(types, "ITComponent", "memory", CARD_TYPE_COLORS.ITComponent);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const pageSize = `page_size=${TOP_N}`;
        const [apps, capabilities, dataObjects, interfaces, technology, counts] = await Promise.all([
          api.get<CardListResponse>(`/cards?type=Application&${pageSize}&sort_by=data_quality&sort_dir=desc`),
          // Capabilities: fetch a wider page so the parent tree can be built
          // client-side without needing a separate query per root. 30 is
          // enough to cover the typical BRM top-two-levels; the "+N more"
          // chip covers overflow past the visible tree.
          api.get<CardListResponse>(`/cards?type=BusinessCapability&page_size=30`),
          api.get<CardListResponse>(`/cards?type=DataObject&${pageSize}`),
          api.get<CardListResponse>(`/cards?type=Interface&${pageSize}`),
          api.get<CardListResponse>(`/cards?type=ITComponent&${pageSize}`),
          api.get<CountsResponse>("/cards/counts"),
        ]);
        if (!cancelled) {
          setData({
            apps: apps.items,
            capabilities: capabilities.items,
            dataObjects: dataObjects.items,
            interfaces: interfaces.items,
            technology: technology.items,
            counts: new Map(counts.by_type.map((e) => [e.type, e.count])),
          });
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : t("applicationLayer.error.load"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [t]);

  const totalApps = data.counts.get("Application") ?? data.apps.length;
  const totalInterfaces = data.counts.get("Interface") ?? data.interfaces.length;
  const totalCapabilities = data.counts.get("BusinessCapability") ?? data.capabilities.length;
  const totalTechnology = data.counts.get("ITComponent") ?? data.technology.length;
  const totalData = data.counts.get("DataObject") ?? data.dataObjects.length;

  const appSubtypeDefs = useMemo(() => appType.type?.subtypes ?? [], [appType.type]);
  const appSubtypeLabelMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of appSubtypeDefs) map.set(s.key, subtypeLabel(s));
    return map;
  }, [appSubtypeDefs, subtypeLabel]);

  const otherLabel = t("applicationLayer.group.other");
  const appBuckets = useMemo(
    () =>
      bucketAppsBySubtype(
        data.apps,
        appSubtypeDefs,
        (s) => (s ? subtypeLabel(s) : ""),
        otherLabel,
      ),
    [data.apps, appSubtypeDefs, subtypeLabel, otherLabel],
  );

  const portfolio = useMemo(
    () => portfolioSegments(data.apps, appSubtypeLabelMap, t("applicationLayer.portfolio.unclassified")),
    [data.apps, appSubtypeLabelMap, t],
  );

  const health = useMemo(
    () =>
      healthSegments(data.apps, {
        healthy: t("applicationLayer.health.healthy"),
        atRisk: t("applicationLayer.health.atRisk"),
        retired: t("applicationLayer.health.retired"),
        unknown: t("applicationLayer.health.unknown"),
      }),
    [data.apps, t],
  );
  const healthyCount = data.apps.filter((a) => healthBucket(a) === "healthy").length;
  const atRiskCount = data.apps.filter((a) => healthBucket(a) === "atRisk").length;
  const healthScore = percent(healthyCount, data.apps.length);
  const noOwnerCount = data.apps.filter((a) => (a.stakeholders ?? []).length === 0).length;
  const lowQualityCount = data.apps.filter((a) => (a.data_quality ?? 0) < 50).length;

  const interfaceSubtypeDefs = useMemo(
    () => interfaceType.type?.subtypes ?? [],
    [interfaceType.type],
  );
  const interfaceSubtypeLabelMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of interfaceSubtypeDefs) map.set(s.key, subtypeLabel(s));
    return map;
  }, [interfaceSubtypeDefs, subtypeLabel]);

  const lifecycleBuckets = useMemo(() => {
    const buckets: Record<string, number> = {};
    for (const app of data.apps) {
      const phase = getCurrentPhase(app.lifecycle) ?? "notSet";
      buckets[phase] = (buckets[phase] ?? 0) + 1;
    }
    return buckets;
  }, [data.apps]);

  const capabilityTree = useMemo(() => buildCapabilityTree(data.capabilities), [data.capabilities]);

  const criticalApps = useMemo(
    () =>
      [...data.apps]
        .filter(isCritical)
        .sort((a, b) => (a.data_quality ?? 0) - (b.data_quality ?? 0))
        .slice(0, 6),
    [data.apps],
  );

  if (loading) return <LoadingSkeleton />;

  return (
    <Box sx={{ maxWidth: 1500, mx: "auto" }}>
      <Breadcrumbs
        aria-label={t("applicationLayer.breadcrumbs")}
        separator="›"
        sx={{ mb: 1 }}
      >
        <Link
          component={RouterLink}
          to="/view-library"
          underline="hover"
          color="inherit"
          variant="body2"
        >
          {t("reports.viewLibrary", { ns: "nav" })}
        </Link>
        <Typography variant="body2" color="text.primary" sx={{ fontWeight: 600 }}>
          {t("applicationLayer.title")}
        </Typography>
      </Breadcrumbs>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1fr) 620px" },
          gap: 2,
          alignItems: "start",
          mb: 2,
        }}
      >
        <Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Typography variant="h4" sx={{ fontWeight: 900, letterSpacing: 0 }}>
              {t("applicationLayer.title")}
            </Typography>
            <Tooltip title={t("applicationLayer.note")}>
              <IconButton size="small" aria-label={t("applicationLayer.aboutView")}>
                <MaterialSymbol icon="info" size={18} color="disabled" />
              </IconButton>
            </Tooltip>
            <Box sx={{ flex: 1 }} />
            <Tooltip title={t("applicationLayer.print")}>
              <IconButton
                size="small"
                onClick={() => window.print()}
                aria-label={t("applicationLayer.print")}
                className="report-print-hide"
              >
                <MaterialSymbol icon="print" size={20} />
              </IconButton>
            </Tooltip>
          </Box>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
            {t("applicationLayer.subtitle")}
          </Typography>
        </Box>
        <Box
          sx={{
            display: "flex",
            gap: 1.25,
            flexWrap: "wrap",
          }}
        >
          <MetricCard
            icon="apps"
            iconColor={LAYER_COLORS["Application & Data"]}
            color={LAYER_COLORS["Application & Data"]}
            label={t("applicationLayer.metric.totalApps")}
            value={totalApps}
            subtitle={
              criticalApps.length > 0 ? (
                <Box
                  component={RouterLink}
                  to="/inventory?type=Application&filter=critical"
                  sx={{
                    color: STATUS_COLORS.error,
                    textDecoration: "none",
                    fontWeight: 700,
                    "&:hover": { textDecoration: "underline" },
                  }}
                >
                  {t("applicationLayer.metric.critical", { count: criticalApps.length })} →
                </Box>
              ) : (
                t("applicationLayer.metric.critical", { count: criticalApps.length })
              )
            }
          />
          <MetricCard
            icon="groups"
            iconColor={CARD_TYPE_COLORS.Organization}
            color={CARD_TYPE_COLORS.Organization}
            label={t("applicationLayer.metric.owners")}
            value={ownerCount(data.apps)}
          />
          <MetricCard
            icon="hub"
            iconColor={CARD_TYPE_COLORS.Interface}
            color={CARD_TYPE_COLORS.Interface}
            label={t("applicationLayer.metric.integrations")}
            value={totalInterfaces}
          />
          <MetricCard
            icon="health_and_safety"
            iconColor={healthScore >= 75 ? STATUS_COLORS.success : STATUS_COLORS.warning}
            color={healthScore >= 75 ? STATUS_COLORS.success : STATUS_COLORS.warning}
            label={t("applicationLayer.metric.health")}
            value={`${healthScore}%`}
            subtitle={t("applicationLayer.metric.healthy")}
            ariaLabel={t("applicationLayer.metric.healthAria", {
              percent: healthScore,
              healthy: healthyCount,
              total: data.apps.length,
            })}
          />
        </Box>
      </Box>

      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", xl: "minmax(0, 1fr) 360px" },
          gap: 2,
        }}
      >
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
            <LayerBand
              title={t("applicationLayer.band.business")}
              subtitle={t("applicationLayer.band.businessHint")}
              color={LAYER_COLORS["Business Architecture"]}
            >
              {capabilityTree.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {t("applicationLayer.empty.capabilities")}
                </Typography>
              ) : (
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)", lg: "repeat(3, 1fr)" },
                    gap: 1,
                  }}
                >
                  {capabilityTree.slice(0, cap(6)).map((node) => (
                    <Box
                      key={node.card.id}
                      sx={{
                        display: "flex",
                        flexDirection: "column",
                        gap: 0.5,
                        p: 1,
                        border: "1px solid",
                        borderColor: withAlpha(capType.color, "22"),
                        borderRadius: 1,
                        bgcolor: "background.paper",
                      }}
                    >
                      <Box
                        component={RouterLink}
                        to={`/cards/${node.card.id}`}
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 0.75,
                          textDecoration: "none",
                          color: "text.primary",
                          "&:hover": { color: capType.color },
                        }}
                      >
                        <MaterialSymbol icon={capType.icon} size={18} color={capType.color} />
                        <Typography variant="body2" sx={{ fontWeight: 800 }} noWrap>
                          {node.card.name}
                        </Typography>
                      </Box>
                      {node.children.slice(0, 4).map((child) => (
                        <Box
                          key={child.id}
                          component={RouterLink}
                          to={`/cards/${child.id}`}
                          sx={{
                            pl: 2.5,
                            display: "flex",
                            alignItems: "center",
                            gap: 0.5,
                            textDecoration: "none",
                            color: "text.secondary",
                            "&:hover": { color: capType.color },
                          }}
                        >
                          <MaterialSymbol icon="subdirectory_arrow_right" size={14} color="disabled" />
                          <Typography variant="caption" noWrap>
                            {child.name}
                          </Typography>
                        </Box>
                      ))}
                      {node.children.length > 4 && (
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ pl: 2.5, fontStyle: "italic" }}
                        >
                          +{node.children.length - 4}
                        </Typography>
                      )}
                    </Box>
                  ))}
                </Box>
              )}
              {totalCapabilities > data.capabilities.length && (
                <Box sx={{ mt: 1 }}>
                  <MoreChip
                    count={totalCapabilities - data.capabilities.length}
                    to="/inventory?type=BusinessCapability"
                    label={t("applicationLayer.more", {
                      count: totalCapabilities - data.capabilities.length,
                    })}
                  />
                </Box>
              )}
            </LayerBand>

            <BandDivider />

            <LayerBand
              title={t("applicationLayer.band.application")}
              subtitle={t("applicationLayer.band.applicationHint")}
              color={LAYER_COLORS["Application & Data"]}
              emphasized
            >
              {appBuckets.length === 0 && (
                <Typography variant="caption" color="text.secondary">
                  {t("applicationLayer.empty.applications")}
                </Typography>
              )}
              {appBuckets.length === 1 ? (
                // Single-subtype tenants get a flat 4-column grid — a
                // one-bucket card-in-card was a whole 100%-wide bucket
                // wrapping four MiniCards, which wasted the layer's
                // horizontal real estate.
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" },
                    gap: 1,
                  }}
                >
                  {appBuckets[0].cards.slice(0, cap(8)).map((card) => (
                    <MiniCard
                      key={card.id}
                      card={card}
                      icon={appType.icon}
                      color={appType.color}
                      subtypeText={
                        card.subtype ? appSubtypeLabelMap.get(card.subtype) : undefined
                      }
                    />
                  ))}
                </Box>
              ) : (
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: {
                      xs: "1fr",
                      lg: `repeat(${Math.max(appBuckets.length, 1)}, 1fr)`,
                    },
                    gap: 1,
                  }}
                >
                  {appBuckets.map((bucket) => (
                    <Box
                      key={bucket.key}
                      sx={{
                        border: "1px solid",
                        borderColor: withAlpha(LAYER_COLORS["Application & Data"], "33"),
                        borderRadius: 1,
                        p: 1,
                        bgcolor: "rgba(255, 255, 255, 0.72)",
                      }}
                    >
                      <Typography
                        variant="subtitle2"
                        sx={{ color: LAYER_COLORS["Application & Data"], fontWeight: 850, mb: 1 }}
                      >
                        {bucket.label} · {bucket.cards.length}
                      </Typography>
                      <Box sx={{ display: "grid", gap: 1 }}>
                        {bucket.cards.slice(0, cap(4)).map((card) => (
                          <MiniCard
                            key={card.id}
                            card={card}
                            icon={appType.icon}
                            color={appType.color}
                            subtypeText={
                              card.subtype ? appSubtypeLabelMap.get(card.subtype) : undefined
                            }
                          />
                        ))}
                      </Box>
                    </Box>
                  ))}
                </Box>
              )}

              <Box
                sx={{
                  mt: 1,
                  p: 1,
                  border: "1px solid",
                  borderColor: withAlpha(interfaceType.color, "33"),
                  borderRadius: 1,
                  bgcolor: "background.paper",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 0.75,
                    mb: 0.75,
                    color: interfaceType.color,
                  }}
                >
                  <MaterialSymbol icon={interfaceType.icon} size={20} color="inherit" />
                  <Typography variant="subtitle2" sx={{ fontWeight: 850 }}>
                    {t("applicationLayer.integrationLayer")}
                  </Typography>
                </Box>
                {data.interfaces.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    {t("applicationLayer.empty.interfaces")}
                  </Typography>
                ) : (
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                    {data.interfaces.slice(0, cap(8)).map((item) => {
                      const sub = item.subtype
                        ? interfaceSubtypeLabelMap.get(item.subtype)
                        : undefined;
                      return (
                        <Tooltip key={item.id} title={sub || item.name}>
                          <Chip
                            component={RouterLink}
                            to={`/cards/${item.id}`}
                            clickable
                            size="small"
                            variant="outlined"
                            icon={
                              <Box sx={{ display: "flex", color: interfaceType.color }}>
                                <MaterialSymbol
                                  icon={interfaceType.icon}
                                  size={16}
                                  color="inherit"
                                />
                              </Box>
                            }
                            label={item.name}
                            sx={{
                              borderColor: withAlpha(interfaceType.color, "55"),
                              "&:hover": { borderColor: interfaceType.color },
                            }}
                          />
                        </Tooltip>
                      );
                    })}
                    {totalInterfaces > cap(8) && (
                      <MoreChip
                        count={totalInterfaces - cap(8)}
                        to="/inventory?type=Interface"
                        label={t("applicationLayer.more", { count: totalInterfaces - cap(8) })}
                      />
                    )}
                  </Box>
                )}
              </Box>
            </LayerBand>

            <BandDivider />

            <LayerBand
              title={t("applicationLayer.band.technology")}
              subtitle={t("applicationLayer.band.technologyHint")}
              color={LAYER_COLORS["Technical Architecture"]}
            >
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(4, 1fr)" },
                  gap: 1,
                }}
              >
                {data.technology.slice(0, cap(8)).map((card) => (
                  <MiniCard
                    key={card.id}
                    card={card}
                    icon={techType.icon}
                    color={techType.color}
                  />
                ))}
                {data.technology.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    {t("applicationLayer.empty.technology")}
                  </Typography>
                )}
              </Box>
              {totalTechnology > cap(8) && (
                <Box sx={{ mt: 1 }}>
                  <MoreChip
                    count={totalTechnology - cap(8)}
                    to="/inventory?type=ITComponent"
                    label={t("applicationLayer.more", { count: totalTechnology - cap(8) })}
                  />
                </Box>
              )}
            </LayerBand>

            <BandDivider />

            <LayerBand
              title={t("applicationLayer.band.data")}
              subtitle={t("applicationLayer.band.dataHint")}
              color={dataType.color}
            >
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(3, 1fr)" },
                  gap: 1,
                }}
              >
                {data.dataObjects.slice(0, cap(6)).map((card) => (
                  <MiniCard
                    key={card.id}
                    card={card}
                    icon={dataType.icon}
                    color={dataType.color}
                  />
                ))}
                {data.dataObjects.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    {t("applicationLayer.empty.data")}
                  </Typography>
                )}
              </Box>
              {totalData > cap(6) && (
                <Box sx={{ mt: 1 }}>
                  <MoreChip
                    count={totalData - cap(6)}
                    to="/inventory?type=DataObject"
                    label={t("applicationLayer.more", { count: totalData - cap(6) })}
                  />
                </Box>
              )}
            </LayerBand>
          </Paper>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "1fr 1.35fr 1.35fr" },
              gap: 1.5,
            }}
          >
            <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 850, mb: 1 }}>
                {t("applicationLayer.relationships.title")}
              </Typography>
              {[
                [LAYER_COLORS["Business Architecture"], "dashed", "applicationLayer.relationships.realizes"],
                [LAYER_COLORS["Application & Data"], "solid", "applicationLayer.relationships.supports"],
                [CARD_TYPE_COLORS.Interface, "solid", "applicationLayer.relationships.integrates"],
                [CARD_TYPE_COLORS.DataObject, "dashed", "applicationLayer.relationships.stores"],
              ].map(([color, style, key]) => (
                <Box key={key} sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.75 }}>
                  <Box sx={{ width: 42, borderTop: `2px ${style} ${color}` }} />
                  <Typography variant="caption" color="text.secondary">
                    {t(String(key))}
                  </Typography>
                </Box>
              ))}
            </Paper>

            <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 850 }}>
                {t("applicationLayer.lifecycle.title")}
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1.25, display: "block" }}>
                {t("applicationLayer.lifecycle.subtitle")}
              </Typography>
              <LifecycleStackedBar
                buckets={lifecycleBuckets}
                total={data.apps.length}
                labels={{
                  plan: t("lifecycle.plan", { ns: "common" }),
                  phaseIn: t("lifecycle.phaseIn", { ns: "common" }),
                  active: t("lifecycle.active", { ns: "common" }),
                  phaseOut: t("lifecycle.phaseOut", { ns: "common" }),
                  endOfLife: t("lifecycle.endOfLife", { ns: "common" }),
                  notSet: t("lifecycle.notSet", { ns: "common" }),
                }}
                emptyLabel={t("applicationLayer.lifecycle.empty")}
              />
            </Paper>

            <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 850, mb: 1 }}>
                {t("applicationLayer.actions.title")}
              </Typography>
              <Box sx={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 1 }}>
                <Button
                  component={RouterLink}
                  to="/inventory?type=Application"
                  variant="outlined"
                  sx={{ textTransform: "none" }}
                >
                  {t("applicationLayer.actions.inventory")}
                </Button>
                <Button
                  component={RouterLink}
                  to="/reports/dependencies"
                  variant="outlined"
                  sx={{ textTransform: "none" }}
                >
                  {t("applicationLayer.actions.dependencies")}
                </Button>
                <Button
                  component={RouterLink}
                  to="/reports/application-summary"
                  variant="outlined"
                  sx={{ textTransform: "none" }}
                >
                  {t("applicationLayer.actions.summary")}
                </Button>
                <Button
                  component={RouterLink}
                  to="/reports/portfolio"
                  variant="contained"
                  sx={{ textTransform: "none" }}
                >
                  {t("applicationLayer.actions.portfolio")}
                </Button>
              </Box>
            </Paper>
          </Box>
        </Box>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
          <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                gap: 2,
              }}
            >
              {/* Portfolio */}
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 850, mb: 1 }} noWrap>
                  {t("applicationLayer.portfolio.title")}
                </Typography>
                <Box sx={{ display: "flex", justifyContent: "center", mb: 1 }}>
                  <Donut
                    segments={portfolio}
                    total={data.apps.length}
                    totalLabel={t("applicationLayer.donut.total")}
                    size={104}
                    ariaLabel={portfolio
                      .map((s) => `${s.label}: ${s.value}`)
                      .join(", ")}
                  />
                </Box>
                <Box sx={{ minWidth: 0 }}>
                  {portfolio.slice(0, 3).map((segment) => (
                    <Box
                      key={segment.label}
                      sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}
                    >
                      <Box
                        sx={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          bgcolor: segment.color,
                          flexShrink: 0,
                        }}
                      />
                      <Typography variant="caption" sx={{ flex: 1, minWidth: 0 }} noWrap>
                        {segment.label}
                      </Typography>
                      <Typography variant="caption" sx={{ fontWeight: 800 }}>
                        {segment.value}
                      </Typography>
                    </Box>
                  ))}
                  {portfolio.length > 3 && (
                    <Typography variant="caption" color="text.secondary" sx={{ fontStyle: "italic" }}>
                      +{portfolio.length - 3}
                    </Typography>
                  )}
                </Box>
                <Button
                  component={RouterLink}
                  to="/reports/portfolio"
                  size="small"
                  endIcon={<MaterialSymbol icon="arrow_forward" size={16} />}
                  sx={{ mt: 0.5, textTransform: "none", pl: 0 }}
                >
                  {t("applicationLayer.portfolio.open")}
                </Button>
              </Box>

              {/* Health */}
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 850, mb: 1 }} noWrap>
                  {t("applicationLayer.health.title")}
                </Typography>
                <Box sx={{ display: "flex", justifyContent: "center", mb: 1 }}>
                  <Donut
                    segments={health}
                    total={data.apps.length}
                    totalLabel={`${healthScore}%`}
                    size={104}
                    ariaLabel={health.map((s) => `${s.label}: ${s.value}`).join(", ")}
                  />
                </Box>
                <Box sx={{ minWidth: 0 }}>
                  {health.map((segment) => (
                    <Box
                      key={segment.label}
                      sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}
                    >
                      <Box
                        sx={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          bgcolor: segment.color,
                          flexShrink: 0,
                        }}
                      />
                      <Typography variant="caption" sx={{ flex: 1, minWidth: 0 }} noWrap>
                        {segment.label}
                      </Typography>
                      <Typography variant="caption" sx={{ fontWeight: 800 }}>
                        {segment.value}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </Box>
            </Box>
          </Paper>

          <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 850, mb: 1 }}>
              {t("applicationLayer.critical.title")}
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {criticalApps.map((app) => (
                <Box key={app.id}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Typography
                      component={RouterLink}
                      to={`/cards/${app.id}`}
                      variant="body2"
                      sx={{ color: "primary.main", textDecoration: "none", fontWeight: 750, flex: 1 }}
                    >
                      {app.name}
                    </Typography>
                    <Chip
                      size="small"
                      label={criticality(app) ?? t("applicationLayer.critical.chipDefault")}
                      color="error"
                      variant="outlined"
                    />
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={Math.max(0, Math.min(100, app.data_quality ?? 0))}
                    sx={{
                      mt: 0.5,
                      height: 5,
                      borderRadius: 1,
                      bgcolor: "action.hover",
                      "& .MuiLinearProgress-bar": {
                        bgcolor: qualityColor(app.data_quality ?? 0),
                      },
                    }}
                  />
                </Box>
              ))}
              {criticalApps.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                  {t("applicationLayer.critical.empty")}
                </Typography>
              )}
            </Box>
          </Paper>

          <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 850 }}>
              {t("applicationLayer.filters.title")}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ mb: 1.25, display: "block" }}
            >
              {t("applicationLayer.filters.subtitle")}
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
              {[
                {
                  key: "critical",
                  icon: "priority_high",
                  color: CARD_TYPE_COLORS.Application,
                  count: criticalApps.length,
                  label: t("applicationLayer.filters.critical"),
                  to: "/inventory?type=Application&filter=critical",
                },
                {
                  key: "atRisk",
                  icon: "warning",
                  color: STATUS_COLORS.warning,
                  count: atRiskCount,
                  label: t("applicationLayer.filters.atRisk"),
                  to: "/inventory?type=Application&filter=atRisk",
                },
                {
                  key: "noOwner",
                  icon: "person_off",
                  color: STATUS_COLORS.neutral,
                  count: noOwnerCount,
                  label: t("applicationLayer.filters.noOwner"),
                  to: "/inventory?type=Application&filter=noOwner",
                },
                {
                  key: "lowQuality",
                  icon: "data_alert",
                  color: STATUS_COLORS.error,
                  count: lowQualityCount,
                  label: t("applicationLayer.filters.lowQuality"),
                  to: "/inventory?type=Application&filter=lowQuality",
                },
              ].map((row) => (
                <Box
                  key={row.key}
                  component={RouterLink}
                  to={row.to}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    p: 0.75,
                    borderRadius: 1,
                    textDecoration: "none",
                    color: "text.primary",
                    border: "1px solid transparent",
                    "&:hover": {
                      bgcolor: withAlpha(row.color, "0d"),
                      borderColor: withAlpha(row.color, "44"),
                    },
                  }}
                >
                  <Box
                    sx={{
                      width: 30,
                      height: 30,
                      borderRadius: 1,
                      bgcolor: withAlpha(row.color, "1a"),
                      color: row.color,
                      display: "grid",
                      placeItems: "center",
                      flexShrink: 0,
                    }}
                  >
                    <MaterialSymbol icon={row.icon} size={18} color="inherit" />
                  </Box>
                  <Typography variant="body2" sx={{ flex: 1, minWidth: 0 }} noWrap>
                    {row.label}
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{ fontWeight: 800, color: row.count > 0 ? row.color : "text.disabled" }}
                  >
                    {row.count}
                  </Typography>
                  <MaterialSymbol icon="arrow_forward" size={16} color="disabled" />
                </Box>
              ))}
            </Box>
          </Paper>
        </Box>
      </Box>

    </Box>
  );
}
