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
import { api } from "@/api/client";

interface CardBrief {
  id: string;
  name: string;
  type: string;
}
interface DataObjectRow {
  id: string;
  name: string;
  domain: string;
  applications: CardBrief[];
  interfaces: CardBrief[];
  components: CardBrief[];
  is_orphan: boolean;
}
interface DataFlow {
  summary: { data_objects: number; domains: number; apps_touching_data: number; orphans: number };
  by_domain: { domain: string; count: number }[];
  data_objects: DataObjectRow[];
}

function Chips({ items, icon }: { items: CardBrief[]; icon: string }) {
  if (items.length === 0) return <Typography variant="caption" color="text.secondary">—</Typography>;
  return (
    <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
      {items.map((c) => (
        <Chip
          key={c.id}
          size="small"
          variant="outlined"
          icon={<MaterialSymbol icon={icon} size={14} />}
          label={
            <Box component="a" href={`/cards/${c.id}`} sx={{ color: "inherit", textDecoration: "none" }}>
              {c.name}
            </Box>
          }
        />
      ))}
    </Box>
  );
}

export default function DataFlowMap() {
  const { t } = useTranslation(["reports", "common"]);
  const chartRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<DataFlow | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.get<DataFlow>("/reports/data-flow"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Group data objects by domain for display.
  const grouped = (data?.data_objects ?? []).reduce<Record<string, DataObjectRow[]>>((acc, d) => {
    (acc[d.domain] ||= []).push(d);
    return acc;
  }, {});

  return (
    <ReportShell
      title={t("dataFlow.title")}
      icon="schema"
      iconColor="#774fcc"
      hasTableToggle={false}
      chartRef={chartRef}
    >
      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      ) : data ? (
        <Box>
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 3 }}>
            <MetricCard label={t("dataFlow.dataObjects")} value={data.summary.data_objects} icon="database" />
            <MetricCard label={t("dataFlow.domains")} value={data.summary.domains} icon="category" />
            <MetricCard label={t("dataFlow.appsTouching")} value={data.summary.apps_touching_data} icon="apps" />
            <MetricCard
              label={t("dataFlow.orphans")}
              value={data.summary.orphans}
              icon="link_off"
              color={data.summary.orphans > 0 ? "#ed6c02" : undefined}
            />
          </Box>

          {data.data_objects.length === 0 && (
            <Box sx={{ textAlign: "center", py: 8, color: "text.secondary" }}>
              <MaterialSymbol icon="schema" size={48} />
              <Typography sx={{ mt: 2 }}>{t("dataFlow.emptyState")}</Typography>
            </Box>
          )}

          {Object.entries(grouped).map(([domain, rows]) => (
            <Paper key={domain} variant="outlined" sx={{ mb: 2 }}>
              <Box sx={{ px: 2, py: 1, bgcolor: "action.hover", display: "flex", gap: 1, alignItems: "center" }}>
                <MaterialSymbol icon="category" size={18} color="#774fcc" />
                <Typography variant="subtitle2" sx={{ fontWeight: 700, flex: 1 }}>
                  {domain}
                </Typography>
                <Chip size="small" label={rows.length} />
              </Box>
              <Box sx={{ p: 2, display: "flex", flexDirection: "column", gap: 2 }}>
                {rows.map((d) => (
                  <Box key={d.id}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                      <MaterialSymbol icon="database" size={16} color="#774fcc" />
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        <Box component="a" href={`/cards/${d.id}`} sx={{ color: "primary.main", textDecoration: "none" }}>
                          {d.name}
                        </Box>
                      </Typography>
                      {d.is_orphan && <Chip size="small" color="warning" label={t("dataFlow.orphan")} />}
                    </Box>
                    <Box sx={{ pl: 3, display: "grid", gridTemplateColumns: "120px 1fr", gap: 1, alignItems: "center" }}>
                      <Typography variant="caption" color="text.secondary">{t("dataFlow.applications")}</Typography>
                      <Chips items={d.applications} icon="apps" />
                      <Typography variant="caption" color="text.secondary">{t("dataFlow.interfaces")}</Typography>
                      <Chips items={d.interfaces} icon="sync_alt" />
                      <Typography variant="caption" color="text.secondary">{t("dataFlow.components")}</Typography>
                      <Chips items={d.components} icon="memory" />
                    </Box>
                  </Box>
                ))}
              </Box>
            </Paper>
          ))}
        </Box>
      ) : null}
    </ReportShell>
  );
}
