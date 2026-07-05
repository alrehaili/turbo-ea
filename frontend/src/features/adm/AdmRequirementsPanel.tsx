/**
 * Cross-phase Requirements Management panel. Fetches every
 * ``kind='requirement'`` artefact across every phase of the workspace, so
 * the "continuous" nature of Requirements Management is visible without
 * hunting through each phase.
 *
 * [FORK FEATURE]
 */

import { useCallback, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import { useTranslation } from "react-i18next";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import type { AdmArtefact } from "./types";

type WorkspaceRequirement = AdmArtefact & { phase_key: string; phase_title: string };

interface Props {
  workspaceId: string;
  onNavigateToPhase: (phaseKey: string) => void;
}

export default function AdmRequirementsPanel({ workspaceId, onNavigateToPhase }: Props) {
  const { t } = useTranslation("adm");
  const [rows, setRows] = useState<WorkspaceRequirement[] | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.get<WorkspaceRequirement[]>(
        `/adm/workspaces/${workspaceId}/requirements`,
      );
      setRows(data);
    } catch {
      setRows([]);
    }
  }, [workspaceId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (rows === null) return null;

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 1 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
        <MaterialSymbol icon="assignment" size={20} color="#0f7eb5" />
        <Typography variant="subtitle1" sx={{ fontWeight: 800, flex: 1 }}>
          {t("requirements.title")}
        </Typography>
        <Chip size="small" label={rows.length} />
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1.5 }}>
        {t("requirements.subtitle")}
      </Typography>
      {rows.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          {t("requirements.empty")}
        </Typography>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
          {rows.map((r) => (
            <Box
              key={r.id}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                p: 1,
                borderRadius: 1,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Box
                sx={{
                  color: r.is_waived
                    ? "text.disabled"
                    : r.is_linked
                      ? "success.main"
                      : "warning.main",
                  display: "flex",
                }}
              >
                <MaterialSymbol
                  icon={r.is_waived ? "block" : r.is_linked ? "check_circle" : "radio_button_unchecked"}
                  size={16}
                  color="inherit"
                />
              </Box>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="body2" sx={{ fontWeight: 700 }} noWrap>
                  {r.title}
                </Typography>
                {r.notes && (
                  <Typography variant="caption" color="text.secondary" noWrap sx={{ display: "block" }}>
                    {r.notes}
                  </Typography>
                )}
              </Box>
              <Chip
                size="small"
                variant="outlined"
                label={r.phase_title}
                onClick={() => onNavigateToPhase(r.phase_key)}
              />
            </Box>
          ))}
        </Box>
      )}
    </Paper>
  );
}
