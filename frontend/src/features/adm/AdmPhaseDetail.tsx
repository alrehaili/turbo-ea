/**
 * Right-hand panel for a selected ADM phase. Shows description, gate
 * readiness (linked/waived vs required), artefact list with waive controls,
 * approval history, and the gate action buttons that open ``AdmGateDialog``.
 *
 * [FORK FEATURE]
 */

import { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { PHASE_ICONS, PHASE_STATUS_COLORS, PHASE_STATUS_ICONS } from "./admConstants";
import AdmArtefactLinkDialog from "./AdmArtefactLinkDialog";
import AdmGateDialog, { type AdmGateAction } from "./AdmGateDialog";
import type { AdmPhase } from "./types";

interface Props {
  phase: AdmPhase;
  canManage: boolean;
  canApprove: boolean;
  onRefresh: () => void;
}

export default function AdmPhaseDetail({ phase, canManage, canApprove, onRefresh }: Props) {
  const { t } = useTranslation("adm");
  const [gateAction, setGateAction] = useState<AdmGateAction | null>(null);
  const [linkOpen, setLinkOpen] = useState(false);
  const [waiveTarget, setWaiveTarget] = useState<string | null>(null);
  const [waiveReason, setWaiveReason] = useState("");

  const outstanding = useMemo(
    () =>
      phase.artefacts.filter(
        (a) => a.is_required && !a.is_waived && !a.ref_id && !(a.ref_url && a.ref_url.trim()),
      ),
    [phase.artefacts],
  );

  const color = PHASE_STATUS_COLORS[phase.status];

  const readyDisabled =
    phase.is_continuous ||
    phase.status === "approved" ||
    phase.status === "skipped" ||
    phase.status === "ready_for_gate";

  const approveDisabled = phase.status !== "ready_for_gate";

  const waive = async (artefactId: string, waived: boolean, reason?: string) => {
    await api.post(`/adm/artefacts/${artefactId}/waive`, {
      is_waived: waived,
      reason: waived ? reason : undefined,
    });
    setWaiveTarget(null);
    setWaiveReason("");
    onRefresh();
  };

  const unlink = async (artefactId: string) => {
    if (!window.confirm(t("artefact.confirmUnlink"))) return;
    await api.delete(`/adm/artefacts/${artefactId}`);
    onRefresh();
  };

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 1, borderLeft: `3px solid ${color}` }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1, flexWrap: "wrap" }}>
        <Box
          sx={{
            width: 32,
            height: 32,
            borderRadius: 1,
            bgcolor: `${color}1a`,
            color,
            display: "grid",
            placeItems: "center",
            flexShrink: 0,
          }}
        >
          <MaterialSymbol icon={PHASE_ICONS[phase.phase_key] || "flag"} size={20} color="inherit" />
        </Box>
        <Typography variant="h6" sx={{ fontWeight: 800, flex: 1, minWidth: 0 }}>
          {phase.title}
        </Typography>
        <Chip
          size="small"
          icon={
            <Box sx={{ display: "flex", color: "#fff" }}>
              <MaterialSymbol icon={PHASE_STATUS_ICONS[phase.status]} size={14} color="inherit" />
            </Box>
          }
          label={t(`status.${phase.status}`)}
          sx={{ bgcolor: color, color: "#fff", fontWeight: 700 }}
        />
      </Box>

      {phase.description && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {phase.description}
        </Typography>
      )}

      {/* Gate readiness summary */}
      {!phase.is_continuous && (
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
            <Typography variant="caption" sx={{ fontWeight: 700 }}>
              {t("gate.readiness")}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {phase.linked_count}/{phase.required_count || 0} {t("timeline.artefacts")} ·{" "}
              {phase.completion_pct}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={phase.completion_pct}
            sx={{
              height: 6,
              borderRadius: 1,
              bgcolor: "action.hover",
              "& .MuiLinearProgress-bar": { bgcolor: color },
            }}
          />
        </Box>
      )}

      {/* Gate actions */}
      {(canManage || canApprove) && (
        <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
          {canManage && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<MaterialSymbol icon="how_to_reg" size={16} />}
              disabled={readyDisabled}
              onClick={() => setGateAction("mark_ready")}
            >
              {t("gate.actions.markReady")}
            </Button>
          )}
          {canApprove && (
            <Button
              size="small"
              variant="contained"
              color="success"
              startIcon={<MaterialSymbol icon="check_circle" size={16} />}
              disabled={approveDisabled}
              onClick={() => setGateAction("approve")}
            >
              {t("gate.actions.approve")}
            </Button>
          )}
          {canApprove && phase.status === "approved" && (
            <Button
              size="small"
              variant="outlined"
              color="warning"
              startIcon={<MaterialSymbol icon="restart_alt" size={16} />}
              onClick={() => setGateAction("reopen")}
            >
              {t("gate.actions.reopen")}
            </Button>
          )}
          {canApprove && !phase.is_continuous && phase.status !== "approved" && phase.status !== "skipped" && (
            <Button
              size="small"
              variant="outlined"
              color="inherit"
              startIcon={<MaterialSymbol icon="skip_next" size={16} />}
              onClick={() => setGateAction("skip")}
            >
              {t("gate.actions.skip")}
            </Button>
          )}
        </Box>
      )}

      {/* Approval history */}
      {(phase.approved_at || phase.approval_override_reason) && (
        <Paper
          variant="outlined"
          sx={{ p: 1.25, mb: 2, borderRadius: 1, bgcolor: `${color}0a` }}
        >
          {phase.approved_at && (
            <Typography variant="caption" sx={{ display: "block" }}>
              <strong>{t("gate.history.approvedAt")}</strong> {phase.approved_at.slice(0, 10)}
              {phase.approval_comment ? ` — ${phase.approval_comment}` : ""}
            </Typography>
          )}
          {phase.approval_override_reason && (
            <Typography variant="caption" sx={{ display: "block", color: "warning.main" }}>
              <strong>{t("gate.history.override")}</strong> {phase.approval_override_reason}
            </Typography>
          )}
        </Paper>
      )}

      <Divider sx={{ my: 2 }} />

      {/* Artefacts */}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>
          {t("artefact.header")} · {phase.artefacts.length}
        </Typography>
        {canManage && (
          <Button
            size="small"
            variant="text"
            startIcon={<MaterialSymbol icon="add" size={16} />}
            onClick={() => setLinkOpen(true)}
          >
            {t("artefact.add")}
          </Button>
        )}
      </Box>
      {phase.artefacts.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          {t("artefact.empty")}
        </Typography>
      )}
      <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75 }}>
        {phase.artefacts.map((a) => {
          const linked = a.is_linked;
          return (
            <Paper
              key={a.id}
              variant="outlined"
              sx={{ p: 1, borderRadius: 1, display: "flex", alignItems: "center", gap: 1 }}
            >
              <Tooltip title={t(`artefact.kinds.${a.kind}`)}>
                <Box
                  sx={{
                    width: 26,
                    height: 26,
                    borderRadius: 0.75,
                    bgcolor: "action.hover",
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                    color: linked || a.is_waived ? "success.main" : "warning.main",
                  }}
                >
                  <MaterialSymbol
                    icon={a.is_waived ? "block" : linked ? "check_circle" : "radio_button_unchecked"}
                    size={16}
                    color="inherit"
                  />
                </Box>
              </Tooltip>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="body2" sx={{ fontWeight: 700 }} noWrap>
                  {a.title}
                  {a.is_required && (
                    <Chip
                      size="small"
                      label={t("artefact.required")}
                      sx={{ ml: 0.75, height: 18, fontSize: "0.6rem" }}
                    />
                  )}
                </Typography>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block" }}
                  noWrap
                >
                  {t(`artefact.kinds.${a.kind}`)}
                  {a.ref_url && ` · ${a.ref_url}`}
                  {a.is_waived && a.waived_reason && ` · ${t("artefact.waivedLabel")} — ${a.waived_reason}`}
                </Typography>
              </Box>
              {canManage && (
                <>
                  {a.is_required && !a.is_waived && (
                    <Tooltip title={t("artefact.waive")}>
                      <IconButton
                        size="small"
                        onClick={() => {
                          setWaiveTarget(a.id);
                          setWaiveReason("");
                        }}
                      >
                        <MaterialSymbol icon="block" size={16} />
                      </IconButton>
                    </Tooltip>
                  )}
                  {a.is_waived && (
                    <Tooltip title={t("artefact.unwaive")}>
                      <IconButton size="small" onClick={() => waive(a.id, false)}>
                        <MaterialSymbol icon="restore" size={16} />
                      </IconButton>
                    </Tooltip>
                  )}
                  <Tooltip title={t("artefact.unlink")}>
                    <IconButton size="small" color="error" onClick={() => unlink(a.id)}>
                      <MaterialSymbol icon="delete" size={16} />
                    </IconButton>
                  </Tooltip>
                </>
              )}
            </Paper>
          );
        })}
      </Box>

      {/* Waive prompt */}
      {waiveTarget && (
        <Paper variant="outlined" sx={{ mt: 1.5, p: 1.5, borderRadius: 1 }}>
          <Typography variant="caption" sx={{ fontWeight: 700, display: "block", mb: 1 }}>
            {t("artefact.waiveReason")}
          </Typography>
          <input
            type="text"
            value={waiveReason}
            onChange={(e) => setWaiveReason(e.target.value)}
            placeholder={t("artefact.waiveReasonPlaceholder")}
            style={{ width: "100%", padding: 6 }}
          />
          <Box sx={{ display: "flex", gap: 1, mt: 1, justifyContent: "flex-end" }}>
            <Button size="small" onClick={() => setWaiveTarget(null)}>
              {t("actions.cancel", { ns: "common" })}
            </Button>
            <Button
              size="small"
              variant="contained"
              disabled={waiveReason.trim().length < 8}
              onClick={() => waive(waiveTarget, true, waiveReason.trim())}
            >
              {t("artefact.confirmWaive")}
            </Button>
          </Box>
        </Paper>
      )}

      <AdmGateDialog
        open={gateAction !== null}
        action={gateAction}
        phase={phase}
        outstandingRequired={outstanding.length}
        onClose={() => setGateAction(null)}
        onCompleted={() => {
          setGateAction(null);
          onRefresh();
        }}
      />

      <AdmArtefactLinkDialog
        open={linkOpen}
        phaseId={phase.id}
        onClose={() => setLinkOpen(false)}
        onCompleted={() => {
          setLinkOpen(false);
          onRefresh();
        }}
      />
    </Paper>
  );
}
