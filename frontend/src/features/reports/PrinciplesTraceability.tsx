/**
 * Principles & Standards Traceability
 * Link EA principles and standards to applications for traceability.
 * Part of Phase 8: Standards & Security Traceability.
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
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface PrincipleTrace {
  id: string;
  principle: string;
  statement: string;
  applicableApps: number;
  alignedApps: number;
  alignmentRate: number;
}

export default function PrinciplesTraceability() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [traces, setTraces] = useState<PrincipleTrace[]>([]);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          // Real EA principles (Admin → Principles / GRC Governance) — alignment
          // is not assessed per application yet, so those cells render "—"
          // instead of an invented percentage.
          const [appResp, principles] = await Promise.all([
            api.get<{ items: any[]; total?: number }>("/cards?type=Application&page_size=1"),
            api.get<any[]>("/metamodel/principles"),
          ]);
          const totalApps = Array.isArray(appResp) ? appResp.length : appResp.total || 0;

          const rows: PrincipleTrace[] = principles.map((p) => ({
            id: p.id,
            principle: p.title || p.name,
            statement: p.statement || "",
            applicableApps: totalApps,
            alignedApps: -1,
            alignmentRate: -1,
          }));
          setTraces(rows);
        } catch (err) {
          setError("Failed to load principles traceability");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const filtered = useMemo(
    () => traces.filter((t) => t.principle.toLowerCase().includes(search.toLowerCase()) || t.statement.toLowerCase().includes(search.toLowerCase())),
    [traces, search]
  );

  const stats = useMemo(() => {
    const total = traces.length;
    const assessed = traces.filter((t) => t.alignmentRate >= 0);
    const avgAlignment = assessed.length
      ? Math.round(assessed.reduce((sum, t) => sum + t.alignmentRate, 0) / assessed.length)
      : null;
    const wellAligned = assessed.filter((t) => t.alignmentRate >= 75).length;
    return { total, avgAlignment, wellAligned };
  }, [traces]);

  return (
    <ReportShell title={t("principlesTraceability.title", "Principles & Standards Traceability")} icon="rule_folder">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("principlesTraceability.subtitle", "Track how well applications align with enterprise architecture principles.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && traces.length === 0 && !error && <Alert severity="info">{t("principlesTraceability.empty", "No principles found.")}</Alert>}

      {!loading && traces.length > 0 && (
        <>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("principlesTraceability.metric.total", "Principles")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#4caf50" }}>
                {stats.wellAligned}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("principlesTraceability.metric.wellAligned", "Well Aligned (75%+)")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                {stats.avgAlignment === null ? "—" : `${stats.avgAlignment}%`}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("principlesTraceability.metric.average", "Average Alignment")}
              </Typography>
            </Paper>
          </Box>

          <TextField
            size="small"
            placeholder={t("principlesTraceability.search", "Search principles…")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <MaterialSymbol icon="search" size={18} color="disabled" />
                  </InputAdornment>
                ),
              },
            }}
            sx={{ mb: 2, maxWidth: 360 }}
          />

          <Paper variant="outlined" sx={{ overflow: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: "#fafafa" }}>
                  <TableCell sx={{ fontWeight: 700, minWidth: 150 }}>{t("principlesTraceability.col.principle", "Principle")}</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>{t("principlesTraceability.col.statement", "Statement")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100 }}>{t("principlesTraceability.col.applicable", "Applicable")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100 }}>{t("principlesTraceability.col.aligned", "Aligned")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("principlesTraceability.col.alignment", "Alignment")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((trace) => (
                  <TableRow key={trace.id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {trace.principle}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{trace.statement}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={trace.applicableApps} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      {trace.alignedApps >= 0 ? (
                        <Chip size="small" label={trace.alignedApps} sx={{ backgroundColor: "#4caf50", color: "white" }} />
                      ) : (
                        <Typography variant="caption" color="text.secondary">—</Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      {trace.alignmentRate >= 0 ? (
                        <Chip
                          size="small"
                          label={`${trace.alignmentRate}%`}
                          sx={{
                            backgroundColor: trace.alignmentRate >= 75 ? "#4caf50" : trace.alignmentRate >= 50 ? "#ff9800" : "#f44336",
                            color: "white",
                          }}
                        />
                      ) : (
                        <Typography variant="caption" color="text.secondary">—</Typography>
                      )}
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
