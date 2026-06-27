import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Menu from "@mui/material/Menu";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import MaterialSymbol from "@/components/MaterialSymbol";
import ReportShell from "./ReportShell";
import ReportLegend from "./ReportLegend";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useResolveMetaLabel } from "@/hooks/useResolveLabel";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Bar {
  id: string;
  name: string;
  type: string;
  subtype?: string;
  lifecycle: Record<string, string>;
}

interface Lane {
  id: string;
  name: string;
  items: Bar[];
}

interface Milestone {
  id: string;
  label: string;
  target_date: string;
  initiative_id?: string | null;
  color?: string | null;
}

interface RoadmapData {
  group_by: string;
  card_type: string;
  lanes: Lane[];
  ungrouped: Bar[];
  milestones?: Milestone[];
  roadmap?: { id: string; name: string };
}

interface SavedRoadmap {
  id: string;
  name: string;
  config: { type?: string; group_by?: string };
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const PHASES = [
  { key: "plan", labelKey: "lifecycle.phasePlan", color: "#9e9e9e" },
  { key: "phaseIn", labelKey: "lifecycle.phasePhaseIn", color: "#2196f3" },
  { key: "active", labelKey: "lifecycle.phaseActive", color: "#4caf50" },
  { key: "phaseOut", labelKey: "lifecycle.phasePhaseOut", color: "#ff9800" },
  { key: "endOfLife", labelKey: "lifecycle.phaseEndOfLife", color: "#f44336" },
];
const PHASE_KEYS = PHASES.map((p) => p.key);
const PHASE_COLOR: Record<string, string> = Object.fromEntries(
  PHASES.map((p) => [p.key, p.color]),
);
const MS_PER_DAY = 86_400_000;

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function parseDate(s: string | undefined | null): number | null {
  if (!s) return null;
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d.getTime();
}

interface Segment {
  key: string;
  color: string;
  leftPct: number;
  widthPct: number;
}

/** Build colored phase segments for one card across the [min,max] axis. */
function buildSegments(
  lifecycle: Record<string, string>,
  axisMin: number,
  axisMax: number,
): Segment[] {
  const span = axisMax - axisMin || 1;
  const pct = (t: number) => Math.max(0, Math.min(100, ((t - axisMin) / span) * 100));
  const segments: Segment[] = [];
  for (let i = 0; i < PHASE_KEYS.length; i++) {
    const start = parseDate(lifecycle[PHASE_KEYS[i]]);
    if (!start) continue;
    const end = i < PHASE_KEYS.length - 1 ? parseDate(lifecycle[PHASE_KEYS[i + 1]]) : axisMax;
    const endTime = end || axisMax;
    segments.push({
      key: PHASE_KEYS[i],
      color: PHASE_COLOR[PHASE_KEYS[i]],
      leftPct: pct(start),
      widthPct: pct(endTime) - pct(start),
    });
  }
  return segments;
}

function buildTicks(
  axisMin: number,
  axisMax: number,
): { label: string; leftPct: number }[] {
  const span = axisMax - axisMin || 1;
  const pct = (t: number) => ((t - axisMin) / span) * 100;
  const startYear = new Date(axisMin).getFullYear();
  const endYear = new Date(axisMax).getFullYear();
  const totalQuarters = (endYear - startYear + 1) * 4;
  const ticks: { label: string; leftPct: number }[] = [];
  if (totalQuarters <= 20) {
    for (let y = startYear; y <= endYear; y++) {
      for (let q = 0; q < 4; q++) {
        const t = new Date(y, q * 3, 1).getTime();
        if (t < axisMin || t > axisMax) continue;
        ticks.push({ label: `Q${q + 1} '${String(y).slice(2)}`, leftPct: pct(t) });
      }
    }
  } else {
    for (let y = startYear; y <= endYear; y++) {
      const t = new Date(y, 0, 1).getTime();
      if (t < axisMin || t > axisMax) continue;
      ticks.push({ label: String(y), leftPct: pct(t) });
    }
  }
  return ticks;
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export default function TransformationRoadmap() {
  const { t } = useTranslation(["reports", "common"]);
  const { types } = useMetamodel();
  const rml = useResolveMetaLabel();
  const chartRef = useRef<HTMLDivElement>(null);

  const [cardTypeKey, setCardTypeKey] = useState("Application");
  const [groupByKey, setGroupByKey] = useState("BusinessCapability");
  const [data, setData] = useState<RoadmapData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Saved roadmaps (Phase 2)
  const [saved, setSaved] = useState<SavedRoadmap[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [savedMenu, setSavedMenu] = useState<HTMLElement | null>(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [msOpen, setMsOpen] = useState(false);
  const [msLabel, setMsLabel] = useState("");
  const [msDate, setMsDate] = useState("");

  const visibleTypes = useMemo(() => types.filter((tp) => !tp.is_hidden), [types]);

  const loadSavedList = useCallback(async () => {
    try {
      setSaved(await api.get<SavedRoadmap[]>("/roadmaps"));
    } catch {
      /* non-fatal */
    }
  }, []);

  useEffect(() => {
    loadSavedList();
  }, [loadSavedList]);

  // Fetch timeline whenever the scope changes (ad-hoc) or a saved roadmap loads.
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const d = currentId
        ? await api.get<RoadmapData>(`/roadmaps/${currentId}/data`)
        : await api.get<RoadmapData>("/roadmaps/data", {
            type: cardTypeKey,
            group_by: groupByKey,
          });
      setData(d);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load roadmap data",
      );
    } finally {
      setLoading(false);
    }
  }, [currentId, cardTypeKey, groupByKey]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Compute axis range from all dates in data + milestones.
  const [axisMin, axisMax] = useMemo(() => {
    const times: number[] = [];
    const collect = (b: Bar) => {
      for (const k of PHASE_KEYS) {
        const t = parseDate(b.lifecycle[k]);
        if (t != null) times.push(t);
      }
    };
    data?.lanes.forEach((l) => l.items.forEach(collect));
    data?.ungrouped.forEach(collect);
    data?.milestones?.forEach((m) => {
      const t = parseDate(m.target_date);
      if (t != null) times.push(t);
    });
    const now = Date.now();
    if (times.length === 0) {
      return [now - 365 * MS_PER_DAY, now + 3 * 365 * MS_PER_DAY];
    }
    let lo = Math.min(...times);
    let hi = Math.max(...times);
    // Cap minimum to 5 years back to avoid outlier dates dragging the axis.
    const minCap = now - 5 * 365 * MS_PER_DAY;
    lo = Math.max(lo, minCap);
    const pad = Math.max((hi - lo) * 0.05, 30 * MS_PER_DAY);
    lo -= pad;
    hi += pad;
    return [lo, hi];
  }, [data]);

  const ticks = useMemo(() => buildTicks(axisMin, axisMax), [axisMin, axisMax]);

  const milestoneMarkers = useMemo(() => {
    const span = axisMax - axisMin || 1;
    return (data?.milestones ?? [])
      .filter((m) => parseDate(m.target_date) != null)
      .map((m) => ({
        ...m,
        leftPct: ((parseDate(m.target_date)! - axisMin) / span) * 100,
      }));
  }, [data, axisMin, axisMax]);

  const typeLabel = rml(cardTypeKey, types.find((t) => t.key === cardTypeKey)?.translations, "label");
  const groupLabel =
    groupByKey === ""
      ? t("transformationRoadmap.ungrouped")
      : rml(groupByKey, types.find((t) => t.key === groupByKey)?.translations, "label");

  const handleSave = async () => {
    if (!saveName.trim()) return;
    const created = await api.post<SavedRoadmap>("/roadmaps", {
      name: saveName.trim(),
      config: { type: cardTypeKey, group_by: groupByKey },
    });
    setSaveOpen(false);
    setSaveName("");
    await loadSavedList();
    setCurrentId(created.id);
  };

  const handleLoad = (r: SavedRoadmap) => {
    setSavedMenu(null);
    setCurrentId(r.id);
    if (r.config.type) setCardTypeKey(r.config.type);
    if (r.config.group_by) setGroupByKey(r.config.group_by);
  };

  const handleNewView = () => {
    setSavedMenu(null);
    setCurrentId(null);
  };

  const handleDeleteSaved = async (id: string) => {
    await api.delete(`/roadmaps/${id}`);
    if (currentId === id) setCurrentId(null);
    await loadSavedList();
  };

  const handleAddMilestone = async () => {
    if (!currentId || !msLabel.trim() || !msDate) return;
    await api.post(`/roadmaps/${currentId}/milestones`, {
      label: msLabel.trim(),
      target_date: msDate,
    });
    setMsOpen(false);
    setMsLabel("");
    setMsDate("");
    await fetchData();
  };

  const handleDeleteMilestone = async (id: string) => {
    await api.delete(`/roadmaps/milestones/${id}`);
    await fetchData();
  };

  const laneCount = data ? data.lanes.length + (data.ungrouped.length ? 1 : 0) : 0;

  const renderLane = (name: string, items: Bar[]) => (
    <Box key={name} sx={{ mb: 3, pb: 2, borderBottom: "1px solid", borderColor: "divider" }}>
      {/* Lane title */}
      <Typography sx={{ fontSize: 14, fontWeight: 700, mb: 1.5, color: "primary.main" }}>
        {name}
      </Typography>

      {/* Cards in lane */}
      {items.map((b) => {
        const segs = buildSegments(b.lifecycle, axisMin, axisMax);
        const cardType = types.find((t) => t.key === b.type);
        return (
          <Box
            key={b.id}
            sx={{
              display: "grid",
              gridTemplateColumns: "240px 1fr",
              alignItems: "center",
              mb: 1.5,
              gap: 2,
            }}
          >
            {/* Card label with type chip */}
            <Box sx={{ minWidth: 0 }}>
              <Tooltip title={`${b.name} (${b.type})`}>
                <Typography
                  sx={{
                    fontSize: 13,
                    fontWeight: 600,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    mb: 0.5,
                  }}
                >
                  {b.name}
                </Typography>
              </Tooltip>
              <Chip
                size="small"
                label={rml(b.type, cardType?.translations, "label")}
                variant="outlined"
                sx={{ height: 22, fontSize: 11 }}
              />
            </Box>

            {/* Timeline bar */}
            <Box sx={{ position: "relative", height: 32, bgcolor: "background.paper", borderRadius: 1, border: "1px solid", borderColor: "divider" }}>
              {segs.length === 0 ? (
                <Typography sx={{ fontSize: 11, color: "text.secondary", p: 0.5 }}>
                  No lifecycle data
                </Typography>
              ) : (
                segs.map((s, i) => (
                  <Tooltip
                    key={i}
                    title={`${t(
                      PHASES.find((p) => p.key === s.key)?.labelKey ?? s.key,
                    )}`}
                    arrow
                  >
                    <Box
                      sx={{
                        position: "absolute",
                        left: `${s.leftPct}%`,
                        width: `${Math.max(s.widthPct, 2)}%`,
                        top: 4,
                        height: 24,
                        bgcolor: s.color,
                        borderRadius: "2px",
                        cursor: "pointer",
                        transition: "opacity 0.2s",
                        "&:hover": { opacity: 0.8 },
                      }}
                    />
                  </Tooltip>
                ))
              )}

              {/* Milestone markers on this card */}
              {milestoneMarkers.map((m) => (
                <Tooltip
                  key={m.id}
                  title={`${m.label} — ${new Date(m.target_date).toLocaleDateString()}`}
                  arrow
                >
                  <Box
                    sx={{
                      position: "absolute",
                      left: `${m.leftPct}%`,
                      top: 0,
                      bottom: 0,
                      width: 2,
                      bgcolor: m.color || "warning.main",
                      transform: "translateX(-50%)",
                      cursor: "pointer",
                    }}
                  />
                </Tooltip>
              ))}
            </Box>
          </Box>
        );
      })}
    </Box>
  );

  return (
    <ReportShell
      title={t("reports:transformationRoadmap.title")}
      printParams={[
        { label: t("transformationRoadmap.cardType"), value: typeLabel },
        { label: t("transformationRoadmap.groupBy"), value: groupLabel },
      ]}
      actions={
        <>
          <Button
            size="small"
            startIcon={<MaterialSymbol icon="bookmarks" size={18} />}
            onClick={(e) => setSavedMenu(e.currentTarget)}
            sx={{ textTransform: "none" }}
          >
            {t("transformationRoadmap.saved")}
          </Button>
          <Menu anchorEl={savedMenu} open={!!savedMenu} onClose={() => setSavedMenu(null)}>
            <MenuItem onClick={handleNewView}>{t("transformationRoadmap.newView")}</MenuItem>
            <MenuItem onClick={() => { setSavedMenu(null); setSaveOpen(true); }}>
              {t("transformationRoadmap.saveCurrent")}
            </MenuItem>
            {saved.length > 0 && <Box sx={{ borderTop: "1px solid", borderColor: "divider", my: 0.5 }} />}
            {saved.map((r) => (
              <MenuItem key={r.id} onClick={() => handleLoad(r)} sx={{ display: "flex", gap: 1 }}>
                <Box sx={{ flex: 1 }}>{r.name}</Box>
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); handleDeleteSaved(r.id); }}
                >
                  <MaterialSymbol icon="delete" size={16} />
                </IconButton>
              </MenuItem>
            ))}
          </Menu>
        </>
      }
      toolbar={
        <>
          <TextField
            select
            size="small"
            label={t("transformationRoadmap.cardType")}
            value={cardTypeKey}
            onChange={(e) => { setCurrentId(null); setCardTypeKey(e.target.value); }}
            sx={{ minWidth: 180 }}
          >
            {visibleTypes.map((tp) => (
              <MenuItem key={tp.key} value={tp.key}>{rml(tp.key, tp.translations, "label")}</MenuItem>
            ))}
          </TextField>
          <TextField
            select
            size="small"
            label={t("transformationRoadmap.groupBy")}
            value={groupByKey}
            onChange={(e) => { setCurrentId(null); setGroupByKey(e.target.value); }}
            sx={{ minWidth: 180 }}
          >
            <MenuItem value="">— {t("transformationRoadmap.ungrouped")} —</MenuItem>
            {visibleTypes.map((tp) => (
              <MenuItem key={tp.key} value={tp.key}>{rml(tp.key, tp.translations, "label")}</MenuItem>
            ))}
          </TextField>
          {currentId && (
            <Button
              size="small"
              startIcon={<MaterialSymbol icon="flag" size={18} />}
              onClick={() => setMsOpen(true)}
              sx={{ textTransform: "none" }}
            >
              {t("transformationRoadmap.addMilestone")}
            </Button>
          )}
        </>
      }
      legend={
        <ReportLegend
          items={PHASES.map((p) => ({ label: t(p.labelKey), color: p.color }))}
        />
      }
    >
      {/* Description */}
      <Box sx={{ mb: 3, p: 2, bgcolor: "info.lighter", borderRadius: 1, borderLeft: "4px solid", borderLeftColor: "info.main" }}>
        <Typography variant="body2" sx={{ color: "text.primary" }}>
          <strong>How to read this chart:</strong> Each row shows one {typeLabel.toLowerCase()} grouped by {groupLabel.toLowerCase()}. Colored bars represent when each card is planned (gray), phasing in (blue), actively used (green), phasing out (orange), or end-of-life (red). Vertical lines mark important milestones.
        </Typography>
      </Box>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : !data || laneCount === 0 ? (
        <Alert severity="info">
          {t("transformationRoadmap.empty")}
        </Alert>
      ) : (
        <Box ref={chartRef} sx={{ position: "relative" }}>
          {/* Time axis header */}
          <Box sx={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: 2, mb: 2 }}>
            <Box />
            <Box sx={{ position: "relative", height: 28, borderBottom: "2px solid", borderColor: "primary.main", pb: 1 }}>
              {ticks.map((tk, i) => (
                <Typography
                  key={i}
                  sx={{
                    position: "absolute",
                    left: `${tk.leftPct}%`,
                    fontSize: 12,
                    fontWeight: 600,
                    color: "primary.main",
                    transform: "translateX(-50%)",
                  }}
                >
                  {tk.label}
                </Typography>
              ))}
            </Box>
          </Box>

          {/* Render all lanes */}
          {data.lanes.map((lane) => renderLane(lane.name, lane.items))}

          {/* Ungrouped items */}
          {data.ungrouped.length > 0 && renderLane(t("transformationRoadmap.ungrouped"), data.ungrouped)}
        </Box>
      )}

      {/* Save dialog */}
      <Dialog open={saveOpen} onClose={() => setSaveOpen(false)}>
        <DialogTitle>{t("transformationRoadmap.saveCurrent")}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label={t("transformationRoadmap.name")}
            type="text"
            fullWidth
            variant="outlined"
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button onClick={handleSave} variant="contained">
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Milestone dialog */}
      <Dialog open={msOpen} onClose={() => setMsOpen(false)}>
        <DialogTitle>{t("transformationRoadmap.addMilestone")}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label={t("transformationRoadmap.milestoneLabel")}
            type="text"
            fullWidth
            variant="outlined"
            value={msLabel}
            onChange={(e) => setMsLabel(e.target.value)}
            sx={{ mt: 1, mb: 2 }}
          />
          <TextField
            margin="dense"
            label={t("transformationRoadmap.milestoneDate")}
            type="date"
            fullWidth
            variant="outlined"
            value={msDate}
            onChange={(e) => setMsDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMsOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button onClick={handleAddMilestone} variant="contained">
            {t("common:actions.add")}
          </Button>
        </DialogActions>
      </Dialog>
    </ReportShell>
  );
}
