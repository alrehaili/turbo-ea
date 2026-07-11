/**
 * StrategyCascadeReport — the agency's strategy chain on one screen:
 * Strategic Pillars ⊃ Strategic Objectives → Programs ⊃ Initiatives ⊃
 * Projects. Pillars/objectives ride the Objective hierarchy (pillar
 * subtype); delivery rides the Objective↔Initiative relation plus the
 * Initiative hierarchy (program/project subtypes). Initiatives with no
 * strategic alignment anywhere in their chain are flagged.
 *
 * [FORK FEATURE].
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";

interface InitiativeNode {
  id: string;
  name: string;
  subtype: string | null;
  children: InitiativeNode[];
}

interface ObjectiveEntry {
  id: string;
  name: string;
  initiatives: InitiativeNode[];
}

interface PillarEntry {
  id: string;
  name: string;
  objectives: ObjectiveEntry[];
}

interface CascadeData {
  pillars: PillarEntry[];
  unpillared_objectives: ObjectiveEntry[];
  unaligned_initiatives: InitiativeNode[];
  summary: {
    pillars: number;
    objectives: number;
    programs: number;
    initiatives: number;
    projects: number;
    unaligned: number;
  };
}

const PILLAR_COLOR = "#7b1fa2";
const SUBTYPE_STYLE: Record<string, { icon: string; color: string }> = {
  program: { icon: "flag_circle", color: "#1976d2" },
  project: { icon: "task_alt", color: "#33cc58" },
  epic: { icon: "bolt", color: "#7b1fa2" },
  idea: { icon: "lightbulb", color: "#9e9e9e" },
};

export default function StrategyCascadeReport() {
  const { t } = useTranslation(["reports"]);
  const [data, setData] = useState<CascadeData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<CascadeData>("/reports/strategy-cascade")
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "error"));
  }, []);

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }
  if (!data) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const subtypeLabel = (subtype: string | null) =>
    t(`strategyCascade.level.${subtype ?? "initiative"}`);

  const renderInitiative = (node: InitiativeNode, depth: number) => {
    const style = SUBTYPE_STYLE[node.subtype ?? ""] ?? {
      icon: "rocket_launch",
      color: "#33cc58",
    };
    return (
      <Box key={node.id}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            py: 0.4,
            pl: depth * 3,
          }}
        >
          <MaterialSymbol icon={style.icon} size={16} color={style.color} />
          <Link component={RouterLink} to={`/cards/${node.id}`} underline="hover">
            {node.name}
          </Link>
          <Chip
            size="small"
            variant="outlined"
            label={subtypeLabel(node.subtype)}
            sx={{ height: 18, borderColor: style.color, color: style.color }}
          />
        </Box>
        {node.children.map((c) => renderInitiative(c, depth + 1))}
      </Box>
    );
  };

  const renderObjective = (o: ObjectiveEntry) => (
    <Box key={o.id} sx={{ mb: 1.5 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <MaterialSymbol icon="flag" size={18} color={PILLAR_COLOR} />
        <Link
          component={RouterLink}
          to={`/cards/${o.id}`}
          underline="hover"
          sx={{ fontWeight: 600 }}
        >
          {o.name}
        </Link>
      </Box>
      {o.initiatives.length === 0 ? (
        <Typography variant="caption" color="text.secondary" sx={{ pl: 3.5 }}>
          {t("strategyCascade.noDelivery")}
        </Typography>
      ) : (
        <Box sx={{ pl: 3.5 }}>{o.initiatives.map((n) => renderInitiative(n, 0))}</Box>
      )}
    </Box>
  );

  const tiles: { label: string; value: number; icon: string; color: string }[] = [
    { label: t("strategyCascade.tilePillars"), value: data.summary.pillars, icon: "temple_buddhist", color: PILLAR_COLOR },
    { label: t("strategyCascade.tileObjectives"), value: data.summary.objectives, icon: "flag", color: "#c7527d" },
    { label: t("strategyCascade.tilePrograms"), value: data.summary.programs, icon: "flag_circle", color: "#1976d2" },
    { label: t("strategyCascade.tileInitiatives"), value: data.summary.initiatives, icon: "rocket_launch", color: "#33cc58" },
    { label: t("strategyCascade.tileProjects"), value: data.summary.projects, icon: "task_alt", color: "#2e7d32" },
  ];

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        {t("strategyCascade.title")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("strategyCascade.subtitle")}
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        {tiles.map((tile) => (
          <Grid item xs={6} sm={4} md={2.4} key={tile.label}>
            <Paper sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
              <MaterialSymbol icon={tile.icon} size={24} color={tile.color} />
              <Box>
                <Typography variant="h6" fontWeight={700} lineHeight={1.1}>
                  {tile.value}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {tile.label}
                </Typography>
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {data.summary.unaligned > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {t("strategyCascade.unalignedWarning", { n: data.summary.unaligned })}
        </Alert>
      )}

      {data.pillars.length === 0 && data.unpillared_objectives.length === 0 ? (
        <Alert severity="info">{t("strategyCascade.empty")}</Alert>
      ) : (
        <>
          {data.pillars.map((p) => (
            <Paper key={p.id} variant="outlined" sx={{ mb: 2 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  px: 2,
                  py: 1,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                  borderTop: `3px solid ${PILLAR_COLOR}`,
                }}
              >
                <MaterialSymbol icon="temple_buddhist" size={20} color={PILLAR_COLOR} />
                <Link
                  component={RouterLink}
                  to={`/cards/${p.id}`}
                  underline="hover"
                  sx={{ fontWeight: 700 }}
                >
                  {p.name}
                </Link>
                <Chip
                  size="small"
                  variant="outlined"
                  label={`${p.objectives.length} ${t("strategyCascade.objectives")}`}
                />
              </Box>
              <Box sx={{ p: 2 }}>
                {p.objectives.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    {t("strategyCascade.noObjectives")}
                  </Typography>
                ) : (
                  p.objectives.map(renderObjective)
                )}
              </Box>
            </Paper>
          ))}

          {data.unpillared_objectives.length > 0 && (
            <Paper variant="outlined" sx={{ mb: 2 }}>
              <Box sx={{ px: 2, py: 1, borderBottom: "1px solid", borderColor: "divider" }}>
                <Typography fontWeight={700}>
                  {t("strategyCascade.unpillared")}
                </Typography>
              </Box>
              <Box sx={{ p: 2 }}>{data.unpillared_objectives.map(renderObjective)}</Box>
            </Paper>
          )}
        </>
      )}

      {data.unaligned_initiatives.length > 0 && (
        <Paper variant="outlined" sx={{ borderColor: "warning.main" }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: 2,
              py: 1,
              borderBottom: "1px solid",
              borderColor: "divider",
            }}
          >
            <MaterialSymbol icon="warning" size={18} color="#f57c00" />
            <Typography fontWeight={700}>{t("strategyCascade.unalignedSection")}</Typography>
          </Box>
          <Box sx={{ p: 2 }}>
            {data.unaligned_initiatives.map((n) => renderInitiative(n, 0))}
          </Box>
        </Paper>
      )}
    </Box>
  );
}
