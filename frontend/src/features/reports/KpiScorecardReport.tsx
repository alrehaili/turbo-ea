/**
 * KpiScorecardReport — NORA PRM scorecard: every KPI card with baseline,
 * target and current values and a computed RAG status.
 * [FORK FEATURE] — noraPlan.md WP4.2.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { api } from "@/api/client";
import { STATUS_COLORS } from "@/theme/tokens";
import type { Card } from "@/types";

type Rag = "green" | "amber" | "red" | "none";

/** RAG from progress between baseline and target (direction-aware). */
function ragFor(card: Card): { rag: Rag; progress: number | null } {
  const a = card.attributes ?? {};
  const baseline = Number(a.baselineValue);
  const target = Number(a.targetValue);
  const current = Number(a.currentValue);
  if ([baseline, target, current].some((v) => Number.isNaN(v)) || baseline === target) {
    return { rag: "none", progress: null };
  }
  const progress = Math.round(((current - baseline) / (target - baseline)) * 100);
  if (progress >= 90) return { rag: "green", progress };
  if (progress >= 50) return { rag: "amber", progress };
  return { rag: "red", progress };
}

const RAG_COLOR: Record<Rag, string> = {
  green: STATUS_COLORS.success,
  amber: STATUS_COLORS.warning,
  red: STATUS_COLORS.error,
  none: STATUS_COLORS.neutral,
};

export default function KpiScorecardReport() {
  const { t } = useTranslation(["reports", "common"]);
  const [kpis, setKpis] = useState<Card[] | null>(null);

  useEffect(() => {
    api
      .get<{ items: Card[] }>("/cards?type=KPI&page_size=10000")
      .then((res) => setKpis(res.items))
      .catch(() => setKpis([]));
  }, []);

  if (!kpis) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        {t("kpiScorecard.title")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("kpiScorecard.subtitle")}
      </Typography>
      {kpis.length === 0 ? (
        <Alert severity="info">{t("kpiScorecard.empty")}</Alert>
      ) : (
        <Paper variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>{t("kpiScorecard.colKpi")}</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>{t("kpiScorecard.colUnit")}</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  {t("kpiScorecard.colBaseline")}
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  {t("kpiScorecard.colCurrent")}
                </TableCell>
                <TableCell align="right" sx={{ fontWeight: 700 }}>
                  {t("kpiScorecard.colTarget")}
                </TableCell>
                <TableCell sx={{ fontWeight: 700 }}>{t("kpiScorecard.colProgress")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {kpis.map((kpi) => {
                const a = kpi.attributes ?? {};
                const { rag, progress } = ragFor(kpi);
                return (
                  <TableRow key={kpi.id} hover>
                    <TableCell>
                      <Link component={RouterLink} to={`/cards/${kpi.id}`} underline="hover">
                        {kpi.name}
                      </Link>
                    </TableCell>
                    <TableCell>{String(a.unit ?? "—")}</TableCell>
                    <TableCell align="right">{String(a.baselineValue ?? "—")}</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>
                      {String(a.currentValue ?? "—")}
                    </TableCell>
                    <TableCell align="right">{String(a.targetValue ?? "—")}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={progress === null ? "—" : `${progress}%`}
                        sx={{ bgcolor: RAG_COLOR[rag], color: "#fff", minWidth: 64 }}
                      />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Box>
  );
}
