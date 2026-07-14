/**
 * ServiceTraceabilityReport — "how is this service delivered": everything
 * reachable from a Government Service within two relation hops, grouped by
 * EA layer. The primary NORA/DGA service-delivery view.
 *
 * [FORK FEATURE] — noraPlan.md WP3.4.
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useSearchParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import CardPicker, { type CardOption } from "@/components/CardPicker";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { useTypeLabel } from "@/hooks/useResolveLabel";
import { useMetamodel } from "@/hooks/useMetamodel";
import { LAYER_COLORS } from "@/theme";

interface TraceCard {
  id: string;
  name: string;
  type: string;
  architecture_state: string;
  hops: number;
}

interface TraceData {
  root: { id: string; name: string; type: string };
  layers: { category: string; cards: TraceCard[] }[];
  other: TraceCard[];
}

export default function ServiceTraceabilityReport() {
  const { t } = useTranslation(["reports", "common"]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [service, setService] = useState<CardOption | null>(null);
  const [data, setData] = useState<TraceData | null>(null);
  const [loading, setLoading] = useState(false);
  const { types } = useMetamodel();
  const typeLabel = useTypeLabel();

  const load = useCallback(async (cardId: string) => {
    setLoading(true);
    try {
      setData(await api.get<TraceData>(`/reports/service-traceability?card_id=${cardId}`));
    } finally {
      setLoading(false);
    }
  }, []);

  // Deep-link: ?card_id=… (e.g. from a GovService card).
  useEffect(() => {
    const cardId = searchParams.get("card_id");
    if (cardId && !data && !loading) {
      load(cardId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onPick = (option: CardOption | null) => {
    setService(option);
    if (option) {
      setSearchParams({ card_id: option.id }, { replace: true });
      load(option.id);
    } else {
      setData(null);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        {t("serviceTraceability.title")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("serviceTraceability.subtitle")}
      </Typography>

      <Box sx={{ maxWidth: 480, mb: 3 }}>
        <CardPicker
          types="GovService"
          value={service}
          onChange={onPick}
          label={t("serviceTraceability.pickService")}
        />
      </Box>

      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {data && !loading && (
        <>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
            <MaterialSymbol icon="assured_workload" size={22} color="#00838f" />
            <Typography variant="h6">
              <Link component={RouterLink} to={`/cards/${data.root.id}`} underline="hover">
                {data.root.name}
              </Link>
            </Typography>
          </Box>

          {data.layers.every((l) => l.cards.length === 0) && data.other.length === 0 ? (
            <Alert severity="info">{t("serviceTraceability.empty")}</Alert>
          ) : (
            <Box
              sx={{
                display: "grid",
                gap: 2,
                gridTemplateColumns: { xs: "1fr", md: "repeat(4, 1fr)" },
              }}
            >
              {data.layers.map((layer) => (
                <Paper key={layer.category} variant="outlined" sx={{ overflow: "hidden" }}>
                  <Box
                    sx={{
                      px: 1.5,
                      py: 1,
                      bgcolor:
                        (LAYER_COLORS as Record<string, string>)[layer.category] ?? "#607d8b",
                      color: "#fff",
                    }}
                  >
                    <Typography variant="subtitle2">{layer.category}</Typography>
                  </Box>
                  <Box sx={{ p: 1.5, display: "flex", flexDirection: "column", gap: 1 }}>
                    {layer.cards.length === 0 ? (
                      <Typography variant="caption" color="text.disabled">
                        —
                      </Typography>
                    ) : (
                      layer.cards.map((c) => {
                        const typeDef = types.find((ty) => ty.key === c.type);
                        return (
                          <Chip
                            key={c.id}
                            size="small"
                            variant="outlined"
                            component={RouterLink}
                            to={`/cards/${c.id}`}
                            clickable
                            sx={{
                              justifyContent: "flex-start",
                              ...(c.architecture_state === "target" && {
                                borderStyle: "dashed",
                                borderColor: "#2e7d32",
                              }),
                            }}
                            label={`${c.name} · ${typeDef ? typeLabel(typeDef) : c.type}${
                              c.hops > 1 ? ` (${t("serviceTraceability.indirect")})` : ""
                            }`}
                          />
                        );
                      })
                    )}
                  </Box>
                </Paper>
              ))}
            </Box>
          )}
        </>
      )}
    </Box>
  );
}
