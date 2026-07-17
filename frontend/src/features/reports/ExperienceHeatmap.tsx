/**
 * Experience Heatmap
 * Journey stages × satisfaction/pain metrics visualization.
 * Part of Phase 9: Beneficiary Experience Views.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface JourneyData {
  name: string;
  stages: string;
  satisfaction: string;
}

export default function ExperienceHeatmap() {
  const { t } = useTranslation(["reports"]);
  const [journeys, setJourneys] = useState<JourneyData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          const response = await api.get<{ items: any[] }>("/cards?type=Journey&page_size=100");
          const cards = Array.isArray(response) ? response : response.items || [];

          const journeyData: JourneyData[] = cards.map((c) => ({
            name: c.name,
            stages: c.attributes?.stages || "Initiation",
            satisfaction: c.attributes?.satisfaction || "medium",
          }));

          setJourneys(journeyData);
        } catch (err) {
          setError("Failed to load heatmap data");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const heatmapData = useMemo(() => {
    const stages = ["Initiation", "Planning", "Execution", "Review", "Closure"];
    const satisfactionMap = { veryLow: 20, low: 40, medium: 60, high: 80, veryHigh: 100 };

    // Satisfaction is the card-level rating applied uniformly across the
    // generic stage columns — per-stage scoring is not modeled yet.
    return {
      stages,
      journeys: journeys.map((j) => j.name),
      matrix: journeys.map((journey) => {
        const satisfaction = satisfactionMap[journey.satisfaction as keyof typeof satisfactionMap] || 60;
        return {
          name: journey.name,
          stages: stages.map((stage) => ({
            name: stage,
            satisfaction,
            pain: 100 - satisfaction,
          })),
        };
      }),
    };
  }, [journeys]);

  const getColor = (value: number) => {
    if (value >= 75) return "#4caf50"; // Green
    if (value >= 50) return "#ff9800"; // Orange
    return "#f44336"; // Red
  };

  return (
    <ReportShell title={t("experienceHeatmap.title", "Experience Heatmap")} icon="heatmap">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("experienceHeatmap.subtitle", "Journey stages heatmap showing satisfaction and pain levels.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && (
        <>
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
              {t("experienceHeatmap.satisfaction", "Satisfaction Heatmap")}
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, overflow: "auto" }}>
              <Box sx={{ display: "grid", gridTemplateColumns: `150px repeat(${heatmapData.stages.length}, 100px)`, gap: 1 }}>
                <Box />
                {heatmapData.stages.map((stage) => (
                  <Typography key={stage} variant="caption" sx={{ fontWeight: 700, textAlign: "center" }}>
                    {stage}
                  </Typography>
                ))}

                {heatmapData.matrix.map((journey, idx) => (
                  <Box key={idx} sx={{ gridColumn: "1 / -1", display: "contents" }}>
                    <Typography variant="caption" sx={{ fontWeight: 600, display: "flex", alignItems: "center" }}>
                      {journey.name}
                    </Typography>
                    {journey.stages.map((stage, stageIdx) => (
                      <Box
                        key={stageIdx}
                        sx={{
                          backgroundColor: getColor(stage.satisfaction),
                          borderRadius: 1,
                          p: 1,
                          textAlign: "center",
                          color: "white",
                        }}
                      >
                        <Typography variant="caption" sx={{ fontWeight: 700 }}>
                          {stage.satisfaction}%
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                ))}
              </Box>
            </Paper>
          </Box>

          <Box>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
              {t("experienceHeatmap.pain", "Pain Level Heatmap")}
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, overflow: "auto" }}>
              <Box sx={{ display: "grid", gridTemplateColumns: `150px repeat(${heatmapData.stages.length}, 100px)`, gap: 1 }}>
                <Box />
                {heatmapData.stages.map((stage) => (
                  <Typography key={stage} variant="caption" sx={{ fontWeight: 700, textAlign: "center" }}>
                    {stage}
                  </Typography>
                ))}

                {heatmapData.matrix.map((journey, idx) => (
                  <Box key={idx} sx={{ gridColumn: "1 / -1", display: "contents" }}>
                    <Typography variant="caption" sx={{ fontWeight: 600, display: "flex", alignItems: "center" }}>
                      {journey.name}
                    </Typography>
                    {journey.stages.map((stage, stageIdx) => (
                      <Box
                        key={stageIdx}
                        sx={{
                          backgroundColor: stage.pain > 70 ? "#f44336" : stage.pain > 40 ? "#ff9800" : "#4caf50",
                          borderRadius: 1,
                          p: 1,
                          textAlign: "center",
                          color: "white",
                        }}
                      >
                        <Typography variant="caption" sx={{ fontWeight: 700 }}>
                          {stage.pain}%
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                ))}
              </Box>
            </Paper>
          </Box>
        </>
      )}
    </ReportShell>
  );
}
