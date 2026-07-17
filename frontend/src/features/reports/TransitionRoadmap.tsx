/**
 * Transition Roadmap by Wave
 * Shows planned transitions organized by delivery wave/phase.
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
import ReportShell from "./ReportShell";

interface TransitionItem {
  id: string;
  element: string;
  type: string;
  wave: string;
  transitionType: "create" | "modify" | "retire" | "migrate";
  status: string;
  plannedDate?: string;
}

export default function TransitionRoadmap() {
  const { t } = useTranslation(["reports"]);
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<TransitionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          setError(null);
          // Every card participating in an architecture-state change (WP2.1):
          // target/transition cards plus current cards flagged for retirement.
          const [targetResp, transitionResp, retireResp] = await Promise.all([
            api.get<{ items: any[] }>("/cards?architecture_state=target&page_size=500"),
            api.get<{ items: any[] }>("/cards?architecture_state=transition&page_size=500"),
            api.get<{ items: any[] }>("/cards?architecture_state=current&change_type=retire&page_size=500"),
          ]);
          const unwrap = (r: any) => (Array.isArray(r) ? r : r.items || []);
          const cards = [...unwrap(targetResp), ...unwrap(transitionResp), ...unwrap(retireResp)];

          // Wave = the year-quarter of the card's planned lifecycle date;
          // cards without lifecycle planning land in "Unscheduled".
          const waveFor = (c: any): { wave: string; date?: string } => {
            const lc = c.lifecycle || {};
            const date: string | undefined = lc.plan || lc.phaseIn || lc.active;
            if (!date) return { wave: "Unscheduled" };
            const d = new Date(date);
            if (isNaN(d.getTime())) return { wave: "Unscheduled" };
            const q = Math.floor(d.getMonth() / 3) + 1;
            return { wave: `${d.getFullYear()} Q${q}`, date };
          };

          const items: TransitionItem[] = cards.map((c) => {
            const { wave, date } = waveFor(c);
            return {
              id: c.id,
              element: c.name,
              type: c.type,
              wave,
              transitionType: (c.change_type === "consolidate" ? "migrate" : c.change_type) || "create",
              status: c.architecture_state === "transition" ? "in transition" : "planned",
              plannedDate: date,
            };
          });
          setItems(items);
        } catch (err) {
          console.error("Failed to fetch transition roadmap:", err);
          setError("Failed to load roadmap data");
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
    return items.filter((i) => i.element.toLowerCase().includes(q) || i.wave.toLowerCase().includes(q));
  }, [items, search]);

  const waveGroups = useMemo(() => {
    const grouped = new Map<string, TransitionItem[]>();
    filtered.forEach((item) => {
      if (!grouped.has(item.wave)) {
        grouped.set(item.wave, []);
      }
      grouped.get(item.wave)!.push(item);
    });
    return Array.from(grouped.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [filtered]);

  const stats = useMemo(() => {
    const total = items.length;
    const create = items.filter((i) => i.transitionType === "create").length;
    const retire = items.filter((i) => i.transitionType === "retire").length;
    return { total, create, retire };
  }, [items]);

  const transitionColor = (type: TransitionItem["transitionType"]) => {
    switch (type) {
      case "create":
        return "#4caf50";
      case "retire":
        return "#f44336";
      case "migrate":
        return "#2196f3";
      default:
        return "#ff9800";
    }
  };

  return (
    <ReportShell title={t("transitionRoadmap.title", "Transition Roadmap by Wave")} icon="timeline">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("transitionRoadmap.subtitle", "Plan and track architecture transitions across delivery waves.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && items.length === 0 && !error && <Alert severity="info">{t("transitionRoadmap.empty", "No transitions planned.")}</Alert>}

      {!loading && items.length > 0 && (
        <>
          {/* KPI Cards */}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2, mb: 3 }}>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {stats.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("transitionRoadmap.metric.total", "Planned Transitions")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#4caf50" }}>
                {stats.create}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("transitionRoadmap.metric.create", "Create")}
              </Typography>
            </Paper>
            <Paper sx={{ p: 2, textAlign: "center" }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: "#f44336" }}>
                {stats.retire}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("transitionRoadmap.metric.retire", "Retire")}
              </Typography>
            </Paper>
          </Box>

          {/* Search */}
          <TextField
            size="small"
            placeholder={t("transitionRoadmap.search", "Search transitions…")}
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

          {/* Waves Timeline */}
          {waveGroups.map(([wave, waveItems]) => (
            <Paper key={wave} sx={{ mb: 2 }}>
              <Box sx={{ p: 2, bgcolor: "#fafafa", borderBottom: "1px solid", borderColor: "divider" }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, justifyContent: "space-between" }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    {wave}
                  </Typography>
                  <Chip size="small" label={`${waveItems.length} items`} variant="outlined" />
                </Box>
              </Box>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 700 }}>{t("transitionRoadmap.col.element", "Element")}</TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 100 }}>{t("transitionRoadmap.col.type", "Type")}</TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 120 }}>{t("transitionRoadmap.col.transition", "Transition")}</TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 110 }}>{t("transitionRoadmap.col.status", "Status")}</TableCell>
                    <TableCell sx={{ fontWeight: 700, width: 130 }}>{t("transitionRoadmap.col.date", "Planned Date")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {waveItems.map((item) => (
                    <TableRow key={item.id} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {item.element}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">{item.type}</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip size="small" label={item.transitionType} sx={{ backgroundColor: transitionColor(item.transitionType), color: "white" }} />
                      </TableCell>
                      <TableCell>
                        <Chip size="small" label={item.status} variant="outlined" />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">{item.plannedDate || "—"}</Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          ))}

          {filtered.length === 0 && search && <Alert severity="info" sx={{ mt: 2 }}>{t("transitionRoadmap.noResults", "No transitions found.")}</Alert>}
        </>
      )}
    </ReportShell>
  );
}
