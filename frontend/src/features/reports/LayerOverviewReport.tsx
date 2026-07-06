/**
 * LayerOverviewReport — a generic, layer-parameterised dashboard mirroring the
 * bespoke Application Layer Overview for every other EA layer (Strategy &
 * Transformation, Business Architecture, Technical Architecture, and any custom
 * layer). Given an EA layer (card-type `category`), it renders metric tiles,
 * a per-card-type breakdown, a lifecycle distribution bar, a data-quality tier
 * split, an attention list, and quick actions — all data-driven from the
 * metamodel + cards, so new card types in a layer appear automatically.
 * [FORK FEATURE] — noraPlan.md (layer overviews).
 */
import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import { getCurrentPhase } from "@/components/LifecycleBadge";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useTypeLabel } from "@/hooks/useResolveLabel";
import { CARD_TYPE_COLORS, DATA_QUALITY_COLORS, LAYER_COLORS, STATUS_COLORS } from "@/theme/tokens";
import type { Card, CardType } from "@/types";

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

function dqTier(q: number): (typeof DQ_TIERS)[number] {
  if (q < 25) return "0-25";
  if (q < 50) return "25-50";
  if (q < 75) return "50-75";
  return "75-100";
}

function typeColor(key: string): string {
  return (CARD_TYPE_COLORS as Record<string, string>)[key] ?? "#78909c";
}

export default function LayerOverviewReport({ layer }: { layer: string }) {
  const { t } = useTranslation(["reports", "common"]);
  const { types } = useMetamodel();
  const typeLabel = useTypeLabel();
  const [cards, setCards] = useState<Card[] | null>(null);
  const [error, setError] = useState(false);

  const layerTypes = useMemo(
    () => types.filter((ty) => ty.category === layer && !ty.is_hidden),
    [types, layer],
  );

  useEffect(() => {
    if (layerTypes.length === 0) {
      setCards([]);
      return;
    }
    setCards(null);
    Promise.all(
      layerTypes.map((ty) =>
        api
          .get<{ items: Card[] }>(`/cards?type=${encodeURIComponent(ty.key)}&page_size=5000`)
          .then((r) => r.items)
          .catch(() => [] as Card[]),
      ),
    )
      .then((lists) => setCards(lists.flat()))
      .catch(() => {
        setError(true);
        setCards([]);
      });
  }, [layerTypes]);

  const stats = useMemo(() => {
    const list = cards ?? [];
    const total = list.length;
    const avgQuality = total
      ? Math.round(list.reduce((s, c) => s + (c.data_quality ?? 0), 0) / total)
      : 0;
    const approved = list.filter((c) => c.approval_status === "APPROVED").length;
    const phases: Record<string, number> = {};
    const dq: Record<string, number> = {};
    const byType: Record<string, number> = {};
    let atRisk = 0;
    let attention = 0;
    for (const c of list) {
      const phase = getCurrentPhase(c.lifecycle) ?? "notSet";
      phases[phase] = (phases[phase] ?? 0) + 1;
      if (phase === "phaseOut" || phase === "endOfLife") atRisk += 1;
      const q = c.data_quality ?? 0;
      dq[dqTier(q)] = (dq[dqTier(q)] ?? 0) + 1;
      if (q < 50) attention += 1;
      byType[c.type] = (byType[c.type] ?? 0) + 1;
    }
    return { total, avgQuality, approved, phases, dq, byType, atRisk, attention };
  }, [cards]);

  const attentionCards = useMemo(
    () =>
      [...(cards ?? [])]
        .sort((a, b) => (a.data_quality ?? 0) - (b.data_quality ?? 0))
        .slice(0, 12),
    [cards],
  );

  const accent = (LAYER_COLORS as Record<string, string>)[layer] ?? STATUS_COLORS.info;

  if (cards === null) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const maxTypeCount = Math.max(1, ...Object.values(stats.byType));

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 0.5 }}>
        <Box sx={{ width: 8, height: 32, borderRadius: 1, bgcolor: accent }} />
        <Typography variant="h5" fontWeight={800}>
          {t("layerOverview.title", { layer })}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("layerOverview.subtitle")}
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{t("layerOverview.error")}</Alert>}

      {stats.total === 0 ? (
        <Alert severity="info">{t("layerOverview.empty")}</Alert>
      ) : (
        <>
          {/* Metric tiles */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" },
              gap: 1.5,
              mb: 2,
            }}
          >
            <MetricTile icon="dashboard" label={t("layerOverview.metric.total")} value={stats.total} color={accent} />
            <MetricTile
              icon="verified"
              label={t("layerOverview.metric.avgQuality")}
              value={`${stats.avgQuality}%`}
              color={STATUS_COLORS.info}
            />
            <MetricTile
              icon="task_alt"
              label={t("layerOverview.metric.approved")}
              value={`${stats.total ? Math.round((stats.approved / stats.total) * 100) : 0}%`}
              color={STATUS_COLORS.success}
            />
            <MetricTile
              icon="warning"
              label={t("layerOverview.metric.atRisk")}
              value={stats.atRisk}
              color={stats.atRisk ? STATUS_COLORS.warning : STATUS_COLORS.neutral}
            />
          </Box>

          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2 }}>
            {/* By card type */}
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="subtitle1" fontWeight={700} mb={1}>
                {t("layerOverview.byType")}
              </Typography>
              <Stack spacing={1}>
                {layerTypes
                  .filter((ty) => (stats.byType[ty.key] ?? 0) > 0)
                  .sort((a, b) => (stats.byType[b.key] ?? 0) - (stats.byType[a.key] ?? 0))
                  .map((ty) => {
                    const count = stats.byType[ty.key] ?? 0;
                    return (
                      <Box key={ty.key}>
                        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.25 }}>
                          <Link
                            component={RouterLink}
                            to={`/inventory?type=${ty.key}`}
                            underline="hover"
                            variant="body2"
                          >
                            {typeLabel(ty as CardType)}
                          </Link>
                          <Typography variant="body2" fontWeight={700}>
                            {count}
                          </Typography>
                        </Box>
                        <Box sx={{ height: 8, borderRadius: 1, bgcolor: "action.hover" }}>
                          <Box
                            sx={{
                              height: 8,
                              borderRadius: 1,
                              width: `${(count / maxTypeCount) * 100}%`,
                              bgcolor: ty.color || typeColor(ty.key),
                            }}
                          />
                        </Box>
                      </Box>
                    );
                  })}
              </Stack>
            </Paper>

            {/* Lifecycle + quality */}
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
                  label: tier + "%",
                  value: stats.dq[tier] ?? 0,
                  color: DATA_QUALITY_COLORS[tier],
                }))}
                total={stats.total}
              />
            </Paper>
          </Box>

          {/* Attention list */}
          <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
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
                    <TableCell>{t("layerOverview.colType")}</TableCell>
                    <TableCell align="right">{t("layerOverview.colQuality")}</TableCell>
                    <TableCell>{t("layerOverview.colApproval")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {attentionCards.map((c) => {
                    const ty = types.find((x) => x.key === c.type);
                    const q = Math.round(c.data_quality ?? 0);
                    return (
                      <TableRow key={c.id} hover>
                        <TableCell>
                          <Link component={RouterLink} to={`/cards/${c.id}`} underline="hover">
                            {c.name}
                          </Link>
                        </TableCell>
                        <TableCell>{ty ? typeLabel(ty) : c.type}</TableCell>
                        <TableCell align="right">
                          <Chip
                            size="small"
                            label={`${q}%`}
                            sx={{ bgcolor: DATA_QUALITY_COLORS[dqTier(q)], color: "#fff", minWidth: 52 }}
                          />
                        </TableCell>
                        <TableCell>{c.approval_status}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </Paper>

          {/* Quick actions */}
          <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: "wrap" }} useFlexGap>
            {layerTypes[0] && (
              <Button
                component={RouterLink}
                to={`/inventory?type=${layerTypes[0].key}`}
                variant="outlined"
                startIcon={<MaterialSymbol icon="inventory_2" size={18} />}
              >
                {t("layerOverview.actions.inventory")}
              </Button>
            )}
            <Button
              component={RouterLink}
              to="/reports/dependencies"
              variant="outlined"
              startIcon={<MaterialSymbol icon="hub" size={18} />}
            >
              {t("layerOverview.actions.dependencies")}
            </Button>
            <Button
              component={RouterLink}
              to="/reports/portfolio"
              variant="outlined"
              startIcon={<MaterialSymbol icon="dashboard" size={18} />}
            >
              {t("layerOverview.actions.portfolio")}
            </Button>
          </Stack>
        </>
      )}
    </Box>
  );
}

function MetricTile({
  icon,
  label,
  value,
  color,
}: {
  icon: string;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <Paper variant="outlined" sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
      <MaterialSymbol icon={icon} size={30} color={color} />
      <Box>
        <Typography variant="h5" fontWeight={800} lineHeight={1.1}>
          {value}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
      </Box>
    </Paper>
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
