/**
 * Beneficiary Journey Map Renderer (NORA)
 * Visualizes beneficiary journeys from their REAL card data: each root
 * BeneficiaryJourney (subtype `journeyPhase`) with its "Journey Mapping"
 * attributes (stage, objective, improvement opportunity, expected impact,
 * priority) and any child `journeyStep` cards as an ordered timeline.
 *
 * The earlier version discarded the real cards and injected identical
 * hardcoded mock stages/touchpoints for every journey — this reads the actual
 * hierarchy + attributes and resolves select-option labels from the metamodel.
 */

import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Link,
  Paper,
  Typography,
} from "@mui/material";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";
import ReportShell from "../ReportShell";

interface JourneyCard {
  id: string;
  name: string;
  subtype?: string | null;
  parent_id?: string | null;
  description?: string;
  attributes?: Record<string, unknown>;
}

const PRIORITY_COLORS: Record<string, string> = {
  high: "#c7527d",
  medium: "#ed6c02",
  low: "#0288d1",
};

export default function BeneficiaryJourneyMapReport() {
  const { types } = useMetamodel();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cards, setCards] = useState<JourneyCard[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const resp = await api.get<{ items: JourneyCard[] }>(
          "/cards?type=BeneficiaryJourney&page_size=500",
        );
        setCards(resp.items || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load journeys");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Resolve a select field's stored key to its metamodel option label.
  const optionLabel = useMemo(() => {
    const bt = types.find((t) => t.key === "BeneficiaryJourney");
    const map: Record<string, Record<string, string>> = {};
    for (const section of bt?.fields_schema ?? []) {
      for (const f of section.fields ?? []) {
        if (f.options?.length) {
          map[f.key] = Object.fromEntries(f.options.map((o) => [o.key, o.label]));
        }
      }
    }
    return (fieldKey: string, value: unknown): string => {
      if (value == null || value === "") return "";
      const s = String(value);
      return map[fieldKey]?.[s] ?? s;
    };
  }, [types]);

  const ids = useMemo(() => new Set(cards.map((c) => c.id)), [cards]);
  const roots = useMemo(
    () => cards.filter((c) => !c.parent_id || !ids.has(c.parent_id)),
    [cards, ids],
  );
  const childrenOf = useMemo(() => {
    const m: Record<string, JourneyCard[]> = {};
    for (const c of cards) {
      if (c.parent_id && ids.has(c.parent_id)) (m[c.parent_id] ??= []).push(c);
    }
    return m;
  }, [cards, ids]);

  const selected = roots.find((r) => r.id === selectedId) ?? roots[0] ?? null;

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", p: 6 }}>
        <CircularProgress />
      </Box>
    );
  }
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!selected) {
    return (
      <Alert severity="info">
        No beneficiary journeys yet. Create a BeneficiaryJourney card first.
      </Alert>
    );
  }

  const a = selected.attributes ?? {};
  const steps = childrenOf[selected.id] ?? [];
  const priority = String(a.improvementPriority ?? "").toLowerCase();

  const attrRow = (label: string, fieldKey: string) => {
    const v = optionLabel(fieldKey, a[fieldKey]);
    if (!v) return null;
    return (
      <Box sx={{ mb: 1 }}>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", fontWeight: 600 }}>
          {label}
        </Typography>
        <Typography variant="body2">{v}</Typography>
      </Box>
    );
  };

  return (
    <ReportShell title="Beneficiary Journey Map" icon="route" hasTableToggle={false}>
      {/* Journey selector */}
      <Box sx={{ mb: 3, display: "flex", gap: 1, flexWrap: "wrap" }}>
        {roots.map((j) => (
          <Chip
            key={j.id}
            label={j.name}
            onClick={() => setSelectedId(j.id)}
            color={selected.id === j.id ? "primary" : "default"}
            variant={selected.id === j.id ? "filled" : "outlined"}
          />
        ))}
      </Box>

      {/* Selected journey header */}
      <Paper sx={{ p: 2.5, mb: 3, borderLeft: `4px solid ${PRIORITY_COLORS[priority] || "#2889ff"}` }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mb: 1 }}>
          <Link
            component={RouterLink}
            to={`/cards/${selected.id}`}
            underline="hover"
            variant="h6"
            sx={{ fontWeight: 700 }}
          >
            {selected.name}
          </Link>
          {a.journeyCode ? (
            <Chip size="small" variant="outlined" label={String(a.journeyCode)} />
          ) : null}
          {a.journeyStage ? (
            <Chip size="small" variant="outlined" label={optionLabel("journeyStage", a.journeyStage)} />
          ) : null}
          {priority ? (
            <Chip
              size="small"
              label={optionLabel("improvementPriority", a.improvementPriority)}
              sx={{ bgcolor: PRIORITY_COLORS[priority] || "#9e9e9e", color: "white" }}
            />
          ) : null}
        </Box>
        {selected.description && (
          <Typography variant="body2" color="text.secondary">
            {selected.description}
          </Typography>
        )}
      </Paper>

      <Grid container spacing={2}>
        {/* Objective + improvement (the real Journey-Mapping fields) */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
                Objective & Improvement
              </Typography>
              {attrRow("Journey objective", "journeyObjective")}
              {attrRow("Improvement opportunity", "improvementOpportunity")}
              {attrRow("Expected impact", "expectedImpact")}
              {attrRow("Associated gaps", "associatedGaps")}
              {!a.journeyObjective &&
                !a.improvementOpportunity &&
                !a.expectedImpact &&
                !a.associatedGaps && (
                  <Typography variant="caption" color="text.secondary">
                    No journey-mapping details captured yet.
                  </Typography>
                )}
            </CardContent>
          </Card>
        </Grid>

        {/* Child steps timeline (real journeyStep cards, if any) */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
                Steps ({steps.length})
              </Typography>
              {steps.length === 0 ? (
                <Typography variant="caption" color="text.secondary">
                  No steps linked to this journey. Add child cards (subtype “Journey step”) to build
                  the timeline.
                </Typography>
              ) : (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {steps.map((s, idx) => (
                    <Box key={s.id} sx={{ display: "flex", gap: 1.5, alignItems: "flex-start" }}>
                      <Box
                        sx={{
                          flexShrink: 0,
                          width: 26,
                          height: 26,
                          borderRadius: "50%",
                          bgcolor: "primary.main",
                          color: "white",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "0.8rem",
                          fontWeight: 700,
                        }}
                      >
                        {idx + 1}
                      </Box>
                      <Box>
                        <Link
                          component={RouterLink}
                          to={`/cards/${s.id}`}
                          underline="hover"
                          sx={{ fontWeight: 600 }}
                        >
                          {s.name}
                        </Link>
                        {s.attributes?.journeyObjective ? (
                          <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                            {String(s.attributes.journeyObjective)}
                          </Typography>
                        ) : null}
                      </Box>
                    </Box>
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Summary across all journeys */}
      <Paper sx={{ p: 2, mt: 3, backgroundColor: "action.hover", borderRadius: 1 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
          Portfolio summary
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={6} sm={3}>
            <Box sx={{ textAlign: "center" }}>
              <Typography variant="h6" color="primary">
                {roots.length}
              </Typography>
              <Typography variant="caption">Journeys</Typography>
            </Box>
          </Grid>
          {(["high", "medium", "low"] as const).map((p) => (
            <Grid item xs={6} sm={3} key={p}>
              <Box sx={{ textAlign: "center" }}>
                <Typography variant="h6" sx={{ color: PRIORITY_COLORS[p] }}>
                  {roots.filter(
                    (r) => String(r.attributes?.improvementPriority ?? "").toLowerCase() === p,
                  ).length}
                </Typography>
                <Typography variant="caption" sx={{ textTransform: "capitalize" }}>
                  {p} priority
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
      </Paper>
    </ReportShell>
  );
}
