import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import LinearProgress from "@mui/material/LinearProgress";
import List from "@mui/material/List";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useApiQuery } from "@/hooks/useApiQuery";
import { useDateFormat } from "@/hooks/useDateFormat";
import type { ExecutiveDecisionSection, ExecutiveDecisionsData } from "@/types";
import { DecisionItemLine } from "./ExecutiveOverview";

const SECTIONS = [
  { key: "risks", icon: "warning" },
  { key: "adrs", icon: "draw" },
  { key: "arb", icon: "groups" },
  { key: "exceptions", icon: "rule" },
] as const;

function DecisionSection({
  title,
  hint,
  icon,
  section,
  extra,
}: {
  title: string;
  hint: string;
  icon: string;
  section: ExecutiveDecisionSection;
  extra?: ReactNode;
}) {
  const { t } = useTranslation("common");
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <MaterialSymbol icon={icon} size={20} />
          <Typography variant="subtitle1" fontWeight={700} sx={{ flex: 1, minWidth: 0 }}>
            {title}
          </Typography>
          {section.status !== "disabled" && <Chip size="small" label={section.count ?? 0} />}
        </Box>
        <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 1 }}>
          {hint}
        </Typography>
        {extra}
        {section.status === "disabled" && (
          <Typography variant="body2" color="text.secondary">
            {t("dashboard.executive.moduleDisabled")}
          </Typography>
        )}
        {section.status === "restricted" && (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, color: "text.secondary" }}>
            <MaterialSymbol icon="lock" size={18} color="inherit" />
            <Typography variant="body2">{t("dashboard.executive.decisionsPage.restricted")}</Typography>
          </Box>
        )}
        {section.status === "ok" &&
          ((section.items ?? []).length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {t("dashboard.executive.decisionsPage.none")}
            </Typography>
          ) : (
            <List dense disablePadding>
              {(section.items ?? []).map((item) => (
                <DecisionItemLine key={item.id} item={item} />
              ))}
            </List>
          ))}
      </CardContent>
    </Card>
  );
}

/** Escalated risks and pending governance decisions (DEC-01, DEC-02). */
export default function ExecutiveDecisions() {
  const { t } = useTranslation("common");
  const { data, error, loading } = useApiQuery<ExecutiveDecisionsData>("/reports/executive/decisions");
  const { formatDateTime } = useDateFormat();

  if (error) return <Alert severity="error">{error.message || t("errors.generic")}</Alert>;
  if (!data) return loading ? <LinearProgress /> : null;

  return (
    <Box>
      <Typography variant="h6" fontWeight={700}>
        {t("dashboard.executive.decisionsPage.title")}
      </Typography>
      <Typography variant="caption" color="text.secondary" component="div" sx={{ mb: 2 }}>
        {t("dashboard.executive.decisionsPage.subtitle")} ·{" "}
        {t("dashboard.executive.generatedAt", { time: formatDateTime(data.generated_at) })}
      </Typography>
      <Grid container spacing={2}>
        {SECTIONS.map(({ key, icon }) => {
          const section = data[key];
          return (
            <Grid item xs={12} md={6} key={key}>
              <DecisionSection
                title={t(`dashboard.executive.decisionsPage.${key}`)}
                hint={t(`dashboard.executive.decisionsPage.${key}Hint`)}
                icon={icon}
                section={section}
                extra={
                  key === "risks" && section.status !== "disabled" && section.open !== undefined ? (
                    <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 1 }}>
                      <Chip size="small" variant="outlined" label={t("dashboard.executive.decisionsPage.openRisks", { count: section.open })} />
                      <Chip size="small" variant="outlined" label={t("dashboard.executive.decisionsPage.mitigatedRisks", { count: section.mitigated ?? 0 })} />
                      <Chip size="small" variant="outlined" color="error" label={t("dashboard.executive.decisionsPage.escalatedRisks", { count: section.count ?? 0 })} />
                    </Box>
                  ) : undefined
                }
              />
            </Grid>
          );
        })}
      </Grid>
    </Box>
  );
}
