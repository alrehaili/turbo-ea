/**
 * Exception & Waiver Matrix
 * Track approved exceptions and waivers to architecture standards.
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

interface Exception {
  id: string;
  item: string;
  type: string;
  standard: string;
  approvalStatus: "approved" | "pending" | "denied";
  expiryDate: string;
  risk: "low" | "medium" | "high";
}

export default function ExceptionWaiverMatrix() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exceptions, setExceptions] = useState<Exception[]>([]);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          // The TechStandard exception register (fork WP1.3/WP4.3) is the real
          // waiver store: time-boxed, approver-gated exceptions per standard.
          const [standardsList, registerRows] = await Promise.all([
            api.get<any[]>("/tech-standards").catch(() => []),
            api.get<any[]>("/tech-standards/exceptions").catch(() => []),
          ]);
          const standardName = new Map<string, string>(standardsList.map((s) => [s.id, s.name]));
          const standardMandate = new Map<string, string>(standardsList.map((s) => [s.id, s.mandate]));

          // Risk: expired or imminent expiry on a mandatory standard is high;
          // expiry within 90 days or a mandatory standard is medium; else low.
          const riskFor = (exc: any): Exception["risk"] => {
            const mandatory = standardMandate.get(exc.standard_id) === "mandatory";
            if (exc.status === "expired") return "high";
            if (exc.expiry_date) {
              const days = (new Date(exc.expiry_date).getTime() - Date.now()) / 86400000;
              if (days <= 30) return "high";
              if (days <= 90) return mandatory ? "high" : "medium";
            }
            return mandatory ? "medium" : "low";
          };

          const statusFor = (s: string): Exception["approvalStatus"] =>
            s === "approved" ? "approved" : s === "rejected" ? "denied" : "pending";

          const rows: Exception[] = registerRows.map((exc) => ({
            id: exc.id,
            item: exc.card?.name || exc.initiative?.name || "—",
            type: "Exception",
            standard: standardName.get(exc.standard_id) || exc.standard_id,
            approvalStatus: statusFor(exc.status),
            expiryDate: exc.expiry_date || "—",
            risk: riskFor(exc),
          }));

          const riskOrder = { high: 0, medium: 1, low: 2 };
          setExceptions(rows.sort((a, b) => riskOrder[a.risk] - riskOrder[b.risk]));
        } catch (err) {
          setError("Failed to load exceptions and waivers");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const filtered = useMemo(
    () => exceptions.filter((e) => e.item.toLowerCase().includes(search.toLowerCase()) || e.standard.toLowerCase().includes(search.toLowerCase())),
    [exceptions, search]
  );

  const stats = useMemo(() => {
    const total = exceptions.length;
    const approved = exceptions.filter((e) => e.approvalStatus === "approved").length;
    const pending = exceptions.filter((e) => e.approvalStatus === "pending").length;
    const high = exceptions.filter((e) => e.risk === "high").length;
    return { total, approved, pending, high };
  }, [exceptions]);

  const statusColor = (status: Exception["approvalStatus"]) => {
    switch (status) {
      case "approved":
        return "#4caf50";
      case "pending":
        return "#ff9800";
      case "denied":
        return "#f44336";
      default:
        return "#9e9e9e";
    }
  };

  const riskColor = (risk: Exception["risk"]) => {
    switch (risk) {
      case "high":
        return "#f44336";
      case "medium":
        return "#ff9800";
      case "low":
        return "#4caf50";
      default:
        return "#9e9e9e";
    }
  };

  return (
    <ReportShell title={t("exceptionWaiver.title", "Exception & Waiver Matrix")} icon="published_with_changes">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("exceptionWaiver.subtitle", "Manage and track approved exceptions and waivers to architecture standards.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && exceptions.length === 0 && !error && <Alert severity="success">{t("exceptionWaiver.empty", "No exceptions or waivers. Architecture is fully aligned.")}</Alert>}

      {!loading && exceptions.length > 0 && (
        <>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(4, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("exceptionWaiver.metric.total", "Total")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#4caf50" }}>
                {stats.approved}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("exceptionWaiver.metric.approved", "Approved")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#ff9800" }}>
                {stats.pending}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("exceptionWaiver.metric.pending", "Pending")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#f44336" }}>
                {stats.high}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("exceptionWaiver.metric.highRisk", "High Risk")}
              </Typography>
            </Paper>
          </Box>

          <TextField
            size="small"
            placeholder={t("exceptionWaiver.search", "Search items…")}
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
                  <TableCell sx={{ fontWeight: 700 }}>{t("exceptionWaiver.col.item", "Item")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100 }}>{t("exceptionWaiver.col.type", "Type")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 150 }}>{t("exceptionWaiver.col.standard", "Standard")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120 }}>{t("exceptionWaiver.col.expiry", "Expiry Date")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 110, textAlign: "center" }}>{t("exceptionWaiver.col.status", "Status")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("exceptionWaiver.col.risk", "Risk")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((exc) => (
                  <TableRow key={exc.id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {exc.item}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={exc.type} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{exc.standard}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{exc.expiryDate}</Typography>
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Chip size="small" label={exc.approvalStatus} sx={{ backgroundColor: statusColor(exc.approvalStatus), color: "white" }} />
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Chip size="small" label={exc.risk} sx={{ backgroundColor: riskColor(exc.risk), color: "white" }} />
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
