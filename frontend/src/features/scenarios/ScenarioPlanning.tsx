import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Autocomplete from "@mui/material/Autocomplete";
import Tooltip from "@mui/material/Tooltip";
import Alert from "@mui/material/Alert";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import MaterialSymbol from "@/components/MaterialSymbol";
import MetricCard from "@/features/reports/MetricCard";
import { useMetamodel } from "@/hooks/useMetamodel";
import { api } from "@/api/client";

type Op = "add" | "modify" | "retire";
const OP_COLOR: Record<Op, "success" | "warning" | "error"> = {
  add: "success",
  modify: "warning",
  retire: "error",
};

interface CardBrief {
  id: string;
  name: string;
  type: string;
}
interface ScenarioChange {
  id: string;
  op: Op;
  card_type: string | null;
  target_card_id: string | null;
  name: string | null;
  payload: Record<string, unknown>;
  merge_status: string | null;
}
interface ScenarioSummary {
  id: string;
  name: string;
  status: string;
  change_count: number;
}
interface ScenarioDetail {
  id: string;
  name: string;
  description: string | null;
  status: string;
  changes: ScenarioChange[];
}
interface DiffData {
  summary: {
    changes: number;
    added: number;
    modified: number;
    retired: number;
    impact_affected: number;
  };
  changes: { id: string; impact_affected: number | null; missing_target: boolean }[];
}
interface MergeResult {
  dry_run: boolean;
  applied: number;
  conflicts: number;
}

export default function ScenarioPlanning() {
  const { t } = useTranslation(["reports", "common"]);
  const { types } = useMetamodel();
  const [list, setList] = useState<ScenarioSummary[]>([]);
  const [detail, setDetail] = useState<ScenarioDetail | null>(null);
  const [diff, setDiff] = useState<DiffData | null>(null);
  const [loading, setLoading] = useState(true);
  const [newOpen, setNewOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [changeOpen, setChangeOpen] = useState(false);
  const [op, setOp] = useState<Op>("add");
  const [cardType, setCardType] = useState("Application");
  const [name, setName] = useState("");
  const [target, setTarget] = useState<CardBrief | null>(null);
  const [options, setOptions] = useState<CardBrief[]>([]);
  const [mergePreview, setMergePreview] = useState<MergeResult | null>(null);

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      setList(await api.get<ScenarioSummary[]>("/scenarios"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadList();
  }, [loadList]);

  const openScenario = async (id: string) => {
    const [d, df] = await Promise.all([
      api.get<ScenarioDetail>(`/scenarios/${id}`),
      api.get<DiffData>(`/scenarios/${id}/diff`),
    ]);
    setDetail(d);
    setDiff(df);
    setMergePreview(null);
  };

  const refresh = async () => {
    if (detail) await openScenario(detail.id);
    await loadList();
  };

  const saveEdit = async () => {
    if (!detail || !editName.trim()) return;
    await api.patch(`/scenarios/${detail.id}`, { name: editName, description: editDesc || null });
    setEditOpen(false);
    await refresh();
  };

  const deleteScenario = async () => {
    if (!detail) return;
    if (!window.confirm(t("scenarios.confirmDelete", { name: detail.name }))) return;
    await api.delete(`/scenarios/${detail.id}`);
    setDetail(null);
    await loadList();
  };

  const createScenario = async () => {
    if (!newName.trim()) return;
    const s = await api.post<ScenarioSummary>("/scenarios", { name: newName });
    setNewOpen(false);
    setNewName("");
    await loadList();
    await openScenario(s.id);
  };

  const searchCards = async (q: string) => {
    if (q.trim().length < 2) return setOptions([]);
    const res = await api.get<{ items: CardBrief[] }>(
      `/cards?search=${encodeURIComponent(q)}&page_size=20`,
    );
    setOptions(res.items ?? []);
  };

  const addChange = async () => {
    if (!detail) return;
    const body: Record<string, unknown> = { op };
    if (op === "add") {
      if (!cardType || !name.trim()) return;
      body.card_type = cardType;
      body.name = name;
    } else {
      if (!target) return;
      body.target_card_id = target.id;
    }
    await api.post(`/scenarios/${detail.id}/changes`, body);
    setChangeOpen(false);
    setName("");
    setTarget(null);
    await refresh();
  };

  const deleteChange = async (id: string) => {
    await api.delete(`/scenarios/changes/${id}`);
    await refresh();
  };

  const previewMerge = async () => {
    if (!detail) return;
    setMergePreview(await api.post<MergeResult>(`/scenarios/${detail.id}/merge?dry_run=true`, {}));
  };

  const doMerge = async () => {
    if (!detail) return;
    await api.post<MergeResult>(`/scenarios/${detail.id}/merge`, {});
    setMergePreview(null);
    await refresh();
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  // --- List view ---
  if (!detail) {
    return (
      <Box sx={{ maxWidth: 1100, mx: "auto", p: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 3 }}>
          <MaterialSymbol icon="account_tree" size={26} color="#33cc58" />
          <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>
            {t("scenarios.title")}
          </Typography>
          <Button
            variant="contained"
            startIcon={<MaterialSymbol icon="add" size={18} />}
            onClick={() => setNewOpen(true)}
          >
            {t("scenarios.newScenario")}
          </Button>
        </Box>
        {list.length === 0 ? (
          <Box sx={{ textAlign: "center", py: 8, color: "text.secondary" }}>
            <MaterialSymbol icon="account_tree" size={48} />
            <Typography sx={{ mt: 2 }}>{t("scenarios.emptyState")}</Typography>
          </Box>
        ) : (
          list.map((s) => (
            <Paper
              key={s.id}
              variant="outlined"
              sx={{ p: 2, mb: 1.5, cursor: "pointer", display: "flex", alignItems: "center", gap: 2 }}
              onClick={() => openScenario(s.id)}
            >
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                  {s.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("scenarios.changeCount", { count: s.change_count })}
                </Typography>
              </Box>
              <Chip size="small" label={t(`scenarios.status.${s.status}`)} />
              <MaterialSymbol icon="chevron_right" size={20} />
            </Paper>
          ))
        )}
        <Dialog open={newOpen} onClose={() => setNewOpen(false)} fullWidth maxWidth="sm">
          <DialogTitle>{t("scenarios.newScenario")}</DialogTitle>
          <DialogContent sx={{ pt: 1 }}>
            <TextField
              autoFocus
              fullWidth
              label={t("scenarios.scenarioName")}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setNewOpen(false)}>{t("common:actions.cancel")}</Button>
            <Button variant="contained" onClick={createScenario}>
              {t("common:actions.create")}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    );
  }

  // --- Detail / diff view ---
  const merged = detail.status === "merged";
  return (
    <Box sx={{ maxWidth: 1100, mx: "auto", p: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <IconButton size="small" onClick={() => setDetail(null)}>
          <MaterialSymbol icon="arrow_back" size={20} />
        </IconButton>
        <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>
          {detail.name}
        </Typography>
        <Chip size="small" label={t(`scenarios.status.${detail.status}`)} sx={{ mr: 1 }} />
        {!merged && (
          <>
            <Button
              variant="outlined"
              startIcon={<MaterialSymbol icon="add" size={18} />}
              onClick={() => setChangeOpen(true)}
            >
              {t("scenarios.addChange")}
            </Button>
            <Tooltip title={t("common:actions.edit")}>
              <IconButton
                size="small"
                onClick={() => {
                  setEditName(detail.name);
                  setEditDesc(detail.description || "");
                  setEditOpen(true);
                }}
              >
                <MaterialSymbol icon="edit" size={20} />
              </IconButton>
            </Tooltip>
          </>
        )}
        <Tooltip title={t("common:actions.delete")}>
          <IconButton size="small" color="error" onClick={deleteScenario}>
            <MaterialSymbol icon="delete" size={20} />
          </IconButton>
        </Tooltip>
      </Box>

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{t("scenarios.editScenario")}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            autoFocus
            label={t("scenarios.scenarioName")}
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            fullWidth
          />
          <TextField
            label={t("common:labels.description")}
            value={editDesc}
            onChange={(e) => setEditDesc(e.target.value)}
            fullWidth
            multiline
            minRows={2}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={saveEdit}>
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>

      {diff && (
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 3 }}>
          <MetricCard label={t("scenarios.added")} value={diff.summary.added} icon="add_circle" color="#2e7d32" />
          <MetricCard label={t("scenarios.modified")} value={diff.summary.modified} icon="edit" color="#ed6c02" />
          <MetricCard label={t("scenarios.retired")} value={diff.summary.retired} icon="cancel" color="#d32f2f" />
          <MetricCard
            label={t("scenarios.impactAffected")}
            value={diff.summary.impact_affected}
            icon="electric_bolt"
          />
        </Box>
      )}

      <Paper variant="outlined" sx={{ mb: 3 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("scenarios.colOp")}</TableCell>
              <TableCell>{t("scenarios.colCard")}</TableCell>
              <TableCell>{t("scenarios.colType")}</TableCell>
              <TableCell align="center">{t("scenarios.colImpact")}</TableCell>
              {!merged && <TableCell />}
              {merged && <TableCell>{t("scenarios.colOutcome")}</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {detail.changes.map((c) => {
              const dr = diff?.changes.find((x) => x.id === c.id);
              return (
                <TableRow key={c.id} hover>
                  <TableCell>
                    <Chip size="small" color={OP_COLOR[c.op]} label={t(`scenarios.op.${c.op}`)} />
                  </TableCell>
                  <TableCell>
                    {c.name}
                    {dr?.missing_target && (
                      <Chip size="small" color="error" label={t("scenarios.missingTarget")} sx={{ ml: 1 }} />
                    )}
                  </TableCell>
                  <TableCell>{c.card_type}</TableCell>
                  <TableCell align="center">{dr?.impact_affected ?? "—"}</TableCell>
                  {!merged && (
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => deleteChange(c.id)}>
                        <MaterialSymbol icon="delete" size={18} />
                      </IconButton>
                    </TableCell>
                  )}
                  {merged && (
                    <TableCell>
                      {c.merge_status && (
                        <Chip
                          size="small"
                          color={c.merge_status === "conflict" ? "error" : "success"}
                          label={t(`scenarios.merge.${c.merge_status}`, c.merge_status)}
                        />
                      )}
                    </TableCell>
                  )}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Paper>

      {/* Merge */}
      {!merged && detail.changes.length > 0 && (
        <Box>
          {mergePreview ? (
            <Alert
              severity={mergePreview.conflicts > 0 ? "warning" : "info"}
              action={
                <Button color="inherit" size="small" onClick={doMerge}>
                  {t("scenarios.confirmMerge")}
                </Button>
              }
              sx={{ mb: 2 }}
            >
              {t("scenarios.mergePreview", {
                applied: mergePreview.applied,
                conflicts: mergePreview.conflicts,
              })}
            </Alert>
          ) : (
            <Button
              variant="contained"
              color="success"
              startIcon={<MaterialSymbol icon="merge" size={18} />}
              onClick={previewMerge}
            >
              {t("scenarios.merge")}
            </Button>
          )}
        </Box>
      )}

      {/* Add-change dialog */}
      <Dialog open={changeOpen} onClose={() => setChangeOpen(false)} fullWidth maxWidth="sm" disableRestoreFocus>
        <DialogTitle>{t("scenarios.addChange")}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            select
            label={t("scenarios.colOp")}
            value={op}
            onChange={(e) => setOp(e.target.value as Op)}
          >
            <MenuItem value="add">{t("scenarios.op.add")}</MenuItem>
            <MenuItem value="modify">{t("scenarios.op.modify")}</MenuItem>
            <MenuItem value="retire">{t("scenarios.op.retire")}</MenuItem>
          </TextField>
          {op === "add" ? (
            <>
              <TextField
                select
                label={t("scenarios.colType")}
                value={cardType}
                onChange={(e) => setCardType(e.target.value)}
              >
                {types.map((tp) => (
                  <MenuItem key={tp.key} value={tp.key}>
                    {tp.label}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label={t("scenarios.cardName")}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </>
          ) : (
            <Autocomplete
              options={options}
              value={target}
              getOptionLabel={(o) => o.name}
              isOptionEqualToValue={(a, b) => a.id === b.id}
              onChange={(_, v) => setTarget(v)}
              onInputChange={(_, v) => searchCards(v)}
              filterOptions={(x) => x}
              renderInput={(p) => <TextField {...p} label={t("scenarios.targetCard")} />}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setChangeOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={addChange}>
            {t("common:actions.add")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
