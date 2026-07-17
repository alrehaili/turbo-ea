/**
 * Persona→Beneficiary Mapping
 * Show how different personas interact with services, journeys, and applications.
 * Part of Phase 9: Beneficiary Experience Views.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
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

interface PersonaJourneyMap {
  personaId: string;
  personaName: string;
  personaSubtype: string;
  journeyCount: number;
  applicationCount: number;
  touchpointCount: number;
  satisfactionLevel: string;
}

export default function PersonaBeneficiaryMapping() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [data, setData] = useState<PersonaJourneyMap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          const [response, journeyRels, appRels, journeyResp] = await Promise.all([
            api.get<{ items: any[] }>("/cards?type=Persona&page_size=500"),
            api.get<any[]>("/relations?type=relJourneyToPersona").catch(() => []),
            api.get<any[]>("/relations?type=relAppToPersona").catch(() => []),
            api.get<{ items: any[] }>("/cards?type=Journey&page_size=500"),
          ]);
          const personas = Array.isArray(response) ? response : response.items || [];
          const journeys = Array.isArray(journeyResp) ? journeyResp : journeyResp.items || [];

          // Real relation counts per persona
          const journeysByPersona = new Map<string, string[]>();
          for (const rel of journeyRels) {
            const list = journeysByPersona.get(rel.target_id) || [];
            list.push(rel.source_id);
            journeysByPersona.set(rel.target_id, list);
          }
          const appsByPersona = new Map<string, number>();
          for (const rel of appRels) {
            appsByPersona.set(rel.target_id, (appsByPersona.get(rel.target_id) || 0) + 1);
          }
          // Satisfaction: worst satisfaction across the persona's journeys
          const journeySatisfaction = new Map<string, string>(
            journeys.map((j) => [j.id, j.attributes?.satisfaction || ""]),
          );
          const order = ["veryLow", "low", "medium", "high", "veryHigh"];
          const worstFor = (personaId: string): string => {
            const linked = journeysByPersona.get(personaId) || [];
            const levels = linked
              .map((jid) => journeySatisfaction.get(jid))
              .filter((s): s is string => Boolean(s));
            if (levels.length === 0) return "—";
            return levels.sort((a, b) => order.indexOf(a) - order.indexOf(b))[0];
          };

          const mappings: PersonaJourneyMap[] = personas.map((p) => ({
            personaId: p.id,
            personaName: p.name,
            personaSubtype: p.subtype || "general",
            journeyCount: (journeysByPersona.get(p.id) || []).length,
            applicationCount: appsByPersona.get(p.id) || 0,
            touchpointCount: p.attributes?.preferredChannels ? (typeof p.attributes.preferredChannels === "string" ? p.attributes.preferredChannels.split(",").length : 1) : 0,
            satisfactionLevel: worstFor(p.id),
          }));

          setData(mappings);
        } catch (err) {
          setError("Failed to load persona mappings");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const filtered = useMemo(
    () => data.filter((m) => m.personaName.toLowerCase().includes(search.toLowerCase())),
    [data, search]
  );

  const stats = useMemo(() => ({
    totalPersonas: data.length,
    avgJourneys: Math.round(data.reduce((sum, m) => sum + m.journeyCount, 0) / Math.max(data.length, 1)),
    avgApplications: Math.round(data.reduce((sum, m) => sum + m.applicationCount, 0) / Math.max(data.length, 1)),
    avgTouchpoints: Math.round(data.reduce((sum, m) => sum + m.touchpointCount, 0) / Math.max(data.length, 1)),
  }), [data]);

  const getSatisfactionColor = (level: string): string => {
    switch (level) {
      case "veryLow": return "#d32f2f";
      case "low": return "#f44336";
      case "medium": return "#ff9800";
      case "high": return "#8bc34a";
      case "veryHigh": return "#4caf50";
      default: return "#9e9e9e";
    }
  };

  const getSubtypeLabel = (subtype: string): string => {
    const labels: Record<string, string> = {
      employee: "Employee",
      customer: "Customer",
      partner: "Partner",
      beneficiary: "Beneficiary",
    };
    return labels[subtype] || subtype;
  };

  return (
    <ReportShell title={t("personaBeneficiaryMapping.title", "Persona→Beneficiary Mapping")} icon="people">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("personaBeneficiaryMapping.subtitle", "Map beneficiary personas to their journeys, applications, and touchpoints across the organization.")}
      </Typography>

      {/* KPI Cards */}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(4, 1fr)" }, gap: 2, mb: 4 }}>
        <Paper sx={{ p: 2, textAlign: "center" }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: "primary.main" }}>
            {stats.totalPersonas}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("personaBeneficiaryMapping.metric.personas", "Personas")}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, textAlign: "center" }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: "secondary.main" }}>
            {stats.avgJourneys}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("personaBeneficiaryMapping.metric.journeys", "Avg Journeys")}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, textAlign: "center" }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: "info.main" }}>
            {stats.avgApplications}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("personaBeneficiaryMapping.metric.applications", "Avg Applications")}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, textAlign: "center" }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: "success.main" }}>
            {stats.avgTouchpoints}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("personaBeneficiaryMapping.metric.touchpoints", "Avg Touchpoints")}
          </Typography>
        </Paper>
      </Box>

      {/* Search */}
      <TextField
        size="small"
        placeholder={t("personaBeneficiaryMapping.search", "Search personas…")}
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
        sx={{ mb: 3, maxWidth: 360 }}
      />

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && data.length === 0 && !error && (
        <Alert severity="info">{t("personaBeneficiaryMapping.empty", "No personas found.")}</Alert>
      )}

      {!loading && filtered.length > 0 && (
        <>
          {/* Mapping Grid */}
          <Grid container spacing={2} sx={{ mb: 4 }}>
            {filtered.map((mapping) => (
              <Grid item xs={12} sm={6} md={4} key={mapping.personaId}>
                <Card
                  sx={{
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                    transition: "all 0.2s ease",
                    "&:hover": {
                      boxShadow: 4,
                      transform: "translateY(-2px)",
                    },
                  }}
                >
                  <CardContent sx={{ flex: 1 }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                      <MaterialSymbol icon="person" size={24} color="primary" />
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                          {mapping.personaName}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {getSubtypeLabel(mapping.personaSubtype)}
                        </Typography>
                      </Box>
                    </Box>

                    <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
                      <Chip
                        size="small"
                        label={`${mapping.journeyCount} Journeys`}
                        icon={<MaterialSymbol icon="trending_flat" size={16} />}
                        variant="outlined"
                      />
                      <Chip
                        size="small"
                        label={`${mapping.applicationCount} Apps`}
                        icon={<MaterialSymbol icon="apps" size={16} />}
                        variant="outlined"
                      />
                      <Chip
                        size="small"
                        label={`${mapping.touchpointCount} Touchpoints`}
                        icon={<MaterialSymbol icon="touch_app" size={16} />}
                        variant="outlined"
                      />
                    </Box>

                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        {t("personaBeneficiaryMapping.satisfaction", "Satisfaction:")}
                      </Typography>
                      <Chip
                        size="small"
                        label={mapping.satisfactionLevel}
                        sx={{
                          backgroundColor: getSatisfactionColor(mapping.satisfactionLevel),
                          color: "white",
                          fontSize: "0.7rem",
                        }}
                      />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {/* Detailed Table */}
          <Paper variant="outlined" sx={{ overflow: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: "#fafafa" }}>
                  <TableCell sx={{ fontWeight: 700 }}>{t("personaBeneficiaryMapping.col.persona", "Persona")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("personaBeneficiaryMapping.col.type", "Type")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("personaBeneficiaryMapping.col.journeys", "Journeys")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("personaBeneficiaryMapping.col.applications", "Applications")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("personaBeneficiaryMapping.col.touchpoints", "Touchpoints")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 100, textAlign: "center" }}>{t("personaBeneficiaryMapping.col.satisfaction", "Satisfaction")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((mapping) => (
                  <TableRow key={mapping.personaId} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {mapping.personaName}
                      </Typography>
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Chip size="small" label={getSubtypeLabel(mapping.personaSubtype)} variant="outlined" />
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Typography variant="caption">{mapping.journeyCount}</Typography>
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Typography variant="caption">{mapping.applicationCount}</Typography>
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Typography variant="caption">{mapping.touchpointCount}</Typography>
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Chip
                        size="small"
                        label={mapping.satisfactionLevel}
                        sx={{
                          backgroundColor: getSatisfactionColor(mapping.satisfactionLevel),
                          color: "white",
                          fontSize: "0.7rem",
                        }}
                      />
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
