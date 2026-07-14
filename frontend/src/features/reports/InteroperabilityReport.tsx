/**
 * InteroperabilityReport — integration & interoperability posture: every
 * Interface and Data Exchange with its NORA attributes and connected
 * applications; sensitive off-GSB exchanges flagged.
 * [FORK FEATURE] — noraPlan.md WP4.5.
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";

interface InteropEntry {
  id: string;
  name: string;
  kind: "Interface" | "DataExchange";
  integration_type: string | null;
  via_gsb: boolean;
  classification: string | null;
  external_party: string | null;
  frequency: string | null;
  applications: { id: string; name: string; direction: string | null }[];
}

interface InteropData {
  items: InteropEntry[];
  summary: { total: number; via_gsb: number; external: number; sensitive_off_gsb: number };
}

export default function InteroperabilityReport() {
  const { t } = useTranslation(["reports", "common"]);
  const [data, setData] = useState<InteropData | null>(null);

  useEffect(() => {
    api
      .get<InteropData>("/reports/interoperability")
      .then(setData)
      .catch(() => setData({ items: [], summary: { total: 0, via_gsb: 0, external: 0, sensitive_off_gsb: 0 } }));
  }, []);

  if (!data) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        {t("interop.title")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("interop.subtitle")}
      </Typography>

      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
        <Chip variant="outlined" label={`${t("interop.total")}: ${data.summary.total}`} />
        <Chip
          variant="outlined"
          icon={<MaterialSymbol icon="hub" size={16} />}
          label={`${t("interop.viaGsb")}: ${data.summary.via_gsb}`}
        />
        <Chip
          variant="outlined"
          label={`${t("interop.external")}: ${data.summary.external}`}
        />
        <Chip
          color={data.summary.sensitive_off_gsb ? "error" : "default"}
          variant="outlined"
          icon={<MaterialSymbol icon="gpp_maybe" size={16} />}
          label={`${t("interop.sensitiveOffGsb")}: ${data.summary.sensitive_off_gsb}`}
        />
      </Box>

      {data.summary.sensitive_off_gsb > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {t("interop.sensitiveHint", { count: data.summary.sensitive_off_gsb })}
        </Alert>
      )}

      {data.items.length === 0 ? (
        <Alert severity="info">{t("interop.empty")}</Alert>
      ) : (
        <Paper variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>{t("interop.colName")}</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>{t("interop.colKind")}</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>{t("interop.colType")}</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>{t("interop.colClassification")}</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>GSB</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>{t("interop.colExternal")}</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>{t("interop.colApplications")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.items.map((e) => (
                <TableRow
                  key={e.id}
                  hover
                  sx={
                    ["secret", "topSecret"].includes(e.classification ?? "") && !e.via_gsb
                      ? { bgcolor: "rgba(244, 67, 54, 0.06)" }
                      : undefined
                  }
                >
                  <TableCell>
                    <Link component={RouterLink} to={`/cards/${e.id}`} underline="hover">
                      {e.name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Chip size="small" variant="outlined" label={e.kind} />
                  </TableCell>
                  <TableCell>{e.integration_type ?? "—"}</TableCell>
                  <TableCell>{e.classification ?? "—"}</TableCell>
                  <TableCell>
                    {e.via_gsb ? (
                      <MaterialSymbol icon="check_circle" size={18} color="#2e7d32" />
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell>{e.external_party ?? "—"}</TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                      {e.applications.map((a) => (
                        <Chip
                          key={`${a.id}-${a.direction ?? ""}`}
                          size="small"
                          variant="outlined"
                          component={RouterLink}
                          to={`/cards/${a.id}`}
                          clickable
                          label={a.direction ? `${a.name} · ${a.direction}` : a.name}
                        />
                      ))}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Box>
  );
}
