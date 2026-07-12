/**
 * NoraProgramPage — the NORA EA Program tracker: ten methodology stages plus
 * continuous governance, each with its deliverables, evidence links and
 * stage-gate approval state. Features an executive dashboard aggregating
 * stage readiness, approval coverage, gaps, and improvement opportunities.
 *
 * [FORK FEATURE] — noraPlan.md WP3.1 + deferred executive dashboard.
 */
import type React from "react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
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
import Divider from "@mui/material/Divider";
import { NORA_DOC_TYPES, PRACTICE_DOC_TYPES } from "@/features/ea-delivery/soawTemplate";
import EaRequirementsPanel from "@/features/nora/EaRequirementsPanel";
import NeaEvidencePanel from "@/features/nora/NeaEvidencePanel";
import PlateausSegmentsPanel from "@/features/nora/PlateausSegmentsPanel";

interface Evidence {
  kind: string;
  ref: string;
  label: string | null;
}

interface Deliverable {
  id: string;
  stage_no: number;
  key: string;
  domain: string | null;
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
  methodology: "v1" | "v2";
  stages: StageBlock[];
  practice: StageBlock;
  summary: { total: number; approved: number; progress: number };
}

interface DashboardData {
  approvals: {
    total: number;
    approved: number;
    in_review: number;
    draft: number;
    broken: number;
    rejected: number;
    approved_pct: number;
  };
  landscape: {
    current: number;
    transition: number;
    target: number;
  };
  gaps: {
    create: number;
    replace: number;
    modify: number;
    retire: number;
    total: number;
    untraceable: number;
  };
  initiatives: {
    onTrack: number;
    atRisk: number;
    offTrack: number;
    noReport: number;
  };
  waivers: {
    active: number;
    pending: number;
    expiringSoon: number;
    expired: number;
  };
  opportunities: {
    proposed: number;
    approved: number;
    inTransition: number;
    realized: number;
  };
  compliance: {
    open: number;
    critical: number;
    high: number;
  };
  // Optional so a backend that predates WP100.1 keeps the page usable.
  strategy?: {
    pillars: number;
    objectives: number;
    unpillared: number;
  };
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
// Updated methodology (WP6.1): phases 1–7, phase 7 is the continuous element.
const V2_PHASE_DISPLAY_ORDER = [1, 2, 3, 4, 5, 6, 7];
// Practice-establishment checklist (WP6.8) — sentinel stage, rendered last.
const PRACTICE_STAGE_NO = -1;

// Practice checklist rows → the governed-document template that authors them.
const PRACTICE_DOC_LINK: Record<string, string> = {
  practice_ea_strategy: "ea_project_strategy",
  practice_mandates: "ea_mandates",
  practice_services: "ea_services",
  practice_org_structure: "ea_org_structure",
  practice_governance_model: "ea_governance_model",
  practice_processes: "ea_processes",
  practice_interaction_model: "ea_interaction_model",
  practice_kpis: "ea_kpis",
  practice_vocabulary: "ea_vocabulary",
};

function practiceDocSuggestion(key: string): { path: string; labelKey: string } | null {
  const docType = PRACTICE_DOC_LINK[key];
  return docType
    ? { path: `/ea-delivery/soaw/new?type=${docType}`, labelKey: "noraProgram.createDocument" }
    : null;
}

// Deep-link suggestions for v2 deliverables: phase-2 data collection lands
// via the DGA template importer; phases 5/6 read the gap and roadmap views.
function v2SuggestedLink(key: string): { path: string; labelKey: string } | null {
  if (key.endsWith("_data_collection"))
    return { path: "/admin/settings?tab=migration", labelKey: "noraProgram.suggestImport" };
  if (key.startsWith("p5_"))
    return { path: "/reports/gap-analysis", labelKey: "noraProgram.suggestGapReport" };
  if (key.startsWith("p6_"))
    return { path: "/ppm", labelKey: "noraProgram.suggestRoadmap" };
  return null;
}

// --- Dashboard tile primitives --------------------------------------------
interface TileProps {
  icon: string;
  iconColor: string;
  label: string;
  value: React.ReactNode;
  detail?: React.ReactNode;
  onClick?: () => void;
  progress?: number;
  progressColor?: "primary" | "success" | "warning" | "error";
  alert?: boolean;
}

function DashboardTile({
  icon,
  iconColor,
  label,
  value,
  detail,
  onClick,
  progress,
  progressColor = "primary",
  alert = false,
}: TileProps) {
  const content = (
    <Box
      sx={{
        p: 2,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        borderLeft: alert ? "3px solid #d32f2f" : "3px solid transparent",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
        <MaterialSymbol icon={icon} color={iconColor} size={22} />
        <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
          {label}
        </Typography>
      </Box>
      <Typography variant="h4" fontWeight={700} sx={{ mb: detail ? 0.5 : 0, lineHeight: 1.2 }}>
        {value}
      </Typography>
      {detail && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
          {detail}
        </Typography>
      )}
      {progress !== undefined && (
        <Box sx={{ mt: "auto", pt: 1 }}>
          <LinearProgress
            variant="determinate"
            value={progress}
            color={progressColor}
            sx={{ height: 4, borderRadius: 2 }}
          />
        </Box>
      )}
    </Box>
  );

  return (
    <Card
      sx={{
        height: "100%",
        transition: "all 0.15s",
        "&:hover": onClick ? { boxShadow: 3, transform: "translateY(-2px)" } : undefined,
      }}
    >
      {onClick ? (
        <CardActionArea onClick={onClick} sx={{ height: "100%" }}>
          {content}
        </CardActionArea>
      ) : (
        content
      )}
    </Card>
  );
}

export default function NoraProgramPage() {
  const { t } = useTranslation(["nav", "common", "grc"]);
  const { user } = useAuthContext();
  const canManage = hasPermission(user?.permissions, "nora.manage");
  const canAdmin = hasPermission(user?.permissions, "admin.settings");
  const [data, setData] = useState<ProgramData | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [evidenceFor, setEvidenceFor] = useState<Deliverable | null>(null);
  const [evidenceLabel, setEvidenceLabel] = useState("");
  const [evidenceRef, setEvidenceRef] = useState("");
  const [addFor, setAddFor] = useState<number | null>(null);
  const [addTitle, setAddTitle] = useState("");
  const [docMenuAnchor, setDocMenuAnchor] = useState<HTMLElement | null>(null);
  const [switchOpen, setSwitchOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
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
      const dashboard = await api.get<DashboardData>("/nora-program/dashboard");
      setDashboardData(dashboard);
    } catch {
      // Dashboard is optional context; keep the page usable if it fails.
      setDashboardData(null);
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

  const switchMethodology = async () => {
    setSwitching(true);
    setError("");
    try {
      await api.post("/nora-program/methodology", { version: "v2" });
      setSwitchOpen(false);
      await load();
    } catch (e) {
      setError(
        e instanceof ApiError && typeof e.detail === "string"
          ? e.detail
          : e instanceof Error
            ? e.message
            : "error",
      );
    } finally {
      setSwitching(false);
    }
  };

  if (!data) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const stageByNo = new Map(data.stages.map((s) => [s.stage_no, s]));
  if (data.practice) stageByNo.set(PRACTICE_STAGE_NO, data.practice);

  // Tile link handler
  const handleTileClick = (path: string) => navigate(path);

  // Placeholder used when the /nora-program/dashboard aggregation endpoint
  // hasn't responded (backend not restarted, permission missing, etc.) so the
  // dashboard still renders instead of vanishing.
  const dash: DashboardData = dashboardData ?? {
    approvals: {
      total: 0,
      approved: 0,
      in_review: 0,
      draft: 0,
      broken: 0,
      rejected: 0,
      approved_pct: 0,
    },
    landscape: { current: 0, transition: 0, target: 0 },
    gaps: { create: 0, replace: 0, modify: 0, retire: 0, total: 0, untraceable: 0 },
    initiatives: { onTrack: 0, atRisk: 0, offTrack: 0, noReport: 0 },
    waivers: { active: 0, pending: 0, expiringSoon: 0, expired: 0 },
    opportunities: { proposed: 0, approved: 0, inTransition: 0, realized: 0 },
    compliance: { open: 0, critical: 0, high: 0 },
    strategy: { pillars: 0, objectives: 0, unpillared: 0 },
  };

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
        <Chip
          size="small"
          variant="outlined"
          icon={<MaterialSymbol icon="route" size={14} />}
          label={t(`noraProgram.methodology.${data.methodology}`)}
        />
        <Box sx={{ flex: 1 }} />
        {canAdmin && data.methodology === "v1" && (
          <Button
            variant="outlined"
            color="secondary"
            startIcon={<MaterialSymbol icon="upgrade" size={18} />}
            onClick={() => setSwitchOpen(true)}
          >
            {t("noraProgram.switchToV2")}
          </Button>
        )}
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
              <Divider />
              {PRACTICE_DOC_TYPES.map((dt) => (
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
        {t(data.methodology === "v2" ? "noraProgram.subtitleV2" : "noraProgram.subtitle")}
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Executive Dashboard — always renders; enrichment tiles fill in when
          the /nora-program/dashboard aggregation endpoint responds. */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <MaterialSymbol icon="dashboard" size={22} color="#1976d2" />
          <Typography variant="h6" fontWeight={700}>
            {t("noraProgram.dashboard")}
          </Typography>
          <Chip
            size="small"
            variant="outlined"
            label={t("noraProgram.dashboardSubtitle")}
            sx={{ ml: 1 }}
          />
          {!dashboardData && (
            <Chip
              size="small"
              color="warning"
              variant="outlined"
              icon={<MaterialSymbol icon="sync_problem" size={14} />}
              label={t("noraProgram.dashEnrichmentUnavailable")}
              sx={{ ml: 1 }}
            />
          )}
        </Box>

          {/* Row 1 — Program state (methodology + governance) */}
          <Typography
            variant="overline"
            color="text.secondary"
            sx={{ display: "block", mb: 1, fontWeight: 600 }}
          >
            {t("noraProgram.dashSectionProgram")}
          </Typography>
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <DashboardTile
                icon="checklist"
                iconColor="#2e7d32"
                label={t("noraProgram.tileProgram")}
                value={`${data.summary.progress}%`}
                detail={`${data.summary.approved}/${data.summary.total} ${t("noraProgram.dashApproved")}`}
                progress={data.summary.progress}
                progressColor={data.summary.progress === 100 ? "success" : "primary"}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <DashboardTile
                icon="verified"
                iconColor="#1976d2"
                label={t("noraProgram.tileApprovals")}
                value={`${dash.approvals.approved_pct}%`}
                detail={
                  <>
                    {dash.approvals.approved} {t("noraProgram.dashApproved")} ·{" "}
                    {dash.approvals.in_review} {t("noraProgram.dashInReview")}
                    {dash.approvals.broken > 0 && (
                      <>
                        {" · "}
                        <Box component="span" sx={{ color: "#d32f2f", fontWeight: 600 }}>
                          {dash.approvals.broken} {t("noraProgram.dashBroken")}
                        </Box>
                      </>
                    )}
                  </>
                }
                progress={dash.approvals.approved_pct}
                progressColor={dash.approvals.broken > 0 ? "warning" : "success"}
                onClick={() =>
                  handleTileClick("/inventory?approval_status=IN_REVIEW,DRAFT,BROKEN")
                }
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <DashboardTile
                icon="account_tree"
                iconColor="#0288d1"
                label={t("noraProgram.tileLandscape")}
                value={dash.landscape.current}
                detail={
                  <>
                    {t("noraProgram.dashCurrentCards")}
                    <br />
                    <Box component="span" sx={{ fontWeight: 600 }}>
                      +{dash.landscape.transition + dash.landscape.target}
                    </Box>{" "}
                    {t("noraProgram.dashTargetChanges")} (
                    {dash.landscape.transition} T ·{" "}
                    {dash.landscape.target} F)
                  </>
                }
                onClick={() => handleTileClick("/inventory")}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <DashboardTile
                icon="difference"
                iconColor="#f57c00"
                label={t("noraProgram.tileGaps")}
                value={dash.gaps.total}
                detail={
                  <>
                    {dash.gaps.create} {t("noraProgram.gapNew")} ·{" "}
                    {dash.gaps.replace} {t("noraProgram.gapReplace")} ·{" "}
                    {dash.gaps.modify} {t("noraProgram.gapModify")} ·{" "}
                    {dash.gaps.retire} {t("noraProgram.gapRetire")}
                    {dash.gaps.untraceable > 0 && (
                      <>
                        <br />
                        <Box component="span" sx={{ color: "#d32f2f", fontWeight: 600 }}>
                          ⚠ {dash.gaps.untraceable}{" "}
                          {t("noraProgram.dashUntraceable")}
                        </Box>
                      </>
                    )}
                  </>
                }
                alert={dash.gaps.untraceable > 0}
                onClick={() => handleTileClick("/reports/gap-analysis")}
              />
            </Grid>
          </Grid>

          {/* Row 2 — Governance and risk */}
          <Typography
            variant="overline"
            color="text.secondary"
            sx={{ display: "block", mb: 1, fontWeight: 600 }}
          >
            {t("noraProgram.dashSectionGovernance")}
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <DashboardTile
                icon="rocket_launch"
                iconColor="#1976d2"
                label={t("noraProgram.tileInitiatives")}
                value={
                  <Box sx={{ display: "flex", alignItems: "baseline", gap: 1 }}>
                    <Box component="span" sx={{ color: "#2e7d32" }}>
                      {dash.initiatives.onTrack}
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      /
                    </Typography>
                    <Box component="span" sx={{ color: "#f57c00", fontSize: "0.75em" }}>
                      {dash.initiatives.atRisk}
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      /
                    </Typography>
                    <Box component="span" sx={{ color: "#d32f2f", fontSize: "0.75em" }}>
                      {dash.initiatives.offTrack}
                    </Box>
                  </Box>
                }
                detail={
                  <>
                    {t("noraProgram.initOnTrack")} / {t("noraProgram.initAtRisk")} /{" "}
                    {t("noraProgram.initOffTrack")}
                    {dash.initiatives.noReport > 0 && (
                      <>
                        <br />
                        {dash.initiatives.noReport}{" "}
                        {t("noraProgram.dashNoReport")}
                      </>
                    )}
                  </>
                }
                alert={dash.initiatives.offTrack > 0}
                onClick={() => handleTileClick("/ppm")}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <DashboardTile
                icon="gavel"
                iconColor="#7b1fa2"
                label={t("noraProgram.tileWaivers")}
                value={dash.waivers.active}
                detail={
                  <>
                    {dash.waivers.pending} {t("noraProgram.dashPending")}
                    {dash.waivers.expiringSoon > 0 && (
                      <>
                        {" · "}
                        <Box component="span" sx={{ color: "#f57c00", fontWeight: 600 }}>
                          {dash.waivers.expiringSoon}{" "}
                          {t("noraProgram.dashExpiringSoon")}
                        </Box>
                      </>
                    )}
                    {dash.waivers.expired > 0 && (
                      <>
                        {" · "}
                        <Box component="span" sx={{ color: "#d32f2f", fontWeight: 600 }}>
                          {dash.waivers.expired} {t("noraProgram.dashExpired")}
                        </Box>
                      </>
                    )}
                  </>
                }
                alert={dash.waivers.expired > 0}
                onClick={() => handleTileClick("/tech-standards")}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <DashboardTile
                icon="trending_up"
                iconColor="#00897b"
                label={t("noraProgram.tileOpportunities")}
                value={dash.opportunities.inTransition}
                detail={
                  <>
                    {dash.opportunities.proposed} {t("noraProgram.oppProposed")} ·{" "}
                    {dash.opportunities.approved} {t("noraProgram.oppApproved")}
                    <br />
                    {dash.opportunities.realized}{" "}
                    {t("noraProgram.dashRealized")}
                  </>
                }
                onClick={() => handleTileClick("/grc?tab=governance")}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <DashboardTile
                icon="shield"
                iconColor={
                  dash.compliance.critical > 0
                    ? "#d32f2f"
                    : dash.compliance.high > 0
                      ? "#f57c00"
                      : "#2e7d32"
                }
                label={t("noraProgram.tileCompliance")}
                value={dash.compliance.open}
                detail={
                  dash.compliance.open === 0 ? (
                    t("noraProgram.dashNoFindings")
                  ) : (
                    <>
                      {dash.compliance.critical > 0 && (
                        <Box component="span" sx={{ color: "#d32f2f", fontWeight: 600 }}>
                          {dash.compliance.critical}{" "}
                          {t("noraProgram.dashCritical")}
                        </Box>
                      )}
                      {dash.compliance.critical > 0 &&
                        dash.compliance.high > 0 &&
                        " · "}
                      {dash.compliance.high > 0 && (
                        <Box component="span" sx={{ color: "#f57c00", fontWeight: 600 }}>
                          {dash.compliance.high} {t("noraProgram.dashHigh")}
                        </Box>
                      )}
                    </>
                  )
                }
                alert={dash.compliance.critical > 0}
                onClick={() => handleTileClick("/grc?tab=compliance")}
              />
            </Grid>
            {/* WP100.1 — strategy cascade tile (pillars / objectives / unaligned) */}
            <Grid item xs={12} sm={6} md={3}>
              <DashboardTile
                icon="foundation"
                iconColor="#7b1fa2"
                label={t("noraProgram.tileStrategy")}
                value={dash.strategy?.pillars ?? 0}
                detail={
                  <>
                    {dash.strategy?.objectives ?? 0} {t("noraProgram.dashObjectives")}
                    {(dash.strategy?.unpillared ?? 0) > 0 && (
                      <>
                        {" · "}
                        <Box component="span" sx={{ color: "#f57c00", fontWeight: 600 }}>
                          {dash.strategy?.unpillared} {t("noraProgram.dashUnpillared")}
                        </Box>
                      </>
                    )}
                  </>
                }
                onClick={() => handleTileClick("/reports/strategy-cascade")}
              />
            </Grid>
          </Grid>
      </Paper>

      {[
        ...(data.methodology === "v2" ? V2_PHASE_DISPLAY_ORDER : STAGE_DISPLAY_ORDER),
        PRACTICE_STAGE_NO,
      ].map((stageNo) => {
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
                  {stageNo === PRACTICE_STAGE_NO
                    ? t("noraProgram.practiceChecklist")
                    : t(
                        data.methodology === "v2"
                          ? `noraProgram.phase.${stageNo}`
                          : `noraProgram.stage.${stageNo}`,
                      )}
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
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          {d.domain && (
                            <Chip
                              size="small"
                              variant="outlined"
                              label={t(`noraProgram.domain.${d.domain}`)}
                              sx={{ flexShrink: 0 }}
                            />
                          )}
                          <Tooltip
                            title={
                              d.approved_at
                                ? `${d.approved_by_display_name ?? ""} — ${new Date(d.approved_at).toLocaleString()}`
                                : d.description || ""
                            }
                          >
                            <span>{d.title}</span>
                          </Tooltip>
                        </Box>
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
                          {d.evidence.length === 0 &&
                            (() => {
                              const suggestion = d.key.startsWith("practice_")
                                ? practiceDocSuggestion(d.key)
                                : data.methodology === "v2"
                                  ? v2SuggestedLink(d.key)
                                  : null;
                              return suggestion ? (
                                <Chip
                                  size="small"
                                  variant="outlined"
                                  color="info"
                                  icon={<MaterialSymbol icon="arrow_forward" size={14} />}
                                  label={t(suggestion.labelKey)}
                                  onClick={() => navigate(suggestion.path)}
                                />
                              ) : null;
                            })()}
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
              {canManage && stageNo !== PRACTICE_STAGE_NO && (
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

      {/* EA Requirements register — methodology phase 7 (WP6.1) */}
      <EaRequirementsPanel canManage={canManage} />

      {/* NEA alignment / evidence-pack export (WP5.3) */}
      <NeaEvidencePanel canManage={canManage} />

      {/* Plateaus (time-slices) + segment scopes (WP5.4) */}
      <PlateausSegmentsPanel canManage={canManage} />

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

      {/* Switch to the updated 7-phase methodology (WP6.1) */}
      <Dialog open={switchOpen} onClose={() => setSwitchOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{t("noraProgram.switchToV2")}</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            {t("noraProgram.switchExplain")}
          </Alert>
          <Typography variant="body2" color="text.secondary">
            {t("noraProgram.switchKeepsHistory")}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSwitchOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={switchMethodology} disabled={switching}>
            {t("noraProgram.switchConfirm")}
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
