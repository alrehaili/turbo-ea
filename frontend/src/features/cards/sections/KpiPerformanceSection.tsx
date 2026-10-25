import { useState } from "react";
import { useTranslation } from "react-i18next";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import LinearProgress from "@mui/material/LinearProgress";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import LinkifiedText from "@/components/LinkifiedText";
import { api } from "@/api/client";
import { useOptionalAuthUser } from "@/hooks/AuthContext";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useDateFormat } from "@/hooks/useDateFormat";
import type { KpiMeasurement, KpiPerformance } from "@/types";

type DialogState =
  | { kind: "record" }
  | { kind: "correct"; measurement: KpiMeasurement }
  | { kind: "ratify" }
  | null;

const STATUS_COLOR: Record<string, "default" | "info" | "success" | "warning"> = {
  submitted: "warning",
  verified: "success",
  superseded: "default",
};

/**
 * A KPI card's target (with its ratification state) and measurement history
 * (decisions D-19, D-17a). Every write goes through the server's rules: the
 * section only offers what the caller's permissions allow, and shows the
 * server's refusal (own measurement, frozen period, missing reason) verbatim.
 */
export default function KpiPerformanceSection({ cardId }: { cardId: string }) {
  const { t } = useTranslation("cards");
  // The server refuses to let anyone verify a value they recorded (D-19).
  const me = useOptionalAuthUser();
  const { formatDate, formatDateTime } = useDateFormat();
  const [refetchKey, setRefetchKey] = useState(0);
  const { data, error, loading } = useApiQuery<KpiPerformance>(`/kpis/${cardId}/performance`, {
    refetchKey,
  });
  const [dialog, setDialog] = useState<DialogState>(null);
  const [form, setForm] = useState({ period: "", value: "", evidence: "", reason: "", note: "" });
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (error) return null; // not a KPI the caller may read: the section does not exist
  if (!data) return loading ? <LinearProgress /> : null;

  const open = (next: DialogState) => {
    setForm({ period: "", value: "", evidence: "", reason: "", note: "" });
    setSaveError(null);
    setDialog(next);
  };

  const run = async (action: () => Promise<unknown>) => {
    setSaving(true);
    setSaveError(null);
    try {
      await action();
      setDialog(null);
      setRefetchKey((k) => k + 1);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const submit = () => {
    if (!dialog) return;
    if (dialog.kind === "record") {
      return run(() =>
        api.post(`/kpis/${cardId}/measurements`, {
          period_key: form.period.trim(),
          value: Number(form.value),
          evidence: form.evidence || null,
        }),
      );
    }
    if (dialog.kind === "correct") {
      return run(() =>
        api.post(`/kpis/measurements/${dialog.measurement.id}/corrections`, {
          value: Number(form.value),
          evidence: form.evidence || null,
          reason: form.reason,
        }),
      );
    }
    return run(() => api.post(`/kpis/${cardId}/target-ratifications`, { note: form.note || null }));
  };

  const verify = (m: KpiMeasurement) =>
    run(() => api.post(`/kpis/measurements/${m.id}/verify`, {}));

  const target = data.target;
  const periodRows = data.measurements.filter((m) => m.kind === "period");
  const valueValid = form.value.trim() !== "" && Number.isFinite(Number(form.value));

  return (
    <Accordion defaultExpanded disableGutters variant="outlined" data-testid="kpi-performance">
      <AccordionSummary expandIcon={<MaterialSymbol icon="expand_more" size={20} />}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <MaterialSymbol icon="monitoring" size={20} />
          <Typography fontWeight={700}>{t("kpiPerformance.title")}</Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <Typography variant="subtitle2" sx={{ flex: 1, minWidth: 0 }}>
            {target.value === null
              ? t("kpiPerformance.noTarget")
              : t(target.date ? "kpiPerformance.targetLine" : "kpiPerformance.targetLineNoDate", {
                  value: target.value,
                  unit: target.unit ?? "",
                  date: target.date ? formatDate(target.date) : "",
                  baseline: target.baseline ?? "—",
                })}
          </Typography>
          {target.status !== "none" && (
            <Chip
              size="small"
              color={target.status === "ratified" ? "success" : "warning"}
              variant="outlined"
              label={t(`kpiPerformance.targetStatus.${target.status}`)}
              data-testid="target-status"
            />
          )}
          {data.can_ratify && target.status === "unratified" && (
            <Button size="small" variant="outlined" onClick={() => open({ kind: "ratify" })}>
              {t("kpiPerformance.ratify")}
            </Button>
          )}
        </Box>
        {target.invalidated && (
          <Alert severity="warning">{t("kpiPerformance.invalidated")}</Alert>
        )}
        {target.status === "ratified" && target.ratified_at && (
          <Typography variant="caption" color="text.secondary">
            {t("kpiPerformance.ratifiedAt", { time: formatDateTime(target.ratified_at) })}
          </Typography>
        )}

        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="subtitle2" sx={{ flex: 1 }}>
            {t("kpiPerformance.history")}
          </Typography>
          {data.can_measure && (
            <Button size="small" variant="contained" onClick={() => open({ kind: "record" })}>
              {t("kpiPerformance.record")}
            </Button>
          )}
        </Box>
        {periodRows.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {t("kpiPerformance.noMeasurements")}
          </Typography>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("kpiPerformance.col.period")}</TableCell>
                  <TableCell align="right">{t("kpiPerformance.col.value")}</TableCell>
                  <TableCell>{t("kpiPerformance.col.status")}</TableCell>
                  <TableCell>{t("kpiPerformance.col.evidence")}</TableCell>
                  <TableCell />
                </TableRow>
              </TableHead>
              <TableBody>
                {periodRows.map((m) => (
                  <TableRow key={m.id} sx={{ opacity: m.status === "superseded" ? 0.6 : 1 }}>
                    <TableCell sx={{ whiteSpace: "nowrap" }}>
                      <bdi>{m.period_key}</bdi>
                    </TableCell>
                    <TableCell align="right">
                      <bdi>{m.value ?? "—"}</bdi>
                    </TableCell>
                    <TableCell sx={{ minWidth: 160 }}>
                      <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                        <Chip
                          size="small"
                          variant="outlined"
                          color={STATUS_COLOR[m.status] ?? "default"}
                          label={t(`kpiPerformance.status.${m.status}`)}
                        />
                        {m.frozen && (
                          <Chip size="small" variant="outlined" label={t("kpiPerformance.frozen")} />
                        )}
                      </Box>
                      {m.correction_reason && (
                        <Typography variant="caption" color="text.secondary" component="div">
                          {t("kpiPerformance.correctionReason", { reason: m.correction_reason })}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ maxWidth: 260, overflowWrap: "anywhere" }}>
                      {m.evidence ? <LinkifiedText text={m.evidence} /> : "—"}
                    </TableCell>
                    <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                      {data.can_verify && m.status === "submitted" && m.recorded_by !== me?.id && (
                        <Button size="small" onClick={() => verify(m)} disabled={saving}>
                          {t("kpiPerformance.verify")}
                        </Button>
                      )}
                      {data.can_measure && (m.status === "submitted" || m.status === "verified") && (
                        <Button size="small" onClick={() => open({ kind: "correct", measurement: m })}>
                          {t("kpiPerformance.correct")}
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
        {saveError && !dialog && <Alert severity="error">{saveError}</Alert>}
      </AccordionDetails>

      <Dialog open={dialog !== null} onClose={() => setDialog(null)} fullWidth maxWidth="xs" disableRestoreFocus>
        <DialogTitle>
          {dialog?.kind === "record"
            ? t("kpiPerformance.record")
            : dialog?.kind === "correct"
              ? t("kpiPerformance.correctTitle", { period: dialog.measurement.period_key })
              : t("kpiPerformance.ratify")}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "8px !important" }}>
          {dialog?.kind === "record" && (
            <TextField
              label={t("kpiPerformance.periodField")}
              placeholder="FY2026-Q3"
              helperText={t("kpiPerformance.periodHint")}
              value={form.period}
              onChange={(e) => setForm({ ...form, period: e.target.value })}
            />
          )}
          {(dialog?.kind === "record" || dialog?.kind === "correct") && (
            <>
              <TextField
                label={t("kpiPerformance.valueField")}
                type="number"
                value={form.value}
                onChange={(e) => setForm({ ...form, value: e.target.value })}
              />
              <TextField
                label={t("kpiPerformance.evidenceField")}
                placeholder={t("kpiPerformance.evidenceHint")}
                value={form.evidence}
                onChange={(e) => setForm({ ...form, evidence: e.target.value })}
              />
            </>
          )}
          {dialog?.kind === "correct" && (
            <TextField
              label={t("kpiPerformance.reasonField")}
              required
              multiline
              minRows={2}
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
            />
          )}
          {dialog?.kind === "ratify" && (
            <>
              <Typography variant="body2">
                {t(target.date ? "kpiPerformance.ratifyConfirm" : "kpiPerformance.ratifyConfirmNoDate", {
                  value: target.value,
                  unit: target.unit ?? "",
                  date: target.date ? formatDate(target.date) : "",
                })}
              </Typography>
              <TextField
                label={t("kpiPerformance.noteField")}
                value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })}
              />
            </>
          )}
          {saveError && <Alert severity="error">{saveError}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialog(null)}>{t("kpiPerformance.cancel")}</Button>
          <Button
            variant="contained"
            onClick={submit}
            disabled={
              saving ||
              ((dialog?.kind === "record" || dialog?.kind === "correct") && !valueValid) ||
              (dialog?.kind === "record" && !form.period.trim()) ||
              (dialog?.kind === "correct" && !form.reason.trim())
            }
          >
            {t("kpiPerformance.save")}
          </Button>
        </DialogActions>
      </Dialog>
    </Accordion>
  );
}
