/**
 * Standards Compliance Matrix
 * Compliance matrix showing applications against architecture standards.
 * Part of Phase 8: Standards & Security Traceability.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface ComplianceRecord {
  appId: string;
  appName: string;
  standards: Map<string, boolean>;
  complianceRate: number;
}

export default function StandardsComplianceMatrix() {
  const { t } = useTranslation(["reports"]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [records, setRecords] = useState<ComplianceRecord[]>([]);
  const [standards, setStandards] = useState<string[]>([]);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          // Real compliance signal: the TechStandard catalogue + its exception
          // register. An app is non-compliant with a standard when it holds an
          // active (approved/requested, unexpired) exception against it.
          const [appResp, standardsList, exceptions] = await Promise.all([
            api.get<{ items: any[] }>("/cards?type=Application&page_size=200"),
            api.get<any[]>("/tech-standards").catch(() => []),
            api.get<any[]>("/tech-standards/exceptions").catch(() => []),
          ]);
          const apps = Array.isArray(appResp) ? appResp : appResp.items || [];

          const standardById = new Map<string, any>(standardsList.map((s) => [s.id, s]));

          // Exceptions per app card, keyed by standard
          const exceptionsByApp = new Map<string, Set<string>>();
          const standardsWithExceptions = new Set<string>();
          for (const exc of exceptions) {
            if (exc.status === "rejected" || exc.status === "expired") continue;
            const cardId = exc.card?.id;
            if (!cardId) continue;
            standardsWithExceptions.add(exc.standard_id);
            if (!exceptionsByApp.has(cardId)) exceptionsByApp.set(cardId, new Set());
            exceptionsByApp.get(cardId)!.add(exc.standard_id);
          }

          // Columns: mandatory standards first, then any standard that has
          // exceptions on file; capped so the matrix stays readable.
          const columnStandards = standardsList
            .filter((s) => s.mandate === "mandatory" || standardsWithExceptions.has(s.id))
            .slice(0, 10);
          if (columnStandards.length === 0) {
            // Fall back to the whole catalogue when nothing is flagged mandatory
            columnStandards.push(...standardsList.slice(0, 10));
          }
          setStandards(columnStandards.map((s) => s.name));

          const rows: ComplianceRecord[] = apps.map((app) => {
            const appExceptions = exceptionsByApp.get(app.id) || new Set<string>();
            const perStandard = new Map<string, boolean>();
            for (const std of columnStandards) {
              perStandard.set(std.name, !appExceptions.has(std.id));
            }
            const compliant = Array.from(perStandard.values()).filter(Boolean).length;
            const complianceRate =
              columnStandards.length > 0 ? Math.round((compliant / columnStandards.length) * 100) : 100;
            return {
              appId: app.id,
              appName: app.name,
              standards: perStandard,
              complianceRate,
            };
          });

          // keep standardById referenced for future drill-in use
          void standardById;
          setRecords(rows.sort((a, b) => a.complianceRate - b.complianceRate));
        } catch (err) {
          setError("Failed to load compliance data");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const stats = useMemo(() => {
    const total = records.length;
    const fullyCompliant = records.filter((r) => r.complianceRate === 100).length;
    const avgCompliance = Math.round(records.reduce((sum, r) => sum + r.complianceRate, 0) / Math.max(records.length, 1));
    return { total, fullyCompliant, avgCompliance };
  }, [records]);

  return (
    <ReportShell title={t("standardsMatrix.title", "Standards Compliance Matrix")} icon="checklist">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("standardsMatrix.subtitle", "Application compliance against architecture standards and best practices.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && records.length === 0 && !error && <Alert severity="info">{t("standardsMatrix.empty", "No applications found.")}</Alert>}

      {!loading && records.length > 0 && (
        <>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("standardsMatrix.metric.total", "Applications")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#4caf50" }}>
                {stats.fullyCompliant}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("standardsMatrix.metric.compliant", "Fully Compliant")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                {stats.avgCompliance}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("standardsMatrix.metric.average", "Average Compliance")}
              </Typography>
            </Paper>
          </Box>

          <Paper variant="outlined" sx={{ overflow: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: "#fafafa" }}>
                  <TableCell sx={{ fontWeight: 700, minWidth: 200 }}>{t("standardsMatrix.col.application", "Application")}</TableCell>
                  {standards.map((std) => (
                    <TableCell key={std} sx={{ fontWeight: 700, width: 80, textAlign: "center" }}>
                      <Typography variant="caption">{std}</Typography>
                    </TableCell>
                  ))}
                  <TableCell sx={{ fontWeight: 700, width: 80 }}>{t("standardsMatrix.col.compliance", "Compliance")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {records.slice(0, 50).map((record) => (
                  <TableRow key={record.appId} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {record.appName}
                      </Typography>
                    </TableCell>
                    {standards.map((std) => (
                      <TableCell key={std} sx={{ textAlign: "center" }}>
                        <Box sx={{ color: record.standards.get(std) ? "#4caf50" : "#f44336", fontSize: "1.2rem" }}>
                          {record.standards.get(std) ? "✓" : "✕"}
                        </Box>
                      </TableCell>
                    ))}
                    <TableCell>
                      <Chip
                        size="small"
                        label={`${record.complianceRate}%`}
                        sx={{
                          backgroundColor: record.complianceRate === 100 ? "#4caf50" : record.complianceRate >= 50 ? "#ff9800" : "#f44336",
                          color: "white",
                        }}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          {records.length > 50 && (
            <Alert severity="info" sx={{ mt: 2 }}>
              {t("standardsMatrix.truncated", "Showing first 50 of {{count}} applications", { count: records.length })}
            </Alert>
          )}
        </>
      )}
    </ReportShell>
  );
}
