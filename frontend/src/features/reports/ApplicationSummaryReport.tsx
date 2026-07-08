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

export default function ApplicationSummaryReport() {
  const { t } = useTranslation(["reports", "common"]);
  const [params, setParams] = useSearchParams();
  const [selected, setSelected] = useState<CardOption | null>(null);
  const [app, setApp] = useState<Card | null>(null);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [loading, setLoading] = useState(false);
  const { types, relationTypes, getType } = useMetamodel();
  const typeLabel = useTypeLabel();

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
      setApp(cardRes);
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
      setApp(null);
      setRelations([]);
      return;
    }
    setParams({ card_id: option.id }, { replace: true });
    load(option.id);
  };

  const relatedByLayer = useMemo(() => {
    const groups = new Map<string, RelatedEntry[]>();
    for (const layer of LAYER_ORDER) groups.set(layer, []);
    if (!app) return groups;
    for (const relation of relations) {
      const isOutgoing = relation.source_id === app.id;
      const peer = isOutgoing ? relation.target : relation.source;
      if (!peer) continue;
      const typeDef = types.find((type) => type.key === peer.type);
      const category = typeDef?.category && LAYER_ORDER.includes(typeDef.category)
        ? typeDef.category
        : "Other";
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
  }, [app, relations, relationTypeMap, types]);

  const metrics = useMemo(() => {
    const uniqueRelated = new Set<string>();
    const business = new Set<string>();
    const data = new Set<string>();
    const technology = new Set<string>();
    for (const relation of relations) {
      const peer = relation.source_id === app?.id ? relation.target : relation.source;
      if (!peer) continue;
      uniqueRelated.add(peer.id);
      const category = getType(peer.type)?.category;
      // Beneficiary Experience counts toward business reach — journeys and
      // channels are business-facing consumers of the application.
      if (category === "Business" || category === "Beneficiary Experience") business.add(peer.id);
      if (category === "Data") data.add(peer.id);
      if (category === "Technology" || category === "Security") technology.add(peer.id);
    }
    return {
      related: uniqueRelated.size,
      business: business.size,
      data: data.size,
      technology: technology.size,
    };
  }, [app?.id, getType, relations]);

  const phase = lifecyclePhase(app?.lifecycle);
  const phaseLabelKey =
    phase === "notSet"
      ? "lifecycle.notSet"
      : `lifecycle.phase${phase.charAt(0).toUpperCase()}${phase.slice(1)}`;

  return (
    <Box sx={{ maxWidth: 1320, mx: "auto" }}>
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Box sx={{ flex: 1, minWidth: 280 }}>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>
            {t("applicationSummary.title")}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 0.75 }}>
            {t("applicationSummary.subtitle")}
          </Typography>
        </Box>
        <Box sx={{ width: { xs: "100%", sm: 420 } }}>
          <CardPicker
            types="Application"
            value={selected}
            onChange={onPick}
            label={t("applicationSummary.pickApplication")}
            fullWidth
          />
        </Box>
      </Box>

      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {!loading && !app && (
        <Paper variant="outlined" sx={{ p: 4, textAlign: "center", borderRadius: 1 }}>
          <MaterialSymbol icon="apps" size={42} color="#90a4ae" />
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            {t("applicationSummary.empty")}
          </Typography>
        </Paper>
      )}

      {!loading && app && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Paper variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
            <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start", flexWrap: "wrap" }}>
              <Box
                sx={{
                  width: 54,
                  height: 54,
                  borderRadius: 1,
                  bgcolor: getType(app.type)?.color ?? "#1565c0",
                  display: "grid",
                  placeItems: "center",
                  color: "#fff",
                  flexShrink: 0,
                }}
              >
                <MaterialSymbol icon={getType(app.type)?.icon ?? "apps"} size={30} color="inherit" />
              </Box>
              <Box sx={{ flex: 1, minWidth: 260 }}>
                <Typography variant="h5" sx={{ fontWeight: 800 }}>
                  {app.name}
                </Typography>
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1 }}>
                  <Chip
                    size="small"
                    label={getType(app.type) ? typeLabel(getType(app.type)!) : app.type}
                  />
                  <Chip size="small" label={t(phaseLabelKey)} variant="outlined" />
                  <Chip
                    size="small"
                    label={`${Math.round(app.data_quality ?? 0)}% ${t("applicationSummary.dataQuality")}`}
                    variant="outlined"
                  />
                  <Chip size="small" label={app.approval_status} variant="outlined" />
                </Box>
                {app.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
                    {app.description}
                  </Typography>
                )}
              </Box>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                <Button component={RouterLink} to={`/cards/${app.id}`} variant="contained" sx={{ textTransform: "none" }}>
                  {t("applicationSummary.openCard")}
                </Button>
                <Button component={RouterLink} to={`/reports/impact?card_id=${app.id}`} variant="outlined" sx={{ textTransform: "none" }}>
                  {t("applicationSummary.impact")}
                </Button>
              </Box>
            </Box>
          </Paper>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" },
              gap: 1.5,
            }}
          >
            {[
              ["related", metrics.related, "hub"],
              ["business", metrics.business, "domain"],
              ["data", metrics.data, "database"],
              ["technology", metrics.technology, "memory"],
            ].map(([key, value, icon]) => (
              <Paper key={key} variant="outlined" sx={{ p: 1.5, borderRadius: 1 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <MaterialSymbol icon={String(icon)} size={22} color="#1565c0" />
                  <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
                    {t(`applicationSummary.metric.${key}`)}
                  </Typography>
                </Box>
                <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5 }}>
                  {String(value)}
                </Typography>
              </Paper>
            ))}
          </Box>

          {relations.length === 0 ? (
            <Alert severity="info">{t("applicationSummary.noRelations")}</Alert>
          ) : (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", lg: "repeat(2, 1fr)" },
                gap: 2,
              }}
            >
              {LAYER_ORDER.map((layer) => {
                const entries = relatedByLayer.get(layer) ?? [];
                if (entries.length === 0) return null;
                return (
                  <Paper key={layer} variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
                    <Typography variant="h6" sx={{ fontWeight: 750, mb: 1 }}>
                      {layer}
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
