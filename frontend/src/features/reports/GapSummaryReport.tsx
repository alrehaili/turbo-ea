/**
 * Gap Summary Report
 * Identifies and summarizes gaps between current and target architectures.
 * Part of Phase 5: Current, Target & Transition Views.
 */

import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import { alpha } from "@mui/material/styles";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { SEVERITY_COLORS, STATUS_COLORS } from "@/theme/tokens";
import ReportShell from "./ReportShell";
import MetricCard from "./MetricCard";

interface Gap {
  id: string;
  element: string;
  type: string;
  gapType: "create" | "replace" | "modify" | "retire";
  priority: "low" | "medium" | "high" | "critical";
  linkedInitiatives: number;
}

const GAP_TYPE_COLORS: Record<Gap["gapType"], string> = {
  create: STATUS_COLORS.success,
  replace: STATUS_COLORS.warning,
  modify: STATUS_COLORS.info,
  retire: STATUS_COLORS.neutral,
};

export default function GapSummaryReport() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
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
          if (initiatives === 0)
            return bucket === "retire" || bucket === "replace" ? "critical" : "high";
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
    })();
  }, []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return gaps.filter(
      (g) => g.element.toLowerCase().includes(q) || g.type.toLowerCase().includes(q)
    );
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
        {t(
          "gapSummary.subtitle",
          "Identify gaps between current and target architectures that require initiatives to close."
        )}
      </Typography>

      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && gaps.length === 0 && !error && (
        <Alert severity="success">
          {t("gapSummary.noGaps", "No gaps identified. Architecture is aligned with target state.")}
        </Alert>
      )}

      {!loading && gaps.length > 0 && (
        <>
          {/* KPI tiles — shared MetricCard, same as the other reports */}
          <Box sx={{ display: "flex", gap: 2, mb: 3, flexWrap: "wrap" }}>
            <MetricCard
              label={t("gapSummary.metric.total", "Total Gaps")}
              value={stats.total}
              icon="warning"
              iconColor={STATUS_COLORS.info}
            />
            <MetricCard
              label={t("gapSummary.metric.critical", "Critical")}
              value={stats.critical}
              icon="report"
              iconColor={SEVERITY_COLORS.critical}
              color={SEVERITY_COLORS.critical}
            />
            <MetricCard
              label={t("gapSummary.metric.high", "High")}
              value={stats.high}
              icon="priority_high"
              iconColor={SEVERITY_COLORS.high}
              color={SEVERITY_COLORS.high}
            />
            <MetricCard
              label={t("gapSummary.metric.missing", "Missing")}
              value={stats.missing}
              icon="add_circle"
              iconColor={SEVERITY_COLORS.medium}
              color={SEVERITY_COLORS.medium}
            />
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
                    <MaterialSymbol icon="search" size={18} />
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
                <TableRow
                  sx={{ "& th": { fontWeight: 700, backgroundColor: "action.hover" } }}
                >
                  <TableCell>{t("gapSummary.col.element", "Element")}</TableCell>
                  <TableCell sx={{ width: 130 }}>{t("gapSummary.col.type", "Type")}</TableCell>
                  <TableCell sx={{ width: 120 }}>
                    {t("gapSummary.col.gapType", "Gap Type")}
                  </TableCell>
                  <TableCell sx={{ width: 110 }}>
                    {t("gapSummary.col.priority", "Priority")}
                  </TableCell>
                  <TableCell sx={{ width: 100, textAlign: "center" }}>
                    {t("gapSummary.col.initiatives", "Initiatives")}
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((gap) => (
                  <TableRow
                    key={gap.id}
                    hover
                    sx={{
                      backgroundColor:
                        gap.priority === "critical"
                          ? alpha(SEVERITY_COLORS.critical, 0.06)
                          : undefined,
                    }}
                  >
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {gap.element}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{gap.type}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={gap.gapType}
                        sx={{
                          backgroundColor: alpha(GAP_TYPE_COLORS[gap.gapType], 0.12),
                          color: GAP_TYPE_COLORS[gap.gapType],
                          fontWeight: 600,
                          textTransform: "capitalize",
                        }}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={gap.priority}
                        sx={{
                          backgroundColor: priorityColor(gap.priority),
                          color: "white",
                          fontWeight: 600,
                          textTransform: "capitalize",
                        }}
                      />
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

          {filtered.length === 0 && search && (
            <Alert severity="info" sx={{ mt: 2 }}>
              {t("gapSummary.noResults", "No gaps found.")}
            </Alert>
          )}
        </>
      )}
    </ReportShell>
  );
}
