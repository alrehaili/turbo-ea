/**
 * Data Domain Landscape
 * Shows all data objects grouped by domain, owner, or classification.
 * Part of Phase 6: Data Architecture Views.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
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

interface DataDomain {
  name: string;
  count: number;
  objects: Array<{ id: string; name: string; owner?: string; classification?: string }>;
}

type GroupBy = "owner" | "classification" | "none";

export default function DataDomainLandscape() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [groupBy, setGroupBy] = useState<GroupBy>("owner");
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
          console.error("Failed to fetch data domain landscape:", err);
          setError("Failed to load data objects");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const domains = useMemo(() => {
    const q = search.toLowerCase();
    const filtered = data.filter((obj) => obj.name.toLowerCase().includes(q));

    const grouped = new Map<string, DataDomain>();

    filtered.forEach((obj) => {
      const key =
        groupBy === "owner"
          ? obj.attributes?.dataOwner || obj.attributes?.owner || "Unassigned"
          : groupBy === "classification"
            ? obj.attributes?.dataClassification || obj.attributes?.dataSensitivity || "Unclassified"
            : "All Data Objects";

      if (!grouped.has(key)) {
        grouped.set(key, { name: key, count: 0, objects: [] });
      }
      const domain = grouped.get(key)!;
      domain.count += 1;
      domain.objects.push({
        id: obj.id,
        name: obj.name,
        owner: obj.attributes?.dataOwner || obj.attributes?.owner,
        classification: obj.attributes?.dataClassification || obj.attributes?.dataSensitivity,
      });
    });

    return Array.from(grouped.values()).sort((a, b) => b.count - a.count);
  }, [data, search, groupBy]);

  const totalObjects = useMemo(() => data.length, [data]);
  const domainCount = useMemo(() => domains.length, [domains]);

  return (
    <ReportShell title={t("dataDomain.title", "Data Domain Landscape")} icon="dashboard">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("dataDomain.subtitle", "Browse your data landscape organized by domain, owner, or classification.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && totalObjects === 0 && !error && <Alert severity="info">{t("dataDomain.empty", "No data objects found.")}</Alert>}

      {!loading && totalObjects > 0 && (
        <>
          {/* KPI Cards */}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {totalObjects}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dataDomain.metric.total", "Total Data Objects")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {domainCount}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dataDomain.metric.domains", `${groupBy === "owner" ? "Owners" : groupBy === "classification" ? "Classifications" : "Domains"}`)}
              </Typography>
            </Paper>
          </Box>

          {/* Controls */}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 200px" }, gap: 1.5, mb: 2 }}>
            <TextField
              size="small"
              placeholder={t("dataDomain.search", "Search data objects…")}
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
            />
            <FormControl size="small">
              <InputLabel>{t("dataDomain.groupBy", "Group By")}</InputLabel>
              <Select value={groupBy} label="Group By" onChange={(e) => setGroupBy(e.target.value as GroupBy)}>
                <MenuItem value="owner">{t("dataDomain.groupBy.owner", "Owner")}</MenuItem>
                <MenuItem value="classification">{t("dataDomain.groupBy.classification", "Classification")}</MenuItem>
                <MenuItem value="none">{t("dataDomain.groupBy.all", "None")}</MenuItem>
              </Select>
            </FormControl>
          </Box>

          {/* Domains List */}
          {domains.map((domain) => (
            <Paper key={domain.name} sx={{ mb: 2, overflow: "auto" }}>
              <Box sx={{ p: 2, bgcolor: "#fafafa", borderBottom: "1px solid", borderColor: "divider" }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, justifyContent: "space-between" }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    {domain.name}
                  </Typography>
                  <Chip size="small" label={`${domain.count} objects`} variant="outlined" />
                </Box>
              </Box>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>{t("dataDomain.col.name", "Name")}</TableCell>
                    {groupBy !== "owner" && <TableCell sx={{ fontWeight: 700, width: 150 }}>{t("dataDomain.col.owner", "Owner")}</TableCell>}
                    {groupBy !== "classification" && <TableCell sx={{ fontWeight: 700, width: 140 }}>{t("dataDomain.col.classification", "Classification")}</TableCell>}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {domain.objects.map((obj) => (
                    <TableRow key={obj.id}>
                      <TableCell>
                        <Typography variant="body2">{obj.name}</Typography>
                      </TableCell>
                      {groupBy !== "owner" && (
                        <TableCell>
                          {obj.owner ? <Chip size="small" label={obj.owner} variant="outlined" /> : <Typography variant="caption" color="text.secondary">—</Typography>}
                        </TableCell>
                      )}
                      {groupBy !== "classification" && (
                        <TableCell>
                          {obj.classification ? <Chip size="small" label={obj.classification} /> : <Typography variant="caption" color="text.secondary">—</Typography>}
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          ))}
        </>
      )}
    </ReportShell>
  );
}
