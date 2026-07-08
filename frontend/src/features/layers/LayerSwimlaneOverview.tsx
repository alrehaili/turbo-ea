/**
 * LayerSwimlaneOverview — a rich, layer-parameterised architecture overview.
 *
 * Structured after the ea-ui-mvp domain pages: a per-layer description and
 * health score card, a mini-KPI strip, a **portfolio** grid of status-coloured
 * cards, an MVP-style **lifecycle view** (lanes), per-target-layer **mapping**
 * panels ("Application to Business", …), an **integration map** of relations
 * within the layer, the architecture-layer stack with live cross-layer link
 * counts, a priority-attention list, and a full **catalog table**. Clicking
 * any card opens the component-details side drawer (LayerCardDrawer).
 * Everything is metamodel-driven, so new card types in a layer appear
 * automatically. Card "status" is derived: end-of-life or <50% data quality →
 * risk; phase-out or <75% → warning; otherwise healthy.
 *
 * Rendered under the top-level **Layers** nav tab (routes `/layers/:slug`).
 * [FORK FEATURE] — noraPlan.md (layer overviews).
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import MetricCard from "@/features/reports/MetricCard";
import LifecycleBadge, { getCurrentPhase } from "@/components/LifecycleBadge";
import LayerCardDrawer from "@/features/layers/LayerCardDrawer";
import {
  EA_LAYERS,
  ExplorerPage,
  HealthLine,
  LAYER_SLUG,
  NodePill,
  Panel,
  STATUS_COLOR,
  cardStatus,
  scoreStatus,
  statusChipSx,
  statusSurfaceSx,
  typeColor,
  useLayerName,
  type CardStatus,
  type RelCardRef,
  type RelRow,
} from "@/features/layers/shared";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useRelationLabel, useSubtypeLabel, useTypeLabel } from "@/hooks/useResolveLabel";
import { LAYER_COLORS, STATUS_COLORS } from "@/theme/tokens";
import type { Card, CardType, RelationType } from "@/types";

const LIFECYCLE_LANES = ["plan", "phaseIn", "active", "phaseOut", "endOfLife", "notSet"] as const;
const LANE_ITEMS = 6;
const ATTENTION_ITEMS = 8;
const PORTFOLIO_ITEMS = 12;
const MAPPING_ROWS = 6;
const MAPPING_CHIPS = 8;
const INTEGRATION_ROWS = 12;
const CATALOG_ROWS = 50;

interface CountsResponse {
  by_type: { type: string; count: number }[];
}

export default function LayerSwimlaneOverview({ layer }: { layer: string }) {
  const { t } = useTranslation(["reports", "common"]);
  const navigate = useNavigate();
  const { types, relationTypes } = useMetamodel();
  const typeLabel = useTypeLabel();
  const subtypeLabel = useSubtypeLabel();
  const relationLabel = useRelationLabel();
  const [cards, setCards] = useState<Card[] | null>(null);
  const [rels, setRels] = useState<RelRow[]>([]);
  const [counts, setCounts] = useState<Map<string, number>>(new Map());
  const [error, setError] = useState(false);
  const [drawerCardId, setDrawerCardId] = useState<string | null>(null);

  const typesByLayer = useMemo(() => {
    const m: Record<string, CardType[]> = {};
    for (const l of EA_LAYERS) m[l] = types.filter((ty) => ty.category === l && !ty.is_hidden);
    return m;
  }, [types]);

  const anchorTypes = typesByLayer[layer] ?? [];
  const typeByKey = useMemo(() => new Map(types.map((ty) => [ty.key, ty])), [types]);
  const relTypeByKey = useMemo(
    () => new Map(relationTypes.map((rt) => [rt.key, rt])),
    [relationTypes],
  );
  /** Card-type key → EA layer (category). */
  const layerOfType = useMemo(() => {
    const m = new Map<string, string>();
    for (const ty of types) if (ty.category) m.set(ty.key, ty.category);
    return m;
  }, [types]);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    setCards(null);
    setRels([]);
    setDrawerCardId(null);

    Promise.all(
      (typesByLayer[layer] ?? []).map((ty) =>
        api
          .get<{ items: Card[] }>(`/cards?type=${encodeURIComponent(ty.key)}&page_size=2000`)
          .then((r) => r.items)
          .catch(() => {
            setError(true);
            return [] as Card[];
          }),
      ),
    ).then((results) => {
      if (!cancelled) setCards(results.flat());
    });

    // Relations touching this layer — powers the mapping + integration panels.
    const anchorKeys = new Set((typesByLayer[layer] ?? []).map((ty) => ty.key));
    const layerRelTypes = relationTypes.filter(
      (rt: RelationType) =>
        !rt.is_hidden && (anchorKeys.has(rt.source_type_key) || anchorKeys.has(rt.target_type_key)),
    );
    Promise.all(
      layerRelTypes.map((rt) =>
        api
          .get<RelRow[]>(`/relations?type=${encodeURIComponent(rt.key)}`)
          .catch(() => [] as RelRow[]),
      ),
    ).then((results) => {
      if (!cancelled) setRels(results.flat());
    });

    api
      .get<CountsResponse>("/cards/counts")
      .then((r) => {
        if (cancelled) return;
        const m = new Map<string, number>();
        for (const row of r.by_type) m.set(row.type, row.count);
        setCounts(m);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [layer, typesByLayer, relationTypes]);

  const stats = useMemo(() => {
    const list = cards ?? [];
    const total = list.length;
    const avgQuality = total
      ? Math.round(list.reduce((s, c) => s + (c.data_quality ?? 0), 0) / total)
      : 0;
    const byStatus: Record<CardStatus, number> = { healthy: 0, warning: 0, risk: 0 };
    const lanes: Record<string, Card[]> = {};
    for (const lane of LIFECYCLE_LANES) lanes[lane] = [];
    for (const c of list) {
      byStatus[cardStatus(c)] += 1;
      lanes[getCurrentPhase(c.lifecycle) ?? "notSet"].push(c);
    }
    return { total, avgQuality, byStatus, lanes };
  }, [cards]);

  const attentionCards = useMemo(
    () =>
      [...(cards ?? [])]
        .filter((c) => cardStatus(c) !== "healthy")
        .sort((a, b) => (a.data_quality ?? 0) - (b.data_quality ?? 0))
        .slice(0, ATTENTION_ITEMS),
    [cards],
  );

  const catalogCards = useMemo(
    () => [...(cards ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
    [cards],
  );

  /** Relation-derived content: per-layer link counts, per-target-layer mapping groups, in-layer edges. */
  const relInsights = useMemo(() => {
    const linkCounts = new Map<string, number>();
    // other layer → anchor card id → { card, links }
    const groups = new Map<
      string,
      Map<string, { card: RelCardRef; links: { other: RelCardRef; verb: string }[] }>
    >();
    const inLayer: { source: RelCardRef; verb: string; target: RelCardRef }[] = [];

    for (const r of rels) {
      if (!r.source || !r.target) continue;
      const srcLayer = layerOfType.get(r.source.type);
      const tgtLayer = layerOfType.get(r.target.type);
      const rt = relTypeByKey.get(r.type);

      if (srcLayer === layer && tgtLayer === layer) {
        inLayer.push({ source: r.source, verb: rt ? relationLabel(rt) : r.type, target: r.target });
        continue;
      }

      const anchorSide = srcLayer === layer ? r.source : tgtLayer === layer ? r.target : null;
      if (!anchorSide) continue;
      const otherSide = srcLayer === layer ? r.target : r.source;
      const otherLayer = (srcLayer === layer ? tgtLayer : srcLayer) ?? "";
      linkCounts.set(otherLayer, (linkCounts.get(otherLayer) ?? 0) + 1);

      let group = groups.get(otherLayer);
      if (!group) {
        group = new Map();
        groups.set(otherLayer, group);
      }
      let row = group.get(anchorSide.id);
      if (!row) {
        row = { card: anchorSide, links: [] };
        group.set(anchorSide.id, row);
      }
      row.links.push({
        other: otherSide,
        verb: rt ? relationLabel(rt, anchorSide === r.target) : r.type,
      });
    }

    const mappingGroups = [...groups.entries()]
      .map(([otherLayer, byCard]) => ({
        otherLayer,
        rows: [...byCard.values()].sort((a, b) => b.links.length - a.links.length),
        total: linkCounts.get(otherLayer) ?? 0,
      }))
      .sort((a, b) => b.total - a.total);

    return { linkCounts, mappingGroups, inLayer };
  }, [rels, layer, layerOfType, relTypeByKey, relationLabel]);

  const accent = (LAYER_COLORS as Record<string, string>)[layer] ?? STATUS_COLORS.info;
  const layerName = useLayerName();
  const healthStatus = scoreStatus(stats.avgQuality);
  const openDrawer = (id: string) => setDrawerCardId(id);

  if (cards === null) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <ExplorerPage>
      {/* Page intro — title + layer health score card */}
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Box sx={{ flex: 1, minWidth: 260 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 0.5 }}>
            <Box sx={{ width: 8, height: 32, borderRadius: 1, bgcolor: accent }} />
            <Typography variant="h5" fontWeight={800} sx={{ flex: 1 }}>
              {t("layerOverview.title", { layer: layerName(layer) })}
            </Typography>
            <Tooltip title={t("layerSwimlane.print")}>
              <IconButton
                size="small"
                onClick={() => window.print()}
                aria-label={t("layerSwimlane.print")}
                className="no-print"
              >
                <MaterialSymbol icon="print" size={20} />
              </IconButton>
            </Tooltip>
          </Box>
          <Typography variant="body2" color="text.secondary">
            {t(`layerOverview.about.${LAYER_SLUG[layer] ?? "business"}`)}
          </Typography>
        </Box>
        {stats.total > 0 && (
          <Paper
            variant="outlined"
            sx={{
              px: 2.5,
              py: 1.25,
              textAlign: "center",
              borderColor: STATUS_COLOR[healthStatus],
              borderWidth: 2,
              borderRadius: 2.5,
              minWidth: 140,
            }}
          >
            <Typography variant="caption" color="text.secondary" display="block">
              {t("layerOverview.health")}
            </Typography>
            <Typography variant="h4" fontWeight={800} sx={{ color: STATUS_COLOR[healthStatus] }}>
              {stats.avgQuality}%
            </Typography>
            <Typography
              variant="caption"
              sx={{ color: STATUS_COLOR[healthStatus], fontWeight: 700 }}
            >
              {t(`layerOverview.status.${healthStatus}`)}
            </Typography>
          </Paper>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {t("layerOverview.error")}
        </Alert>
      )}

      {stats.total === 0 ? (
        <Alert severity="info">{t("layerOverview.empty")}</Alert>
      ) : (
        <>
          {/* Mini-KPI strip */}
          <Box sx={{ display: "flex", gap: 1.25, flexWrap: "wrap", mb: 2 }}>
            <MetricCard
              icon="dashboard"
              iconColor={accent}
              color={accent}
              label={t("layerOverview.metric.total")}
              value={stats.total}
            />
            <MetricCard
              icon="category"
              iconColor={accent}
              color={accent}
              label={t("layerOverview.metric.types")}
              value={anchorTypes.length}
            />
            <MetricCard
              icon="verified"
              iconColor={STATUS_COLORS.info}
              color={STATUS_COLORS.info}
              label={t("layerOverview.metric.avgQuality")}
              value={`${stats.avgQuality}%`}
            />
            <MetricCard
              icon="check_circle"
              iconColor={STATUS_COLORS.success}
              color={STATUS_COLORS.success}
              label={t("layerOverview.status.healthy")}
              value={stats.byStatus.healthy}
            />
            <MetricCard
              icon="warning"
              iconColor={STATUS_COLORS.warning}
              color={STATUS_COLORS.warning}
              label={t("layerOverview.status.warning")}
              value={stats.byStatus.warning}
            />
            <MetricCard
              icon="report"
              iconColor={STATUS_COLORS.error}
              color={STATUS_COLORS.error}
              label={t("layerOverview.status.risk")}
              value={stats.byStatus.risk}
            />
          </Box>

          {/* Row A — portfolio | lifecycle view */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "repeat(2, minmax(0, 1fr))" },
              gap: 2,
              mb: 2,
            }}
          >
            <Panel
              eyebrow={t("layerOverview.panel.portfolioEyebrow")}
              title={t("layerOverview.panel.portfolio", { layer: layerName(layer) })}
              count={t("layerOverview.items", { count: catalogCards.length })}
            >
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
                  gap: 1,
                }}
              >
                {catalogCards.slice(0, PORTFOLIO_ITEMS).map((c) => {
                  const status = cardStatus(c);
                  const color = STATUS_COLOR[status];
                  const ty = typeByKey.get(c.type);
                  const sub = ty?.subtypes?.find((s) => s.key === c.subtype);
                  return (
                    <ButtonBase
                      key={c.id}
                      onClick={() => openDrawer(c.id)}
                      sx={[
                        {
                          display: "block",
                          textAlign: "start",
                          border: "1px solid",
                          borderInlineStart: `4px solid ${color}`,
                          borderRadius: 2,
                          p: 1.25,
                          minWidth: 0,
                          "&:hover": { borderColor: color },
                        },
                        statusSurfaceSx(status),
                      ]}
                    >
                      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                        <Typography variant="body2" fontWeight={700} noWrap sx={{ flex: 1 }}>
                          {c.name}
                        </Typography>
                        <LifecycleBadge lifecycle={c.lifecycle} />
                      </Box>
                      <Typography variant="caption" color="text.secondary" noWrap display="block">
                        {sub ? subtypeLabel(sub) : ty ? typeLabel(ty) : c.type}
                      </Typography>
                      {c.description && (
                        <Typography
                          variant="caption"
                          display="block"
                          sx={{
                            mt: 0.5,
                            display: "-webkit-box",
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: "vertical",
                            overflow: "hidden",
                          }}
                        >
                          {c.description}
                        </Typography>
                      )}
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        display="block"
                        sx={{ mt: 0.5 }}
                      >
                        {ty ? typeLabel(ty) : c.type} • {Math.round(c.data_quality ?? 0)}%
                      </Typography>
                    </ButtonBase>
                  );
                })}
              </Box>
              {catalogCards.length > PORTFOLIO_ITEMS && (
                <Box sx={{ mt: 1 }}>
                  <Link
                    component="button"
                    underline="hover"
                    variant="caption"
                    onClick={() => navigate("/inventory")}
                  >
                    {t("layerSwimlane.more", { count: catalogCards.length - PORTFOLIO_ITEMS })}
                  </Link>
                </Box>
              )}
            </Panel>

            <Panel
              eyebrow={t("layerOverview.panel.lifecycleEyebrow")}
              title={t("layerOverview.panel.lifecycleLanes")}
            >
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "repeat(2, minmax(0, 1fr))",
                    md: "repeat(3, minmax(0, 1fr))",
                  },
                  gap: 1,
                }}
              >
                {LIFECYCLE_LANES.map((lane) => {
                  const laneCards = stats.lanes[lane];
                  return (
                    <Box
                      key={lane}
                      sx={{
                        border: "1px dashed",
                        borderColor: "divider",
                        borderRadius: 1,
                        p: 1,
                        minWidth: 0,
                      }}
                    >
                      <Typography variant="caption" fontWeight={800} display="block" mb={0.75}>
                        {t(`layerOverview.phase.${lane}`)} ({laneCards.length})
                      </Typography>
                      {laneCards.length === 0 ? (
                        <Typography variant="caption" color="text.secondary">
                          {t("layerOverview.laneEmpty")}
                        </Typography>
                      ) : (
                        <Stack spacing={0.5}>
                          {laneCards.slice(0, LANE_ITEMS).map((c) => {
                            const ty = typeByKey.get(c.type);
                            return (
                              <ButtonBase
                                key={c.id}
                                onClick={() => openDrawer(c.id)}
                                sx={{
                                  display: "block",
                                  width: "100%",
                                  textAlign: "start",
                                  bgcolor: "action.hover",
                                  borderRadius: 1,
                                  px: 1,
                                  py: 0.5,
                                  minWidth: 0,
                                  "&:hover": { bgcolor: "action.selected" },
                                }}
                              >
                                <Typography variant="caption" fontWeight={700} noWrap display="block">
                                  {c.name}
                                </Typography>
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                  noWrap
                                  display="block"
                                >
                                  {ty ? typeLabel(ty) : c.type}
                                </Typography>
                              </ButtonBase>
                            );
                          })}
                          {laneCards.length > LANE_ITEMS && (
                            <Typography variant="caption" color="text.secondary">
                              {t("layerSwimlane.more", { count: laneCards.length - LANE_ITEMS })}
                            </Typography>
                          )}
                        </Stack>
                      )}
                    </Box>
                  );
                })}
              </Box>
            </Panel>
          </Box>

          {/* Row B — per-layer mapping | integration map */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "repeat(2, minmax(0, 1fr))" },
              gap: 2,
              mb: 2,
            }}
          >
            <Panel
              eyebrow={t("layerOverview.panel.mappingEyebrow")}
              title={t("layerOverview.panel.mapping")}
              count={t("layerOverview.links", {
                count: [...relInsights.linkCounts.values()].reduce((s, n) => s + n, 0),
              })}
            >
              {relInsights.mappingGroups.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {t("layerOverview.mappingEmpty")}
                </Typography>
              ) : (
                <Stack spacing={1.5}>
                  {relInsights.mappingGroups.map((group) => {
                    const gColor =
                      (LAYER_COLORS as Record<string, string>)[group.otherLayer] ??
                      STATUS_COLORS.neutral;
                    return (
                      <Box key={group.otherLayer}>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.75 }}>
                          <Box
                            sx={{ width: 10, height: 10, borderRadius: "2px", bgcolor: gColor }}
                          />
                          <Typography variant="subtitle2" fontWeight={800} sx={{ flex: 1 }}>
                            {t("layerOverview.mappingTo", {
                              anchor: layerName(layer),
                              other: layerName(group.otherLayer),
                            })}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {t("layerOverview.links", { count: group.total })}
                          </Typography>
                        </Box>
                        <Stack spacing={0.75}>
                          {group.rows.slice(0, MAPPING_ROWS).map((row) => (
                            <Box
                              key={row.card.id}
                              sx={{
                                display: "flex",
                                alignItems: "flex-start",
                                gap: 1,
                                border: "1px solid",
                                borderColor: "divider",
                                borderRadius: 1,
                                px: 1.25,
                                py: 0.75,
                              }}
                            >
                              <Box sx={{ width: 170, flexShrink: 0, minWidth: 0 }}>
                                <Link
                                  component="button"
                                  underline="hover"
                                  variant="body2"
                                  onClick={() => openDrawer(row.card.id)}
                                  sx={{
                                    fontWeight: 700,
                                    display: "block",
                                    maxWidth: "100%",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    whiteSpace: "nowrap",
                                    textAlign: "start",
                                  }}
                                >
                                  {row.card.name}
                                </Link>
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                  noWrap
                                  display="block"
                                >
                                  {(() => {
                                    const ty = typeByKey.get(row.card.type);
                                    return ty ? typeLabel(ty) : row.card.type;
                                  })()}
                                </Typography>
                              </Box>
                              <Box
                                sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, minWidth: 0 }}
                              >
                                {row.links.slice(0, MAPPING_CHIPS).map((lnk, i) => (
                                  <Tooltip key={`${lnk.other.id}-${i}`} title={lnk.verb}>
                                    <Chip
                                      clickable
                                      onClick={() => openDrawer(lnk.other.id)}
                                      size="small"
                                      label={lnk.other.name}
                                      sx={{
                                        maxWidth: 170,
                                        height: 22,
                                        border: `1px solid ${gColor}`,
                                        bgcolor: `${gColor}14`,
                                      }}
                                    />
                                  </Tooltip>
                                ))}
                                {row.links.length > MAPPING_CHIPS && (
                                  <Chip
                                    size="small"
                                    label={t("layerSwimlane.more", {
                                      count: row.links.length - MAPPING_CHIPS,
                                    })}
                                    sx={{ height: 22 }}
                                  />
                                )}
                              </Box>
                            </Box>
                          ))}
                          {group.rows.length > MAPPING_ROWS && (
                            <Typography variant="caption" color="text.secondary">
                              {t("layerSwimlane.more", {
                                count: group.rows.length - MAPPING_ROWS,
                              })}
                            </Typography>
                          )}
                        </Stack>
                      </Box>
                    );
                  })}
                </Stack>
              )}
            </Panel>

            <Panel
              eyebrow={t("layerOverview.panel.integrationEyebrow")}
              title={t("layerOverview.panel.integration")}
              count={t("layerOverview.links", { count: relInsights.inLayer.length })}
            >
              {relInsights.inLayer.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {t("layerOverview.integrationEmpty")}
                </Typography>
              ) : (
                <Stack spacing={0.75}>
                  {relInsights.inLayer.slice(0, INTEGRATION_ROWS).map((edge, i) => (
                    <Box
                      key={`${edge.source.id}-${edge.target.id}-${i}`}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        minWidth: 0,
                      }}
                    >
                      <NodePill name={edge.source.name} onClick={() => openDrawer(edge.source.id)} />
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ flexShrink: 0, whiteSpace: "nowrap" }}
                      >
                        {edge.verb} →
                      </Typography>
                      <NodePill name={edge.target.name} onClick={() => openDrawer(edge.target.id)} />
                    </Box>
                  ))}
                  {relInsights.inLayer.length > INTEGRATION_ROWS && (
                    <Typography variant="caption" color="text.secondary">
                      {t("layerSwimlane.more", {
                        count: relInsights.inLayer.length - INTEGRATION_ROWS,
                      })}
                    </Typography>
                  )}
                </Stack>
              )}
            </Panel>
          </Box>

          {/* Row C — layer stack + attention list */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "repeat(2, minmax(0, 1fr))" },
              gap: 2,
              mb: 2,
            }}
          >
            <Panel
              eyebrow={t("layerOverview.panel.stackEyebrow")}
              title={t("layerOverview.panel.stack")}
            >
              <Stack spacing={0.75}>
                {EA_LAYERS.map((l) => {
                  const lColor =
                    (LAYER_COLORS as Record<string, string>)[l] ?? STATUS_COLORS.neutral;
                  const lCount = (typesByLayer[l] ?? []).reduce(
                    (s, ty) => s + (counts.get(ty.key) ?? 0),
                    0,
                  );
                  const current = l === layer;
                  return (
                    <ButtonBase
                      key={l}
                      onClick={() => navigate(`/layers/${LAYER_SLUG[l]}`)}
                      disabled={current}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1,
                        width: "100%",
                        textAlign: "start",
                        border: "1px solid",
                        borderColor: current ? lColor : "divider",
                        borderInlineStart: `4px solid ${lColor}`,
                        borderRadius: 1,
                        px: 1.5,
                        py: 1,
                        bgcolor: current ? `${lColor}14` : "background.paper",
                        "&:hover": { bgcolor: current ? `${lColor}14` : "action.hover" },
                      }}
                    >
                      <Typography variant="body2" fontWeight={800} sx={{ color: lColor, flex: 1 }}>
                        {layerName(l)}
                      </Typography>
                      {current && (
                        <Chip
                          size="small"
                          label={t("layerSwimlane.thisLayer")}
                          sx={{ bgcolor: lColor, color: "#fff", height: 20, fontSize: "0.68rem" }}
                        />
                      )}
                      {!current && (relInsights.linkCounts.get(l) ?? 0) > 0 && (
                        <Chip
                          size="small"
                          variant="outlined"
                          label={t("layerOverview.links", {
                            count: relInsights.linkCounts.get(l) ?? 0,
                          })}
                          sx={{ height: 20, fontSize: "0.68rem" }}
                        />
                      )}
                      <Typography variant="caption" color="text.secondary">
                        {t("layerSwimlane.cards", { count: lCount })}
                      </Typography>
                    </ButtonBase>
                  );
                })}
              </Stack>
            </Panel>

            <Panel
              eyebrow={t("layerOverview.panel.attentionEyebrow")}
              title={t("layerOverview.attention")}
              count={t("layerOverview.items", { count: attentionCards.length })}
            >
              {attentionCards.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {t("layerOverview.attentionEmpty")}
                </Typography>
              ) : (
                <Stack spacing={0.75}>
                  {attentionCards.map((c) => {
                    const status = cardStatus(c);
                    const ty = typeByKey.get(c.type);
                    return (
                      <ButtonBase
                        key={c.id}
                        onClick={() => openDrawer(c.id)}
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          gap: 1,
                          width: "100%",
                          textAlign: "start",
                          border: "1px solid",
                          borderColor: "divider",
                          borderRadius: 1,
                          px: 1.25,
                          py: 0.75,
                          "&:hover": { bgcolor: "action.hover" },
                        }}
                      >
                        <Box
                          sx={{
                            width: 10,
                            height: 10,
                            borderRadius: "50%",
                            bgcolor: STATUS_COLOR[status],
                            flexShrink: 0,
                          }}
                        />
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography variant="body2" fontWeight={700} noWrap>
                            {c.name}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            noWrap
                            display="block"
                          >
                            {ty ? typeLabel(ty) : c.type}
                          </Typography>
                        </Box>
                        <Chip
                          size="small"
                          label={`${Math.round(c.data_quality ?? 0)}%`}
                          sx={[{ minWidth: 52, height: 22 }, statusChipSx(status)]}
                        />
                      </ButtonBase>
                    );
                  })}
                </Stack>
              )}
            </Panel>
          </Box>

          {/* Catalog table */}
          <Panel
            eyebrow={t("layerOverview.panel.catalogEyebrow")}
            title={t("layerOverview.panel.catalog", { layer: layerName(layer) })}
            count={t("layerOverview.items", { count: catalogCards.length })}
          >
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("layerOverview.colCard")}</TableCell>
                    <TableCell>{t("layerOverview.colArea")}</TableCell>
                    <TableCell>{t("layerOverview.colType")}</TableCell>
                    <TableCell>{t("layerOverview.colStatus")}</TableCell>
                    <TableCell>{t("layerOverview.colLifecycle")}</TableCell>
                    <TableCell sx={{ minWidth: 160 }}>{t("layerOverview.colQuality")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {catalogCards.slice(0, CATALOG_ROWS).map((c) => {
                    const ty = typeByKey.get(c.type);
                    const sub = ty?.subtypes?.find((s) => s.key === c.subtype);
                    const status = cardStatus(c);
                    const q = Math.round(c.data_quality ?? 0);
                    return (
                      <TableRow
                        key={c.id}
                        hover
                        onClick={() => openDrawer(c.id)}
                        sx={{ cursor: "pointer" }}
                      >
                        <TableCell sx={{ maxWidth: 340 }}>
                          <Typography variant="body2" fontWeight={700} noWrap>
                            {c.name}
                          </Typography>
                          {c.description && (
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              noWrap
                              display="block"
                            >
                              {c.description}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          {sub ? (
                            <Chip size="small" variant="outlined" label={subtypeLabel(sub)} />
                          ) : null}
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                            {ty && (
                              <MaterialSymbol icon={ty.icon} size={16} color={typeColor(ty)} />
                            )}
                            <Typography variant="body2" noWrap>
                              {ty ? typeLabel(ty) : c.type}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={t(`layerOverview.status.${status}`)}
                            sx={[{ height: 22 }, statusChipSx(status)]}
                          />
                        </TableCell>
                        <TableCell>
                          <LifecycleBadge lifecycle={c.lifecycle} />
                        </TableCell>
                        <TableCell>
                          <HealthLine status={status} value={q} />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Box>
            {catalogCards.length > CATALOG_ROWS && (
              <Box sx={{ mt: 1, textAlign: "center" }}>
                <Link
                  component="button"
                  underline="hover"
                  variant="body2"
                  onClick={() => navigate("/inventory")}
                >
                  {t("layerOverview.viewAllInventory", {
                    count: catalogCards.length - CATALOG_ROWS,
                  })}
                </Link>
              </Box>
            )}
          </Panel>
        </>
      )}

      <LayerCardDrawer
        cardId={drawerCardId}
        layerName={layerName}
        onClose={() => setDrawerCardId(null)}
        onOpenCard={openDrawer}
      />
    </ExplorerPage>
  );
}
