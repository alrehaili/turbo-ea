import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import ReportShell from "./ReportShell";
import MetricCard from "./MetricCard";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useCurrency } from "@/hooks/useCurrency";
import { api } from "@/api/client";

interface CardBrief {
  id: string;
  name: string;
  type: string;
  subtype: string | null;
}

interface StrategyInitiative extends CardBrief {
  status: string | null;
  budget: number | null;
  actual: number | null;
  applications: CardBrief[];
}

interface StrategyObjective extends CardBrief {
  kpi: string | null;
  capabilities: CardBrief[];
  initiatives: StrategyInitiative[];
}

interface StrategyMap {
  objectives: StrategyObjective[];
  summary: {
    objective_count: number;
    initiative_count: number;
    application_count: number;
    total_budget: number;
    total_actual: number;
  };
}

function CardLink({ card }: { card: CardBrief }) {
  return (
    <Box
      component="a"
      href={`/cards/${card.id}`}
      sx={{
        color: "primary.main",
        textDecoration: "none",
        "&:hover": { textDecoration: "underline" },
      }}
    >
      {card.name}
    </Box>
  );
}

export default function ExecutiveStrategyMap() {
  const { t } = useTranslation(["reports", "common"]);
  const { fmtShort } = useCurrency();
  const chartRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<StrategyMap | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.get<StrategyMap>("/reports/strategy-map"));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <ReportShell
      title={t("strategyMap.title")}
      icon="flag"
      iconColor="#c7527d"
      hasTableToggle={false}
      chartRef={chartRef}
    >
      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Typography color="error" sx={{ py: 4 }}>
          {t("strategyMap.error")}: {error}
        </Typography>
      )}

      {data && !loading && (
        <Box>
          {/* Summary metrics */}
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 3 }}>
            <MetricCard
              label={t("strategyMap.objectives")}
              value={data.summary.objective_count}
              icon="flag"
            />
            <MetricCard
              label={t("strategyMap.initiatives")}
              value={data.summary.initiative_count}
              icon="rocket_launch"
            />
            <MetricCard
              label={t("strategyMap.applications")}
              value={data.summary.application_count}
              icon="apps"
            />
            <MetricCard
              label={t("strategyMap.totalBudget")}
              value={fmtShort(data.summary.total_budget)}
              icon="savings"
            />
          </Box>

          {data.objectives.length === 0 && (
            <Box sx={{ textAlign: "center", py: 8, color: "text.secondary" }}>
              <MaterialSymbol icon="flag" size={48} />
              <Typography sx={{ mt: 2 }}>{t("strategyMap.emptyState")}</Typography>
            </Box>
          )}

          {/* One panel per objective: KPI + capabilities + initiative→app chains */}
          {data.objectives.map((obj) => (
            <Paper key={obj.id} variant="outlined" sx={{ mb: 2, p: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                <MaterialSymbol icon="flag" size={20} color="#c7527d" />
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  <CardLink card={obj} />
                </Typography>
                {obj.kpi && (
                  <Chip
                    size="small"
                    icon={<MaterialSymbol icon="trending_up" size={16} />}
                    label={obj.kpi}
                    color="success"
                    variant="outlined"
                  />
                )}
              </Box>

              {/* Capabilities */}
              {obj.capabilities.length > 0 && (
                <Box sx={{ mt: 1.5, display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                    {t("strategyMap.capabilities")}:
                  </Typography>
                  {obj.capabilities.map((c) => (
                    <Chip
                      key={c.id}
                      size="small"
                      label={<CardLink card={c} />}
                      icon={<MaterialSymbol icon="account_tree" size={14} />}
                    />
                  ))}
                </Box>
              )}

              {/* Initiatives */}
              {obj.initiatives.length === 0 ? (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1.5, display: "block" }}>
                  {t("strategyMap.noInitiatives")}
                </Typography>
              ) : (
                <Box sx={{ mt: 1.5, display: "flex", flexDirection: "column", gap: 1 }}>
                  {obj.initiatives.map((init) => (
                    <Box
                      key={init.id}
                      sx={{
                        p: 1.5,
                        borderRadius: 1,
                        bgcolor: "action.hover",
                        display: "flex",
                        flexWrap: "wrap",
                        alignItems: "center",
                        gap: 1,
                      }}
                    >
                      <MaterialSymbol icon="rocket_launch" size={18} color="#33cc58" />
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        <CardLink card={init} />
                      </Typography>
                      {init.status && <Chip size="small" label={init.status} />}
                      {init.budget != null && (
                        <Chip
                          size="small"
                          variant="outlined"
                          label={`${t("strategyMap.budget")}: ${fmtShort(init.budget)}`}
                        />
                      )}
                      {init.applications.length > 0 && (
                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexWrap: "wrap" }}>
                          <MaterialSymbol icon="arrow_forward" size={14} />
                          {init.applications.map((app) => (
                            <Chip
                              key={app.id}
                              size="small"
                              variant="outlined"
                              label={<CardLink card={app} />}
                              icon={<MaterialSymbol icon="apps" size={14} />}
                            />
                          ))}
                        </Box>
                      )}
                    </Box>
                  ))}
                </Box>
              )}
            </Paper>
          ))}
        </Box>
      )}
    </ReportShell>
  );
}
