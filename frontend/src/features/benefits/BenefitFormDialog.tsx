import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "@/api/client";
import CardPicker, { type CardOption } from "@/components/CardPicker";
import { useAuthContext } from "@/hooks/AuthContext";
import { hasPermission } from "@/components/RequirePermission";
import { useApiQuery } from "@/hooks/useApiQuery";
import type {
  BenefitClassification,
  BenefitDetail,
  BenefitMeasurement,
  BenefitType,
} from "@/types";

const TYPES: BenefitType[] = ["cost_saving", "cost_avoidance", "revenue", "productivity", "non_financial"];
const FINANCIAL: BenefitType[] = ["cost_saving", "cost_avoidance", "revenue"];
const CLASSIFICATIONS: BenefitClassification[] = ["direct", "contributing", "not_attributable"];

interface DecisionOption {
  id: string;
  title: string;
  reference_number?: string;
}

interface Props {
  open: boolean;
  /** The benefit being edited; null creates a new one. */
  benefit: BenefitDetail | null;
  onClose: () => void;
  onSaved: (benefit: BenefitDetail) => void;
}

const num = (v: string): number | null => (v.trim() === "" ? null : Number(v));
const str = (v: number | null | undefined): string => (v === null || v === undefined ? "" : String(v));

/**
 * Creates or edits a benefit (D-12). Financial benefits carry a currency and
 * amounts; non-financial ones never do (D-43) and name a KPI card or are
 * assessed qualitatively. Each initiative carries its D-14 classification; the
 * money itself is only allocated by Finance when an actual is confirmed.
 * Validation locks the financial basis (I-67), so those fields are read-only
 * on a validated benefit.
 */
export default function BenefitFormDialog({ open, benefit, onClose, onSaved }: Props) {
  const { t } = useTranslation("common");
  const { user } = useAuthContext();
  const k = (key: string) => `benefits.form.${key}`;
  const editing = benefit !== null;
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState<BenefitType>("cost_saving");
  const [measurement, setMeasurement] = useState<BenefitMeasurement>("kpi");
  const [currency, setCurrency] = useState("SAR");
  const [recurrence, setRecurrence] = useState<"one_time" | "annual">("annual");
  const [planned, setPlanned] = useState("");
  const [baseline, setBaseline] = useState("");
  const [counterfactual, setCounterfactual] = useState("");
  const [counterfactualNote, setCounterfactualNote] = useState("");
  const [method, setMethod] = useState("");
  const [expectedFy, setExpectedFy] = useState("");
  const [initiatives, setInitiatives] = useState<CardOption[]>([]);
  const [classes, setClasses] = useState<Record<string, BenefitClassification>>({});
  const [affected, setAffected] = useState<CardOption[]>([]);
  const [kpi, setKpi] = useState<CardOption | null>(null);
  const [decisionKind, setDecisionKind] = useState<"" | "adr" | "arb">("");
  const [decisionId, setDecisionId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setError(null);
    setTitle(benefit?.title ?? "");
    setDescription(benefit?.description ?? "");
    setType(benefit?.benefit_type ?? "cost_saving");
    setMeasurement(benefit && benefit.measurement !== "financial" ? benefit.measurement : "kpi");
    setCurrency(benefit?.currency ?? "SAR");
    setRecurrence(benefit?.recurrence ?? "annual");
    setPlanned(str(benefit?.planned_amount));
    setBaseline(str(benefit?.baseline_amount));
    setCounterfactual(str(benefit?.counterfactual_amount));
    setCounterfactualNote(benefit?.counterfactual_note ?? "");
    setMethod(benefit?.method_note ?? "");
    setExpectedFy(str(benefit?.expected_fiscal_year));
    setInitiatives((benefit?.initiatives ?? []).map(({ id, name, type: ct }) => ({ id, name, type: ct })));
    setClasses(Object.fromEntries((benefit?.initiatives ?? []).map((i) => [i.id, i.classification])));
    setAffected(benefit?.affected ?? []);
    setKpi(benefit?.kpi_card ?? null);
    const kind = benefit?.decision?.kind;
    setDecisionKind(kind === "adr" || kind === "arb" ? kind : "");
    setDecisionId(benefit?.decision?.id ?? "");
  }, [open, benefit]);

  const canAdr = hasPermission(user?.permissions, "adr.view");
  const canArb = hasPermission(user?.permissions, "arb.view");
  const { data: adrs } = useApiQuery<DecisionOption[]>(
    open && decisionKind === "adr" && canAdr ? "/adr?status=signed" : null,
  );
  const { data: reviews } = useApiQuery<DecisionOption[]>(
    open && decisionKind === "arb" && canArb ? "/arb?status=approved" : null,
  );
  const decisionOptions = decisionKind === "adr" ? adrs ?? [] : decisionKind === "arb" ? reviews ?? [] : [];

  const financial = FINANCIAL.includes(type);
  const locked = editing && benefit?.status !== "planned";
  // A decision kind the form does not offer (rationalization, opportunity) is kept as is.
  const keepsOtherDecision =
    editing && benefit?.decision != null && benefit.decision.kind !== "adr" && benefit.decision.kind !== "arb";
  const anchored = initiatives.length > 0 || (decisionKind !== "" && decisionId !== "") || keepsOtherDecision;

  const save = async () => {
    setBusy(true);
    setError(null);
    const body: Record<string, unknown> = {
      title,
      description: description || null,
      initiatives: initiatives.map((c) => ({ card_id: c.id, classification: classes[c.id] ?? "contributing" })),
      affected: affected.map((c) => c.id),
    };
    if (!keepsOtherDecision) {
      body.decision_kind = decisionKind || null;
      body.decision_id = decisionKind ? decisionId || null : null;
    }
    if (!editing) {
      body.benefit_type = type;
      if (!financial) body.measurement = measurement;
    }
    const outcomeMeasurement = editing ? benefit.measurement : financial ? "financial" : measurement;
    if (outcomeMeasurement === "kpi") body.kpi_card_id = kpi?.id ?? null;
    if (financial && !locked) {
      Object.assign(body, {
        currency: currency.trim().toUpperCase(),
        recurrence,
        planned_amount: num(planned),
        baseline_amount: num(baseline),
        counterfactual_amount: num(counterfactual),
        counterfactual_note: counterfactualNote || null,
        method_note: method || null,
        expected_fiscal_year: num(expectedFy),
      });
    }
    try {
      const saved = editing
        ? await api.patch<BenefitDetail>(`/benefits/${benefit.id}`, body)
        : await api.post<BenefitDetail>("/benefits", body);
      onSaved(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : t(k("failed")));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md" disableRestoreFocus>
      <DialogTitle>{t(k(editing ? "editTitle" : "createTitle"))}</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        {error && <Alert severity="error">{error}</Alert>}
        <TextField
          label={t(k("title"))}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          inputProps={{ maxLength: 300 }}
          required
          fullWidth
          sx={{ mt: 1 }}
        />
        <TextField
          label={t(k("description"))}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          multiline
          minRows={2}
          fullWidth
        />
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <TextField
            select
            label={t(k("type"))}
            value={type}
            onChange={(e) => setType(e.target.value as BenefitType)}
            disabled={editing}
            sx={{ minWidth: 220 }}
          >
            {TYPES.map((v) => (
              <MenuItem key={v} value={v}>
                {t(`benefits.type.${v}`)}
              </MenuItem>
            ))}
          </TextField>
          {!financial && (
            <TextField
              select
              label={t(k("measurement"))}
              value={measurement}
              onChange={(e) => setMeasurement(e.target.value as BenefitMeasurement)}
              disabled={editing}
              sx={{ minWidth: 220 }}
            >
              <MenuItem value="kpi">{t("benefits.measurement.kpi")}</MenuItem>
              <MenuItem value="qualitative">{t("benefits.measurement.qualitative")}</MenuItem>
            </TextField>
          )}
        </Box>

        {financial ? (
          <>
            {locked && <Alert severity="info">{t(k("lockedBasis"))}</Alert>}
            <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
              <TextField
                label={t(k("currency"))}
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                inputProps={{ maxLength: 3 }}
                disabled={locked}
                sx={{ width: 120 }}
              />
              <TextField
                select
                label={t(k("recurrence"))}
                value={recurrence}
                onChange={(e) => setRecurrence(e.target.value as "one_time" | "annual")}
                disabled={locked}
                sx={{ minWidth: 160 }}
              >
                <MenuItem value="annual">{t("benefits.recurrence.annual")}</MenuItem>
                <MenuItem value="one_time">{t("benefits.recurrence.one_time")}</MenuItem>
              </TextField>
              <TextField
                label={t(k("planned"))}
                helperText={recurrence === "annual" ? t(k("plannedAnnual")) : undefined}
                type="number"
                value={planned}
                onChange={(e) => setPlanned(e.target.value)}
                disabled={locked}
                sx={{ width: 200 }}
              />
              <TextField
                label={t(k("expectedFy"))}
                type="number"
                value={expectedFy}
                onChange={(e) => setExpectedFy(e.target.value)}
                disabled={locked}
                sx={{ width: 200 }}
              />
            </Box>
            {type === "cost_saving" && (
              <TextField
                label={t(k("baseline"))}
                type="number"
                value={baseline}
                onChange={(e) => setBaseline(e.target.value)}
                disabled={locked}
                sx={{ width: 260 }}
              />
            )}
            {type === "cost_avoidance" && (
              <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                <TextField
                  label={t(k("counterfactual"))}
                  type="number"
                  value={counterfactual}
                  onChange={(e) => setCounterfactual(e.target.value)}
                  disabled={locked}
                  sx={{ width: 260 }}
                />
                <TextField
                  label={t(k("counterfactualNote"))}
                  value={counterfactualNote}
                  onChange={(e) => setCounterfactualNote(e.target.value)}
                  disabled={locked}
                  sx={{ flex: 1, minWidth: 240 }}
                />
              </Box>
            )}
            <TextField
              label={t(k("method"))}
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              disabled={locked}
              multiline
              minRows={2}
              fullWidth
            />
          </>
        ) : (
          <>
            <Alert severity="info">{t(k("outcomeNoMoney"))}</Alert>
            {(editing ? benefit.measurement : measurement) === "kpi" && (
              <CardPicker types="KPI" value={kpi} onChange={setKpi} label={t(k("kpi"))} fullWidth />
            )}
          </>
        )}

        <Typography variant="subtitle2">{t(k("anchor"))}</Typography>
        <CardPicker
          multiple
          types="Initiative"
          value={initiatives}
          onChange={setInitiatives}
          label={t(k("initiatives"))}
          fullWidth
        />
        {initiatives.map((c) => (
          <Box key={c.id} sx={{ display: "flex", alignItems: "center", gap: 2, pl: 1 }}>
            <Typography variant="body2" sx={{ flex: 1 }} dir="auto">
              {c.name}
            </Typography>
            <TextField
              select
              size="small"
              label={t(k("classification"))}
              value={classes[c.id] ?? "contributing"}
              onChange={(e) =>
                setClasses((prev) => ({ ...prev, [c.id]: e.target.value as BenefitClassification }))
              }
              sx={{ minWidth: 200 }}
            >
              {CLASSIFICATIONS.map((v) => (
                <MenuItem key={v} value={v}>
                  {t(`benefits.classification.${v}`)}
                </MenuItem>
              ))}
            </TextField>
          </Box>
        ))}
        {keepsOtherDecision ? (
          <Typography variant="body2" color="text.secondary">
            {t(k("decisionKept"))}
          </Typography>
        ) : (
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
            <TextField
              select
              label={t(k("decisionKind"))}
              value={decisionKind}
              onChange={(e) => {
                setDecisionKind(e.target.value as "" | "adr" | "arb");
                setDecisionId("");
              }}
              sx={{ minWidth: 240 }}
            >
              <MenuItem value="">{t(k("decisionNone"))}</MenuItem>
              {canAdr && <MenuItem value="adr">{t(k("decisionAdr"))}</MenuItem>}
              {canArb && <MenuItem value="arb">{t(k("decisionArb"))}</MenuItem>}
            </TextField>
            {decisionKind && (
              <TextField
                select
                label={t(k("decision"))}
                value={decisionId}
                onChange={(e) => setDecisionId(e.target.value)}
                sx={{ flex: 1, minWidth: 240 }}
              >
                {decisionOptions.map((d) => (
                  <MenuItem key={d.id} value={d.id}>
                    {d.reference_number ? `${d.reference_number} ${d.title}` : d.title}
                  </MenuItem>
                ))}
              </TextField>
            )}
          </Box>
        )}
        {!anchored && (
          <Typography variant="caption" color="warning.main">
            {t(k("anchorHint"))}
          </Typography>
        )}
        <CardPicker multiple value={affected} onChange={setAffected} label={t(k("affected"))} fullWidth />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("actions.cancel")}</Button>
        <Button variant="contained" disabled={busy || !title.trim() || !anchored} onClick={save}>
          {t(k("save"))}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
