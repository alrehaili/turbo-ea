import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { BenefitListResponse, BenefitStatus, BenefitType } from "@/types";
import BenefitDrawer from "./BenefitDrawer";
import BenefitFormDialog from "./BenefitFormDialog";
import { BENEFIT_STATUS_COLOR, formatMoney } from "./benefitFormat";

const STATUSES: BenefitStatus[] = ["planned", "validated", "not_realised", "withdrawn"];
const TYPES: BenefitType[] = ["cost_saving", "cost_avoidance", "revenue", "productivity", "non_financial"];

/**
 * The benefits register (D-12): every benefit the viewer may see, with its
 * planned value and what Finance has confirmed — never one figure for both.
 * The selected benefit lives in the URL (`?benefit=`) so a link opens it.
 */
export default function BenefitsRegisterPage() {
  const { t, i18n } = useTranslation("common");
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState<"" | BenefitStatus>("");
  const [type, setType] = useState<"" | BenefitType>("");
  const [creating, setCreating] = useState(false);
  const [refetchKey, setRefetchKey] = useState(0);
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (type) params.set("benefit_type", type);
  const query = params.toString();
  const { data, error, loading } = useApiQuery<BenefitListResponse>(
    `/benefits${query ? `?${query}` : ""}`,
    { refetchKey },
  );
  const selected = searchParams.get("benefit");

  const select = (id: string | null) => {
    const next = new URLSearchParams(searchParams);
    if (id) next.set("benefit", id);
    else next.delete("benefit");
    setSearchParams(next, { replace: true });
  };
  const money = (v: number | null, currency: string | null) =>
    v === null || !currency ? "—" : formatMoney(v, currency, i18n.language);

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <Box sx={{ flex: 1, minWidth: 240 }}>
          <Typography variant="h5" fontWeight={700}>
            {t("benefits.title")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t("benefits.subtitle")}
          </Typography>
        </Box>
        {data?.permissions.manage && (
          <Button
            variant="contained"
            startIcon={<MaterialSymbol icon="add" />}
            onClick={() => setCreating(true)}
          >
            {t("benefits.new")}
          </Button>
        )}
      </Box>

      <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <TextField
          select
          size="small"
          label={t("benefits.filters.status")}
          value={status}
          onChange={(e) => setStatus(e.target.value as "" | BenefitStatus)}
          sx={{ minWidth: 200 }}
        >
          <MenuItem value="">{t("benefits.filters.all")}</MenuItem>
          {STATUSES.map((s) => (
            <MenuItem key={s} value={s}>
              {t(`benefits.status.${s}`)}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          size="small"
          label={t("benefits.filters.type")}
          value={type}
          onChange={(e) => setType(e.target.value as "" | BenefitType)}
          sx={{ minWidth: 220 }}
        >
          <MenuItem value="">{t("benefits.filters.all")}</MenuItem>
          {TYPES.map((v) => (
            <MenuItem key={v} value={v}>
              {t(`benefits.type.${v}`)}
            </MenuItem>
          ))}
        </TextField>
      </Box>

      {data && !data.permissions.costs && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {t("benefits.amountRestricted")}
        </Alert>
      )}
      {error && <Alert severity="error">{error.message}</Alert>}
      {loading && <LinearProgress />}
      {data && data.items.length === 0 && (
        <Typography variant="body2" color="text.secondary">
          {t("benefits.empty")}
        </Typography>
      )}
      {data && data.items.length > 0 && (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t("benefits.col.reference")}</TableCell>
                <TableCell>{t("benefits.col.title")}</TableCell>
                <TableCell>{t("benefits.col.type")}</TableCell>
                <TableCell>{t("benefits.col.status")}</TableCell>
                <TableCell>{t("benefits.col.owner")}</TableCell>
                <TableCell align="right">{t("benefits.col.planned")}</TableCell>
                <TableCell align="right">{t("benefits.col.confirmed")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.items.map((b) => (
                <TableRow key={b.id} hover sx={{ cursor: "pointer" }} onClick={() => select(b.id)}>
                  <TableCell>{b.reference}</TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight={600} dir="auto">
                      {b.title}
                    </Typography>
                    <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap", mt: 0.5 }}>
                      {b.awaiting_finance > 0 && (
                        <Chip
                          size="small"
                          color="info"
                          variant="outlined"
                          label={t("benefits.awaitingFinance", { count: b.awaiting_finance })}
                        />
                      )}
                      {!b.governance_link && (
                        <Chip size="small" variant="outlined" color="warning" label={t("benefits.noGovernanceLink")} />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    {t(`benefits.type.${b.benefit_type}`)}
                    <Typography variant="caption" color="text.secondary" component="div">
                      {t(`benefits.measurement.${b.measurement}`)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip size="small" color={BENEFIT_STATUS_COLOR[b.status]} label={t(`benefits.status.${b.status}`)} />
                  </TableCell>
                  <TableCell>{b.owner_name ?? "—"}</TableCell>
                  <TableCell align="right">
                    <bdi>{b.measurement === "financial" ? money(b.planned_amount, b.currency) : "—"}</bdi>
                    {b.recurrence && b.planned_amount !== null && (
                      <Typography variant="caption" color="text.secondary" component="div">
                        {t(`benefits.recurrence.${b.recurrence}`)}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <bdi>{b.measurement === "financial" ? money(b.confirmed_total, b.currency) : "—"}</bdi>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <BenefitFormDialog
        open={creating}
        benefit={null}
        onClose={() => setCreating(false)}
        onSaved={(b) => {
          setCreating(false);
          setRefetchKey((n) => n + 1);
          select(b.id);
        }}
      />
      <BenefitDrawer
        benefitId={selected}
        onClose={() => select(null)}
        onChanged={() => setRefetchKey((n) => n + 1)}
      />
    </Box>
  );
}
