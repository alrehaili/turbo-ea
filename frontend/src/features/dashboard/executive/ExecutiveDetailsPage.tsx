import { useMemo, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
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
import RestrictedAmount from "@/features/ppm/RestrictedAmount";
import { useAuthContext } from "@/hooks/AuthContext";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useChartTheme } from "@/hooks/useChartTheme";
import { useDateFormat } from "@/hooks/useDateFormat";
import { useIsRtl } from "@/hooks/useIsRtl";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useOptionLabel, useTypeLabel } from "@/hooks/useResolveLabel";
import { fiscalYearLabel } from "@/lib/fiscalYear";
import { fiscalYearOfPeriod, useExecutivePeriod } from "./useExecutivePeriod";
import { makeRtlAxisTick, mirrorChartMargin, rtlTooltipStyle } from "@/lib/rechartsRtl";
import { canAccessPath } from "@/lib/routePermissions";
import { RAG_COLORS, SEVERITY_COLORS, STATUS_COLORS } from "@/theme/tokens";
import type { ExecutiveDashboardData, ExecutiveSectionStatus, FieldOption } from "@/types";
import { deliveryTone, formatCompactMoney, pct } from "./executiveFormat";

/** One slice / bar of a chart. */
interface Datum {
  key: string;
  label: string;
  count: number;
  color: string;
}

/**
 * Where a figure comes from, shown as a chip on every headline tile so an
 * executive can tell a counted fact from a self-reported status or a forecast.
 * `verified` (Finance-confirmed) has no Phase 1 source and is only explained.
 */
type Provenance = "recorded" | "reported" | "forecast" | "restricted" | "notAvailable";

const PROVENANCE_COLOR: Record<Provenance, "default" | "info" | "warning" | "success"> = {
  recorded: "success",
  reported: "info",
  forecast: "warning",
  restricted: "default",
  notAvailable: "default",
};

const DELIVERY_KEYS = ["onTrack", "atRisk", "offTrack", "notReported"] as const;
const DELIVERY_COLORS: Record<(typeof DELIVERY_KEYS)[number], string> = {
  onTrack: RAG_COLORS.green,
  atRisk: RAG_COLORS.amber,
  offTrack: RAG_COLORS.red,
  notReported: STATUS_COLORS.neutral,
};
const DIMENSION_KEYS = ["onTrack", "atRisk", "offTrack", "noReport"] as const;
const DIMENSION_COLORS: Record<(typeof DIMENSION_KEYS)[number], string> = {
  onTrack: RAG_COLORS.green,
  atRisk: RAG_COLORS.amber,
  offTrack: RAG_COLORS.red,
  noReport: STATUS_COLORS.neutral,
};
const TONE_COLORS = {
  offTrack: RAG_COLORS.red,
  atRisk: RAG_COLORS.amber,
  onTrack: RAG_COLORS.green,
  none: STATUS_COLORS.neutral,
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
function Ring({ pct: value, color, size = 64 }: { pct: number; color: string; size?: number }) {
  const theme = useTheme();
  const stroke = 7;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, value));
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
        {Math.round(value)}%
      </Typography>
    </Box>
  );
}

function ProvenanceChip({ kind }: { kind: Provenance }) {
  const { t } = useTranslation("common");
  return (
    <Tooltip title={t(`dashboard.executive.provenance.${kind}Hint`)}>
      <Chip
        size="small"
        variant="outlined"
        color={PROVENANCE_COLOR[kind]}
        label={t(`dashboard.executive.provenance.${kind}`)}
        sx={{ height: 20, fontSize: 11 }}
      />
    </Tooltip>
  );
}

/** A link shown only when the caller can open its target. */
function DrillLink({ to, label }: { to: string; label: string }) {
  const { user } = useAuthContext();
  if (!canAccessPath(user?.permissions, to)) return null;
  return (
    <Link component={RouterLink} to={to} variant="caption" underline="hover">
      {label}
    </Link>
  );
}

function KpiTile({
  icon,
  label,
  description,
  value,
  caption,
  color,
  ringPct,
  provenance,
  drill,
}: {
  icon: string;
  label: string;
  /** Plain-language definition, shown on the info icon. */
  description: string;
  /** `null` renders an em dash: unknown, never an authoritative zero. */
  value: ReactNode | null;
  caption?: ReactNode;
  color: string;
  ringPct?: number | null;
  provenance: Provenance;
  drill?: { to: string; label: string };
}) {
  return (
    <Card sx={{ height: "100%", borderTop: 3, borderColor: color }} data-testid="executive-kpi">
      <CardContent sx={{ display: "flex", flexDirection: "column", gap: 1, height: "100%" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, color }}>
          <MaterialSymbol icon={icon} size={18} color="inherit" />
          <Typography variant="caption" color="text.secondary" sx={{ flex: 1, minWidth: 0 }}>
            {label}
          </Typography>
          <Tooltip title={description}>
            <Box component="span" sx={{ display: "flex", color: "text.disabled", cursor: "help" }} aria-label={description}>
              <MaterialSymbol icon="info" size={16} color="inherit" />
            </Box>
          </Tooltip>
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography variant="h4" component="div" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
              {value ?? "—"}
            </Typography>
            {caption && (
              <Typography variant="caption" color="text.secondary" component="div">
                {caption}
              </Typography>
            )}
          </Box>
          {ringPct !== undefined && ringPct !== null && value !== null && <Ring pct={ringPct} color={color} />}
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, mt: "auto", flexWrap: "wrap" }}>
          <ProvenanceChip kind={provenance} />
          {drill && <DrillLink to={drill.to} label={drill.label} />}
        </Box>
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
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2, flexWrap: "wrap" }}>
          <MaterialSymbol icon={icon} size={20} />
          <Typography variant="subtitle1" fontWeight={700} sx={{ flex: 1, minWidth: 0 }}>
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

/** One stacked bar of the four delivery states, with a wrapping legend. */
function StateBar({ data, ariaLabel }: { data: Datum[]; ariaLabel: string }) {
  const total = data.reduce((sum, d) => sum + d.count, 0);
  return (
    <Box>
      <Box
        role="img"
        aria-label={ariaLabel}
        sx={{ display: "flex", height: 14, borderRadius: 7, overflow: "hidden", bgcolor: "action.hover" }}
      >
        {total > 0 &&
          data
            .filter((d) => d.count > 0)
            .map((d) => <Box key={d.key} sx={{ width: `${(d.count / total) * 100}%`, bgcolor: d.color }} />)}
      </Box>
      <Box sx={{ display: "flex", flexWrap: "wrap", columnGap: 2, rowGap: 0.5, mt: 1 }}>
        {data.map((d) => (
          <Box key={d.key} sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: d.color }} />
            <Typography variant="caption">
              {d.label}: <strong>{d.count}</strong>
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

function RestrictedNote() {
  const { t } = useTranslation("common");
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, color: "text.secondary" }}>
      <MaterialSymbol icon="lock" size={18} color="inherit" />
      <Typography variant="body2">{t("dashboard.executive.costsRestricted")}</Typography>
    </Box>
  );
}

// ── Tab ──────────────────────────────────────────────────────────────────

export default function ExecutiveDetailsPage() {
  const theme = useTheme();
  const chart = useChartTheme();
  const isRtl = useIsRtl();
  const { t, i18n } = useTranslation(["common", "grc", "reports"]);
  // Details reports money per fiscal year: it follows the fiscal year of the
  // period chosen on any Executive page, and choosing a year here sets it.
  const { period, setPeriod } = useExecutivePeriod();
  const fiscalYear = fiscalYearOfPeriod(period);
  const setFiscalYear = (fy: number) => setPeriod(`FY${fy}`);
  const path = fiscalYear ? `/reports/executive?fiscal_year=${fiscalYear}` : "/reports/executive";
  const { data, error, loading } = useApiQuery<ExecutiveDashboardData>(path);
  const { types } = useMetamodel();
  const typeLabel = useTypeLabel();
  const optionLabel = useOptionLabel();
  const { formatDate, formatDateTime } = useDateFormat();

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
      ? [...known, { key: "__unset", label: t("dashboard.executive.notAssessed"), count: unset, color: STATUS_COLORS.neutral }]
      : known;
  };

  if (error) return <Alert severity="error">{error.message || t("errors.generic")}</Alert>;
  if (!data) return loading ? <LinearProgress /> : null;
  // The kept payload belongs to the previous request: show none of it until
  // the requested year's figures have arrived.
  const shownFy = data.delivery.budget?.fiscal_year;
  if (loading || (fiscalYear !== null && shownFy !== undefined && shownFy !== fiscalYear)) {
    return (
      <Box role="status" aria-live="polite" data-testid="period-loading" sx={{ py: 4 }}>
        <LinearProgress sx={{ mb: 1 }} />
        <Typography variant="body2" color="text.secondary">
          {t("dashboard.executive.ceo.loadingFigures")}
        </Typography>
      </Box>
    );
  }

  const { portfolio, delivery, processes, risks, rationalization } = data;
  const noData = t("dashboard.executive.noData");
  const money = (value: number, currency: string) => formatCompactMoney(value, currency, i18n.language);

  // ── Delivery ──
  const states = delivery.states;
  const coverage = delivery.coverage;
  const stateData: Datum[] = DELIVERY_KEYS.map((k) => ({
    key: k,
    label: t(`dashboard.executive.state.${k}`),
    count: states?.[k] ?? 0,
    color: DELIVERY_COLORS[k],
  }));
  const excludedTotal = Object.values(delivery.excluded ?? {}).reduce((a, b) => a + b, 0);
  const stalenessNote =
    delivery.source === "initiative_status"
      ? t("dashboard.executive.coverage.sourceStatus")
      : delivery.staleness_days
        ? t("dashboard.executive.coverage.staleness", { count: delivery.staleness_days })
        : t("dashboard.executive.coverage.noStaleness");
  const dimensionRows = delivery.dimensions
    ? (["schedule", "cost", "scope"] as const).map((dim) => ({
        dim: t(`dashboard.executive.health.${dim}`),
        ...(delivery.dimensions?.[dim] ?? {}),
      }))
    : null;

  // ── Budget ──
  const budget = delivery.budget;
  const fyStart = budget?.fiscal_year_start ?? 1;
  const fyLabel = budget ? fiscalYearLabel(budget.fiscal_year, fyStart, t) : null;
  const budgetOk = budget?.status === "ok" && budget.currency !== undefined;

  // ── Savings ──
  const savings = rationalization.planned_savings;
  const conflicts = savings.conflicts ?? [];
  // The count is always known; the names and amounts need rationalization access.
  const conflictCount = savings.conflict_count ?? conflicts.length;

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

  const typeData: Datum[] = types
    .filter((ty) => (portfolio.by_type[ty.key] ?? 0) > 0)
    .map((ty) => ({ key: ty.key, label: typeLabel(ty), count: portfolio.by_type[ty.key], color: ty.color }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  const lifecycleData: Datum[] = LIFECYCLE_KEYS.map((k) => ({
    key: k,
    label:
      k === "none"
        ? t("lifecycle.notSet")
        : k === "endOfLife"
          ? t("dashboard.executive.pastPlannedEol")
          : t(`lifecycle.${k}`),
    count: portfolio.lifecycle[k] ?? 0,
    color: LIFECYCLE_COLORS[k],
  }));

  const ppmOff = !data.ppm_enabled;

  return (
    <Box>
      {/* -------- Hero: title, reporting period, freshness -------- */}
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
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h5" fontWeight={700}>
            {t("dashboard.executive.heroTitle")}
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.85 }}>
            {t("dashboard.executive.heroSubtitle")}
          </Typography>
          <Typography variant="caption" sx={{ opacity: 0.85, display: "block", mt: 0.5 }}>
            {t("dashboard.executive.generatedAt", { time: formatDateTime(data.generated_at) })}
            {coverage?.latest_report_date &&
              ` · ${t("dashboard.executive.latestReport", { date: formatDate(coverage.latest_report_date) })}`}
          </Typography>
        </Box>
        {budget && !ppmOff && (
          <TextField
            select
            size="small"
            label={t("dashboard.executive.period")}
            value={budget.fiscal_year}
            onChange={(e) => setFiscalYear(Number(e.target.value))}
            sx={{
              minWidth: 180,
              bgcolor: "background.paper",
              borderRadius: 1,
            }}
          >
            {budget.available_years.map((fy) => (
              <MenuItem key={fy} value={fy}>
                {fiscalYearLabel(fy, fyStart, t)}
                {fy === budget.current_fiscal_year ? ` · ${t("dashboard.executive.currentPeriod")}` : ""}
              </MenuItem>
            ))}
          </TextField>
        )}
      </Paper>

      {/* -------- Headline KPIs (CEO view) -------- */}
      <Grid container spacing={2} sx={{ mb: 1 }}>
        <Grid item xs={12} sm={6} lg={4} xl>
          <KpiTile
            icon="rocket_launch"
            label={t("dashboard.executive.kpi.delivery")}
            description={t("dashboard.executive.kpi.deliveryHint")}
            value={pct(delivery.on_track_pct)}
            ringPct={delivery.on_track_pct}
            caption={
              (coverage?.reported ?? 0) > 0
                ? t("dashboard.executive.kpi.deliveryCaption", {
                    atRisk: states?.atRisk ?? 0,
                    offTrack: states?.offTrack ?? 0,
                  })
                : t("dashboard.executive.notReported")
            }
            color={TONE_COLORS[deliveryTone(states)]}
            provenance={(coverage?.reported ?? 0) > 0 ? "reported" : "notAvailable"}
            drill={{ to: "/ppm", label: t("dashboard.executive.viewInitiatives") }}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={4} xl>
          <KpiTile
            icon="assignment_turned_in"
            label={t("dashboard.executive.kpi.coverage")}
            description={t("dashboard.executive.kpi.coverageHint")}
            value={coverage ? `${coverage.reported} / ${coverage.in_flight}` : null}
            ringPct={coverage?.percentage}
            caption={stalenessNote}
            color={STATUS_COLORS.info}
            provenance="recorded"
            drill={{ to: "/ppm", label: t("dashboard.executive.viewInitiatives") }}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={4} xl>
          <KpiTile
            icon="account_balance_wallet"
            label={t("dashboard.executive.kpi.budgetExecution")}
            description={t("dashboard.executive.kpi.budgetExecutionHint")}
            value={
              budget?.status === "restricted" ? (
                <RestrictedAmount variant="h6" />
              ) : budgetOk ? (
                pct(budget.execution_pct) ?? t("dashboard.executive.noBudget")
              ) : null
            }
            caption={
              ppmOff
                ? t("dashboard.executive.moduleDisabled")
                : budgetOk
                  ? t("dashboard.executive.kpi.budgetCaption", {
                      period: fyLabel,
                      actual: money(budget.actual ?? 0, budget.currency ?? data.currency),
                      budget: money(budget.budget ?? 0, budget.currency ?? data.currency),
                    })
                  : fyLabel
            }
            color={(budget?.execution_pct ?? 0) > 100 ? RAG_COLORS.red : STATUS_COLORS.warning}
            provenance={budget?.status === "restricted" ? "restricted" : budgetOk ? "recorded" : "notAvailable"}
            drill={{ to: "/ppm", label: t("dashboard.executive.viewBudgets") }}
          />
        </Grid>
        <Grid item xs={12} sm={6} lg={6} xl>
          <KpiTile
            icon="warning"
            label={t("dashboard.executive.kpi.criticalRisks")}
            description={t("dashboard.executive.kpi.criticalRisksHint")}
            value={risks.status === "ok" ? risks.critical_high_open ?? 0 : null}
            caption={
              risks.status === "ok"
                ? t("dashboard.executive.kpi.overdue", { count: risks.overdue ?? 0 })
                : t("dashboard.executive.moduleDisabled")
            }
            color={SEVERITY_COLORS.high}
            provenance={risks.status === "ok" ? "recorded" : "notAvailable"}
            drill={{ to: "/grc?tab=risk", label: t("dashboard.executive.viewRisks") }}
          />
        </Grid>
        <Grid item xs={12} sm={12} lg={6} xl>
          <KpiTile
            icon="savings"
            label={t("dashboard.executive.plannedSavings")}
            description={t("dashboard.executive.kpi.plannedSavingsHint")}
            value={
              savings.status === "ok" ? (
                money(savings.total ?? 0, savings.currency ?? data.currency)
              ) : (
                <RestrictedAmount variant="h6" />
              )
            }
            caption={
              savings.status === "ok"
                ? t("dashboard.executive.kpi.savingsCaption", {
                    count: savings.applications_counted ?? 0,
                    conflicts: conflictCount,
                  })
                : undefined
            }
            color={STATUS_COLORS.warning}
            provenance={savings.status === "ok" ? "forecast" : "restricted"}
            drill={{ to: "/rationalization", label: t("dashboard.executive.viewRationalization") }}
          />
        </Grid>
      </Grid>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 3 }}>
        {t("dashboard.executive.provenanceLegend")}
      </Typography>

      {/* -------- Row: Delivery + Risk -------- */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} lg={8}>
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
                <Typography variant="overline" color="text.secondary">
                  {t("dashboard.executive.deliveryStates", { count: delivery.in_flight ?? 0 })}
                </Typography>
                <StateBar data={stateData} ariaLabel={t("dashboard.executive.deliveryStates", { count: delivery.in_flight ?? 0 })} />
                <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                  {t("dashboard.executive.notReportedRule")}
                  {excludedTotal > 0 &&
                    ` ${t("dashboard.executive.excludedNote", {
                      completed: delivery.excluded?.completed ?? 0,
                      onHold: delivery.excluded?.onHold ?? 0,
                    })}`}
                </Typography>

                {coverage && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="overline" color="text.secondary">
                      {t("dashboard.executive.kpi.coverage")}
                    </Typography>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                      <LinearProgress
                        variant="determinate"
                        value={coverage.percentage ?? 0}
                        sx={{ flex: 1, height: 10, borderRadius: 5, bgcolor: "action.hover" }}
                        aria-label={t("dashboard.executive.kpi.coverage")}
                      />
                      <Typography variant="body2" fontWeight={700}>
                        {pct(coverage.percentage) ?? "—"}
                      </Typography>
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      {stalenessNote}
                      {coverage.stale_reports > 0 &&
                        ` · ${t("dashboard.executive.coverage.staleCount", { count: coverage.stale_reports })}`}
                      {coverage.oldest_report_date &&
                        ` · ${t("dashboard.executive.coverage.oldest", { date: formatDate(coverage.oldest_report_date) })}`}
                    </Typography>
                  </Box>
                )}

                {dimensionRows && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="overline" color="text.secondary">
                      {t("dashboard.executive.healthDimensions")}
                    </Typography>
                    <ResponsiveContainer width="100%" height={130}>
                      <BarChart
                        data={dimensionRows}
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
                        {DIMENSION_KEYS.map((k) => (
                          <Bar
                            key={k}
                            dataKey={k}
                            stackId="health"
                            name={t(`dashboard.executive.state.${k === "noReport" ? "notReported" : k}`)}
                            fill={DIMENSION_COLORS[k]}
                            barSize={20}
                            isAnimationActive={false}
                          />
                        ))}
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                )}
              </>
            )}

            <Box sx={{ mt: 2 }}>
              <Typography variant="overline" color="text.secondary">
                {t("dashboard.executive.budgetVsActual")}
                {fyLabel && ` · ${fyLabel}`}
              </Typography>
              {ppmOff ? (
                <Typography variant="body2" color="text.secondary">
                  {t("dashboard.executive.moduleDisabled")}
                </Typography>
              ) : budgetOk ? (
                <>
                  {(budget.budget ?? 0) === 0 && (budget.actual ?? 0) === 0 ? (
                    <Typography variant="body2" color="text.secondary">
                      {t("dashboard.executive.noBudgetForPeriod", { period: fyLabel })}
                    </Typography>
                  ) : (
                    [
                      { key: "budget", label: t("dashboard.executive.budget"), value: budget.budget ?? 0, color: theme.palette.primary.main },
                      { key: "actual", label: t("dashboard.executive.actual"), value: budget.actual ?? 0, color: STATUS_COLORS.warning },
                    ].map((b) => (
                      <Box key={b.key} sx={{ mb: 1 }}>
                        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 1 }}>
                          <Typography variant="body2">{b.label}</Typography>
                          <Typography variant="body2" fontWeight={700}>
                            {money(b.value, budget.currency ?? data.currency)}
                          </Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={(budget.budget ?? 0) > 0 ? Math.min(100, (b.value / (budget.budget ?? 1)) * 100) : 0}
                          sx={{ height: 10, borderRadius: 5, bgcolor: "action.hover", "& .MuiLinearProgress-bar": { bgcolor: b.color, borderRadius: 5 } }}
                        />
                      </Box>
                    ))
                  )}
                  <Typography variant="caption" color="text.secondary">
                    {t("dashboard.executive.budgetRule")}
                    {(budget.undated_cost_lines ?? 0) > 0 &&
                      ` ${t("dashboard.executive.undatedCostLines", { count: budget.undated_cost_lines ?? 0 })}`}
                  </Typography>
                </>
              ) : (
                <RestrictedNote />
              )}
            </Box>
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

      {/* -------- Row: Rationalization and savings -------- */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12}>
          <SectionCard
            title={t("dashboard.executive.section.rationalization")}
            icon="balance"
            status={rationalization.status}
            link={{ to: "/rationalization", label: t("dashboard.executive.open") }}
          >
            <Grid container spacing={3} alignItems="flex-start">
              <Grid item xs={12} md={6}>
                <Donut
                  data={timeData}
                  centerValue={rationalization.decisions}
                  centerLabel={t("dashboard.executive.decisions")}
                  emptyLabel={t("dashboard.executive.noAssessments")}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2, borderColor: alpha(STATUS_COLORS.warning, 0.5), mb: 2 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1, flexWrap: "wrap" }}>
                    <Box sx={{ color: "warning.main", display: "flex" }}>
                      <MaterialSymbol icon="savings" size={20} color="inherit" />
                    </Box>
                    <Typography variant="subtitle2" fontWeight={700} sx={{ flex: 1 }}>
                      {t("dashboard.executive.plannedSavings")}
                    </Typography>
                    <ProvenanceChip kind={savings.status === "ok" ? "forecast" : "restricted"} />
                  </Box>
                  {savings.status === "ok" ? (
                    <>
                      <Typography variant="h4" fontWeight={700}>
                        {money(savings.total ?? 0, savings.currency ?? data.currency)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" component="div">
                        {t("dashboard.executive.savingsDedupe", {
                          count: savings.applications_counted ?? 0,
                          merged: savings.duplicates_merged ?? 0,
                        })}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" component="div">
                        {t("dashboard.executive.savingsPeriodBlocked")}
                      </Typography>
                    </>
                  ) : (
                    <RestrictedNote />
                  )}
                </Paper>
                <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                    <Typography variant="subtitle2" fontWeight={700} sx={{ flex: 1 }}>
                      {t("dashboard.executive.realizedSavings")}
                    </Typography>
                    <ProvenanceChip kind="notAvailable" />
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {t("dashboard.executive.realizedSavingsHint")}
                  </Typography>
                </Paper>
              </Grid>
              {savings.status === "ok" && conflictCount > 0 && savings.conflict_detail === "restricted" && (
                <Grid item xs={12}>
                  <Alert severity="warning" icon={<MaterialSymbol icon="lock" size={20} />}>
                    {t("dashboard.executive.conflictsRestricted", { count: conflictCount })}
                  </Alert>
                </Grid>
              )}
              {savings.status === "ok" && conflicts.length > 0 && (
                <Grid item xs={12}>
                  <Alert severity="warning" sx={{ mb: 1 }}>
                    {t("dashboard.executive.conflictsIntro", {
                      count: conflicts.length,
                      min: money(savings.excluded_range?.[0] ?? 0, savings.currency ?? data.currency),
                      max: money(savings.excluded_range?.[1] ?? 0, savings.currency ?? data.currency),
                    })}
                  </Alert>
                  <Box sx={{ overflowX: "auto" }}>
                    <Table size="small" aria-label={t("dashboard.executive.conflictsTitle")}>
                      <TableHead>
                        <TableRow>
                          <TableCell>{t("dashboard.executive.conflictApplication")}</TableCell>
                          <TableCell>{t("dashboard.executive.conflictEstimates")}</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {conflicts.map((c) => (
                          <TableRow key={c.card_id}>
                            <TableCell>
                              <Link component={RouterLink} to={`/cards/${c.card_id}`} underline="hover">
                                {c.card_name}
                              </Link>
                            </TableCell>
                            <TableCell>
                              {c.candidates
                                .map((cand) => `${cand.assessment_name}: ${money(cand.amount, savings.currency ?? data.currency)}`)
                                .join(" · ")}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Box>
                </Grid>
              )}
            </Grid>
          </SectionCard>
        </Grid>
      </Grid>

      {/* -------- Row: Processes -------- */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12}>
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
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary">
                  {t("dashboard.executive.documentationCoverage", {
                    pct: processes.documentation_coverage?.percentage ?? 0,
                    documented: processes.documentation_coverage?.with_diagram ?? 0,
                    total: processes.documentation_coverage?.total ?? 0,
                  })}
                </Typography>
              </Grid>
            </Grid>
          </SectionCard>
        </Grid>
      </Grid>

      {/* -------- Specialist: repository metrics, out of the CEO view -------- */}
      <Accordion disableGutters variant="outlined" sx={{ mb: 2, borderRadius: 1 }}>
        <AccordionSummary expandIcon={<MaterialSymbol icon="expand_more" size={20} />}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
            <MaterialSymbol icon="inventory_2" size={20} />
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="subtitle1" fontWeight={700}>
                {t("dashboard.executive.section.repository")}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("dashboard.executive.repositoryHint")}
              </Typography>
            </Box>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={3}>
              <Typography variant="overline" color="text.secondary" component="div">
                {t("dashboard.executive.kpi.cards")}
              </Typography>
              <Typography variant="h5" fontWeight={700}>
                {portfolio.total_cards}
              </Typography>
              {portfolio.last_updated && (
                <Typography variant="caption" color="text.secondary">
                  {t("dashboard.executive.lastUpdated", { date: formatDate(portfolio.last_updated) })}
                </Typography>
              )}
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Tooltip title={t("dashboard.executive.dataCompletenessHint")}>
                <Typography variant="overline" color="text.secondary" component="div">
                  {t("dashboard.executive.dataCompleteness")}
                </Typography>
              </Tooltip>
              <Typography variant="h5" fontWeight={700}>
                {portfolio.data_completeness}%
              </Typography>
              <DrillLink to="/reports/data-quality" label={t("dashboard.executive.open")} />
            </Grid>
            <Grid item xs={12} md={6}>
              <Tooltip title={t("dashboard.executive.reviewStatusHint")}>
                <Typography variant="overline" color="text.secondary" component="div">
                  {t("dashboard.executive.reviewStatus")}
                </Typography>
              </Tooltip>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                {Object.entries(portfolio.approval).map(([status, n]) => (
                  <Chip key={status} size="small" variant="outlined" label={`${t(`dashboard.executive.review.${status}`, { defaultValue: status })}: ${n}`} />
                ))}
              </Box>
            </Grid>
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
              <Box sx={{ textAlign: "center" }}>
                <DrillLink to="/reports/lifecycle" label={t("dashboard.executive.viewLifecycle")} />
              </Box>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
        {t("dashboard.executive.footnote")}
      </Typography>
    </Box>
  );
}
