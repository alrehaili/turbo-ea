import { useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { useAbortableEffect } from "@/hooks/useLatestRequest";

/** The fields of an exception row the lifecycle actions need. */
export interface LifecycleException {
  id: string;
  /** Stored status, or `expired` for an approved waiver past its expiry date. */
  status: string;
  created_by?: string | null;
  remediation_submitted_by?: string | null;
  /** The card the waiver covers; its documents and files can back a remediation. */
  card?: { id: string } | null;
}

/** A document or file already on the card, offered as remediation evidence (I-32). */
interface EvidenceOption {
  kind: "document" | "attachment";
  id: string;
  name: string;
}

/** A text step: the dialog that asks for its evidence, reason or note. */
type TextStep = "remediation" | "verify" | "withdraw" | "return" | "delete";

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
 * than the requester and the submitter, and only once the standards check no
 * longer finds the usage or, where it cannot check, when the submission cites a
 * document or file on the card and the verifier notes what was checked (I-32); withdraw with a reason (the requester or a manager) while
 * the exception is not yet terminal, past its expiry too (I-30); and permanently delete, with a reason, only for holders of
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
  const [evidenceOptions, setEvidenceOptions] = useState<EvidenceOption[]>([]);
  const [chosen, setChosen] = useState<string[]>([]);
  // The verifier's attestation (I-36): the main field is what was examined.
  const [demonstrates, setDemonstrates] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const cardId = exception.card?.id ?? null;

  // The card's existing documents and files, loaded when the remediation dialog
  // opens: the evidence mechanisms the card already has are reused, not a new one.
  useAbortableEffect(
    async ({ signal, isCurrent }) => {
      if (step !== "remediation" || !cardId) return;
      const load = async <T,>(path: string): Promise<T[]> => {
        try {
          return await api.get<T[]>(path, { signal });
        } catch {
          return [];
        }
      };
      const [docs, files] = await Promise.all([
        load<{ id: string; name: string }>(`/cards/${cardId}/documents`),
        load<{ id: string; name: string }>(`/cards/${cardId}/file-attachments`),
      ]);
      if (!isCurrent()) return;
      setEvidenceOptions([
        ...docs.map((d) => ({ kind: "document" as const, id: d.id, name: d.name })),
        ...files.map((f) => ({ kind: "attachment" as const, id: f.id, name: f.name })),
      ]);
    },
    [step, cardId],
  );

  const status = exception.status;
  const isApproved = status === "approved" || status === "expired";
  const isRequester = !!userId && exception.created_by === userId;
  const isSubmitter = !!userId && exception.remediation_submitted_by === userId;
  const canApprove = can("tech_standards.approve_exception");
  const canManage = can("tech_standards.manage");
  const canWithdraw =
    (status === "requested" || isApproved || status === "remediation_submitted") && (canManage || isRequester);
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
    if (!step || (!value && step !== "verify")) return;
    if (step === "verify") {
      const why = demonstrates.trim();
      const attested = value || why || confirmed;
      return run(() =>
        api.post(
          `${base}/remediation/verify`,
          attested
            ? { outcome: "verified", attestation: { examined: value, demonstrates: why, confirmed } }
            : { outcome: "verified" },
        ),
      );
    }
    if (step === "remediation") {
      const evidenceRefs = evidenceOptions
        .filter((o) => chosen.includes(`${o.kind}:${o.id}`))
        .map((o) => ({ kind: o.kind, id: o.id }));
      return run(() =>
        api.post(
          `${base}/remediation`,
          evidenceRefs.length ? { evidence: value, evidence_refs: evidenceRefs } : { evidence: value },
        ),
      );
    }
    if (step === "withdraw") return run(() => api.post(`${base}/withdraw`, { reason: value }));
    if (step === "return")
      return run(() => api.post(`${base}/remediation/verify`, { outcome: "returned", note: value }));
    return run(() => api.delete(`${base}?reason=${encodeURIComponent(value)}`));
  };

  const open = (next: TextStep) => {
    setError(null);
    setText("");
    setChosen([]);
    setEvidenceOptions([]);
    setDemonstrates("");
    setConfirmed(false);
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
              onClick={() => open("verify")}
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
          {step === "verify" && (
            <Box sx={{ mt: 2 }} data-testid="verify-attestation">
              <TextField
                fullWidth
                multiline
                minRows={2}
                label={t(k("verify.demonstratesLabel"))}
                value={demonstrates}
                onChange={(e) => setDemonstrates(e.target.value)}
                inputProps={{ maxLength: 5000 }}
              />
              <FormControlLabel
                sx={{ mt: 1 }}
                control={<Checkbox checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />}
                label={t(k("verify.confirmStatement"))}
              />
            </Box>
          )}
          {step === "remediation" && (
            <Box sx={{ mt: 2 }} data-testid="remediation-evidence-refs">
              <Typography variant="subtitle2">{t(k("remediation.refsTitle"))}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {t(k(evidenceOptions.length ? "remediation.refsHint" : "remediation.refsNone"))}
              </Typography>
              {evidenceOptions.map((o) => {
                const key = `${o.kind}:${o.id}`;
                return (
                  <FormControlLabel
                    key={key}
                    sx={{ display: "flex" }}
                    control={
                      <Checkbox
                        size="small"
                        checked={chosen.includes(key)}
                        onChange={(e) =>
                          setChosen((prev) => (e.target.checked ? [...prev, key] : prev.filter((c) => c !== key)))
                        }
                      />
                    }
                    label={`${o.name} · ${t(k(`remediation.kind.${o.kind}`))}`}
                  />
                );
              })}
            </Box>
          )}
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
            disabled={busy || (!text.trim() && step !== "verify")}
            onClick={submitText}
          >
            {step ? t(k(`${step}.confirm`)) : ""}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
