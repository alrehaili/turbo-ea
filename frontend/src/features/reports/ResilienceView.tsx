import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import ReportShell from "./ReportShell";
import MetricCard from "./MetricCard";
import { api } from "@/api/client";

interface CriticalService {
  id: string;
  name: string;
  type: string;
  criticality: string | null;
  rto: string | null;
  rpo: string | null;
  recovery_tier: string | null;
  chain_size: number;
}
interface Spof {
  id: string;
  name: string;
  type: string;
  layer: string;
  is_supplier: boolean;
  concentration: number;
  dependents: string[];
}
interface Gap {
  id: string;
  name: string;
  missing: string[];
  risk_id: string | null;
  risk_reference: string | null;
}
interface ResilienceData {
  summary: {
    critical_services: number;
    spof_count: number;
    supplier_spofs: number;
    rto_rpo_gaps: number;
  };
  critical_services: CriticalService[];
  spofs: Spof[];
  rto_rpo_gaps: Gap[];
}

export default function ResilienceView() {
  const { t } = useTranslation(["reports", "common"]);
  const chartRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<ResilienceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [promoting, setPromoting] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.get<ResilienceData>("/reports/resilience"));
    } finally {
      setLoading(false);
    }
  }, []);

  const promoteGap = useCallback(
    async (cardId: string) => {
      setPromoting(cardId);
      try {
        await api.post(`/risks/promote/resilience/${cardId}`, {});
        await load();
      } finally {
        setPromoting(null);
      }
    },
    [load],
  );

  useEffect(() => {
    load();
  }, [load]);

  return (
    <ReportShell
      title={t("resilience.title")}
      icon="health_and_safety"
      iconColor="#b71c1c"
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
            <MetricCard
              label={t("resilience.criticalServices")}
              value={data.summary.critical_services}
              icon="emergency"
            />
            <MetricCard
              label={t("resilience.spofs")}
              value={data.summary.spof_count}
              icon="warning"
              color="#d32f2f"
            />
            <MetricCard
              label={t("resilience.supplierSpofs")}
              value={data.summary.supplier_spofs}
              icon="store"
              color="#ed6c02"
            />
            <MetricCard
              label={t("resilience.rtoRpoGaps")}
              value={data.summary.rto_rpo_gaps}
              icon="timer_off"
              color={data.summary.rto_rpo_gaps > 0 ? "#d32f2f" : undefined}
            />
          </Box>

          {/* SPOFs */}
          <Paper variant="outlined" sx={{ mb: 3 }}>
            <Box sx={{ px: 2, py: 1, bgcolor: "action.hover" }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {t("resilience.spofHeader")}
              </Typography>
            </Box>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("resilience.colNode")}</TableCell>
                  <TableCell>{t("resilience.colLayer")}</TableCell>
                  <TableCell align="center">{t("resilience.colConcentration")}</TableCell>
                  <TableCell>{t("resilience.colDependents")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.spofs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} align="center" sx={{ py: 4, color: "text.secondary" }}>
                      {t("resilience.noSpofs")}
                    </TableCell>
                  </TableRow>
                ) : (
                  data.spofs.map((s) => (
                    <TableRow key={s.id} hover>
                      <TableCell>
                        <Box
                          component="a"
                          href={`/cards/${s.id}`}
                          sx={{ color: "primary.main", textDecoration: "none" }}
                        >
                          {s.name}
                        </Box>
                        {s.is_supplier && (
                          <Chip size="small" label={t("resilience.supplier")} sx={{ ml: 1 }} />
                        )}
                      </TableCell>
                      <TableCell>{s.layer}</TableCell>
                      <TableCell align="center">
                        <Chip size="small" color="error" label={s.concentration} />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {s.dependents.join(", ")}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Paper>

          {/* Critical services */}
          <Paper variant="outlined">
            <Box sx={{ px: 2, py: 1, bgcolor: "action.hover" }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {t("resilience.criticalHeader")}
              </Typography>
            </Box>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("resilience.colService")}</TableCell>
                  <TableCell>{t("resilience.colRto")}</TableCell>
                  <TableCell>{t("resilience.colRpo")}</TableCell>
                  <TableCell>{t("resilience.colRecoveryTier")}</TableCell>
                  <TableCell align="center">{t("resilience.colChain")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.critical_services.map((c) => (
                  <TableRow key={c.id} hover>
                    <TableCell>
                      <Box
                        component="a"
                        href={`/cards/${c.id}`}
                        sx={{ color: "primary.main", textDecoration: "none" }}
                      >
                        {c.name}
                      </Box>
                    </TableCell>
                    <TableCell>
                      {c.rto || <Chip size="small" color="warning" label={t("resilience.missing")} />}
                    </TableCell>
                    <TableCell>
                      {c.rpo || <Chip size="small" color="warning" label={t("resilience.missing")} />}
                    </TableCell>
                    <TableCell>{c.recovery_tier || "—"}</TableCell>
                    <TableCell align="center">{c.chain_size}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          {/* RTO/RPO coverage gaps */}
          <Paper variant="outlined" sx={{ mb: 3 }}>
            <Box sx={{ px: 2, py: 1, bgcolor: "action.hover" }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {t("resilience.gapsHeader")}
              </Typography>
            </Box>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("resilience.colService")}</TableCell>
                  <TableCell>{t("resilience.colMissing")}</TableCell>
                  <TableCell align="right">{t("resilience.colAction")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.rto_rpo_gaps.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={3} align="center" sx={{ py: 4, color: "text.secondary" }}>
                      {t("resilience.noGaps")}
                    </TableCell>
                  </TableRow>
                ) : (
                  data.rto_rpo_gaps.map((g) => (
                    <TableRow key={g.id} hover>
                      <TableCell>
                        <Box
                          component="a"
                          href={`/cards/${g.id}`}
                          sx={{ color: "primary.main", textDecoration: "none" }}
                        >
                          {g.name}
                        </Box>
                      </TableCell>
                      <TableCell>
                        {g.missing.map((m) => (
                          <Chip
                            key={m}
                            size="small"
                            color="warning"
                            label={m.toUpperCase()}
                            sx={{ mr: 0.5 }}
                          />
                        ))}
                      </TableCell>
                      <TableCell align="right">
                        {g.risk_id ? (
                          <Button
                            size="small"
                            variant="text"
                            href={`/grc/risks/${g.risk_id}`}
                          >
                            {t("resilience.openRisk", { ref: g.risk_reference })}
                          </Button>
                        ) : (
                          <Button
                            size="small"
                            variant="outlined"
                            disabled={promoting === g.id}
                            onClick={() => promoteGap(g.id)}
                          >
                            {t("resilience.createRisk")}
                          </Button>
                        )}
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
