import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Link from "@mui/material/Link";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useAuthContext } from "@/hooks/AuthContext";
import { useDateFormat } from "@/hooks/useDateFormat";
import { canAccessPath } from "@/lib/routePermissions";
import { STATUS_COLORS } from "@/theme/tokens";
import type { ExecutiveKpi } from "@/types";
import { unavailableReason } from "./executiveFormat";
import { useExecutivePeriod } from "./useExecutivePeriod";

const CONFIDENCE_COLOR = { high: "success", medium: "info", low: "warning" } as const;

/**
 * The standard executive KPI tile (UI_UX_SPECIFICATION §3): actual, target,
 * previous period, period, freshness, owner, confidence and drill-down, from the
 * one KPI contract the backend returns. Anything unknown says so in words —
 * never an empty space and never a zero.
 */
export default function ExecutiveKpiTile({
  kpi,
  icon,
  title,
  description,
  value,
  previousValue,
  periodText,
  formatPeriod = (key) => key,
  children,
}: {
  kpi: ExecutiveKpi;
  icon: string;
  title: string;
  description: string;
  /** The formatted value; ignored unless the KPI's status is `ok`. */
  value?: ReactNode;
  /** The formatted previous-period value, when there is one. */
  previousValue?: string | null;
  periodText: string;
  /** How a period key reads on screen ("Q3 · FY 2026", not "FY2026-Q3"). */
  formatPeriod?: (key: string) => string;
  /** Supporting figures under the value (states, coverage, forecast …). */
  children?: ReactNode;
}) {
  const { t } = useTranslation("common");
  const { user } = useAuthContext();
  const { formatDate } = useDateFormat();
  const { period } = useExecutivePeriod();
  const available = kpi.status === "ok";
  const currentState = kpi.temporal === "current_state";
  const historical = kpi.reason?.code === "historical_unavailable";
  const rawDrill = kpi.drilldown?.path;
  const showDrill = rawDrill && canAccessPath(user?.permissions, rawDrill.split("?")[0]);
  // A link to another Executive page carries the selected period with it.
  const drillPath =
    rawDrill && period && rawDrill.startsWith("/?tab=executive")
      ? `${rawDrill}&period=${encodeURIComponent(period)}`
      : rawDrill;

  const reason = historical
    ? t("dashboard.executive.ceo.historicalUnavailableHint")
    : kpi.reason
      ? unavailableReason(kpi, t)
      : null;

  // The linked KPI card's target (D-26) and its ratification state (D-17a).
  const target = kpi.target;
  const targetValue =
    target.value !== undefined && target.value !== null
      ? t("dashboard.executive.ceo.targetValue", { value: target.value, unit: target.unit ?? "" }).trim()
      : null;
  const targetText =
    targetValue && (target.status === "ratified" || target.status === "unratified")
      ? `${targetValue} · ${t(`dashboard.executive.ceo.targetState.${target.status}`)}${
          target.invalidated ? ` · ${t("dashboard.executive.ceo.targetChanged")}` : ""
        }`
      : t(`dashboard.executive.ceo.targetState.${target.status}`);
  const showCard = kpi.kpi_card && canAccessPath(user?.permissions, `/cards/${kpi.kpi_card.id}`);

  const previousText =
    kpi.previous.status === "ok" && previousValue
      ? t("dashboard.executive.ceo.previous", {
          value: previousValue,
          period: kpi.previous.period ? formatPeriod(kpi.previous.period) : "",
        })
      : kpi.previous.reason === "no_history"
        ? t("dashboard.executive.ceo.noHistory")
        : kpi.previous.reason === "historical_unavailable"
          ? t("dashboard.executive.ceo.historicalUnavailable")
          : t("dashboard.executive.ceo.previousNotAvailable", {
              period: kpi.previous.period ? formatPeriod(kpi.previous.period) : "",
            });

  return (
    <Card
      variant="outlined"
      sx={{ height: "100%", borderTop: 3, borderTopColor: available ? "primary.main" : STATUS_COLORS.neutral }}
      data-testid={`executive-kpi-${kpi.slot}`}
    >
      <CardContent sx={{ display: "flex", flexDirection: "column", gap: 1, height: "100%" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.75 }}>
          <MaterialSymbol icon={icon} size={18} />
          <Typography variant="subtitle2" fontWeight={700} sx={{ flex: 1, minWidth: 0 }}>
            {title}
          </Typography>
          <Tooltip title={description}>
            <Box component="span" sx={{ display: "flex", color: "text.disabled", cursor: "help" }} aria-label={description}>
              <MaterialSymbol icon="info" size={16} color="inherit" />
            </Box>
          </Tooltip>
        </Box>

        {available ? (
          <Typography variant="h4" component="div" fontWeight={700} lineHeight={1.1}>
            {value}
          </Typography>
        ) : (
          <Box>
            <Typography variant="h6" component="div" color="text.secondary" fontWeight={700}>
              {historical ? t("dashboard.executive.ceo.historicalUnavailable") : t("dashboard.executive.ceo.notAvailable")}
            </Typography>
            {reason && (
              <Typography variant="caption" color="text.secondary" component="div">
                {reason}
              </Typography>
            )}
          </Box>
        )}

        {children}

        <Box component="dl" sx={{ m: 0, display: "grid", gridTemplateColumns: "auto 1fr", columnGap: 1, rowGap: 0.25 }}>
          {[
            [t("dashboard.executive.ceo.target"), targetText],
            [t("dashboard.executive.ceo.previousLabel"), previousText],
            [
              t("dashboard.executive.ceo.periodLabel"),
              currentState
                ? t("dashboard.executive.ceo.currentStatePeriod", { date: formatDate(kpi.as_of) })
                : periodText,
            ],
            [
              t("dashboard.executive.ceo.freshness"),
              kpi.freshness ? t("dashboard.executive.ceo.dataFrom", { date: formatDate(kpi.freshness) }) : t("dashboard.executive.ceo.asOf", { date: formatDate(kpi.as_of) }),
            ],
            [t("dashboard.executive.ceo.owner"), kpi.owner.name ?? t(`dashboard.executive.ceo.ownerState.${kpi.owner.status}`)],
          ].map(([label, text]) => (
            <Box key={label} sx={{ display: "contents" }}>
              <Typography component="dt" variant="caption" color="text.secondary">
                {label}
              </Typography>
              <Typography component="dd" variant="caption" sx={{ m: 0, minWidth: 0 }}>
                {text}
              </Typography>
            </Box>
          ))}
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mt: "auto", flexWrap: "wrap" }}>
          {currentState && (
            <Tooltip title={t("dashboard.executive.ceo.currentStateHint")}>
              <Chip
                size="small"
                color="info"
                variant="outlined"
                icon={<MaterialSymbol icon="schedule" size={14} />}
                label={t("dashboard.executive.ceo.currentState")}
                sx={{ height: 20, fontSize: 11 }}
                data-testid="current-state-chip"
              />
            </Tooltip>
          )}
          {kpi.target.achieved !== undefined && kpi.target.achieved !== null && (
            <Chip
              size="small"
              color={kpi.target.achieved ? "success" : "warning"}
              label={t(kpi.target.achieved ? "dashboard.executive.ceo.onTarget" : "dashboard.executive.ceo.belowTarget")}
              sx={{ height: 20, fontSize: 11 }}
              data-testid="target-achieved"
            />
          )}
          {kpi.confidence && (
            <Tooltip title={t("dashboard.executive.ceo.confidenceHint")}>
              <Chip
                size="small"
                variant="outlined"
                color={CONFIDENCE_COLOR[kpi.confidence]}
                label={t(`dashboard.executive.ceo.confidence.${kpi.confidence}`)}
                sx={{ height: 20, fontSize: 11 }}
              />
            </Tooltip>
          )}
          {kpi.provenance && (
            <Chip
              size="small"
              variant="outlined"
              label={t(`dashboard.executive.provenance.${kpi.provenance}`)}
              sx={{ height: 20, fontSize: 11 }}
            />
          )}
          <Box sx={{ flex: 1 }} />
          {showCard && kpi.kpi_card && (
            <Link component={RouterLink} to={`/cards/${kpi.kpi_card.id}`} variant="caption" underline="hover">
              {t("dashboard.executive.ceo.kpiCard")}
            </Link>
          )}
          {showDrill && drillPath && (
            <Link component={RouterLink} to={drillPath} variant="caption" underline="hover">
              {t("dashboard.executive.ceo.viewRecords")}
            </Link>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
