/**
 * Current vs Target Comparison
 * Side-by-side comparison of architecture elements in current and target states.
 * Part of Phase 5: Current, Target & Transition Views.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import InputAdornment from "@mui/material/InputAdornment";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import { SEVERITY_COLORS, STATUS_COLORS } from "@/theme/tokens";
import ReportShell from "./ReportShell";

interface ArchItem {
  id: string;
  name: string;
  type: string;
  currentState: string;
  targetState?: string;
  status: "current-only" | "retained" | "modified" | "new-target" | "retired";
}

export default function CurrentVsTargetComparison() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<ArchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          setError(null);
          const resp = await api.get<{ items: any[] }>("/cards?page_size=500");
          const cards = Array.isArray(resp) ? resp : resp.items || [];
          const items: ArchItem[] = cards.map((card) => {
            const archState: string = card.architecture_state || "current";
            const changeType: string | null = card.change_type || null;
            let status: ArchItem["status"] = "current-only";

            if (changeType === "retire") {
              status = "retired";
            } else if (archState === "current" && !changeType) {
              status = "retained";
            } else if (changeType === "modify" || changeType === "replace" || changeType === "consolidate" || card.successor_id) {
              status = "modified";
            } else if (archState === "target" || archState === "transition") {
              status = "new-target";
            }

            return {
              id: card.id,
              name: card.name,
              type: card.type,
              currentState: archState,
              targetState: changeType || (archState !== "current" ? archState : undefined),
              status,
            };
          });
          setItems(items);
        } catch (err) {
          console.error("Failed to fetch current vs target:", err);
          setError("Failed to load architecture elements");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return items.filter((item) => item.name.toLowerCase().includes(q) || item.type.toLowerCase().includes(q));
  }, [items, search]);

  const stats = useMemo(() => {
    const current = items.filter((i) => i.currentState === "current").length;
    const target = items.filter((i) => i.status !== "retired").length;
    const gaps = items.filter((i) => i.status === "modified").length;
    const new_items = items.filter((i) => i.status === "new-target").length;
    return { current, target, gaps, new_items };
  }, [items]);

  const statusColor = (status: ArchItem["status"]) => {
    switch (status) {
      case "retained":
        return STATUS_COLORS.success;
      case "modified":
        return SEVERITY_COLORS.medium;
      case "new-target":
        return "primary";
      case "retired":
        return SEVERITY_COLORS.high;
      default:
        return STATUS_COLORS.info;
    }
  };

  const statusLabel = (status: ArchItem["status"]) => {
    switch (status) {
      case "retained":
        return t("currentVsTarget.status.retained", "Retained");
      case "modified":
        return t("currentVsTarget.status.modified", "Modified");
      case "new-target":
        return t("currentVsTarget.status.new", "New");
      case "retired":
        return t("currentVsTarget.status.retired", "Retired");
      default:
        return t("currentVsTarget.status.current", "Current");
    }
  };

  return (
    <ReportShell title={t("currentVsTarget.title", "Current vs Target Comparison")} icon="compare_arrows">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t(
          "currentVsTarget.subtitle",
          "Compare architecture elements across current and target states to identify gaps and transitions."
        )}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && items.length === 0 && !error && <Alert severity="info">{t("currentVsTarget.empty", "No architecture elements found.")}</Alert>}

      {!loading && items.length > 0 && (
        <>
          {/* KPI Cards */}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(4, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.current}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("currentVsTarget.metric.current", "Current State")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
                {stats.target}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("currentVsTarget.metric.target", "Target State")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: SEVERITY_COLORS.medium }}>
                {stats.gaps}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("currentVsTarget.metric.gaps", "Gaps")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "success.main" }}>
                {stats.new_items}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("currentVsTarget.metric.new", "New")}
              </Typography>
            </Paper>
          </Box>

          {/* Search */}
          <TextField
            size="small"
            placeholder={t("currentVsTarget.search", "Search elements…")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <MaterialSymbol icon="search" size={18} color="disabled" />
                  </InputAdornment>
                ),
              },
            }}
            sx={{ mb: 2, maxWidth: 360 }}
          />

          {/* Comparison Table */}
          <Paper variant="outlined" sx={{ overflow: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ backgroundColor: "#fafafa" }}>
                  <TableCell sx={{ fontWeight: 700 }}>{t("currentVsTarget.col.element", "Element")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120 }}>{t("currentVsTarget.col.type", "Type")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120 }}>{t("currentVsTarget.col.current", "Current")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 120 }}>{t("currentVsTarget.col.target", "Target")}</TableCell>
                  <TableCell sx={{ fontWeight: 700, width: 130 }}>{t("currentVsTarget.col.status", "Status")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((item) => (
                  <TableRow key={item.id} hover>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {item.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{item.type}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={item.currentState} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      {item.targetState ? (
                        <Chip size="small" label={item.targetState} variant="filled" />
                      ) : (
                        <Typography variant="caption" color="text.secondary">
                          —
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={statusLabel(item.status)} sx={{ backgroundColor: statusColor(item.status), color: "white" }} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          {filtered.length === 0 && search && <Alert severity="info" sx={{ mt: 2 }}>{t("currentVsTarget.noResults", "No results found.")}</Alert>}
        </>
      )}
    </ReportShell>
  );
}
