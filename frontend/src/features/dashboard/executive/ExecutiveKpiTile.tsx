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
  /** Supporting figures under the value (states, coverage, forecast …). */
  children?: ReactNode;
}) {
  const { t } = useTranslation("common");
  const { user } = useAuthContext();
  const { formatDate } = useDateFormat();
  const available = kpi.status === "ok";
  const drillPath = kpi.drilldown?.path;
  const showDrill = drillPath && canAccessPath(user?.permissions, drillPath.split("?")[0]);

  const reason = kpi.reason
    ? t(`dashboard.executive.reason.${kpi.reason.code}`, {
        decisions: (kpi.reason.decisions ?? []).join(", "),
        phase: kpi.reason.phase,
        defaultValue: kpi.reason.code,
      })
    : null;

  const previousText =
    kpi.previous.status === "ok" && previousValue
      ? t("dashboard.executive.ceo.previous", { value: previousValue, period: kpi.previous.period })
      : kpi.previous.reason === "no_history"
        ? t("dashboard.executive.ceo.noHistory")
        : t("dashboard.executive.ceo.previousNotAvailable", { period: kpi.previous.period ?? "" });

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
              {t("dashboard.executive.ceo.notAvailable")}
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
            [t("dashboard.executive.ceo.target"), t(`dashboard.executive.ceo.targetState.${kpi.target.status}`)],
            [t("dashboard.executive.ceo.previousLabel"), previousText],
            [t("dashboard.executive.ceo.periodLabel"), periodText],
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
          {showDrill && (
            <Link component={RouterLink} to={drillPath} variant="caption" underline="hover">
              {t("dashboard.executive.ceo.viewRecords")}
            </Link>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
