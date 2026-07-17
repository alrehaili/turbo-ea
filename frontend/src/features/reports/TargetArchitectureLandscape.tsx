/**
 * Target Architecture Landscape
 * Shows applications and technology in the target state.
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
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import InputAdornment from "@mui/material/InputAdornment";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface TargetElement {
  id: string;
  name: string;
  type: string;
  currentExists: boolean;
  targetDeployment?: string;
  owner?: string;
}

export default function TargetArchitectureLandscape() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [elements, setElements] = useState<TargetElement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          setError(null);
          // Target state = target + transition slices (WP2.1 architecture_state)
          const [targetResp, transitionResp] = await Promise.all([
            api.get<{ items: any[] }>("/cards?architecture_state=target&page_size=500"),
            api.get<{ items: any[] }>("/cards?architecture_state=transition&page_size=500"),
          ]);
          const cards = [
            ...(Array.isArray(targetResp) ? targetResp : targetResp.items || []),
            ...(Array.isArray(transitionResp) ? transitionResp : transitionResp.items || []),
          ];
          const elements: TargetElement[] = cards.map((c) => ({
            id: c.id,
            name: c.name,
            type: c.type,
            // A target card that replaces/modifies an existing one is "retained"
            // landscape-wise; a plain create is genuinely new.
            currentExists: Boolean(c.successor_id || c.change_type === "modify" || c.change_type === "replace"),
            targetDeployment: c.attributes?.hostingType || c.attributes?.hostingModel,
            owner: c.attributes?.dataOwner || undefined,
          }));
          setElements(elements);
        } catch (err) {
          console.error("Failed to fetch target landscape:", err);
          setError("Failed to load target architecture");
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
    return elements.filter((e) => e.name.toLowerCase().includes(q) || e.type.toLowerCase().includes(q));
  }, [elements, search]);

  const stats = useMemo(() => {
    const total = elements.length;
    const retained = elements.filter((e) => e.currentExists).length;
    const new_items = elements.filter((e) => !e.currentExists).length;
    return { total, retained, new: new_items };
  }, [elements]);

  return (
    <ReportShell title={t("targetLandscape.title", "Target Architecture Landscape")} icon="architecture">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("targetLandscape.subtitle", "Preview the target state architecture with planned deployments and ownership.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && elements.length === 0 && !error && <Alert severity="info">{t("targetLandscape.empty", "No target architecture defined yet.")}</Alert>}

      {!loading && elements.length > 0 && (
        <>
          {/* KPI Cards */}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("targetLandscape.metric.total", "Target Elements")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "success.main" }}>
                {stats.retained}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("targetLandscape.metric.retained", "Retained")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                {stats.new}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("targetLandscape.metric.new", "New")}
              </Typography>
            </Paper>
          </Box>

          {/* Search */}
          <TextField
            size="small"
            placeholder={t("targetLandscape.search", "Search target elements…")}
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

          {/* Target Elements Table */}
          <Paper variant="outlined" sx={{ overflow: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: "#fafafa" }}>
                  <TableCell sx={{ fontWeight: 700 }}>{t("targetLandscape.col.element", "Element")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100 }}>{t("targetLandscape.col.type", "Type")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120 }}>{t("targetLandscape.col.deployment", "Deployment")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120 }}>{t("targetLandscape.col.owner", "Owner")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100 }}>{t("targetLandscape.col.status", "Status")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((elem) => (
                  <TableRow key={elem.id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {elem.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{elem.type}</Typography>
                    </TableCell>
                    <TableCell>
                      {elem.targetDeployment ? (
                        <Chip size="small" label={elem.targetDeployment} variant="outlined" />
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          —
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {elem.owner ? <Chip size="small" label={elem.owner} /> : <Typography variant="caption" color="text.secondary">—</Typography>}
                    </TableCell>
                    <TableCell>
                      {elem.currentExists ? (
                        <Chip size="small" label={t("targetLandscape.status.retained", "Retained")} color="success" variant="outlined" />
                      ) : (
                        <Chip size="small" label={t("targetLandscape.status.new", "New")} color="primary" variant="outlined" />
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          {filtered.length === 0 && search && <Alert severity="info" sx={{ mt: 2 }}>{t("targetLandscape.noResults", "No results found.")}</Alert>}
        </>
      )}
    </ReportShell>
  );
}
