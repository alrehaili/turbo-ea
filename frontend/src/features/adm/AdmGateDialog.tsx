/**
 * Dialog used for the three governance actions: mark-ready (with optional
 * override), approve, reopen, skip. Enforces a non-empty reason when the
 * action requires one; the underlying API validates the length (≥ 8 chars).
 *
 * [FORK FEATURE]
 */

import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import { api } from "@/api/client";
import type { AdmPhase } from "./types";

export type AdmGateAction = "mark_ready" | "approve" | "reopen" | "skip";

interface Props {
  open: boolean;
  action: AdmGateAction | null;
  phase: AdmPhase | null;
  outstandingRequired: number;
  onClose: () => void;
  onCompleted: () => void;
}

const MIN_REASON_LEN = 8;

export default function AdmGateDialog({
  open,
  action,
  phase,
  outstandingRequired,
  onClose,
  onCompleted,
}: Props) {
  const { t } = useTranslation("adm");
  const [text, setText] = useState("");
  const [override, setOverride] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setText("");
      setOverride(false);
      setBusy(false);
      setError(null);
    }
  }, [open, action]);

  if (!phase || !action) return null;

  const reasonRequired = action === "reopen" || action === "skip";
  const overrideNeeded = action === "mark_ready" && outstandingRequired > 0;
  const validReason = !reasonRequired || text.trim().length >= MIN_REASON_LEN;
  const validOverride =
    !overrideNeeded || !override || (override && text.trim().length >= MIN_REASON_LEN);
  const canSubmit = validReason && validOverride && (!overrideNeeded || override);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      if (action === "mark_ready") {
        await api.post(`/adm/phases/${phase.id}/mark-ready`, {
          override,
          override_reason: override ? text.trim() : undefined,
        });
      } else if (action === "approve") {
        await api.post(`/adm/phases/${phase.id}/approve`, {
          comment: text.trim() || undefined,
        });
      } else if (action === "reopen") {
        await api.post(`/adm/phases/${phase.id}/reopen`, { reason: text.trim() });
      } else if (action === "skip") {
        await api.post(`/adm/phases/${phase.id}/skip`, { reason: text.trim() });
      }
      onCompleted();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm" disableRestoreFocus>
      <DialogTitle>{t(`gate.title.${action}`)}</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        <Typography variant="body2" color="text.secondary">
          {t(`gate.body.${action}`, { phase: phase.title })}
        </Typography>
        {overrideNeeded && (
          <>
            <Alert severity="warning">
              {t("gate.outstandingArtefacts", { count: outstandingRequired })}
            </Alert>
            <FormControlLabel
              control={
                <Switch checked={override} onChange={(e) => setOverride(e.target.checked)} />
              }
              label={t("gate.overrideToggle")}
            />
          </>
        )}
        <TextField
          label={t(
            reasonRequired
              ? "gate.reasonRequired"
              : overrideNeeded && override
                ? "gate.overrideReason"
                : "gate.comment",
          )}
          value={text}
          onChange={(e) => setText(e.target.value)}
          multiline
          minRows={3}
          helperText={
            reasonRequired || (overrideNeeded && override)
              ? t("gate.reasonHelper", { min: MIN_REASON_LEN })
              : t("gate.commentHelper")
          }
          error={
            (reasonRequired && text.length > 0 && text.trim().length < MIN_REASON_LEN) ||
            (overrideNeeded &&
              override &&
              text.length > 0 &&
              text.trim().length < MIN_REASON_LEN)
          }
        />
        {error && <Alert severity="error">{error}</Alert>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>
          {t("actions.cancel", { ns: "common" })}
        </Button>
        <Button variant="contained" onClick={submit} disabled={!canSubmit || busy}>
          {t(`gate.submit.${action}`)}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
