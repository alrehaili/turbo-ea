/**
 * OpportunitiesPanel — Improvement Opportunity registry (NORA Stage 6.6).
 * Governable records classified by architecture domain, linked to the cards
 * they concern and the transition initiative that realises them.
 *
 * [FORK FEATURE] — noraPlan.md WP3.3.
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import CardPicker, { type CardOption } from "@/components/CardPicker";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { useAuthContext } from "@/hooks/AuthContext";
import { hasPermission } from "@/components/RequirePermission";

interface Opportunity {
  id: string;
  title: string;
  description: string | null;
  domain: "BA" | "AA" | "DA" | "TA";
  source: string;
  priority: "low" | "medium" | "high";
  status: "proposed" | "approved" | "inTransition" | "realized" | "rejected";
  initiative: { id: string; name: string } | null;
  cards: { id: string; name: string; type: string }[];
}

const DOMAINS = ["BA", "AA", "DA", "TA"] as const;
const PRIORITIES = ["low", "medium", "high"] as const;
const STATUSES = ["proposed", "approved", "inTransition", "realized", "rejected"] as const;

const STATUS_COLOR: Record<string, "default" | "info" | "success" | "warning" | "error"> = {
  proposed: "default",
  approved: "info",
  inTransition: "warning",
  realized: "success",
  rejected: "error",
};

interface FormState {
  title: string;
  description: string;
  domain: (typeof DOMAINS)[number];
  priority: (typeof PRIORITIES)[number];
}

const EMPTY_FORM: FormState = { title: "", description: "", domain: "AA", priority: "medium" };

export default function OpportunitiesPanel() {
  const { t } = useTranslation(["grc", "common"]);
  const { user } = useAuthContext();
  const canManage = hasPermission(user?.permissions, "grc.manage");
  const [rows, setRows] = useState<Opportunity[] | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [initiativeFor, setInitiativeFor] = useState<Opportunity | null>(null);
  const [initiative, setInitiative] = useState<CardOption | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setRows(await api.get<Opportunity[]>("/improvement-opportunities"));
    } catch {
      setRows([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    if (!form.title.trim()) return;
    setError("");
    try {
      if (editingId) {
        await api.patch(`/improvement-opportunities/${editingId}`, form);
      } else {
        await api.post("/improvement-opportunities", form);
      }
      setDialogOpen(false);
      setEditingId(null);
      setForm(EMPTY_FORM);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common:errors.generic"));
    }
  };

  const setStatus = async (o: Opportunity, status: string) => {
    await api.patch(`/improvement-opportunities/${o.id}`, { status });
    await load();
  };

  const assignInitiative = async () => {
    if (!initiativeFor || !initiative) return;
    await api.patch(`/improvement-opportunities/${initiativeFor.id}`, {
      initiative_id: initiative.id,
    });
    setInitiativeFor(null);
    setInitiative(null);
    await load();
  };

  const remove = async (o: Opportunity) => {
    if (!window.confirm(t("governance.opportunities.confirmDelete", { title: o.title }))) return;
    await api.delete(`/improvement-opportunities/${o.id}`);
    await load();
  };

  if (rows === null) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
        {canManage && (
          <Button
            variant="contained"
            startIcon={<MaterialSymbol icon="add" size={18} />}
            onClick={() => {
              setEditingId(null);
              setForm(EMPTY_FORM);
              setDialogOpen(true);
            }}
          >
            {t("governance.opportunities.new")}
          </Button>
        )}
      </Box>

      {rows.length === 0 ? (
        <Alert severity="info">{t("governance.opportunities.empty")}</Alert>
      ) : (
        <Paper variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>
                  {t("governance.opportunities.colTitle")}
                </TableCell>
                <TableCell sx={{ fontWeight: 700 }}>
                  {t("governance.opportunities.colDomain")}
                </TableCell>
                <TableCell sx={{ fontWeight: 700 }}>
                  {t("governance.opportunities.colPriority")}
                </TableCell>
                <TableCell sx={{ fontWeight: 700 }}>
                  {t("governance.opportunities.colStatus")}
                </TableCell>
                <TableCell sx={{ fontWeight: 700 }}>
                  {t("governance.opportunities.colInitiative")}
                </TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((o) => (
                <TableRow key={o.id} hover>
                  <TableCell>
                    <Tooltip title={o.description || ""}>
                      <span>{o.title}</span>
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <Chip size="small" variant="outlined" label={o.domain} />
                  </TableCell>
                  <TableCell>{t(`governance.opportunities.priority.${o.priority}`)}</TableCell>
                  <TableCell>
                    {canManage ? (
                      <TextField
                        select
                        size="small"
                        variant="standard"
                        value={o.status}
                        onChange={(e) => setStatus(o, e.target.value)}
                        sx={{ minWidth: 130 }}
                      >
                        {STATUSES.map((s) => (
                          <MenuItem key={s} value={s}>
                            {t(`governance.opportunities.status.${s}`)}
                          </MenuItem>
                        ))}
                      </TextField>
                    ) : (
                      <Chip
                        size="small"
                        color={STATUS_COLOR[o.status]}
                        label={t(`governance.opportunities.status.${o.status}`)}
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    {o.initiative ? (
                      <Chip
                        size="small"
                        variant="outlined"
                        component="a"
                        href={`/cards/${o.initiative.id}`}
                        clickable
                        label={o.initiative.name}
                      />
                    ) : canManage ? (
                      <Button
                        size="small"
                        onClick={() => {
                          setInitiativeFor(o);
                          setInitiative(null);
                        }}
                      >
                        {t("governance.opportunities.assign")}
                      </Button>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {canManage && (
                      <>
                        <IconButton
                          size="small"
                          onClick={() => {
                            setEditingId(o.id);
                            setForm({
                              title: o.title,
                              description: o.description || "",
                              domain: o.domain,
                              priority: o.priority,
                            });
                            setDialogOpen(true);
                          }}
                        >
                          <MaterialSymbol icon="edit" size={18} />
                        </IconButton>
                        <IconButton size="small" color="error" onClick={() => remove(o)}>
                          <MaterialSymbol icon="delete" size={18} />
                        </IconButton>
                      </>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}

      {/* Create / edit dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>
          {editingId
            ? t("governance.opportunities.edit")
            : t("governance.opportunities.new")}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField
            autoFocus
            label={t("governance.opportunities.colTitle")}
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            fullWidth
          />
          <TextField
            label={t("governance.opportunities.description")}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            multiline
            minRows={3}
          />
          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              select
              label={t("governance.opportunities.colDomain")}
              value={form.domain}
              onChange={(e) => setForm({ ...form, domain: e.target.value as FormState["domain"] })}
              sx={{ flex: 1 }}
            >
              {DOMAINS.map((d) => (
                <MenuItem key={d} value={d}>
                  {d}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label={t("governance.opportunities.colPriority")}
              value={form.priority}
              onChange={(e) =>
                setForm({ ...form, priority: e.target.value as FormState["priority"] })
              }
              sx={{ flex: 1 }}
            >
              {PRIORITIES.map((p) => (
                <MenuItem key={p} value={p}>
                  {t(`governance.opportunities.priority.${p}`)}
                </MenuItem>
              ))}
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={save}>
            {editingId ? t("common:actions.save") : t("common:actions.create")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Assign initiative dialog */}
      <Dialog
        open={!!initiativeFor}
        onClose={() => setInitiativeFor(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>{t("governance.opportunities.assign")}</DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          <CardPicker
            types="Initiative"
            value={initiative}
            onChange={setInitiative}
            label={t("governance.opportunities.colInitiative")}
            enabled={!!initiativeFor}
            autoFocus
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInitiativeFor(null)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={assignInitiative} disabled={!initiative}>
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
