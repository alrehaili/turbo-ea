import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
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
import { STATUS_COLORS } from "@/theme/tokens";
import type { ExecutiveGovernanceData, GovernanceDrilldown } from "@/types";
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
            <Typography variant="body2" color="text.secondary">
              {g("dashboard.executive.governancePage.activity.excRejected", { count: activity.exceptions.rejected })}
            </Typography>
            <Typography variant="caption" color="text.secondary" component="div" sx={{ mt: 0.5 }}>
              {g("dashboard.executive.governancePage.activity.excCurrentStateHint")}
            </Typography>
          </CountCard>
        </Grid>
      </Grid>

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
        {(["exceptionResolution", "decisionImplementation", "turnaround"] as const).map((key) => (
          <Grid item xs={12} sm={6} md={3} key={key}>
            <NotAvailableTile
              label={g(`dashboard.executive.governancePage.indicator.${key}`)}
              reason={reason(key)}
            />
          </Grid>
        ))}
      </Grid>

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
        {(["architectureRisks", "governedDelivery", "businessValue"] as const).map((key) => (
          <Grid item xs={12} sm={4} key={key}>
            <NotAvailableTile
              label={g(`dashboard.executive.governancePage.indicator.${key}`)}
              reason={reason(key)}
            />
          </Grid>
        ))}
      </Grid>

      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 3 }}>
        {g("dashboard.executive.governancePage.footnote")}
      </Typography>
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
