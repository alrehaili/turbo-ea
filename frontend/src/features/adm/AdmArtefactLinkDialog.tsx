/**
 * Add-artefact dialog. MVP shape: user picks a kind, provides a title, and
 * optionally a URL or a ref_id. Per-kind pickers (SoAW / ADR / Diagram /
 * Card) are a follow-up — for the MVP we accept a raw UUID for kinds that
 * need one, plus a URL for the ``url`` kind, plus a title-only entry for
 * ``requirement`` / ``document`` / ``file_attachment``.
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
import MenuItem from "@mui/material/MenuItem";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import { useTranslation } from "react-i18next";
import { api } from "@/api/client";
import type { AdmArtefactKind } from "./types";

const ALL_KINDS: AdmArtefactKind[] = [
  "soaw",
  "adr",
  "arb_review",
  "diagram",
  "roadmap",
  "risk",
  "compliance_finding",
  "tech_standard",
  "standard_exception",
  "rationalization_assessment",
  "card",
  "url",
  "document",
  "file_attachment",
  "requirement",
];

const REQUIRES_UUID: AdmArtefactKind[] = [
  "soaw",
  "adr",
  "arb_review",
  "diagram",
  "roadmap",
  "risk",
  "compliance_finding",
  "tech_standard",
  "standard_exception",
  "rationalization_assessment",
  "card",
];

interface Props {
  open: boolean;
  phaseId: string;
  onClose: () => void;
  onCompleted: () => void;
}

export default function AdmArtefactLinkDialog({ open, phaseId, onClose, onCompleted }: Props) {
  const { t } = useTranslation("adm");
  const [kind, setKind] = useState<AdmArtefactKind>("url");
  const [title, setTitle] = useState("");
  const [refId, setRefId] = useState("");
  const [refUrl, setRefUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [isRequired, setIsRequired] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setKind("url");
      setTitle("");
      setRefId("");
      setRefUrl("");
      setNotes("");
      setIsRequired(false);
      setError(null);
      setBusy(false);
    }
  }, [open]);

  const needsUuid = REQUIRES_UUID.includes(kind);
  const needsUrl = kind === "url";
  const canSubmit =
    title.trim().length > 0 &&
    (!needsUuid || refId.trim().length > 0) &&
    (!needsUrl || refUrl.trim().length > 0);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/adm/phases/${phaseId}/artefacts`, {
        kind,
        ref_id: needsUuid ? refId.trim() : undefined,
        ref_url: needsUrl ? refUrl.trim() : undefined,
        title: title.trim(),
        is_required: isRequired,
        notes: notes.trim() || undefined,
      });
      onCompleted();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm" disableRestoreFocus>
      <DialogTitle>{t("artefact.linkTitle")}</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        <TextField
          select
          label={t("artefact.kind")}
          value={kind}
          onChange={(e) => setKind(e.target.value as AdmArtefactKind)}
        >
          {ALL_KINDS.map((k) => (
            <MenuItem key={k} value={k}>
              {t(`artefact.kinds.${k}`)}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label={t("artefact.title")}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        {needsUuid && (
          <TextField
            label={t("artefact.refId")}
            value={refId}
            onChange={(e) => setRefId(e.target.value)}
            required
            helperText={t("artefact.refIdHelper")}
          />
        )}
        {needsUrl && (
          <TextField
            label={t("artefact.refUrl")}
            value={refUrl}
            onChange={(e) => setRefUrl(e.target.value)}
            required
            type="url"
          />
        )}
        <TextField
          label={t("artefact.notes")}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          multiline
          minRows={2}
        />
        <FormControlLabel
          control={
            <Switch checked={isRequired} onChange={(e) => setIsRequired(e.target.checked)} />
          }
          label={t("artefact.markRequired")}
        />
        {error && <Alert severity="error">{error}</Alert>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>
          {t("actions.cancel", { ns: "common" })}
        </Button>
        <Button variant="contained" onClick={submit} disabled={!canSubmit || busy}>
          {t("artefact.link")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
