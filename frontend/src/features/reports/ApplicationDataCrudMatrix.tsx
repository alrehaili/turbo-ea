/**
 * Application-Data CRUD Matrix
 * Shows which applications Create, Read, Update, Delete which data objects.
 * Part of Phase 6: Data Architecture Views.
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
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface AppDataCrudEntry {
  appName: string;
  dataName: string;
  create: boolean;
  read: boolean;
  update: boolean;
  delete: boolean;
}

export default function ApplicationDataCrudMatrix() {
  const { t } = useTranslation(["reports"]);
  const [data, setData] = useState<AppDataCrudEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch applications and data objects with their relations
  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          setError(null);
          // relAppToDataObj carries real CRUD boolean attributes
          // (crudCreate/crudRead/crudUpdate/crudDelete) on each relation.
          const relations = await api.get<any[]>("/relations?type=relAppToDataObj");

          const entries: AppDataCrudEntry[] = relations.map((rel) => {
            const a = rel.attributes || {};
            const hasFlags =
              a.crudCreate !== undefined ||
              a.crudRead !== undefined ||
              a.crudUpdate !== undefined ||
              a.crudDelete !== undefined;
            return {
              appName: rel.source?.name || rel.source_id,
              dataName: rel.target?.name || rel.target_id,
              create: Boolean(a.crudCreate),
              // A CRUD relation without explicit flags implies at least read access
              read: hasFlags ? Boolean(a.crudRead) : true,
              update: Boolean(a.crudUpdate),
              delete: Boolean(a.crudDelete),
            };
          });

          setData(entries);
        } catch (err) {
          console.error("Failed to fetch CRUD matrix:", err);
          setError("Failed to load applications and data objects");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const operations = useMemo(() => {
    const ops = new Map<string, number>();
    data.forEach((entry) => {
      if (entry.create) ops.set("create", (ops.get("create") ?? 0) + 1);
      if (entry.read) ops.set("read", (ops.get("read") ?? 0) + 1);
      if (entry.update) ops.set("update", (ops.get("update") ?? 0) + 1);
      if (entry.delete) ops.set("delete", (ops.get("delete") ?? 0) + 1);
    });
    return ops;
  }, [data]);

  return (
    <ReportShell title={t("appDataCrud.title", "Application-Data CRUD Matrix")} icon="table_chart">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("appDataCrud.subtitle", "Track Create, Read, Update, Delete operations between applications and data objects.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && data.length === 0 && !error && (
        <Alert severity="info">{t("appDataCrud.empty", "No application-data relationships found. Create relations between Applications and DataObjects to track CRUD operations.")}</Alert>
      )}

      {!loading && data.length > 0 && (
        <>
          {/* KPI Cards */}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(4, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#4caf50" }}>
                {operations.get("create") ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Create
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#2196f3" }}>
                {operations.get("read") ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Read
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#ff9800" }}>
                {operations.get("update") ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Update
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#f44336" }}>
                {operations.get("delete") ?? 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Delete
              </Typography>
            </Paper>
          </Box>

          {/* CRUD Matrix Table */}
          <Paper variant="outlined" sx={{ overflow: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: "#fafafa" }}>
                  <TableCell sx={{ fontWeight: 700 }}>{t("appDataCrud.col.application", "Application")}</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>{t("appDataCrud.col.dataObject", "Data Object")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120, textAlign: "center" }}>C</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120, textAlign: "center" }}>R</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120, textAlign: "center" }}>U</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120, textAlign: "center" }}>D</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.slice(0, 100).map((entry, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      <Typography variant="body2">{entry.appName}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{entry.dataName}</Typography>
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      {entry.create ? <Chip size="small" label="✓" color="success" /> : <Typography variant="caption">—</Typography>}
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      {entry.read ? <Chip size="small" label="✓" color="info" /> : <Typography variant="caption">—</Typography>}
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      {entry.update ? <Chip size="small" label="✓" color="warning" /> : <Typography variant="caption">—</Typography>}
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      {entry.delete ? <Chip size="small" label="✓" color="error" /> : <Typography variant="caption">—</Typography>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          {data.length > 100 && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: "block" }}>
              {t("appDataCrud.truncated", "Showing first 100 of {{total}} relationships", { total: data.length })}
            </Typography>
          )}
        </>
      )}
    </ReportShell>
  );
}
