/**
 * Persona Catalog
 * Browse beneficiary personas with demographics and characteristics.
 * Part of Phase 9: Beneficiary Experience Views.
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

interface Persona {
  id: string;
  name: string;
  description: string;
  demographic: string;
  primaryGoal: string;
  painPoints: string[];
  touchpointCount: number;
}

export default function PersonaCatalog() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          const response = await api.get<{ items: any[] }>("/cards?type=Persona&page_size=500");
          const cards = Array.isArray(response) ? response : response.items || [];

          const personasData: Persona[] = cards.map((c) => ({
            id: c.id,
            name: c.name,
            description: c.description || "User persona",
            demographic: c.attributes?.demographics || "Not specified",
            primaryGoal: c.attributes?.goals || "Achieve objectives",
            painPoints: c.attributes?.painPoints ? (typeof c.attributes.painPoints === "string" ? c.attributes.painPoints.split(",").map((s: string) => s.trim()) : [c.attributes.painPoints]) : [],
            touchpointCount: c.attributes?.preferredChannels ? (typeof c.attributes.preferredChannels === "string" ? c.attributes.preferredChannels.split(",").length : 1) : 0,
          }));

          setPersonas(personasData);
        } catch (err) {
          setError("Failed to load personas");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const filtered = useMemo(
    () => personas.filter((p) => p.name.toLowerCase().includes(search.toLowerCase())),
    [personas, search]
  );

  const stats = useMemo(() => {
    const total = personas.length;
    const avgTouchpoints = Math.round(personas.reduce((sum, p) => sum + p.touchpointCount, 0) / Math.max(personas.length, 1));
    return { total, avgTouchpoints };
  }, [personas]);

  return (
    <ReportShell title={t("personaCatalog.title", "Persona Catalog")} icon="people">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("personaCatalog.subtitle", "Beneficiary personas, demographics, goals, and pain points.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && personas.length === 0 && !error && (
        <Alert severity="info">{t("personaCatalog.empty", "No personas found. Create Persona cards to build your beneficiary model.")}</Alert>
      )}

      {!loading && personas.length > 0 && (
        <>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("personaCatalog.metric.total", "Personas")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                {stats.avgTouchpoints}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("personaCatalog.metric.avgTouchpoints", "Avg Touchpoints")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "success.main" }}>
                {filtered.length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("personaCatalog.metric.shown", "Shown")}
              </Typography>
            </Paper>
          </Box>

          <TextField
            size="small"
            placeholder={t("personaCatalog.search", "Search personas…")}
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
                  <TableCell sx={{ fontWeight: 700 }}>{t("personaCatalog.col.name", "Persona")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 150 }}>{t("personaCatalog.col.demographic", "Demographic")}</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>{t("personaCatalog.col.goal", "Primary Goal")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 150 }}>{t("personaCatalog.col.painPoints", "Pain Points")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("personaCatalog.col.touchpoints", "Touchpoints")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((persona) => (
                  <TableRow key={persona.id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {persona.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={persona.demographic} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{persona.primaryGoal}</Typography>
                    </TableCell>
                    <TableCell>
                      {persona.painPoints.length > 0 ? (
                        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                          {persona.painPoints.map((point, idx) => (
                            <Chip key={idx} size="small" label={point} variant="outlined" sx={{ fontSize: "0.7rem" }} />
                          ))}
                        </Box>
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          —
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Chip size="small" label={persona.touchpointCount} variant="outlined" />
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
