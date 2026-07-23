/**
 * Strategic House Renderer (NORA)
 * Visualizes strategic alignment as a stacked house: Vision → Mission →
 * Pillars → Objectives.
 *
 * Data model (fork): Vision and Mission are stored as settings
 * (`noraVision`/`noraMission`, served by GET /settings/strategy-house), NOT as
 * Objective cards; Pillars are a dedicated `Pillar` card type and their
 * Objectives come from the strategy-cascade relation graph
 * (GET /reports/strategy-cascade). The earlier version guessed all of these
 * from Objective-card names + parent_id and therefore always rendered empty.
 */

import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Alert,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Link,
  MenuItem,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import { api } from "@/api/client";
import ReportShell from "../ReportShell";

interface ObjectiveNode {
  id: string;
  name: string;
  owner?: { id: string; name: string } | null;
}

interface PillarNode {
  id: string;
  name: string;
  objectives: ObjectiveNode[];
}

interface CascadeData {
  pillars: PillarNode[];
  unpillared_objectives: ObjectiveNode[];
}

interface StrategyHouse {
  vision: string;
  mission: string;
}

const COLORS = {
  vision: "#c7527d",
  mission: "#9c27b0",
  pillar: "#2889ff",
  objective: "#0f7eb5",
};

function TextBanner({ title, body, color }: { title: string; body: string; color: string }) {
  return (
    <Box sx={{ mb: 3 }}>
      <Paper sx={{ p: 2, backgroundColor: color, color: "white", mb: 1, borderRadius: 1 }}>
        <Typography variant="overline" sx={{ opacity: 0.85, letterSpacing: 1 }}>
          {title}
        </Typography>
        <Typography variant="h6" sx={{ fontWeight: 600, lineHeight: 1.3 }}>
          {body || <em style={{ opacity: 0.7 }}>Not set — add it on the Strategic House page.</em>}
        </Typography>
      </Paper>
    </Box>
  );
}

export default function StrategicHouseReport() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [house, setHouse] = useState<StrategyHouse | null>(null);
  const [cascade, setCascade] = useState<CascadeData | null>(null);
  const [selectedPillar, setSelectedPillar] = useState<string>("");

  useEffect(() => {
    (async () => {
      try {
        const [h, c] = await Promise.all([
          api.get<StrategyHouse>("/settings/strategy-house"),
          api.get<CascadeData>("/reports/strategy-cascade"),
        ]);
        setHouse(h);
        setCascade(c);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load the strategic house");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const pillars = cascade?.pillars ?? [];
  const displayedPillars = useMemo(
    () => (selectedPillar ? pillars.filter((p) => p.id === selectedPillar) : pillars),
    [pillars, selectedPillar],
  );

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", p: 6 }}>
        <CircularProgress />
      </Box>
    );
  }
  if (error) return <Alert severity="error">{error}</Alert>;

  const hasContent = (house?.vision || house?.mission || pillars.length > 0);

  return (
    <ReportShell title="Strategic House" icon="architecture" hasTableToggle={false}>
      {!hasContent && (
        <Alert severity="info" sx={{ mb: 2 }}>
          No strategy content yet. Set a vision/mission and add{" "}
          <Link component={RouterLink} to="/reports/strategic-house" underline="hover">
            Pillars on the Strategic House page
          </Link>
          .
        </Alert>
      )}

      {pillars.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <TextField
            select
            label="Filter by Pillar"
            value={selectedPillar}
            onChange={(e) => setSelectedPillar(e.target.value)}
            size="small"
            sx={{ minWidth: 220 }}
          >
            <MenuItem value="">All Pillars ({pillars.length})</MenuItem>
            {pillars.map((p) => (
              <MenuItem key={p.id} value={p.id}>
                {p.name}
              </MenuItem>
            ))}
          </TextField>
        </Box>
      )}

      <TextBanner title="Vision" body={house?.vision ?? ""} color={COLORS.vision} />
      <TextBanner title="Mission" body={house?.mission ?? ""} color={COLORS.mission} />

      {/* Pillars row */}
      <Box sx={{ mb: 3 }}>
        <Paper sx={{ p: 2, backgroundColor: COLORS.pillar, color: "white", mb: 1, borderRadius: 1 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Pillars ({displayedPillars.length})
          </Typography>
        </Paper>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: 2,
          }}
        >
          {displayedPillars.map((p) => (
            <Card
              key={p.id}
              component={RouterLink}
              to={`/cards/${p.id}`}
              sx={{
                textDecoration: "none",
                backgroundColor: `${COLORS.pillar}15`,
                borderLeft: `4px solid ${COLORS.pillar}`,
                "&:hover": { boxShadow: 3 },
              }}
            >
              <CardContent sx={{ p: 1.5 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  {p.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {p.objectives.length} objective{p.objectives.length === 1 ? "" : "s"}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Box>

      {/* Objectives under each displayed pillar */}
      {displayedPillars.map((pillar) => (
        <Box key={pillar.id} sx={{ mb: 3 }}>
          <Paper
            sx={{ p: 1.5, backgroundColor: COLORS.objective, color: "white", mb: 1, borderRadius: 1 }}
          >
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              Objectives under {pillar.name}
            </Typography>
          </Paper>
          {pillar.objectives.length === 0 ? (
            <Typography variant="caption" color="text.secondary" sx={{ pl: 1 }}>
              No objectives linked to this pillar yet.
            </Typography>
          ) : (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                gap: 2,
              }}
            >
              {pillar.objectives.map((o) => (
                <Card
                  key={o.id}
                  component={RouterLink}
                  to={`/cards/${o.id}`}
                  sx={{
                    textDecoration: "none",
                    backgroundColor: `${COLORS.objective}15`,
                    borderLeft: `4px solid ${COLORS.objective}`,
                    "&:hover": { boxShadow: 3 },
                  }}
                >
                  <CardContent sx={{ p: 1.5 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      {o.name}
                    </Typography>
                    {o.owner && (
                      <Typography variant="caption" color="text.secondary">
                        {o.owner.name}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              ))}
            </Box>
          )}
        </Box>
      ))}
    </ReportShell>
  );
}
