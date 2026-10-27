import { useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import Radio from "@mui/material/Radio";
import RadioGroup from "@mui/material/RadioGroup";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "@/api/client";

interface Props {
  initiative: { id: string; name: string } | null;
  onClose: () => void;
  onSaved: () => void;
}

/**
 * Records whether an initiative requires EA governance review (D-37): the
 * decision, the approved criteria applied and why. Each save appends a new
 * assessment; earlier ones are kept. The server requires
 * `governance.assess_applicability` and every field.
 */
export default function AssessApplicabilityDialog({ initiative, onClose, onSaved }: Props) {
  const { t } = useTranslation("common");
  const k = (key: string) => `dashboard.executive.governancePage.applicability.${key}`;
  const [decision, setDecision] = useState<"required" | "not_required">("required");
  const [criteria, setCriteria] = useState("");
  const [justification, setJustification] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (!initiative) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/cards/${initiative.id}/ea-applicability`, {
        decision,
        criteria_reference: criteria,
        justification,
      });
      setCriteria("");
      setJustification("");
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : t(k("failed")));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={!!initiative} onClose={onClose} fullWidth maxWidth="sm" disableRestoreFocus>
      <DialogTitle>{t(k("title"))}</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        <Typography variant="body2" fontWeight={600} dir="auto">
          {initiative?.name}
        </Typography>
        {error && <Alert severity="error">{error}</Alert>}
        <RadioGroup
          value={decision}
          onChange={(e) => setDecision(e.target.value as "required" | "not_required")}
        >
          <FormControlLabel value="required" control={<Radio />} label={t(k("required"))} />
          <FormControlLabel value="not_required" control={<Radio />} label={t(k("notRequired"))} />
        </RadioGroup>
        <TextField
          label={t(k("criteria"))}
          placeholder={t(k("criteriaHint"))}
          value={criteria}
          onChange={(e) => setCriteria(e.target.value)}
          inputProps={{ maxLength: 300 }}
          fullWidth
        />
        <TextField
          label={t(k("justification"))}
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          multiline
          minRows={3}
          fullWidth
        />
        <Typography variant="caption" color="text.secondary">
          {t(k("appendOnly"))}
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("actions.cancel")}</Button>
        <Button
          variant="contained"
          disabled={busy || !criteria.trim() || !justification.trim()}
          onClick={save}
        >
          {t(k("save"))}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
