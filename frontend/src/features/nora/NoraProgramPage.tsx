/**
 * NoraProgramPage — the NORA EA Program tracker: ten methodology stages plus
 * continuous governance, each with its deliverables, evidence links and
 * stage-gate approval state. Features an executive dashboard aggregating
 * stage readiness, approval coverage, gaps, and improvement opportunities.
 *
 * [FORK FEATURE] — noraPlan.md WP3.1 + deferred executive dashboard.
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardActionArea from "@mui/material/CardActionArea";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
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
import Menu from "@mui/material/Menu";
import { useNavigate } from "react-router-dom";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api, ApiError } from "@/api/client";
import { useAuthContext } from "@/hooks/AuthContext";
import { hasPermission } from "@/components/RequirePermission";
import { NORA_DOC_TYPES } from "@/features/ea-delivery/soawTemplate";

interface Evidence {
  kind: string;
  ref: string;
  label: string | null;
}

interface Deliverable {
  id: string;
  stage_no: number;
  key: string;
  title: string;
  description: string | null;
  status: "notStarted" | "inProgress" | "inReview" | "approved" | "descoped";
  built_in: boolean;
  evidence: Evidence[];
  owner_display_name: string | null;
  approved_by_display_name: string | null;
  approved_at: string | null;
}

interface StageBlock {
  stage_no: number;
  deliverables: Deliverable[];
  progress: number;
  complete: boolean;
}

interface ProgramData {
  stages: StageBlock[];
  summary: { total: number; approved: number; progress: number };
}

interface GapData {
  create: number;
  replace: number;
  modify: number;
  retire: number;
  untraceable: number;
}

interface OpportunitiesData {
  proposed: number;
  approved: number;
  inTransition: number;
}

interface DashboardData {
  gaps: GapData;
  opportunities: OpportunitiesData;
}

const STATUSES = ["notStarted", "inProgress", "inReview", "approved", "descoped"] as const;

const STATUS_COLOR: Record<string, "default" | "info" | "warning" | "success"> = {
  notStarted: "default",
  inProgress: "info",
  inReview: "warning",
  approved: "success",
  descoped: "default",
};

// Stage order for display: 1..10 then the cross-cutting governance track.
const STAGE_DISPLAY_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 0];

export default function NoraProgramPage() {
  const { t } = useTranslation(["nav", "common", "grc"]);
  const { user } = useAuthContext();
  const canManage = hasPermission(user?.permissions, "nora.manage");
  const [data, setData] = useState<ProgramData | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [evidenceFor, setEvidenceFor] = useState<Deliverable | null>(null);
  const [evidenceLabel, setEvidenceLabel] = useState("");
  const [evidenceRef, setEvidenceRef] = useState("");
  const [addFor, setAddFor] = useState<number | null>(null);
  const [addTitle, setAddTitle] = useState("");
  const [docMenuAnchor, setDocMenuAnchor] = useState<HTMLElement | null>(null);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      setData(await api.get<ProgramData>("/nora-program"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    }
  }, []);

  const loadDashboard = useCallback(async () => {
    try {
      // Fetch gap analysis summary
      const gapResponse = await api.get<{
        summary: GapData;
      }>("/reports/gap-analysis");

      // Fetch improvement opportunities with status counts
      const oppResponse = await api.get<{
        items: Array<{ status: string }>;
      }>("/improvement-opportunities");
      const oppCounts = oppResponse.items.reduce(
        (acc, item) => {
          if (item.status === "proposed") acc.proposed += 1;
          else if (item.status === "approved") acc.approved += 1;
          else if (item.status === "inTransition") acc.inTransition += 1;
          return acc;
        },
        { proposed: 0, approved: 0, inTransition: 0 },
      );

      setDashboardData({
        gaps: gapResponse.summary,
        opportunities: oppCounts,
      });
    } catch {
      // Dashboard data is optional; silently fail with empty data
      setDashboardData({
        gaps: { create: 0, replace: 0, modify: 0, retire: 0, untraceable: 0 },
        opportunities: { proposed: 0, approved: 0, inTransition: 0 },
      });
    }
  }, []);

  useEffect(() => {
    load();
    loadDashboard();
  }, [load, loadDashboard]);

  const patch = async (d: Deliverable, body: Record<string, unknown>) => {
    setError("");
    try {
      await api.patch(`/nora-program/deliverables/${d.id}`, body);
      await load();
    } catch (e) {
      setError(
        e instanceof ApiError && typeof e.detail === "string"
          ? e.detail
          : e instanceof Error
            ? e.message
            : "error",
      );
    }
  };

  const addEvidence = async () => {
    if (!evidenceFor || !evidenceRef.trim()) return;
    const next = [
      ...evidenceFor.evidence,
      { kind: "link", ref: evidenceRef.trim(), label: evidenceLabel.trim() || null },
    ];
    await patch(evidenceFor, { evidence: next });
    setEvidenceFor(null);
    setEvidenceLabel("");
    setEvidenceRef("");
  };

  const removeEvidence = async (d: Deliverable, index: number) => {
    await patch(d, { evidence: d.evidence.filter((_, i) => i !== index) });
  };

  const addDeliverable = async () => {
    if (addFor === null || !addTitle.trim()) return;
    await api.post("/nora-program/deliverables", { stage_no: addFor, title: addTitle.trim() });
    setAddFor(null);
    setAddTitle("");
    await load();
  };

  if (!data) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const stageByNo = new Map(data.stages.map((s) => [s.stage_no, s]));

  // Tile link handler
  const handleTileClick = (path: string) => navigate(path);

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 0.5 }}>
        <Typography variant="h5" fontWeight={700}>
          {t("noraProgram.title")}
        </Typography>
        <Chip
          size="small"
          color={data.summary.progress === 100 ? "success" : "default"}
          label={`${data.summary.approved}/${data.summary.total} · ${data.summary.progress}%`}
        />
        <Box sx={{ flex: 1 }} />
        {canManage && (
          <>
            <Button
              variant="outlined"
              startIcon={<MaterialSymbol icon="post_add" size={18} />}
              onClick={(e) => setDocMenuAnchor(e.currentTarget)}
            >
              {t("noraProgram.newDocument")}
            </Button>
            <Menu
              anchorEl={docMenuAnchor}
              open={!!docMenuAnchor}
              onClose={() => setDocMenuAnchor(null)}
            >
              {NORA_DOC_TYPES.map((dt) => (
                <MenuItem
                  key={dt}
                  onClick={() => {
                    setDocMenuAnchor(null);
                    navigate(`/ea-delivery/soaw/new?type=${dt}`);
                  }}
                >
                  {t(`noraProgram.docType.${dt}`)}
                </MenuItem>
              ))}
            </Menu>
          </>
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("noraProgram.subtitle")}
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Executive Dashboard */}
      {dashboardData && (
        <Paper sx={{ p: 3, mb: 3, bgcolor: "background.paper" }}>
          <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>
            {t("noraProgram.dashboard")}
          </Typography>
          <Grid container spacing={2}>
            {/* Program Progress Tile */}
            <Grid item xs={12} sm={6} md={3}>
              <Card
                sx={{
                  height: "100%",
                  cursor: "pointer",
                  transition: "all 0.2s",
                  "&:hover": { boxShadow: 3, transform: "translateY(-2px)" },
                }}
              >
                <CardActionArea
                  onClick={() => handleTileClick("/nora-program")}
                  sx={{ p: 2, height: "100%", display: "flex", flexDirection: "column" }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                    <MaterialSymbol icon="checklist" color="#2e7d32" size={24} />
                    <Typography variant="caption" color="text.secondary">
                      {t("noraProgram.tileProgram")}
                    </Typography>
                  </Box>
                  <Typography variant="h4" fontWeight={700} sx={{ mb: 1 }}>
                    {data.summary.progress}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {data.summary.approved}/{data.summary.total} {t("common:approved")}
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={data.summary.progress}
                    sx={{ height: 4, borderRadius: 2 }}
                  />
                </CardActionArea>
              </Card>
            </Grid>

            {/* Gaps Tile */}
            <Grid item xs={12} sm={6} md={3}>
              <Card
                sx={{
                  height: "100%",
                  cursor: "pointer",
                  transition: "all 0.2s",
                  "&:hover": { boxShadow: 3, transform: "translateY(-2px)" },
                }}
              >
                <CardActionArea
                  onClick={() => handleTileClick("/reports/gap-analysis")}
                  sx={{ p: 2, height: "100%", display: "flex", flexDirection: "column" }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                    <MaterialSymbol icon="difference" color="#d32f2f" size={24} />
                    <Typography variant="caption" color="text.secondary">
                      {t("noraProgram.tileGaps")}
                    </Typography>
                  </Box>
                  <Typography variant="h4" fontWeight={700}>
                    {dashboardData.gaps.create + dashboardData.gaps.replace +
                     dashboardData.gaps.modify + dashboardData.gaps.retire}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {dashboardData.gaps.create} {t("noraProgram.gapNew")},
                    {dashboardData.gaps.replace} {t("noraProgram.gapReplace")}
                  </Typography>
                </CardActionArea>
              </Card>
            </Grid>

            {/* Opportunities Tile */}
            <Grid item xs={12} sm={6} md={3}>
              <Card
                sx={{
                  height: "100%",
                  cursor: "pointer",
                  transition: "all 0.2s",
                  "&:hover": { boxShadow: 3, transform: "translateY(-2px)" },
                }}
              >
                <CardActionArea
                  onClick={() => handleTileClick("/grc?tab=governance")}
                  sx={{ p: 2, height: "100%", display: "flex", flexDirection: "column" }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                    <MaterialSymbol icon="trending_up" color="#f57c00" size={24} />
                    <Typography variant="caption" color="text.secondary">
                      {t("noraProgram.tileOpportunities")}
                    </Typography>
                  </Box>
                  <Typography variant="h4" fontWeight={700}>
                    {dashboardData.opportunities.inTransition}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {dashboardData.opportunities.proposed} {t("noraProgram.oppProposed")},
                    {dashboardData.opportunities.approved} {t("noraProgram.oppApproved")}
                  </Typography>
                </CardActionArea>
              </Card>
            </Grid>
          </Grid>
        </Paper>
      )}

      {STAGE_DISPLAY_ORDER.map((stageNo) => {
        const stage = stageByNo.get(stageNo);
        if (!stage || stage.deliverables.length === 0) return null;
        return (
          <Accordion key={stageNo} defaultExpanded={false} disableGutters>
            <AccordionSummary expandIcon={<MaterialSymbol icon="expand_more" size={20} />}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, width: "100%", pr: 2 }}>
                <MaterialSymbol
                  icon={stage.complete ? "check_circle" : "flag"}
                  size={20}
                  color={stage.complete ? "#2e7d32" : "#607d8b"}
                />
                <Typography sx={{ fontWeight: 600, flexShrink: 0 }}>
                  {t(`noraProgram.stage.${stageNo}`)}
                </Typography>
                <Box sx={{ flex: 1, mx: 2 }}>
                  <LinearProgress
                    variant="determinate"
                    value={stage.progress}
                    color={stage.complete ? "success" : "primary"}
                    sx={{ height: 6, borderRadius: 3 }}
                  />
                </Box>
                <Typography variant="caption" color="text.secondary">
                  {stage.progress}%
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails sx={{ p: 0 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>
                      {t("noraProgram.colDeliverable")}
                    </TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 170 }}>
                      {t("noraProgram.colStatus")}
                    </TableCell>
                    <TableCell sx={{ fontWeight: 700 }}>{t("noraProgram.colEvidence")}</TableCell>
                    <TableCell sx={{ width: 60 }} />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {stage.deliverables.map((d) => (
                    <TableRow key={d.id} hover>
                      <TableCell
                        sx={{
                          textDecoration: d.status === "descoped" ? "line-through" : undefined,
                          color: d.status === "descoped" ? "text.disabled" : undefined,
                        }}
                      >
                        <Tooltip
                          title={
                            d.approved_at
                              ? `${d.approved_by_display_name ?? ""} — ${new Date(d.approved_at).toLocaleString()}`
                              : d.description || ""
                          }
                        >
                          <span>{d.title}</span>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        {canManage ? (
                          <TextField
                            select
                            size="small"
                            variant="standard"
                            value={d.status}
                            onChange={(e) => patch(d, { status: e.target.value })}
                            sx={{ minWidth: 140 }}
                          >
                            {STATUSES.map((s) => (
                              <MenuItem key={s} value={s}>
                                {t(`noraProgram.status.${s}`)}
                              </MenuItem>
                            ))}
                          </TextField>
                        ) : (
                          <Chip
                            size="small"
                            color={STATUS_COLOR[d.status]}
                            label={t(`noraProgram.status.${d.status}`)}
                          />
                        )}
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", alignItems: "center" }}>
                          {d.evidence.map((ev, i) => (
                            <Chip
                              key={`${ev.ref}-${i}`}
                              size="small"
                              variant="outlined"
                              icon={<MaterialSymbol icon="attachment" size={14} />}
                              label={
                                <Link
                                  href={ev.ref}
                                  target={ev.ref.startsWith("/") ? undefined : "_blank"}
                                  rel="noopener noreferrer"
                                  underline="hover"
                                >
                                  {ev.label || ev.ref}
                                </Link>
                              }
                              onDelete={canManage ? () => removeEvidence(d, i) : undefined}
                            />
                          ))}
                          {canManage && (
                            <Tooltip title={t("noraProgram.addEvidence")}>
                              <IconButton size="small" onClick={() => setEvidenceFor(d)}>
                                <MaterialSymbol icon="add_link" size={18} />
                              </IconButton>
                            </Tooltip>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        {canManage && !d.built_in && (
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => api.delete(`/nora-program/deliverables/${d.id}`).then(load)}
                          >
                            <MaterialSymbol icon="delete" size={18} />
                          </IconButton>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {canManage && (
                <Box sx={{ p: 1 }}>
                  <Button
                    size="small"
                    startIcon={<MaterialSymbol icon="add" size={16} />}
                    onClick={() => {
                      setAddFor(stageNo);
                      setAddTitle("");
                    }}
                  >
                    {t("noraProgram.addDeliverable")}
                  </Button>
                </Box>
              )}
            </AccordionDetails>
          </Accordion>
        );
      })}

      {/* Add evidence dialog */}
      <Dialog open={!!evidenceFor} onClose={() => setEvidenceFor(null)} fullWidth maxWidth="sm">
        <DialogTitle>{t("noraProgram.addEvidence")}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            autoFocus
            label={t("noraProgram.evidenceLabel")}
            value={evidenceLabel}
            onChange={(e) => setEvidenceLabel(e.target.value)}
          />
          <TextField
            label={t("noraProgram.evidenceRef")}
            placeholder="/reports/gap-analysis · /cards/… · https://…"
            value={evidenceRef}
            onChange={(e) => setEvidenceRef(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEvidenceFor(null)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={addEvidence} disabled={!evidenceRef.trim()}>
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Add deliverable dialog */}
      <Dialog open={addFor !== null} onClose={() => setAddFor(null)} fullWidth maxWidth="sm">
        <DialogTitle>{t("noraProgram.addDeliverable")}</DialogTitle>
        <DialogContent sx={{ pt: 1 }}>
          <TextField
            autoFocus
            fullWidth
            label={t("noraProgram.colDeliverable")}
            value={addTitle}
            onChange={(e) => setAddTitle(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddFor(null)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={addDeliverable} disabled={!addTitle.trim()}>
            {t("common:actions.create")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
