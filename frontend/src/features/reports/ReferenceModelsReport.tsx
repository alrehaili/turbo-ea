/**
 * ReferenceModelsReport — coverage + distribution across NORA's four
 * reference models (BRM, ARM, DRM, TRM). Each model card shows how many of
 * the relevant card type are classified, a distribution bar chart, and a
 * click-through to the inventory filtered by option or "not set".
 *
 * [FORK FEATURE] — noraPlan.md WP1.1 companion.
 */
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import i18n from "@/i18n";
import { optionLabel } from "@/hooks/useResolveLabel";

interface OptionDef {
  key: string;
  label: string;
  translations?: Record<string, string>;
}

interface ReferenceModel {
  key: "brm" | "arm" | "drm" | "trm";
  card_type: string;
  card_type_label?: string;
  card_type_icon?: string;
  card_type_color?: string;
  card_type_translations?: Record<string, string>;
  field_key: string;
  field_label?: string;
  field_translations?: Record<string, string>;
  available: boolean;
  total: number;
  classified: number;
  uncategorised: number;
  options: OptionDef[];
  distribution: Record<string, number>;
  reference_model?: {
    id: string;
    name: string;
    name_ar: string | null;
    version: string;
    item_count: number;
    mapped: number;
    unmatched: number;
    uncoded: number;
  };
}

interface ReferenceModelsPayload {
  models: ReferenceModel[];
}

// Distinct hue per option so the bar chart is a mini legend on its own.
const BAR_PALETTE = [
  "#1976d2",
  "#0288d1",
  "#00897b",
  "#7cb342",
  "#f57c00",
  "#e65100",
  "#7b1fa2",
  "#c2185b",
  "#455a64",
  "#5d4037",
];

const MODEL_ICONS: Record<string, { icon: string; color: string }> = {
  brm: { icon: "account_tree", color: "#003399" },
  arm: { icon: "apps", color: "#0f7eb5" },
  drm: { icon: "database", color: "#774fcc" },
  trm: { icon: "memory", color: "#d29270" },
};

export default function ReferenceModelsReport() {
  const { t } = useTranslation(["reports", "common", "nav"]);
  const navigate = useNavigate();
  const [payload, setPayload] = useState<ReferenceModelsPayload | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<ReferenceModelsPayload>("/reports/reference-models")
      .then(setPayload)
      .catch((e) => setError(e instanceof Error ? e.message : "error"));
  }, []);

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!payload) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
        <MaterialSymbol icon="hub" size={26} color="#1976d2" />
        <Typography variant="h5" fontWeight={700}>
          {t("referenceModels.title")}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("referenceModels.subtitle")}
      </Typography>

      <Grid container spacing={2}>
        {payload.models.map((m) => (
          <Grid item xs={12} md={6} key={m.key}>
            <ModelCard model={m} onNavigate={navigate} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

interface ModelCardProps {
  model: ReferenceModel;
  onNavigate: (path: string) => void;
}

function ModelCard({ model, onNavigate }: ModelCardProps) {
  const { t } = useTranslation(["reports", "common"]);
  const locale = i18n.language;

  const coverage = model.total > 0 ? Math.round((model.classified / model.total) * 100) : 0;

  const chartData = useMemo(
    () =>
      model.options.map((opt, i) => ({
        key: opt.key,
        name: optionLabel(opt, locale),
        count: model.distribution[opt.key] ?? 0,
        color: BAR_PALETTE[i % BAR_PALETTE.length],
      })),
    [model.options, model.distribution, locale],
  );

  const iconMeta = MODEL_ICONS[model.key];
  const modelName = t(`referenceModels.model.${model.key}.name`);
  const modelDescription = t(`referenceModels.model.${model.key}.description`);

  const goToOption = (optionKey: string) => {
    onNavigate(
      `/inventory?type=${encodeURIComponent(model.card_type)}&search=${encodeURIComponent(
        `${model.field_key}:${optionKey}`,
      )}`,
    );
  };

  const goToType = () => {
    onNavigate(`/inventory?type=${encodeURIComponent(model.card_type)}`);
  };

  if (!model.available) {
    return (
      <Paper sx={{ p: 3, height: "100%", opacity: 0.7 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          <MaterialSymbol icon={iconMeta.icon} size={22} color={iconMeta.color} />
          <Typography variant="h6" fontWeight={700}>
            {modelName}
          </Typography>
        </Box>
        <Alert severity="warning" sx={{ mt: 2 }}>
          {t("referenceModels.notAvailable", {
            field: model.field_key,
            type: model.card_type,
          })}
        </Alert>
      </Paper>
    );
  }

  const noData = model.total === 0;

  return (
    <Paper sx={{ p: 3, height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 0.5 }}>
        <MaterialSymbol icon={iconMeta.icon} size={26} color={iconMeta.color} />
        <Box sx={{ flex: 1 }}>
          <Typography variant="h6" fontWeight={700} lineHeight={1.2}>
            {modelName}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("referenceModels.appliesTo")}: {model.card_type_label || model.card_type} ·{" "}
            {t("referenceModels.classifiedBy")}: {model.field_label || model.field_key}
          </Typography>
        </Box>
        <Tooltip title={t("referenceModels.openInventory")}>
          <Chip
            size="small"
            label={model.total}
            onClick={goToType}
            clickable
            sx={{ cursor: "pointer" }}
          />
        </Tooltip>
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {modelDescription}
      </Typography>

      {/* Coverage */}
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
          <Typography variant="caption" color="text.secondary" fontWeight={600}>
            {t("referenceModels.coverage")}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {model.classified}/{model.total} · {coverage}%
          </Typography>
          <Box sx={{ flex: 1 }} />
          {model.uncategorised > 0 && (
            <Tooltip title={t("referenceModels.showUncategorised")}>
              <Chip
                size="small"
                color="warning"
                variant="outlined"
                icon={<MaterialSymbol icon="warning" size={14} />}
                label={`${model.uncategorised} ${t("referenceModels.uncategorised")}`}
                onClick={() =>
                  onNavigate(
                    `/inventory?type=${encodeURIComponent(model.card_type)}`,
                  )
                }
                clickable
                sx={{ cursor: "pointer" }}
              />
            </Tooltip>
          )}
        </Box>
        <LinearProgress
          variant="determinate"
          value={coverage}
          color={coverage >= 80 ? "success" : coverage >= 50 ? "warning" : "error"}
          sx={{ height: 6, borderRadius: 3 }}
        />
      </Box>

      {/* Published Reference Model code coverage (WP100.3) */}
      {model.reference_model && (
        <Box
          sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2, flexWrap: "wrap" }}
        >
          <MaterialSymbol icon="schema" size={16} color="#00695c" />
          <Typography variant="caption" color="text.secondary" fontWeight={600}>
            {t("referenceModels.rmCoverage")}
          </Typography>
          <Tooltip title={t("referenceModels.openRmLibrary")}>
            <Chip
              size="small"
              variant="outlined"
              label={`${
                locale.startsWith("ar") && model.reference_model.name_ar
                  ? model.reference_model.name_ar
                  : model.reference_model.name
              } · ${model.reference_model.version}`}
              onClick={() => onNavigate("/reference-models")}
              clickable
              sx={{ cursor: "pointer" }}
            />
          </Tooltip>
          <Chip
            size="small"
            color="success"
            variant="outlined"
            label={`${model.reference_model.mapped} ${t("referenceModels.rmMapped")}`}
          />
          {model.reference_model.unmatched > 0 && (
            <Chip
              size="small"
              color="warning"
              variant="outlined"
              label={`${model.reference_model.unmatched} ${t("referenceModels.rmUnmatched")}`}
            />
          )}
        </Box>
      )}

      {/* Chart */}
      {noData ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          {t("referenceModels.noCards", {
            type: model.card_type_label || model.card_type,
          })}
        </Alert>
      ) : (
        <>
          <Box sx={{ width: "100%", height: 180, mb: 2 }}>
            <ResponsiveContainer>
              <BarChart
                data={chartData}
                margin={{ top: 8, right: 8, left: 0, bottom: 30 }}
              >
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11 }}
                  angle={-25}
                  textAnchor="end"
                  interval={0}
                  height={40}
                />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <RechartsTooltip
                  formatter={(v) => [Number(v ?? 0), t("referenceModels.count")]}
                />
                <Bar dataKey="count" cursor="pointer" onClick={(d) => goToOption(String(d.key))}>
                  {chartData.map((entry) => (
                    <Cell key={entry.key} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Box>

          {/* Distribution table */}
          <Box sx={{ mt: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700, fontSize: 12 }}>
                    {t("referenceModels.category")}
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700, fontSize: 12 }}>
                    {t("referenceModels.count")}
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700, fontSize: 12 }}>
                    %
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {chartData
                  .slice()
                  .sort((a, b) => b.count - a.count)
                  .map((row) => (
                    <TableRow
                      key={row.key}
                      hover
                      sx={{ cursor: "pointer" }}
                      onClick={() => goToOption(row.key)}
                    >
                      <TableCell>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          <Box
                            sx={{
                              width: 10,
                              height: 10,
                              borderRadius: "50%",
                              bgcolor: row.color,
                            }}
                          />
                          {row.name}
                        </Box>
                      </TableCell>
                      <TableCell align="right">{row.count}</TableCell>
                      <TableCell align="right" sx={{ color: "text.secondary" }}>
                        {model.total > 0
                          ? `${Math.round((row.count / model.total) * 100)}%`
                          : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </Box>
        </>
      )}
    </Paper>
  );
}
