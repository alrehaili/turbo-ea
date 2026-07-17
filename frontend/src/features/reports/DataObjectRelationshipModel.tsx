/**
 * Data Object Relationship Model
 * Shows the network and dependencies between data objects.
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
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface DataRelation {
  sourceId: string;
  sourceName: string;
  targetId: string;
  targetName: string;
  relationType: string;
  direction: string;
}

export default function DataObjectRelationshipModel() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [relations, setRelations] = useState<DataRelation[]>([]);
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch data objects and relations
  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          setError(null);
          const [objResp, allRels] = await Promise.all([
            api.get<{ items: any[] }>("/cards?type=DataObject&page_size=1000"),
            api.get<any[]>("/relations"),
          ]);
          const objects = Array.isArray(objResp) ? objResp : objResp.items || [];
          setData(objects);

          const byId = new Map<string, any>(objects.map((o) => [o.id, o]));
          const allRelations: DataRelation[] = [];

          // Typed relations where both endpoints are DataObjects (e.g. successor links)
          for (const rel of allRels) {
            if (byId.has(rel.source_id) && byId.has(rel.target_id)) {
              allRelations.push({
                sourceId: rel.source_id,
                sourceName: rel.source?.name || byId.get(rel.source_id)?.name || rel.source_id,
                targetId: rel.target_id,
                targetName: rel.target?.name || byId.get(rel.target_id)?.name || rel.target_id,
                relationType: rel.type,
                direction: "→",
              });
            }
          }

          // Hierarchy edges (parent_id) between data objects
          for (const obj of objects) {
            if (obj.parent_id && byId.has(obj.parent_id)) {
              allRelations.push({
                sourceId: obj.id,
                sourceName: obj.name,
                targetId: obj.parent_id,
                targetName: byId.get(obj.parent_id)!.name,
                relationType: "hierarchy",
                direction: "→",
              });
            }
          }
          setRelations(allRelations);
        } catch (err) {
          console.error("Failed to fetch data object relationships:", err);
          setError("Failed to load data object relationships");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const filteredRelations = useMemo(() => {
    const q = search.toLowerCase();
    return relations.filter(
      (r) =>
        r.sourceName.toLowerCase().includes(q) ||
        r.targetName.toLowerCase().includes(q) ||
        r.relationType.toLowerCase().includes(q)
    );
  }, [relations, search]);

  const stats = useMemo(
    () => ({
      total: data.length,
      withRelations: new Set(relations.map((r) => r.sourceId)).size,
      relationCount: relations.length,
    }),
    [data, relations]
  );

  return (
    <ReportShell title={t("dataRelationship.title", "Data Object Relationship Model")} icon="hub">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("dataRelationship.subtitle", "Explore relationships and dependencies between data objects in your architecture.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && stats.total === 0 && !error && <Alert severity="info">{t("dataRelationship.empty", "No data objects found.")}</Alert>}

      {!loading && stats.total > 0 && (
        <>
          {/* KPI Cards */}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dataRelationship.metric.total", "Data Objects")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                {stats.withRelations}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dataRelationship.metric.linked", "With Relations")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "success.main" }}>
                {stats.relationCount}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dataRelationship.metric.relationCount", "Total Relations")}
              </Typography>
            </Paper>
          </Box>

          {/* Search */}
          <TextField
            size="small"
            placeholder={t("dataRelationship.search", "Search by name or relation type…")}
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

          {filteredRelations.length === 0 && !search && (
            <Alert severity="info">{t("dataRelationship.noRelations", "No relationships defined between data objects yet.")}</Alert>
          )}

          {filteredRelations.length === 0 && search && (
            <Alert severity="info">{t("dataRelationship.noResults", "No results found for your search.")}</Alert>
          )}

          {filteredRelations.length > 0 && (
            <Paper variant="outlined" sx={{ overflow: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ backgroundColor: "#fafafa" }}>
                    <TableCell sx={{ fontWeight: 700 }}>{t("dataRelationship.col.source", "Source Data Object")}</TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("dataRelationship.col.direction", "Dir.")}</TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>{t("dataRelationship.col.target", "Target Data Object")}</TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 180 }}>{t("dataRelationship.col.relationType", "Relation Type")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredRelations.slice(0, 100).map((rel, idx) => (
                    <TableRow key={idx} hover>
                      <TableCell>
                        <Typography variant="body2">{rel.sourceName}</Typography>
                      </TableCell>
                      <TableCell sx={{ textAlign: "center" }}>
                        <Typography variant="caption">{rel.direction}</Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{rel.targetName}</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip size="small" label={rel.relationType} variant="outlined" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          )}

          {filteredRelations.length > 100 && (
            <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: "block" }}>
              {t("dataRelationship.truncated", "Showing first 100 of {{total}} relationships", { total: filteredRelations.length })}
            </Typography>
          )}
        </>
      )}
    </ReportShell>
  );
}
