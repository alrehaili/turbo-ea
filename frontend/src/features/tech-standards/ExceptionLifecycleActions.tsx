import { useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";

/** The fields of an exception row the lifecycle actions need. */
export interface LifecycleException {
  id: string;
  /** Stored status, or `expired` for an approved waiver past its expiry date. */
  status: string;
  created_by?: string | null;
  remediation_submitted_by?: string | null;
}

/** A text step: the dialog that asks for its evidence, reason or note. */
type TextStep = "remediation" | "withdraw" | "return" | "delete";

interface Props {
  exception: LifecycleException;
  userId: string | null;
  can: (permission: string) => boolean;
  onChanged: () => void | Promise<void>;
}

/**
 * Row actions of the exception register, following the approved lifecycle
 * (D-34, D-40): approve / reject a request; submit remediation evidence on an
 * approved (or expired) waiver; verify or return it — only by someone other
 * than the requester and the submitter; withdraw with a reason (the requester
 * or a manager); and permanently delete, with a reason, only for holders of
 * `tech_standards.delete_exception`. The server enforces every rule; the
 * buttons only spare the user a refusal.
 */
export default function ExceptionLifecycleActions({ exception, userId, can, onChanged }: Props) {
  const { t } = useTranslation("reports");
  const k = (key: string) => `techStandards.lifecycle.${key}`;
  const [step, setStep] = useState<TextStep | null>(null);
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const status = exception.status;
  const isApproved = status === "approved" || status === "expired";
  const isRequester = !!userId && exception.created_by === userId;
  const isSubmitter = !!userId && exception.remediation_submitted_by === userId;
  const canApprove = can("tech_standards.approve_exception");
  const canManage = can("tech_standards.manage");
  const canWithdraw = (status === "requested" || isApproved) && (canManage || isRequester);
  const selfVerification = isRequester || isSubmitter;

  const run = async (call: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await call();
      setStep(null);
      setText("");
      await onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : t(k("failed")));
    } finally {
      setBusy(false);
    }
  };

  const base = `/tech-standards/exceptions/${exception.id}`;
  const submitText = () => {
    const value = text.trim();
    if (!value || !step) return;
    if (step === "remediation") return run(() => api.post(`${base}/remediation`, { evidence: value }));
    if (step === "withdraw") return run(() => api.post(`${base}/withdraw`, { reason: value }));
    if (step === "return")
      return run(() => api.post(`${base}/remediation/verify`, { outcome: "returned", note: value }));
    return run(() => api.delete(`${base}?reason=${encodeURIComponent(value)}`));
  };

  const open = (next: TextStep) => {
    setError(null);
    setText("");
    setStep(next);
  };

  return (
    <Box sx={{ display: "flex", gap: 0.5, justifyContent: "flex-end", alignItems: "center", flexWrap: "wrap" }}>
      {status === "requested" && canApprove && (
        <>
          <Button size="small" color="success" disabled={busy} onClick={() => run(() => api.post(`${base}/decision?action=approve`, {}))}>
            {t("techStandards.approve")}
          </Button>
          <Button size="small" color="error" disabled={busy} onClick={() => run(() => api.post(`${base}/decision?action=reject`, {}))}>
            {t("techStandards.reject")}
          </Button>
        </>
      )}
      {isApproved && canManage && (
        <Button size="small" onClick={() => open("remediation")}>
          {t(k("submitRemediation"))}
        </Button>
      )}
      {status === "remediation_submitted" && canApprove && (
        <Tooltip title={selfVerification ? t(k("selfVerification")) : ""}>
          <span>
            <Button
              size="small"
              color="success"
              disabled={busy || selfVerification}
              onClick={() => run(() => api.post(`${base}/remediation/verify`, { outcome: "verified" }))}
            >
              {t(k("verify"))}
            </Button>
            <Button size="small" disabled={busy || selfVerification} onClick={() => open("return")}>
              {t(k("return"))}
            </Button>
          </span>
        </Tooltip>
      )}
      {canWithdraw && (
        <Button size="small" color="inherit" onClick={() => open("withdraw")}>
          {t(k("withdraw"))}
        </Button>
      )}
      {can("tech_standards.delete_exception") && (
        <Tooltip title={t(k("deleteTooltip"))}>
          <IconButton size="small" color="error" aria-label={t(k("deleteTooltip"))} onClick={() => open("delete")}>
            <MaterialSymbol icon="delete" size={18} />
          </IconButton>
        </Tooltip>
      )}
      {error && !step && (
        <Typography variant="caption" color="error" role="alert">
          {error}
        </Typography>
      )}

      <Dialog open={step !== null} onClose={() => !busy && setStep(null)} maxWidth="sm" fullWidth disableRestoreFocus>
        <DialogTitle>{step ? t(k(`${step}.title`)) : ""}</DialogTitle>
        <DialogContent>
          {step && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t(k(`${step}.hint`))}
            </Typography>
          )}
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={3}
            label={step ? t(k(`${step}.label`)) : ""}
            value={text}
            onChange={(e) => setText(e.target.value)}
            inputProps={{ maxLength: step === "remediation" ? 10000 : 2000 }}
          />
          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setStep(null)} disabled={busy}>
            {t(k("cancel"))}
          </Button>
          <Button
            variant="contained"
            color={step === "delete" ? "error" : "primary"}
            disabled={busy || !text.trim()}
            onClick={submitText}
          >
            {step ? t(k(`${step}.confirm`)) : ""}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
