/**
 * Shared building blocks of the Layers section (ea-ui-mvp visual language):
 * layer constants, the derived healthy/warning/risk status model, and the
 * Panel / HealthLine / NodePill primitives used by the overview pages, the
 * EA dashboard, and the traceability view.
 * [FORK FEATURE] — noraPlan.md (layer overviews).
 */
import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import type { Theme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { getCurrentPhase } from "@/components/LifecycleBadge";
import { CARD_TYPE_COLORS, EXPLORER_COLORS } from "@/theme/tokens";
import type { Card, CardType } from "@/types";

/** The six NORA 2.0 EA layers, top-to-bottom — the layer-stack order. */
export const EA_LAYERS = [
  "Business",
  "Beneficiary Experience",
  "Application",
  "Data",
  "Technology",
  "Security",
] as const;

/** Layer `category` → url slug / i18n key. */
export const LAYER_SLUG: Record<string, string> = {
  Business: "business",
  "Beneficiary Experience": "beneficiary",
  Application: "application",
  Data: "data",
  Technology: "technology",
  Security: "security",
};

export type CardStatus = "healthy" | "warning" | "risk";

export const STATUS_COLOR: Record<CardStatus, string> = {
  healthy: EXPLORER_COLORS.healthy.main,
  warning: EXPLORER_COLORS.warning.main,
  risk: EXPLORER_COLORS.risk.main,
};

/** MVP badge look: pastel surface + darker companion text (mode-aware). */
export function statusChipSx(status: CardStatus) {
  const c = EXPLORER_COLORS[status];
  return (theme: Theme) =>
    theme.palette.mode === "light"
      ? { bgcolor: c.soft, color: c.text, fontWeight: 700 }
      : { bgcolor: `${c.main}33`, color: c.main, fontWeight: 700 };
}

/** MVP tile look: pastel surface + tinted border, for status-coloured cards. */
export function statusSurfaceSx(status: CardStatus) {
  const c = EXPLORER_COLORS[status];
  return (theme: Theme) =>
    theme.palette.mode === "light"
      ? { bgcolor: c.soft, borderColor: c.border }
      : { bgcolor: `${c.main}1a`, borderColor: `${c.main}66` };
}

/** Minimal endpoint shape of a `/relations` row. */
export interface RelCardRef {
  id: string;
  type: string;
  name: string;
}

export interface RelRow {
  id: string;
  type: string;
  source: RelCardRef | null;
  target: RelCardRef | null;
}

/** MVP-style derived status: EOL / very low quality → risk; phase-out / low quality → warning. */
export function cardStatus(c: Card): CardStatus {
  const phase = getCurrentPhase(c.lifecycle);
  const q = c.data_quality ?? 0;
  if (phase === "endOfLife" || q < 50) return "risk";
  if (phase === "phaseOut" || q < 75) return "warning";
  return "healthy";
}

export function scoreStatus(score: number): CardStatus {
  if (score < 50) return "risk";
  if (score < 75) return "warning";
  return "healthy";
}

export function typeColor(ty: CardType): string {
  return ty.color || (CARD_TYPE_COLORS as Record<string, string>)[ty.key] || "#78909c";
}

/** Localized layer name for a card-type category. */
export function useLayerName(): (cat: string) => string {
  const { t } = useTranslation("reports");
  return (cat: string) => {
    const slug = LAYER_SLUG[cat];
    return slug ? t(`layerSwimlane.layerName.${slug}`) : cat;
  };
}

/** Full-page wrapper: the MVP's light blue-grey canvas behind the panels. */
export function ExplorerPage({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={(theme) => ({
        minHeight: "100%",
        bgcolor: theme.palette.mode === "light" ? EXPLORER_COLORS.bg : "transparent",
      })}
    >
      <Box sx={{ p: 3, maxWidth: 1500, mx: "auto" }}>{children}</Box>
    </Box>
  );
}

/** MVP-style panel: eyebrow + heading (+ optional count chip) over content. */
export function Panel({
  eyebrow,
  title,
  count,
  action,
  children,
}: {
  eyebrow: string;
  title: string;
  count?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Paper
      variant="outlined"
      sx={(theme) => ({
        p: 2.5,
        borderRadius: 2.5,
        ...(theme.palette.mode === "light" && {
          borderColor: EXPLORER_COLORS.line,
          boxShadow: EXPLORER_COLORS.shadow,
        }),
      })}
    >
      <Box sx={{ display: "flex", alignItems: "flex-start", mb: 1.5, gap: 1 }}>
        <Box sx={{ flex: 1 }}>
          <Typography
            variant="overline"
            sx={(theme) => ({
              lineHeight: 1.4,
              letterSpacing: 1.1,
              fontWeight: 800,
              color:
                theme.palette.mode === "light"
                  ? EXPLORER_COLORS.primary
                  : theme.palette.primary.light,
            })}
            display="block"
          >
            {eyebrow}
          </Typography>
          <Typography variant="subtitle1" fontWeight={800}>
            {title}
          </Typography>
        </Box>
        {count && (
          <Chip
            size="small"
            label={count}
            sx={(theme) => ({
              fontWeight: 800,
              bgcolor:
                theme.palette.mode === "light" ? EXPLORER_COLORS.bg : theme.palette.action.hover,
              color: "text.secondary",
            })}
          />
        )}
        {action}
      </Box>
      {children}
    </Paper>
  );
}

/** MVP-style node pill used by the integration map / trace diagram. */
export function NodePill({ name, onClick }: { name: string; onClick: () => void }) {
  return (
    <ButtonBase
      onClick={onClick}
      sx={{
        flex: 1,
        minWidth: 0,
        justifyContent: "flex-start",
        bgcolor: "action.hover",
        borderRadius: 99,
        px: 1.5,
        py: 0.5,
        "&:hover": { bgcolor: "action.selected" },
      }}
    >
      <Typography variant="caption" fontWeight={700} noWrap>
        {name}
      </Typography>
    </ButtonBase>
  );
}

/** MVP-style health pill: status dot + mini bar + percentage. */
export function HealthLine({ status, value }: { status: CardStatus; value: number }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
      <Box
        sx={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          bgcolor: STATUS_COLOR[status],
          flexShrink: 0,
        }}
      />
      <Box
        sx={{
          flex: 1,
          height: 6,
          borderRadius: 3,
          bgcolor: "action.hover",
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            width: `${value}%`,
            height: "100%",
            borderRadius: 3,
            bgcolor: STATUS_COLOR[status],
          }}
        />
      </Box>
      <Typography variant="caption" fontWeight={800} sx={{ minWidth: 34, textAlign: "end" }}>
        {value}%
      </Typography>
    </Box>
  );
}
