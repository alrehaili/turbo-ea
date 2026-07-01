import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Autocomplete from "@mui/material/Autocomplete";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import MenuItem from "@mui/material/MenuItem";
import ReportShell from "./ReportShell";
import MaterialSymbol from "@/components/MaterialSymbol";
import MetricCard from "./MetricCard";
import { useMetamodel } from "@/hooks/useMetamodel";
import { api } from "@/api/client";

/* ------------------------------------------------------------------ */
/*  Response types (mirrors app.services.impact_service.gather_impact) */
/* ------------------------------------------------------------------ */

interface AffectedCard {
  id: string;
  name: string;
  type: string;
  layer: string;
  depth: number;
  path: string[];
  relation_label: string | null;
  criticality: string | null;
  is_critical: boolean;
}

interface LayerGroup {
  layer: string;
  count: number;
  cards: AffectedCard[];
}

interface ImpactRisk {
  id: string;
  reference: string;
  title: string;
  status: string;
  level: string;
  via_cards: string[];
}

interface ImpactInitiative {
  id: string;
  name: string;
  subtype: string | null;
  depth: number;
}

interface ImpactResult {
  center: {
    id: string;
    name: string;
    type: string;
    subtype: string | null;
    layer: string;
    criticality: string | null;
  };
  change_type: string;
  depth: number;
  summary: {
    total_affected: number;
    by_layer: Record<string, number>;
    by_criticality: Record<string, number>;
    critical_count: number;
    risk_count: number;
    initiative_count: number;
  };
  affected: AffectedCard[];
  by_layer: LayerGroup[];
  risks: ImpactRisk[];
  initiatives: ImpactInitiative[];
}

interface CardOption {
  id: string;
  name: string;
  type: string;
}

type ChangeType = "modify" | "replace" | "retire";

const LEVEL_COLOR: Record<string, "default" | "warning" | "error" | "success"> = {
  low: "success",
  medium: "warning",
  high: "error",
  critical: "error",
};

export default function ChangeImpactWorkbench() {
  const { t } = useTranslation(["reports", "common"]);
  const { types } = useMetamodel();
  const typeLabel = useCallback(
    (key: string) => types.find((tp) => tp.key === key)?.label || key,
    [types],
  );
  const [params, setParams] = useSearchParams();
  const chartRef = useRef<HTMLDivElement>(null);

  const [options, setOptions] = useState<CardOption[]>([]);
  const [selected, setSelected] = useState<CardOption | null>(null);
  const [searching, setSearching] = useState(false);
  const [changeType, setChangeType] = useState<ChangeType>(
    (params.get("change_type") as ChangeType) || "retire",
  );
  const [depth, setDepth] = useState<number>(Number(params.get("depth")) || 2);
  const [result, setResult] = useState<ImpactResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Debounced card search for the picker.
  const [query, setQuery] = useState("");
  useEffect(() => {
    let active = true;
    if (query.trim().length < 2) {
      setOptions([]);
      return;
    }
    setSearching(true);
    const handle = setTimeout(async () => {
      try {
        const res = await api.get<{ items: CardOption[] }>(
          `/cards?search=${encodeURIComponent(query)}&page_size=20`,
        );
        if (active) setOptions(res.items ?? []);
      } catch {
        if (active) setOptions([]);
      } finally {
        if (active) setSearching(false);
      }
    }, 300);
    return () => {
      active = false;
      clearTimeout(handle);
    };
  }, [query]);

  const runImpact = useCallback(
    async (cardId: string, ct: ChangeType, d: number) => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.get<ImpactResult>(
          `/reports/impact?card_id=${cardId}&change_type=${ct}&depth=${d}`,
        );
        setResult(res);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        setResult(null);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  // Re-run whenever the selected card / change type / depth changes.
  useEffect(() => {
    if (!selected) return;
    setParams(
      { card_id: selected.id, change_type: changeType, depth: String(depth) },
      { replace: true },
    );
    runImpact(selected.id, changeType, depth);
  }, [selected, changeType, depth, runImpact, setParams]);

  // Restore selection from URL on first load.
  useEffect(() => {
    const cardId = params.get("card_id");
    if (cardId && !selected) {
      api
        .get<{ id: string; name: string; type: string }>(`/cards/${cardId}`)
        .then((c) => setSelected({ id: c.id, name: c.name, type: c.type }))
        .catch(() => undefined);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toolbar = (
    <>
      <Autocomplete
        sx={{ minWidth: 320 }}
        size="small"
        options={options}
        value={selected}
        loading={searching}
        getOptionLabel={(o) => o.name}
        isOptionEqualToValue={(a, b) => a.id === b.id}
        onChange={(_, v) => setSelected(v)}
        onInputChange={(_, v) => setQuery(v)}
        filterOptions={(x) => x}
        renderOption={(props, o) => (
          <li {...props} key={o.id}>
            <Box sx={{ display: "flex", flexDirection: "column" }}>
              <Typography variant="body2">{o.name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {typeLabel(o.type)}
              </Typography>
            </Box>
          </li>
        )}
        renderInput={(p) => (
          <TextField
            {...p}
            label={t("impact.selectCard")}
            placeholder={t("impact.searchPlaceholder")}
            InputProps={{
              ...p.InputProps,
              endAdornment: (
                <>
                  {searching ? <CircularProgress size={16} /> : null}
                  {p.InputProps.endAdornment}
                </>
              ),
            }}
          />
        )}
      />
      <ToggleButtonGroup
        size="small"
        exclusive
        value={changeType}
        onChange={(_, v) => v && setChangeType(v)}
      >
        <ToggleButton value="retire">{t("impact.retire")}</ToggleButton>
        <ToggleButton value="replace">{t("impact.replace")}</ToggleButton>
        <ToggleButton value="modify">{t("impact.modify")}</ToggleButton>
      </ToggleButtonGroup>
      <TextField
        select
        size="small"
        label={t("impact.depth")}
        value={depth}
        onChange={(e) => setDepth(Number(e.target.value))}
        sx={{ width: 110 }}
      >
        {[1, 2, 3].map((d) => (
          <MenuItem key={d} value={d}>
            {d}
          </MenuItem>
        ))}
      </TextField>
    </>
  );

  const headline = useMemo(() => {
    if (!result) return "";
    return t("impact.headline", {
      num: result.summary.total_affected,
      change: t(`impact.${result.change_type}` as const),
      name: result.center.name,
    });
  }, [result, t]);

  return (
    <ReportShell
      title={t("impact.title")}
      icon="electric_bolt"
      iconColor="#c7527d"
      toolbar={toolbar}
      hasTableToggle={false}
      chartRef={chartRef}
    >
      {!selected && !loading && (
        <Box sx={{ textAlign: "center", py: 8, color: "text.secondary" }}>
          <MaterialSymbol icon="electric_bolt" size={48} />
          <Typography sx={{ mt: 2 }}>{t("impact.emptyState")}</Typography>
        </Box>
      )}

      {loading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Typography color="error" sx={{ py: 4 }}>
          {t("impact.error")}: {error}
        </Typography>
      )}

      {result && !loading && (
        <Box>
          <Typography variant="h6" sx={{ mb: 2 }}>
            {headline}
          </Typography>

          {/* Summary metrics */}
          <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", mb: 3 }}>
            <MetricCard
              label={t("impact.totalAffected")}
              value={result.summary.total_affected}
              icon="account_tree"
            />
            <MetricCard
              label={t("impact.criticalAffected")}
              value={result.summary.critical_count}
              icon="priority_high"
              color={result.summary.critical_count > 0 ? "#d32f2f" : undefined}
            />
            <MetricCard
              label={t("impact.linkedRisks")}
              value={result.summary.risk_count}
              icon="warning"
            />
            <MetricCard
              label={t("impact.linkedInitiatives")}
              value={result.summary.initiative_count}
              icon="rocket_launch"
            />
          </Box>

          {/* Affected cards grouped by layer */}
          {result.by_layer.map((group) => (
            <Paper key={group.layer} variant="outlined" sx={{ mb: 2, p: 0 }}>
              <Box
                sx={{
                  px: 2,
                  py: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  bgcolor: "action.hover",
                }}
              >
                <Typography variant="subtitle2" sx={{ fontWeight: 700, flex: 1 }}>
                  {group.layer}
                </Typography>
                <Chip size="small" label={group.count} />
              </Box>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("impact.colCard")}</TableCell>
                    <TableCell>{t("impact.colType")}</TableCell>
                    <TableCell align="center">{t("impact.colDepth")}</TableCell>
                    <TableCell>{t("impact.colPath")}</TableCell>
                    <TableCell>{t("impact.colCriticality")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {group.cards.map((c) => (
                    <TableRow key={c.id} hover>
                      <TableCell>
                        <Box
                          component="a"
                          href={`/cards/${c.id}`}
                          sx={{ color: "primary.main", textDecoration: "none" }}
                        >
                          {c.name}
                        </Box>
                      </TableCell>
                      <TableCell>{typeLabel(c.type)}</TableCell>
                      <TableCell align="center">{c.depth}</TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {c.path.join(" → ")}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {c.criticality && (
                          <Chip
                            size="small"
                            label={c.criticality}
                            color={c.is_critical ? "error" : "default"}
                            variant={c.is_critical ? "filled" : "outlined"}
                          />
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          ))}

          {/* Linked risks */}
          {result.risks.length > 0 && (
            <Paper variant="outlined" sx={{ mb: 2 }}>
              <Box sx={{ px: 2, py: 1, bgcolor: "action.hover" }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  {t("impact.risksHeader")}
                </Typography>
              </Box>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("impact.colRiskRef")}</TableCell>
                    <TableCell>{t("impact.colRiskTitle")}</TableCell>
                    <TableCell>{t("impact.colRiskLevel")}</TableCell>
                    <TableCell>{t("impact.colVia")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {result.risks.map((r) => (
                    <TableRow key={r.id} hover>
                      <TableCell>
                        <Box
                          component="a"
                          href={`/grc/risks/${r.id}`}
                          sx={{ color: "primary.main", textDecoration: "none" }}
                        >
                          {r.reference}
                        </Box>
                      </TableCell>
                      <TableCell>{r.title}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={r.level}
                          color={LEVEL_COLOR[r.level] || "default"}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {r.via_cards.join(", ")}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          )}
        </Box>
      )}
    </ReportShell>
  );
}
