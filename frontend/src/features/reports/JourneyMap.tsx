/**
 * Journey Map
 * Visualize customer/beneficiary journeys with stages and touchpoints.
 * Part of Phase 9: Beneficiary Experience Views.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import LinearProgress from "@mui/material/LinearProgress";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface JourneyStage {
  id: string;
  name: string;
  sequence: number;
  touchpoints: string[];
  satisfaction: number;
  painLevel: number;
}

interface Journey {
  id: string;
  name: string;
  persona: string;
  stages: JourneyStage[];
}

export default function JourneyMap() {
  const { t } = useTranslation(["reports"]);
  const [journeys, setJourneys] = useState<Journey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          const response = await api.get<{ items: any[] }>("/cards?type=Journey&page_size=200");
          const cards = Array.isArray(response) ? response : response.items || [];

          const journeysData: Journey[] = cards.map((c) => {
            const stages = c.attributes?.stages ? c.attributes.stages.split("→").map((s: string, i: number) => ({
              id: String(i + 1),
              name: s.trim(),
              sequence: i + 1,
              touchpoints: c.attributes?.touchpoints ? (typeof c.attributes.touchpoints === "string" ? c.attributes.touchpoints.split(",").slice(0, 3).map((t: string) => t.trim()) : []) : [],
              satisfaction: ["veryLow", "low", "medium", "high", "veryHigh"].indexOf(c.attributes?.satisfaction || "medium") * 25,
              painLevel: 100 - (["veryLow", "low", "medium", "high", "veryHigh"].indexOf(c.attributes?.satisfaction || "medium") * 25),
            })) : [];

            return {
              id: c.id,
              name: c.name,
              persona: c.subtype || "Generic",
              stages: stages.length > 0 ? stages : [
                { id: "1", name: "Initiation", sequence: 1, touchpoints: [], satisfaction: 50, painLevel: 50 },
              ],
            };
          });

          setJourneys(journeysData);
        } catch (err) {
          setError("Failed to load journeys");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  return (
    <ReportShell title={t("journeyMap.title", "Journey Map")} icon="journey">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("journeyMap.subtitle", "Visualize beneficiary journeys with stages, touchpoints, and satisfaction metrics.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && journeys.length === 0 && !error && (
        <Alert severity="info">{t("journeyMap.empty", "No journeys found. Create Journey cards to map beneficiary experiences.")}</Alert>
      )}

      {!loading && journeys.length > 0 && (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {journeys.map((journey) => (
            <Paper key={journey.id} sx={{ p: 3, backgroundColor: "#fafafa" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
                {journey.name}
              </Typography>
              <Chip size="small" label={journey.persona} variant="outlined" sx={{ mb: 2 }} />

              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(5, 1fr)" }, gap: 2 }}>
                {journey.stages.map((stage) => (
                  <Card key={stage.id} sx={{ backgroundColor: "white" }}>
                    <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                        {stage.name}
                      </Typography>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="caption" color="text.secondary">
                          Satisfaction
                        </Typography>
                        <LinearProgress variant="determinate" value={stage.satisfaction} sx={{ my: 0.5 }} />
                        <Typography variant="caption" sx={{ fontWeight: 600 }}>
                          {stage.satisfaction}%
                        </Typography>
                      </Box>

                      <Box sx={{ mb: 2 }}>
                        <Typography variant="caption" color="text.secondary">
                          Pain Level
                        </Typography>
                        <LinearProgress
                          variant="determinate"
                          value={stage.painLevel}
                          sx={{
                            my: 0.5,
                            "& .MuiLinearProgress-bar": { backgroundColor: "#f44336" },
                          }}
                        />
                        <Typography variant="caption" sx={{ fontWeight: 600 }}>
                          {stage.painLevel}%
                        </Typography>
                      </Box>

                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                        Touchpoints:
                      </Typography>
                      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                        {stage.touchpoints.map((tp, idx) => (
                          <Chip key={idx} size="small" label={tp} variant="outlined" sx={{ fontSize: "0.65rem" }} />
                        ))}
                      </Box>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            </Paper>
          ))}
        </Box>
      )}
    </ReportShell>
  );
}
