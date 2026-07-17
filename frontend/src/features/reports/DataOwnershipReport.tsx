/**
 * Data Ownership and Stewardship Report
 * Shows which data objects have assigned owners and stewards, with contact info.
 * Part of Phase 6: Data Architecture Views (NEA Domain).
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

interface DataOwnershipRow {
  id: string;
  name: string;
  type?: string;
  owner?: string;
  steward?: string;
  classification?: string;
  hasOwner: boolean;
  hasSteward: boolean;
}

export default function DataOwnershipReport() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [data, setData] = useState<DataOwnershipRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch DataObjects and their ownership metadata
  const fetchData = useMemo(
    () => async () => {
      try {
        setLoading(true);
        setError(null);
        // Fetch all DataObject cards with attributes
        const response = await api.get<{ items: any[] }>("/cards?type=DataObject&page_size=1000");
        const cards = Array.isArray(response) ? response : response.items || [];
        const rows: DataOwnershipRow[] = cards.map((card) => {
          const a = card.attributes || {};
          // `dataOwner` is the built-in field; `authoritativeSource` comes from
          // the NORA profile and doubles as the stewarding system of record.
          const owner = a.dataOwner || a.owner;
          const steward = a.dataSteward || a.authoritativeSource;
          return {
            id: card.id,
            name: card.name,
            type: card.type,
            owner,
            steward,
            classification: a.dataClassification || a.dataSensitivity,
            hasOwner: Boolean(owner),
            hasSteward: Boolean(steward),
          };
        });
        setData(rows);
      } catch (err) {
        console.error("Failed to fetch data ownership:", err);
        setError("Failed to load data objects");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Trigger fetch on mount
  useMemo(() => {
    fetchData();
  }, [fetchData]);

  const filteredData = useMemo(() => {
    const q = search.toLowerCase();
    return data.filter((row) => row.name.toLowerCase().includes(q));
  }, [data, search]);

  const ownershipStats = useMemo(() => {
    const total = data.length;
    const withOwner = data.filter((r) => r.hasOwner).length;
    const withSteward = data.filter((r) => r.hasSteward).length;
    const fullyAssigned = data.filter((r) => r.hasOwner && r.hasSteward).length;
    return {
      total,
      withOwner,
      withSteward,
      fullyAssigned,
      coverage: total > 0 ? Math.round((fullyAssigned / total) * 100) : 0,
    };
  }, [data]);

  return (
    <ReportShell
      title={t("dataOwnership.title", "Data Ownership & Stewardship")}
      icon="person_check"
    >
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("dataOwnership.subtitle", "Assign and track data owners and stewards across your data landscape.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && data.length === 0 && !error && (
        <Alert severity="info">
          {t("dataOwnership.empty", "No data objects found. Create DataObject cards to track ownership.")}
        </Alert>
      )}

      {data.length > 0 && (
        <>
          {/* KPI Cards */}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(4, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {ownershipStats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dataOwnership.metric.total", "Data Objects")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                {ownershipStats.withOwner}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dataOwnership.metric.withOwner", "With Owner")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "success.main" }}>
                {ownershipStats.withSteward}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dataOwnership.metric.withSteward", "With Steward")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: ownershipStats.coverage < 50 ? "warning.main" : "success.main" }}>
                {ownershipStats.coverage}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dataOwnership.metric.coverage", "Coverage")}
              </Typography>
            </Paper>
          </Box>

          {/* Search */}
          <TextField
            size="small"
            fullWidth
            placeholder={t("dataOwnership.search", "Search data objects…")}
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

          {/* Table */}
          <Paper variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: "#fafafa" }}>
                  <TableCell sx={{ fontWeight: 700 }}>
                    {t("dataOwnership.col.name", "Data Object")}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 200 }}>
                    {t("dataOwnership.col.owner", "Owner")}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 200 }}>
                    {t("dataOwnership.col.steward", "Steward")}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 140 }}>
                    {t("dataOwnership.col.classification", "Classification")}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>
                    {t("dataOwnership.col.coverage", "Coverage")}
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredData.map((row) => (
                  <TableRow key={row.id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {row.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {row.owner ? (
                        <Chip size="small" label={row.owner} variant="outlined" />
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          —
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {row.steward ? (
                        <Chip size="small" label={row.steward} variant="outlined" />
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          —
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {row.classification ? (
                        <Chip size="small" label={row.classification} variant="filled" color="default" />
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          —
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      {row.hasOwner && row.hasSteward ? (
                        <Chip size="small" label="100%" color="success" variant="outlined" />
                      ) : row.hasOwner || row.hasSteward ? (
                        <Chip size="small" label="50%" color="warning" variant="outlined" />
                      ) : (
                        <Chip size="small" label="0%" variant="outlined" />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          {filteredData.length === 0 && search && (
            <Alert severity="info" sx={{ mt: 2 }}>
              {t("dataOwnership.noResults", "No results found for your search.")}
            </Alert>
          )}
        </>
      )}
    </ReportShell>
  );
}
