import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { formatMoney } from "@/features/benefits/benefitFormat";
import { useAuthContext } from "@/hooks/AuthContext";
import { useApiQuery } from "@/hooks/useApiQuery";
import { canAccessPath } from "@/lib/routePermissions";
import type { BenefitCurrencySummary, BenefitOutcomeGroup, ExecutiveBenefitsData } from "@/types";
import { periodLabel } from "./executiveFormat";
import { useExecutivePeriod } from "./useExecutivePeriod";

function Section({
  title,
  hint,
  chip,
  children,
}: {
  title: string;
  hint?: string;
  chip?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5, flexWrap: "wrap" }}>
          <Typography variant="subtitle1" fontWeight={700} sx={{ flex: 1 }}>
            {title}
          </Typography>
          {chip}
        </Box>
        {hint && (
          <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1.5 }}>
            {hint}
          </Typography>
        )}
        {children}
      </CardContent>
    </Card>
  );
}

function Figure({ label, value, caption }: { label: string; value: ReactNode; caption?: string }) {
  return (
    <Box sx={{ mb: 1.5 }}>
      <Typography variant="caption" color="text.secondary" component="div">
        {label}
      </Typography>
      <Typography variant="h6" fontWeight={700} component="div">
        {value}
      </Typography>
      {caption && (
        <Typography variant="caption" color="text.secondary" component="div">
          {caption}
        </Typography>
      )}
    </Box>
  );
}

/**
 * Benefits realisation (Phase 4 Batches 4.2 and 4.3): planned, reported and
 * Finance-confirmed value side by side and never added together; the
 * rationalization run-rate forecast apart (D-31); attribution and the
 * governance link as Finance recorded them (D-14); non-financial outcomes
 * apart, KPI-verified and assessed never blended (D-43). ROI stays Not
 * Available until Batch 4.4.
 */
export default function ExecutiveBenefits() {
  const { t, i18n } = useTranslation("common");
  const { user } = useAuthContext();
  const { period } = useExecutivePeriod();
  const path = period
    ? `/reports/executive/benefits?period=${encodeURIComponent(period)}`
    : "/reports/executive/benefits";
  const { data, error, loading } = useApiQuery<ExecutiveBenefitsData>(path);
  const k = (key: string, opts?: Record<string, unknown>) =>
    t(`dashboard.executive.benefitsPage.${key}`, opts ?? {});

  if (error) return <Alert severity="error">{error.message || t("errors.generic")}</Alert>;
  if (!data) return loading ? <LinearProgress /> : null;
  if (period && data.period.key !== period) return <LinearProgress />;

  const money = (v: number, currency: string) => <bdi>{formatMoney(v, currency, i18n.language)}</bdi>;
  const canRegister = canAccessPath(user?.permissions, "/benefits");
  const financial = data.financial;

  const currencyBlock = (c: BenefitCurrencySummary) => (
    <Box key={c.currency} sx={{ mb: 3 }}>
      {financial.status === "ok" && financial.mixed_currencies && (
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          {c.currency}
        </Typography>
      )}
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Section
            title={k("planned")}
            hint={k("plannedHint")}
            chip={<Chip size="small" variant="outlined" color="warning" label={t("dashboard.executive.provenance.forecast")} />}
          >
            {(["validated", "planned"] as const).map((status) => (
              <Box key={status} sx={{ mb: 1 }}>
                <Typography variant="caption" fontWeight={700} component="div">
                  {k(`plannedStatus.${status}`)}
                </Typography>
                {(["annual", "one_time"] as const).map((rec) => (
                  <Typography key={rec} variant="body2">
                    {t(`benefits.recurrence.${rec}`)}: {money(c.planned[status][rec].total, c.currency)}{" "}
                    <Typography component="span" variant="caption" color="text.secondary">
                      ({k("benefitCount", { count: c.planned[status][rec].count })})
                    </Typography>
                  </Typography>
                ))}
              </Box>
            ))}
          </Section>
        </Grid>
        <Grid item xs={12} md={4}>
          <Section
            title={k("reported")}
            hint={k("reportedHint")}
            chip={<Chip size="small" variant="outlined" color="info" label={k("reportedChip")} />}
          >
            <Figure
              label={k("reported")}
              value={money(c.reported.total, c.currency)}
              caption={k("actualCount", { count: c.reported.count })}
            />
          </Section>
        </Grid>
        <Grid item xs={12} md={4}>
          <Section
            title={k("confirmed")}
            hint={k("confirmedHint", { fy: data.fiscal_year })}
            chip={<Chip size="small" variant="outlined" color="success" label={k("confirmedChip")} />}
          >
            <Figure
              label={k("confirmedCash")}
              value={money(c.confirmed_cash.total, c.currency)}
              caption={k("actualCount", { count: c.confirmed_cash.count })}
            />
            <Figure
              label={k("confirmedAvoidance")}
              value={money(c.confirmed_avoidance.total, c.currency)}
              caption={k("actualCount", { count: c.confirmed_avoidance.count })}
            />
            <Figure
              label={k("rate")}
              value={c.rate.status === "ok" && c.rate.value !== null ? `${c.rate.value}%` : k("notAvailable")}
              caption={c.rate.status === "ok" ? k("rateHint") : k("rateNa")}
            />
          </Section>
        </Grid>
        <Grid item xs={12}>
          <Section title={k("attribution")} hint={k("attributionHint")}>
            <Box sx={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
              <Figure label={k("direct")} value={money(c.attribution.direct, c.currency)} />
              <Figure label={k("contributing")} value={money(c.attribution.contributing, c.currency)} />
              <Figure label={k("unallocated")} value={money(c.attribution.unallocated, c.currency)} />
            </Box>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {k("governance", {
                linked: c.governance.linked,
                total: c.governance.linked + c.governance.not_linked,
              })}
            </Typography>
            <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1 }}>
              {k("governanceHint")}
            </Typography>
            {c.by_initiative.length > 0 && (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{k("initiative")}</TableCell>
                    <TableCell align="right">{k("direct")}</TableCell>
                    <TableCell align="right">{k("contributing")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {c.by_initiative.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell>
                        <Link component={RouterLink} to={row.path}>
                          {row.name}
                        </Link>
                      </TableCell>
                      <TableCell align="right">{money(row.direct, c.currency)}</TableCell>
                      <TableCell align="right">{money(row.contributing, c.currency)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Section>
        </Grid>
      </Grid>
    </Box>
  );

  const outcomeGroup = (key: "productivity" | "non_financial", group: BenefitOutcomeGroup) => (
    <Grid item xs={12} md={6} key={key}>
      <Section title={k(key === "productivity" ? "productivity" : "nonFinancial")}>
        {group.items.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {k("none")}
          </Typography>
        ) : (
          <>
            <Typography variant="caption" fontWeight={700} component="div">
              {k("verified")}
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {Object.entries(group.kpi).map(([s, n]) => `${k(`state.${s}`)}: ${n}`).join(" · ") || "—"}
            </Typography>
            <Typography variant="caption" fontWeight={700} component="div">
              {k("assessed")}
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              {Object.entries(group.qualitative).map(([s, n]) => `${k(`state.${s}`)}: ${n}`).join(" · ") || "—"}
            </Typography>
            <Table size="small">
              <TableBody>
                {group.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      {canRegister ? (
                        <Link component={RouterLink} to={`/benefits?benefit=${item.id}`}>
                          {item.reference}
                        </Link>
                      ) : (
                        item.reference
                      )}
                    </TableCell>
                    <TableCell dir="auto">{item.title}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        variant="outlined"
                        color={item.evidence === "verified_kpi" ? "success" : "default"}
                        label={k(item.evidence === "verified_kpi" ? "verifiedChip" : "assessedChip")}
                      />{" "}
                      {k(`state.${item.state}`)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        )}
      </Section>
    </Grid>
  );

  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, flexWrap: "wrap", mb: 2 }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" fontWeight={700}>
            {k("title")}
          </Typography>
          <Typography variant="caption" color="text.secondary" component="div">
            {k("fiscalYear", { fy: periodLabel(`FY${data.fiscal_year}`, data.fiscal_year_start, t) })}
          </Typography>
        </Box>
        {canRegister && (
          <Link component={RouterLink} to="/benefits" variant="body2">
            {k("openRegister")}
          </Link>
        )}
      </Box>
      {data.quarter_selected && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {k("quarterNote")}
        </Alert>
      )}

      {financial.status === "restricted" ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          {k("restricted", {
            count: data.counts.benefits,
            confirmed: data.counts.actuals_confirmed,
            awaiting: data.counts.actuals_awaiting_finance,
          })}
        </Alert>
      ) : financial.currencies.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {k("noFinancial")}
        </Typography>
      ) : (
        <>
          {financial.mixed_currencies && (
            <Alert severity="info" sx={{ mb: 2 }}>
              {k("mixed")}
            </Alert>
          )}
          {financial.currencies.map(currencyBlock)}
        </>
      )}

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Section
            title={k("forecast")}
            hint={k("forecastHint")}
            chip={<Chip size="small" variant="outlined" color="info" label={t("dashboard.executive.ceo.currentState")} />}
          >
            {data.run_rate_forecast.status === "ok" ? (
              <Figure
                label={k("forecastValue")}
                value={money(data.run_rate_forecast.total ?? 0, data.run_rate_forecast.currency ?? "")}
                caption={k("forecastCount", { count: data.run_rate_forecast.applications_counted ?? 0 })}
              />
            ) : (
              <Typography variant="body2" color="text.secondary">
                {t("benefits.amountRestricted")}
              </Typography>
            )}
          </Section>
        </Grid>
        <Grid item xs={12} md={6}>
          <Section title={k("roi")}>
            <Typography variant="h6" fontWeight={700}>
              {k("notAvailable")}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {k("roiNa")}
            </Typography>
          </Section>
        </Grid>
      </Grid>

      <Typography variant="subtitle1" fontWeight={700}>
        {k("outcomes")}
      </Typography>
      <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1.5 }}>
        {k("outcomesHint")}
      </Typography>
      <Grid container spacing={2}>
        {outcomeGroup("productivity", data.outcomes.groups.productivity)}
        {outcomeGroup("non_financial", data.outcomes.groups.non_financial)}
      </Grid>
    </Box>
  );
}
