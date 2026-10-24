import { useState } from "react";
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

const SLOT_ICONS: Record<ExecutiveKpiSlot, string> = {
  strategy: "flag",
  governance: "gavel",
  delivery: "rocket_launch",
  services: "settings_suggest",
  value: "savings",
  decisions: "priority_high",
};

/** One line of the "decisions needing attention" panel. */
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
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
        {item.level && (
          <Box sx={{ width: 8, height: 8, borderRadius: "50%", flexShrink: 0, bgcolor: SEVERITY_COLORS[item.level as keyof typeof SEVERITY_COLORS] ?? "text.disabled" }} />
        )}
        {canOpen ? (
          <Link component={RouterLink} to={item.path} underline="hover" variant="body2" noWrap sx={{ minWidth: 0 }}>
            {label}
          </Link>
        ) : (
          <Typography variant="body2" noWrap sx={{ minWidth: 0 }}>
            {label}
          </Typography>
        )}
      </Box>
      <Typography variant="caption" color="text.secondary">
        {meta.join(" · ")}
      </Typography>
    </ListItem>
  );
}

export default function ExecutiveOverview() {
  const { t, i18n } = useTranslation(["common", "grc"]);
  const [period, setPeriod] = useState<string | null>(null);
  const path = period ? `/reports/executive/overview?period=${period}` : "/reports/executive/overview";
  const { data, error, loading } = useApiQuery<ExecutiveOverviewData>(path);
  const { formatDateTime, formatDate } = useDateFormat();

  if (error) return <Alert severity="error">{error.message || t("errors.generic")}</Alert>;
  if (!data) return loading ? <LinearProgress /> : null;

  const start = data.fiscal_year_start;
  const label = (key: string) => periodLabel(key, start, t);
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
    };
    if (slot === "delivery") {
      const d = kpi.details as {
        states?: Record<string, number>;
        excluded?: Record<string, number>;
      };
      const c = kpi.completeness;
      return (
        <ExecutiveKpiTile
          {...common}
          value={`${pct(kpi.value)} ${t("dashboard.executive.ceo.onTrackUnit")}`}
          previousValue={pct(kpi.previous.value ?? null)}
        >
          {c && (
            <Typography variant="caption" color="text.secondary">
              {t("dashboard.executive.ceo.coverage", { reported: c.numerator, total: c.denominator })}
            </Typography>
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
        pending?: Record<string, number>;
      };
      return (
        <ExecutiveKpiTile {...common} value={`${kpi.value} ${t("dashboard.executive.ceo.escalatedUnit")}`}>
          {kpi.status === "ok" && (
            <Typography variant="caption" color="text.secondary">
              {t("dashboard.executive.ceo.riskSplit", { open: d.open_risks ?? 0, mitigated: d.mitigated_risks ?? 0 })}
            </Typography>
          )}
          {d.pending && (
            <Typography variant="caption" color="text.secondary">
              {t("dashboard.executive.ceo.pendingSplit", {
                adrs: d.pending.adrs ?? 0,
                arb: d.pending.arb ?? 0,
                exceptions: d.pending.exceptions ?? 0,
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
              </Box>
              {forecast.status === "ok" ? (
                <Typography variant="body2" fontWeight={700}>
                  {money(forecast.total ?? 0, forecast.currency ?? data.currency)}
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
          <Typography variant="caption" color="text.secondary">
            {t("dashboard.executive.generatedAt", { time: formatDateTime(data.generated_at) })}
            {" · "}
            {t("dashboard.executive.ceo.comparedWith", { period: label(data.previous_period.key) })}
          </Typography>
        </Box>
        <TextField
          select
          size="small"
          label={t("dashboard.executive.period")}
          value={data.period.key}
          onChange={(e) => setPeriod(e.target.value)}
          sx={{ minWidth: 220 }}
        >
          {data.available_periods.map((key) => (
            <MenuItem key={key} value={key} sx={{ paddingInlineStart: key.includes("-Q") ? 4 : 2 }}>
              {label(key)}
            </MenuItem>
          ))}
        </TextField>
      </Box>

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
        <Grid item xs={12} lg={4}>
          <Card variant="outlined" sx={{ height: "100%" }}>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                <MaterialSymbol icon="notification_important" size={20} />
                <Typography variant="subtitle1" fontWeight={700} sx={{ flex: 1 }}>
                  {t("dashboard.executive.ceo.panelTitle")}
                </Typography>
              </Box>
              {data.decisions_panel.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {t("dashboard.executive.ceo.panelEmpty")}
                </Typography>
              ) : (
                <List dense disablePadding>
                  {data.decisions_panel.map((item) => (
                    <DecisionItemLine key={`${item.kind}-${item.id}`} item={item} />
                  ))}
                </List>
              )}
              <Link component={RouterLink} to="/?tab=executive&page=decisions" variant="body2" underline="hover" sx={{ display: "inline-block", mt: 1 }}>
                {t("dashboard.executive.ceo.allDecisions")}
              </Link>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
        {t("dashboard.executive.ceo.footnote")}
      </Typography>
    </Box>
  );
}
