/**
 * Reference Model — coverage & gap analysis (RMPlan Phase 4 / §8).
 *
 * Turns the model into decision support: KPI tiles (coverage %, uncovered /
 * duplicate-support / retiring-only capabilities, unmapped inventory), a gap
 * list grouped by kind, and a per-capability coverage matrix. Gap rows and
 * matrix rows open the same item side panel the other views use.
 *
 * [FORK FEATURE] — Reference Models coverage (RMPlan/rmPlan.md).
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import type { ReferenceModelGap, ReferenceModelGapsResponse } from "@/types";

const GAP_META: Record<
  ReferenceModelGap["kind"],
  { color: "default" | "warning" | "error"; icon: string }
> = {
  no_mapping: { color: "error", icon: "link_off" },
  duplicate: { color: "warning", icon: "content_copy" },
  retiring_only: { color: "warning", icon: "schedule" },
};

interface Props {
  modelId: string;
  query: string;
  itemName: (i: { name: string; name_ar: string | null }) => string;
  onSelect: (id: string) => void;
}

export default function ReferenceModelCoverage({ modelId, query, itemName, onSelect }: Props) {
  const { t } = useTranslation(["reports"]);
  const [data, setData] = useState<ReferenceModelGapsResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(false);
    api
      .get<ReferenceModelGapsResponse>(`/reference-models/${modelId}/gaps`)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [modelId]);

  if (error) return <Alert severity="error">{t("common:errors.generic")}</Alert>;
  if (!data)
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );

  const { totals } = data;
  const q = query.trim().toLowerCase();
  const match = (r: { code: string; name: string; name_ar: string | null }) =>
    !q ||
    r.code.toLowerCase().includes(q) ||
    r.name.toLowerCase().includes(q) ||
    (r.name_ar ?? "").toLowerCase().includes(q);
  const gaps = data.gaps.filter(match);
  const matrix = data.matrix.filter(match);

  const tiles: { key: string; value: number | string; tone?: "error" | "warning" }[] = [
    { key: "coverage", value: `${totals.coverage_pct}%` },
    { key: "covered", value: totals.covered_leaves },
    { key: "uncovered", value: totals.uncovered_leaves, tone: totals.uncovered_leaves ? "error" : undefined },
    { key: "duplicate", value: totals.duplicate_leaves, tone: totals.duplicate_leaves ? "warning" : undefined },
    { key: "retiring", value: totals.retiring_leaves, tone: totals.retiring_leaves ? "warning" : undefined },
    { key: "unmapped", value: totals.unmapped_cards, tone: totals.unmapped_cards ? "warning" : undefined },
  ];

  return (
    <Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(6, 1fr)" },
          gap: 1.5,
          mb: 2,
        }}
      >
        {tiles.map((tile) => (
          <Paper key={tile.key} variant="outlined" sx={{ p: 1.5, textAlign: "center" }}>
            <Typography
              variant="h5"
              fontWeight={700}
              color={tile.tone === "error" ? "error.main" : tile.tone === "warning" ? "warning.main" : "text.primary"}
            >
              {tile.value}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t(`rmGap.tile.${tile.key}`)}
            </Typography>
          </Paper>
        ))}
      </Box>

      {/* Gap list */}
      <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
        {t("rmGap.gapsTitle", { count: gaps.length })}
      </Typography>
      {gaps.length === 0 ? (
        <Alert severity="success" sx={{ mb: 2 }} icon={<MaterialSymbol icon="check_circle" size={20} />}>
          {t("rmGap.noGaps")}
        </Alert>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.75, mb: 2 }}>
          {gaps.map((gap) => {
            const meta = GAP_META[gap.kind];
            return (
              <Paper
                key={`${gap.item_id}-${gap.kind}`}
                variant="outlined"
                onClick={() => onSelect(gap.item_id)}
                sx={{
                  p: 1,
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  cursor: "pointer",
                  "&:hover": { bgcolor: "action.hover" },
                }}
              >
                <MaterialSymbol icon={meta.icon} size={18} />
                <Chip size="small" variant="outlined" label={gap.code} sx={{ direction: "ltr", fontFamily: "monospace" }} />
                <Typography variant="body2" sx={{ flex: 1, minWidth: 0 }} noWrap>
                  {itemName(gap)}
                </Typography>
                {gap.cards.length > 0 && (
                  <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 260 }}>
                    {gap.cards.join("، ")}
                  </Typography>
                )}
                <Chip size="small" color={meta.color} label={t(`rmGap.kind.${gap.kind}`)} />
              </Paper>
            );
          })}
        </Box>
      )}

      {/* Coverage matrix */}
      <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
        {t("rmGap.matrixTitle")}
      </Typography>
      <Paper variant="outlined" sx={{ overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("rmLibrary.colCode")}</TableCell>
              <TableCell>{t("rmLibrary.colName")}</TableCell>
              <TableCell align="center">{t("rmGap.colMapped")}</TableCell>
              <TableCell>{t("rmBrowse.coverage")}</TableCell>
              <TableCell>{t("rmGap.colLifecycleRisk")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {matrix.map((row) => (
              <TableRow
                key={row.item_id}
                hover
                sx={{ cursor: "pointer" }}
                onClick={() => onSelect(row.item_id)}
              >
                <TableCell sx={{ direction: "ltr", fontFamily: "monospace" }}>{row.code}</TableCell>
                <TableCell>{itemName(row)}</TableCell>
                <TableCell align="center">{row.mapped}</TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    color={row.coverage === "covered" ? "success" : "default"}
                    variant={row.coverage === "covered" ? "filled" : "outlined"}
                    label={t(`rmGap.coverage.${row.coverage}`)}
                  />
                </TableCell>
                <TableCell>
                  {row.lifecycle_risk ? (
                    <Chip size="small" color="warning" label={t("rmGap.kind.retiring_only")} />
                  ) : row.duplicate ? (
                    <Chip size="small" color="warning" variant="outlined" label={t("rmGap.kind.duplicate")} />
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      —
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}
