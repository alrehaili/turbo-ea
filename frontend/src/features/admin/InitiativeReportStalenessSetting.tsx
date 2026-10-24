import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "@/api/client";
import MaterialSymbol from "@/components/MaterialSymbol";

const MAX_DAYS = 3650;

/**
 * Days after which an initiative status report no longer counts on the
 * Executive dashboard (decision D-02). Deliberately no default: an empty field
 * means no report is ever stale, and the dashboard says so.
 */
export default function InitiativeReportStalenessSetting({
  onSaved,
  onError,
}: {
  onSaved: (message: string) => void;
  onError: (message: string) => void;
}) {
  const { t } = useTranslation(["admin", "common"]);
  const [stored, setStored] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .get<{ days: number | null }>("/settings/initiative-report-staleness")
      .then((r) => {
        setStored(r.days);
        setInput(r.days === null ? "" : String(r.days));
      })
      .catch(() => {
        /* the card simply shows the empty, unset state */
      });
  }, []);

  const trimmed = input.trim();
  const parsed = trimmed === "" ? null : Number(trimmed);
  const valid = parsed === null || (Number.isInteger(parsed) && parsed >= 1 && parsed <= MAX_DAYS);

  const save = async () => {
    if (!valid) return;
    setSaving(true);
    try {
      const r = await api.patch<{ days: number | null }>("/settings/initiative-report-staleness", {
        days: parsed,
      });
      setStored(r.days);
      onSaved(t("settings.reportStaleness.saved"));
    } catch (e) {
      onError(e instanceof Error ? e.message : t("common:errors.generic"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", mb: 2, gap: 1 }}>
        <MaterialSymbol icon="event_busy" size={22} color="#555" />
        <Typography variant="h6" fontWeight={600}>
          {t("settings.reportStaleness.title")}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("settings.reportStaleness.description")}
      </Typography>
      <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start", flexWrap: "wrap" }}>
        <TextField
          size="small"
          type="number"
          label={t("settings.reportStaleness.days")}
          placeholder={t("settings.reportStaleness.placeholder")}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          error={!valid}
          helperText={valid ? t("settings.reportStaleness.emptyMeans") : t("settings.reportStaleness.invalid", { max: MAX_DAYS })}
          inputProps={{ min: 1, max: MAX_DAYS }}
          sx={{ width: 260 }}
        />
        <Button
          variant="contained"
          sx={{ textTransform: "none" }}
          onClick={save}
          disabled={saving || !valid || parsed === stored}
        >
          {saving ? t("common:labels.loading") : t("common:actions.save")}
        </Button>
      </Box>
    </Paper>
  );
}
