/**
 * Touchpoint Matrix
 * Map personas × touchpoints/channels to understand interaction patterns.
 * Part of Phase 9: Beneficiary Experience Views.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { api } from "@/api/client";
import ReportShell from "./ReportShell";

interface PersonaData {
  name: string;
  touchpoints: string[];
}

export default function TouchpointMatrix() {
  const { t } = useTranslation(["reports"]);
  const [data, setData] = useState<PersonaData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useMemo(
    () => {
      const fetch = async () => {
        try {
          setLoading(true);
          const response = await api.get<{ items: any[] }>("/cards?type=Persona&page_size=100");
          const cards = Array.isArray(response) ? response : response.items || [];

          const personaData: PersonaData[] = cards.map((c) => ({
            name: c.name,
            touchpoints: c.attributes?.preferredChannels ? (typeof c.attributes.preferredChannels === "string" ? c.attributes.preferredChannels.split(",").map((s: string) => s.trim()) : []) : [],
          }));

          setData(personaData);
        } catch (err) {
          setError("Failed to load matrix data");
        } finally {
          setLoading(false);
        }
      };
      fetch();
    },
    []
  );

  const mockData = useMemo(() => {
    // Extract unique touchpoints from all personas
    const allTouchpoints = new Set<string>();
    data.forEach((p) => {
      if (p.touchpoints) {
        p.touchpoints.forEach((tp) => allTouchpoints.add(tp));
      }
    });
    const touchpointsList = Array.from(allTouchpoints);

    // Usage is binary today (a channel is either in the persona's preferred
    // channels or not) — satisfaction per channel is not yet modeled.
    const matrix = data.map((persona) => ({
      persona: persona.name,
      touchpoints: touchpointsList.map((tp) => ({
        name: tp,
        usage: persona.touchpoints?.includes(tp) ? 100 : 0,
        satisfaction: -1,
      })),
    }));

    return { personas: data.map((p) => p.name), touchpoints: touchpointsList, matrix };
  }, [data]);

  return (
    <ReportShell title={t("touchpointMatrix.title", "Touchpoint Matrix")} icon="grid_view">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {t("touchpointMatrix.subtitle", "Personas × channels and touchpoints showing usage and satisfaction.")}
      </Typography>

      {loading && (
        <Box sx={{ textAlign: "center", py: 4 }}>
          <Typography color="text.secondary">{t("common:loading", "Loading…")}</Typography>
        </Box>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {!loading && (
        <Paper variant="outlined" sx={{ overflow: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ backgroundColor: "#fafafa" }}>
                <TableCell sx={{ fontWeight: 700, minWidth: 150 }}>{t("touchpointMatrix.col.persona", "Persona")}</TableCell>
                {mockData.touchpoints.map((tp) => (
                  <TableCell key={tp} sx={{ fontWeight: 700, width: 120, textAlign: "center" }}>
                    <Typography variant="caption">{tp}</Typography>
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {mockData.matrix.map((row, idx) => (
                <TableRow key={idx} hover>
                  <TableCell sx={{ fontWeight: 600 }}>{row.persona}</TableCell>
                  {row.touchpoints.map((tp, tpIdx) => (
                    <TableCell key={tpIdx} sx={{ textAlign: "center" }}>
                      <Box
                        sx={{
                          width: 40,
                          height: 40,
                          mx: "auto",
                          borderRadius: 1,
                          backgroundColor: tp.usage > 0 ? "#4caf50" : "action.hover",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: tp.usage > 0 ? "white" : "text.disabled",
                          fontSize: "0.9rem",
                          fontWeight: 600,
                        }}
                      >
                        {tp.usage > 0 ? "✓" : "—"}
                      </Box>
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </ReportShell>
  );
}
