/**
 * Data Classification & Sensitivity Heatmap
 * Shows data objects by classification and sensitivity level.
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
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import InputAdornment from "@mui/material/InputAdornment";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { SEVERITY_COLORS } from "@/theme/tokens";
import ReportShell from "./ReportShell";

interface ClassificationRow {
  classification: string;
  count: number;
  sensitive: number;
  objects: Array<{ id: string; name: string; sensitive: boolean }>;
}

export default function DataClassificationReport() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch DataObjects
  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          setError(null);
          const response = await api.get<{ items: any[] }>("/cards?type=DataObject&page_size=1000");
          setData(Array.isArray(response) ? response : response.items || []);
        } catch (err) {
          console.error("Failed to fetch data classification:", err);
          setError("Failed to load data objects");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const classifications = useMemo(() => {
    const q = search.toLowerCase();
    const filtered = data.filter((obj) => obj.name.toLowerCase().includes(q));

    const grouped = new Map<string, ClassificationRow>();

    filtered.forEach((obj) => {
      const a = obj.attributes || {};
      // NORA profile classification (NDMO levels) first, base sensitivity second
      const classification = a.dataClassification || a.dataSensitivity || "Unclassified";
      // Sensitive = personal data (PII) or an elevated classification level
      const sensitive =
        a.isPersonalData === true ||
        a.piiFlag === true ||
        ["secret", "topSecret", "restricted", "confidential"].includes(String(classification));

      if (!grouped.has(classification)) {
        grouped.set(classification, { classification, count: 0, sensitive: 0, objects: [] });
      }
      const row = grouped.get(classification)!;
      row.count += 1;
      if (sensitive) row.sensitive += 1;
      row.objects.push({
        id: obj.id,
        name: obj.name,
        sensitive,
      });
    });

    return Array.from(grouped.values()).sort((a, b) => b.count - a.count);
  }, [data, search]);

  const stats = useMemo(() => {
    const total = data.length;
    const classified = data.filter(
      (d) => d.attributes?.dataClassification || d.attributes?.dataSensitivity,
    ).length;
    const sensitive = data.filter((d) => {
      const a = d.attributes || {};
      const cls = a.dataClassification || a.dataSensitivity;
      return (
        a.isPersonalData === true ||
        a.piiFlag === true ||
        ["secret", "topSecret", "restricted", "confidential"].includes(String(cls))
      );
    }).length;
    return { total, classified, sensitive };
  }, [data]);

  return (
    <ReportShell title={t("dataClassification.title", "Data Classification & Sensitivity")} icon="security">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("dataClassification.subtitle", "Track data object classifications and sensitivity levels across your organization.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && stats.total === 0 && !error && <Alert severity="info">{t("dataClassification.empty", "No data objects found.")}</Alert>}

      {!loading && stats.total > 0 && (
        <>
          {/* KPI Cards */}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dataClassification.metric.total", "Total Objects")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                {stats.classified}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dataClassification.metric.classified", "Classified")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: SEVERITY_COLORS.high }}>
                {stats.sensitive}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dataClassification.metric.sensitive", "Sensitive")}
              </Typography>
            </Paper>
          </Box>

          {/* Search */}
          <TextField
            size="small"
            placeholder={t("dataClassification.search", "Search data objects…")}
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

          {/* Classification Table */}
          <Paper variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: "#fafafa" }}>
                  <TableCell sx={{ fontWeight: 700 }}>{t("dataClassification.col.classification", "Classification")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 80, textAlign: "center" }}>{t("dataClassification.col.count", "Count")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("dataClassification.col.sensitive", "Sensitive")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("dataClassification.col.percentage", "%")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {classifications.map((row) => (
                  <TableRow key={row.classification} hover>
                    <TableCell>
                      <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
                        <Box
                          sx={{
                            width: 12,
                            height: 12,
                            borderRadius: 1,
                            backgroundColor:
                              row.classification.toLowerCase().includes("public") ||
                              row.classification.toLowerCase().includes("unrestricted")
                                ? "#4caf50"
                                : row.classification.toLowerCase().includes("confidential") ||
                                    row.classification.toLowerCase().includes("sensitive")
                                  ? "#f44336"
                                  : "#ff9800",
                          }}
                        />
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {row.classification}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Chip size="small" label={row.count} variant="outlined" />
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      {row.sensitive > 0 ? (
                        <Chip size="small" label={row.sensitive} color="error" variant="outlined" />
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          0
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Typography variant="caption">{Math.round((row.sensitive / row.count) * 100)}%</Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          {classifications.length === 0 && search && (
            <Alert severity="info" sx={{ mt: 2 }}>
              {t("dataClassification.noResults", "No results found for your search.")}
            </Alert>
          )}
        </>
      )}
    </ReportShell>
  );
}
