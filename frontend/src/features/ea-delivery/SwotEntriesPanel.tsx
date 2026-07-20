/**
 * SwotEntriesPanel — structured, promotable SWOT rows for an Environment-
 * Analysis document (WP3.3). Sits alongside the rich-text quadrants: each
 * bullet becomes a row, and a weakness/threat can be promoted into the
 * Improvement-Opportunity registry (mirrors the compliance-finding → risk
 * bridge). Idempotent promotion — a promoted row shows "Opportunity created".
 * [FORK FEATURE] — noraPlan.md WP3.3.
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";

const QUADRANTS = ["strength", "weakness", "opportunity", "threat"] as const;
type Quadrant = (typeof QUADRANTS)[number];

const QUADRANT_META: Record<Quadrant, { color: string; icon: string }> = {
  strength: { color: "#2e7d32", icon: "trending_up" },
  weakness: { color: "#ed6c02", icon: "trending_down" },
  opportunity: { color: "#0288d1", icon: "lightbulb" },
  threat: { color: "#d32f2f", icon: "warning" },
};

interface SwotEntry {
  id: string;
  quadrant: Quadrant;
  text: string;
  opportunity_id: string | null;
  promotable: boolean;
}

interface Props {
  soawId: string;
  canManage: boolean;
  canPromote: boolean;
  readOnly?: boolean;
}

export default function SwotEntriesPanel({ soawId, canManage, canPromote, readOnly }: Props) {
  const { t } = useTranslation(["delivery", "common"]);
  const [entries, setEntries] = useState<SwotEntry[]>([]);
  const [newQuadrant, setNewQuadrant] = useState<Quadrant>("weakness");
  const [newText, setNewText] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setEntries(await api.get<SwotEntry[]>(`/soaw/${soawId}/swot`));
    } catch {
      setEntries([]);
    }
  }, [soawId]);

  useEffect(() => {
    load();
  }, [load]);

  const add = async () => {
    if (!newText.trim()) return;
    setBusy(true);
    try {
      await api.post(`/soaw/${soawId}/swot`, { quadrant: newQuadrant, text: newText.trim() });
      setNewText("");
      await load();
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    await api.delete(`/soaw/swot/${id}`);
    await load();
  };

  const promote = async (id: string) => {
    setBusy(true);
    try {
      await api.post(`/soaw/swot/${id}/promote`, {});
      await load();
    } finally {
      setBusy(false);
    }
  };

  const byQuadrant = (q: Quadrant) => entries.filter((e) => e.quadrant === q);

  return (
    <Paper variant="outlined" sx={{ p: 2.5, my: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
        <MaterialSymbol icon="grid_view" size={20} />
        <Typography variant="subtitle1" fontWeight={700}>
          {t("swot.title", "SWOT entries")}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t(
          "swot.subtitle",
          "Structured rows alongside the quadrants above. Promote a weakness or threat into the Improvement-Opportunity registry.",
        )}
      </Typography>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 2 }}>
        {QUADRANTS.map((q) => {
          const meta = QUADRANT_META[q];
          const rows = byQuadrant(q);
          return (
            <Box key={q} sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.5 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 1 }}>
                <MaterialSymbol icon={meta.icon} size={16} color={meta.color} />
                <Typography variant="subtitle2" sx={{ fontWeight: 700, color: meta.color }}>
                  {t(`swot.quadrant.${q}`, q)}
                </Typography>
                <Chip size="small" label={rows.length} sx={{ height: 18, ml: "auto" }} />
              </Box>
              {rows.length === 0 ? (
                <Typography variant="caption" color="text.secondary">
                  {t("swot.emptyQuadrant", "No entries.")}
                </Typography>
              ) : (
                rows.map((e) => (
                  <Box
                    key={e.id}
                    sx={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 0.5,
                      py: 0.5,
                      borderBottom: "1px dashed",
                      borderColor: "divider",
                    }}
                  >
                    <Typography variant="body2" sx={{ flex: 1 }}>
                      {e.text}
                    </Typography>
                    {e.opportunity_id ? (
                      <Tooltip title={t("swot.openOpportunity", "Open opportunity")}>
                        <Chip
                          size="small"
                          color="success"
                          variant="outlined"
                          component={RouterLink}
                          to="/grc?tab=governance"
                          clickable
                          icon={<MaterialSymbol icon="check_circle" size={14} />}
                          label={t("swot.promoted", "Promoted")}
                          sx={{ height: 22 }}
                        />
                      </Tooltip>
                    ) : (
                      e.promotable &&
                      canPromote &&
                      !readOnly && (
                        <Tooltip title={t("swot.promote", "Promote to opportunity")}>
                          <span>
                            <IconButton size="small" disabled={busy} onClick={() => promote(e.id)}>
                              <MaterialSymbol icon="north_east" size={16} />
                            </IconButton>
                          </span>
                        </Tooltip>
                      )
                    )}
                    {canManage && !readOnly && (
                      <IconButton size="small" onClick={() => remove(e.id)}>
                        <MaterialSymbol icon="delete" size={16} />
                      </IconButton>
                    )}
                  </Box>
                ))
              )}
            </Box>
          );
        })}
      </Box>

      {canManage && !readOnly && (
        <Box sx={{ display: "flex", gap: 1, mt: 2, alignItems: "flex-start", flexWrap: "wrap" }}>
          <TextField
            select
            size="small"
            label={t("swot.quadrantLabel", "Quadrant")}
            value={newQuadrant}
            onChange={(e) => setNewQuadrant(e.target.value as Quadrant)}
            sx={{ minWidth: 150 }}
          >
            {QUADRANTS.map((q) => (
              <MenuItem key={q} value={q}>
                {t(`swot.quadrant.${q}`, q)}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            size="small"
            label={t("swot.entryText", "Entry")}
            value={newText}
            onChange={(e) => setNewText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && add()}
            sx={{ flex: 1, minWidth: 200 }}
          />
          <Button
            variant="outlined"
            startIcon={<MaterialSymbol icon="add" size={18} />}
            onClick={add}
            disabled={busy || !newText.trim()}
          >
            {t("common:actions.add")}
          </Button>
        </Box>
      )}

      <Box sx={{ mt: 1.5 }}>
        <Link component={RouterLink} to="/grc?tab=governance" underline="hover" variant="caption">
          {t("swot.openRegistry", "Open the Improvement-Opportunity registry")}
        </Link>
      </Box>
    </Paper>
  );
}
