/**
 * Horizontal timeline of ADM phases for a workspace. Non-continuous phases
 * render as a strip of tiles in canonical order; the continuous
 * ``requirements_management`` phase is surfaced as a chip beside the
 * timeline to make the "cross-cutting" nature obvious.
 *
 * Renders a small tile per phase with status accent, owner avatar, due
 * date, completion bar. Clicking a tile selects the phase; the parent
 * page handles the detail view.
 *
 * [FORK FEATURE]
 */

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import { PHASE_ICONS, PHASE_STATUS_COLORS, PHASE_STATUS_ICONS } from "./admConstants";
import type { AdmPhase } from "./types";

interface Props {
  phases: AdmPhase[];
  activePhaseKey?: string;
  onSelectPhase: (phaseKey: string) => void;
}

export default function AdmPhaseTimeline({ phases, activePhaseKey, onSelectPhase }: Props) {
  const { t } = useTranslation("adm");
  const sequential = phases.filter((p) => !p.is_continuous);
  const continuous = phases.filter((p) => p.is_continuous);

  return (
    <Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, 1fr)",
            md: "repeat(3, 1fr)",
            lg: `repeat(${Math.min(sequential.length, 5)}, 1fr)`,
          },
          gap: 1.25,
        }}
      >
        {sequential.map((p) => (
          <PhaseTile
            key={p.phase_key}
            phase={p}
            active={p.phase_key === activePhaseKey}
            onClick={() => onSelectPhase(p.phase_key)}
          />
        ))}
      </Box>
      {continuous.length > 0 && (
        <Box sx={{ mt: 2, display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
            {t("timeline.continuous")}
          </Typography>
          {continuous.map((p) => (
            <Chip
              key={p.phase_key}
              icon={<MaterialSymbol icon={PHASE_ICONS[p.phase_key] || "assignment"} size={16} />}
              label={`${p.title} · ${p.artefacts.length}`}
              onClick={() => onSelectPhase(p.phase_key)}
              variant={p.phase_key === activePhaseKey ? "filled" : "outlined"}
              color="info"
              size="small"
            />
          ))}
        </Box>
      )}
    </Box>
  );
}

function PhaseTile({
  phase,
  active,
  onClick,
}: {
  phase: AdmPhase;
  active: boolean;
  onClick: () => void;
}) {
  const { t } = useTranslation("adm");
  const color = PHASE_STATUS_COLORS[phase.status];
  const icon = PHASE_ICONS[phase.phase_key] || "flag";
  const overdue =
    phase.due_date &&
    new Date(phase.due_date) < new Date() &&
    phase.status !== "approved" &&
    phase.status !== "skipped";
  return (
    <Box
      role="button"
      onClick={onClick}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " " ? onClick() : null)}
      tabIndex={0}
      sx={{
        cursor: "pointer",
        border: "1px solid",
        borderColor: active ? color : "divider",
        borderLeft: `4px solid ${color}`,
        borderRadius: 1,
        p: 1.25,
        bgcolor: active ? `${color}0d` : "background.paper",
        transition: "background-color 120ms, border-color 120ms",
        "&:hover": { borderColor: color, boxShadow: 2 },
        "&:focus-visible": { outline: `2px solid ${color}`, outlineOffset: 2 },
        minHeight: 122,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}>
        <Box
          sx={{
            width: 26,
            height: 26,
            borderRadius: 0.75,
            bgcolor: `${color}1a`,
            color,
            display: "grid",
            placeItems: "center",
            flexShrink: 0,
          }}
        >
          <MaterialSymbol icon={icon} size={16} color="inherit" />
        </Box>
        <Typography variant="caption" sx={{ fontWeight: 800, flex: 1, minWidth: 0 }} noWrap>
          {phase.title}
        </Typography>
      </Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.75 }}>
        <Chip
          size="small"
          icon={
            <Box sx={{ display: "flex", color }}>
              <MaterialSymbol icon={PHASE_STATUS_ICONS[phase.status]} size={12} color="inherit" />
            </Box>
          }
          label={t(`status.${phase.status}`)}
          sx={{
            borderColor: `${color}55`,
            color,
            fontWeight: 700,
            height: 22,
            fontSize: "0.65rem",
          }}
          variant="outlined"
        />
        {overdue && (
          <Tooltip title={t("timeline.overdue")}>
            <Box sx={{ display: "flex", color: "error.main" }}>
              <MaterialSymbol icon="event_busy" size={16} color="inherit" />
            </Box>
          </Tooltip>
        )}
      </Box>
      <Box sx={{ mt: "auto" }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.25 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem" }}>
            {phase.linked_count}/{phase.required_count || 0} {t("timeline.artefacts")}
          </Typography>
          <Typography variant="caption" sx={{ fontWeight: 700, fontSize: "0.65rem" }}>
            {phase.completion_pct}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={phase.completion_pct}
          sx={{
            height: 4,
            borderRadius: 1,
            bgcolor: "action.hover",
            "& .MuiLinearProgress-bar": { bgcolor: color },
          }}
        />
      </Box>
    </Box>
  );
}
