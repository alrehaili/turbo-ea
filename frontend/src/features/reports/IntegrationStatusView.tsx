import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import ReportShell from "./ReportShell";
import MetricCard from "./MetricCard";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";

interface ConnRow {
  id: string;
  name: string;
  source_type: string;
  is_active: boolean;
  last_sync_at: string | null;
  last_sync_status: string | null;
  days_since_sync: number | null;
  is_stale: boolean;
  mapped_cards: number;
  pending_changes: number;
}
interface IntegrationStatus {
  summary: {
    connections: number;
    stale_connections: number;
    pending_changes: number;
    mapped_cards: number;
  };
  connections: ConnRow[];
}

export default function IntegrationStatusView() {
  const { t } = useTranslation(["reports", "common"]);
  const chartRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<IntegrationStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.get<IntegrationStatus>("/reports/integration-status"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const fmtDate = (iso: string | null) => (iso ? new Date(iso).toLocaleString() : t("integration.never"));

  return (
    <ReportShell
      title={t("integration.title")}
      icon="sync"
      iconColor="#0288d1"
      hasTableToggle={false}
      chartRef={chartRef}
    >
      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : data ? (
        <Box>
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 3 }}>
            <MetricCard label={t("integration.connections")} value={data.summary.connections} icon="hub" />
            <MetricCard
              label={t("integration.stale")}
              value={data.summary.stale_connections}
              icon="sync_problem"
              color={data.summary.stale_connections > 0 ? "#ed6c02" : undefined}
            />
            <MetricCard
              label={t("integration.pending")}
              value={data.summary.pending_changes}
              icon="pending_actions"
            />
            <MetricCard label={t("integration.mappedCards")} value={data.summary.mapped_cards} icon="link" />
          </Box>

          {data.connections.length === 0 ? (
            <Box sx={{ textAlign: "center", py: 8, color: "text.secondary" }}>
              <MaterialSymbol icon="hub" size={48} />
              <Typography sx={{ mt: 2 }}>{t("integration.emptyState")}</Typography>
            </Box>
          ) : (
            <Paper variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("integration.colSource")}</TableCell>
                    <TableCell>{t("integration.colLastSync")}</TableCell>
                    <TableCell>{t("integration.colStatus")}</TableCell>
                    <TableCell align="right">{t("integration.colMapped")}</TableCell>
                    <TableCell align="right">{t("integration.colPending")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.connections.map((c) => (
                    <TableRow key={c.id} hover>
                      <TableCell>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          <MaterialSymbol icon="cloud_sync" size={16} />
                          {c.name}
                          <Chip size="small" variant="outlined" label={c.source_type} />
                        </Box>
                      </TableCell>
                      <TableCell>{fmtDate(c.last_sync_at)}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          color={c.is_stale ? "warning" : "success"}
                          label={c.is_stale ? t("integration.staleLabel") : t("integration.fresh")}
                        />
                      </TableCell>
                      <TableCell align="right">{c.mapped_cards}</TableCell>
                      <TableCell align="right">
                        {c.pending_changes > 0 ? (
                          <Chip size="small" color="info" label={c.pending_changes} />
                        ) : (
                          "0"
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          )}
        </Box>
      ) : null}
    </ReportShell>
  );
}
