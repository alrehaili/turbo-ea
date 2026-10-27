import { useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import LinkifiedText from "@/components/LinkifiedText";
import { api } from "@/api/client";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useAbortableEffect } from "@/hooks/useLatestRequest";
import { useDateFormat } from "@/hooks/useDateFormat";
import type { DecisionAction, DecisionImplementationState, ImplementationEvidence } from "@/types";

interface Props {
  kind: "adr" | "arb";
  decisionId: string;
  /** The cards the decision is about; their documents and files can be cited. */
  linkedCardIds: string[];
}

interface UserOption {
  id: string;
  display_name: string;
  is_active?: boolean;
}

interface EvidenceOption {
  kind: "document" | "attachment";
  id: string;
  name: string;
}

type DialogKind = "action" | "complete" | "due" | "submit" | "verify" | "return" | null;

const STATE_COLOR: Record<string, "default" | "info" | "warning" | "success"> = {
  no_plan: "default",
  in_progress: "info",
  awaiting_verification: "warning",
  implemented: "success",
};

/**
 * Implementation of an approved decision (D-13, D-32, D-41): its deadline, its
 * actions (owner, due date, completion evidence) and the independent
 * verification. The server enforces every rule — owner and due date required,
 * evidence on completion, a verifier who owned, completed and submitted none of
 * it, a reason for every deadline change; the buttons only spare a refusal.
 */
export default function DecisionImplementationPanel({ kind, decisionId, linkedCardIds }: Props) {
  const { t } = useTranslation("delivery");
  const k = (key: string, opts?: Record<string, unknown>) =>
    t(`decisionImplementation.${key}`, opts);
  const { formatDate, formatDateTime } = useDateFormat();
  const base = `/${kind}/${decisionId}`;
  const [refetchKey, setRefetchKey] = useState(0);
  const { data, error: loadError } = useApiQuery<DecisionImplementationState>(
    `${base}/implementation`,
    { refetchKey },
  );

  const [dialog, setDialog] = useState<DialogKind>(null);
  const [target, setTarget] = useState<DecisionAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Form fields, shared by the dialogs (only one is open at a time).
  const [text, setText] = useState("");
  const [text2, setText2] = useState("");
  const [date, setDate] = useState("");
  const [owner, setOwner] = useState<UserOption | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [chosen, setChosen] = useState<string[]>([]);
  const [references, setReferences] = useState<string[]>([]);
  const [users, setUsers] = useState<UserOption[]>([]);
  const [evidenceOptions, setEvidenceOptions] = useState<EvidenceOption[]>([]);

  // People to own an action, loaded when that dialog opens.
  useAbortableEffect(
    async ({ signal, isCurrent }) => {
      if (dialog !== "action") return;
      try {
        const list = await api.get<UserOption[]>("/users", { signal });
        if (isCurrent()) setUsers(list.filter((u) => u.is_active !== false));
      } catch {
        if (isCurrent()) setUsers([]);
      }
    },
    [dialog],
  );

  // The linked cards' existing documents and files, offered as evidence.
  const cardKey = linkedCardIds.join(",");
  useAbortableEffect(
    async ({ signal, isCurrent }) => {
      if (dialog !== "complete" || linkedCardIds.length === 0) return;
      const load = async <T,>(path: string): Promise<T[]> => {
        try {
          return await api.get<T[]>(path, { signal });
        } catch {
          return [];
        }
      };
      const lists = await Promise.all(
        linkedCardIds.flatMap((id) => [
          load<{ id: string; name: string }>(`/cards/${id}/documents`).then((rows) =>
            rows.map((r) => ({ kind: "document" as const, id: r.id, name: r.name })),
          ),
          load<{ id: string; name: string }>(`/cards/${id}/file-attachments`).then((rows) =>
            rows.map((r) => ({ kind: "attachment" as const, id: r.id, name: r.name })),
          ),
        ]),
      );
      if (isCurrent()) setEvidenceOptions(lists.flat());
    },
    [dialog, cardKey],
  );

  const openDialog = (next: DialogKind, action: DecisionAction | null = null) => {
    setDialog(next);
    setTarget(action);
    setError(null);
    setText(action && next === "action" ? action.description : "");
    setText2("");
    setDate(
      next === "due"
        ? data?.implementation.due_date ?? ""
        : action && next === "action"
          ? action.due_date ?? ""
          : "",
    );
    setOwner(
      action?.assigned_to && next === "action"
        ? { id: action.assigned_to.id, display_name: action.assigned_to.display_name ?? "" }
        : null,
    );
    setConfirmed(false);
    setChosen([]);
    setReferences([]);
  };

  const run = async (call: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await call();
      setDialog(null);
      setRefetchKey((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : k("failed"));
    } finally {
      setBusy(false);
    }
  };

  if (loadError) {
    return <Alert severity="error">{k("loadFailed")}</Alert>;
  }
  if (!data) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  const impl = data.implementation;
  const perms = data.permissions;
  const approved = data.decision.approved;
  const verified = impl.status === "verified";
  const allDone = data.actions.length > 0 && data.actions.every((a) => a.status === "done");
  // An unsigned ADR's deadline is a proposal the signatories approve by signing.
  const proposing = kind === "adr" && !approved;

  const submitDialog = () => {
    if (dialog === "action") {
      const body = { description: text.trim(), assigned_to: owner?.id ?? null, due_date: date || null };
      return run(() =>
        target ? api.patch(`${base}/actions/${target.id}`, body) : api.post(`${base}/actions`, body),
      );
    }
    if (dialog === "complete" && target) {
      const evidence = [
        ...evidenceOptions
          .filter((o) => chosen.includes(`${o.kind}:${o.id}`))
          .map((o) => ({ kind: o.kind, id: o.id })),
        ...references.map((r) => ({ kind: "reference", text: r })),
      ];
      return run(() =>
        api.post(`${base}/actions/${target.id}/complete`, { note: text, evidence }),
      );
    }
    if (dialog === "due") {
      return run(() =>
        api.put(`${base}/implementation/due-date`, { due_date: date || null, reason: text || null }),
      );
    }
    if (dialog === "submit") {
      return run(() => api.post(`${base}/implementation/submit`, { note: text || null }));
    }
    if (dialog === "verify") {
      return run(() =>
        api.post(`${base}/implementation/verify`, {
          outcome: "verified",
          attestation: { examined: text, demonstrates: text2, confirmed },
        }),
      );
    }
    if (dialog === "return") {
      return run(() =>
        api.post(`${base}/implementation/verify`, { outcome: "returned", note: text }),
      );
    }
  };

  const renderEvidence = (e: ImplementationEvidence, i: number) => {
    if ("hidden" in e) return <Chip key={i} size="small" label={k("evidenceHidden")} />;
    if (e.kind === "reference") {
      return (
        <Chip
          key={i}
          size="small"
          variant="outlined"
          icon={<MaterialSymbol icon="tag" size={14} />}
          label={e.text}
        />
      );
    }
    return (
      <Chip
        key={i}
        size="small"
        variant="outlined"
        icon={<MaterialSymbol icon={e.kind === "document" ? "link" : "attach_file"} size={14} />}
        label={e.name}
      />
    );
  };

  return (
    <Box data-testid="decision-implementation">
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5, flexWrap: "wrap" }}>
        <MaterialSymbol icon="task_alt" size={22} />
        <Typography variant="h6" sx={{ fontWeight: 700, flex: 1 }}>
          {k("title")}
        </Typography>
        {approved && (
          <Chip size="small" color={STATE_COLOR[data.state]} label={k(`state.${data.state}`)} />
        )}
        {data.overdue && <Chip size="small" color="error" label={k("overdue")} />}
      </Box>

      {/* Deadline */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5, flexWrap: "wrap" }}>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {proposing ? k("proposedDeadline") : k("deadline")}:
        </Typography>
        <Typography variant="body2">
          {impl.due_date ? formatDate(impl.due_date) : k("noDeadline")}
        </Typography>
        {impl.revised && impl.original_due_date && (
          <Typography variant="caption" color="text.secondary">
            {k("originalDeadline", { date: formatDate(impl.original_due_date) })}
          </Typography>
        )}
        {impl.due_date_basis === "set_after_decision" && (
          <Chip size="small" variant="outlined" label={k("setAfterDecision")} />
        )}
        {perms.manage && !verified && (proposing || approved) && (
          <Button size="small" onClick={() => openDialog("due")}>
            {impl.due_date ? k("changeDeadline") : k("setDeadline")}
          </Button>
        )}
      </Box>

      {!approved ? (
        <Typography variant="body2" color="text.secondary">
          {k(kind === "adr" ? "notSignedYet" : "notApprovedYet")}
        </Typography>
      ) : (
        <>
          {data.actions.length === 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {k("noActions")}
            </Typography>
          )}
          {data.actions.map((a) => {
            return (
              <Paper key={a.id} variant="outlined" sx={{ p: 1.5, mb: 1 }}>
                <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1 }}>
                  <MaterialSymbol
                    icon={a.status === "done" ? "check_circle" : "radio_button_unchecked"}
                    size={20}
                  />
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      <LinkifiedText text={a.description} />
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {k("actionMeta", {
                        owner: a.assigned_to?.display_name ?? "—",
                        date: a.due_date ? formatDate(a.due_date) : "—",
                      })}
                    </Typography>
                    {a.status === "done" && (
                      <Box sx={{ mt: 0.5 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                          {k("completedBy", {
                            name: a.completed_by?.display_name ?? "—",
                            date: a.completed_at ? formatDateTime(a.completed_at) : "—",
                          })}
                        </Typography>
                        {a.completion_note && (
                          <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                            <LinkifiedText text={a.completion_note} />
                          </Typography>
                        )}
                        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mt: 0.5 }}>
                          {a.evidence.map(renderEvidence)}
                          {impl.text_withheld && a.evidence_count > 0 && (
                            <Chip size="small" label={k("evidenceWithheld", { count: a.evidence_count })} />
                          )}
                        </Box>
                      </Box>
                    )}
                  </Box>
                  <Box sx={{ display: "flex", gap: 0.5 }}>
                    {!verified && a.can_complete && (
                      a.status !== "done" ? (
                        <Button size="small" onClick={() => openDialog("complete", a)}>
                          {k("complete")}
                        </Button>
                      ) : (
                        <Button size="small" onClick={() => run(() => api.post(`${base}/actions/${a.id}/reopen`, {}))}>
                          {k("reopen")}
                        </Button>
                      )
                    )}
                    {/* Rewording stays possible after verification (cosmetic, I-44). */}
                    {perms.manage && (
                      <Tooltip title={k("editAction")}>
                        <IconButton size="small" onClick={() => openDialog("action", a)}>
                          <MaterialSymbol icon="edit" size={18} />
                        </IconButton>
                      </Tooltip>
                    )}
                    {perms.manage && !verified && (
                      <Tooltip title={k("deleteAction")}>
                        <IconButton
                          size="small"
                          onClick={() => run(() => api.delete(`${base}/actions/${a.id}`))}
                        >
                          <MaterialSymbol icon="delete" size={18} />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </Box>
              </Paper>
            );
          })}

          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1 }}>
            {perms.manage && !verified && (
              <Button
                size="small"
                variant="outlined"
                startIcon={<MaterialSymbol icon="add" size={18} />}
                onClick={() => openDialog("action")}
              >
                {k("addAction")}
              </Button>
            )}
            {perms.submit && impl.status === "open" && allDone && (
              <Button size="small" variant="contained" onClick={() => openDialog("submit")}>
                {k("submit")}
              </Button>
            )}
            {perms.verify && impl.status === "submitted" && (
              <>
                <Button size="small" variant="contained" color="success" onClick={() => openDialog("verify")}>
                  {k("verify")}
                </Button>
                <Button size="small" onClick={() => openDialog("return")}>
                  {k("return")}
                </Button>
              </>
            )}
          </Box>

          {impl.status === "submitted" && (
            <Alert severity="info" sx={{ mt: 1.5 }}>
              {k("awaitingInfo", {
                name: impl.submitted_by?.display_name ?? "—",
                date: impl.submitted_at ? formatDateTime(impl.submitted_at) : "—",
              })}
            </Alert>
          )}
          {verified && (
            <Alert severity="success" sx={{ mt: 1.5 }}>
              {k("verifiedInfo", {
                name: impl.verified_by?.display_name ?? "—",
                date: impl.verified_at ? formatDateTime(impl.verified_at) : "—",
              })}
              {impl.attestation && (
                <Box sx={{ mt: 0.5 }}>
                  <Typography variant="body2">
                    <strong>{k("examined")}:</strong> <LinkifiedText text={impl.attestation.examined} />
                  </Typography>
                  <Typography variant="body2">
                    <strong>{k("demonstrates")}:</strong>{" "}
                    <LinkifiedText text={impl.attestation.demonstrates} />
                  </Typography>
                </Box>
              )}
            </Alert>
          )}
        </>
      )}

      {data.history.recorded && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.5 }}>
            {k("history")}
          </Typography>
          {data.history.transitions.map((h, i) => (
            <Typography key={i} variant="caption" color="text.secondary" sx={{ display: "block" }}>
              {h.occurred_at ? formatDateTime(h.occurred_at) : "—"} ·{" "}
              {h.event_kind
                ? k(`event.${h.event_kind}`, {
                    from: h.previous_due_date ? formatDate(h.previous_due_date) : "—",
                    to: h.due_date ? formatDate(h.due_date) : "—",
                  })
                : k("move", { from: h.from_status ?? "—", to: h.to_status })}{" "}
              · {h.actor?.display_name ?? "—"}
              {h.reason ? ` — ${h.reason}` : ""}
            </Typography>
          ))}
        </Box>
      )}

      <Dialog open={dialog !== null} onClose={() => setDialog(null)} fullWidth maxWidth="sm" disableRestoreFocus>
        <DialogTitle>{dialog ? k(`dialog.${dialog === "action" && target ? "editAction" : dialog}`) : ""}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          {dialog === "action" && (
            <>
              <TextField
                autoFocus
                label={k("field.description")}
                value={text}
                onChange={(e) => setText(e.target.value)}
                multiline
                minRows={2}
                fullWidth
              />
              <Autocomplete
                options={users}
                value={owner}
                getOptionLabel={(o) => o.display_name}
                isOptionEqualToValue={(a, b) => a.id === b.id}
                onChange={(_, v) => setOwner(v)}
                // Once verified, only the wording may change (I-44).
                disabled={verified}
                renderInput={(p) => <TextField {...p} label={k("field.owner")} />}
              />
              <TextField
                type="date"
                label={k("field.dueDate")}
                value={date}
                disabled={verified}
                onChange={(e) => setDate(e.target.value)}
                fullWidth
              />
            </>
          )}
          {dialog === "complete" && (
            <>
              <TextField
                autoFocus
                label={k("field.completionNote")}
                value={text}
                onChange={(e) => setText(e.target.value)}
                multiline
                minRows={2}
                fullWidth
              />
              <Typography variant="body2">{k("evidenceHelp")}</Typography>
              {evidenceOptions.map((o) => {
                const key = `${o.kind}:${o.id}`;
                return (
                  <FormControlLabel
                    key={key}
                    control={
                      <Checkbox
                        checked={chosen.includes(key)}
                        onChange={(e) =>
                          setChosen((c) => (e.target.checked ? [...c, key] : c.filter((x) => x !== key)))
                        }
                      />
                    }
                    label={o.name}
                  />
                );
              })}
              <Box sx={{ display: "flex", gap: 1 }}>
                <TextField
                  label={k("field.reference")}
                  placeholder={k("field.referenceHint")}
                  value={text2}
                  onChange={(e) => setText2(e.target.value)}
                  fullWidth
                />
                <Button
                  onClick={() => {
                    if (text2.trim()) setReferences((r) => [...r, text2.trim()]);
                    setText2("");
                  }}
                >
                  {k("addReference")}
                </Button>
              </Box>
              <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                {references.map((r, i) => (
                  <Chip
                    key={i}
                    size="small"
                    label={r}
                    onDelete={() => setReferences((rs) => rs.filter((_, j) => j !== i))}
                  />
                ))}
              </Box>
            </>
          )}
          {dialog === "due" && (
            <>
              <TextField
                type="date"
                label={k("field.deadline")}
                value={date}
                onChange={(e) => setDate(e.target.value)}
                fullWidth
              />
              {!proposing && (
                <TextField
                  label={k("field.reason")}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  multiline
                  minRows={2}
                  fullWidth
                  helperText={k("reasonHelp")}
                />
              )}
            </>
          )}
          {dialog === "submit" && (
            <TextField
              autoFocus
              label={k("field.submissionNote")}
              value={text}
              onChange={(e) => setText(e.target.value)}
              multiline
              minRows={2}
              fullWidth
            />
          )}
          {dialog === "verify" && (
            <>
              <Typography variant="body2">{k("verifyHelp")}</Typography>
              <TextField
                autoFocus
                label={k("examined")}
                value={text}
                onChange={(e) => setText(e.target.value)}
                multiline
                minRows={2}
                fullWidth
              />
              <TextField
                label={k("demonstrates")}
                value={text2}
                onChange={(e) => setText2(e.target.value)}
                multiline
                minRows={2}
                fullWidth
              />
              <FormControlLabel
                control={<Checkbox checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />}
                label={k("confirm")}
              />
            </>
          )}
          {dialog === "return" && (
            <TextField
              autoFocus
              label={k("field.returnNote")}
              value={text}
              onChange={(e) => setText(e.target.value)}
              multiline
              minRows={2}
              fullWidth
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialog(null)}>{k("cancel")}</Button>
          <Button variant="contained" disabled={busy} onClick={submitDialog}>
            {k("save")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
