/**
 * LayersDashboard — the "Dashboard / Overview" of the EA layers section, in
 * the ea-ui-mvp style: a hero banner with a jump to the traceability view, a
 * KPI grid, six layer cards (health pill + meta grid), the layer stack, a
 * health-by-layer bar chart, a priority-attention list, and an inventory
 * preview table. Clicking any card opens the component-details side drawer.
 * Route: `/layers/overview`.
 * [FORK FEATURE] — noraPlan.md (layer overviews).
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
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
import MetricCard from "@/features/reports/MetricCard";
import LifecycleBadge from "@/components/LifecycleBadge";
import LayerCardDrawer from "@/features/layers/LayerCardDrawer";
import {
  EA_LAYERS,
  ExplorerPage,
  HealthLine,
  LAYER_SLUG,
  Panel,
  STATUS_COLOR,
  cardStatus,
  scoreStatus,
  statusChipSx,
  useLayerName,
} from "@/features/layers/shared";
import { EXPLORER_COLORS } from "@/theme/tokens";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useTypeLabel } from "@/hooks/useResolveLabel";
import { LAYER_COLORS, STATUS_COLORS } from "@/theme/tokens";
import type { Card, CardType } from "@/types";

const ATTENTION_ITEMS = 8;
const PREVIEW_ROWS = 12;

const LAYER_ICONS: Record<string, string> = {
  Business: "domain",
  "Beneficiary Experience": "diversity_3",
  Application: "apps",
  Data: "database",
  Technology: "memory",
  Security: "security",
};

export default function LayersDashboard() {
  const { t } = useTranslation(["reports", "common"]);
  const navigate = useNavigate();
  const { types } = useMetamodel();
  const typeLabel = useTypeLabel();
  const layerName = useLayerName();
  const [cards, setCards] = useState<Card[] | null>(null);
  const [error, setError] = useState(false);
  const [drawerCardId, setDrawerCardId] = useState<string | null>(null);

  const typesByLayer = useMemo(() => {
    const m: Record<string, CardType[]> = {};
    for (const l of EA_LAYERS) m[l] = types.filter((ty) => ty.category === l && !ty.is_hidden);
    return m;
  }, [types]);

  const typeByKey = useMemo(() => new Map(types.map((ty) => [ty.key, ty])), [types]);
  const layerOfType = useMemo(() => {
    const m = new Map<string, string>();
    for (const ty of types) if (ty.category) m.set(ty.key, ty.category);
    return m;
  }, [types]);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    setCards(null);
    const allTypes = EA_LAYERS.flatMap((l) => typesByLayer[l] ?? []);
    Promise.all(
      allTypes.map((ty) =>
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
    return () => {
      cancelled = true;
    };
  }, [typesByLayer]);

  const byLayer = useMemo(() => {
    const m: Record<string, { cards: Card[]; avg: number; risky: number }> = {};
    for (const l of EA_LAYERS) m[l] = { cards: [], avg: 0, risky: 0 };
    for (const c of cards ?? []) {
      const l = layerOfType.get(c.type);
      if (l && m[l]) m[l].cards.push(c);
    }
    for (const l of EA_LAYERS) {
      const list = m[l].cards;
      m[l].avg = list.length
        ? Math.round(list.reduce((s, c) => s + (c.data_quality ?? 0), 0) / list.length)
        : 0;
      m[l].risky = list.filter((c) => cardStatus(c) !== "healthy").length;
    }
    return m;
  }, [cards, layerOfType]);

  const totalCards = cards?.length ?? 0;
  const totalRisky = useMemo(
    () => (cards ?? []).filter((c) => cardStatus(c) !== "healthy").length,
    [cards],
  );

  const attentionCards = useMemo(
    () =>
      [...(cards ?? [])]
        .filter((c) => cardStatus(c) !== "healthy")
        .sort((a, b) => (a.data_quality ?? 0) - (b.data_quality ?? 0))
        .slice(0, ATTENTION_ITEMS),
    [cards],
  );

  const previewCards = useMemo(
    () => [...(cards ?? [])].sort((a, b) => a.name.localeCompare(b.name)).slice(0, PREVIEW_ROWS),
    [cards],
  );

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
      {/* Hero */}
      <Paper
        variant="outlined"
        sx={(theme) => ({
          p: 3,
          mb: 2,
          display: "flex",
          alignItems: "center",
          gap: 2,
          flexWrap: "wrap",
          borderRadius: 3.5,
          ...(theme.palette.mode === "light" && {
            background: "linear-gradient(135deg, #ffffff 0%, #eef5ff 100%)",
            borderColor: EXPLORER_COLORS.line,
            boxShadow: EXPLORER_COLORS.shadow,
          }),
        })}
      >
        <Box sx={{ flex: 1, minWidth: 280 }}>
          <Typography
            variant="overline"
            sx={(theme) => ({
              lineHeight: 1.4,
              letterSpacing: 1.1,
              fontWeight: 800,
              color:
                theme.palette.mode === "light"
                  ? EXPLORER_COLORS.primary
                  : theme.palette.primary.light,
            })}
            display="block"
          >
            {t("layersDashboard.eyebrow")}
          </Typography>
          <Typography variant="h5" fontWeight={800} sx={{ mb: 0.5 }}>
            {t("layersDashboard.heroTitle")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("layersDashboard.heroText")}
          </Typography>
        </Box>
        <Button
          variant="contained"
          className="no-print"
          startIcon={<MaterialSymbol icon="hub" size={18} />}
          onClick={() => navigate("/layers/traceability")}
        >
          {t("layersDashboard.exploreTraceability")}
        </Button>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {t("layerOverview.error")}
        </Alert>
      )}

      {/* KPI grid — total, six layers, risks/gaps */}
      <Box sx={{ display: "flex", gap: 1.25, flexWrap: "wrap", mb: 2 }}>
        <MetricCard
          icon="dashboard"
          iconColor={STATUS_COLORS.info}
          color={STATUS_COLORS.info}
          label={t("layersDashboard.metric.total")}
          value={totalCards}
        />
        {EA_LAYERS.map((l) => (
          <MetricCard
            key={l}
            icon={LAYER_ICONS[l]}
            iconColor={(LAYER_COLORS as Record<string, string>)[l] ?? STATUS_COLORS.neutral}
            color={(LAYER_COLORS as Record<string, string>)[l] ?? STATUS_COLORS.neutral}
            label={layerName(l)}
            value={byLayer[l].cards.length}
          />
        ))}
        <MetricCard
          icon="report"
          iconColor={totalRisky ? STATUS_COLORS.error : STATUS_COLORS.neutral}
          color={totalRisky ? STATUS_COLORS.error : STATUS_COLORS.neutral}
          label={t("layersDashboard.metric.risks")}
          value={totalRisky}
        />
      </Box>

      {/* Row A — six layer cards | layer stack */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 3fr) minmax(0, 2fr)" },
          gap: 2,
          mb: 2,
        }}
      >
        <Panel
          eyebrow={t("layersDashboard.domainsEyebrow")}
          title={t("layersDashboard.domainsTitle")}
        >
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
              gap: 1,
            }}
          >
            {EA_LAYERS.map((l) => {
              const lColor = (LAYER_COLORS as Record<string, string>)[l] ?? STATUS_COLORS.neutral;
              const info = byLayer[l];
              const status = scoreStatus(info.avg);
              return (
                <ButtonBase
                  key={l}
                  onClick={() => navigate(`/layers/${LAYER_SLUG[l]}`)}
                  sx={{
                    display: "block",
                    textAlign: "start",
                    border: "1px solid",
                    borderColor: "divider",
                    borderTop: `4px solid ${lColor}`,
                    borderRadius: 1,
                    p: 1.5,
                    minWidth: 0,
                    "&:hover": { bgcolor: "action.hover" },
                  }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                    <MaterialSymbol icon={LAYER_ICONS[l]} size={20} color={lColor} />
                    <Typography variant="subtitle2" fontWeight={800} sx={{ color: lColor }} noWrap>
                      {layerName(l)}
                    </Typography>
                  </Box>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    display="block"
                    sx={{
                      mb: 1,
                      display: "-webkit-box",
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: "vertical",
                      overflow: "hidden",
                    }}
                  >
                    {t(`layerOverview.about.${LAYER_SLUG[l]}`)}
                  </Typography>
                  {info.cards.length > 0 && <HealthLine status={status} value={info.avg} />}
                  <Box
                    sx={{
                      display: "grid",
                      gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                      gap: 0.5,
                      mt: 1,
                    }}
                  >
                    <MetaCell
                      label={t("layerOverview.metric.total")}
                      value={String(info.cards.length)}
                    />
                    <MetaCell
                      label={t("layerOverview.metric.types")}
                      value={String((typesByLayer[l] ?? []).length)}
                    />
                    <MetaCell label={t("layersDashboard.metric.risks")} value={String(info.risky)} />
                  </Box>
                </ButtonBase>
              );
            })}
          </Box>
        </Panel>

        <Panel
          eyebrow={t("layerOverview.panel.stackEyebrow")}
          title={t("layersDashboard.stackTitle")}
        >
          <Stack spacing={0.75}>
            {EA_LAYERS.map((l) => {
              const lColor = (LAYER_COLORS as Record<string, string>)[l] ?? STATUS_COLORS.neutral;
              const info = byLayer[l];
              return (
                <ButtonBase
                  key={l}
                  onClick={() => navigate(`/layers/${LAYER_SLUG[l]}`)}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    width: "100%",
                    textAlign: "start",
                    border: "1px solid",
                    borderColor: "divider",
                    borderInlineStart: `4px solid ${lColor}`,
                    borderRadius: 1,
                    px: 1.5,
                    py: 1.25,
                    "&:hover": { bgcolor: "action.hover" },
                  }}
                >
                  <Typography variant="body2" fontWeight={800} sx={{ color: lColor, flex: 1 }}>
                    {layerName(l)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t("layersDashboard.stackMeta", {
                      count: info.cards.length,
                      health: info.avg,
                    })}
                  </Typography>
                </ButtonBase>
              );
            })}
          </Stack>
        </Panel>
      </Box>

      {/* Row B — health by layer | priority attention */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "repeat(2, minmax(0, 1fr))" },
          gap: 2,
          mb: 2,
        }}
      >
        <Panel
          eyebrow={t("layersDashboard.healthEyebrow")}
          title={t("layersDashboard.healthTitle")}
        >
          <Stack spacing={1.25}>
            {EA_LAYERS.map((l) => {
              const info = byLayer[l];
              const lColor = (LAYER_COLORS as Record<string, string>)[l] ?? STATUS_COLORS.neutral;
              return (
                <Box key={l} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Typography variant="body2" sx={{ width: 170, flexShrink: 0 }} noWrap>
                    {layerName(l)}
                  </Typography>
                  <Box
                    sx={{
                      flex: 1,
                      height: 10,
                      borderRadius: 5,
                      bgcolor: "action.hover",
                      overflow: "hidden",
                    }}
                  >
                    <Box
                      sx={{
                        width: `${info.avg}%`,
                        height: "100%",
                        borderRadius: 5,
                        bgcolor: lColor,
                      }}
                    />
                  </Box>
                  <Typography variant="body2" fontWeight={800} sx={{ minWidth: 40, textAlign: "end" }}>
                    {info.avg}%
                  </Typography>
                </Box>
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
                const l = layerOfType.get(c.type);
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
                      <Typography variant="caption" color="text.secondary" noWrap display="block">
                        {l ? `${layerName(l)} • ` : ""}
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

      {/* Inventory preview */}
      <Panel
        eyebrow={t("layersDashboard.previewEyebrow")}
        title={t("layersDashboard.previewTitle")}
        count={t("layerOverview.items", { count: totalCards })}
      >
        <Box sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t("layerOverview.colCard")}</TableCell>
                <TableCell>{t("layersDashboard.colLayer")}</TableCell>
                <TableCell>{t("layerOverview.colType")}</TableCell>
                <TableCell>{t("layerOverview.colStatus")}</TableCell>
                <TableCell>{t("layerOverview.colLifecycle")}</TableCell>
                <TableCell sx={{ minWidth: 160 }}>{t("layerOverview.colQuality")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {previewCards.map((c) => {
                const ty = typeByKey.get(c.type);
                const l = layerOfType.get(c.type);
                const lColor = l
                  ? ((LAYER_COLORS as Record<string, string>)[l] ?? STATUS_COLORS.neutral)
                  : STATUS_COLORS.neutral;
                const status = cardStatus(c);
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
                        <Typography variant="caption" color="text.secondary" noWrap display="block">
                          {c.description}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {l && (
                        <Chip
                          size="small"
                          label={layerName(l)}
                          sx={{ bgcolor: lColor, color: "#fff", height: 22 }}
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" noWrap>
                        {ty ? typeLabel(ty) : c.type}
                      </Typography>
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
                      <HealthLine status={status} value={Math.round(c.data_quality ?? 0)} />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Box>
        {totalCards > PREVIEW_ROWS && (
          <Box sx={{ mt: 1, textAlign: "center" }}>
            <Link
              component="button"
              underline="hover"
              variant="body2"
              onClick={() => navigate("/inventory")}
            >
              {t("layerOverview.viewAllInventory", { count: totalCards - PREVIEW_ROWS })}
            </Link>
          </Box>
        )}
      </Panel>

      <LayerCardDrawer
        cardId={drawerCardId}
        layerName={layerName}
        onClose={() => setDrawerCardId(null)}
        onOpenCard={openDrawer}
      />
    </ExplorerPage>
  );
}

function MetaCell({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="caption" color="text.secondary" display="block" noWrap>
        {label}
      </Typography>
      <Typography variant="body2" fontWeight={800}>
        {value}
      </Typography>
    </Box>
  );
}
