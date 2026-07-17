/**
 * NEA Viewpoints Dashboard
 * Comprehensive summary of all 47 NEA (National EA) viewpoints
 * organized by domain and methodology phase.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardActionArea from "@mui/material/CardActionArea";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import InputAdornment from "@mui/material/InputAdornment";
import MaterialSymbol from "@/components/MaterialSymbol";
import { NEA_VIEWPOINTS, NeaViewpoint } from "./neaViewpoints";
import ReportShell from "./ReportShell";

interface ViewpointGroup {
  phase: string;
  domain: string;
  viewpoints: NeaViewpoint[];
}

export default function NEAViewpointsDashboard() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [selectedPhase, setSelectedPhase] = useState<string | null>(null);
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);

  const phases = useMemo(() => {
    const phaseMap = new Map<string, string>();
    NEA_VIEWPOINTS.forEach((vp: NeaViewpoint) => {
      const match = vp.key.match(/^phase(\d)/);
      if (match) {
        const phaseNum = match[1];
        if (!phaseMap.has(phaseNum)) {
          phaseMap.set(phaseNum, `Phase ${phaseNum}`);
        }
      }
    });
    return Array.from(phaseMap.values()).sort();
  }, []);

  const domains = useMemo(() => {
    const domainSet = new Set<string>();
    NEA_VIEWPOINTS.forEach((vp: NeaViewpoint) => {
      domainSet.add(vp.domain);
    });
    return Array.from(domainSet).sort();
  }, []);

  const groupedViewpoints = useMemo(() => {
    const groups = new Map<string, ViewpointGroup>();

    NEA_VIEWPOINTS.forEach((vp: NeaViewpoint) => {
      const match = vp.key.match(/^phase(\d)/);
      if (match) {
        const phaseNum = match[1];
        const phase = `Phase ${phaseNum}`;
        const domain = vp.domain;
        const key = `${phase}|${domain}`;

        if (!groups.has(key)) {
          groups.set(key, { phase, domain, viewpoints: [] });
        }
        groups.get(key)!.viewpoints.push(vp);
      }
    });

    return Array.from(groups.values())
      .sort((a: ViewpointGroup, b: ViewpointGroup) => {
        const phaseA = parseInt(a.phase.replace("Phase ", ""));
        const phaseB = parseInt(b.phase.replace("Phase ", ""));
        if (phaseA !== phaseB) return phaseA - phaseB;
        return a.domain.localeCompare(b.domain);
      });
  }, []);

  const filtered = useMemo(() => {
    return groupedViewpoints
      .map((group) => ({
        ...group,
        viewpoints: group.viewpoints.filter((vp) => {
          const matchesSearch =
            vp.nameEn.toLowerCase().includes(search.toLowerCase()) ||
            vp.domain.toLowerCase().includes(search.toLowerCase()) ||
            (vp.questionEn && vp.questionEn.toLowerCase().includes(search.toLowerCase()));
          const matchesPhase = !selectedPhase || group.phase === selectedPhase;
          const matchesDomain = !selectedDomain || group.domain === selectedDomain;
          return matchesSearch && matchesPhase && matchesDomain;
        }),
      }))
      .filter((group) => group.viewpoints.length > 0);
  }, [groupedViewpoints, search, selectedPhase, selectedDomain]);

  const stats = useMemo(() => {
    return {
      total: NEA_VIEWPOINTS.length,
      grouped: filtered.length > 0 ? filtered.reduce((sum, g) => sum + g.viewpoints.length, 0) : 0,
      phases: phases.length,
      domains: domains.length,
    };
  }, [filtered, phases, domains]);

  const getKindColor = (kind: string): string => {
    switch (kind) {
      case "list":
        return "#2196f3";
      case "matrix":
        return "#ff9800";
      case "diagram":
        return "#4caf50";
      default:
        return "#9e9e9e";
    }
  };

  const getLevelColor = (level: string): string => {
    switch (level) {
      case "conceptual":
        return "#6200ea";
      case "logical":
        return "#1976d2";
      case "physical":
        return "#00897b";
      default:
        return "#757575";
    }
  };

  return (
    <ReportShell title={t("neaDashboard.title", "NEA Viewpoints Dashboard")} icon="dashboard">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("neaDashboard.subtitle", "Complete reference of all 47 National EA viewpoints organized by methodology phase and domain.")}
      </Typography>

      {/* KPI Cards */}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(4, 1fr)" }, gap: 2, mb: 4 }}>
        <Paper sx={{ p: 2, textAlign: "center" }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: "primary.main" }}>
            {stats.total}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("neaDashboard.metric.total", "Total Viewpoints")}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, textAlign: "center" }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: "secondary.main" }}>
            {stats.phases}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("neaDashboard.metric.phases", "Methodology Phases")}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, textAlign: "center" }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: "success.main" }}>
            {stats.domains}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("neaDashboard.metric.domains", "EA Domains")}
          </Typography>
        </Paper>
        <Paper sx={{ p: 2, textAlign: "center" }}>
          <Typography variant="h5" sx={{ fontWeight: 700, color: "warning.main" }}>
            {stats.grouped}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("neaDashboard.metric.filtered", "Filtered")}
          </Typography>
        </Paper>
      </Box>

      {/* Search and Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <TextField
          fullWidth
          size="small"
          placeholder={t("neaDashboard.search", "Search viewpoints, domains, or questions…")}
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
          sx={{ mb: 2 }}
        />

        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap", flex: 1 }}>
            <Typography variant="caption" sx={{ fontWeight: 600, minWidth: 60 }}>
              {t("neaDashboard.filter.phase", "Phase:")}
            </Typography>
            {phases.map((phase) => (
              <Chip
                key={phase}
                label={phase}
                size="small"
                onClick={() => setSelectedPhase(selectedPhase === phase ? null : phase)}
                variant={selectedPhase === phase ? "filled" : "outlined"}
                sx={{
                  backgroundColor: selectedPhase === phase ? "primary.main" : "transparent",
                  color: selectedPhase === phase ? "white" : "primary.main",
                }}
              />
            ))}
          </Box>
        </Box>

        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 2 }}>
          <Typography variant="caption" sx={{ fontWeight: 600, minWidth: 60 }}>
            {t("neaDashboard.filter.domain", "Domain:")}
          </Typography>
          {domains.map((domain) => (
            <Chip
              key={domain}
              label={domain}
              size="small"
              onClick={() => setSelectedDomain(selectedDomain === domain ? null : domain)}
              variant={selectedDomain === domain ? "filled" : "outlined"}
              sx={{
                backgroundColor: selectedDomain === domain ? "secondary.main" : "transparent",
                color: selectedDomain === domain ? "white" : "secondary.main",
              }}
            />
          ))}
        </Box>
      </Paper>

      {/* Viewpoints Grid */}
      {filtered.length === 0 && !search && !selectedPhase && !selectedDomain ? (
        <Alert severity="info">{t("neaDashboard.loading", "Loading viewpoints…")}</Alert>
      ) : filtered.length === 0 ? (
        <Alert severity="warning">{t("neaDashboard.noResults", "No viewpoints match your filters.")}</Alert>
      ) : (
        filtered.map((group) => (
          <Box key={`${group.phase}|${group.domain}`} sx={{ mb: 4 }}>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 700,
                mb: 2,
                pb: 1,
                borderBottom: "2px solid",
                borderColor: "primary.main",
              }}
            >
              {group.phase} → {group.domain}
            </Typography>

            <Grid container spacing={2}>
              {group.viewpoints.map((viewpoint: NeaViewpoint) => (
                <Grid item xs={12} sm={6} md={4} key={viewpoint.key}>
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
                    <CardActionArea
                      sx={{
                        flex: 1,
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "flex-start",
                      }}
                    >
                      <CardContent sx={{ width: "100%", flex: 1 }}>
                        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1, mb: 1 }}>
                          {viewpoint.icon ? (
                            <MaterialSymbol icon={viewpoint.icon} size={24} color="primary" />
                          ) : null}
                          <Box sx={{ flex: 1 }}>
                            <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                              {viewpoint.nameEn}
                            </Typography>
                          </Box>
                        </Box>

                        {viewpoint.questionEn ? (
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: "italic" }}>
                            "{viewpoint.questionEn}"
                          </Typography>
                        ) : null}

                        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
                          <Chip
                            size="small"
                            label={viewpoint.kind}
                            sx={{
                              backgroundColor: getKindColor(viewpoint.kind),
                              color: "white",
                              fontSize: "0.7rem",
                            }}
                          />
                          <Chip
                            size="small"
                            label={viewpoint.level}
                            sx={{
                              backgroundColor: getLevelColor(viewpoint.level),
                              color: "white",
                              fontSize: "0.7rem",
                            }}
                          />
                        </Box>

                        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                          <strong>{t("neaDashboard.key", "Key")}:</strong> {viewpoint.key}
                        </Typography>

                        {viewpoint.status === "available" ? (
                          <Chip size="small" label={t("neaDashboard.status.available", "Available")} color="success" variant="outlined" />
                        ) : null}
                      </CardContent>
                    </CardActionArea>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        ))
      )}

      {/* Footer Summary */}
      <Paper sx={{ p: 2, mt: 4, backgroundColor: "#f5f5f5" }}>
        <Typography variant="body2" sx={{ mb: 1 }}>
          <strong>{t("neaDashboard.summary", "Summary")}:</strong>
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t("neaDashboard.summaryText", "All 47 NEA viewpoints are organized across {{phases}} methodology phases and {{domains}} EA domains. Each viewpoint is defined by its stakeholder questions, visualization kind (list/matrix/diagram), and abstraction level (conceptual/logical/physical).", {
            phases: stats.phases,
            domains: stats.domains,
          })}
        </Typography>
      </Paper>
    </ReportShell>
  );
}
