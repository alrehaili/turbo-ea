import { useState, useEffect } from "react";
import { Link as RouterLink } from "react-router-dom";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import CircularProgress from "@mui/material/CircularProgress";
import { useTranslation } from "react-i18next";
import { useTheme } from "@mui/material/styles";
import { useCurrency } from "@/hooks/useCurrency";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useResolveLabel } from "@/hooks/useResolveLabel";
import { api } from "@/api/client";
import type { Card, PpmStatusReport, PpmCostLine, PpmBudgetLine } from "@/types";

const RAG_COLORS: Record<string, string> = {
  onTrack: "#2e7d32",
  atRisk: "#ed6c02",
  offTrack: "#d32f2f",
};

/** A relation with just the ends we need to spot KPI links. */
interface RelationLite {
  type: string;
  source?: { id: string; type: string; name: string };
  target?: { id: string; type: string; name: string };
}

/** A KPI card reduced to what the overview renders. */
interface LinkedKpi {
  id: string;
  name: string;
  unit: string | null;
  progressPct: number | null; // direction-aware, clamped 0–100
  onTrack: boolean | null;
}

function _num(v: unknown): number | null {
  const n = typeof v === "number" ? v : parseFloat(String(v ?? ""));
  return Number.isFinite(n) ? n : null;
}

/** Reduce a KPI card to direction-aware progress toward its target. */
function toLinkedKpi(c: Card): LinkedKpi {
  const a = c.attributes || {};
  const baseline = _num(a.baselineValue);
  const target = _num(a.targetValue);
  const current = _num(a.currentValue);
  const higherBetter = a.direction !== "lowerIsBetter";

  let progressPct: number | null = null;
  let onTrack: boolean | null = null;
  if (target !== null && current !== null) {
    const base = baseline ?? 0;
    const span = target - base;
    if (span !== 0) {
      const pct = ((current - base) / span) * 100;
      progressPct = Math.max(0, Math.min(100, pct));
    } else {
      progressPct = current === target ? 100 : 0;
    }
    onTrack = higherBetter ? current >= target : current <= target;
  }
  return {
    id: c.id,
    name: c.name,
    unit: (a.unit as string) || null,
    progressPct,
    onTrack,
  };
}

interface Props {
  card: Card;
  latestReport: PpmStatusReport | null;
  costLines: PpmCostLine[];
  budgetLines: PpmBudgetLine[];
}

/** Format a number in compact "k" notation */
function fmtK(n: number): string {
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(0)}k`;
  return String(Math.round(n));
}

/** Reusable budget vs actual bar */
function BudgetBar({
  label,
  budget,
  actual,
  currency,
  barColor,
  overColor,
}: {
  label: string;
  budget: number;
  actual: number;
  currency: string;
  barColor: string;
  overColor: string;
}) {
  const pct = budget > 0 ? Math.min((actual / budget) * 100, 100) : 0;
  const over = actual > budget && budget > 0;
  const color = over ? overColor : barColor;
  const useK = Math.abs(budget) >= 1_000 || Math.abs(actual) >= 1_000;
  const unit = useK ? `k${currency}` : currency;
  const aVal = useK ? fmtK(actual) : String(Math.round(actual));
  const pVal = useK ? fmtK(budget) : String(Math.round(budget));

  return (
    <Box sx={{ mb: 1.5 }}>
      <Box display="flex" justifyContent="space-between" alignItems="baseline" mb={0.25}>
        <Typography variant="body2" fontWeight={500}>
          {label}
        </Typography>
        <Typography
          variant="caption"
          sx={{ color: over ? overColor : "text.secondary" }}
        >
          {aVal}/{pVal} {unit}
          {budget > 0 && ` (${Math.round((actual / budget) * 100)}%)`}
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={pct}
        sx={{
          height: 10,
          borderRadius: 5,
          bgcolor: "action.hover",
          "& .MuiLinearProgress-bar": {
            bgcolor: color,
            borderRadius: 5,
          },
        }}
      />
    </Box>
  );
}

export default function PpmOverviewTab({
  card,
  latestReport,
  costLines,
  budgetLines,
}: Props) {
  const { t } = useTranslation("ppm");
  const theme = useTheme();
  const { fmt, currency } = useCurrency();
  const { getType } = useMetamodel();
  const rl = useResolveLabel();
  const attrs = card.attributes || {};
  const budgetBarColor = theme.palette.primary.main;
  const overBudgetColor = theme.palette.error.dark;

  // Fetch initiative completion
  const [completionPct, setCompletionPct] = useState<number | null>(null);
  useEffect(() => {
    api
      .get<{ completion: number }>(`/ppm/initiatives/${card.id}/completion`)
      .then((r) => setCompletionPct(r.completion))
      .catch(() => {});
  }, [card.id]);

  // Linked KPIs (WP4.2): initiatives that "improve" KPI cards surface them
  // here with live progress, and deep-link to the KPI Scorecard.
  const [kpis, setKpis] = useState<LinkedKpi[]>([]);
  useEffect(() => {
    let cancelled = false;
    api
      .get<RelationLite[]>(`/relations?card_id=${card.id}`)
      .then(async (rels) => {
        // Collect KPI card ids on either end of a KPI relation.
        const kpiIds = new Set<string>();
        for (const r of rels) {
          if (r.target?.type === "KPI") kpiIds.add(r.target.id);
          if (r.source?.type === "KPI") kpiIds.add(r.source.id);
        }
        if (kpiIds.size === 0) {
          if (!cancelled) setKpis([]);
          return;
        }
        const cards = await Promise.all(
          [...kpiIds].map((id) =>
            api.get<Card>(`/cards/${id}`).catch(() => null),
          ),
        );
        if (cancelled) return;
        setKpis(
          cards
            .filter((c): c is Card => c !== null)
            .map((c) => toLinkedKpi(c)),
        );
      })
      .catch(() => {
        if (!cancelled) setKpis([]);
      });
    return () => {
      cancelled = true;
    };
  }, [card.id]);

  // Budget totals (from budget lines)
  const totalBudget = budgetLines.reduce((s, bl) => s + bl.amount, 0);
  const capexBudget = budgetLines
    .filter((b) => b.category === "capex")
    .reduce((s, b) => s + b.amount, 0);
  const opexBudget = budgetLines
    .filter((b) => b.category === "opex")
    .reduce((s, b) => s + b.amount, 0);

  // Actual totals (from cost lines)
  const totalActual = costLines.reduce((s, cl) => s + cl.actual, 0);
  const capexActual = costLines
    .filter((c) => c.category === "capex")
    .reduce((s, c) => s + c.actual, 0);
  const opexActual = costLines
    .filter((c) => c.category === "opex")
    .reduce((s, c) => s + c.actual, 0);

  const variance = totalBudget - totalActual;

  const typeConfig = getType(card.type);

  // Resolve a select field value to its translated label
  const resolveOption = (fieldKey: string, value: unknown): string => {
    if (!value || typeof value !== "string") return "\u2014";
    for (const section of typeConfig?.fields_schema || []) {
      for (const field of section.fields || []) {
        if (field.key === fieldKey && field.options) {
          const opt = field.options.find((o: { key: string }) => o.key === value);
          if (opt) return rl(opt.label, opt.translations);
        }
      }
    }
    return value;
  };

  // Resolve subtype to translated label
  const resolveSubtype = (subtype: string | null | undefined): string | null => {
    if (!subtype || !typeConfig?.subtypes) return subtype || null;
    const st = typeConfig.subtypes.find((s: { key: string }) => s.key === subtype);
    return st ? rl(st.label, st.translations) : subtype;
  };

  const HealthDot = ({ value, label }: { value: string; label: string }) => (
    <Box display="flex" alignItems="center" gap={1}>
      <Box
        sx={{
          width: 16,
          height: 16,
          borderRadius: "50%",
          bgcolor: RAG_COLORS[value] || "#bdbdbd",
        }}
      />
      <Typography variant="body2">{label}</Typography>
    </Box>
  );

  return (
    <Grid container spacing={2}>
      {/* Health Summary */}
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="subtitle1" fontWeight={600} mb={2}>
            {t("healthSummary")}
          </Typography>
          {latestReport ? (
            <Box display="flex" gap={4}>
              <HealthDot
                value={latestReport.schedule_health}
                label={t("health_schedule")}
              />
              <HealthDot
                value={latestReport.cost_health}
                label={t("health_cost")}
              />
              <HealthDot
                value={latestReport.scope_health}
                label={t("health_scope")}
              />
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              {t("noReportsYet")}
            </Typography>
          )}
        </Paper>
      </Grid>

      {/* Completion KPI */}
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="subtitle1" fontWeight={600} mb={2}>
            {t("completion")}
          </Typography>
          {completionPct !== null ? (
            <Box display="flex" alignItems="center" gap={2}>
              <Box sx={{ position: "relative", display: "inline-flex" }}>
                <CircularProgress
                  variant="determinate"
                  value={completionPct}
                  size={64}
                  thickness={5}
                  sx={{
                    color:
                      completionPct >= 80
                        ? theme.palette.success.main
                        : completionPct >= 40
                          ? theme.palette.warning.main
                          : theme.palette.error.main,
                  }}
                />
                <Box
                  sx={{
                    top: 0,
                    left: 0,
                    bottom: 0,
                    right: 0,
                    position: "absolute",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Typography
                    variant="body2"
                    fontWeight={700}
                    color="text.primary"
                  >
                    {Math.round(completionPct)}%
                  </Typography>
                </Box>
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  {t("completionDesc")}
                </Typography>
              </Box>
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              {t("noWbsItems")}
            </Typography>
          )}
        </Paper>
      </Grid>

      {/* Linked KPIs (WP4.2) */}
      {kpis.length > 0 && (
        <Grid item xs={12}>
          <Paper sx={{ p: 2.5 }}>
            <Box
              sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}
            >
              <Typography variant="subtitle1" fontWeight={600}>
                {t("linkedKpis", "Linked KPIs")}
              </Typography>
              <Link component={RouterLink} to="/reports/kpi-scorecard" underline="hover" variant="body2">
                {t("kpiScorecard", "KPI Scorecard")}
              </Link>
            </Box>
            <Grid container spacing={2}>
              {kpis.map((k) => (
                <Grid item xs={12} sm={6} md={4} key={k.id}>
                  <Box sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.5 }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.5 }}>
                      <Link
                        component={RouterLink}
                        to={`/cards/${k.id}`}
                        underline="hover"
                        sx={{ fontWeight: 600, flex: 1, minWidth: 0 }}
                        noWrap
                      >
                        {k.name}
                      </Link>
                      {k.onTrack !== null && (
                        <Chip
                          size="small"
                          label={k.onTrack ? t("onTrack", "On track") : t("offTrack", "Off track")}
                          sx={{
                            bgcolor: k.onTrack ? RAG_COLORS.onTrack : RAG_COLORS.offTrack,
                            color: "#fff",
                            height: 20,
                          }}
                        />
                      )}
                    </Box>
                    {k.progressPct !== null ? (
                      <>
                        <LinearProgress
                          variant="determinate"
                          value={k.progressPct}
                          sx={{ height: 8, borderRadius: 4, my: 0.5 }}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {Math.round(k.progressPct)}%{k.unit ? ` · ${k.unit}` : ""}
                        </Typography>
                      </>
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        {t("kpiNoValues", "No target/current values yet")}
                      </Typography>
                    )}
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>
      )}

      {/* Financials — KPIs + Budget Bars combined */}
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="subtitle1" fontWeight={600} mb={2}>
            {t("financials")}
          </Typography>
          <Box display="flex" gap={4} mb={2.5}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t("totalBudget")}
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {fmt.format(totalBudget)}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t("totalActual")}
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {fmt.format(totalActual)}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t("variance")}
              </Typography>
              <Typography
                variant="h6"
                fontWeight={600}
                color={variance < 0 ? "error" : "success.main"}
              >
                {fmt.format(variance)}
              </Typography>
            </Box>
          </Box>
          <BudgetBar
            label={t("totalBudget")}
            budget={totalBudget}
            actual={totalActual}
            currency={currency}
            barColor={budgetBarColor}
            overColor={overBudgetColor}
          />
          <BudgetBar
            label={t("capex")}
            budget={capexBudget}
            actual={capexActual}
            currency={currency}
            barColor={budgetBarColor}
            overColor={overBudgetColor}
          />
          <BudgetBar
            label={t("opex")}
            budget={opexBudget}
            actual={opexActual}
            currency={currency}
            barColor={budgetBarColor}
            overColor={overBudgetColor}
          />
        </Paper>
      </Grid>

      {/* Timeline + Status */}
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2.5 }}>
          <Typography variant="subtitle1" fontWeight={600} mb={1}>
            {t("timeline")}
          </Typography>
          <Box display="flex" gap={3} mb={2}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t("startDate")}
              </Typography>
              <Typography variant="body2">
                {(attrs.startDate as string) || "\u2014"}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                {t("endDate")}
              </Typography>
              <Typography variant="body2">
                {(attrs.endDate as string) || "\u2014"}
              </Typography>
            </Box>
            {card.subtype && (
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t("subtype")}
                </Typography>
                <Box mt={0.5}>
                  <Chip
                    label={resolveSubtype(card.subtype)}
                    size="small"
                    variant="outlined"
                  />
                </Box>
              </Box>
            )}
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              {t("initiativeStatus")}
            </Typography>
            <Typography variant="body2">
              {resolveOption("initiativeStatus", attrs.initiativeStatus)}
            </Typography>
          </Box>
        </Paper>
      </Grid>

      {/* Description */}
      {card.description && (
        <Grid item xs={12}>
          <Paper sx={{ p: 2.5 }}>
            <Typography variant="subtitle1" fontWeight={600} mb={1}>
              {t("common:description", "Description")}
            </Typography>
            <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
              {card.description}
            </Typography>
          </Paper>
        </Grid>
      )}
    </Grid>
  );
}
