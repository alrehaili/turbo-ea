/**
 * Security Controls Coverage
 * Track security controls and their coverage across the portfolio.
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
import LinearProgress from "@mui/material/LinearProgress";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface ControlCoverage {
  id: string;
  control: string;
  category: string;
  coverage: number;
  applicableApps: number;
  implementedApps: number;
  status: "full" | "partial" | "minimal" | "none";
}

export default function SecurityControlsCoverage() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [controls, setControls] = useState<ControlCoverage[]>([]);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          // SecurityControl cards (NORA Security layer) + their protection
          // relations to Applications, DataObjects and ITComponents.
          const [ctrlResp, appResp, appRels, dataRels, itcRels] = await Promise.all([
            api.get<{ items: any[] }>("/cards?type=SecurityControl&page_size=500"),
            api.get<{ items: any[] }>("/cards?type=Application&page_size=1"),
            api.get<any[]>("/relations?type=relSecCtrlToApp").catch(() => []),
            api.get<any[]>("/relations?type=relSecCtrlToData").catch(() => []),
            api.get<any[]>("/relations?type=relSecCtrlToITC").catch(() => []),
          ]);
          const controlCards = Array.isArray(ctrlResp) ? ctrlResp : ctrlResp.items || [];
          const totalApps = Array.isArray(appResp) ? appResp.length : (appResp as any).total || 0;

          const appsByControl = new Map<string, number>();
          for (const rel of appRels) {
            appsByControl.set(rel.source_id, (appsByControl.get(rel.source_id) || 0) + 1);
          }
          const otherAssetsByControl = new Map<string, number>();
          for (const rel of [...dataRels, ...itcRels]) {
            otherAssetsByControl.set(rel.source_id, (otherAssetsByControl.get(rel.source_id) || 0) + 1);
          }

          const statusFromImpl = (impl: string | undefined, coverage: number): ControlCoverage["status"] => {
            if (impl === "implemented" || impl === "operational") return coverage > 0 ? "full" : "partial";
            if (impl === "inProgress" || impl === "partial") return "partial";
            if (impl === "planned") return "minimal";
            return coverage >= 80 ? "full" : coverage >= 50 ? "partial" : coverage > 0 ? "minimal" : "none";
          };

          const rows: ControlCoverage[] = controlCards.map((c) => {
            const protectedApps = appsByControl.get(c.id) || 0;
            const coverage = totalApps > 0 ? Math.round((protectedApps / totalApps) * 100) : 0;
            return {
              id: c.id,
              control: c.name,
              category: c.attributes?.controlDomain || "unassigned",
              coverage,
              applicableApps: totalApps,
              implementedApps: protectedApps + (otherAssetsByControl.get(c.id) || 0),
              status: statusFromImpl(c.attributes?.implementationStatus, coverage),
            };
          });
          setControls(rows.sort((a, b) => b.coverage - a.coverage));
        } catch (err) {
          setError("Failed to load security controls data");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const filtered = useMemo(
    () => controls.filter((c) => c.control.toLowerCase().includes(search.toLowerCase())),
    [controls, search]
  );

  const stats = useMemo(() => {
    const total = controls.length;
    const full = controls.filter((c) => c.status === "full").length;
    const avgCoverage = Math.round(controls.reduce((sum, c) => sum + c.coverage, 0) / Math.max(controls.length, 1));
    return { total, full, avgCoverage };
  }, [controls]);

  const statusColor = (status: ControlCoverage["status"]) => {
    switch (status) {
      case "full":
        return "#4caf50";
      case "partial":
        return "#ff9800";
      case "minimal":
        return "#f44336";
      default:
        return "#9e9e9e";
    }
  };

  return (
    <ReportShell title={t("securityControls.title", "Security Controls Coverage")} icon="security">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("securityControls.subtitle", "Overview of security control implementation across applications.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && controls.length === 0 && !error && (
        <Alert severity="info">{t("securityControls.empty", "No security controls found.")}</Alert>
      )}

      {!loading && controls.length > 0 && (
        <>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("securityControls.metric.total", "Total Controls")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#4caf50" }}>
                {stats.full}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("securityControls.metric.fullCoverage", "Fully Implemented")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                {stats.avgCoverage}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("securityControls.metric.avgCoverage", "Average Coverage")}
              </Typography>
            </Paper>
          </Box>

          <TextField
            size="small"
            placeholder={t("securityControls.search", "Search controls…")}
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
                  <TableCell sx={{ fontWeight: 700 }}>{t("securityControls.col.control", "Control")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100 }}>{t("securityControls.col.category", "Category")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 150 }}>{t("securityControls.col.coverage", "Coverage")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120, textAlign: "center" }}>{t("securityControls.col.status", "Status")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((control) => (
                  <TableRow key={control.id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {control.control}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={control.category} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Box sx={{ flex: 1 }}>
                          <LinearProgress variant="determinate" value={control.coverage} />
                        </Box>
                        <Typography variant="caption" sx={{ minWidth: 40, fontWeight: 600 }}>
                          {control.coverage}%
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Chip size="small" label={control.status} sx={{ backgroundColor: statusColor(control.status), color: "white" }} />
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
