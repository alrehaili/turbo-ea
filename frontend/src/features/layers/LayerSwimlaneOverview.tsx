/**
 * LayerSwimlaneOverview — a rich, layer-parameterised architecture overview.
 *
 * Generalises the former bespoke Application Layer Overview so **every** EA
 * layer gets the same swim-lane treatment: the six NORA 2.0 layers render as
 * stacked bands (Business → Beneficiary Experience → Application → Data →
 * Technology → Security), with the *anchor* layer emphasised. Metric tiles, lifecycle + data-quality distributions and the
 * attention list are computed on the anchor layer's cards. Everything is
 * metamodel-driven, so new card types in a layer appear automatically.
 *
 * Rendered under the top-level **Layers** nav tab (routes `/layers/:slug`).
 * [FORK FEATURE] — noraPlan.md (layer overviews).
 */
import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
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
import { getCurrentPhase } from "@/components/LifecycleBadge";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useTypeLabel } from "@/hooks/useResolveLabel";
import { CARD_TYPE_COLORS, DATA_QUALITY_COLORS, LAYER_COLORS, STATUS_COLORS } from "@/theme/tokens";
import type { Card, CardType } from "@/types";

/** The six NORA 2.0 EA layers, top-to-bottom — the swim-lane band order. */
const EA_LAYERS = [
  "Business",
  "Beneficiary Experience",
  "Application",
  "Data",
  "Technology",
  "Security",
] as const;

/** Layer `category` → url slug / i18n key. */
export const LAYER_SLUG: Record<string, string> = {
  Business: "business",
  "Beneficiary Experience": "beneficiary",
  Application: "application",
  Data: "data",
  Technology: "technology",
  Security: "security",
};

const LIFECYCLE_PHASE_COLORS: Record<string, string> = {
  plan: STATUS_COLORS.neutral,
  phaseIn: STATUS_COLORS.info,
  active: STATUS_COLORS.success,
  phaseOut: STATUS_COLORS.warning,
  endOfLife: STATUS_COLORS.error,
  notSet: "#cbd5e1",
};
const LIFECYCLE_PHASES = ["plan", "phaseIn", "active", "phaseOut", "endOfLife", "notSet"] as const;

const DQ_TIERS = ["0-25", "25-50", "50-75", "75-100"] as const;
const SAMPLE_CARDS = 8;

interface CountsResponse {
  by_type: { type: string; count: number }[];
}

function dqTier(q: number): (typeof DQ_TIERS)[number] {
  if (q < 25) return "0-25";
  if (q < 50) return "25-50";
  if (q < 75) return "50-75";
  return "75-100";
}

function typeColor(ty: CardType): string {
  return ty.color || (CARD_TYPE_COLORS as Record<string, string>)[ty.key] || "#78909c";
}

export default function LayerSwimlaneOverview({ layer }: { layer: string }) {
  const { t } = useTranslation(["reports", "common"]);
  const { types } = useMetamodel();
  const typeLabel = useTypeLabel();
  const [cardsByLayer, setCardsByLayer] = useState<Record<string, Card[]> | null>(null);
  const [counts, setCounts] = useState<Map<string, number>>(new Map());
  const [error, setError] = useState(false);

  const typesByLayer = useMemo(() => {
    const m: Record<string, CardType[]> = {};
    for (const l of EA_LAYERS) m[l] = types.filter((ty) => ty.category === l && !ty.is_hidden);
    return m;
  }, [types]);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    setCardsByLayer(null);
    const anchorTypes = typesByLayer[layer] ?? [];
    const otherTypes = EA_LAYERS.filter((l) => l !== layer).flatMap((l) => typesByLayer[l] ?? []);

    Promise.all([
      // Anchor layer — full pages for accurate stats + attention list.
      ...anchorTypes.map((ty) =>
        api
          .get<{ items: Card[] }>(`/cards?type=${encodeURIComponent(ty.key)}&page_size=2000`)
          .then((r) => ({ cat: layer, cards: r.items }))
          .catch(() => ({ cat: layer, cards: [] as Card[] })),
      ),
      // Other layers — a sample per type for the band context.
      ...otherTypes.map((ty) =>
        api
          .get<{ items: Card[] }>(`/cards?type=${encodeURIComponent(ty.key)}&page_size=${SAMPLE_CARDS}`)
          .then((r) => ({ cat: ty.category ?? "", cards: r.items }))
          .catch(() => ({ cat: ty.category ?? "", cards: [] as Card[] })),
      ),
    ])
      .then((results) => {
        if (cancelled) return;
        const grouped: Record<string, Card[]> = {};
        for (const l of EA_LAYERS) grouped[l] = [];
        for (const r of results) (grouped[r.cat] ??= []).push(...r.cards);
        setCardsByLayer(grouped);
      })
      .catch(() => {
        if (!cancelled) {
          setError(true);
          setCardsByLayer({});
        }
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
  }, [layer, typesByLayer]);

  const anchorCards = cardsByLayer?.[layer] ?? [];

  const stats = useMemo(() => {
    const list = anchorCards;
    const total = list.length;
    const avgQuality = total
      ? Math.round(list.reduce((s, c) => s + (c.data_quality ?? 0), 0) / total)
      : 0;
    const approved = list.filter((c) => c.approval_status === "APPROVED").length;
    const phases: Record<string, number> = {};
    const dq: Record<string, number> = {};
    let atRisk = 0;
    let attention = 0;
    for (const c of list) {
      const phase = getCurrentPhase(c.lifecycle) ?? "notSet";
      phases[phase] = (phases[phase] ?? 0) + 1;
      if (phase === "phaseOut" || phase === "endOfLife") atRisk += 1;
      const q = c.data_quality ?? 0;
      dq[dqTier(q)] = (dq[dqTier(q)] ?? 0) + 1;
      if (q < 50) attention += 1;
    }
    return { total, avgQuality, approved, phases, dq, atRisk, attention };
  }, [anchorCards]);

  const attentionCards = useMemo(
    () => [...anchorCards].sort((a, b) => (a.data_quality ?? 0) - (b.data_quality ?? 0)).slice(0, 12),
    [anchorCards],
  );

  const accent = (LAYER_COLORS as Record<string, string>)[layer] ?? STATUS_COLORS.info;
  const layerName = (cat: string) => {
    const slug = LAYER_SLUG[cat];
    return slug ? t(`layerSwimlane.layerName.${slug}`) : cat;
  };

  if (cardsByLayer === null) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, maxWidth: 1500, mx: "auto" }}>
      {/* Header */}
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
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("layerOverview.subtitle")}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {t("layerOverview.error")}
        </Alert>
      )}

      {stats.total === 0 ? (
        <Alert severity="info">{t("layerOverview.empty")}</Alert>
      ) : (
        <>
          {/* Metric tiles (anchor layer) */}
          <Box sx={{ display: "flex", gap: 1.25, flexWrap: "wrap", mb: 2 }}>
            <MetricCard
              icon="dashboard"
              iconColor={accent}
              color={accent}
              label={t("layerOverview.metric.total")}
              value={stats.total}
            />
            <MetricCard
              icon="verified"
              iconColor={STATUS_COLORS.info}
              color={STATUS_COLORS.info}
              label={t("layerOverview.metric.avgQuality")}
              value={`${stats.avgQuality}%`}
            />
            <MetricCard
              icon="task_alt"
              iconColor={STATUS_COLORS.success}
              color={STATUS_COLORS.success}
              label={t("layerOverview.metric.approved")}
              value={`${stats.total ? Math.round((stats.approved / stats.total) * 100) : 0}%`}
            />
            <MetricCard
              icon="warning"
              iconColor={stats.atRisk ? STATUS_COLORS.warning : STATUS_COLORS.neutral}
              color={stats.atRisk ? STATUS_COLORS.warning : STATUS_COLORS.neutral}
              label={t("layerOverview.metric.atRisk")}
              value={stats.atRisk}
            />
          </Box>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) 340px" },
              gap: 2,
            }}
          >
            {/* Swim-lane of the four EA layers */}
            <Box>
              <Typography variant="subtitle1" fontWeight={700} mb={1}>
                {t("layerSwimlane.swimlane")}
              </Typography>
              <Stack spacing={1.25}>
                {EA_LAYERS.map((l) => (
                  <LayerBand
                    key={l}
                    title={layerName(l)}
                    color={(LAYER_COLORS as Record<string, string>)[l] ?? STATUS_COLORS.neutral}
                    emphasized={l === layer}
                    thisLayerLabel={t("layerSwimlane.thisLayer")}
                    emptyLabel={t("layerSwimlane.emptyBand")}
                    moreLabel={(n: number) => t("layerSwimlane.more", { count: n })}
                    cardsLabel={(n: number) => t("layerSwimlane.cards", { count: n })}
                    layerTypes={typesByLayer[l] ?? []}
                    cards={cardsByLayer[l] ?? []}
                    counts={counts}
                    typeLabel={typeLabel}
                  />
                ))}
              </Stack>
            </Box>

            {/* Right rail — lifecycle, data quality, attention */}
            <Stack spacing={1.5}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle1" fontWeight={700} mb={1}>
                  {t("layerOverview.lifecycle")}
                </Typography>
                <SegmentBar
                  segments={LIFECYCLE_PHASES.map((p) => ({
                    label: t(`layerOverview.phase.${p}`),
                    value: stats.phases[p] ?? 0,
                    color: LIFECYCLE_PHASE_COLORS[p],
                  }))}
                  total={stats.total}
                />
                <Typography variant="subtitle1" fontWeight={700} mt={2} mb={1}>
                  {t("layerOverview.dataQuality")}
                </Typography>
                <SegmentBar
                  segments={DQ_TIERS.map((tier) => ({
                    label: `${tier}%`,
                    value: stats.dq[tier] ?? 0,
                    color: DATA_QUALITY_COLORS[tier],
                  }))}
                  total={stats.total}
                />
              </Paper>

              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle1" fontWeight={700} mb={1}>
                  {t("layerOverview.attention")} ({stats.attention})
                </Typography>
                {attentionCards.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    {t("layerOverview.attentionEmpty")}
                  </Typography>
                ) : (
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>{t("layerOverview.colCard")}</TableCell>
                        <TableCell align="right">{t("layerOverview.colQuality")}</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {attentionCards.map((c) => {
                        const q = Math.round(c.data_quality ?? 0);
                        return (
                          <TableRow key={c.id} hover>
                            <TableCell>
                              <Link
                                component={RouterLink}
                                to={`/cards/${c.id}`}
                                underline="hover"
                              >
                                {c.name}
                              </Link>
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                size="small"
                                label={`${q}%`}
                                sx={{
                                  bgcolor: DATA_QUALITY_COLORS[dqTier(q)],
                                  color: "#fff",
                                  minWidth: 52,
                                }}
                              />
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                )}
              </Paper>
            </Stack>
          </Box>
        </>
      )}
    </Box>
  );
}

function LayerBand({
  title,
  color,
  emphasized,
  thisLayerLabel,
  emptyLabel,
  moreLabel,
  cardsLabel,
  layerTypes,
  cards,
  counts,
  typeLabel,
}: {
  title: string;
  color: string;
  emphasized?: boolean;
  thisLayerLabel: string;
  emptyLabel: string;
  moreLabel: (n: number) => string;
  cardsLabel: (n: number) => string;
  layerTypes: CardType[];
  cards: Card[];
  counts: Map<string, number>;
  typeLabel: (ty: CardType) => string;
}) {
  const byType = new Map<string, Card[]>();
  for (const c of cards) {
    if (!byType.has(c.type)) byType.set(c.type, []);
    byType.get(c.type)!.push(c);
  }
  const totalCount = layerTypes.reduce(
    (s, ty) => s + (counts.get(ty.key) ?? byType.get(ty.key)?.length ?? 0),
    0,
  );

  return (
    <Box
      sx={{
        border: "1px solid",
        borderColor: emphasized ? color : "divider",
        borderLeft: `4px solid ${color}`,
        borderRadius: 1.5,
        p: 1.5,
        bgcolor: emphasized ? `${color}0d` : "background.paper",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
        <Typography variant="subtitle2" fontWeight={800} sx={{ color }}>
          {title}
        </Typography>
        {emphasized && (
          <Chip
            size="small"
            label={thisLayerLabel}
            sx={{ bgcolor: color, color: "#fff", height: 20, fontSize: "0.68rem" }}
          />
        )}
        <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }}>
          {cardsLabel(totalCount)}
        </Typography>
      </Box>

      {layerTypes.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          {emptyLabel}
        </Typography>
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              sm: "repeat(2, minmax(0, 1fr))",
              md: "repeat(3, minmax(0, 1fr))",
            },
            gap: 1,
          }}
        >
          {layerTypes
            .map((ty) => ({ ty, count: counts.get(ty.key) ?? byType.get(ty.key)?.length ?? 0 }))
            .sort((a, b) => b.count - a.count)
            .map(({ ty, count }) => {
              const sample = byType.get(ty.key) ?? [];
              return (
                <Box
                  key={ty.key}
                  sx={{
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 1,
                    p: 1,
                    minWidth: 0,
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}>
                    <Box
                      sx={{
                        width: 10,
                        height: 10,
                        borderRadius: "2px",
                        bgcolor: typeColor(ty),
                        flexShrink: 0,
                      }}
                    />
                    <Link
                      component={RouterLink}
                      to={`/inventory?type=${ty.key}`}
                      underline="hover"
                      variant="body2"
                      sx={{ fontWeight: 700, minWidth: 0 }}
                      noWrap
                    >
                      {typeLabel(ty)}
                    </Link>
                    <Typography variant="body2" fontWeight={800} sx={{ ml: "auto" }}>
                      {count}
                    </Typography>
                  </Box>
                  {emphasized && sample.length > 0 && (
                    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                      {sample.slice(0, SAMPLE_CARDS).map((c) => (
                        <Chip
                          key={c.id}
                          component={RouterLink}
                          to={`/cards/${c.id}`}
                          clickable
                          size="small"
                          label={c.name}
                          variant="outlined"
                          sx={{ maxWidth: 160, height: 22 }}
                        />
                      ))}
                      {count > SAMPLE_CARDS && (
                        <Chip
                          component={RouterLink}
                          to={`/inventory?type=${ty.key}`}
                          clickable
                          size="small"
                          label={moreLabel(count - SAMPLE_CARDS)}
                          sx={{ height: 22 }}
                        />
                      )}
                    </Box>
                  )}
                </Box>
              );
            })}
        </Box>
      )}
    </Box>
  );
}

function SegmentBar({
  segments,
  total,
}: {
  segments: { label: string; value: number; color: string }[];
  total: number;
}) {
  const shown = segments.filter((s) => s.value > 0);
  return (
    <Box>
      <Box sx={{ display: "flex", height: 14, borderRadius: 1, overflow: "hidden", mb: 0.75 }}>
        {shown.map((s) => (
          <Box
            key={s.label}
            sx={{ width: `${(s.value / (total || 1)) * 100}%`, bgcolor: s.color }}
            title={`${s.label}: ${s.value}`}
          />
        ))}
      </Box>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {shown.map((s) => (
          <Box key={s.label} sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: "2px", bgcolor: s.color }} />
            <Typography variant="caption" color="text.secondary">
              {s.label}: {s.value}
            </Typography>
          </Box>
        ))}
      </Stack>
    </Box>
  );
}
