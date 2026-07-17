/**
 * Gap Summary Report
 * Identifies and summarizes gaps between current and target architectures.
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
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { SEVERITY_COLORS } from "@/theme/tokens";
import ReportShell from "./ReportShell";

interface Gap {
  id: string;
  element: string;
  type: string;
  gapType: "create" | "replace" | "modify" | "retire";
  priority: "low" | "medium" | "high" | "critical";
  linkedInitiatives: number;
}

export default function GapSummaryReport() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          setError(null);
          // WP2.4 gap-analysis: buckets every architecture-state delta with initiative traceability
          const report = await api.get<{
            buckets: Record<string, any[]>;
            untraceable: any[];
          }>("/reports/gap-analysis");

          // Priority derived from change semantics: untraceable retire/replace
          // gaps are the riskiest; traced create/modify the least.
          const priorityFor = (bucket: string, initiatives: number): Gap["priority"] => {
            if (initiatives === 0) return bucket === "retire" || bucket === "replace" ? "critical" : "high";
            return bucket === "retire" || bucket === "replace" ? "medium" : "low";
          };

          const rows: Gap[] = [];
          for (const bucket of ["create", "replace", "modify", "retire"] as const) {
            for (const row of report.buckets?.[bucket] || []) {
              const initiatives = (row.initiatives || []).length;
              rows.push({
                id: row.id,
                element: row.name,
                type: row.type,
                gapType: bucket,
                priority: priorityFor(bucket, initiatives),
                linkedInitiatives: initiatives,
              });
            }
          }
          setGaps(rows);
        } catch (err) {
          console.error("Failed to fetch gaps:", err);
          setError("Failed to load gap analysis");
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
    return gaps.filter((g) => g.element.toLowerCase().includes(q) || g.type.toLowerCase().includes(q));
  }, [gaps, search]);

  const stats = useMemo(() => {
    const total = gaps.length;
    const critical = gaps.filter((g) => g.priority === "critical").length;
    const high = gaps.filter((g) => g.priority === "high").length;
    const missing = gaps.filter((g) => g.gapType === "create").length;
    return { total, critical, high, missing };
  }, [gaps]);

  const priorityColor = (priority: Gap["priority"]) => {
    switch (priority) {
      case "critical":
        return SEVERITY_COLORS.critical;
      case "high":
        return SEVERITY_COLORS.high;
      case "medium":
        return SEVERITY_COLORS.medium;
      default:
        return SEVERITY_COLORS.low;
    }
  };

  return (
    <ReportShell title={t("gapSummary.title", "Gap Summary")} icon="warning">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("gapSummary.subtitle", "Identify gaps between current and target architectures that require initiatives to close.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && gaps.length === 0 && !error && <Alert severity="success">{t("gapSummary.noGaps", "No gaps identified. Architecture is aligned with target state.")}</Alert>}

      {!loading && gaps.length > 0 && (
        <>
          {/* KPI Cards */}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(4, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("gapSummary.metric.total", "Total Gaps")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: SEVERITY_COLORS.critical }}>
                {stats.critical}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("gapSummary.metric.critical", "Critical")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: SEVERITY_COLORS.high }}>
                {stats.high}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("gapSummary.metric.high", "High")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: SEVERITY_COLORS.medium }}>
                {stats.missing}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("gapSummary.metric.missing", "Missing")}
              </Typography>
            </Paper>
          </Box>

          {/* Search */}
          <TextField
            size="small"
            placeholder={t("gapSummary.search", "Search gaps…")}
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

          {/* Gaps Table */}
          <Paper variant="outlined" sx={{ overflow: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: "#fafafa" }}>
                  <TableCell sx={{ fontWeight: 700 }}>{t("gapSummary.col.element", "Element")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100 }}>{t("gapSummary.col.type", "Type")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120 }}>{t("gapSummary.col.gapType", "Gap Type")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 110 }}>{t("gapSummary.col.priority", "Priority")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("gapSummary.col.initiatives", "Initiatives")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((gap) => (
                  <TableRow key={gap.id} hover sx={{ backgroundColor: gap.priority === "critical" ? "rgba(244, 67, 54, 0.05)" : undefined }}>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {gap.element}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{gap.type}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={gap.gapType} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={gap.priority} sx={{ backgroundColor: priorityColor(gap.priority), color: "white" }} />
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      {gap.linkedInitiatives > 0 ? (
                        <Chip size="small" label={gap.linkedInitiatives} variant="outlined" />
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

          {filtered.length === 0 && search && <Alert severity="info" sx={{ mt: 2 }}>{t("gapSummary.noResults", "No gaps found.")}</Alert>}
        </>
      )}
    </ReportShell>
  );
}
