/**
 * Reference Model — poster narrative editor (RMPlan Phase 3 / §18).
 *
 * Authors the editable poster panels for a model: add / remove / reorder
 * bilingual text or list panels, choose placement (header band vs. grid).
 * List panels edit one item per line (a parallel Arabic textarea keeps the
 * lines aligned). "Load starter panels" seeds the common mission / vision /
 * objectives / stakeholders / principles / KPIs / value set so an admin gets
 * a full poster to trim rather than a blank slate. Saves via
 * PATCH /reference-models/{id}/narrative.
 *
 * [FORK FEATURE] — Reference Models poster (RMPlan/rmPlan.md).
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api, ApiError } from "@/api/client";
import type { ReferenceModel, ReferenceModelNarrativePanel } from "@/types";

type Panel = ReferenceModelNarrativePanel;

const emptyPanel = (id: string): Panel => ({
  id,
  title: "",
  title_ar: "",
  kind: "text",
  text: "",
  text_ar: "",
  items: [],
  items_ar: [],
  placement: "grid",
});

// Starter set mirroring the reference-image posters (English seeds; the admin
// translates + trims). Kept generic so it fits any model type.
function starterPanels(): Panel[] {
  const p = (
    id: string,
    title: string,
    kind: "text" | "list",
    placement: "header" | "grid",
  ): Panel => ({ ...emptyPanel(id), title, kind, placement });
  return [
    p("mission", "Mission", "text", "header"),
    p("vision", "Vision", "text", "header"),
    p("mandate", "Mandate / legal basis", "list", "header"),
    p("objectives", "Strategic objectives", "list", "grid"),
    p("stakeholders", "Key stakeholders", "list", "grid"),
    p("principles", "Guiding principles", "list", "grid"),
    p("kpis", "Key performance indicators", "list", "grid"),
    p("value", "Value / outcomes", "list", "grid"),
  ];
}

interface Props {
  open: boolean;
  model: ReferenceModel | null;
  onClose: () => void;
  onSaved: (updated: ReferenceModel) => void;
}

export default function NarrativeEditor({ open, model, onClose, onSaved }: Props) {
  const { t } = useTranslation(["reports", "common"]);
  const [panels, setPanels] = useState<Panel[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && model) {
      setPanels(model.narrative?.panels ?? []);
      setError(null);
    }
  }, [open, model]);

  const update = (idx: number, patch: Partial<Panel>) =>
    setPanels((prev) => prev.map((p, i) => (i === idx ? { ...p, ...patch } : p)));

  const move = (idx: number, dir: -1 | 1) =>
    setPanels((prev) => {
      const next = [...prev];
      const j = idx + dir;
      if (j < 0 || j >= next.length) return prev;
      [next[idx], next[j]] = [next[j], next[idx]];
      return next;
    });

  const addPanel = () =>
    setPanels((prev) => [...prev, emptyPanel(`panel${Date.now().toString(36)}`)]);

  const save = async () => {
    if (!model) return;
    setSaving(true);
    setError(null);
    // Normalise list panels: split textarea lines into items.
    const payload = {
      panels: panels.map((p) => ({
        ...p,
        items: p.kind === "list" ? p.items.filter((s) => s.trim()) : [],
        items_ar: p.kind === "list" ? p.items_ar.filter((s) => s.trim()) : [],
        text: p.kind === "text" ? p.text : "",
        text_ar: p.kind === "text" ? p.text_ar : "",
      })),
    };
    try {
      const updated = await api.patch<ReferenceModel>(
        `/reference-models/${model.id}/narrative`,
        payload,
      );
      onSaved(updated);
      onClose();
    } catch (e) {
      setError(
        e instanceof ApiError && typeof e.detail === "string"
          ? e.detail
          : t("common:errors.generic"),
      );
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth disableRestoreFocus>
      <DialogTitle>
        {t("rmPoster.editTitle")}
        {model && (
          <Typography variant="body2" color="text.secondary">
            {model.name}
          </Typography>
        )}
      </DialogTitle>
      <DialogContent dividers>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
          <Button
            size="small"
            startIcon={<MaterialSymbol icon="add" size={18} />}
            onClick={addPanel}
          >
            {t("rmPoster.addPanel")}
          </Button>
          {panels.length === 0 && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<MaterialSymbol icon="auto_awesome" size={18} />}
              onClick={() => setPanels(starterPanels())}
            >
              {t("rmPoster.loadStarter")}
            </Button>
          )}
        </Box>

        {panels.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            {t("rmPoster.empty")}
          </Typography>
        )}

        <Stack spacing={1.5}>
          {panels.map((p, idx) => (
            <Paper key={idx} variant="outlined" sx={{ p: 1.5 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                <Typography variant="caption" color="text.secondary" sx={{ minWidth: 24 }}>
                  #{idx + 1}
                </Typography>
                <TextField
                  select
                  size="small"
                  label={t("rmPoster.kind")}
                  value={p.kind}
                  onChange={(e) => update(idx, { kind: e.target.value as "text" | "list" })}
                  sx={{ width: 120 }}
                >
                  <MenuItem value="text">{t("rmPoster.kindText")}</MenuItem>
                  <MenuItem value="list">{t("rmPoster.kindList")}</MenuItem>
                </TextField>
                <TextField
                  select
                  size="small"
                  label={t("rmPoster.placement")}
                  value={p.placement}
                  onChange={(e) =>
                    update(idx, { placement: e.target.value as "header" | "grid" })
                  }
                  sx={{ width: 140 }}
                >
                  <MenuItem value="header">{t("rmPoster.placementHeader")}</MenuItem>
                  <MenuItem value="grid">{t("rmPoster.placementGrid")}</MenuItem>
                </TextField>
                <Box sx={{ flex: 1 }} />
                <Tooltip title={t("rmPoster.moveUp")}>
                  <span>
                    <IconButton size="small" disabled={idx === 0} onClick={() => move(idx, -1)}>
                      <MaterialSymbol icon="arrow_upward" size={18} />
                    </IconButton>
                  </span>
                </Tooltip>
                <Tooltip title={t("rmPoster.moveDown")}>
                  <span>
                    <IconButton
                      size="small"
                      disabled={idx === panels.length - 1}
                      onClick={() => move(idx, 1)}
                    >
                      <MaterialSymbol icon="arrow_downward" size={18} />
                    </IconButton>
                  </span>
                </Tooltip>
                <IconButton
                  size="small"
                  onClick={() => setPanels((prev) => prev.filter((_, i) => i !== idx))}
                >
                  <MaterialSymbol icon="delete" size={18} />
                </IconButton>
              </Box>

              <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
                <TextField
                  size="small"
                  label={t("rmPoster.title")}
                  value={p.title}
                  onChange={(e) => update(idx, { title: e.target.value })}
                />
                <TextField
                  size="small"
                  label={t("rmPoster.titleAr")}
                  value={p.title_ar}
                  onChange={(e) => update(idx, { title_ar: e.target.value })}
                  inputProps={{ dir: "rtl" }}
                />
                {p.kind === "text" ? (
                  <>
                    <TextField
                      size="small"
                      label={t("rmPoster.text")}
                      value={p.text}
                      onChange={(e) => update(idx, { text: e.target.value })}
                      multiline
                      minRows={2}
                    />
                    <TextField
                      size="small"
                      label={t("rmPoster.textAr")}
                      value={p.text_ar}
                      onChange={(e) => update(idx, { text_ar: e.target.value })}
                      multiline
                      minRows={2}
                      inputProps={{ dir: "rtl" }}
                    />
                  </>
                ) : (
                  <>
                    <TextField
                      size="small"
                      label={t("rmPoster.itemsHint")}
                      value={p.items.join("\n")}
                      onChange={(e) => update(idx, { items: e.target.value.split("\n") })}
                      multiline
                      minRows={3}
                    />
                    <TextField
                      size="small"
                      label={t("rmPoster.itemsArHint")}
                      value={p.items_ar.join("\n")}
                      onChange={(e) => update(idx, { items_ar: e.target.value.split("\n") })}
                      multiline
                      minRows={3}
                      inputProps={{ dir: "rtl" }}
                    />
                  </>
                )}
              </Box>
            </Paper>
          ))}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:cancel")}</Button>
        <Button variant="contained" onClick={save} disabled={saving}>
          {t("common:save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
