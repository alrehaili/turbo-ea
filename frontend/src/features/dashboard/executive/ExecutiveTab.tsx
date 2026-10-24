import { useMemo, type ReactNode } from "react";
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
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { alpha, useTheme } from "@mui/material/styles";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useAuthContext } from "@/hooks/AuthContext";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useChartTheme } from "@/hooks/useChartTheme";
import { useCurrency } from "@/hooks/useCurrency";
import { useDateFormat } from "@/hooks/useDateFormat";
import { useIsRtl } from "@/hooks/useIsRtl";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useOptionLabel, useTypeLabel } from "@/hooks/useResolveLabel";
import { makeRtlAxisTick, mirrorChartMargin, rtlTooltipStyle } from "@/lib/rechartsRtl";
import { canAccessPath } from "@/lib/routePermissions";
import { RAG_COLORS, SEVERITY_COLORS, STATUS_COLORS } from "@/theme/tokens";
import type { ExecutiveDashboardData, ExecutiveSectionStatus, FieldOption } from "@/types";

/** One slice / bar of a chart. */
interface Datum {
  key: string;
  label: string;
  count: number;
  color: string;
}

const HEALTH_KEYS = ["onTrack", "atRisk", "offTrack", "noReport"] as const;
const HEALTH_COLORS: Record<(typeof HEALTH_KEYS)[number], string> = {
  onTrack: RAG_COLORS.green,
  atRisk: RAG_COLORS.amber,
  offTrack: RAG_COLORS.red,
  noReport: STATUS_COLORS.neutral,
};
const RISK_LEVELS = ["critical", "high", "medium", "low"] as const;
const TIME_DECISIONS = ["invest", "tolerate", "migrate", "eliminate", "undecided"] as const;
const TIME_COLORS: Record<string, string> = {
  invest: STATUS_COLORS.success,
  tolerate: STATUS_COLORS.info,
  migrate: STATUS_COLORS.warning,
  eliminate: STATUS_COLORS.error,
  undecided: STATUS_COLORS.neutral,
};
const LIFECYCLE_KEYS = ["plan", "phaseIn", "active", "phaseOut", "endOfLife", "none"] as const;
const LIFECYCLE_COLORS: Record<string, string> = {
  plan: STATUS_COLORS.neutral,
  phaseIn: STATUS_COLORS.info,
  active: STATUS_COLORS.success,
  phaseOut: STATUS_COLORS.warning,
  endOfLife: STATUS_COLORS.error,
  none: alpha(STATUS_COLORS.neutral, 0.45),
};

// ── Building blocks ──────────────────────────────────────────────────────

/** Percentage ring: a plain SVG arc, so it needs no RTL handling. */
function Ring({ pct, color, size = 64 }: { pct: number; color: string; size?: number }) {
  const theme = useTheme();
  const stroke = 7;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <Box sx={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={theme.palette.action.hover} strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${(clamped / 100) * c} ${c}`}
        />
      </svg>
      <Typography
        variant="caption"
        sx={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", fontWeight: 700 }}
      >
        {Math.round(clamped)}%
      </Typography>
    </Box>
  );
}

function KpiTile({
  icon,
  label,
  value,
  caption,
  color,
  ringPct,
}: {
  icon: string;
  label: string;
  /** `null` renders an em dash: unknown, never an authoritative zero. */
  value: string | number | null;
  caption?: string;
  color: string;
  ringPct?: number;
}) {
  return (
    <Card sx={{ height: "100%", borderTop: 3, borderColor: color }}>
      <CardContent sx={{ display: "flex", gap: 1.5, alignItems: "center" }}>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, color, mb: 0.5 }}>
            <MaterialSymbol icon={icon} size={18} color="inherit" />
            <Typography variant="caption" color="text.secondary" noWrap>
              {label}
            </Typography>
          </Box>
          <Typography variant="h4" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
            {value ?? "—"}
          </Typography>
          {caption && (
            <Typography variant="caption" color="text.secondary">
              {caption}
            </Typography>
          )}
        </Box>
        {ringPct !== undefined && value !== null && <Ring pct={ringPct} color={color} />}
      </CardContent>
    </Card>
  );
}

function SectionCard({
  title,
  icon,
  status,
  link,
  action,
  children,
}: {
  title: string;
  icon: string;
  status: ExecutiveSectionStatus;
  link?: { to: string; label: string };
  action?: ReactNode;
  children: ReactNode;
}) {
  const { t } = useTranslation("common");
  const { user } = useAuthContext();
  const showLink = link && status === "ok" && canAccessPath(user?.permissions, link.to);
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <MaterialSymbol icon={icon} size={20} />
          <Typography variant="subtitle1" fontWeight={700} sx={{ flex: 1 }}>
            {title}
          </Typography>
          {action}
          {showLink && (
            <Button size="small" component={RouterLink} to={link.to} sx={{ textTransform: "none" }}>
              {link.label}
            </Button>
          )}
        </Box>
        {status === "disabled" ? (
          <Box sx={{ py: 4, textAlign: "center", color: "text.secondary" }}>
            <MaterialSymbol icon="toggle_off" size={28} color="inherit" />
            <Typography variant="body2">{t("dashboard.executive.moduleDisabled")}</Typography>
          </Box>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  );
}

function EmptyNote({ label }: { label: string }) {
  return (
    <Box sx={{ py: 4, textAlign: "center" }}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}

/** Legend rendered in MUI so it wraps and mirrors with the document direction. */
function ChartLegend({ data }: { data: Datum[] }) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, minWidth: 0 }}>
      {data.map((d) => (
        <Box key={d.key} sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: d.color, flexShrink: 0 }} />
          <Typography variant="body2" noWrap sx={{ flex: 1, minWidth: 0 }}>
            {d.label}
          </Typography>
          <Typography variant="body2" fontWeight={700}>
            {d.count}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}

/** Donut with a centre figure and a side legend. */
function Donut({
  data,
  centerValue,
  centerLabel,
  emptyLabel,
}: {
  data: Datum[];
  centerValue: string | number;
  centerLabel: string;
  emptyLabel: string;
}) {
  const chart = useChartTheme();
  const isRtl = useIsRtl();
  const slices = data.filter((d) => d.count > 0);
  if (slices.length === 0) return <EmptyNote label={emptyLabel} />;
  return (
    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 2, flexWrap: "wrap", minWidth: 0 }}>
      <Box sx={{ position: "relative", width: 180, height: 180, flexShrink: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={slices}
              dataKey="count"
              nameKey="label"
              innerRadius={58}
              outerRadius={84}
              paddingAngle={2}
              stroke="none"
              isAnimationActive={false}
            >
              {slices.map((d) => (
                <Cell key={d.key} fill={d.color} />
              ))}
            </Pie>
            <RTooltip
              {...chart.tooltipProps}
              contentStyle={{ ...chart.tooltipProps.contentStyle, ...rtlTooltipStyle(isRtl) }}
            />
          </PieChart>
        </ResponsiveContainer>
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "none",
          }}
        >
          <Typography variant="h5" fontWeight={700} lineHeight={1}>
            {centerValue}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {centerLabel}
          </Typography>
        </Box>
      </Box>
      <Box sx={{ flex: "1 1 180px", minWidth: 180, maxWidth: 300 }}>
        <ChartLegend data={data} />
      </Box>
    </Box>
  );
}

/** Horizontal bar chart, one bar per datum. */
function HBars({ data, emptyLabel, labelWidth = 140 }: { data: Datum[]; emptyLabel: string; labelWidth?: number }) {
  const theme = useTheme();
  const chart = useChartTheme();
  const isRtl = useIsRtl();
  if (data.every((d) => d.count === 0)) return <EmptyNote label={emptyLabel} />;
  return (
    <ResponsiveContainer width="100%" height={Math.max(data.length * 34, 160)}>
      <BarChart data={data} layout="vertical" margin={mirrorChartMargin({ left: 0, right: 24, top: 4, bottom: 4 }, isRtl)}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={chart.gridStroke} />
        <XAxis type="number" allowDecimals={false} reversed={isRtl} tick={chart.axisTick} />
        <YAxis
          type="category"
          dataKey="label"
          width={labelWidth}
          orientation={isRtl ? "right" : "left"}
          tickLine={false}
          tick={isRtl ? makeRtlAxisTick(theme.palette.text.secondary) : chart.axisTick}
        />
        <RTooltip {...chart.tooltipProps} contentStyle={{ ...chart.tooltipProps.contentStyle, ...rtlTooltipStyle(isRtl) }} />
        <Bar dataKey="count" radius={isRtl ? [4, 0, 0, 4] : [0, 4, 4, 0]} barSize={18} isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={d.key} fill={d.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function Restricted() {
  const { t } = useTranslation("common");
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, color: "text.secondary" }}>
      <MaterialSymbol icon="lock" size={18} color="inherit" />
      <Typography variant="body2">{t("dashboard.executive.costsRestricted")}</Typography>
    </Box>
  );
}

// ── Tab ──────────────────────────────────────────────────────────────────

export default function ExecutiveTab() {
  const theme = useTheme();
  const chart = useChartTheme();
  const isRtl = useIsRtl();
  const { t, i18n } = useTranslation(["common", "grc", "reports"]);
  const { data, error, loading } = useApiQuery<ExecutiveDashboardData>("/reports/executive");
  const { types } = useMetamodel();
  const typeLabel = useTypeLabel();
  const optionLabel = useOptionLabel();
  const { symbol } = useCurrency();
  const compact = useMemo(
    () => new Intl.NumberFormat(i18n.language, { notation: "compact", maximumFractionDigits: 1 }),
    [i18n.language],
  );
  const money = (value: number) => `${symbol}${compact.format(value)}`;
  const { formatDateTime } = useDateFormat();

  // BusinessProcess option labels/colours come from the metamodel, so an admin's
  // renamed or recoloured options show here exactly as on card detail.
  const processOptions = useMemo(() => {
    const bp = types.find((ty) => ty.key === "BusinessProcess");
    const byField = (fieldKey: string): FieldOption[] => {
      for (const s of bp?.fields_schema ?? []) {
        const f = s.fields.find((fd) => fd.key === fieldKey);
        if (f) return f.options ?? [];
      }
      return [];
    };
    return { automationLevel: byField("automationLevel"), maturity: byField("maturity") };
  }, [types]);

  const optionData = (counts: Record<string, number> | undefined, options: FieldOption[]): Datum[] => {
    if (!counts) return [];
    const known = options.map((o) => ({
      key: o.key,
      label: optionLabel(o),
      count: counts[o.key] ?? 0,
      color: o.color ?? STATUS_COLORS.info,
    }));
    const knownKeys = new Set(options.map((o) => o.key));
    const unset = Object.entries(counts)
      .filter(([k]) => !knownKeys.has(k))
      .reduce((sum, [, n]) => sum + n, 0);
    return unset > 0
      ? [...known, { key: "__unset", label: t("dashboard.executive.notSet"), count: unset, color: STATUS_COLORS.neutral }]
      : known;
  };

  if (error) return <Alert severity="error">{error.message || t("errors.generic")}</Alert>;
  if (!data) return loading ? <LinearProgress /> : null;

  const { portfolio, delivery, processes, risks, rationalization } = data;
  const noData = t("dashboard.executive.noData");

  const typeData: Datum[] = types
    .filter((ty) => (portfolio.by_type[ty.key] ?? 0) > 0)
    .map((ty) => ({ key: ty.key, label: typeLabel(ty), count: portfolio.by_type[ty.key], color: ty.color }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  const lifecycleData: Datum[] = LIFECYCLE_KEYS.map((k) => ({
    key: k,
    label: t(k === "none" ? "lifecycle.notSet" : `lifecycle.${k}`),
    count: portfolio.lifecycle[k] ?? 0,
    color: LIFECYCLE_COLORS[k],
  }));

  const riskData: Datum[] = RISK_LEVELS.map((lvl) => ({
    key: lvl,
    label: t(`grc:risks.level.${lvl}`),
    count: risks.open_by_level?.[lvl] ?? 0,
    color: SEVERITY_COLORS[lvl],
  }));

  const timeData: Datum[] = TIME_DECISIONS.map((d) => ({
    key: d,
    label: t(`reports:rationalization.decision.${d}`),
    count: rationalization.by_decision[d] ?? 0,
    color: TIME_COLORS[d],
  }));

  // One row per health dimension, one stacked segment per RAG state.
  const healthRows = [
    { dim: t("dashboard.executive.health.schedule"), ...(delivery.health_schedule ?? {}) },
    { dim: t("dashboard.executive.health.cost"), ...(delivery.health_cost ?? {}) },
    { dim: t("dashboard.executive.health.scope"), ...(delivery.health_scope ?? {}) },
  ];

  const budget = delivery.budget;
  const spentPct =
    budget?.status === "ok" && (budget.total_budget ?? 0) > 0
      ? ((budget.total_actual ?? 0) / (budget.total_budget ?? 1)) * 100
      : null;

  return (
    <Box>
      {/* -------- Hero -------- */}
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, md: 3 },
          mb: 3,
          borderRadius: 2,
          color: theme.palette.primary.contrastText,
          background: `linear-gradient(${isRtl ? 255 : 105}deg, ${theme.palette.primary.dark}, ${theme.palette.primary.main})`,
          display: "flex",
          alignItems: { xs: "flex-start", md: "center" },
          justifyContent: "space-between",
          gap: 2,
          flexDirection: { xs: "column", md: "row" },
        }}
      >
        <Box>
          <Typography variant="h5" fontWeight={700}>
            {t("dashboard.executive.heroTitle")}
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.85 }}>
            {t("dashboard.executive.heroSubtitle")}
          </Typography>
        </Box>
        <Box sx={{ display: "flex", gap: { xs: 3, md: 5 } }}>
          {[
            { label: t("dashboard.executive.kpi.cards"), value: portfolio.total_cards },
            { label: t("dashboard.executive.hero.initiatives"), value: delivery.status === "ok" ? delivery.total_initiatives ?? 0 : "—" },
            { label: t("dashboard.executive.hero.processes"), value: processes.status === "ok" ? processes.total_processes ?? 0 : "—" },
          ].map((h) => (
            <Box key={h.label}>
              <Typography variant="h4" fontWeight={700} lineHeight={1}>
                {h.value}
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.85 }}>
                {h.label}
              </Typography>
            </Box>
          ))}
        </Box>
      </Paper>

      {/* -------- Headline KPIs -------- */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} lg={4} xl={2}>
          <KpiTile
            icon="fact_check"
            label={t("dashboard.executive.kpi.dataQuality")}
            value={`${portfolio.avg_data_quality}%`}
            ringPct={portfolio.avg_data_quality}
            color={STATUS_COLORS.info}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={4} xl={2}>
          <KpiTile
            icon="verified"
            label={t("dashboard.executive.kpi.approved")}
            value={`${portfolio.approved_pct}%`}
            ringPct={portfolio.approved_pct}
            color={STATUS_COLORS.success}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={4} xl={2}>
          <KpiTile
            icon="account_tree"
            label={t("dashboard.executive.kpi.processCoverage")}
            value={processes.status === "ok" ? `${processes.diagram_coverage?.percentage ?? 0}%` : null}
            ringPct={processes.diagram_coverage?.percentage ?? 0}
            caption={processes.status === "ok" ? undefined : t("dashboard.executive.moduleDisabled")}
            color={theme.palette.primary.main}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={4} xl={2}>
          <KpiTile
            icon="rocket_launch"
            label={t("dashboard.executive.kpi.offTrack")}
            value={delivery.status === "ok" ? delivery.off_track ?? 0 : null}
            caption={
              delivery.status === "ok"
                ? t("dashboard.executive.kpi.ofInitiatives", { count: delivery.total_initiatives ?? 0 })
                : t("dashboard.executive.moduleDisabled")
            }
            color={RAG_COLORS.red}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={4} xl={2}>
          <KpiTile
            icon="warning"
            label={t("dashboard.executive.kpi.criticalRisks")}
            value={risks.status === "ok" ? risks.critical_high_open ?? 0 : null}
            caption={
              risks.status === "ok"
                ? t("dashboard.executive.kpi.overdue", { count: risks.overdue ?? 0 })
                : t("dashboard.executive.moduleDisabled")
            }
            color={SEVERITY_COLORS.high}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={4} xl={2}>
          <KpiTile
            icon="savings"
            label={t("dashboard.executive.plannedSavings")}
            value={
              rationalization.planned_savings.status === "ok"
                ? money(rationalization.planned_savings.total ?? 0)
                : null
            }
            caption={
              rationalization.planned_savings.status === "ok"
                ? t("dashboard.executive.estimated")
                : t("dashboard.executive.costsRestricted")
            }
            color={STATUS_COLORS.warning}
          />
        </Grid>
      </Grid>

      {/* -------- Row: Portfolio + Risk -------- */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} lg={8}>
          <SectionCard
            title={t("dashboard.executive.section.portfolio")}
            icon="apps"
            status={portfolio.status}
            link={{ to: "/inventory", label: t("dashboard.executive.open") }}
          >
            <Grid container spacing={3}>
              <Grid item xs={12} md={7}>
                <Typography variant="overline" color="text.secondary">
                  {t("dashboard.executive.cardsByType")}
                </Typography>
                <HBars data={typeData} emptyLabel={noData} />
              </Grid>
              <Grid item xs={12} md={5}>
                <Typography variant="overline" color="text.secondary">
                  {t("dashboard.lifecycleOverview")}
                </Typography>
                <Donut
                  data={lifecycleData}
                  centerValue={portfolio.total_cards}
                  centerLabel={t("dashboard.executive.kpi.cards")}
                  emptyLabel={noData}
                />
              </Grid>
            </Grid>
          </SectionCard>
        </Grid>

        <Grid item xs={12} lg={4}>
          <SectionCard
            title={t("dashboard.executive.section.risks")}
            icon="shield"
            status={risks.status}
            link={{ to: "/grc?tab=risk", label: t("dashboard.executive.open") }}
            action={
              risks.status === "ok" && (risks.overdue ?? 0) > 0 ? (
                <Chip size="small" color="error" variant="outlined" label={t("dashboard.executive.kpi.overdue", { count: risks.overdue ?? 0 })} />
              ) : undefined
            }
          >
            <Donut
              data={riskData}
              centerValue={risks.open ?? 0}
              centerLabel={t("dashboard.executive.openLabel")}
              emptyLabel={noData}
            />
          </SectionCard>
        </Grid>
      </Grid>

      {/* -------- Row: Delivery + Processes -------- */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} lg={6}>
          <SectionCard
            title={t("dashboard.executive.section.delivery")}
            icon="rocket_launch"
            status={delivery.status}
            link={{ to: "/ppm", label: t("dashboard.executive.open") }}
          >
            {(delivery.total_initiatives ?? 0) === 0 ? (
              <EmptyNote label={noData} />
            ) : (
              <>
                <ResponsiveContainer width="100%" height={150}>
                  <BarChart
                    data={healthRows}
                    layout="vertical"
                    stackOffset="expand"
                    margin={mirrorChartMargin({ left: 0, right: 16, top: 4, bottom: 4 }, isRtl)}
                  >
                    <XAxis type="number" hide reversed={isRtl} />
                    <YAxis
                      type="category"
                      dataKey="dim"
                      width={90}
                      orientation={isRtl ? "right" : "left"}
                      tickLine={false}
                      axisLine={false}
                      tick={isRtl ? makeRtlAxisTick(theme.palette.text.secondary) : chart.axisTick}
                    />
                    <RTooltip {...chart.tooltipProps} contentStyle={{ ...chart.tooltipProps.contentStyle, ...rtlTooltipStyle(isRtl) }} />
                    {HEALTH_KEYS.map((k) => (
                      <Bar
                        key={k}
                        dataKey={k}
                        stackId="health"
                        name={t(`dashboard.executive.health.${k}`)}
                        fill={HEALTH_COLORS[k]}
                        barSize={22}
                        isAnimationActive={false}
                      />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2, mt: 1, mb: 2 }}>
                  {HEALTH_KEYS.map((k) => (
                    <Box key={k} sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
                      <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: HEALTH_COLORS[k] }} />
                      <Typography variant="caption">{t(`dashboard.executive.health.${k}`)}</Typography>
                    </Box>
                  ))}
                </Box>
              </>
            )}
            <Typography variant="overline" color="text.secondary">
              {t("dashboard.executive.budgetVsActual")}
            </Typography>
            {budget?.status === "ok" ? (
              <Box sx={{ display: "flex", alignItems: "center", gap: 3 }}>
                <Box sx={{ flex: 1 }}>
                  {[
                    { label: t("dashboard.executive.budget"), value: budget.total_budget ?? 0, color: theme.palette.primary.main },
                    { label: t("dashboard.executive.actual"), value: budget.total_actual ?? 0, color: STATUS_COLORS.warning },
                  ].map((b) => (
                    <Box key={b.label} sx={{ mb: 1 }}>
                      <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                        <Typography variant="body2">{b.label}</Typography>
                        <Typography variant="body2" fontWeight={700}>
                          {money(b.value)}
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={(budget.total_budget ?? 0) > 0 ? Math.min(100, (b.value / (budget.total_budget ?? 1)) * 100) : 0}
                        sx={{ height: 10, borderRadius: 5, bgcolor: "action.hover", "& .MuiLinearProgress-bar": { bgcolor: b.color, borderRadius: 5 } }}
                      />
                    </Box>
                  ))}
                </Box>
                {spentPct !== null && (
                  <Box sx={{ textAlign: "center" }}>
                    <Ring pct={spentPct} color={spentPct > 100 ? RAG_COLORS.red : STATUS_COLORS.warning} size={72} />
                    <Typography variant="caption" color="text.secondary">
                      {t("dashboard.executive.spent")}
                    </Typography>
                  </Box>
                )}
              </Box>
            ) : (
              <Restricted />
            )}
          </SectionCard>
        </Grid>

        <Grid item xs={12} lg={6}>
          <SectionCard
            title={t("dashboard.executive.section.processes")}
            icon="route"
            status={processes.status}
            link={{ to: "/bpm", label: t("dashboard.executive.open") }}
          >
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="overline" color="text.secondary">
                  {t("dashboard.executive.automation")}
                </Typography>
                <Donut
                  data={optionData(processes.by_automation, processOptions.automationLevel)}
                  centerValue={processes.total_processes ?? 0}
                  centerLabel={t("dashboard.executive.hero.processes")}
                  emptyLabel={noData}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="overline" color="text.secondary">
                  {t("dashboard.executive.maturity")}
                </Typography>
                <HBars data={optionData(processes.by_maturity, processOptions.maturity)} emptyLabel={noData} labelWidth={120} />
              </Grid>
            </Grid>
          </SectionCard>
        </Grid>
      </Grid>

      {/* -------- Row: Rationalization -------- */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12}>
          <SectionCard
            title={t("dashboard.executive.section.rationalization")}
            icon="balance"
            status={rationalization.status}
            link={{ to: "/rationalization", label: t("dashboard.executive.open") }}
          >
            <Grid container spacing={3} alignItems="center">
              <Grid item xs={12} md={7}>
                <Donut
                  data={timeData}
                  centerValue={rationalization.decisions}
                  centerLabel={t("dashboard.executive.decisions")}
                  emptyLabel={t("dashboard.executive.noAssessments")}
                />
              </Grid>
              <Grid item xs={12} md={5}>
                <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2, borderColor: alpha(STATUS_COLORS.warning, 0.5) }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                    <Box sx={{ color: "warning.main", display: "flex" }}>
                      <MaterialSymbol icon="savings" size={20} color="inherit" />
                    </Box>
                    <Typography variant="subtitle2" fontWeight={700} sx={{ flex: 1 }}>
                      {t("dashboard.executive.plannedSavings")}
                    </Typography>
                    <Chip size="small" variant="outlined" color="warning" label={t("dashboard.executive.estimated")} />
                  </Box>
                  {rationalization.planned_savings.status === "ok" ? (
                    <>
                      <Typography variant="h3" fontWeight={700}>
                        {money(rationalization.planned_savings.total ?? 0)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {t("dashboard.executive.fromDecisions", {
                          count: rationalization.planned_savings.decisions_with_savings ?? 0,
                        })}
                      </Typography>
                    </>
                  ) : (
                    <Restricted />
                  )}
                </Paper>
              </Grid>
            </Grid>
          </SectionCard>
        </Grid>
      </Grid>

      <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
        {t("dashboard.executive.footnote")} · {t("dashboard.executive.generatedAt", { time: formatDateTime(data.generated_at) })}
      </Typography>
    </Box>
  );
}
