/**
 * ServiceCatalogueReport — NORA Business Architecture "Service Catalogue"
 * artifact: every Government Service with its beneficiaries, delivery channels,
 * maturity, fee model and SLA. A real app-wide view (the per-user "seeded saved
 * view" idea from the original plan was the wrong vehicle).
 * [FORK FEATURE] — noraPlan.md WP1.2 / #4.
 */
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Link from "@mui/material/Link";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "@/api/client";
import { STATUS_COLORS } from "@/theme/tokens";
import type { Card } from "@/types";

const MATURITY_COLOR: Record<string, string> = {
  informational: STATUS_COLORS.neutral,
  interactive: STATUS_COLORS.info,
  transactional: STATUS_COLORS.warning,
  proactive: STATUS_COLORS.success,
};

const MATURITY_ORDER = ["proactive", "transactional", "interactive", "informational"];

function asArray(v: unknown): string[] {
  if (Array.isArray(v)) return v.map(String);
  if (typeof v === "string" && v) return [v];
  return [];
}

export default function ServiceCatalogueReport() {
  const { t } = useTranslation(["reports", "common"]);
  const [services, setServices] = useState<Card[] | null>(null);
  const [maturityFilter, setMaturityFilter] = useState("");

  useEffect(() => {
    api
      .get<{ items: Card[] }>("/cards?type=GovService&page_size=10000")
      .then((res) => setServices(res.items))
      .catch(() => setServices([]));
  }, []);

  const filtered = useMemo(() => {
    const list = services ?? [];
    if (!maturityFilter) return list;
    return list.filter((s) => (s.attributes?.serviceMaturity ?? "") === maturityFilter);
  }, [services, maturityFilter]);

  const byMaturity = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const s of services ?? []) {
      const m = String(s.attributes?.serviceMaturity ?? "unknown");
      counts[m] = (counts[m] ?? 0) + 1;
    }
    return counts;
  }, [services]);

  if (!services) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const maturityLabel = (key: string) =>
    t(`serviceCatalogue.maturity.${key}`, { defaultValue: key });
  const feeLabel = (key: string) => t(`serviceCatalogue.fee.${key}`, { defaultValue: key });

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight={700} sx={{ mb: 0.5 }}>
        {t("serviceCatalogue.title")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("serviceCatalogue.subtitle")}
      </Typography>

      {services.length === 0 ? (
        <Alert severity="info">{t("serviceCatalogue.empty")}</Alert>
      ) : (
        <>
          {/* Maturity summary tiles */}
          <Grid container spacing={1} sx={{ mb: 2 }}>
            {MATURITY_ORDER.map((m) => (
              <Grid item xs={6} sm={3} key={m}>
                <Paper variant="outlined" sx={{ p: 1.5, textAlign: "center" }}>
                  <Typography variant="h6" fontWeight={700} sx={{ color: MATURITY_COLOR[m] }}>
                    {byMaturity[m] ?? 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {maturityLabel(m)}
                  </Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>

          <Stack direction="row" sx={{ mb: 1 }}>
            <TextField
              select
              size="small"
              label={t("serviceCatalogue.filterMaturity")}
              value={maturityFilter}
              onChange={(e) => setMaturityFilter(e.target.value)}
              sx={{ minWidth: 200 }}
            >
              <MenuItem value="">{t("serviceCatalogue.allMaturities")}</MenuItem>
              {MATURITY_ORDER.map((m) => (
                <MenuItem key={m} value={m}>
                  {maturityLabel(m)}
                </MenuItem>
              ))}
            </TextField>
          </Stack>

          <Paper variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>{t("serviceCatalogue.colService")}</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>{t("serviceCatalogue.colCode")}</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>
                    {t("serviceCatalogue.colBeneficiaries")}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>
                    {t("serviceCatalogue.colChannels")}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>
                    {t("serviceCatalogue.colMaturity")}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>{t("serviceCatalogue.colFee")}</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }}>
                    {t("serviceCatalogue.colSla")}
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((s) => {
                  const a = s.attributes ?? {};
                  const maturity = String(a.serviceMaturity ?? "");
                  return (
                    <TableRow key={s.id} hover>
                      <TableCell>
                        <Link component={RouterLink} to={`/cards/${s.id}`} underline="hover">
                          {s.name}
                        </Link>
                      </TableCell>
                      <TableCell>{String(a.serviceCode ?? "—")}</TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                          {asArray(a.beneficiaryType).map((b) => (
                            <Chip key={b} size="small" variant="outlined" label={b} />
                          ))}
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                          {asArray(a.deliveryChannel).map((c) => (
                            <Chip key={c} size="small" variant="outlined" label={c} />
                          ))}
                        </Stack>
                      </TableCell>
                      <TableCell>
                        {maturity ? (
                          <Chip
                            size="small"
                            label={maturityLabel(maturity)}
                            sx={{
                              bgcolor: MATURITY_COLOR[maturity] ?? STATUS_COLORS.neutral,
                              color: "#fff",
                            }}
                          />
                        ) : (
                          "—"
                        )}
                      </TableCell>
                      <TableCell>{a.feeModel ? feeLabel(String(a.feeModel)) : "—"}</TableCell>
                      <TableCell align="right">
                        {a.slaDays != null && a.slaDays !== ""
                          ? t("serviceCatalogue.slaDays", { n: Number(a.slaDays) })
                          : "—"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Paper>
        </>
      )}
    </Box>
  );
}
