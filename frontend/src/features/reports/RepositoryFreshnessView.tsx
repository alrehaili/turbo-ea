import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import CircularProgress from "@mui/material/CircularProgress";
import LinearProgress from "@mui/material/LinearProgress";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import ReportShell from "./ReportShell";
import MetricCard from "./MetricCard";
import { api } from "@/api/client";

interface StaleRecord {
  id: string;
  name: string;
  type: string;
  owner: string | null;
  last_confirmed_at: string | null;
  source_system: string | null;
  confidence: string | null;
  data_quality: number;
}

interface TypeBucket {
  type: string;
  total: number;
  stale: number;
}
interface OwnerBucket {
  owner: string;
  total: number;
  stale: number;
}

interface FreshnessData {
  stale_days: number;
  summary: {
    total: number;
    confirmed: number;
    stale: number;
    stale_pct: number;
    dq_issues: number;
  };
  by_source: { source: string; count: number }[];
  by_confidence: Record<string, number>;
  by_type: TypeBucket[];
  by_owner: OwnerBucket[];
  stale_records: StaleRecord[];
}

const STALE_DAY_OPTIONS = [30, 60, 90, 180, 365];

export default function RepositoryFreshnessView() {
  const { t } = useTranslation(["reports", "common"]);
  const chartRef = useRef<HTMLDivElement>(null);
  const [staleDays, setStaleDays] = useState(90);
  const [data, setData] = useState<FreshnessData | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.get<FreshnessData>(`/reports/freshness?stale_days=${staleDays}`));
    } finally {
      setLoading(false);
    }
  }, [staleDays]);

  useEffect(() => {
    load();
  }, [load]);

  const confirmCard = async (id: string) => {
    setConfirming(id);
    try {
      await api.post(`/cards/${id}/confirm`, {});
      await load();
    } finally {
      setConfirming(null);
    }
  };

  const fmtDate = (iso: string | null) =>
    iso ? new Date(iso).toLocaleDateString() : t("freshness.neverConfirmed");

  const toolbar = (
    <TextField
      select
      size="small"
      label={t("freshness.staleThreshold")}
      value={staleDays}
      onChange={(e) => setStaleDays(Number(e.target.value))}
      sx={{ width: 170 }}
    >
      {STALE_DAY_OPTIONS.map((d) => (
        <MenuItem key={d} value={d}>
          {t("freshness.daysOption", { count: d })}
        </MenuItem>
      ))}
    </TextField>
  );

  return (
    <ReportShell
      title={t("freshness.title")}
      icon="fact_check"
      iconColor="#027446"
      toolbar={toolbar}
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
            <MetricCard label={t("freshness.totalCards")} value={data.summary.total} icon="inventory_2" />
            <MetricCard
              label={t("freshness.confirmed")}
              value={data.summary.confirmed}
              icon="check_circle"
              color="#33cc58"
            />
            <MetricCard
              label={t("freshness.stale")}
              value={data.summary.stale}
              icon="schedule"
              color="#ed6c02"
              subtitle={`${data.summary.stale_pct}%`}
            />
            <MetricCard
              label={t("freshness.dqIssues")}
              value={data.summary.dq_issues}
              icon="error"
              color="#d32f2f"
            />
          </Box>

          {/* Source coverage + confidence */}
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 3 }}>
            <Paper variant="outlined" sx={{ p: 2, flex: "1 1 280px" }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                {t("freshness.bySource")}
              </Typography>
              {data.by_source.map((s) => (
                <Box
                  key={s.source}
                  sx={{ display: "flex", justifyContent: "space-between", py: 0.25 }}
                >
                  <Typography variant="body2">{s.source}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {s.count}
                  </Typography>
                </Box>
              ))}
            </Paper>
            <Paper variant="outlined" sx={{ p: 2, flex: "1 1 280px" }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                {t("freshness.byConfidence")}
              </Typography>
              {Object.entries(data.by_confidence).map(([k, v]) => (
                <Box key={k} sx={{ display: "flex", justifyContent: "space-between", py: 0.25 }}>
                  <Typography variant="body2">
                    {k === "unset" ? t("freshness.confidenceUnset") : t(`freshness.confidence.${k}`, k)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {v}
                  </Typography>
                </Box>
              ))}
            </Paper>
          </Box>

          {/* Ownership coverage */}
          <Paper variant="outlined" sx={{ mb: 3 }}>
            <Box sx={{ px: 2, py: 1, bgcolor: "action.hover" }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {t("freshness.byOwner")}
              </Typography>
            </Box>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("freshness.colOwner")}</TableCell>
                  <TableCell align="right">{t("freshness.colTotal")}</TableCell>
                  <TableCell align="right">{t("freshness.colStale")}</TableCell>
                  <TableCell sx={{ width: 180 }}>{t("freshness.colFreshness")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.by_owner.map((o) => {
                  const freshPct = o.total ? (100 * (o.total - o.stale)) / o.total : 0;
                  return (
                    <TableRow key={o.owner} hover>
                      <TableCell>{o.owner}</TableCell>
                      <TableCell align="right">{o.total}</TableCell>
                      <TableCell align="right">{o.stale}</TableCell>
                      <TableCell>
                        <LinearProgress
                          variant="determinate"
                          value={freshPct}
                          sx={{ height: 6, borderRadius: 3 }}
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Paper>

          {/* Stale-record worklist */}
          <Paper variant="outlined">
            <Box sx={{ px: 2, py: 1, bgcolor: "action.hover" }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {t("freshness.worklist")}
              </Typography>
            </Box>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("freshness.colCard")}</TableCell>
                  <TableCell>{t("freshness.colType")}</TableCell>
                  <TableCell>{t("freshness.colOwner")}</TableCell>
                  <TableCell>{t("freshness.colLastConfirmed")}</TableCell>
                  <TableCell>{t("freshness.colSource")}</TableCell>
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {data.stale_records.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 4, color: "text.secondary" }}>
                      {t("freshness.allFresh")}
                    </TableCell>
                  </TableRow>
                ) : (
                  data.stale_records.map((r) => (
                    <TableRow key={r.id} hover>
                      <TableCell>
                        <Box
                          component="a"
                          href={`/cards/${r.id}`}
                          sx={{ color: "primary.main", textDecoration: "none" }}
                        >
                          {r.name}
                        </Box>
                      </TableCell>
                      <TableCell>{r.type}</TableCell>
                      <TableCell>{r.owner || t("freshness.unassigned")}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={fmtDate(r.last_confirmed_at)}
                          color={r.last_confirmed_at ? "default" : "warning"}
                        />
                      </TableCell>
                      <TableCell>{r.source_system || "—"}</TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          variant="outlined"
                          disabled={confirming === r.id}
                          onClick={() => confirmCard(r.id)}
                        >
                          {t("freshness.confirm")}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Paper>
        </Box>
      ) : null}
    </ReportShell>
  );
}
