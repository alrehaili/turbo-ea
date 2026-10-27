import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useAuthContext } from "@/hooks/AuthContext";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useDateFormat } from "@/hooks/useDateFormat";
import { canAccessPath } from "@/lib/routePermissions";
import { hasPermission } from "@/components/RequirePermission";
import { STATUS_COLORS } from "@/theme/tokens";
import type {
  GovernanceState,
  GovernedDelivery,
  ReviewCoverageFigures,
  ReviewCoverageRow,
  ArchitectureRiskFigures,
  ArchitectureRiskRow,
  ExecutiveGovernanceData,
  GovernanceDrilldown,
  GovernanceElapsed,
  GovernanceImplementation,
  GovernanceProcessing,
  GovernanceResolution,
  GovernanceTurnaround,
  GovernanceWorkingDaysFigure,
} from "@/types";
import AssessApplicabilityDialog from "./AssessApplicabilityDialog";
import ExecutiveKpiTile from "./ExecutiveKpiTile";
import { pct, periodLabel } from "./executiveFormat";
import { useExecutivePeriod } from "./useExecutivePeriod";

/** A labelled section heading, so Activity / Effectiveness / Impact never blur. */
function SectionHeader({ icon, title, hint }: { icon: string; title: string; hint: string }) {
  return (
    <Box sx={{ mt: 3, mb: 1 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
        <MaterialSymbol icon={icon} size={18} />
        <Typography variant="subtitle1" fontWeight={700}>
          {title}
        </Typography>
      </Box>
      <Typography variant="caption" color="text.secondary" component="div">
        {hint}
      </Typography>
    </Box>
  );
}

function CountCard({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="subtitle2" fontWeight={700} gutterBottom>
          {label}
        </Typography>
        {children}
      </CardContent>
    </Card>
  );
}

/**
 * EA Governance (Batch 3.1, DECISION_LOG §3.1). Activity, effectiveness and
 * impact are shown as three **separate labelled sections** and never mixed:
 * Activity states that governance happened (no value claim), Effectiveness
 * carries the rule-based technology standards compliance (GOV-03) and its
 * assessment coverage as two distinct figures, and anything without a
 * defensible calculation shows *Not available* with the reason it needs.
 */
export default function ExecutiveGovernance() {
  const { t } = useTranslation("common");
  const { user } = useAuthContext();
  const { formatDate, formatDateTime } = useDateFormat();
  const { period } = useExecutivePeriod();
  const path = period
    ? `/reports/executive/governance?period=${encodeURIComponent(period)}`
    : "/reports/executive/governance";
  const { data, error, loading } = useApiQuery<ExecutiveGovernanceData>(path);

  const canStandards = canAccessPath(user?.permissions, "/tech-standards");
  const drillPath =
    data && data.effectiveness.compliance.status === "ok" && canStandards
      ? `/reports/executive/kpi/GOV-03/drilldown${period ? `?period=${encodeURIComponent(period)}` : ""}`
      : null;
  const { data: drill } = useApiQuery<GovernanceDrilldown>(drillPath);
  // The architecture-related risks behind RSK-01, under the risks permission.
  const riskDrillPath =
    data && data.impact.architecture_risks.status === "ok" && hasPermission(user?.permissions, "risks.view")
      ? "/reports/executive/kpi/RSK-01/drilldown"
      : null;
  const { data: riskDrill } = useApiQuery<{ rows: ArchitectureRiskRow[] }>(riskDrillPath);
  // GOV-01 rows need a review module permission (I-62); refreshed after an assessment.
  const [assessKey, setAssessKey] = useState(0);
  const [assessing, setAssessing] = useState<{ id: string; name: string } | null>(null);
  const canReviews =
    hasPermission(user?.permissions, "arb.view") || hasPermission(user?.permissions, "adr.view");
  const { data: coverageDrill } = useApiQuery<{ rows: ReviewCoverageRow[]; can_assess: boolean }>(
    data && canReviews ? "/reports/executive/kpi/GOV-01/drilldown" : null,
    { refetchKey: assessKey },
  );

  if (error) return <Alert severity="error">{error.message || t("errors.generic")}</Alert>;
  if (!data) return loading ? <LinearProgress /> : null;
  // The payload belongs to a period; while a switch is in flight keep the bar
  // rather than show the old period's figures under the new heading.
  if (period && data.period.key !== period) return <LinearProgress />;

  const start = data.fiscal_year_start;
  const label = (key: string) => periodLabel(key, start, t);
  const periodText = `${label(data.period.key)} · ${t("dashboard.executive.ceo.asOf", { date: formatDate(data.period.as_of) })}`;
  const g = t;
  const reason = (key: string) => g(`dashboard.executive.governancePage.reason.${key}`);

  const { activity, effectiveness } = data;
  const compliance = effectiveness.compliance;
  const coverage = effectiveness.coverage;

  return (
    <Box>
      <Typography variant="h6" fontWeight={700}>
        {g("dashboard.executive.governancePage.title")}
      </Typography>
      <Typography variant="caption" color="text.secondary" component="div">
        {g("dashboard.executive.governancePage.subtitle")} ·{" "}
        {t("dashboard.executive.generatedAt", { time: formatDateTime(data.generated_at) })} · {periodText}
      </Typography>

      {/* ── Activity ─────────────────────────────────────────────── */}
      <SectionHeader
        icon="history_edu"
        title={g("dashboard.executive.governancePage.section.activity")}
        hint={g("dashboard.executive.governancePage.sectionHint.activity")}
      />
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} md={6}>
          {/* GOV-01: reviews happened where they were required (D-37). */}
          <ExecutiveKpiTile
            kpi={activity.review_coverage_tile}
            icon="fact_check"
            title={g("dashboard.executive.governancePage.indicator.reviewCoverage")}
            description={g("dashboard.executive.governancePage.reviewCoverage.description")}
            periodText={periodText}
            formatPeriod={label}
            value={pct(activity.review_coverage_tile.value)}
            previousValue={pct(activity.review_coverage_tile.previous.value ?? null)}
          >
            <ReviewCoverageBreakdown figures={activity.review_coverage} />
          </ExecutiveKpiTile>
        </Grid>
      </Grid>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={4}>
          <CountCard label={g("dashboard.executive.governancePage.activity.adrsSigned")}>
            <Typography variant="h4" fontWeight={700}>
              {activity.adrs_signed}
            </Typography>
          </CountCard>
        </Grid>
        <Grid item xs={12} sm={4}>
          <CountCard label={g("dashboard.executive.governancePage.activity.arb")}>
            <Typography variant="body2">
              {g("dashboard.executive.governancePage.activity.arbApproved", { count: activity.arb.approved })}
            </Typography>
            <Typography variant="body2">
              {g("dashboard.executive.governancePage.activity.arbRejected", { count: activity.arb.rejected })}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {g("dashboard.executive.governancePage.activity.arbDeferred", { count: activity.arb.deferred })}
            </Typography>
            <Typography variant="caption" color="text.secondary" component="div" sx={{ mt: 0.5 }}>
              {g("dashboard.executive.governancePage.activity.arbDatingHint")}
            </Typography>
          </CountCard>
        </Grid>
        <Grid item xs={12} sm={4}>
          <CountCard label={g("dashboard.executive.governancePage.activity.exceptions")}>
            <Typography variant="body2">
              {g("dashboard.executive.governancePage.activity.excRequested", { count: activity.exceptions.requested })}
            </Typography>
            <Typography variant="body2">
              {g("dashboard.executive.governancePage.activity.excApprovedActive", { count: activity.exceptions.approved_active })}
            </Typography>
            <Typography variant="body2" color="warning.main">
              {g("dashboard.executive.governancePage.activity.excExpired", { count: activity.exceptions.expired })}
            </Typography>
            <Typography variant="body2">
              {g("dashboard.executive.governancePage.activity.excAwaitingVerification", { count: activity.exceptions.remediation_submitted })}
            </Typography>
            <Typography variant="body2" color="success.main">
              {g("dashboard.executive.governancePage.activity.excRemediated", { count: activity.exceptions.remediated })}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {g("dashboard.executive.governancePage.activity.excRejected", { count: activity.exceptions.rejected })}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {g("dashboard.executive.governancePage.activity.excWithdrawn", { count: activity.exceptions.withdrawn })}
            </Typography>
            <Typography variant="caption" color="text.secondary" component="div" sx={{ mt: 0.5 }}>
              {g("dashboard.executive.governancePage.activity.excCurrentStateHint")}
            </Typography>
          </CountCard>
        </Grid>
      </Grid>

      {coverageDrill && (
        <Box sx={{ mt: 2 }} data-testid="gov01-drilldown">
          <Typography variant="subtitle2" fontWeight={700} gutterBottom>
            {g("dashboard.executive.governancePage.reviewCoverage.drilldownTitle")}
          </Typography>
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{g("dashboard.executive.governancePage.reviewCoverage.col.initiative")}</TableCell>
                  <TableCell>{g("dashboard.executive.governancePage.reviewCoverage.col.state")}</TableCell>
                  <TableCell>{g("dashboard.executive.governancePage.reviewCoverage.col.assessment")}</TableCell>
                  <TableCell>{g("dashboard.executive.governancePage.reviewCoverage.col.reviews")}</TableCell>
                  {coverageDrill.can_assess && <TableCell />}
                </TableRow>
              </TableHead>
              <TableBody>
                {coverageDrill.rows.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>
                      {canAccessPath(user?.permissions, r.path) ? (
                        <Link component={RouterLink} to={r.path} underline="hover" dir="auto">
                          {r.name}
                        </Link>
                      ) : (
                        <bdi>{r.name}</bdi>
                      )}
                    </TableCell>
                    <TableCell>
                      {g(`dashboard.executive.governancePage.state.${r.state}`)}
                      {r.review_in_progress &&
                        ` · ${g("dashboard.executive.governancePage.reviewCoverage.inProgressFlag")}`}
                    </TableCell>
                    <TableCell>
                      {r.assessment ? (
                        <bdi>
                          {r.assessment.criteria_reference}
                          {r.assessment.decided_at ? ` · ${formatDate(r.assessment.decided_at)}` : ""}
                        </bdi>
                      ) : (
                        g("dashboard.executive.governancePage.state.unknown")
                      )}
                    </TableCell>
                    <TableCell>
                      {(r.reviews ?? []).map((rv) => (
                        <Box key={rv.id}>
                          <bdi>{rv.title}</bdi> · {rv.status}
                        </Box>
                      ))}
                      {(r.signed_adrs ?? []).length > 0 && (
                        <Typography variant="caption" color="text.secondary" component="div">
                          {g("dashboard.executive.governancePage.reviewCoverage.adrContext", {
                            count: r.signed_adrs!.length,
                          })}
                        </Typography>
                      )}
                    </TableCell>
                    {coverageDrill.can_assess && (
                      <TableCell>
                        <Button size="small" onClick={() => setAssessing({ id: r.id, name: r.name })}>
                          {g("dashboard.executive.governancePage.applicability.assess")}
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Box>
      )}
      <AssessApplicabilityDialog
        initiative={assessing}
        onClose={() => setAssessing(null)}
        onSaved={() => {
          setAssessing(null);
          setAssessKey((n) => n + 1);
        }}
      />

      {/* ── Effectiveness ────────────────────────────────────────── */}
      <SectionHeader
        icon="rule"
        title={g("dashboard.executive.governancePage.section.effectiveness")}
        hint={g("dashboard.executive.governancePage.sectionHint.effectiveness")}
      />
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <ExecutiveKpiTile
            kpi={compliance}
            icon="verified"
            title={g("dashboard.executive.governancePage.compliance.title")}
            description={g("dashboard.executive.governancePage.compliance.description")}
            periodText={periodText}
            formatPeriod={label}
            value={pct(compliance.value)}
          >
            {/* Coverage is shown beside compliance, never multiplied into it. */}
            {coverage.status === "ok" ? (
              <Typography variant="body2" fontWeight={700} data-testid="assessment-coverage">
                {g("dashboard.executive.governancePage.coverage.value", {
                  assessed: coverage.assessed,
                  total: coverage.population,
                  pct: pct(coverage.percentage) ?? "—",
                })}
              </Typography>
            ) : (
              <Typography variant="caption" color="text.secondary" data-testid="assessment-coverage">
                {g("dashboard.executive.governancePage.coverage.unavailable")}
              </Typography>
            )}
          </ExecutiveKpiTile>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <ResolutionCard resolution={effectiveness.exception_resolution} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <ExecutiveKpiTile
            kpi={effectiveness.decision_implementation_tile}
            icon="task_alt"
            title={g("dashboard.executive.governancePage.indicator.decisionImplementation")}
            description={g("dashboard.executive.governancePage.implementation.description")}
            periodText={periodText}
            formatPeriod={label}
            value={pct(effectiveness.decision_implementation_tile.value)}
            previousValue={pct(effectiveness.decision_implementation_tile.previous.value ?? null)}
          >
            <ImplementationBreakdown implementation={effectiveness.decision_implementation} />
          </ExecutiveKpiTile>
        </Grid>
      </Grid>

      <Box sx={{ mt: 2 }}>
        <TurnaroundCard turnaround={effectiveness.turnaround} />
      </Box>

      {/* The records behind the GOV-03 gap, under the standards permission. */}
      {drill && (
        <Box sx={{ mt: 2 }} data-testid="gov03-drilldown">
          <Typography variant="subtitle2" fontWeight={700} gutterBottom>
            {g("dashboard.executive.governancePage.drilldown.title")}
          </Typography>
          {drill.status !== "ok" || drill.rows.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {g("dashboard.executive.governancePage.drilldown.empty")}
            </Typography>
          ) : (
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{g("dashboard.executive.governancePage.drilldown.col.card")}</TableCell>
                    <TableCell>{g("dashboard.executive.governancePage.drilldown.col.standard")}</TableCell>
                    <TableCell>{g("dashboard.executive.governancePage.drilldown.col.via")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {drill.rows.map((r) => (
                    <TableRow key={`${r.card_id}:${r.standard_name}`}>
                      <TableCell>
                        {canAccessPath(user?.permissions, r.path) ? (
                          <Link component={RouterLink} to={r.path} underline="hover" dir="auto">
                            {r.card_name}
                          </Link>
                        ) : (
                          <bdi>{r.card_name}</bdi>
                        )}
                      </TableCell>
                      <TableCell dir="auto">{r.standard_name}</TableCell>
                      <TableCell>
                        {r.via === "application" && r.component_name
                          ? g("dashboard.executive.governancePage.drilldown.viaComponent", { name: r.component_name })
                          : g("dashboard.executive.governancePage.drilldown.viaDirect")}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          )}
        </Box>
      )}

      {/* ── Impact ───────────────────────────────────────────────── */}
      <SectionHeader
        icon="trending_up"
        title={g("dashboard.executive.governancePage.section.impact")}
        hint={g("dashboard.executive.governancePage.sectionHint.impact")}
      />
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          {/* RSK-01: current state, from explicit governance links only (D-42). */}
          <ExecutiveKpiTile
            kpi={data.impact.architecture_risk_tile}
            icon="warning"
            title={g("dashboard.executive.governancePage.indicator.architectureRisks")}
            description={g("dashboard.executive.governancePage.architectureRisks.description")}
            periodText={periodText}
            formatPeriod={label}
            value={data.impact.architecture_risk_tile.value ?? undefined}
            previousValue={
              data.impact.architecture_risk_tile.previous.value != null
                ? String(data.impact.architecture_risk_tile.previous.value)
                : null
            }
          >
            <ArchitectureRiskBreakdown figures={data.impact.architecture_risks} />
          </ExecutiveKpiTile>
        </Grid>
        <Grid item xs={12} sm={6} md={2}>
          <NotAvailableTile
            label={g("dashboard.executive.governancePage.indicator.riskReduction")}
            reason={reason("riskReduction")}
          />
        </Grid>
        <Grid item xs={12}>
          <GovernedDeliveryCard delivery={data.impact.governed_delivery} />
        </Grid>
        {(["businessValue"] as const).map((key) => (
          <Grid item xs={12} sm={6} md={2} key={key}>
            <NotAvailableTile
              label={g(`dashboard.executive.governancePage.indicator.${key}`)}
              reason={reason(key)}
            />
          </Grid>
        ))}
      </Grid>

      {riskDrill && (
        <Box sx={{ mt: 2 }} data-testid="rsk01-drilldown">
          <Typography variant="subtitle2" fontWeight={700} gutterBottom>
            {g("dashboard.executive.governancePage.architectureRisks.drilldownTitle")}
          </Typography>
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{g("dashboard.executive.governancePage.architectureRisks.col.risk")}</TableCell>
                  <TableCell>{g("dashboard.executive.governancePage.architectureRisks.col.status")}</TableCell>
                  <TableCell>{g("dashboard.executive.governancePage.architectureRisks.col.records")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {riskDrill.rows.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>
                      {canAccessPath(user?.permissions, r.path) ? (
                        <Link component={RouterLink} to={r.path} underline="hover" dir="auto">
                          {r.reference} — {r.title}
                        </Link>
                      ) : (
                        <bdi>
                          {r.reference} — {r.title}
                        </bdi>
                      )}
                    </TableCell>
                    <TableCell>
                      {r.status} · {r.level}
                      {r.escalated && ` · ${g("dashboard.executive.governancePage.architectureRisks.escalatedFlag")}`}
                    </TableCell>
                    <TableCell>
                      {r.records.map((rec) => (
                        <Box key={`${rec.instrument}:${rec.record_id}`}>
                          {canAccessPath(user?.permissions, rec.path.split("?")[0]) ? (
                            <Link component={RouterLink} to={rec.path} underline="hover" dir="auto">
                              {rec.label}
                            </Link>
                          ) : (
                            <bdi>{rec.label}</bdi>
                          )}
                        </Box>
                      ))}
                      {r.records_withheld > 0 && (
                        <Typography variant="caption" color="text.secondary">
                          {g("dashboard.executive.governancePage.architectureRisks.withheld", {
                            count: r.records_withheld,
                          })}
                        </Typography>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Box>
      )}

      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 3 }}>
        {g("dashboard.executive.governancePage.footnote")}
      </Typography>
    </Box>
  );
}

const GOV_STATES: GovernanceState[] = ["governed", "ungoverned", "exempt", "unknown"];

/**
 * The GOV-01 breakdown (D-37, I-59): every group of the population apart —
 * requiring review, completed, awaiting (of which in progress), exempt and
 * undetermined — with assessment coverage. Undetermined is never exempt or
 * compliant.
 */
function ReviewCoverageBreakdown({ figures }: { figures: ReviewCoverageFigures }) {
  const { t } = useTranslation("common");
  const k = (key: string) => `dashboard.executive.governancePage.reviewCoverage.${key}`;
  return (
    <Box data-testid="gov01-breakdown">
      <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 0.5 }}>
        {t(k("label"))}
      </Typography>
      <Typography variant="body2">{t(k("requiring"), { count: figures.requiring_review })}</Typography>
      <Typography variant="body2" color="success.main">
        {t(k("completed"), { count: figures.review_completed })}
      </Typography>
      <Typography variant="body2" color="warning.main">
        {t(k("awaiting"), { count: figures.awaiting_review, inProgress: figures.review_in_progress })}
      </Typography>
      <Typography variant="body2" color="text.secondary" data-testid="gov01-exempt">
        {t(k("exempt"), { count: figures.exempt })}
      </Typography>
      <Typography variant="body2" color="text.secondary" data-testid="gov01-undetermined">
        {t(k("undetermined"), { count: figures.undetermined })}
      </Typography>
      <Typography variant="caption" fontWeight={700} component="div" sx={{ mt: 0.5 }}>
        {t(k("assessmentCoverage"), {
          assessed: figures.assessment_coverage.assessed,
          total: figures.assessment_coverage.population,
          pct: pct(figures.assessment_coverage.percentage) ?? "—",
        })}
      </Typography>
    </Box>
  );
}

/**
 * GOV-09 (D-37, D-20, I-61): delivery health of the four governance groups
 * side by side. Only governed and ungoverned are compared; a rate is shown
 * only when at least five initiatives of the group reported; the difference
 * is an association, never an effect of governance.
 */
function GovernedDeliveryCard({ delivery }: { delivery: GovernedDelivery }) {
  const { t } = useTranslation("common");
  const k = (key: string) => `dashboard.executive.governancePage.governedDelivery.${key}`;
  const comparison = delivery.comparison;
  return (
    <Card variant="outlined" data-testid="gov09-delivery">
      <CardContent>
        <Typography variant="subtitle2" fontWeight={700}>
          {t("dashboard.executive.governancePage.indicator.governedDelivery")}
        </Typography>
        <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1 }}>
          {t(k("label"), { min: delivery.minimum_group_size })}
        </Typography>
        {delivery.status !== "ok" ? (
          <Typography variant="body2" color="text.secondary">
            {t(k("noGroups"))}
          </Typography>
        ) : (
          <>
            <Box
              sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(4, 1fr)" }, gap: 1.5 }}
            >
              {GOV_STATES.map((state) => {
                const group = delivery.groups[state];
                return (
                  <Box key={state} data-testid={`gov09-${state}`}>
                    <Typography variant="body2" fontWeight={700}>
                      {t(`dashboard.executive.governancePage.state.${state}`)}
                    </Typography>
                    <Typography variant="body2">
                      {t(k("inFlight"), { count: group.in_flight })}
                    </Typography>
                    <Typography variant="body2">
                      {group.suppressed
                        ? t(k("suppressed"), { min: delivery.minimum_group_size })
                        : t(k("onTrack"), { pct: pct(group.on_track_pct) ?? "—" })}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" component="div">
                      {t(k("coverage"), {
                        reported: group.reported,
                        total: group.in_flight,
                        pct: pct(group.reporting_coverage) ?? "—",
                      })}
                    </Typography>
                    {(state === "exempt" || state === "unknown") && (
                      <Typography variant="caption" color="text.secondary" component="div">
                        {t(k("notCompared"))}
                      </Typography>
                    )}
                  </Box>
                );
              })}
            </Box>
            <Box data-testid="gov09-comparison" sx={{ mt: 1.5, pt: 1, borderTop: 1, borderColor: "divider" }}>
              <Typography variant="body2" fontWeight={700}>
                {comparison && comparison.status === "ok"
                  ? t(k("difference"), { points: comparison.difference_pct_points })
                  : t(k("comparisonSuppressed"), { min: delivery.minimum_group_size })}
              </Typography>
              <Typography variant="caption" color="text.secondary" component="div">
                {t(k("association"))}
              </Typography>
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * The architecture-risk breakdown under RSK-01 (D-42, I-53): every risk is
 * counted once in total / open / escalated / mitigated; the record-type and
 * approved-record figures overlap and are labelled as not adding up.
 */
function ArchitectureRiskBreakdown({ figures }: { figures: ArchitectureRiskFigures }) {
  const { t } = useTranslation("common");
  const k = (key: string) => `dashboard.executive.governancePage.architectureRisks.${key}`;
  if (figures.status !== "ok") return null;
  const byType = figures.by_record_type!;
  return (
    <Box data-testid="rsk01-breakdown">
      {/* Always visible, not only in the tooltip (D-42.7). */}
      <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 0.5 }} data-testid="rsk01-label">
        {t(k("label"))}
      </Typography>
      <Typography variant="body2" data-testid="rsk01-total">
        {t(k("total"), { count: figures.total })}
      </Typography>
      <Typography variant="body2">{t(k("open"), { count: figures.open })}</Typography>
      <Typography variant="body2" color="error.main">
        {t(k("escalated"), { count: figures.escalated })}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {t(k("mitigated"), { count: figures.mitigated })}
      </Typography>
      <Box data-testid="rsk01-overlap" sx={{ mt: 1, pt: 1, borderTop: 1, borderColor: "divider" }}>
        <Typography variant="caption" fontWeight={700} component="div">
          {t(k("byTypeHeading"))}
        </Typography>
        <Typography variant="body2">
          {t(k("byType"), { adr: byType.adr, arb: byType.arb, exception: byType.exception })}
        </Typography>
        <Typography variant="body2">
          {t(k("approved"), { count: figures.linked_to_approved!.count })}
        </Typography>
        <Typography variant="caption" color="text.secondary" component="div">
          {t(k("overlapHint"))}
        </Typography>
      </Box>
      <Typography variant="caption" color="text.secondary" component="div" sx={{ mt: 1 }}>
        {t(k("basisHint"))}
      </Typography>
    </Box>
  );
}

const IMPLEMENTATION_OUTCOMES = [
  "verified_on_time",
  "verified_late",
  "awaiting_verification",
  "in_progress",
  "no_plan",
] as const;

/**
 * The GOV-05 breakdown under its KPI tile (D-32, D-41): every outcome of the
 * decisions due apart from the verified-on-time numerator, performance against
 * revised deadlines separately, and the decisions the rate cannot time (no
 * deadline) disclosed with the planning coverage — never hidden.
 */
function ImplementationBreakdown({ implementation }: { implementation: GovernanceImplementation }) {
  const { t } = useTranslation("common");
  const k = (key: string) => `dashboard.executive.governancePage.implementation.${key}`;
  const coverage = implementation.planning_coverage;
  return (
    <Box data-testid="gov05-implementation">
      <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 0.5 }}>
        {t(k("basis"), { count: implementation.eligible })}
      </Typography>
      {IMPLEMENTATION_OUTCOMES.map((o) => (
        <Typography variant="body2" key={o} data-testid={`gov05-${o}`}>
          {t(k(`outcome.${o}`), { count: implementation.outcomes[o] })}
        </Typography>
      ))}
      {implementation.revised_deadlines.revised > 0 && (
        <Typography variant="body2" color="text.secondary" data-testid="gov05-revised">
          {t(k("revised"), {
            count: implementation.revised_deadlines.revised,
            verified: implementation.revised_deadlines.verified_within_revised,
          })}
        </Typography>
      )}
      <Box data-testid="gov05-coverage" sx={{ mt: 1, pt: 1, borderTop: 1, borderColor: "divider" }}>
        <Typography variant="caption" fontWeight={700} component="div">
          {t(k("coverage"), {
            planned: coverage.planned,
            total: coverage.approved_decisions,
            pct: pct(coverage.percentage) ?? "—",
          })}
        </Typography>
        <Typography variant="body2" color="warning.main" data-testid="gov05-excluded">
          {t(k("noDeadline"), { count: implementation.excluded.no_deadline })}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t(k("noActions"), { count: coverage.without_actions })}
        </Typography>
        <Typography variant="caption" color="text.secondary" component="div">
          {t(k("coverageHint"))}
        </Typography>
      </Box>
    </Box>
  );
}

const INSTRUMENTS = ["adr", "arb", "exception"] as const;

const OUTCOMES = [
  "remediated_on_time",
  "remediated_late",
  "awaiting_verification",
  "expired_unresolved",
  "withdrawn",
  "rejected",
] as const;

/**
 * GOV-04 exception resolution (D-40, I-26): the share of due exceptions whose
 * remediation was verified on or before expiry. Every other outcome — late
 * remediation, awaiting verification, expired unresolved, and the
 * administrative closes (withdrawn, rejected) — is listed apart and never
 * counted as remediation.
 */
function ResolutionCard({ resolution }: { resolution: GovernanceResolution }) {
  const { t } = useTranslation("common");
  const k = (key: string) => `dashboard.executive.governancePage.resolution.${key}`;
  const ok = resolution.status === "ok" && resolution.value != null;
  return (
    <Card
      variant="outlined"
      data-testid="gov04-resolution"
      sx={{ height: "100%", borderTop: 3, borderTopColor: ok ? STATUS_COLORS.info : STATUS_COLORS.neutral }}
    >
      <CardContent>
        <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.5 }}>
          {t("dashboard.executive.governancePage.indicator.exceptionResolution")}
        </Typography>
        {ok ? (
          <Typography variant="h5" fontWeight={700}>
            {pct(resolution.value ?? null)}
          </Typography>
        ) : (
          <>
            <Typography variant="h6" color="text.secondary" fontWeight={700}>
              {t("dashboard.executive.ceo.notAvailable")}
            </Typography>
            <Typography variant="caption" color="text.secondary" component="div">
              {t(k("noEligible"))}
            </Typography>
          </>
        )}
        <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 0.5 }}>
          {t(k("basis"), { count: resolution.eligible })}
        </Typography>
        <Typography variant="caption" fontWeight={700} component="div">
          {t(k("exceptionsHeading"))}
        </Typography>
        {OUTCOMES.map((o) => (
          <Typography variant="body2" key={o} data-testid={`gov04-${o}`}>
            {t(k(`outcome.${o}`), { count: resolution.outcomes[o] })}
          </Typography>
        ))}
        {resolution.not_recorded > 0 && (
          <Typography variant="body2" color="text.secondary">
            {t(k("notRecorded"), { count: resolution.not_recorded })}
          </Typography>
        )}
        <Typography variant="caption" color="text.secondary" component="div" sx={{ mt: 0.5 }}>
          {t(k("rejectedRequests"), { count: resolution.rejected_requests })}
        </Typography>
        {resolution.approval_cycles && resolution.approval_cycles.eligible > 0 && (
          <Box data-testid="gov04-cycles" sx={{ mt: 1, pt: 1, borderTop: 1, borderColor: "divider" }}>
            <Typography variant="caption" fontWeight={700} component="div">
              {t(k("cyclesHeading"), { count: resolution.approval_cycles.eligible })}
            </Typography>
            <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 0.5 }}>
              {t(k("cyclesHint"))}
            </Typography>
            {OUTCOMES.filter((o) => resolution.approval_cycles!.outcomes[o] > 0).map((o) => (
              <Typography variant="body2" key={o} data-testid={`gov04-cycle-${o}`}>
                {t(k(`outcome.${o}`), { count: resolution.approval_cycles!.outcomes[o] })}
              </Typography>
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * GOV-07 elapsed calendar days, one row per instrument and never pooled
 * (Batch 3.2, D-35), with governance-controlled time beside each (D-39):
 * only waits explicitly attributed to the requester or an external dependency
 * are left out, and a record that cannot be timed is counted by cause.
 * Decisions whose lifecycle was not recorded are never timed from a
 * reconstructed date. Working days (D-28, D-38) are shown per instrument
 * only while the business calendar is confirmed for the period.
 */
function TurnaroundCard({ turnaround }: { turnaround: GovernanceTurnaround }) {
  const { t } = useTranslation("common");
  const k = (key: string) => `dashboard.executive.governancePage.turnaround.${key}`;
  return (
    <Card variant="outlined" data-testid="gov07-turnaround">
      <CardContent>
        <Typography variant="subtitle2" fontWeight={700}>
          {t(k("title"))}
        </Typography>
        <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1 }}>
          {t(k("description"))}
        </Typography>
        <Grid container spacing={2}>
          {INSTRUMENTS.map((key) => (
            <Grid item xs={12} md={4} key={key}>
              <ElapsedFigure label={t(k(`instrument.${key}`))} figure={turnaround.instruments[key]} />
              <ProcessingFigure figure={turnaround.processing_time.instruments[key]} instrument={key} />
              {turnaround.working_days.status === "ok" && (
                <WorkingDaysFigure figure={turnaround.working_days.instruments[key]} instrument={key} />
              )}
            </Grid>
          ))}
        </Grid>
        <Typography variant="caption" color="text.secondary" component="div" sx={{ mt: 1.5 }}>
          {t(k("processingHint"))}
        </Typography>
        {turnaround.working_days.status === "not_available" && (
          <Typography variant="caption" color="text.secondary" component="div" data-testid="gov07-working-days-na">
            {turnaround.working_days.reason.fiscal_years?.length
              ? t(k("workingDaysUnconfirmed"), {
                  years: turnaround.working_days.reason.fiscal_years.map((y) => `FY${y}`).join(", "),
                })
              : t(k("workingDays"))}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

function WorkingDaysFigure({ figure, instrument }: { figure: GovernanceWorkingDaysFigure; instrument: string }) {
  const { t } = useTranslation("common");
  const k = (key: string) => `dashboard.executive.governancePage.turnaround.workingDaysFigure.${key}`;
  const untimed = figure.not_computable.calendar_not_confirmed ?? 0;
  return (
    <Box data-testid={`gov07-working-days-${instrument}`} sx={{ mt: 1, pt: 1, borderTop: 1, borderColor: "divider" }}>
      {figure.status === "ok" ? (
        <>
          <Typography variant="body2" fontWeight={700}>
            {t(k("median"), { days: figure.median_days })}
          </Typography>
          <Typography variant="body2">{t(k("max"), { days: figure.max_days })}</Typography>
        </>
      ) : (
        <Typography variant="body2" color="text.secondary">
          {t(k("notAvailable"))}
        </Typography>
      )}
      {untimed > 0 && (
        <Typography variant="body2" color="text.secondary">
          {t(k("unconfirmedSpan"), { count: untimed })}
        </Typography>
      )}
    </Box>
  );
}

function ElapsedFigure({ label, figure }: { label: string; figure: GovernanceElapsed }) {
  const { t } = useTranslation("common");
  const k = (key: string) => `dashboard.executive.governancePage.turnaround.${key}`;
  const notRecordedKey =
    figure.not_recorded_temporal === "current_state" ? "notRecordedCurrent" : "notRecorded";
  return (
    <Box data-testid={`gov07-${figure.basis}`}>
      <Typography variant="body2" fontWeight={700}>
        {label}
      </Typography>
      {figure.status === "ok" ? (
        <>
          <Typography variant="h6" fontWeight={700}>
            {t(k("median"), { days: figure.median_days })}
          </Typography>
          <Typography variant="body2">{t(k("max"), { days: figure.max_days })}</Typography>
          <Typography variant="body2">{t(k("decisions"), { count: figure.decisions })}</Typography>
        </>
      ) : (
        <Typography variant="body2" color="text.secondary">
          {t("dashboard.executive.ceo.notAvailable")} · {t(k("noDecisions"))}
        </Typography>
      )}
      {figure.not_recorded > 0 && (
        <Typography variant="body2" color="text.secondary">
          {t(k(notRecordedKey), { count: figure.not_recorded })}
        </Typography>
      )}
      <Typography variant="caption" color="text.secondary" component="div">
        {t(k(`basis.${figure.basis}`))}
      </Typography>
    </Box>
  );
}

function ProcessingFigure({ figure, instrument }: { figure: GovernanceProcessing; instrument: string }) {
  const { t } = useTranslation("common");
  const k = (key: string) => `dashboard.executive.governancePage.turnaround.processing.${key}`;
  const causes = Object.entries(figure.not_computable).filter(([, n]) => n > 0);
  return (
    <Box data-testid={`gov07-processing-${instrument}`} sx={{ mt: 1, pt: 1, borderTop: 1, borderColor: "divider" }}>
      {figure.status === "ok" ? (
        <>
          <Typography variant="body2" fontWeight={700}>
            {t(k("median"), { days: figure.median_days })}
          </Typography>
          <Typography variant="body2">{t(k("max"), { days: figure.max_days })}</Typography>
        </>
      ) : (
        <Typography variant="body2" color="text.secondary">
          {t(k("notAvailable"))}
        </Typography>
      )}
      {causes.map(([cause, n]) => (
        <Typography variant="caption" color="text.secondary" component="div" key={cause}>
          {t(k(`cause.${cause}`), { count: n })}
        </Typography>
      ))}
    </Box>
  );
}

/** A tile that reads *Not available* with the plain reason it needs. */
function NotAvailableTile({ label, reason }: { label: string; reason: string }) {
  const { t } = useTranslation("common");
  return (
    <Card variant="outlined" sx={{ height: "100%", borderTop: 3, borderTopColor: STATUS_COLORS.neutral }}>
      <CardContent>
        <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.5 }}>
          {label}
        </Typography>
        <Typography variant="h6" color="text.secondary" fontWeight={700}>
          {t("dashboard.executive.ceo.notAvailable")}
        </Typography>
        <Typography variant="caption" color="text.secondary" component="div">
          {reason}
        </Typography>
      </CardContent>
    </Card>
  );
}
