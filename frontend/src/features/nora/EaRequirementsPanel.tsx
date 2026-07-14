/**
 * EA Requirements register panel — NORA WP6.1 (methodology phase 7).
 *
 * Embedded on the NORA Program page. Requirements are registered before a
 * development cycle, approved (governance-gated server-side), tracked while
 * the cycle runs, and change-impact-assessed via the dependency report on
 * their linked cards.
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
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
import Typography from "@mui/material/Typography";
import { useNavigate } from "react-router-dom";
import MaterialSymbol from "@/components/MaterialSymbol";
import CardPicker, { type CardOption } from "@/components/CardPicker";
import { api, ApiError } from "@/api/client";

interface CardBrief {
  id: string;
  name: string;
  type: string;
}

interface EaRequirement {
  id: string;
  title: string;
  description: string | null;
  source: string | null;
  domain: string | null;
  status: "proposed" | "approved" | "inCycle" | "fulfilled" | "rejected" | "changed";
  approved_by_display_name: string | null;
  approved_at: string | null;
  initiative: CardBrief | null;
  cards: CardBrief[];
}

const DOMAINS = [
  "business",
  "beneficiaryExperience",
  "applications",
  "data",
  "technology",
  "security",
] as const;

const STATUSES = ["proposed", "approved", "inCycle", "fulfilled", "rejected", "changed"] as const;

const STATUS_COLOR: Record<string, "default" | "info" | "warning" | "success" | "error"> = {
  proposed: "default",
  approved: "info",
  inCycle: "warning",
  fulfilled: "success",
  rejected: "error",
  changed: "warning",
};

interface EditState {
  id: string | null;
  title: string;
  description: string;
  source: string;
  domain: string;
  cards: CardBrief[];
}

const EMPTY_EDIT: EditState = {
  id: null,
  title: "",
  description: "",
  source: "",
  domain: "",
  cards: [],
};

export default function EaRequirementsPanel({ canManage }: { canManage: boolean }) {
  const { t } = useTranslation(["nav", "common"]);
  const navigate = useNavigate();
  const [rows, setRows] = useState<EaRequirement[]>([]);
  const [error, setError] = useState("");
  const [edit, setEdit] = useState<EditState | null>(null);
  const [linkPick, setLinkPick] = useState<CardOption | null>(null);
  const [initiativeFor, setInitiativeFor] = useState<EaRequirement | null>(null);
  const [initiativePick, setInitiativePick] = useState<CardOption | null>(null);

  const load = useCallback(async () => {
    try {
      setRows(await api.get<EaRequirement[]>("/ea-requirements"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleError = (e: unknown) => {
    setError(
      e instanceof ApiError && typeof e.detail === "string"
        ? e.detail
        : e instanceof Error
          ? e.message
          : "error",
    );
  };

  const save = async () => {
    if (!edit || !edit.title.trim()) return;
    setError("");
    const payload = {
      title: edit.title.trim(),
      description: edit.description.trim() || null,
      source: edit.source.trim() || null,
      domain: edit.domain || null,
      card_ids: edit.cards.map((c) => c.id),
    };
    try {
      if (edit.id) {
        await api.patch(`/ea-requirements/${edit.id}`, payload);
      } else {
        await api.post("/ea-requirements", payload);
      }
      setEdit(null);
      await load();
    } catch (e) {
      handleError(e);
    }
  };

  const setStatus = async (r: EaRequirement, status: string) => {
    setError("");
    try {
      await api.patch(`/ea-requirements/${r.id}`, { status });
      await load();
    } catch (e) {
      handleError(e);
    }
  };

  const assignInitiative = async () => {
    if (!initiativeFor || !initiativePick) return;
    setError("");
    try {
      await api.patch(`/ea-requirements/${initiativeFor.id}`, {
        initiative_id: initiativePick.id,
      });
      setInitiativeFor(null);
      setInitiativePick(null);
      await load();
    } catch (e) {
      handleError(e);
    }
  };

  const remove = async (r: EaRequirement) => {
    setError("");
    try {
      await api.delete(`/ea-requirements/${r.id}`);
      await load();
    } catch (e) {
      handleError(e);
    }
  };

  return (
    <Paper sx={{ p: 3, mt: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
        <MaterialSymbol icon="fact_check" size={22} color="#5e35b1" />
        <Typography variant="h6" fontWeight={700}>
          {t("noraProgram.requirements.title")}
        </Typography>
        <Box sx={{ flex: 1 }} />
        {canManage && (
          <Button
            size="small"
            variant="outlined"
            startIcon={<MaterialSymbol icon="add" size={16} />}
            onClick={() => setEdit({ ...EMPTY_EDIT })}
          >
            {t("noraProgram.requirements.add")}
          </Button>
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("noraProgram.requirements.subtitle")}
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {rows.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          {t("noraProgram.requirements.empty")}
        </Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 700 }}>
                {t("noraProgram.requirements.colTitle")}
              </TableCell>
              <TableCell sx={{ fontWeight: 700, width: 150 }}>
                {t("noraProgram.requirements.colDomain")}
              </TableCell>
              <TableCell sx={{ fontWeight: 700, width: 160 }}>
                {t("noraProgram.colStatus")}
              </TableCell>
              <TableCell sx={{ fontWeight: 700 }}>
                {t("noraProgram.requirements.colLinks")}
              </TableCell>
              <TableCell sx={{ width: 120 }} />
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.id} hover>
                <TableCell>
                  <Tooltip title={r.description || r.source || ""}>
                    <span>{r.title}</span>
                  </Tooltip>
                  {r.source && (
                    <Typography variant="caption" color="text.secondary" display="block">
                      {r.source}
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  {r.domain ? (
                    <Chip
                      size="small"
                      variant="outlined"
                      label={t(`noraProgram.domain.${r.domain}`)}
                    />
                  ) : null}
                </TableCell>
                <TableCell>
                  {canManage ? (
                    <TextField
                      select
                      size="small"
                      variant="standard"
                      value={r.status}
                      onChange={(e) => setStatus(r, e.target.value)}
                      sx={{ minWidth: 130 }}
                    >
                      {STATUSES.map((s) => (
                        <MenuItem key={s} value={s}>
                          {t(`noraProgram.requirements.status.${s}`)}
                        </MenuItem>
                      ))}
                    </TextField>
                  ) : (
                    <Chip
                      size="small"
                      color={STATUS_COLOR[r.status]}
                      label={t(`noraProgram.requirements.status.${r.status}`)}
                    />
                  )}
                </TableCell>
                <TableCell>
                  <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", alignItems: "center" }}>
                    {r.initiative && (
                      <Chip
                        size="small"
                        color="primary"
                        variant="outlined"
                        icon={<MaterialSymbol icon="rocket_launch" size={14} />}
                        label={r.initiative.name}
                        onClick={() => navigate(`/cards/${r.initiative!.id}`)}
                      />
                    )}
                    {r.cards.map((c) => (
                      <Chip
                        key={c.id}
                        size="small"
                        variant="outlined"
                        label={c.name}
                        onClick={() => navigate(`/cards/${c.id}`)}
                      />
                    ))}
                    {r.cards.length > 0 && (
                      <Tooltip title={t("noraProgram.requirements.impact")}>
                        <IconButton
                          size="small"
                          onClick={() =>
                            navigate(`/reports/dependencies?focus=${r.cards[0].id}`)
                          }
                        >
                          <MaterialSymbol icon="hub" size={16} />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </TableCell>
                <TableCell align="right">
                  {canManage && (
                    <>
                      {!r.initiative && (
                        <Tooltip title={t("noraProgram.requirements.assignInitiative")}>
                          <IconButton
                            size="small"
                            onClick={() => {
                              setInitiativeFor(r);
                              setInitiativePick(null);
                            }}
                          >
                            <MaterialSymbol icon="rocket_launch" size={16} />
                          </IconButton>
                        </Tooltip>
                      )}
                      <IconButton
                        size="small"
                        onClick={() =>
                          setEdit({
                            id: r.id,
                            title: r.title,
                            description: r.description ?? "",
                            source: r.source ?? "",
                            domain: r.domain ?? "",
                            cards: r.cards,
                          })
                        }
                      >
                        <MaterialSymbol icon="edit" size={16} />
                      </IconButton>
                      <IconButton size="small" color="error" onClick={() => remove(r)}>
                        <MaterialSymbol icon="delete" size={16} />
                      </IconButton>
                    </>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Create / edit dialog */}
      <Dialog open={!!edit} onClose={() => setEdit(null)} fullWidth maxWidth="sm">
        <DialogTitle>
          {edit?.id
            ? t("noraProgram.requirements.edit")
            : t("noraProgram.requirements.add")}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            autoFocus
            label={t("noraProgram.requirements.colTitle")}
            value={edit?.title ?? ""}
            onChange={(e) => setEdit((p) => (p ? { ...p, title: e.target.value } : p))}
          />
          <TextField
            label={t("noraProgram.requirements.description")}
            multiline
            minRows={2}
            value={edit?.description ?? ""}
            onChange={(e) => setEdit((p) => (p ? { ...p, description: e.target.value } : p))}
          />
          <TextField
            label={t("noraProgram.requirements.source")}
            value={edit?.source ?? ""}
            onChange={(e) => setEdit((p) => (p ? { ...p, source: e.target.value } : p))}
          />
          <TextField
            select
            label={t("noraProgram.requirements.colDomain")}
            value={edit?.domain ?? ""}
            onChange={(e) => setEdit((p) => (p ? { ...p, domain: e.target.value } : p))}
          >
            <MenuItem value="">—</MenuItem>
            {DOMAINS.map((d) => (
              <MenuItem key={d} value={d}>
                {t(`noraProgram.domain.${d}`)}
              </MenuItem>
            ))}
          </TextField>
          <Box>
            <Typography variant="caption" color="text.secondary">
              {t("noraProgram.requirements.colLinks")}
            </Typography>
            <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", my: 1 }}>
              {edit?.cards.map((c) => (
                <Chip
                  key={c.id}
                  size="small"
                  label={c.name}
                  onDelete={() =>
                    setEdit((p) =>
                      p ? { ...p, cards: p.cards.filter((x) => x.id !== c.id) } : p,
                    )
                  }
                />
              ))}
            </Box>
            <CardPicker
              value={linkPick}
              onChange={(v) => {
                if (v) {
                  setEdit((p) =>
                    p && !p.cards.some((c) => c.id === v.id)
                      ? { ...p, cards: [...p.cards, { id: v.id, name: v.name, type: v.type }] }
                      : p,
                  );
                }
                setLinkPick(null);
              }}
              excludeIds={edit?.cards.map((c) => c.id)}
              enabled={!!edit}
              size="small"
              label={t("noraProgram.requirements.linkCard")}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEdit(null)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={save} disabled={!edit?.title.trim()}>
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Assign cycle initiative dialog */}
      <Dialog
        open={!!initiativeFor}
        onClose={() => setInitiativeFor(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>{t("noraProgram.requirements.assignInitiative")}</DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          <CardPicker
            types="Initiative"
            value={initiativePick}
            onChange={setInitiativePick}
            enabled={!!initiativeFor}
            autoFocus
            label={t("noraProgram.requirements.initiative")}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInitiativeFor(null)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={assignInitiative} disabled={!initiativePick}>
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
