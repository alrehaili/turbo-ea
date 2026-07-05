/**
 * ADM Workspace detail page.
 *
 * Route: /ea-delivery/adm/:workspaceId
 *
 * Layout: breadcrumb → header (name, status, owner, linked SoAW /
 * Initiative buttons, target completion) → phase timeline (left / top) →
 * selected-phase detail (right / bottom) → cross-phase requirements
 * management panel below.
 *
 * [FORK FEATURE]
 */

import { useCallback, useEffect, useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Breadcrumbs from "@mui/material/Breadcrumbs";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useAuthContext } from "@/hooks/AuthContext";
import { api } from "@/api/client";
import AdmPhaseDetail from "./AdmPhaseDetail";
import AdmPhaseTimeline from "./AdmPhaseTimeline";
import AdmRequirementsPanel from "./AdmRequirementsPanel";
import type { AdmWorkspace } from "./types";

export default function AdmWorkspacePage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation(["adm", "nav", "common"]);
  const { user } = useAuthContext();
  const [ws, setWs] = useState<AdmWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPhaseKey, setSelectedPhaseKey] = useState<string | null>(null);

  const canManage = !!(user?.permissions?.["*"] || user?.permissions?.["adm.manage"]);
  const canApprove = !!(user?.permissions?.["*"] || user?.permissions?.["adm.approve_gate"]);

  const load = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<AdmWorkspace>(`/adm/workspaces/${workspaceId}`);
      setWs(data);
      if (!selectedPhaseKey && data.phases && data.phases.length > 0) {
        const active = data.phases.find(
          (p) =>
            !p.is_continuous &&
            (p.status === "in_progress" ||
              p.status === "ready_for_gate" ||
              p.status === "blocked"),
        );
        setSelectedPhaseKey((active || data.phases[0]).phase_key);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [workspaceId, selectedPhaseKey]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !ws) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 10 }}>
        <CircularProgress />
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

  if (!ws) return null;

  const selectedPhase = ws.phases?.find((p) => p.phase_key === selectedPhaseKey) || null;

  return (
    <Box sx={{ maxWidth: 1400, mx: "auto", p: { xs: 1, sm: 2 } }}>
      <Breadcrumbs aria-label={t("breadcrumbs")} separator="›" sx={{ mb: 1 }}>
        <Link
          component={RouterLink}
          to="/reports/ea-delivery"
          underline="hover"
          color="inherit"
          variant="body2"
        >
          {t("reports.eaDelivery", { ns: "nav" })}
        </Link>
        <Link
          component={RouterLink}
          to="/ea-delivery/adm"
          underline="hover"
          color="inherit"
          variant="body2"
        >
          {t("nav.workspaces")}
        </Link>
        <Typography variant="body2" color="text.primary" sx={{ fontWeight: 600 }}>
          {ws.name}
        </Typography>
      </Breadcrumbs>

      {/* Header */}
      <Paper variant="outlined" sx={{ p: 2, borderRadius: 1, mb: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", mb: 1 }}>
          <MaterialSymbol icon="account_tree" size={24} color="#0f7eb5" />
          <Typography variant="h5" sx={{ fontWeight: 800, flex: 1, minWidth: 0 }}>
            {ws.name}
          </Typography>
          <Chip size="small" label={t(`workspace.status.${ws.status}`)} />
        </Box>
        {ws.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {ws.description}
          </Typography>
        )}
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
          {ws.soaw_id && (
            <Button
              size="small"
              variant="outlined"
              component={RouterLink}
              to={`/ea-delivery/soaw/${ws.soaw_id}`}
              startIcon={<MaterialSymbol icon="description" size={16} />}
            >
              {t("header.linkedSoaw")}
            </Button>
          )}
          {ws.initiative_id && (
            <Button
              size="small"
              variant="outlined"
              component={RouterLink}
              to={`/cards/${ws.initiative_id}`}
              startIcon={<MaterialSymbol icon="rocket_launch" size={16} />}
            >
              {t("header.linkedInitiative")}
            </Button>
          )}
          {ws.target_completion && (
            <Chip
              size="small"
              icon={<MaterialSymbol icon="event" size={14} />}
              label={`${t("header.target")} ${ws.target_completion}`}
              variant="outlined"
            />
          )}
        </Box>
      </Paper>

      {/* Timeline */}
      <Paper variant="outlined" sx={{ p: 2, borderRadius: 1, mb: 2 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 1.25 }}>
          {t("timeline.title")}
        </Typography>
        <AdmPhaseTimeline
          phases={ws.phases || []}
          activePhaseKey={selectedPhaseKey || undefined}
          onSelectPhase={setSelectedPhaseKey}
        />
      </Paper>

      {/* Selected phase detail */}
      {selectedPhase && (
        <Box sx={{ mb: 2 }}>
          <AdmPhaseDetail
            phase={selectedPhase}
            canManage={canManage}
            canApprove={canApprove}
            onRefresh={load}
          />
        </Box>
      )}

      {/* Cross-phase Requirements Management */}
      <AdmRequirementsPanel workspaceId={ws.id} onNavigateToPhase={setSelectedPhaseKey} />

      {/* Delete affordance for owners */}
      {canManage && (
        <Box sx={{ mt: 4, display: "flex", justifyContent: "flex-end" }}>
          <Button
            size="small"
            color="error"
            startIcon={<MaterialSymbol icon="delete" size={16} />}
            onClick={async () => {
              if (!window.confirm(t("workspace.confirmDelete", { name: ws.name }))) return;
              await api.delete(`/adm/workspaces/${ws.id}`);
              navigate("/ea-delivery/adm");
            }}
          >
            {t("workspace.delete")}
          </Button>
        </Box>
      )}
    </Box>
  );
}
