import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import CircularProgress from "@mui/material/CircularProgress";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Autocomplete from "@mui/material/Autocomplete";
import Tooltip from "@mui/material/Tooltip";
import MaterialSymbol from "@/components/MaterialSymbol";
import MetricCard from "@/features/reports/MetricCard";
import { useCurrency } from "@/hooks/useCurrency";
import { api } from "@/api/client";

const TIME_DECISIONS = ["undecided", "tolerate", "invest", "migrate", "eliminate"] as const;
type TimeDecision = (typeof TIME_DECISIONS)[number];

const DECISION_COLOR: Record<TimeDecision, "default" | "info" | "success" | "warning" | "error"> = {
  undecided: "default",
  tolerate: "info",
  invest: "success",
  migrate: "warning",
  eliminate: "error",
};

interface CardBrief {
  id: string;
  name: string;
  type: string;
}

interface Decision {
  id: string;
  card: CardBrief | null;
  time_decision: TimeDecision;
  successor: CardBrief | null;
  initiative: CardBrief | null;
  annual_cost: number | null;
  planned_savings: number | null;
  risk_note: string | null;
  notes: string | null;
  progress: number;
}

interface CampaignSummary {
  id: string;
  name: string;
  description: string | null;
  status: string;
  target_savings: number | null;
  decision_count: number;
  planned_savings_total: number;
}

interface CampaignDetail extends Omit<CampaignSummary, "decision_count" | "planned_savings_total"> {
  decisions: Decision[];
  summary: {
    decision_count: number;
    by_decision: Record<string, number>;
    planned_savings_total: number;
    target_savings: number | null;
  };
}

export default function ApplicationRationalizationBoard() {
  const { t } = useTranslation(["reports", "common"]);
  const { fmtShort } = useCurrency();
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [active, setActive] = useState<CampaignDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [newCampaignOpen, setNewCampaignOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newTarget, setNewTarget] = useState("");
  const [decisionDialog, setDecisionDialog] = useState(false);
  const [appOptions, setAppOptions] = useState<CardBrief[]>([]);
  const [decisionCard, setDecisionCard] = useState<CardBrief | null>(null);
  const [decisionType, setDecisionType] = useState<TimeDecision>("undecided");
  // Campaign edit
  const [editCampaignOpen, setEditCampaignOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editTarget, setEditTarget] = useState("");
  const [editStatus, setEditStatus] = useState("draft");
  // Decision edit
  const [editDecision, setEditDecision] = useState<Decision | null>(null);
  const [edSuccessor, setEdSuccessor] = useState<CardBrief | null>(null);
  const [edCost, setEdCost] = useState("");
  const [edSavings, setEdSavings] = useState("");
  const [edProgress, setEdProgress] = useState("0");
  const [edNotes, setEdNotes] = useState("");

  const loadCampaigns = useCallback(async () => {
    setLoading(true);
    try {
      setCampaigns(await api.get<CampaignSummary[]>("/rationalization/campaigns"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCampaigns();
  }, [loadCampaigns]);

  const openCampaign = useCallback(async (id: string) => {
    setActive(await api.get<CampaignDetail>(`/rationalization/campaigns/${id}`));
  }, []);

  const createCampaign = async () => {
    if (!newName.trim()) return;
    const created = await api.post<CampaignSummary>("/rationalization/campaigns", {
      name: newName,
      target_savings: newTarget ? Number(newTarget) : null,
    });
    setNewCampaignOpen(false);
    setNewName("");
    setNewTarget("");
    await loadCampaigns();
    await openCampaign(created.id);
  };

  const searchApps = async (q: string) => {
    if (q.trim().length < 2) {
      setAppOptions([]);
      return;
    }
    const res = await api.get<{ items: CardBrief[] }>(
      `/cards?search=${encodeURIComponent(q)}&type=Application&page_size=20`,
    );
    setAppOptions(res.items ?? []);
  };

  const addDecision = async () => {
    if (!active || !decisionCard) return;
    await api.post(`/rationalization/campaigns/${active.id}/decisions`, {
      card_id: decisionCard.id,
      time_decision: decisionType,
    });
    setDecisionDialog(false);
    setDecisionCard(null);
    setDecisionType("undecided");
    await openCampaign(active.id);
    await loadCampaigns();
  };

  const updateDecision = async (id: string, patch: Partial<Decision>) => {
    if (!active) return;
    await api.patch(`/rationalization/decisions/${id}`, patch);
    await openCampaign(active.id);
    await loadCampaigns();
  };

  const deleteDecision = async (id: string) => {
    if (!active) return;
    if (!window.confirm(t("rationalization.confirmDeleteDecision"))) return;
    await api.delete(`/rationalization/decisions/${id}`);
    await openCampaign(active.id);
    await loadCampaigns();
  };

  const saveCampaignEdit = async () => {
    if (!active || !editName.trim()) return;
    await api.patch(`/rationalization/campaigns/${active.id}`, {
      name: editName,
      target_savings: editTarget ? Number(editTarget) : null,
      status: editStatus,
    });
    setEditCampaignOpen(false);
    await openCampaign(active.id);
    await loadCampaigns();
  };

  const deleteCampaign = async (id: string, name: string) => {
    if (!window.confirm(t("rationalization.confirmDeleteCampaign", { name }))) return;
    await api.delete(`/rationalization/campaigns/${id}`);
    if (active?.id === id) setActive(null);
    await loadCampaigns();
  };

  const openDecisionEdit = (d: Decision) => {
    setEditDecision(d);
    setEdSuccessor(d.successor);
    setEdCost(d.annual_cost != null ? String(d.annual_cost) : "");
    setEdSavings(d.planned_savings != null ? String(d.planned_savings) : "");
    setEdProgress(String(d.progress ?? 0));
    setEdNotes(d.notes || "");
  };

  const saveDecisionEdit = async () => {
    if (!active || !editDecision) return;
    await api.patch(`/rationalization/decisions/${editDecision.id}`, {
      successor_id: edSuccessor?.id ?? null,
      annual_cost: edCost ? Number(edCost) : null,
      planned_savings: edSavings ? Number(edSavings) : null,
      progress: Number(edProgress) || 0,
      notes: edNotes || null,
    });
    setEditDecision(null);
    await openCampaign(active.id);
    await loadCampaigns();
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  // Campaign list view.
  if (!active) {
    return (
      <Box sx={{ maxWidth: 1200, mx: "auto", p: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}>
          <MaterialSymbol icon="recycling" size={26} color="#0f7eb5" />
          <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>
            {t("rationalization.title")}
          </Typography>
          <Button
            variant="contained"
            startIcon={<MaterialSymbol icon="add" size={18} />}
            onClick={() => setNewCampaignOpen(true)}
          >
            {t("rationalization.newCampaign")}
          </Button>
        </Box>

        {campaigns.length === 0 ? (
          <Box sx={{ textAlign: "center", py: 8, color: "text.secondary" }}>
            <MaterialSymbol icon="recycling" size={48} />
            <Typography sx={{ mt: 2 }}>{t("rationalization.emptyState")}</Typography>
          </Box>
        ) : (
          campaigns.map((c) => (
            <Paper
              key={c.id}
              variant="outlined"
              sx={{ p: 2, mb: 1.5, cursor: "pointer", display: "flex", alignItems: "center", gap: 2 }}
              onClick={() => openCampaign(c.id)}
            >
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                  {c.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("rationalization.appsAssessed", { count: c.decision_count })} ·{" "}
                  {t("rationalization.plannedSavings")}: {fmtShort(c.planned_savings_total)}
                </Typography>
              </Box>
              <Chip size="small" label={t(`rationalization.status.${c.status}`)} />
              <Tooltip title={t("common:actions.delete")}>
                <IconButton
                  size="small"
                  color="error"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteCampaign(c.id, c.name);
                  }}
                >
                  <MaterialSymbol icon="delete" size={18} />
                </IconButton>
              </Tooltip>
              <MaterialSymbol icon="chevron_right" size={20} />
            </Paper>
          ))
        )}

        <Dialog open={newCampaignOpen} onClose={() => setNewCampaignOpen(false)} fullWidth maxWidth="sm">
          <DialogTitle>{t("rationalization.newCampaign")}</DialogTitle>
          <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
            <TextField
              autoFocus
              label={t("rationalization.campaignName")}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              fullWidth
            />
            <TextField
              label={t("rationalization.targetSavings")}
              type="number"
              value={newTarget}
              onChange={(e) => setNewTarget(e.target.value)}
              fullWidth
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setNewCampaignOpen(false)}>{t("common:actions.cancel")}</Button>
            <Button variant="contained" onClick={createCampaign}>
              {t("common:actions.create")}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    );
  }

  // Campaign detail / board view.
  const savingsPct = active.summary.target_savings
    ? Math.min(100, (active.summary.planned_savings_total / active.summary.target_savings) * 100)
    : null;

  return (
    <Box sx={{ maxWidth: 1200, mx: "auto", p: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <IconButton onClick={() => setActive(null)} size="small">
          <MaterialSymbol icon="arrow_back" size={20} />
        </IconButton>
        <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>
          {active.name}
        </Typography>
        <Button
          variant="contained"
          startIcon={<MaterialSymbol icon="add" size={18} />}
          onClick={() => setDecisionDialog(true)}
        >
          {t("rationalization.addApp")}
        </Button>
        <Tooltip title={t("common:actions.edit")}>
          <IconButton
            size="small"
            onClick={() => {
              setEditName(active.name);
              setEditTarget(active.target_savings != null ? String(active.target_savings) : "");
              setEditStatus(active.status);
              setEditCampaignOpen(true);
            }}
          >
            <MaterialSymbol icon="edit" size={20} />
          </IconButton>
        </Tooltip>
        <Tooltip title={t("common:actions.delete")}>
          <IconButton size="small" color="error" onClick={() => deleteCampaign(active.id, active.name)}>
            <MaterialSymbol icon="delete" size={20} />
          </IconButton>
        </Tooltip>
      </Box>

      <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 3 }}>
        <MetricCard
          label={t("rationalization.appsAssessedShort")}
          value={active.summary.decision_count}
          icon="apps"
        />
        <MetricCard
          label={t("rationalization.plannedSavings")}
          value={fmtShort(active.summary.planned_savings_total)}
          icon="savings"
          color="#33cc58"
        />
        {active.summary.target_savings != null && (
          <MetricCard
            label={t("rationalization.targetSavings")}
            value={fmtShort(active.summary.target_savings)}
            icon="flag"
            subtitle={savingsPct != null ? `${Math.round(savingsPct)}%` : undefined}
          />
        )}
        <MetricCard
          label={t("rationalization.toEliminate")}
          value={active.summary.by_decision.eliminate || 0}
          icon="delete"
          color="#d32f2f"
        />
      </Box>

      <Paper variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("rationalization.colApp")}</TableCell>
              <TableCell>{t("rationalization.colDecision")}</TableCell>
              <TableCell>{t("rationalization.colSuccessor")}</TableCell>
              <TableCell align="right">{t("rationalization.colAnnualCost")}</TableCell>
              <TableCell align="right">{t("rationalization.colSavings")}</TableCell>
              <TableCell>{t("rationalization.colProgress")}</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {active.decisions.map((d) => (
              <TableRow key={d.id} hover>
                <TableCell>
                  {d.card && (
                    <Box component="a" href={`/cards/${d.card.id}`} sx={{ color: "primary.main", textDecoration: "none" }}>
                      {d.card.name}
                    </Box>
                  )}
                </TableCell>
                <TableCell>
                  <TextField
                    select
                    size="small"
                    value={d.time_decision}
                    onChange={(e) => updateDecision(d.id, { time_decision: e.target.value as TimeDecision })}
                    sx={{ minWidth: 130 }}
                    SelectProps={{
                      renderValue: (v) => (
                        <Chip
                          size="small"
                          label={t(`rationalization.decision.${v as string}`)}
                          color={DECISION_COLOR[v as TimeDecision]}
                        />
                      ),
                    }}
                  >
                    {TIME_DECISIONS.map((dec) => (
                      <MenuItem key={dec} value={dec}>
                        {t(`rationalization.decision.${dec}`)}
                      </MenuItem>
                    ))}
                  </TextField>
                </TableCell>
                <TableCell>{d.successor?.name || "—"}</TableCell>
                <TableCell align="right">
                  {d.annual_cost != null ? fmtShort(d.annual_cost) : "—"}
                </TableCell>
                <TableCell align="right">
                  {d.planned_savings != null ? fmtShort(d.planned_savings) : "—"}
                </TableCell>
                <TableCell>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 120 }}>
                    <LinearProgress
                      variant="determinate"
                      value={d.progress}
                      sx={{ flex: 1, height: 6, borderRadius: 3 }}
                    />
                    <Typography variant="caption">{d.progress}%</Typography>
                  </Box>
                </TableCell>
                <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                  <Tooltip title={t("common:actions.edit")}>
                    <IconButton size="small" onClick={() => openDecisionEdit(d)}>
                      <MaterialSymbol icon="edit" size={18} />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title={t("common:actions.delete")}>
                    <IconButton size="small" color="error" onClick={() => deleteDecision(d.id)}>
                      <MaterialSymbol icon="delete" size={18} />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Dialog
        open={decisionDialog}
        onClose={() => setDecisionDialog(false)}
        fullWidth
        maxWidth="sm"
        disableRestoreFocus
      >
        <DialogTitle>{t("rationalization.addApp")}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <Autocomplete
            options={appOptions}
            value={decisionCard}
            getOptionLabel={(o) => o.name}
            isOptionEqualToValue={(a, b) => a.id === b.id}
            onChange={(_, v) => setDecisionCard(v)}
            onInputChange={(_, v) => searchApps(v)}
            filterOptions={(x) => x}
            renderInput={(p) => (
              <TextField {...p} label={t("rationalization.colApp")} autoFocus />
            )}
          />
          <TextField
            select
            label={t("rationalization.colDecision")}
            value={decisionType}
            onChange={(e) => setDecisionType(e.target.value as TimeDecision)}
          >
            {TIME_DECISIONS.map((dec) => (
              <MenuItem key={dec} value={dec}>
                {t(`rationalization.decision.${dec}`)}
              </MenuItem>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDecisionDialog(false)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={addDecision} disabled={!decisionCard}>
            {t("common:actions.add")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit campaign dialog */}
      <Dialog open={editCampaignOpen} onClose={() => setEditCampaignOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{t("rationalization.editCampaign")}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            autoFocus
            label={t("rationalization.campaignName")}
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            fullWidth
          />
          <TextField
            label={t("rationalization.targetSavings")}
            type="number"
            value={editTarget}
            onChange={(e) => setEditTarget(e.target.value)}
            fullWidth
          />
          <TextField
            select
            label={t("rationalization.statusLabel")}
            value={editStatus}
            onChange={(e) => setEditStatus(e.target.value)}
          >
            {["draft", "active", "completed", "archived"].map((s) => (
              <MenuItem key={s} value={s}>
                {t(`rationalization.status.${s}`)}
              </MenuItem>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditCampaignOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={saveCampaignEdit}>
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit decision dialog */}
      <Dialog
        open={!!editDecision}
        onClose={() => setEditDecision(null)}
        fullWidth
        maxWidth="sm"
        disableRestoreFocus
      >
        <DialogTitle>
          {t("rationalization.editDecision")}
          {editDecision?.card && (
            <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
              {editDecision.card.name}
            </Typography>
          )}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <Autocomplete
            options={appOptions}
            value={edSuccessor}
            getOptionLabel={(o) => o.name}
            isOptionEqualToValue={(a, b) => a.id === b.id}
            onChange={(_, v) => setEdSuccessor(v)}
            onInputChange={(_, v) => searchApps(v)}
            filterOptions={(x) => x}
            renderInput={(p) => <TextField {...p} label={t("rationalization.colSuccessor")} />}
          />
          <TextField
            label={t("rationalization.colAnnualCost")}
            type="number"
            value={edCost}
            onChange={(e) => setEdCost(e.target.value)}
          />
          <TextField
            label={t("rationalization.colSavings")}
            type="number"
            value={edSavings}
            onChange={(e) => setEdSavings(e.target.value)}
          />
          <TextField
            label={t("rationalization.colProgress")}
            type="number"
            inputProps={{ min: 0, max: 100 }}
            value={edProgress}
            onChange={(e) => setEdProgress(e.target.value)}
          />
          <TextField
            label={t("common:labels.description")}
            value={edNotes}
            onChange={(e) => setEdNotes(e.target.value)}
            multiline
            minRows={2}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDecision(null)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={saveDecisionEdit}>
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
