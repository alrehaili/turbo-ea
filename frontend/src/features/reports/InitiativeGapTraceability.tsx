/**
 * Initiative-to-Gap Traceability
 * Links initiatives and programs to the gaps they close.
 * Part of Phase 5: Current, Target & Transition Views.
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
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import InputAdornment from "@mui/material/InputAdornment";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface InitiativeGapLink {
  initiativeId: string;
  initiativeName: string;
  gapCount: number;
  status: string;
  priority: string;
  linkedGaps: string[];
}

export default function InitiativeGapTraceability() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [links, setLinks] = useState<InitiativeGapLink[]>([]);
  const [totalGapCount, setTotalGapCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          setError(null);
          // Invert the WP2.4 gap-analysis report: per initiative, which gaps
          // (changed cards) does it deliver?
          const report = await api.get<{
            buckets: Record<string, any[]>;
            untraceable: any[];
          }>("/reports/gap-analysis");

          const byInitiative = new Map<string, InitiativeGapLink>();
          let gapTotal = 0;
          for (const bucket of ["create", "replace", "modify", "retire"]) {
            for (const gap of report.buckets?.[bucket] || []) {
              gapTotal += 1;
              for (const ini of gap.initiatives || []) {
                let entry = byInitiative.get(ini.id);
                if (!entry) {
                  entry = {
                    initiativeId: ini.id,
                    initiativeName: ini.name,
                    gapCount: 0,
                    status: ini.transition_role || "delivers",
                    priority: "medium",
                    linkedGaps: [],
                  };
                  byInitiative.set(ini.id, entry);
                }
                entry.gapCount += 1;
                entry.linkedGaps.push(gap.name);
              }
            }
          }
          // Priority reflects load: initiatives carrying many gaps are the
          // schedule-critical ones.
          for (const entry of byInitiative.values()) {
            entry.priority = entry.gapCount >= 5 ? "critical" : entry.gapCount >= 3 ? "high" : "medium";
          }
          setTotalGapCount(gapTotal);
          setLinks(Array.from(byInitiative.values()).sort((a, b) => b.gapCount - a.gapCount));
        } catch (err) {
          console.error("Failed to fetch initiative-gap traceability:", err);
          setError("Failed to load initiative data");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return links.filter((l) => l.initiativeName.toLowerCase().includes(q));
  }, [links, search]);

  const stats = useMemo(() => {
    const total = links.length;
    const linked = links.filter((l) => l.gapCount > 0).length;
    return { total, linked, totalGaps: totalGapCount };
  }, [links, totalGapCount]);

  return (
    <ReportShell title={t("initiativeGapTraceability.title", "Initiative-to-Gap Traceability")} icon="connect_without_contact">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("initiativeGapTraceability.subtitle", "Track which initiatives are addressing which gaps in the transition roadmap.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && links.length === 0 && !error && (
        <Alert severity="info">{t("initiativeGapTraceability.empty", "No initiatives linked to gaps yet.")}</Alert>
      )}

      {!loading && links.length > 0 && (
        <>
          {/* KPI Cards */}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("initiativeGapTraceability.metric.total", "Initiatives")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                {stats.linked}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("initiativeGapTraceability.metric.linked", "Linked to Gaps")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "success.main" }}>
                {stats.totalGaps}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("initiativeGapTraceability.metric.totalGaps", "Total Gaps")}
              </Typography>
            </Paper>
          </Box>

          {/* Search */}
          <TextField
            size="small"
            placeholder={t("initiativeGapTraceability.search", "Search initiatives…")}
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

          {/* Traceability Table */}
          <Paper variant="outlined" sx={{ overflow: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: "#fafafa" }}>
                  <TableCell sx={{ fontWeight: 700 }}>{t("initiativeGapTraceability.col.initiative", "Initiative")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100 }}>{t("initiativeGapTraceability.col.status", "Status")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100 }}>{t("initiativeGapTraceability.col.priority", "Priority")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("initiativeGapTraceability.col.gaps", "Gaps")}</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>{t("initiativeGapTraceability.col.linkedGaps", "Linked Gaps")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((link) => (
                  <TableRow key={link.initiativeId} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {link.initiativeName}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={link.status} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={link.priority} variant="outlined" />
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      {link.gapCount > 0 ? (
                        <Chip size="small" label={link.gapCount} color="primary" variant="outlined" />
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          —
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {link.linkedGaps.length > 0 ? (
                        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                          {link.linkedGaps.slice(0, 3).map((gap, idx) => (
                            <Chip key={idx} size="small" label={gap.substring(0, 8)} />
                          ))}
                          {link.linkedGaps.length > 3 && <Typography variant="caption">+{link.linkedGaps.length - 3}</Typography>}
                        </Box>
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          —
                        </Typography>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          {filtered.length === 0 && search && <Alert severity="info" sx={{ mt: 2 }}>{t("initiativeGapTraceability.noResults", "No initiatives found.")}</Alert>}
        </>
      )}
    </ReportShell>
  );
}
