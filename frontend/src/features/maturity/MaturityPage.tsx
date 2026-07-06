/**
 * EA maturity self-assessment (Qiyas-style) — NORA WP5.2.
 *
 * A dated self-assessment across admin-definable EA maturity dimensions on a
 * fixed 1–5 scale, with a radar (latest, level vs target), a trend line across
 * assessments, per-dimension gap promotion into the Improvement Opportunity
 * registry, and a dimension-catalogue manager.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
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
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import {
  CartesianGrid,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts";
import MaterialSymbol from "@/components/MaterialSymbol";
import { hasPermission } from "@/components/RequirePermission";
import { api } from "@/api/client";
import { useAuthContext } from "@/hooks/AuthContext";
import { useIsRtl } from "@/hooks/useIsRtl";
import { STATUS_COLORS } from "@/theme/tokens";
import type {
  MaturityAssessment,
  MaturityDimension,
  MaturityDimensionScore,
  MaturityOverview,
} from "@/types";

const MAX_LEVEL = 5;
const LEVELS = [0, 1, 2, 3, 4, 5];

function statusColor(status: string): string {
  if (status === "approved") return STATUS_COLORS.success;
  if (status === "submitted") return STATUS_COLORS.info;
  return STATUS_COLORS.neutral;
}

export default function MaturityPage() {
  const { t } = useTranslation(["reports", "common"]);
  const { user } = useAuthContext();
  const canManage = hasPermission(user?.permissions, "maturity.manage");
  const isRtl = useIsRtl();

  const [overview, setOverview] = useState<MaturityOverview | null>(null);
  const [assessments, setAssessments] = useState<MaturityAssessment[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [openAssessment, setOpenAssessment] = useState<MaturityAssessment | null>(null);
  const [showDimensions, setShowDimensions] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  const levelLabel = useCallback(
    (n: number) => t(`maturity.level.${n}`, { defaultValue: String(n) }),
    [t],
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, list] = await Promise.all([
        api.get<MaturityOverview>("/maturity/overview"),
        api.get<MaturityAssessment[]>("/maturity/assessments"),
      ]);
      setOverview(ov);
      setAssessments(list);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const radarData = useMemo(
    () =>
      (overview?.radar ?? []).map((r) => ({
        dimension: r.dimension_name,
        level: r.level,
        target: r.target_level,
      })),
    [overview],
  );

  const trendData = useMemo(
    () =>
      (overview?.trend ?? []).map((tr) => ({
        date: tr.date ?? "",
        score: tr.overall_score ?? 0,
        title: tr.title,
      })),
    [overview],
  );

  const createAssessment = async () => {
    if (!newTitle.trim()) return;
    const created = await api.post<MaturityAssessment>("/maturity/assessments", {
      title: newTitle.trim(),
    });
    setCreateOpen(false);
    setNewTitle("");
    await load();
    setOpenAssessment(created);
  };

  const deleteAssessment = async (id: string) => {
    await api.delete(`/maturity/assessments/${id}`);
    await load();
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const summary = overview?.summary;

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={2}>
        <Box>
          <Typography variant="h5" fontWeight={700}>
            <MaterialSymbol icon="radar" style={{ verticalAlign: "middle", marginInlineEnd: 6 }} />
            {t("maturity.title")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("maturity.subtitle")}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          {canManage && (
            <Button
              variant="outlined"
              startIcon={<MaterialSymbol icon="tune" />}
              onClick={() => setShowDimensions(true)}
            >
              {t("maturity.manageDimensions")}
            </Button>
          )}
          {canManage && (
            <Button
              variant="contained"
              startIcon={<MaterialSymbol icon="add" />}
              onClick={() => setCreateOpen(true)}
            >
              {t("maturity.newAssessment")}
            </Button>
          )}
        </Stack>
      </Stack>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* KPI tiles */}
      <Grid container spacing={2} mb={2}>
        <MetricTile
          label={t("maturity.overallScore")}
          value={summary?.overall_score != null ? `${summary.overall_score}%` : "—"}
          icon="speed"
        />
        <MetricTile
          label={t("maturity.dimensionsCount")}
          value={String(summary?.dimensions ?? 0)}
          icon="category"
        />
        <MetricTile
          label={t("maturity.belowTarget")}
          value={String(summary?.below_target ?? 0)}
          icon="trending_down"
          alert={(summary?.below_target ?? 0) > 0}
        />
        <MetricTile
          label={t("maturity.assessmentsCount")}
          value={String(summary?.assessments ?? 0)}
          icon="history"
        />
      </Grid>

      <Grid container spacing={2}>
        {/* Radar */}
        <Grid item xs={12} md={7}>
          <Paper sx={{ p: 2, height: 380 }}>
            <Typography variant="subtitle1" fontWeight={600} mb={1}>
              {t("maturity.radarTitle")}
            </Typography>
            {radarData.length ? (
              <ResponsiveContainer width="100%" height={310}>
                <RadarChart data={radarData} outerRadius="72%">
                  <PolarGrid />
                  <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 10 }} />
                  <PolarRadiusAxis domain={[0, MAX_LEVEL]} tickCount={MAX_LEVEL + 1} />
                  <Radar
                    name={t("maturity.target")}
                    dataKey="target"
                    stroke={STATUS_COLORS.neutral}
                    fill={STATUS_COLORS.neutral}
                    fillOpacity={0.15}
                  />
                  <Radar
                    name={t("maturity.current")}
                    dataKey="level"
                    stroke={STATUS_COLORS.info}
                    fill={STATUS_COLORS.info}
                    fillOpacity={0.4}
                  />
                  <RTooltip />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyHint text={t("maturity.noData")} />
            )}
          </Paper>
        </Grid>

        {/* Trend */}
        <Grid item xs={12} md={5}>
          <Paper sx={{ p: 2, height: 380 }}>
            <Typography variant="subtitle1" fontWeight={600} mb={1}>
              {t("maturity.trendTitle")}
            </Typography>
            {trendData.length ? (
              <ResponsiveContainer width="100%" height={310}>
                <LineChart data={trendData} margin={{ top: 8, right: 16, bottom: 8, left: -16 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} reversed={isRtl} />
                  <YAxis domain={[0, 100]} orientation={isRtl ? "right" : "left"} />
                  <RTooltip />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke={STATUS_COLORS.success}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyHint text={t("maturity.noTrend")} />
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Assessments list */}
      <Paper sx={{ p: 2, mt: 2 }}>
        <Typography variant="subtitle1" fontWeight={600} mb={1}>
          {t("maturity.assessments")}
        </Typography>
        {assessments.length ? (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t("maturity.colTitle")}</TableCell>
                <TableCell>{t("maturity.colDate")}</TableCell>
                <TableCell>{t("maturity.colStatus")}</TableCell>
                <TableCell align="right">{t("maturity.colScore")}</TableCell>
                <TableCell align="right" />
              </TableRow>
            </TableHead>
            <TableBody>
              {assessments.map((a) => (
                <TableRow key={a.id} hover sx={{ cursor: "pointer" }}>
                  <TableCell onClick={() => setOpenAssessment(a)}>{a.title}</TableCell>
                  <TableCell onClick={() => setOpenAssessment(a)}>
                    {a.assessment_date ?? "—"}
                  </TableCell>
                  <TableCell onClick={() => setOpenAssessment(a)}>
                    <Chip
                      size="small"
                      label={t(`maturity.status.${a.status}`)}
                      sx={{ bgcolor: statusColor(a.status), color: "#fff" }}
                    />
                  </TableCell>
                  <TableCell align="right" onClick={() => setOpenAssessment(a)}>
                    {a.overall_score != null ? `${a.overall_score}%` : "—"}
                  </TableCell>
                  <TableCell align="right">
                    {canManage && (
                      <Tooltip title={t("common:actions.delete", { defaultValue: "Delete" })}>
                        <IconButton size="small" onClick={() => void deleteAssessment(a.id)}>
                          <MaterialSymbol icon="delete" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyHint text={t("maturity.noAssessments")} />
        )}
      </Paper>

      {openAssessment && (
        <AssessmentDialog
          assessmentId={openAssessment.id}
          canManage={canManage}
          canPromote={hasPermission(user?.permissions, "grc.manage")}
          levelLabel={levelLabel}
          onClose={() => {
            setOpenAssessment(null);
            void load();
          }}
        />
      )}

      {showDimensions && (
        <DimensionsDialog canManage={canManage} onClose={() => setShowDimensions(false)} />
      )}

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{t("maturity.newAssessment")}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            margin="dense"
            label={t("maturity.colTitle")}
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={() => void createAssessment()}>
            {t("common:actions.create")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

function MetricTile({
  label,
  value,
  icon,
  alert,
}: {
  label: string;
  value: string;
  icon: string;
  alert?: boolean;
}) {
  return (
    <Grid item xs={6} md={3}>
      <Card sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
        <MaterialSymbol
          icon={icon}
          size={32}
          color={alert ? STATUS_COLORS.warning : STATUS_COLORS.info}
        />
        <Box>
          <Typography variant="h6" fontWeight={700} lineHeight={1.1}>
            {value}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {label}
          </Typography>
        </Box>
      </Card>
    </Grid>
  );
}

function EmptyHint({ text }: { text: string }) {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: 260 }}>
      <Typography variant="body2" color="text.secondary">
        {text}
      </Typography>
    </Box>
  );
}

// --------------------------------------------------------------------------- //
// Assessment scoring dialog
// --------------------------------------------------------------------------- //
function AssessmentDialog({
  assessmentId,
  canManage,
  canPromote,
  levelLabel,
  onClose,
}: {
  assessmentId: string;
  canManage: boolean;
  canPromote: boolean;
  levelLabel: (n: number) => string;
  onClose: () => void;
}) {
  const { t } = useTranslation(["reports", "common"]);
  const [assessment, setAssessment] = useState<MaturityAssessment | null>(null);
  const [busy, setBusy] = useState(false);
  const [promoted, setPromoted] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    setAssessment(await api.get<MaturityAssessment>(`/maturity/assessments/${assessmentId}`));
  }, [assessmentId]);

  useEffect(() => {
    void load();
  }, [load]);

  const patchScore = async (score: MaturityDimensionScore, patch: Partial<MaturityDimensionScore>) => {
    await api.patch(`/maturity/assessments/${assessmentId}/scores/${score.id}`, patch);
    await load();
  };

  const setStatus = async (status: string) => {
    setBusy(true);
    try {
      await api.patch(`/maturity/assessments/${assessmentId}`, { status });
      await load();
    } finally {
      setBusy(false);
    }
  };

  const promote = async (score: MaturityDimensionScore) => {
    await api.post(`/maturity/assessments/${assessmentId}/scores/${score.id}/promote-opportunity`, {
      domain: "BA",
      priority: "medium",
    });
    setPromoted((p) => ({ ...p, [score.id]: true }));
  };

  const editable = canManage && assessment?.status !== "approved";

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <span>{assessment?.title ?? t("maturity.assessments")}</span>
          {assessment && (
            <Chip
              size="small"
              label={t(`maturity.status.${assessment.status}`)}
              sx={{ bgcolor: statusColor(assessment.status), color: "#fff" }}
            />
          )}
        </Stack>
      </DialogTitle>
      <DialogContent dividers>
        {!assessment ? (
          <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t("maturity.dimension")}</TableCell>
                <TableCell sx={{ width: 160 }}>{t("maturity.current")}</TableCell>
                <TableCell sx={{ width: 120 }}>{t("maturity.target")}</TableCell>
                <TableCell align="right" />
              </TableRow>
            </TableHead>
            <TableBody>
              {(assessment.scores ?? []).map((s) => {
                const gap = (s.target_level || 0) - (s.level || 0);
                return (
                  <TableRow key={s.id}>
                    <TableCell>
                      <Typography variant="body2">{s.dimension_name}</Typography>
                    </TableCell>
                    <TableCell>
                      <TextField
                        select
                        size="small"
                        fullWidth
                        disabled={!editable}
                        value={s.level}
                        onChange={(e) => void patchScore(s, { level: Number(e.target.value) })}
                      >
                        {LEVELS.map((n) => (
                          <MenuItem key={n} value={n}>
                            {n} · {levelLabel(n)}
                          </MenuItem>
                        ))}
                      </TextField>
                    </TableCell>
                    <TableCell>
                      <TextField
                        select
                        size="small"
                        fullWidth
                        disabled={!editable}
                        value={s.target_level}
                        onChange={(e) =>
                          void patchScore(s, { target_level: Number(e.target.value) })
                        }
                      >
                        {LEVELS.map((n) => (
                          <MenuItem key={n} value={n}>
                            {n}
                          </MenuItem>
                        ))}
                      </TextField>
                    </TableCell>
                    <TableCell align="right">
                      {gap > 0 && canPromote && (
                        <Tooltip title={t("maturity.promoteHint")}>
                          <span>
                            <Button
                              size="small"
                              disabled={promoted[s.id]}
                              startIcon={<MaterialSymbol icon="lightbulb" />}
                              onClick={() => void promote(s)}
                            >
                              {promoted[s.id]
                                ? t("maturity.promoted")
                                : t("maturity.promote")}
                            </Button>
                          </span>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("common:actions.close")}</Button>
        {assessment && canManage && assessment.status === "draft" && (
          <Button variant="contained" disabled={busy} onClick={() => void setStatus("submitted")}>
            {t("maturity.submit")}
          </Button>
        )}
        {assessment && canManage && assessment.status === "submitted" && (
          <>
            <Button disabled={busy} onClick={() => void setStatus("draft")}>
              {t("maturity.reopen")}
            </Button>
            <Button
              variant="contained"
              color="success"
              disabled={busy}
              onClick={() => void setStatus("approved")}
            >
              {t("maturity.approve")}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
}

// --------------------------------------------------------------------------- //
// Dimension catalogue manager
// --------------------------------------------------------------------------- //
function DimensionsDialog({
  canManage,
  onClose,
}: {
  canManage: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation(["reports", "common"]);
  const [dims, setDims] = useState<MaturityDimension[]>([]);
  const [newName, setNewName] = useState("");

  const load = useCallback(async () => {
    setDims(await api.get<MaturityDimension[]>("/maturity/dimensions?include_inactive=true"));
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const add = async () => {
    if (!newName.trim()) return;
    await api.post("/maturity/dimensions", { name: newName.trim() });
    setNewName("");
    await load();
  };

  const toggleActive = async (d: MaturityDimension) => {
    await api.patch(`/maturity/dimensions/${d.id}`, { is_active: !d.is_active });
    await load();
  };

  const remove = async (d: MaturityDimension) => {
    await api.delete(`/maturity/dimensions/${d.id}`);
    await load();
  };

  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{t("maturity.manageDimensions")}</DialogTitle>
      <DialogContent dividers>
        <Table size="small">
          <TableBody>
            {dims.map((d) => (
              <TableRow key={d.id}>
                <TableCell>
                  <Typography variant="body2" sx={{ opacity: d.is_active ? 1 : 0.5 }}>
                    {d.name}
                    {!d.built_in && (
                      <Chip label={t("maturity.custom")} size="small" sx={{ ml: 1 }} />
                    )}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  {canManage && (
                    <FormControlLabel
                      control={
                        <Switch
                          size="small"
                          checked={d.is_active}
                          onChange={() => void toggleActive(d)}
                        />
                      }
                      label={t("maturity.active")}
                    />
                  )}
                  {canManage && !d.built_in && (
                    <IconButton size="small" onClick={() => void remove(d)}>
                      <MaterialSymbol icon="delete" />
                    </IconButton>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {canManage && (
          <>
            <Divider sx={{ my: 2 }} />
            <Stack direction="row" spacing={1}>
              <TextField
                size="small"
                fullWidth
                label={t("maturity.newDimension")}
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
              <Button variant="contained" onClick={() => void add()}>
                {t("common:actions.add")}
              </Button>
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
