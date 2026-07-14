/**
 * LayerSummaryReport — generic per-card summary for any EA layer, mirroring the
 * Application Summary: pick a card in the layer and see its relationships
 * grouped by EA layer, with cross-layer reach metrics. Layer card types are
 * derived from the metamodel `category`, so it works for every layer.
 * [FORK FEATURE] — noraPlan.md (layer summaries).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link as RouterLink, useSearchParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import CardPicker, { type CardOption } from "@/components/CardPicker";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useTypeLabel } from "@/hooks/useResolveLabel";
import type { Card, Relation, RelationType } from "@/types";

interface RelatedEntry {
  card: NonNullable<Relation["source"]>;
  relation: Relation;
  direction: "incoming" | "outgoing";
  relationType?: RelationType;
}

const LAYER_ORDER = [
  "Business",
  "Beneficiary Experience",
  "Application",
  "Data",
  "Technology",
  "Security",
  "Other",
];

function lifecyclePhase(lifecycle?: Record<string, string>) {
  if (!lifecycle) return "notSet";
  if (lifecycle.endOfLife) return "endOfLife";
  if (lifecycle.phaseOut) return "phaseOut";
  if (lifecycle.active) return "active";
  if (lifecycle.phaseIn) return "phaseIn";
  if (lifecycle.plan) return "plan";
  return "notSet";
}

export default function LayerSummaryReport({ layer }: { layer: string }) {
  const { t } = useTranslation(["reports", "common"]);
  const [params, setParams] = useSearchParams();
  const [selected, setSelected] = useState<CardOption | null>(null);
  const [card, setCard] = useState<Card | null>(null);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [loading, setLoading] = useState(false);
  const { types, relationTypes, getType } = useMetamodel();
  const typeLabel = useTypeLabel();

  const layerTypeKeys = useMemo(
    () => types.filter((ty) => ty.category === layer && !ty.is_hidden).map((ty) => ty.key),
    [types, layer],
  );

  const relationTypeMap = useMemo(
    () => new Map(relationTypes.map((rt) => [rt.key, rt])),
    [relationTypes],
  );

  const load = useCallback(async (cardId: string) => {
    setLoading(true);
    try {
      const [cardRes, relationRes] = await Promise.all([
        api.get<Card>(`/cards/${cardId}`),
        api.get<Relation[]>(`/relations?card_id=${cardId}`),
      ]);
      setCard(cardRes);
      setSelected({ id: cardRes.id, name: cardRes.name, type: cardRes.type });
      setRelations(relationRes);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const cardId = params.get("card_id");
    if (cardId) load(cardId);
  }, [params, load]);

  const onPick = (option: CardOption | null) => {
    setSelected(option);
    if (!option) {
      setParams({}, { replace: true });
      setCard(null);
      setRelations([]);
      return;
    }
    setParams({ card_id: option.id }, { replace: true });
    load(option.id);
  };

  const relatedByLayer = useMemo(() => {
    const groups = new Map<string, RelatedEntry[]>();
    for (const l of LAYER_ORDER) groups.set(l, []);
    if (!card) return groups;
    for (const relation of relations) {
      const isOutgoing = relation.source_id === card.id;
      const peer = isOutgoing ? relation.target : relation.source;
      if (!peer) continue;
      const typeDef = types.find((type) => type.key === peer.type);
      const category =
        typeDef?.category && LAYER_ORDER.includes(typeDef.category) ? typeDef.category : "Other";
      groups.get(category)!.push({
        card: peer,
        relation,
        direction: isOutgoing ? "outgoing" : "incoming",
        relationType: relationTypeMap.get(relation.type),
      });
    }
    for (const entries of groups.values()) {
      entries.sort((a, b) => a.card.name.localeCompare(b.card.name));
    }
    return groups;
  }, [card, relations, relationTypeMap, types]);

  const total = relations.length;
  const phase = lifecyclePhase(card?.lifecycle);
  const phaseLabelKey =
    phase === "notSet"
      ? "lifecycle.notSet"
      : `lifecycle.phase${phase.charAt(0).toUpperCase()}${phase.slice(1)}`;

  return (
    <Box sx={{ maxWidth: 1320, mx: "auto", p: 3 }}>
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Box sx={{ flex: 1, minWidth: 280 }}>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>
            {t("layerSummary.title", { layer })}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 0.75 }}>
            {t("layerSummary.subtitle")}
          </Typography>
        </Box>
        <Box sx={{ width: { xs: "100%", sm: 420 } }}>
          <CardPicker
            types={layerTypeKeys}
            value={selected}
            onChange={onPick}
            label={t("layerSummary.pickCard")}
            fullWidth
            enabled={layerTypeKeys.length > 0}
          />
        </Box>
      </Box>

      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {!loading && !card && (
        <Paper variant="outlined" sx={{ p: 4, textAlign: "center", borderRadius: 1 }}>
          <MaterialSymbol icon="account_tree" size={42} color="#90a4ae" />
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            {t("layerSummary.empty")}
          </Typography>
        </Paper>
      )}

      {!loading && card && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Paper variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
            <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start", flexWrap: "wrap" }}>
              <Box
                sx={{
                  width: 54,
                  height: 54,
                  borderRadius: 1,
                  bgcolor: getType(card.type)?.color ?? "#1565c0",
                  display: "grid",
                  placeItems: "center",
                  color: "#fff",
                  flexShrink: 0,
                }}
              >
                <MaterialSymbol icon={getType(card.type)?.icon ?? "category"} size={30} color="inherit" />
              </Box>
              <Box sx={{ flex: 1, minWidth: 260 }}>
                <Typography variant="h5" sx={{ fontWeight: 800 }}>
                  {card.name}
                </Typography>
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1 }}>
                  <Chip size="small" label={getType(card.type) ? typeLabel(getType(card.type)!) : card.type} />
                  <Chip size="small" label={t(phaseLabelKey)} variant="outlined" />
                  <Chip
                    size="small"
                    label={`${Math.round(card.data_quality ?? 0)}% ${t("layerSummary.dataQuality")}`}
                    variant="outlined"
                  />
                  <Chip size="small" label={card.approval_status} variant="outlined" />
                </Box>
                {card.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
                    {card.description}
                  </Typography>
                )}
              </Box>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                <Button component={RouterLink} to={`/cards/${card.id}`} variant="contained" sx={{ textTransform: "none" }}>
                  {t("layerSummary.openCard")}
                </Button>
                <Button component={RouterLink} to={`/reports/impact?card_id=${card.id}`} variant="outlined" sx={{ textTransform: "none" }}>
                  {t("layerSummary.impact")}
                </Button>
              </Box>
            </Box>
          </Paper>

          {total === 0 ? (
            <Alert severity="info">{t("layerSummary.noRelations")}</Alert>
          ) : (
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "repeat(2, 1fr)" }, gap: 2 }}>
              {LAYER_ORDER.map((l) => {
                const entries = relatedByLayer.get(l) ?? [];
                if (entries.length === 0) return null;
                return (
                  <Paper key={l} variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
                    <Typography variant="h6" sx={{ fontWeight: 750, mb: 1 }}>
                      {l}
                    </Typography>
                    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                      {entries.map((entry) => {
                        const typeDef = getType(entry.card.type);
                        const label =
                          entry.direction === "outgoing"
                            ? entry.relationType?.label
                            : entry.relationType?.reverse_label || entry.relationType?.label;
                        return (
                          <Box
                            key={`${entry.relation.id}-${entry.card.id}`}
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                              p: 1,
                              border: "1px solid",
                              borderColor: "divider",
                              borderRadius: 1,
                            }}
                          >
                            <Box
                              sx={{
                                width: 10,
                                height: 10,
                                borderRadius: "50%",
                                bgcolor: typeDef?.color ?? "#90a4ae",
                                flexShrink: 0,
                              }}
                            />
                            <Box sx={{ flex: 1, minWidth: 0 }}>
                              <Typography
                                component={RouterLink}
                                to={`/cards/${entry.card.id}`}
                                variant="body2"
                                sx={{ fontWeight: 650, color: "primary.main", textDecoration: "none" }}
                              >
                                {entry.card.name}
                              </Typography>
                              <Typography variant="caption" color="text.secondary" display="block">
                                {(typeDef ? typeLabel(typeDef) : entry.card.type)} · {label ?? entry.relation.type}
                              </Typography>
                            </Box>
                            <MaterialSymbol
                              icon={entry.direction === "outgoing" ? "arrow_forward" : "arrow_back"}
                              size={18}
                              color="#78909c"
                            />
                          </Box>
                        );
                      })}
                    </Box>
                  </Paper>
                );
              })}
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
}
