/**
 * "My ADM actions" widget embedded in the app Dashboard overview.
 *
 * Shows three groups:
 *   - Pending gate approvals (for adm.approve_gate holders)
 *   - Blocked phases the user owns
 *   - Overdue phases the user owns
 *
 * Silently hides if the user has no ADM permissions or nothing to act on.
 *
 * [FORK FEATURE]
 */

import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useAuthContext } from "@/hooks/AuthContext";
import { api } from "@/api/client";
import { PHASE_STATUS_COLORS } from "./admConstants";
import type { AdmMyActions, AdmPhaseStatus } from "./types";

export default function AdmDashboardWidget() {
  const { t } = useTranslation("adm");
  const { user } = useAuthContext();
  const [data, setData] = useState<AdmMyActions | null>(null);

  const canView = !!(user?.permissions?.["*"] || user?.permissions?.["adm.view"]);

  useEffect(() => {
    if (!canView) return;
    api
      .get<AdmMyActions>("/adm/my-actions")
      .then(setData)
      .catch(() => setData(null));
  }, [canView]);

  if (!canView || !data) return null;
  const total = data.pending_gate.length + data.blocked.length + data.overdue.length;
  if (total === 0) return null;

  const row = (
    key: string,
    icon: string,
    color: AdmPhaseStatus,
    items: AdmMyActions["blocked"],
  ) => {
    if (items.length === 0) return null;
    return (
      <Box sx={{ mb: 1 }}>
        <Typography
          variant="caption"
          sx={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 0.5 }}
        >
          <Box sx={{ color: PHASE_STATUS_COLORS[color], display: "flex" }}>
            <MaterialSymbol icon={icon} size={14} color="inherit" />
          </Box>
          {t(`dashboard.${key}`, { count: items.length })}
        </Typography>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, mt: 0.5 }}>
          {items.slice(0, 5).map((p) => (
            <Chip
              key={p.id}
              size="small"
              component={RouterLink}
              to={`/ea-delivery/adm/${p.workspace_id}?phase=${p.phase_key}`}
              clickable
              variant="outlined"
              label={p.title}
              sx={{ justifyContent: "flex-start" }}
            />
          ))}
          {items.length > 5 && (
            <Typography variant="caption" color="text.secondary">
              +{items.length - 5}
            </Typography>
          )}
        </Box>
      </Box>
    );
  };

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
        <MaterialSymbol icon="account_tree" size={20} color="#0f7eb5" />
        <Typography variant="subtitle1" sx={{ fontWeight: 800, flex: 1 }}>
          {t("dashboard.title")}
        </Typography>
        <Chip size="small" label={total} />
      </Box>
      {row("pendingGate", "how_to_reg", "ready_for_gate", data.pending_gate)}
      {row("blocked", "block", "blocked", data.blocked)}
      {row("overdue", "event_busy", "in_progress", data.overdue)}
    </Paper>
  );
}
