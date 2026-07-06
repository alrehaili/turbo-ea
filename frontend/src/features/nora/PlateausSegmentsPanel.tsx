/**
 * NORA plateaus (time-slices) + segment scopes panel — WP5.4.
 *
 * Embedded on the NORA Program page. Segments are card-rooted cross-entity
 * filter scopes resolved to their in-scope cards grouped by EA layer; plateaus
 * are named target dates whose "time-slice" reclassifies the landscape's
 * lifecycle phases as of that date.
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CardPicker, { type CardOption } from "@/components/CardPicker";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { useMetamodel } from "@/hooks/useMetamodel";
import { LAYER_COLORS } from "@/theme/tokens";

interface Segment {
  id: string;
  name: string;
  description: string | null;
  root_card_id: string | null;
  include_descendants: boolean;
  include_related: boolean;
  related_type_keys: string[];
  color: string | null;
}

interface Plateau {
  id: string;
  name: string;
  description: string | null;
  target_date: string | null;
}

interface LayerGroup {
  category: string;
  cards: { id: string; name: string; type: string; category: string | null }[];
}

const PHASE_KEYS = ["plan", "phaseIn", "active", "phaseOut", "endOfLife", "unknown"] as const;

export default function PlateausSegmentsPanel({ canManage }: { canManage: boolean }) {
  const { t } = useTranslation(["nav", "common"]);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [plateaus, setPlateaus] = useState<Plateau[]>([]);
  const [editSeg, setEditSeg] = useState<Segment | null>(null);
  const [scopeSeg, setScopeSeg] = useState<Segment | null>(null);
  const [editPlateau, setEditPlateau] = useState<Plateau | null>(null);
  const [slicePlateau, setSlicePlateau] = useState<Plateau | null>(null);

  const load = useCallback(async () => {
    const [segs, plats] = await Promise.all([
      api.get<Segment[]>("/nora-segments"),
      api.get<Plateau[]>("/nora-plateaus"),
    ]);
    setSegments(segs);
    setPlateaus(plats);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Paper sx={{ p: 2, mt: 3 }}>
      <Typography variant="subtitle1" fontWeight={600}>
        <MaterialSymbol
          icon="dashboard"
          size={20}
          style={{ verticalAlign: "middle", marginInlineEnd: 6 }}
        />
        {t("noraProgram.landscape.title")}
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={1}>
        {t("noraProgram.landscape.subtitle")}
      </Typography>

      <Grid container spacing={2}>
        {/* Segments */}
        <Grid item xs={12} md={6}>
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Typography variant="subtitle2">{t("noraProgram.landscape.segments")}</Typography>
            {canManage && (
              <Button
                size="small"
                startIcon={<MaterialSymbol icon="add" />}
                onClick={() =>
                  setEditSeg({
                    id: "",
                    name: "",
                    description: null,
                    root_card_id: null,
                    include_descendants: true,
                    include_related: true,
                    related_type_keys: [],
                    color: null,
                  })
                }
              >
                {t("common:actions.add")}
              </Button>
            )}
          </Stack>
          {segments.length ? (
            segments.map((s) => (
              <Stack
                key={s.id}
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                sx={{ py: 0.5, borderBottom: "1px solid", borderColor: "divider" }}
              >
                <Typography variant="body2">{s.name}</Typography>
                <Box>
                  <Tooltip title={t("noraProgram.landscape.viewScope")}>
                    <IconButton size="small" onClick={() => setScopeSeg(s)}>
                      <MaterialSymbol icon="account_tree" />
                    </IconButton>
                  </Tooltip>
                  {canManage && (
                    <>
                      <IconButton size="small" onClick={() => setEditSeg(s)}>
                        <MaterialSymbol icon="edit" />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={async () => {
                          await api.delete(`/nora-segments/${s.id}`);
                          await load();
                        }}
                      >
                        <MaterialSymbol icon="delete" />
                      </IconButton>
                    </>
                  )}
                </Box>
              </Stack>
            ))
          ) : (
            <Typography variant="body2" color="text.secondary">
              {t("noraProgram.landscape.noSegments")}
            </Typography>
          )}
        </Grid>

        {/* Plateaus */}
        <Grid item xs={12} md={6}>
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Typography variant="subtitle2">{t("noraProgram.landscape.plateaus")}</Typography>
            {canManage && (
              <Button
                size="small"
                startIcon={<MaterialSymbol icon="add" />}
                onClick={() =>
                  setEditPlateau({ id: "", name: "", description: null, target_date: null })
                }
              >
                {t("common:actions.add")}
              </Button>
            )}
          </Stack>
          {plateaus.length ? (
            plateaus.map((p) => (
              <Stack
                key={p.id}
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                sx={{ py: 0.5, borderBottom: "1px solid", borderColor: "divider" }}
              >
                <Typography variant="body2">
                  {p.name}
                  {p.target_date ? ` · ${p.target_date}` : ""}
                </Typography>
                <Box>
                  {p.target_date && (
                    <Tooltip title={t("noraProgram.landscape.timeSlice")}>
                      <IconButton size="small" onClick={() => setSlicePlateau(p)}>
                        <MaterialSymbol icon="timeline" />
                      </IconButton>
                    </Tooltip>
                  )}
                  {canManage && (
                    <>
                      <IconButton size="small" onClick={() => setEditPlateau(p)}>
                        <MaterialSymbol icon="edit" />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={async () => {
                          await api.delete(`/nora-plateaus/${p.id}`);
                          await load();
                        }}
                      >
                        <MaterialSymbol icon="delete" />
                      </IconButton>
                    </>
                  )}
                </Box>
              </Stack>
            ))
          ) : (
            <Typography variant="body2" color="text.secondary">
              {t("noraProgram.landscape.noPlateaus")}
            </Typography>
          )}
        </Grid>
      </Grid>

      {editSeg && (
        <SegmentDialog
          segment={editSeg}
          onClose={() => setEditSeg(null)}
          onSaved={async () => {
            setEditSeg(null);
            await load();
          }}
        />
      )}
      {scopeSeg && <ScopeDialog segment={scopeSeg} onClose={() => setScopeSeg(null)} />}
      {editPlateau && (
        <PlateauDialog
          plateau={editPlateau}
          onClose={() => setEditPlateau(null)}
          onSaved={async () => {
            setEditPlateau(null);
            await load();
          }}
        />
      )}
      {slicePlateau && (
        <TimeSliceDialog plateau={slicePlateau} onClose={() => setSlicePlateau(null)} />
      )}
    </Paper>
  );
}

function SegmentDialog({
  segment,
  onClose,
  onSaved,
}: {
  segment: Segment;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { t } = useTranslation(["nav", "common"]);
  const { types } = useMetamodel();
  const [name, setName] = useState(segment.name);
  const [root, setRoot] = useState<CardOption | null>(
    segment.root_card_id ? { id: segment.root_card_id, name: segment.name, type: "" } : null,
  );
  const [descendants, setDescendants] = useState(segment.include_descendants);
  const [related, setRelated] = useState(segment.include_related);
  const [relatedTypes, setRelatedTypes] = useState<string[]>(segment.related_type_keys);

  const save = async () => {
    const body = {
      name: name.trim(),
      root_card_id: root?.id ?? null,
      include_descendants: descendants,
      include_related: related,
      related_type_keys: relatedTypes,
    };
    if (segment.id) await api.patch(`/nora-segments/${segment.id}`, body);
    else await api.post("/nora-segments", body);
    onSaved();
  };

  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t("noraProgram.landscape.segment")}</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        <TextField
          autoFocus
          label={t("noraProgram.landscape.name")}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <CardPicker
          value={root}
          onChange={setRoot}
          label={t("noraProgram.landscape.rootCard")}
          enabled
        />
        <FormControlLabel
          control={
            <Switch checked={descendants} onChange={(e) => setDescendants(e.target.checked)} />
          }
          label={t("noraProgram.landscape.includeDescendants")}
        />
        <FormControlLabel
          control={<Switch checked={related} onChange={(e) => setRelated(e.target.checked)} />}
          label={t("noraProgram.landscape.includeRelated")}
        />
        <TextField
          select
          disabled={!related}
          SelectProps={{ multiple: true }}
          label={t("noraProgram.landscape.relatedTypes")}
          helperText={t("noraProgram.landscape.relatedTypesHint")}
          value={relatedTypes}
          onChange={(e) =>
            setRelatedTypes(
              typeof e.target.value === "string" ? e.target.value.split(",") : e.target.value,
            )
          }
        >
          {types.map((ty) => (
            <MenuItem key={ty.key} value={ty.key}>
              {ty.label || ty.key}
            </MenuItem>
          ))}
        </TextField>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:actions.cancel")}</Button>
        <Button variant="contained" disabled={!name.trim() || !root} onClick={() => void save()}>
          {t("common:actions.save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function ScopeDialog({ segment, onClose }: { segment: Segment; onClose: () => void }) {
  const { t } = useTranslation(["nav", "common"]);
  const [layers, setLayers] = useState<LayerGroup[] | null>(null);
  const [count, setCount] = useState(0);

  useEffect(() => {
    void (async () => {
      const res = await api.get<{ layers: LayerGroup[]; count: number }>(
        `/nora-segments/${segment.id}/cards`,
      );
      setLayers(res.layers);
      setCount(res.count);
    })();
  }, [segment.id]);

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        {segment.name} · {t("noraProgram.landscape.cardsInScope", { n: count })}
      </DialogTitle>
      <DialogContent dividers>
        {layers === null ? (
          <Typography variant="body2">{t("common:loading", { defaultValue: "Loading…" })}</Typography>
        ) : layers.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {t("noraProgram.landscape.emptyScope")}
          </Typography>
        ) : (
          layers.map((layer) => (
            <Box key={layer.category} sx={{ mb: 2 }}>
              <Typography
                variant="subtitle2"
                sx={{
                  color:
                    LAYER_COLORS[layer.category as keyof typeof LAYER_COLORS] ?? "text.primary",
                }}
              >
                {layer.category}
              </Typography>
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
                {layer.cards.map((c) => (
                  <Chip
                    key={c.id}
                    size="small"
                    label={c.name}
                    component="a"
                    href={`/cards/${c.id}`}
                    clickable
                  />
                ))}
              </Stack>
            </Box>
          ))
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:actions.close")}</Button>
      </DialogActions>
    </Dialog>
  );
}

function PlateauDialog({
  plateau,
  onClose,
  onSaved,
}: {
  plateau: Plateau;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { t } = useTranslation(["nav", "common"]);
  const [name, setName] = useState(plateau.name);
  const [targetDate, setTargetDate] = useState(plateau.target_date ?? "");

  const save = async () => {
    const body = { name: name.trim(), target_date: targetDate || null };
    if (plateau.id) await api.patch(`/nora-plateaus/${plateau.id}`, body);
    else await api.post("/nora-plateaus", body);
    onSaved();
  };

  return (
    <Dialog open onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{t("noraProgram.landscape.plateau")}</DialogTitle>
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
        <TextField
          autoFocus
          label={t("noraProgram.landscape.name")}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <TextField
          type="date"
          label={t("noraProgram.landscape.targetDate")}
          InputLabelProps={{ shrink: true }}
          value={targetDate}
          onChange={(e) => setTargetDate(e.target.value)}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:actions.cancel")}</Button>
        <Button variant="contained" disabled={!name.trim()} onClick={() => void save()}>
          {t("common:actions.save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function TimeSliceDialog({ plateau, onClose }: { plateau: Plateau; onClose: () => void }) {
  const { t } = useTranslation(["nav", "common"]);
  const [data, setData] = useState<{
    total: number;
    phases: Record<string, number>;
    states: Record<string, number>;
  } | null>(null);

  useEffect(() => {
    void (async () => {
      setData(await api.get(`/nora-plateaus/${plateau.id}/landscape`));
    })();
  }, [plateau.id]);

  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {plateau.name} · {plateau.target_date}
      </DialogTitle>
      <DialogContent dividers>
        {!data ? (
          <Typography variant="body2">{t("common:loading", { defaultValue: "Loading…" })}</Typography>
        ) : (
          <>
            <Typography variant="subtitle2">
              {t("noraProgram.landscape.lifecyclePhases")} ({t("noraProgram.landscape.total")}:{" "}
              {data.total})
            </Typography>
            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ my: 1 }}>
              {PHASE_KEYS.map((ph) => (
                <Chip
                  key={ph}
                  size="small"
                  label={`${t(`noraProgram.landscape.phase.${ph}`)}: ${data.phases[ph] ?? 0}`}
                />
              ))}
            </Stack>
            <Divider sx={{ my: 1 }} />
            <Typography variant="subtitle2">
              {t("noraProgram.landscape.architectureState")}
            </Typography>
            <Stack direction="row" spacing={0.5} sx={{ mt: 1 }}>
              <Chip size="small" label={`${t("noraProgram.landscape.stateCurrent")}: ${data.states.current ?? 0}`} />
              <Chip size="small" label={`${t("noraProgram.landscape.stateTransition")}: ${data.states.transition ?? 0}`} />
              <Chip size="small" label={`${t("noraProgram.landscape.stateTarget")}: ${data.states.target ?? 0}`} />
            </Stack>
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:actions.close")}</Button>
      </DialogActions>
    </Dialog>
  );
}
