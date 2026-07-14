/**
 * NEA alignment / evidence-pack export panel — NORA WP5.3.
 *
 * Embedded on the NORA Program page. Generates an immutable multi-sheet .xlsx
 * snapshot of the agency's NORA posture (maturity, program status, BRM
 * coverage, shared services, standards compliance, approval history), lists
 * past packs with headline metrics, and offers download / delete.
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";

interface EvidencePack {
  id: string;
  title: string;
  status: "generating" | "ready" | "failed";
  filename: string | null;
  file_size: number | null;
  summary: Record<string, number | null>;
  error_message: string | null;
  generated_by_display_name: string | null;
  generated_at: string | null;
  created_at: string | null;
}

export default function NeaEvidencePanel({ canManage }: { canManage: boolean }) {
  const { t } = useTranslation(["nav", "common"]);
  const [packs, setPacks] = useState<EvidencePack[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setPacks(await api.get<EvidencePack[]>("/nea-evidence-packs"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const generate = async () => {
    setBusy(true);
    setError("");
    try {
      await api.post("/nea-evidence-packs", {});
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "error");
    } finally {
      setBusy(false);
    }
  };

  const download = async (pack: EvidencePack) => {
    const res = await api.getRaw(`/nea-evidence-packs/${pack.id}/download`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = pack.filename || "nea_evidence.xlsx";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const remove = async (id: string) => {
    await api.delete(`/nea-evidence-packs/${id}`);
    await load();
  };

  return (
    <Paper sx={{ p: 2, mt: 3 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1}>
        <Box>
          <Typography variant="subtitle1" fontWeight={600}>
            <MaterialSymbol
              icon="inventory_2"
              size={20}
              style={{ verticalAlign: "middle", marginInlineEnd: 6 }}
            />
            {t("noraProgram.evidence.title")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("noraProgram.evidence.subtitle")}
          </Typography>
        </Box>
        {canManage && (
          <Button
            variant="contained"
            disabled={busy}
            startIcon={<MaterialSymbol icon="download_for_offline" />}
            onClick={() => void generate()}
          >
            {t("noraProgram.evidence.generate")}
          </Button>
        )}
      </Stack>

      {error && (
        <Typography variant="body2" color="error" sx={{ mb: 1 }}>
          {error}
        </Typography>
      )}

      {packs.length ? (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("noraProgram.evidence.colTitle")}</TableCell>
              <TableCell>{t("noraProgram.evidence.colGenerated")}</TableCell>
              <TableCell>{t("noraProgram.evidence.colHighlights")}</TableCell>
              <TableCell align="right" />
            </TableRow>
          </TableHead>
          <TableBody>
            {packs.map((p) => (
              <TableRow key={p.id} hover>
                <TableCell>{p.title}</TableCell>
                <TableCell>
                  {p.generated_at ? new Date(p.generated_at).toLocaleString() : "—"}
                  {p.generated_by_display_name ? ` · ${p.generated_by_display_name}` : ""}
                </TableCell>
                <TableCell>
                  {p.status === "ready" ? (
                    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                      <Chip
                        size="small"
                        label={`${t("noraProgram.evidence.maturity")} ${p.summary.maturity_score ?? "—"}%`}
                      />
                      <Chip
                        size="small"
                        label={`${t("noraProgram.evidence.brm")} ${p.summary.brm_coverage ?? 0}%`}
                      />
                      <Chip
                        size="small"
                        label={`${t("noraProgram.evidence.program")} ${p.summary.program_progress ?? 0}%`}
                      />
                    </Stack>
                  ) : (
                    <Chip
                      size="small"
                      color={p.status === "failed" ? "error" : "default"}
                      label={t(`noraProgram.evidence.status.${p.status}`)}
                    />
                  )}
                </TableCell>
                <TableCell align="right">
                  {p.status === "ready" && (
                    <Tooltip title={t("noraProgram.evidence.download")}>
                      <IconButton size="small" onClick={() => void download(p)}>
                        <MaterialSymbol icon="download" />
                      </IconButton>
                    </Tooltip>
                  )}
                  {canManage && (
                    <Tooltip title={t("common:actions.delete")}>
                      <IconButton size="small" onClick={() => void remove(p.id)}>
                        <MaterialSymbol icon="delete" />
                      </IconButton>
                    </Tooltip>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <Typography variant="body2" color="text.secondary">
          {t("noraProgram.evidence.empty")}
        </Typography>
      )}
    </Paper>
  );
}
