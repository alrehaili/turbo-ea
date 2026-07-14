import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid";
import LinearProgress from "@mui/material/LinearProgress";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { useTheme } from "@mui/material/styles";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useMetamodel } from "@/hooks/useMetamodel";
import { useTypeLabel } from "@/hooks/useResolveLabel";
import { useIsRtl } from "@/hooks/useIsRtl";
import { api } from "@/api/client";
import { APPROVAL_STATUS_COLORS, DATA_QUALITY_COLORS, STATUS_COLORS } from "@/theme/tokens";
import type { DashboardData } from "@/types";
import TrendIndicator from "./TrendIndicator";
import RecentActivity from "./RecentActivity";
import AdmDashboardWidget from "@/features/adm/AdmDashboardWidget";
import { makeRtlAxisTick, rtlLegendItemStyle, mirrorChartMargin } from "@/lib/rechartsRtl";

const DATA_QUALITY_LABELS: Record<string, string> = {
  "0-25": "0 - 25%",
  "25-50": "25 - 50%",
  "50-75": "50 - 75%",
  "75-100": "75 - 100%",
};

const RADIAN = Math.PI / 180;

export default function OverviewTab() {
  const navigate = useNavigate();
  const theme = useTheme();
  const isRtl = useIsRtl();
  const { t } = useTranslation("common");

  // In RTL the inherited document `direction` flips how SVG text-anchor resolves,
  // so default axis ticks render over the bars; this anchors them outside instead.
  const rtlAxisTick = makeRtlAxisTick(theme.palette.text.secondary);
  const { types } = useMetamodel();
  const typeLabel = useTypeLabel();
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    api.get<DashboardData>("/reports/dashboard").then(setData);
  }, []);

  const typeChartData = useMemo(() => {
    if (!data) return [];
    return types
      .filter((t) => (data.by_type[t.key] ?? 0) > 0)
      .map((t) => ({ name: typeLabel(t), count: data.by_type[t.key] || 0, color: t.color, key: t.key }))
      .sort((a, b) => b.count - a.count);
  }, [data, types]);

  const approvalChartData = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.approval_statuses)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => ({
        name: t(`status.${k.toLowerCase()}`) || k,
        value: v,
        color:
          APPROVAL_STATUS_COLORS[k as keyof typeof APPROVAL_STATUS_COLORS] ||
          STATUS_COLORS.neutral,
        key: k,
      }));
  }, [data, t]);

  const dataQualityChartData = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.data_quality_distribution).map(([k, v]) => ({
      name: DATA_QUALITY_LABELS[k] || k,
      count: v,
      color: DATA_QUALITY_COLORS[k as keyof typeof DATA_QUALITY_COLORS] || STATUS_COLORS.neutral,
    }));
  }, [data]);

  const lifecyclePhases = useMemo(() => [
    { key: "plan", label: t("lifecycle.plan"), color: STATUS_COLORS.neutral },
    { key: "phaseIn", label: t("lifecycle.phaseIn"), color: STATUS_COLORS.info },
    { key: "active", label: t("lifecycle.active"), color: STATUS_COLORS.success },
    { key: "phaseOut", label: t("lifecycle.phaseOut"), color: STATUS_COLORS.warning },
    { key: "endOfLife", label: t("lifecycle.endOfLife"), color: STATUS_COLORS.error },
    { key: "none", label: t("lifecycle.notSet"), color: STATUS_COLORS.neutral },
  ], [t]);

  const lifecycleChartData = useMemo(() => {
    if (!data) return [];
    return lifecyclePhases.map((p) => ({
      name: p.label,
      count: data.lifecycle_distribution[p.key] || 0,
      color: p.color,
    }));
  }, [data, lifecyclePhases]);

  if (!data) return <LinearProgress />;

  return (
    <Box>
      {/* -------- KPI summary cards -------- */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 1 }}>
        <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 700, letterSpacing: 1 }}>
          {t("dashboard.section.kpis")}
        </Typography>
        {data.trends && (
          <Tooltip title={t("dashboard.trend.caption")}>
            <IconButton size="small" aria-label={t("dashboard.trend.aria")}>
              <MaterialSymbol icon="info" size={14} color="disabled" />
            </IconButton>
          </Tooltip>
        )}
      </Box>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderLeft: `4px solid ${STATUS_COLORS.info}`, height: "100%" }} aria-label={`${t("dashboard.totalCards")}: ${data.total_cards}`}>
            <CardContent>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1, gap: 1 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
                  <MaterialSymbol icon="inventory_2" size={22} color={STATUS_COLORS.info} />
                  <Typography variant="subtitle2" color="text.secondary" noWrap>{t("dashboard.totalCards")}</Typography>
                </Box>
                {data.trends && (
                  <TrendIndicator
                    deltaPct={data.trends.total_cards.delta_pct}
                    deltaAbs={data.trends.total_cards.delta_abs}
                    goodDirection="up"
                  />
                )}
              </Box>
              <Typography variant="h4" fontWeight={700}>{data.total_cards}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderLeft: `4px solid ${STATUS_COLORS.success}`, height: "100%" }} aria-label={`${t("dashboard.avgCompletion")}: ${data.avg_data_quality}%`}>
            <CardContent>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1, gap: 1 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
                  <MaterialSymbol icon="pie_chart" size={22} color={STATUS_COLORS.success} />
                  <Typography variant="subtitle2" color="text.secondary" noWrap>{t("dashboard.avgCompletion")}</Typography>
                </Box>
                {data.trends && (
                  <TrendIndicator
                    deltaPct={data.trends.avg_data_quality.delta_pct}
                    goodDirection="up"
                  />
                )}
              </Box>
              <Typography variant="h4" fontWeight={700}>{data.avg_data_quality}%</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderLeft: `4px solid ${APPROVAL_STATUS_COLORS.APPROVED}`, height: "100%" }} aria-label={`${t("status.approved")}: ${data.approval_statuses["APPROVED"] || 0}`}>
            <CardContent>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1, gap: 1 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
                  <MaterialSymbol icon="verified" size={22} color={APPROVAL_STATUS_COLORS.APPROVED} />
                  <Typography variant="subtitle2" color="text.secondary" noWrap>{t("status.approved")}</Typography>
                </Box>
                {data.trends && (
                  <TrendIndicator
                    deltaPct={data.trends.approved_count.delta_pct}
                    deltaAbs={data.trends.approved_count.delta_abs}
                    goodDirection="up"
                  />
                )}
              </Box>
              <Typography variant="h4" fontWeight={700}>{data.approval_statuses["APPROVED"] || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderLeft: `4px solid ${APPROVAL_STATUS_COLORS.BROKEN}`, height: "100%" }} aria-label={`${t("status.broken")}: ${data.approval_statuses["BROKEN"] || 0}`}>
            <CardContent>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1, gap: 1 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
                  <MaterialSymbol icon="warning" size={22} color={APPROVAL_STATUS_COLORS.BROKEN} />
                  <Typography variant="subtitle2" color="text.secondary" noWrap>{t("status.broken")}</Typography>
                </Box>
                {data.trends && (
                  <TrendIndicator
                    deltaPct={data.trends.broken_count.delta_pct}
                    deltaAbs={data.trends.broken_count.delta_abs}
                    goodDirection="down"
                  />
                )}
              </Box>
              <Typography variant="h4" fontWeight={700}>{data.approval_statuses["BROKEN"] || 0}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* -------- Needs attention band -------- */}
      {(() => {
        const brokenCount = data.approval_statuses["BROKEN"] || 0;
        const lowQualityCount =
          (data.data_quality_distribution["0-25"] || 0) +
          (data.data_quality_distribution["25-50"] || 0);
        const eolCount = data.lifecycle_distribution["endOfLife"] || 0;
        const draftCount = data.approval_statuses["DRAFT"] || 0;
        const attention = [
          {
            key: "broken",
            icon: "report",
            color: APPROVAL_STATUS_COLORS.BROKEN,
            label: t("dashboard.attention.broken"),
            count: brokenCount,
            to: "/inventory?approval_status=BROKEN",
          },
          {
            key: "lowQuality",
            icon: "data_alert",
            color: STATUS_COLORS.error,
            label: t("dashboard.attention.lowQuality"),
            count: lowQualityCount,
            to: "/reports/data-quality",
          },
          {
            key: "eol",
            icon: "hourglass_bottom",
            color: STATUS_COLORS.warning,
            label: t("dashboard.attention.eol"),
            count: eolCount,
            to: "/reports/lifecycle",
          },
          {
            key: "draft",
            icon: "edit_note",
            color: STATUS_COLORS.neutral,
            label: t("dashboard.attention.draft"),
            count: draftCount,
            to: "/inventory?approval_status=DRAFT",
          },
        ];
        const visible = attention.filter((a) => a.count > 0);
        if (visible.length === 0) return null;
        return (
          <Box sx={{ mb: 3 }}>
            <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 700, letterSpacing: 1, display: "block", mb: 1 }}>
              {t("dashboard.attention.title")}
            </Typography>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: `repeat(${Math.min(visible.length, 4)}, 1fr)` },
                gap: 1.25,
              }}
            >
              {visible.map((row) => (
                <Paper
                  key={row.key}
                  variant="outlined"
                  component={RouterLink}
                  to={row.to}
                  aria-label={`${row.label}: ${row.count}`}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1.25,
                    p: 1.25,
                    textDecoration: "none",
                    color: "text.primary",
                    borderRadius: 1,
                    transition: "border-color 120ms, box-shadow 120ms",
                    "&:hover": { borderColor: row.color, boxShadow: 2 },
                    "&:focus-visible": { outline: `2px solid ${row.color}`, outlineOffset: 2 },
                  }}
                >
                  <Box
                    sx={{
                      width: 36,
                      height: 36,
                      borderRadius: 1,
                      bgcolor: `${row.color}1a`,
                      color: row.color,
                      display: "grid",
                      placeItems: "center",
                      flexShrink: 0,
                    }}
                  >
                    <MaterialSymbol icon={row.icon} size={20} color="inherit" />
                  </Box>
                  <Box sx={{ minWidth: 0, flex: 1 }}>
                    <Typography variant="body2" sx={{ fontWeight: 700 }} noWrap>
                      {row.label}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {t("dashboard.attention.openLink")}
                    </Typography>
                  </Box>
                  <Typography variant="h5" sx={{ fontWeight: 800, color: row.color }}>
                    {row.count}
                  </Typography>
                  <MaterialSymbol icon="arrow_forward" size={16} color="disabled" />
                </Paper>
              ))}
            </Box>
          </Box>
        );
      })()}

      {/* -------- Row 2: Type bar chart + Approval status donut -------- */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={7}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", mb: 1 }}>
                <Typography variant="subtitle1" fontWeight={600}>
                  {t("dashboard.cardsByType")}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("dashboard.cardsByType.hint")}
                </Typography>
              </Box>
              {typeChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={Math.max(typeChartData.length * 38, 200)}>
                  <BarChart data={typeChartData} layout="vertical" margin={{ left: 16, right: 16, top: 4, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={theme.palette.divider} />
                    <XAxis type="number" allowDecimals={false} reversed={isRtl} tick={{ fill: theme.palette.text.secondary }} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={150}
                      orientation={isRtl ? "right" : "left"}
                      tickMargin={8}
                      tick={isRtl ? rtlAxisTick : { fontSize: 12, fill: theme.palette.text.secondary }}
                      tickLine={false}
                    />
                    <RTooltip
                      cursor={{ fill: theme.palette.action.hover }}
                      contentStyle={{
                        backgroundColor: theme.palette.background.paper,
                        borderColor: theme.palette.divider,
                        color: theme.palette.text.primary,
                        direction: isRtl ? "rtl" : "ltr",
                        textAlign: isRtl ? "right" : "left",
                      }}
                      labelStyle={{ color: theme.palette.text.primary }}
                      itemStyle={{ color: theme.palette.text.primary }}
                    />
                    <Bar
                      dataKey="count"
                      name={t("labels.count")}
                      radius={isRtl ? [4, 0, 0, 4] : [0, 4, 4, 0]}
                      cursor="pointer"
                      onClick={(_data, _idx) => {
                        const key = typeChartData[_idx]?.key;
                        if (key) navigate(`/inventory?type=${key}`);
                      }}
                    >
                      {typeChartData.map((d, i) => (
                        <Cell key={i} fill={d.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Typography variant="body2" color="text.secondary">{t("dashboard.noCardsYet")}</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={5}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                {t("dashboard.approvalStatusDistribution")}
              </Typography>
              {approvalChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart margin={{ top: 12, right: 16, bottom: 12, left: 16 }}>
                    <Pie
                      data={approvalChartData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={46}
                      outerRadius={78}
                      paddingAngle={2}
                      cursor="pointer"
                      labelLine={false}
                      label={({ cx, cy, midAngle, outerRadius, value }: {
                        cx?: number;
                        cy?: number;
                        midAngle?: number;
                        outerRadius?: number;
                        value?: number;
                      }) => {
                        if (cx == null || cy == null || midAngle == null || outerRadius == null) return null;
                        const r = outerRadius + 14;
                        const x = cx + r * Math.cos(-midAngle * RADIAN);
                        const y = cy + r * Math.sin(-midAngle * RADIAN);
                        return (
                          <text
                            x={x}
                            y={y}
                            fill={theme.palette.text.secondary}
                            fontSize={12}
                            textAnchor={x >= cx ? "start" : "end"}
                            dominantBaseline="central"
                          >
                            {value ?? 0}
                          </text>
                        );
                      }}
                      onClick={(_data, idx) => {
                        const status = approvalChartData[idx]?.key;
                        if (status) navigate(`/inventory?approval_status=${status}`);
                      }}
                    >
                      {approvalChartData.map((d, i) => (
                        <Cell key={i} fill={d.color} />
                      ))}
                    </Pie>
                    <RTooltip
                      cursor={{ fill: theme.palette.action.hover }}
                      contentStyle={{
                        backgroundColor: theme.palette.background.paper,
                        borderColor: theme.palette.divider,
                        color: theme.palette.text.primary,
                        direction: isRtl ? "rtl" : "ltr",
                        textAlign: isRtl ? "right" : "left",
                      }}
                      labelStyle={{ color: theme.palette.text.primary }}
                      itemStyle={{ color: theme.palette.text.primary }}
                    />
                    <Legend
                      align={isRtl ? "right" : "left"}
                      wrapperStyle={{ direction: isRtl ? "rtl" : "ltr" }}
                      formatter={(value: string) => (
                        <span style={rtlLegendItemStyle(isRtl, theme.palette.text.primary)}>{value}</span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <Typography variant="body2" color="text.secondary">{t("emptyStates.noData")}</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* -------- Row 3: Completion distribution + Lifecycle overview -------- */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                {t("dashboard.completionDistribution")}
              </Typography>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={dataQualityChartData} margin={mirrorChartMargin({ left: 0, right: 16, top: 8, bottom: 4 }, isRtl)}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                  <XAxis dataKey="name" reversed={isRtl} tick={{ fontSize: 12, fill: theme.palette.text.secondary }} />
                  <YAxis allowDecimals={false} orientation={isRtl ? "right" : "left"} tick={isRtl ? rtlAxisTick : { fill: theme.palette.text.secondary }} />
                  <RTooltip
                    cursor={{ fill: theme.palette.action.hover }}
                    contentStyle={{
                      backgroundColor: theme.palette.background.paper,
                      borderColor: theme.palette.divider,
                      color: theme.palette.text.primary,
                      direction: isRtl ? "rtl" : "ltr",
                      textAlign: isRtl ? "right" : "left",
                    }}
                    labelStyle={{ color: theme.palette.text.primary }}
                    itemStyle={{ color: theme.palette.text.primary }}
                  />
                  <Bar
                    dataKey="count"
                    name={t("labels.cards")}
                    radius={[4, 4, 0, 0]}
                    cursor="pointer"
                    onClick={() => navigate("/reports/data-quality")}
                  >
                    {dataQualityChartData.map((d, i) => (
                      <Cell key={i} fill={d.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                {t("dashboard.lifecycleOverview")}
              </Typography>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={lifecycleChartData} margin={mirrorChartMargin({ left: 0, right: 16, top: 8, bottom: 4 }, isRtl)}>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                  <XAxis dataKey="name" reversed={isRtl} tick={{ fontSize: 12, fill: theme.palette.text.secondary }} />
                  <YAxis allowDecimals={false} orientation={isRtl ? "right" : "left"} tick={isRtl ? rtlAxisTick : { fill: theme.palette.text.secondary }} />
                  <RTooltip
                    cursor={{ fill: theme.palette.action.hover }}
                    contentStyle={{
                      backgroundColor: theme.palette.background.paper,
                      borderColor: theme.palette.divider,
                      color: theme.palette.text.primary,
                      direction: isRtl ? "rtl" : "ltr",
                      textAlign: isRtl ? "right" : "left",
                    }}
                    labelStyle={{ color: theme.palette.text.primary }}
                    itemStyle={{ color: theme.palette.text.primary }}
                  />
                  <Bar
                    dataKey="count"
                    name={t("labels.cards")}
                    radius={[4, 4, 0, 0]}
                    cursor="pointer"
                    onClick={() => navigate("/reports/lifecycle")}
                  >
                    {lifecycleChartData.map((d, i) => (
                      <Cell key={i} fill={d.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* -------- Row 4: Recent Activity + My ADM actions widget -------- */}
      <Grid container spacing={2}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <RecentActivity events={data.recent_events} />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <AdmDashboardWidget />
        </Grid>
      </Grid>
    </Box>
  );
}
