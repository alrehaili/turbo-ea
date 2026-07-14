import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";

interface Props {
  label: string;
  value: string | number;
  icon?: string;
  iconColor?: string;
  /**
   * Small helper text below the value. Accepts a string (default) or a
   * ReactNode when the caller needs an interactive element such as a link
   * that jumps to the filtered inventory row this metric represents.
   */
  subtitle?: ReactNode;
  color?: string;
  /**
   * Screen-reader label for the tile. When omitted, an aria-label is
   * synthesised as `"{label}: {value}"` — the icon is decorative and the
   * subtitle may be a link with its own accessible name, so the tile itself
   * gets read as a single fact.
   */
  ariaLabel?: string;
}

export default function MetricCard({
  label,
  value,
  icon,
  iconColor = "#1976d2",
  subtitle,
  color,
  ariaLabel,
}: Props) {
  return (
    <Paper
      variant="outlined"
      role="group"
      aria-label={ariaLabel ?? `${label}: ${value}`}
      sx={{
        p: 2,
        minWidth: 150,
        flex: "1 1 150px",
        borderLeft: color ? `4px solid ${color}` : undefined,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
        {icon && <MaterialSymbol icon={icon} size={18} color={iconColor} />}
        <Typography variant="caption" color="text.secondary" noWrap>
          {label}
        </Typography>
      </Box>
      <Typography variant="h5" sx={{ fontWeight: 700 }}>
        {value}
      </Typography>
      {subtitle && (
        <Typography variant="caption" color="text.secondary">
          {subtitle}
        </Typography>
      )}
    </Paper>
  );
}
