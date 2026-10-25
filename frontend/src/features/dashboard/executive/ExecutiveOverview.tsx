import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import LinearProgress from "@mui/material/LinearProgress";
import Link from "@mui/material/Link";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import RestrictedAmount from "@/features/ppm/RestrictedAmount";
import { useAuthContext } from "@/hooks/AuthContext";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useDateFormat } from "@/hooks/useDateFormat";
import { canAccessPath } from "@/lib/routePermissions";
import { SEVERITY_COLORS } from "@/theme/tokens";
import type { ExecutiveDecisionItem, ExecutiveKpi, ExecutiveKpiSlot, ExecutiveOverviewData } from "@/types";
import ExecutiveKpiTile from "./ExecutiveKpiTile";
import { formatCompactMoney, pct, periodLabel } from "./executiveFormat";
import { useExecutivePeriod } from "./useExecutivePeriod";

const SLOT_ICONS: Record<ExecutiveKpiSlot, string> = {
  strategy: "flag",
  governance: "gavel",
  delivery: "rocket_launch",
  services: "settings_suggest",
  value: "savings",
  decisions: "priority_high",
};

const TITLE_SX = { minWidth: 0, overflowWrap: "anywhere", textAlign: "start" } as const;

/**
 * One escalation or pipeline record. Titles and owner names are user data in
 * either script, so each is laid out in its own direction (`dir="auto"`) and
 * every meta fragment is a bidi isolate: an English title inside the Arabic
 * page keeps its word order and is truncated at its own end.
 */
export function DecisionItemLine({ item }: { item: ExecutiveDecisionItem }) {
  const { t } = useTranslation(["common", "grc"]);
  const { user } = useAuthContext();
  const { formatDate } = useDateFormat();
  const canOpen = canAccessPath(user?.permissions, item.path.split("?")[0]);
  const label = [item.reference, item.title].filter(Boolean).join(" · ");
  const meta = [
    t(`dashboard.executive.decisionKind.${item.kind}`),
    item.level ? t(`grc:risks.level.${item.level}`) : null,
    item.owner ? t("dashboard.executive.ceo.ownerName", { name: item.owner }) : null,
    item.pending_signatures !== undefined
      ? t("dashboard.executive.ceo.pendingSignatures", { count: item.pending_signatures })
      : null,
    item.due_date ? t("dashboard.executive.ceo.due", { date: formatDate(item.due_date) }) : null,
    item.age_days !== null ? t("dashboard.executive.ceo.age", { count: item.age_days }) : null,
  ].filter(Boolean);
  return (
    <ListItem disableGutters sx={{ display: "block", py: 0.75 }}>
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1, minWidth: 0 }}>
        {item.level && (
          <Box sx={{ width: 8, height: 8, mt: "7px", borderRadius: "50%", flexShrink: 0, bgcolor: SEVERITY_COLORS[item.level as keyof typeof SEVERITY_COLORS] ?? "text.disabled" }} />
        )}
        {/* Titles wrap rather than truncate: on a phone a cut title lost its
            reference number, and in RTL the cut fell at the wrong end. */}
        {canOpen ? (
          <Link component={RouterLink} to={item.path} underline="hover" variant="body2" dir="auto" sx={TITLE_SX}>
            {label}
          </Link>
        ) : (
          <Typography variant="body2" dir="auto" sx={TITLE_SX}>
            {label}
          </Typography>
        )}
      </Box>
      <Typography variant="caption" color="text.secondary" component="div">
        {meta.map((part, i) => (
          <span key={i}>
            {i > 0 && " · "}
            <bdi>{part}</bdi>
          </span>
        ))}
      </Typography>
    </ListItem>
  );
}

/**
 * The attention panel's body. A restricted reader sees the count and why the
 * records are withheld — never an empty panel that reads as "nothing to do".
 */
export function EscalationsPanelBody({ panel }: { panel: ExecutiveOverviewData["escalations_panel"] }) {
  const { t } = useTranslation("common");
  if (panel.status === "disabled") {
    return (
      <Typography variant="body2" color="text.secondary">
        {t("dashboard.executive.moduleDisabled")}
      </Typography>
    );
  }
  if (panel.count === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        {t("dashboard.executive.ceo.panelNone")}
      </Typography>
    );
  }
  if (panel.status === "restricted") {
    return (
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1 }} data-testid="escalations-restricted">
        <MaterialSymbol icon="lock" size={18} />
        <Box>
          <Typography variant="body2" fontWeight={700}>
            {t("dashboard.executive.ceo.panelRestrictedCount", { count: panel.count })}
          </Typography>
          <Typography variant="caption" color="text.secondary" component="div">
            {t("dashboard.executive.ceo.panelRestricted")}
          </Typography>
        </Box>
      </Box>
    );
  }
  return (
    <>
      <List dense disablePadding>
        {panel.items.map((item) => (
          <DecisionItemLine key={`${item.kind}-${item.id}`} item={item} />
        ))}
      </List>
      {panel.more > 0 && (
        <Typography variant="caption" color="text.secondary" component="div">
          {t("dashboard.executive.ceo.panelMore", { count: panel.more })}
        </Typography>
      )}
    </>
  );
}

export default function ExecutiveOverview() {
  const { t, i18n } = useTranslation(["common", "grc"]);
  const { period, setPeriod } = useExecutivePeriod();
  const path = period
    ? `/reports/executive/overview?period=${encodeURIComponent(period)}`
    : "/reports/executive/overview";
  const { data, error, loading } = useApiQuery<ExecutiveOverviewData>(path);
  const { formatDateTime, formatDate } = useDateFormat();

  if (error) {
    // A period that has not started (e.g. a future year chosen on Details) or
    // that the server refuses: say so and offer the way back, not a dead end.
    return (
      <Alert
        severity={period ? "info" : "error"}
        action={
          period ? (
            <Button color="inherit" size="small" onClick={() => setPeriod(null)}>
              {t("dashboard.executive.ceo.showCurrentPeriod")}
            </Button>
          ) : undefined
        }
      >
        {period ? t("dashboard.executive.ceo.periodUnavailable") : error.message || t("errors.generic")}
      </Alert>
    );
  }
  if (!data) return loading ? <LinearProgress /> : null;

  const start = data.fiscal_year_start;
  const label = (key: string) => periodLabel(key, start, t);
  // The previous payload is kept while the next one loads (for the selector's
  // options); its figures belong to another period, so none of them render
  // until the requested period has arrived.
  const pending = loading || (period !== null && data.period.key !== period);
  const shownKey = period ?? data.period.key;
  const periodText = `${label(data.period.key)} · ${t("dashboard.executive.ceo.asOf", { date: formatDate(data.period.as_of) })}`;
  const tile = (slot: ExecutiveKpiSlot): ExecutiveKpi | undefined => data.kpis.find((k) => k.slot === slot);
  const money = (v: number, currency: string) => formatCompactMoney(v, currency, i18n.language);

  const render = (slot: ExecutiveKpiSlot) => {
    const kpi = tile(slot);
    if (!kpi) return null;
    const common = {
      kpi,
      icon: SLOT_ICONS[slot],
      title: t(`dashboard.executive.ceo.slot.${slot}`),
      description: t(`dashboard.executive.ceo.slotHint.${slot}`),
      periodText,
      formatPeriod: label,
    };
    if (slot === "strategy") {
      // Outcomes and execution are shown apart, never combined (D-21).
      const d = kpi.details as {
        totals?: { linked: number; measured: number; on_target: number };
        execution?: { initiatives: number; on_track_pct: number | null };
      };
      return (
        <ExecutiveKpiTile
          {...common}
          value={t("dashboard.executive.ceo.strategyValue", {
            onTarget: d.totals?.on_target ?? 0,
            measured: d.totals?.measured ?? 0,
          })}
        >
          {d.totals && d.totals.linked > 0 && (
            <Typography variant="body2" fontWeight={700} data-testid="strategy-coverage">
              {t("dashboard.executive.ceo.strategyCoverage", {
                measured: d.totals.measured,
                linked: d.totals.linked,
              })}
            </Typography>
          )}
          {d.execution && d.execution.initiatives > 0 && (
            <Typography variant="caption" color="text.secondary" data-testid="strategy-execution">
              {t("dashboard.executive.ceo.strategyExecution", {
                pct: pct(d.execution.on_track_pct) ?? t("dashboard.executive.ceo.notAvailable"),
                count: d.execution.initiatives,
              })}
            </Typography>
          )}
        </ExecutiveKpiTile>
      );
    }
    if (slot === "delivery") {
      const d = kpi.details as {
        source?: string;
        states?: Record<string, number>;
        excluded?: Record<string, number>;
        staleness_days?: number | null;
        oldest_report_date?: string | null;
      };
      const c = kpi.completeness;
      const missing = c ? c.denominator - c.numerator : 0;
      // Coverage is read beside the health share, never instead of it; the
      // warnings state the actual shortfall, with no threshold of our own.
      const warnings: string[] = [];
      if (c && missing > 0) {
        warnings.push(
          t("dashboard.executive.ceo.coverageGap", { count: missing, total: c.denominator, reported: c.numerator }),
        );
      }
      if (d.source === "ppm_reports" && d.staleness_days == null && c) {
        warnings.push(
          d.oldest_report_date
            ? t("dashboard.executive.ceo.stalenessUnsetOldest", { date: formatDate(d.oldest_report_date) })
            : t("dashboard.executive.ceo.stalenessUnset"),
        );
      }
      return (
        <ExecutiveKpiTile
          {...common}
          value={`${pct(kpi.value)} ${t("dashboard.executive.ceo.onTrackUnit")}`}
          previousValue={pct(kpi.previous.value ?? null)}
        >
          {c && (
            <Typography variant="body2" fontWeight={700} data-testid="delivery-coverage">
              {t("dashboard.executive.ceo.coverageHeadline", {
                pct: pct(c.percentage) ?? "—",
                reported: c.numerator,
                total: c.denominator,
              })}
            </Typography>
          )}
          {warnings.length > 0 && (
            <Alert severity="warning" icon={false} sx={{ py: 0, px: 1, "& .MuiAlert-message": { py: 0.5 } }} data-testid="delivery-warnings">
              {warnings.map((w) => (
                <Typography key={w} variant="caption" component="div">
                  {w}
                </Typography>
              ))}
            </Alert>
          )}
          {d.states && (
            <Typography variant="caption" color="text.secondary">
              {(["onTrack", "atRisk", "offTrack", "notReported"] as const)
                .map((s) => `${t(`dashboard.executive.state.${s}`)}: ${d.states?.[s] ?? 0}`)
                .join(" · ")}
            </Typography>
          )}
        </ExecutiveKpiTile>
      );
    }
    if (slot === "decisions") {
      const d = kpi.details as {
        open_risks?: number;
        mitigated_risks?: number;
        operational_pipeline?: Record<string, number>;
      };
      const pipeline = d.operational_pipeline;
      return (
        <ExecutiveKpiTile {...common} value={t("dashboard.executive.ceo.escalatedValue", { count: kpi.value ?? 0 })}>
          {kpi.status === "ok" && (
            <Typography variant="caption" color="text.secondary">
              {t("dashboard.executive.ceo.riskSplit", { count: d.open_risks ?? 0, mitigated: d.mitigated_risks ?? 0 })}
            </Typography>
          )}
          {pipeline && (
            <Typography variant="caption" color="text.secondary">
              {t("dashboard.executive.ceo.pipelineSplit", {
                count: (pipeline.adrs ?? 0) + (pipeline.arb ?? 0) + (pipeline.exceptions ?? 0),
              })}
            </Typography>
          )}
        </ExecutiveKpiTile>
      );
    }
    if (slot === "value") {
      const forecast = (kpi.details as {
        forecast?: { status: string; total?: number; currency?: string; conflict_count?: number };
      }).forecast;
      return (
        <ExecutiveKpiTile {...common}>
          {forecast && (
            <Box sx={{ p: 1, borderRadius: 1, bgcolor: "action.hover" }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                <Typography variant="caption" fontWeight={700} sx={{ flex: 1 }}>
                  {t("dashboard.executive.plannedSavings")}
                </Typography>
                <Chip size="small" variant="outlined" color="warning" label={t("dashboard.executive.provenance.forecast")} sx={{ height: 20, fontSize: 11 }} />
                <Chip size="small" variant="outlined" color="info" label={t("dashboard.executive.ceo.currentState")} sx={{ height: 20, fontSize: 11 }} />
              </Box>
              {forecast.status === "ok" ? (
                <Typography variant="body2" fontWeight={700} component="div">
                  <bdi>{money(forecast.total ?? 0, forecast.currency ?? data.currency)}</bdi>
                </Typography>
              ) : (
                <RestrictedAmount />
              )}
              <Typography variant="caption" color="text.secondary" component="div">
                {t("dashboard.executive.ceo.forecastNote", { count: forecast.conflict_count ?? 0 })}
              </Typography>
            </Box>
          )}
        </ExecutiveKpiTile>
      );
    }
    return <ExecutiveKpiTile {...common} />;
  };

  const slots: ExecutiveKpiSlot[] = ["strategy", "governance", "delivery", "services", "value", "decisions"];
  const decisionsPath = `/?tab=executive&page=decisions${period ? `&period=${encodeURIComponent(period)}` : ""}`;

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          alignItems: { xs: "stretch", sm: "center" },
          justifyContent: "space-between",
          flexDirection: { xs: "column", sm: "row" },
          gap: 2,
          mb: 2,
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h6" fontWeight={700}>
            {t("dashboard.executive.ceo.title")}
          </Typography>
          {!pending && (
            <Typography variant="caption" color="text.secondary">
              {t("dashboard.executive.generatedAt", { time: formatDateTime(data.generated_at) })}
              {" · "}
              {t("dashboard.executive.ceo.comparedWith", { period: label(data.previous_period.key) })}
            </Typography>
          )}
        </Box>
        <TextField
          select
          size="small"
          label={t("dashboard.executive.period")}
          value={data.available_periods.includes(shownKey) ? shownKey : ""}
          onChange={(e) => setPeriod(e.target.value)}
          disabled={pending}
          sx={{ minWidth: 220 }}
        >
          {data.available_periods.map((key) => (
            <MenuItem key={key} value={key} sx={{ paddingInlineStart: key.includes("-Q") ? 4 : 2 }}>
              {label(key)}
            </MenuItem>
          ))}
        </TextField>
      </Box>

      {pending ? (
        // No figure from the previous period stays on screen while the next loads.
        <Box role="status" aria-live="polite" data-testid="period-loading" sx={{ py: 4 }}>
          <LinearProgress sx={{ mb: 1 }} />
          <Typography variant="body2" color="text.secondary">
            {t("dashboard.executive.ceo.loadingPeriod", { period: label(shownKey) })}
          </Typography>
        </Box>
      ) : (
        <>
          {!data.period.is_current && (
            <Alert severity="info" sx={{ mb: 2 }} data-testid="past-period-notice">
              {t("dashboard.executive.ceo.pastPeriodNotice", { period: label(data.period.key) })}
            </Alert>
          )}

          <Grid container spacing={2}>
            <Grid item xs={12} lg={8}>
              <Grid container spacing={2}>
                {slots.map((slot) => (
                  <Grid item xs={12} sm={6} xl={4} key={slot}>
                    {render(slot)}
                  </Grid>
                ))}
              </Grid>
            </Grid>
            {/* On a phone the escalations come first: they are what needs action,
                and below six stacked tiles they would sit a long scroll away. */}
            <Grid item xs={12} lg={4} sx={{ order: { xs: -1, lg: 0 } }} data-testid="escalations-panel">
              <Card variant="outlined" sx={{ height: { lg: "100%" } }}>
                <CardContent>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                    <MaterialSymbol icon="notification_important" size={20} />
                    <Typography variant="subtitle1" fontWeight={700} sx={{ flex: 1, minWidth: 0 }}>
                      {t("dashboard.executive.ceo.panelTitle")}
                    </Typography>
                    <Chip size="small" variant="outlined" color="info" label={t("dashboard.executive.ceo.currentState")} sx={{ height: 20, fontSize: 11 }} />
                  </Box>
                  <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1 }}>
                    {t("dashboard.executive.ceo.panelHint")}
                  </Typography>
                  <EscalationsPanelBody panel={data.escalations_panel} />
                  <Link component={RouterLink} to={decisionsPath} variant="body2" underline="hover" sx={{ display: "inline-block", mt: 1 }}>
                    {t("dashboard.executive.ceo.allDecisions")}
                  </Link>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
            {t("dashboard.executive.ceo.footnote")}
          </Typography>
        </>
      )}
    </Box>
  );
}
