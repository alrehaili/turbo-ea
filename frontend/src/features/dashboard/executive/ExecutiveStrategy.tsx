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
import MaterialSymbol from "@/components/MaterialSymbol";
import { useAuthContext } from "@/hooks/AuthContext";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useDateFormat } from "@/hooks/useDateFormat";
import { canAccessPath } from "@/lib/routePermissions";
import type { ExecutiveStrategyData, StrategyKpiState } from "@/types";
import { pct } from "./executiveFormat";

const STATE_COLOR: Record<StrategyKpiState, "success" | "warning" | "default"> = {
  on_target: "success",
  off_target: "warning",
  not_measured: "default",
  no_ratified_target: "default",
  no_direction: "default",
  definition_not_approved: "default",
};

function CardLink({ path, name }: { path: string; name: string }) {
  const { user } = useAuthContext();
  return canAccessPath(user?.permissions, path.split("?")[0]) ? (
    <Link component={RouterLink} to={path} underline="hover" dir="auto">
      {name}
    </Link>
  ) : (
    <bdi>{name}</bdi>
  );
}

/**
 * Strategy achievement (TR-01, decision D-21) for the current period: which
 * strategic KPIs are on target, by objective and pillar, with each KPI's
 * evidence state. Strategy execution (delivery of the supporting initiatives)
 * is a separate panel and never folded into the outcome figures.
 */
export default function ExecutiveStrategy() {
  const { t } = useTranslation("common");
  const { formatDateTime } = useDateFormat();
  const { data, error, loading } = useApiQuery<ExecutiveStrategyData>("/reports/executive/strategy");

  if (error) return <Alert severity="error">{error.message || t("errors.generic")}</Alert>;
  if (!data) return loading ? <LinearProgress /> : null;

  const totals = data.totals;
  const rollup = (r: { on_target: number; measured: number; linked: number }) =>
    t("dashboard.executive.strategy.rollup", {
      onTarget: r.on_target,
      measured: r.measured,
      linked: r.linked,
    });

  return (
    <Box>
      <Typography variant="h6" fontWeight={700}>
        {t("dashboard.executive.strategy.title")}
      </Typography>
      <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 2 }}>
        {t("dashboard.executive.strategy.subtitle")} ·{" "}
        {t("dashboard.executive.generatedAt", { time: formatDateTime(data.generated_at) })}
      </Typography>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} md={7}>
          <Card variant="outlined" sx={{ height: "100%" }} data-testid="strategy-outcomes">
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700}>
                {t("dashboard.executive.strategy.outcomes")}
              </Typography>
              {totals.linked === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {t("dashboard.executive.strategy.noKpis")}
                </Typography>
              ) : (
                <>
                  <Typography variant="h4" fontWeight={700}>
                    {totals.measured > 0
                      ? t("dashboard.executive.ceo.strategyValue", {
                          onTarget: totals.on_target,
                          measured: totals.measured,
                        })
                      : t("dashboard.executive.ceo.notAvailable")}
                  </Typography>
                  <Typography variant="body2" fontWeight={700}>
                    {t("dashboard.executive.ceo.strategyCoverage", {
                      measured: totals.measured,
                      linked: totals.linked,
                    })}
                  </Typography>
                  <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mt: 1 }}>
                    {(Object.keys(totals.by_state) as StrategyKpiState[])
                      .filter((s) => totals.by_state[s] > 0)
                      .map((s) => (
                        <Chip
                          key={s}
                          size="small"
                          variant="outlined"
                          color={STATE_COLOR[s]}
                          label={`${t(`dashboard.executive.strategy.state.${s}`)}: ${totals.by_state[s]}`}
                        />
                      ))}
                  </Box>
                </>
              )}
              {data.unlinked_objectives > 0 && (
                <Typography variant="caption" color="text.secondary" component="div" sx={{ mt: 1 }}>
                  {t("dashboard.executive.strategy.unlinkedObjectives", {
                    count: data.unlinked_objectives,
                  })}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={5}>
          <Card variant="outlined" sx={{ height: "100%" }} data-testid="strategy-execution-panel">
            <CardContent>
              <Typography variant="subtitle1" fontWeight={700}>
                {t("dashboard.executive.strategy.execution")}
              </Typography>
              <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1 }}>
                {t("dashboard.executive.strategy.executionHint")}
              </Typography>
              {data.execution.initiatives === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {t("dashboard.executive.strategy.noInitiatives")}
                </Typography>
              ) : (
                <>
                  <Typography variant="h5" fontWeight={700}>
                    {pct(data.execution.on_track_pct) ?? t("dashboard.executive.ceo.notAvailable")}
                  </Typography>
                  <Typography variant="body2">
                    {t("dashboard.executive.ceo.coverage", {
                      reported: data.execution.coverage.reported,
                      total: data.execution.coverage.in_flight,
                    })}
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {data.pillars.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
            {t("dashboard.executive.strategy.pillars")}
          </Typography>
          <Grid container spacing={1}>
            {data.pillars.map((p) => (
              <Grid item xs={12} sm={6} md={4} key={p.id}>
                <Card variant="outlined">
                  <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                    <Typography variant="body2" fontWeight={700}>
                      <CardLink path={p.path} name={p.name} />
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {rollup(p)}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
        {t("dashboard.executive.strategy.objectives")}
      </Typography>
      {data.objectives.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          {t("dashboard.executive.strategy.noObjectives")}
        </Typography>
      ) : (
        data.objectives.map((o) => (
          <Card variant="outlined" key={o.id} sx={{ mb: 1.5 }}>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                <MaterialSymbol icon="flag" size={18} />
                <Typography variant="body1" fontWeight={700} sx={{ flex: 1, minWidth: 0 }}>
                  <CardLink path={o.path} name={o.name} />
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {rollup(o)}
                </Typography>
              </Box>
              {o.kpis.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  {t("dashboard.executive.strategy.noLinkedKpis")}
                </Typography>
              ) : (
                <Box sx={{ overflowX: "auto", mt: 1 }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>{t("dashboard.executive.strategy.col.kpi")}</TableCell>
                        <TableCell align="right">{t("dashboard.executive.strategy.col.actual")}</TableCell>
                        <TableCell align="right">{t("dashboard.executive.strategy.col.target")}</TableCell>
                        <TableCell align="right">{t("dashboard.executive.strategy.col.attainment")}</TableCell>
                        <TableCell>{t("dashboard.executive.strategy.col.state")}</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {o.kpis.map((k) => (
                        <TableRow key={k.id}>
                          <TableCell sx={{ minWidth: 160, overflowWrap: "break-word" }}>
                            <CardLink path={k.path} name={k.name} />
                            {k.owners.length > 0 && (
                              <Typography variant="caption" color="text.secondary" component="div">
                                {t("dashboard.executive.ceo.ownerName", { name: k.owners.join(", ") })}
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell align="right">
                            <bdi>{k.value ?? "—"}</bdi>
                          </TableCell>
                          <TableCell align="right">
                            <bdi>{k.target.value ?? "—"}</bdi>
                            {k.target.status !== "none" && (
                              <Typography variant="caption" color="text.secondary" component="div">
                                {t(`dashboard.executive.ceo.targetState.${k.target.status}`)}
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell align="right">{pct(k.attainment) ?? "—"}</TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              variant="outlined"
                              color={STATE_COLOR[k.state]}
                              label={t(`dashboard.executive.strategy.state.${k.state}`)}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>
              )}
            </CardContent>
          </Card>
        ))
      )}
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
        {t("dashboard.executive.strategy.footnote")}
      </Typography>
    </Box>
  );
}
