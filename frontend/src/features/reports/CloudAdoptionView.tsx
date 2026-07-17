/**
 * Cloud Adoption View
 * Track cloud adoption rates and deployment models across the portfolio.
 * Part of Phase 7: Technology Deployment & Cloud Views.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import LinearProgress from "@mui/material/LinearProgress";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface CloudModel {
  model: string;
  count: number;
  percentage: number;
  color: string;
}

export default function CloudAdoptionView() {
  const { t } = useTranslation(["reports"]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<CloudModel[]>([]);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          const resp = await api.get<{ items: any[] }>("/cards?type=Application&page_size=1000");
          const apps = Array.isArray(resp) ? resp : resp.items || [];
          const grouping = new Map<string, number>();

          // hostingType is the built-in Application field:
          // onPremise | cloudSaaS | cloudPaaS | cloudIaaS | hybrid
          const labels: Record<string, string> = {
            onPremise: "On-Premises",
            cloudSaaS: "Cloud (SaaS)",
            cloudPaaS: "Cloud (PaaS)",
            cloudIaaS: "Cloud (IaaS)",
            hybrid: "Hybrid",
          };
          apps.forEach((app) => {
            const raw = app.attributes?.hostingType;
            const model = labels[raw] || raw || "Unspecified";
            grouping.set(model, (grouping.get(model) || 0) + 1);
          });

          const total = apps.length;
          const modelList = Array.from(grouping.entries()).map(([model, count]) => ({
            model,
            count,
            percentage: Math.round((count / total) * 100),
            color: model.toLowerCase().includes("cloud") ? "#2196f3" : model.toLowerCase().includes("hybrid") ? "#ff9800" : "#4caf50",
          }));

          setModels(modelList.sort((a, b) => b.count - a.count));
        } catch (err) {
          setError("Failed to load cloud adoption data");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const cloudCount = useMemo(() => models.reduce((sum, m) => (m.model.toLowerCase().includes("cloud") ? sum + m.count : sum), 0), [models]);
  const total = useMemo(() => models.reduce((sum, m) => sum + m.count, 0), [models]);

  return (
    <ReportShell title={t("cloudAdoption.title", "Cloud Adoption")} icon="cloud">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("cloudAdoption.subtitle", "Analyze deployment models and cloud migration progress.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && models.length === 0 && !error && <Alert severity="info">{t("cloudAdoption.empty", "No applications found.")}</Alert>}

      {!loading && models.length > 0 && (
        <>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {cloudCount}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("cloudAdoption.metric.cloud", "Cloud Applications")}
              </Typography>
              {total > 0 && (
                <Box sx={{ mt: 1 }}>
                  <LinearProgress variant="determinate" value={(cloudCount / total) * 100} />
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: "block" }}>
                    {Math.round((cloudCount / total) * 100)}% adoption
                  </Typography>
                </Box>
              )}
            </Paper>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("cloudAdoption.metric.total", "Total Applications")}
              </Typography>
            </Paper>
          </Box>

          <Paper variant="outlined" sx={{ overflow: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: "#fafafa" }}>
                  <TableCell sx={{ fontWeight: 700 }}>{t("cloudAdoption.col.model", "Deployment Model")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100 }}>{t("cloudAdoption.col.count", "Count")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 200 }}>{t("cloudAdoption.col.distribution", "Distribution")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 80, textAlign: "right" }}>{t("cloudAdoption.col.percentage", "%")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {models.map((model) => (
                  <TableRow key={model.model} hover>
                    <TableCell>
                      <Chip size="small" label={model.model} sx={{ backgroundColor: model.color, color: "white" }} />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {model.count}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Box sx={{ flex: 1, height: 20, backgroundColor: "#f0f0f0", borderRadius: 1, overflow: "hidden" }}>
                          <Box sx={{ height: "100%", backgroundColor: model.color, width: `${model.percentage}%` }} />
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell sx={{ textAlign: "right" }}>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {model.percentage}%
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </>
      )}
    </ReportShell>
  );
}
