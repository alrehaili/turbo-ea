import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "@/api/client";
import LinkifiedText from "@/components/LinkifiedText";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useDateFormat } from "@/hooks/useDateFormat";
import type { BenefitActualRow, BenefitDetail, BenefitEvidence } from "@/types";
import BenefitFormDialog from "./BenefitFormDialog";
import { ACTUAL_STATUS_COLOR, BENEFIT_STATUS_COLOR, formatMoney, referencesFromText } from "./benefitFormat";

type Action =
  | { kind: "validate" }
  | { kind: "reopen" }
  | { kind: "withdraw" }
  | { kind: "not_realised" }
  | { kind: "report" }
  | { kind: "assess" }
  | { kind: "confirm"; actual: BenefitActualRow }
  | { kind: "reject"; actual: BenefitActualRow }
  | { kind: "reverse"; actual: BenefitActualRow };

interface Props {
  benefitId: string | null;
  onClose: () => void;
  onChanged: () => void;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Box sx={{ mb: 1 }}>
      <Typography variant="caption" color="text.secondary" component="div">
        {label}
      </Typography>
      <Typography variant="body2" component="div">
        {children}
      </Typography>
    </Box>
  );
}

/**
 * One benefit: its basis, links, actuals by fiscal year, assessments and the
 * append-only history, with the actions the viewer's permissions allow. The
 * server enforces every rule — the buttons only mirror them (D-29: a Finance
 * user who created, owns, estimated or reported the benefit sees why they may
 * not decide).
 */
export default function BenefitDrawer({ benefitId, onClose, onChanged }: Props) {
  const { t, i18n } = useTranslation("common");
  const { formatDate, formatDateTime } = useDateFormat();
  const [refetchKey, setRefetchKey] = useState(0);
  const { data, error, loading } = useApiQuery<BenefitDetail>(
    benefitId ? `/benefits/${benefitId}` : null,
    { refetchKey },
  );
  const [action, setAction] = useState<Action | null>(null);
  const [editing, setEditing] = useState(false);
  const k = (key: string) => `benefits.drawer.${key}`;

  const refresh = () => {
    setRefetchKey((n) => n + 1);
    onChanged();
  };
  const money = (v: number | null | undefined) =>
    v === null || v === undefined || !data?.currency ? "—" : formatMoney(v, data.currency, i18n.language);

  const evidence = (items: BenefitEvidence[]) => (
    <Box component="ul" sx={{ m: 0, pl: 2 }}>
      {items.map((e, i) => (
        <li key={i}>
          {e.restricted ? (
            <Typography variant="caption" color="text.secondary">
              {t(k("restrictedEvidence"))}
            </Typography>
          ) : e.kind === "reference" ? (
            <LinkifiedText text={e.text ?? ""} />
          ) : (
            <>
              {e.card_id ? (
                <Link component={RouterLink} to={`/cards/${e.card_id}`}>
                  {e.name}
                </Link>
              ) : (
                e.name
              )}
              {e.missing && (
                <Typography variant="caption" color="warning.main" sx={{ ml: 1 }}>
                  {t(k("missingEvidence"))}
                </Typography>
              )}
            </>
          )}
        </li>
      ))}
    </Box>
  );

  const body = () => {
    if (error) return <Alert severity="error">{error.message}</Alert>;
    if (!data) return loading ? <LinearProgress /> : null;
    const p = data.permissions;
    const financial = data.measurement === "financial";
    const open = data.status === "planned" || data.status === "validated";
    return (
      <>
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
          <Chip size="small" label={t(`benefits.type.${data.benefit_type}`)} />
          <Chip size="small" variant="outlined" label={t(`benefits.measurement.${data.measurement}`)} />
          <Chip size="small" color={BENEFIT_STATUS_COLOR[data.status]} label={t(`benefits.status.${data.status}`)} />
          {!data.governance_link && (
            <Chip size="small" variant="outlined" color="warning" label={t("benefits.noGovernanceLink")} />
          )}
        </Box>
        {data.description && (
          <Typography variant="body2" sx={{ mb: 2, whiteSpace: "pre-wrap" }} dir="auto">
            <LinkifiedText text={data.description} />
          </Typography>
        )}
        <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
          {p.manage && open && (
            <Button size="small" variant="outlined" onClick={() => setEditing(true)}>
              {t("benefits.actions.edit")}
            </Button>
          )}
          {p.validate && financial && data.status === "planned" && (
            <Button size="small" variant="contained" onClick={() => setAction({ kind: "validate" })}>
              {t("benefits.actions.validate")}
            </Button>
          )}
          {p.validate && data.status === "validated" && (
            <Button size="small" variant="outlined" onClick={() => setAction({ kind: "reopen" })}>
              {t("benefits.actions.reopen")}
            </Button>
          )}
          {p.manage && financial && data.status === "validated" && (
            <Button size="small" variant="contained" onClick={() => setAction({ kind: "report" })}>
              {t("benefits.actions.reportActual")}
            </Button>
          )}
          {p.manage && data.measurement === "qualitative" && open && (
            <Button size="small" variant="contained" onClick={() => setAction({ kind: "assess" })}>
              {t("benefits.actions.assess")}
            </Button>
          )}
          {p.manage && open && (
            <Button size="small" color="warning" onClick={() => setAction({ kind: "withdraw" })}>
              {t("benefits.actions.withdraw")}
            </Button>
          )}
          {p.confirm && open && (
            <Button size="small" color="warning" onClick={() => setAction({ kind: "not_realised" })}>
              {t("benefits.actions.notRealised")}
            </Button>
          )}
        </Box>

        {financial && (
          <>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {t(k("basis"))}
            </Typography>
            {data.amounts_restricted && <Alert severity="info" sx={{ mb: 1 }}>{t("benefits.amountRestricted")}</Alert>}
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, columnGap: 2 }}>
              <Field label={t(k("planned"))}>
                <bdi>{money(data.planned_amount)}</bdi>
                {data.recurrence && ` · ${t(`benefits.recurrence.${data.recurrence}`)}`}
              </Field>
              <Field label={t(k("expectedFy"))}>{data.expected_fiscal_year ?? "—"}</Field>
              {data.benefit_type === "cost_saving" && (
                <Field label={t(k("baseline"))}>
                  <bdi>{money(data.baseline_amount)}</bdi>
                </Field>
              )}
              {data.benefit_type === "cost_avoidance" && (
                <Field label={t(k("counterfactual"))}>
                  <bdi>{money(data.counterfactual_amount)}</bdi>
                  {data.counterfactual_note && <> · <LinkifiedText text={data.counterfactual_note} /></>}
                </Field>
              )}
              <Field label={t(k("estimatedBy"))}>{data.estimated_by?.name ?? "—"}</Field>
              <Field label={t(k("validatedBy"))}>
                {data.validated_by
                  ? `${data.validated_by.name ?? ""} · ${data.validated_at ? formatDate(data.validated_at) : ""}`
                  : "—"}
              </Field>
            </Box>
            {data.method_note && (
              <Field label={t(k("method"))}>
                <LinkifiedText text={data.method_note} />
              </Field>
            )}
          </>
        )}

        <Divider sx={{ my: 2 }} />
        <Field label={t(k("owner"))}>{data.owner?.name ?? "—"}</Field>
        <Field label={t(k("decision"))}>
          {data.decision ? (
            data.decision.path && data.decision.title ? (
              <Link component={RouterLink} to={data.decision.path}>
                {data.decision.title}
              </Link>
            ) : (
              t(k("decisionRestricted"))
            )
          ) : (
            "—"
          )}
        </Field>
        <Field label={t(k("initiatives"))}>
          {data.initiatives.length === 0
            ? "—"
            : data.initiatives.map((i) => (
                <Box key={i.id}>
                  <Link component={RouterLink} to={`/cards/${i.id}`}>
                    {i.name}
                  </Link>{" "}
                  · {t(`benefits.classification.${i.classification}`)}
                </Box>
              ))}
        </Field>
        {data.affected.length > 0 && (
          <Field label={t(k("affected"))}>
            {data.affected.map((c, idx) => (
              <span key={c.id}>
                {idx > 0 && ", "}
                <Link component={RouterLink} to={`/cards/${c.id}`}>
                  {c.name}
                </Link>
              </span>
            ))}
          </Field>
        )}
        {data.measurement === "kpi" && (
          <Field label={t(k("kpi"))}>
            {data.kpi_card ? (
              <Link component={RouterLink} to={`/cards/${data.kpi_card.id}`}>
                {data.kpi_card.name}
              </Link>
            ) : (
              "—"
            )}
          </Field>
        )}
        {data.close_reason && (
          <Field label={t(k("closeReason"))}>
            <LinkifiedText text={data.close_reason} />
          </Field>
        )}

        {financial && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {t(k("actuals"))}
            </Typography>
            {data.actuals.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                {t(k("noActuals"))}
              </Typography>
            )}
            {data.actuals.map((a) => (
              <Box key={a.id} sx={{ p: 1.5, mb: 1, border: 1, borderColor: "divider", borderRadius: 1 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                  <Typography variant="body2" fontWeight={700} sx={{ flex: 1 }}>
                    {t(k("fiscalYear"), { fy: a.fiscal_year })} · <bdi>{money(a.amount)}</bdi>
                  </Typography>
                  <Chip size="small" color={ACTUAL_STATUS_COLOR[a.status]} label={t(`benefits.actualStatus.${a.status}`)} />
                </Box>
                <Typography variant="caption" color="text.secondary" component="div">
                  {t(k("reportedBy"), {
                    name: a.reported_by?.name ?? "—",
                    date: a.reported_at ? formatDateTime(a.reported_at) : "",
                  })}
                </Typography>
                {a.note && (
                  <Typography variant="body2" dir="auto">
                    <LinkifiedText text={a.note} />
                  </Typography>
                )}
                <Typography variant="caption" color="text.secondary">
                  {t(k("evidence"))}
                </Typography>
                {evidence(a.evidence)}
                {a.decided_by && (
                  <Typography variant="caption" color="text.secondary" component="div">
                    {t(k("decidedBy"), {
                      name: a.decided_by.name ?? "—",
                      date: a.decided_at ? formatDateTime(a.decided_at) : "",
                    })}
                    {a.finance_reference && ` · ${t(k("financeReference"))}: ${a.finance_reference}`}
                  </Typography>
                )}
                {a.decision_note && (
                  <Typography variant="body2" dir="auto">
                    <LinkifiedText text={a.decision_note} />
                  </Typography>
                )}
                {a.allocations.length > 0 && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      {t(k("allocations"))}
                    </Typography>
                    {a.allocations.map((al, i) => (
                      <Typography key={i} variant="body2">
                        {al.initiative?.name ?? t(k("deletedInitiative"))} ·{" "}
                        {t(`benefits.classification.${al.classification}`)} · <bdi>{money(al.amount)}</bdi> —{" "}
                        <LinkifiedText text={al.rationale} />
                      </Typography>
                    ))}
                  </Box>
                )}
                {a.reverse_reason && (
                  <Typography variant="body2" color="text.secondary" dir="auto">
                    {t(k("reversedBecause"))}: <LinkifiedText text={a.reverse_reason} />
                  </Typography>
                )}
                {p.confirm && (a.status === "reported" || a.status === "confirmed") && (
                  <Box sx={{ mt: 1 }}>
                    {a.independence_conflict ? (
                      <Alert severity="info" variant="outlined">
                        {t(k("independence"))}
                      </Alert>
                    ) : a.status === "reported" ? (
                      <Box sx={{ display: "flex", gap: 1 }}>
                        <Button size="small" variant="contained" color="success" onClick={() => setAction({ kind: "confirm", actual: a })}>
                          {t("benefits.actions.confirm")}
                        </Button>
                        <Button size="small" color="error" onClick={() => setAction({ kind: "reject", actual: a })}>
                          {t("benefits.actions.reject")}
                        </Button>
                      </Box>
                    ) : (
                      <Button size="small" onClick={() => setAction({ kind: "reverse", actual: a })}>
                        {t("benefits.actions.reverse")}
                      </Button>
                    )}
                  </Box>
                )}
              </Box>
            ))}
          </>
        )}

        {data.measurement === "qualitative" && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2">{t(k("assessments"))}</Typography>
            <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1 }}>
              {t(k("assessedLabel"))}
            </Typography>
            {data.assessments.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                {t(k("noAssessments"))}
              </Typography>
            )}
            {data.assessments.map((r) => (
              <Box key={r.id} sx={{ p: 1.5, mb: 1, border: 1, borderColor: "divider", borderRadius: 1 }}>
                <Typography variant="body2" fontWeight={700}>
                  {t(k("fiscalYear"), { fy: r.fiscal_year })} · {t(`benefits.outcome.${r.outcome}`)}
                </Typography>
                <Typography variant="caption" color="text.secondary" component="div">
                  {t(k("assessedBy"), {
                    name: r.assessed_by?.name ?? "—",
                    date: r.assessed_at ? formatDateTime(r.assessed_at) : "",
                  })}
                </Typography>
                <Typography variant="body2" dir="auto">
                  <LinkifiedText text={r.note} />
                </Typography>
                {evidence(r.evidence)}
              </Box>
            ))}
          </>
        )}

        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          {t(k("history"))}
        </Typography>
        {data.history.map((h) => (
          <Box key={h.id} sx={{ mb: 1 }}>
            <Typography variant="body2">
              {t(`benefits.history.${h.action}`, { defaultValue: h.action })}
              {h.to_status && ` → ${t(`benefits.historyStatus.${h.to_status}`, { defaultValue: h.to_status })}`}
            </Typography>
            <Typography variant="caption" color="text.secondary" component="div">
              {h.actor?.name ?? "—"} · {h.occurred_at ? formatDateTime(h.occurred_at) : ""}
            </Typography>
            {h.note && (
              <Typography variant="caption" component="div" dir="auto">
                <LinkifiedText text={h.note} />
              </Typography>
            )}
          </Box>
        ))}
      </>
    );
  };

  return (
    <>
      <Drawer
        anchor="right"
        open={!!benefitId}
        onClose={onClose}
        PaperProps={{ sx: { width: { xs: "100%", sm: 560 }, p: 2 } }}
      >
        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1, mb: 1 }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary">
              {data?.reference}
            </Typography>
            <Typography variant="h6" fontWeight={700} dir="auto">
              {data?.title}
            </Typography>
          </Box>
          <IconButton onClick={onClose} aria-label={t("actions.close")}>
            <MaterialSymbol icon="close" />
          </IconButton>
        </Box>
        {body()}
      </Drawer>
      {data && (
        <BenefitFormDialog
          open={editing}
          benefit={data}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            refresh();
          }}
        />
      )}
      {data && action && (
        <BenefitActionDialog
          benefit={data}
          action={action}
          onClose={() => setAction(null)}
          onDone={() => {
            setAction(null);
            refresh();
          }}
        />
      )}
    </>
  );
}

const ACTION_TITLE: Record<Action["kind"], string> = {
  validate: "validate",
  reopen: "reopen",
  withdraw: "withdraw",
  not_realised: "notRealised",
  report: "reportActual",
  assess: "assess",
  confirm: "confirm",
  reject: "reject",
  reverse: "reverse",
};

/**
 * Every workflow step in one dialog: the fields each step needs and nothing
 * else. Notes and reasons are required where the server requires them.
 */
export function BenefitActionDialog({
  benefit,
  action,
  onClose,
  onDone,
}: {
  benefit: BenefitDetail;
  action: Action;
  onClose: () => void;
  onDone: () => void;
}) {
  const { t, i18n } = useTranslation("common");
  const k = (key: string) => `benefits.dialog.${key}`;
  const thisYear = new Date().getFullYear();
  const [text, setText] = useState("");
  const [fy, setFy] = useState(String(thisYear));
  const [amount, setAmount] = useState("");
  const [evidenceText, setEvidenceText] = useState("");
  const [financeRef, setFinanceRef] = useState("");
  const [outcome, setOutcome] = useState("achieved");
  const allocatable = benefit.initiatives.filter((i) => i.classification !== "not_attributable");
  const [alloc, setAlloc] = useState<Record<string, { amount: string; rationale: string }>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const base = `/benefits/${benefit.id}`;
  const needsReason = ["reopen", "withdraw", "not_realised", "reject", "reverse"].includes(action.kind);
  const evidence = referencesFromText(evidenceText);
  const allocations = allocatable
    .filter((i) => alloc[i.id]?.amount)
    .map((i) => ({ card_id: i.id, amount: Number(alloc[i.id].amount), rationale: alloc[i.id].rationale }));
  const confirmAmount = action.kind === "confirm" ? action.actual.amount ?? 0 : 0;
  const allocated = allocations.reduce((s, a) => s + a.amount, 0);

  const ready = (() => {
    if (needsReason) return text.trim() !== "";
    if (action.kind === "report") return amount !== "" && evidence.length > 0 && fy !== "";
    if (action.kind === "assess") return text.trim() !== "" && evidence.length > 0 && fy !== "";
    if (action.kind === "confirm")
      return (
        financeRef.trim() !== "" &&
        allocations.every((a) => a.amount > 0 && a.rationale.trim() !== "") &&
        allocated <= confirmAmount + 0.005
      );
    return true;
  })();

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      switch (action.kind) {
        case "validate":
          await api.post(`${base}/validate`, { note: text || null });
          break;
        case "reopen":
          await api.post(`${base}/reopen`, { reason: text });
          break;
        case "withdraw":
        case "not_realised":
          await api.post(`${base}/close`, { outcome: action.kind === "withdraw" ? "withdrawn" : "not_realised", reason: text });
          break;
        case "report":
          await api.post(`${base}/actuals`, { fiscal_year: Number(fy), amount: Number(amount), note: text || null, evidence });
          break;
        case "assess":
          await api.post(`${base}/assessments`, { fiscal_year: Number(fy), outcome, note: text, evidence });
          break;
        case "confirm":
          await api.post(`${base}/actuals/${action.actual.id}/confirm`, {
            finance_reference: financeRef,
            note: text || null,
            allocations,
          });
          break;
        case "reject":
          await api.post(`${base}/actuals/${action.actual.id}/reject`, { reason: text });
          break;
        case "reverse":
          await api.post(`${base}/actuals/${action.actual.id}/reverse`, { reason: text });
          break;
      }
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : t(k("failed")));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm" disableRestoreFocus>
      <DialogTitle>{t(`benefits.actions.${ACTION_TITLE[action.kind]}`)}</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        {error && <Alert severity="error">{error}</Alert>}
        <Typography variant="body2" fontWeight={600} dir="auto">
          {benefit.reference} · {benefit.title}
        </Typography>
        {(action.kind === "confirm" || action.kind === "reject" || action.kind === "reverse") && (
          <Typography variant="body2">
            {t("benefits.drawer.fiscalYear", { fy: action.actual.fiscal_year })} ·{" "}
            <bdi>
              {action.actual.amount !== null && benefit.currency
                ? formatMoney(action.actual.amount, benefit.currency, i18n.language)
                : "—"}
            </bdi>
          </Typography>
        )}
        {(action.kind === "report" || action.kind === "assess") && (
          <TextField
            label={t(k("fiscalYear"))}
            type="number"
            value={fy}
            onChange={(e) => setFy(e.target.value)}
            sx={{ width: 180, mt: 1 }}
          />
        )}
        {action.kind === "report" && (
          <TextField
            label={t(k("amount"), { currency: benefit.currency ?? "" })}
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            sx={{ width: 240 }}
          />
        )}
        {action.kind === "assess" && (
          <TextField select label={t(k("outcome"))} value={outcome} onChange={(e) => setOutcome(e.target.value)} sx={{ width: 260 }}>
            {["achieved", "partially_achieved", "not_achieved"].map((o) => (
              <MenuItem key={o} value={o}>
                {t(`benefits.outcome.${o}`)}
              </MenuItem>
            ))}
          </TextField>
        )}
        {action.kind === "confirm" && (
          <TextField
            label={t(k("financeReference"))}
            value={financeRef}
            onChange={(e) => setFinanceRef(e.target.value)}
            inputProps={{ maxLength: 200 }}
            required
            fullWidth
            sx={{ mt: 1 }}
          />
        )}
        <TextField
          label={t(k(needsReason ? "reason" : action.kind === "assess" ? "observed" : "note"))}
          value={text}
          onChange={(e) => setText(e.target.value)}
          required={needsReason || action.kind === "assess"}
          multiline
          minRows={2}
          fullWidth
          sx={needsReason || action.kind === "validate" ? { mt: 1 } : undefined}
        />
        {(action.kind === "report" || action.kind === "assess") && (
          <TextField
            label={t(k("evidence"))}
            helperText={t(k("evidenceHint"))}
            value={evidenceText}
            onChange={(e) => setEvidenceText(e.target.value)}
            multiline
            minRows={2}
            required
            fullWidth
          />
        )}
        {action.kind === "confirm" && allocatable.length > 0 && (
          <Box>
            <Typography variant="subtitle2">{t(k("allocate"))}</Typography>
            <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1 }}>
              {t(k("allocationHint"))}
            </Typography>
            {allocatable.map((i) => (
              <Box key={i.id} sx={{ display: "flex", gap: 1, alignItems: "flex-start", mb: 1, flexWrap: "wrap" }}>
                <Typography variant="body2" sx={{ flex: "1 1 160px", pt: 1 }} dir="auto">
                  {i.name} · {t(`benefits.classification.${i.classification}`)}
                </Typography>
                <TextField
                  size="small"
                  type="number"
                  label={t(k("allocationAmount"))}
                  value={alloc[i.id]?.amount ?? ""}
                  onChange={(e) =>
                    setAlloc((prev) => ({ ...prev, [i.id]: { rationale: prev[i.id]?.rationale ?? "", amount: e.target.value } }))
                  }
                  sx={{ width: 140 }}
                />
                <TextField
                  size="small"
                  label={t(k("rationale"))}
                  value={alloc[i.id]?.rationale ?? ""}
                  onChange={(e) =>
                    setAlloc((prev) => ({ ...prev, [i.id]: { amount: prev[i.id]?.amount ?? "", rationale: e.target.value } }))
                  }
                  sx={{ flex: "2 1 200px" }}
                />
              </Box>
            ))}
            {allocated > confirmAmount + 0.005 && (
              <Alert severity="warning">{t(k("overAllocated"))}</Alert>
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("actions.cancel")}</Button>
        <Button variant="contained" disabled={busy || !ready} onClick={submit}>
          {t(k("submit"))}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
