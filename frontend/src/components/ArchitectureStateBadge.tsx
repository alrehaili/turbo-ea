/**
 * ArchitectureStateBadge — chip + menu for a card's architecture-state slice
 * (current / transition / target) and, on non-current cards, the typed change
 * it represents (create / modify / replace / retire / consolidate).
 *
 * [FORK FEATURE] — NORA current/target modelling, noraPlan.md WP2.1.
 */
import { useState } from "react";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import ListSubheader from "@mui/material/ListSubheader";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "./MaterialSymbol";

export type ArchitectureState = "current" | "transition" | "target";
export type ChangeType = "create" | "modify" | "replace" | "retire" | "consolidate";

const STATES: ArchitectureState[] = ["current", "transition", "target"];
const CHANGE_TYPES: ChangeType[] = ["create", "modify", "replace", "retire", "consolidate"];

const STATE_CONFIG: Record<ArchitectureState, { icon: string; color: string }> = {
  current: { icon: "radio_button_checked", color: "#607d8b" },
  transition: { icon: "sync_alt", color: "#f9a825" },
  target: { icon: "flag_circle", color: "#2e7d32" },
};

interface Props {
  state: ArchitectureState;
  changeType: ChangeType | null;
  canChange?: boolean;
  onChange?: (updates: {
    architecture_state?: ArchitectureState;
    change_type?: ChangeType | null;
  }) => void;
}

export default function ArchitectureStateBadge({ state, changeType, canChange, onChange }: Props) {
  const { t } = useTranslation("cards");
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const cfg = STATE_CONFIG[state] ?? STATE_CONFIG.current;
  const interactive = canChange && onChange;

  // The default slice needs no badge on read-only cards — it would be noise
  // on every card. Non-current states are always visible.
  if (state === "current" && !interactive) return null;

  const label =
    state === "current"
      ? t("architectureState.current")
      : changeType
        ? `${t(`architectureState.${state}`)} · ${t(`changeType.${changeType}`)}`
        : t(`architectureState.${state}`);

  return (
    <>
      <Chip
        size="small"
        variant={state === "current" ? "outlined" : "filled"}
        icon={<MaterialSymbol icon={cfg.icon} size={16} color={state === "current" ? cfg.color : "#fff"} />}
        label={label}
        onClick={interactive ? (e) => setAnchorEl(e.currentTarget) : undefined}
        sx={{
          cursor: interactive ? "pointer" : undefined,
          ...(state !== "current" && { bgcolor: cfg.color, color: "#fff" }),
          ...(state === "target" && { borderStyle: "dashed" }),
        }}
      />
      {interactive && (
        <Menu anchorEl={anchorEl} open={!!anchorEl} onClose={() => setAnchorEl(null)}>
          <ListSubheader sx={{ lineHeight: "32px" }}>
            {t("architectureState.title")}
          </ListSubheader>
          {STATES.map((s) => (
            <MenuItem
              key={s}
              selected={s === state}
              onClick={() => {
                onChange({
                  architecture_state: s,
                  // Returning to the live landscape clears the change marker.
                  ...(s === "current" ? { change_type: null } : {}),
                });
                setAnchorEl(null);
              }}
            >
              <MaterialSymbol icon={STATE_CONFIG[s].icon} size={18} color={STATE_CONFIG[s].color} />
              <Typography sx={{ ml: 1 }}>{t(`architectureState.${s}`)}</Typography>
            </MenuItem>
          ))}
          {state !== "current" && <Divider />}
          {state !== "current" && (
            <ListSubheader sx={{ lineHeight: "32px" }}>{t("changeType.title")}</ListSubheader>
          )}
          {state !== "current" &&
            CHANGE_TYPES.map((c) => (
              <MenuItem
                key={c}
                selected={c === changeType}
                onClick={() => {
                  onChange({ change_type: c === changeType ? null : c });
                  setAnchorEl(null);
                }}
              >
                <Typography sx={{ ml: 3.5 }}>{t(`changeType.${c}`)}</Typography>
              </MenuItem>
            ))}
        </Menu>
      )}
    </>
  );
}
