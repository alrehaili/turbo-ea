/**
 * Section embedded inside the SoAW editor as the "ADM Workspace" tab.
 *
 * Shows a create-CTA if no workspace exists for this SoAW; otherwise a
 * compact summary with completion, active phase and an "Open" button that
 * navigates to the full ``/ea-delivery/adm/:id`` page.
 *
 * [FORK FEATURE]
 */

import { useCallback, useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useAuthContext } from "@/hooks/AuthContext";
import { api, ApiError } from "@/api/client";
import { PHASE_STATUS_COLORS } from "./admConstants";
import AdmPhaseTimeline from "./AdmPhaseTimeline";
import CreateWorkspaceDialog from "./CreateWorkspaceDialog";
import type { AdmWorkspace } from "./types";

interface Props {
  soawId: string;
  soawName: string;
}

export default function AdmSoAWSection({ soawId, soawName }: Props) {
  const { t } = useTranslation("adm");
  const { user } = useAuthContext();
  const [ws, setWs] = useState<AdmWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const canManage = !!(user?.permissions?.["*"] || user?.permissions?.["adm.manage"]);
  const canView = !!(user?.permissions?.["*"] || user?.permissions?.["adm.view"]);

  const load = useCallback(async () => {
    if (!canView) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<AdmWorkspace>(`/adm/workspaces/by-soaw/${soawId}`);
      setWs(data);
      setNotFound(false);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setNotFound(true);
        setWs(null);
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setLoading(false);
    }
  }, [canView, soawId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!canView) {
    return (
      <Alert severity="info" sx={{ m: 2 }}>
        {t("soawSection.noPermission")}
      </Alert>
    );
  }

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  if (notFound || !ws) {
    return (
      <>
        <Paper variant="outlined" sx={{ p: 4, m: 2, textAlign: "center", borderRadius: 1 }}>
          <MaterialSymbol icon="account_tree" size={40} color="disabled" />
          <Typography variant="h6" sx={{ mt: 1, fontWeight: 800 }}>
            {t("soawSection.emptyTitle")}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2, maxWidth: 640, mx: "auto" }}>
            {t("soawSection.emptyBody")}
          </Typography>
          {canManage && (
            <Button
              variant="contained"
              startIcon={<MaterialSymbol icon="add" size={18} />}
              onClick={() => setCreateOpen(true)}
            >
              {t("soawSection.createButton")}
            </Button>
          )}
        </Paper>
        <CreateWorkspaceDialog
          open={createOpen}
          soawId={soawId}
          soawName={soawName}
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            setCreateOpen(false);
            void load();
          }}
        />
      </>
    );
  }

  const active = ws.phases?.find(
    (p) =>
      !p.is_continuous &&
      (p.status === "in_progress" || p.status === "ready_for_gate" || p.status === "blocked"),
  );
  const accent = active ? PHASE_STATUS_COLORS[active.status] : PHASE_STATUS_COLORS.not_started;
  const nonContinuous = ws.phases?.filter((p) => !p.is_continuous) ?? [];
  const approved = nonContinuous.filter((p) => p.status === "approved").length;
  const completion = nonContinuous.length ? Math.round((approved * 100) / nonContinuous.length) : 0;

  return (
    <Box sx={{ p: 2 }}>
      <Paper variant="outlined" sx={{ p: 2, borderRadius: 1, borderLeft: `4px solid ${accent}`, mb: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1, flexWrap: "wrap" }}>
          <MaterialSymbol icon="account_tree" size={22} color="#0f7eb5" />
          <Typography variant="h6" sx={{ fontWeight: 800, flex: 1, minWidth: 0 }}>
            {ws.name}
          </Typography>
          <Chip size="small" label={t(`workspace.status.${ws.status}`)} />
          <Button
            variant="contained"
            size="small"
            component={RouterLink}
            to={`/ea-delivery/adm/${ws.id}`}
            endIcon={<MaterialSymbol icon="arrow_forward" size={16} />}
          >
            {t("soawSection.open")}
          </Button>
        </Box>
        {active && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {t("soawSection.activePhase")}: <strong>{active.title}</strong> ({t(`status.${active.status}`)})
          </Typography>
        )}
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <LinearProgress
            variant="determinate"
            value={completion}
            sx={{
              flex: 1,
              height: 6,
              borderRadius: 1,
              bgcolor: "action.hover",
              "& .MuiLinearProgress-bar": { bgcolor: accent },
            }}
          />
          <Typography variant="caption" sx={{ fontWeight: 800 }}>
            {completion}%
          </Typography>
        </Box>
      </Paper>
      <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 1 }}>
        {t("timeline.title")}
      </Typography>
      <AdmPhaseTimeline
        phases={ws.phases ?? []}
        activePhaseKey={active?.phase_key}
        onSelectPhase={(key) => window.location.assign(`/ea-delivery/adm/${ws.id}?phase=${key}`)}
      />
    </Box>
  );
}
