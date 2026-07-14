/**
 * TraceabilityView — the "Relationships / Traceability" page in the ea-ui-mvp
 * style: pick one card and see its connections across all six EA layers — a
 * selected-component summary, a direct-traceability diagram (one band per
 * layer), direct connections grouped by layer, and the two-hop extended
 * impact. Clicking any node opens the component-details side drawer.
 * Route: `/layers/traceability`.
 * [FORK FEATURE] — noraPlan.md (layer overviews).
 */
import { useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import CardPicker, { type CardOption } from "@/components/CardPicker";
import ApprovalStatusBadge from "@/components/ApprovalStatusBadge";
import LifecycleBadge from "@/components/LifecycleBadge";
import LayerCardDrawer from "@/features/layers/LayerCardDrawer";
import {
  EA_LAYERS,
  ExplorerPage,
  HealthLine,
  Panel,
  cardStatus,
  useLayerName,
  type RelCardRef,
  type RelRow,
} from "@/features/layers/shared";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useRelationLabel, useTypeLabel } from "@/hooks/useResolveLabel";
import { LAYER_COLORS, STATUS_COLORS } from "@/theme/tokens";
import type { Card } from "@/types";

const TWO_HOP_ITEMS = 12;

interface Connection {
  other: RelCardRef;
  verb: string;
  incoming: boolean;
}

export default function TraceabilityView() {
  const { t } = useTranslation(["reports", "common"]);
  const { types, relationTypes } = useMetamodel();
  const typeLabel = useTypeLabel();
  const relationLabel = useRelationLabel();
  const layerName = useLayerName();
  const [selected, setSelected] = useState<CardOption | null>(null);
  const [selectedCard, setSelectedCard] = useState<Card | null>(null);
  const [rels, setRels] = useState<RelRow[] | null>(null);
  const [drawerCardId, setDrawerCardId] = useState<string | null>(null);

  const typeByKey = useMemo(() => new Map(types.map((ty) => [ty.key, ty])), [types]);
  const relTypeByKey = useMemo(
    () => new Map(relationTypes.map((rt) => [rt.key, rt])),
    [relationTypes],
  );
  const layerOfType = useMemo(() => {
    const m = new Map<string, string>();
    for (const ty of types) if (ty.category) m.set(ty.key, ty.category);
    return m;
  }, [types]);

  // The full relation set, fetched once — direct + two-hop are computed client-side.
  useEffect(() => {
    let cancelled = false;
    api
      .get<RelRow[]>("/relations")
      .then((rows) => {
        if (!cancelled) setRels(rows);
      })
      .catch(() => {
        if (!cancelled) setRels([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setSelectedCard(null);
    if (!selected) return;
    let cancelled = false;
    api
      .get<Card>(`/cards/${selected.id}`)
      .then((c) => {
        if (!cancelled) setSelectedCard(c);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const verbFor = (relTypeKey: string, incoming: boolean): string => {
    const rt = relTypeByKey.get(relTypeKey);
    return rt ? relationLabel(rt, incoming) : relTypeKey;
  };

  /** Direct connections of the selected card. */
  const direct = useMemo<Connection[]>(() => {
    if (!selected || !rels) return [];
    const out: Connection[] = [];
    for (const r of rels) {
      if (!r.source || !r.target) continue;
      if (r.source.id === selected.id) {
        out.push({ other: r.target, verb: verbFor(r.type, false), incoming: false });
      } else if (r.target.id === selected.id) {
        out.push({ other: r.source, verb: verbFor(r.type, true), incoming: true });
      }
    }
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, rels, relTypeByKey, relationLabel]);

  /** Two-hop neighbours: connected to a direct neighbour, not direct themselves. */
  const twoHop = useMemo(() => {
    if (!selected || !rels) return [];
    const directIds = new Set(direct.map((c) => c.other.id));
    const seen = new Set<string>();
    const out: { card: RelCardRef; via: RelCardRef }[] = [];
    for (const d of direct) {
      for (const r of rels) {
        if (!r.source || !r.target) continue;
        let other: RelCardRef | null = null;
        if (r.source.id === d.other.id) other = r.target;
        else if (r.target.id === d.other.id) other = r.source;
        if (!other || other.id === selected.id || directIds.has(other.id) || seen.has(other.id))
          continue;
        seen.add(other.id);
        out.push({ card: other, via: d.other });
      }
    }
    return out.slice(0, TWO_HOP_ITEMS);
  }, [selected, rels, direct]);

  const directByLayer = useMemo(() => {
    const m = new Map<string, Connection[]>();
    for (const c of direct) {
      const l = layerOfType.get(c.other.type) ?? "";
      if (!m.has(l)) m.set(l, []);
      m.get(l)!.push(c);
    }
    return m;
  }, [direct, layerOfType]);

  const selectedLayer = selected ? layerOfType.get(selected.type) : undefined;
  const selectedTy = selected ? typeByKey.get(selected.type) : undefined;
  const openDrawer = (id: string) => setDrawerCardId(id);

  return (
    <ExplorerPage>
      {/* Intro + picker */}
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Box sx={{ flex: 1, minWidth: 280 }}>
          <Typography
            variant="overline"
            color="text.secondary"
            sx={{ lineHeight: 1.4, letterSpacing: 0.8 }}
            display="block"
          >
            {t("traceability.eyebrow")}
          </Typography>
          <Typography variant="h5" fontWeight={800} sx={{ mb: 0.5 }}>
            {t("traceability.title")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("traceability.subtitle")}
          </Typography>
        </Box>
        <Box sx={{ width: { xs: "100%", sm: 360 } }}>
          <CardPicker
            value={selected}
            onChange={setSelected}
            label={t("traceability.pickerLabel")}
            placeholder={t("traceability.pickerPlaceholder")}
            fullWidth
          />
        </Box>
      </Box>

      {rels === null ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : !selected ? (
        <Alert severity="info">{t("traceability.empty")}</Alert>
      ) : (
        <>
          {/* Row A — selected component | trace diagram */}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 2fr) minmax(0, 3fr)" },
              gap: 2,
              mb: 2,
            }}
          >
            <Panel
              eyebrow={t("traceability.selectedEyebrow")}
              title={selected.name}
              action={
                <Button
                  size="small"
                  variant="outlined"
                  className="no-print"
                  onClick={() => openDrawer(selected.id)}
                >
                  {t("traceability.openDetails")}
                </Button>
              }
            >
              {!selectedCard ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : (
                <>
                  <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
                    {selectedLayer && (
                      <Chip
                        size="small"
                        label={layerName(selectedLayer)}
                        sx={{
                          bgcolor:
                            (LAYER_COLORS as Record<string, string>)[selectedLayer] ??
                            STATUS_COLORS.neutral,
                          color: "#fff",
                        }}
                      />
                    )}
                    {selectedTy && (
                      <Chip size="small" variant="outlined" label={typeLabel(selectedTy)} />
                    )}
                    <LifecycleBadge lifecycle={selectedCard.lifecycle} />
                    <ApprovalStatusBadge status={selectedCard.approval_status} />
                  </Stack>
                  {selectedCard.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                      {selectedCard.description}
                    </Typography>
                  )}
                  <HealthLine
                    status={cardStatus(selectedCard)}
                    value={Math.round(selectedCard.data_quality ?? 0)}
                  />
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.5 }}>
                    {t("traceability.directCount", { count: direct.length })}
                  </Typography>
                </>
              )}
            </Panel>

            <Panel
              eyebrow={t("traceability.diagramEyebrow")}
              title={t("traceability.diagramTitle")}
            >
              <Stack spacing={0.75}>
                {EA_LAYERS.map((l) => {
                  const lColor =
                    (LAYER_COLORS as Record<string, string>)[l] ?? STATUS_COLORS.neutral;
                  const isSelectedLayer = l === selectedLayer;
                  const nodes = directByLayer.get(l) ?? [];
                  return (
                    <Box
                      key={l}
                      sx={{
                        border: "1px solid",
                        borderColor: isSelectedLayer ? lColor : "divider",
                        borderInlineStart: `4px solid ${lColor}`,
                        borderRadius: 1,
                        px: 1.5,
                        py: 1,
                        bgcolor: isSelectedLayer ? `${lColor}14` : "background.paper",
                      }}
                    >
                      <Typography
                        variant="caption"
                        fontWeight={800}
                        sx={{ color: lColor }}
                        display="block"
                        mb={0.5}
                      >
                        {layerName(l)}
                      </Typography>
                      {isSelectedLayer ? (
                        <Chip
                          size="small"
                          label={selected.name}
                          onClick={() => openDrawer(selected.id)}
                          sx={{ bgcolor: lColor, color: "#fff", fontWeight: 700 }}
                        />
                      ) : nodes.length === 0 ? (
                        <Typography variant="caption" color="text.secondary">
                          {t("traceability.noDirectLink")}
                        </Typography>
                      ) : (
                        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                          {nodes.map((n, i) => (
                            <Chip
                              key={`${n.other.id}-${i}`}
                              size="small"
                              clickable
                              onClick={() => openDrawer(n.other.id)}
                              label={`${n.other.name} • ${n.verb}`}
                              sx={{
                                maxWidth: 240,
                                border: `1px solid ${lColor}`,
                                bgcolor: `${lColor}14`,
                              }}
                            />
                          ))}
                        </Box>
                      )}
                    </Box>
                  );
                })}
              </Stack>
            </Panel>
          </Box>

          {/* Direct connections grouped by layer */}
          <Box sx={{ mb: 2 }}>
            <Panel
              eyebrow={t("traceability.connectedEyebrow")}
              title={t("traceability.connectedTitle")}
              count={t("layerOverview.links", { count: direct.length })}
            >
              {direct.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {t("traceability.noConnections")}
                </Typography>
              ) : (
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: {
                      xs: "1fr",
                      sm: "repeat(2, minmax(0, 1fr))",
                      lg: "repeat(3, minmax(0, 1fr))",
                    },
                    gap: 1,
                  }}
                >
                  {EA_LAYERS.filter((l) => (directByLayer.get(l) ?? []).length > 0).map((l) => {
                    const lColor =
                      (LAYER_COLORS as Record<string, string>)[l] ?? STATUS_COLORS.neutral;
                    return (
                      <Box
                        key={l}
                        sx={{
                          border: "1px solid",
                          borderColor: "divider",
                          borderRadius: 1,
                          p: 1.25,
                          minWidth: 0,
                        }}
                      >
                        <Typography
                          variant="caption"
                          fontWeight={800}
                          sx={{ color: lColor }}
                          display="block"
                          mb={0.75}
                        >
                          {layerName(l)}
                        </Typography>
                        <Stack spacing={0.5}>
                          {(directByLayer.get(l) ?? []).map((c, i) => (
                            <ButtonBase
                              key={`${c.other.id}-${i}`}
                              onClick={() => openDrawer(c.other.id)}
                              sx={{
                                display: "block",
                                width: "100%",
                                textAlign: "start",
                                bgcolor: "action.hover",
                                borderRadius: 1,
                                px: 1,
                                py: 0.5,
                                "&:hover": { bgcolor: "action.selected" },
                              }}
                            >
                              <Typography variant="caption" fontWeight={700} noWrap display="block">
                                {c.other.name}
                              </Typography>
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                noWrap
                                display="block"
                              >
                                {c.incoming ? "←" : "→"} {c.verb}
                              </Typography>
                            </ButtonBase>
                          ))}
                        </Stack>
                      </Box>
                    );
                  })}
                </Box>
              )}
            </Panel>
          </Box>

          {/* Two-hop extended impact */}
          <Panel
            eyebrow={t("traceability.impactEyebrow")}
            title={t("traceability.impactTitle")}
            count={t("layerOverview.items", { count: twoHop.length })}
          >
            {twoHop.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                {t("traceability.noImpact")}
              </Typography>
            ) : (
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    sm: "repeat(2, minmax(0, 1fr))",
                    lg: "repeat(4, minmax(0, 1fr))",
                  },
                  gap: 1,
                }}
              >
                {twoHop.map((x) => {
                  const l = layerOfType.get(x.card.type);
                  const lColor = l
                    ? ((LAYER_COLORS as Record<string, string>)[l] ?? STATUS_COLORS.neutral)
                    : STATUS_COLORS.neutral;
                  return (
                    <ButtonBase
                      key={x.card.id}
                      onClick={() => openDrawer(x.card.id)}
                      sx={{
                        display: "block",
                        textAlign: "start",
                        border: "1px solid",
                        borderColor: "divider",
                        borderInlineStart: `4px solid ${lColor}`,
                        borderRadius: 1,
                        p: 1.25,
                        minWidth: 0,
                        "&:hover": { bgcolor: "action.hover" },
                      }}
                    >
                      <Typography variant="body2" fontWeight={700} noWrap>
                        {x.card.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" noWrap display="block">
                        {l ? layerName(l) : ""}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" noWrap display="block">
                        {t("traceability.via", { name: x.via.name })}
                      </Typography>
                    </ButtonBase>
                  );
                })}
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
