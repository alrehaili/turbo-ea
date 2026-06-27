import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Badge from "@mui/material/Badge";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import CircularProgress from "@mui/material/CircularProgress";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";

const CATEGORIES = ["technology", "cloud", "integration", "data", "security", "other"] as const;
const STATUSES = ["preferred", "allowed", "tolerated", "sunset", "prohibited"] as const;
type Category = (typeof CATEGORIES)[number];
type Status = (typeof STATUSES)[number];

// Radar ring colours: green (preferred) → red (prohibited).
const STATUS_COLOR: Record<Status, string> = {
  preferred: "#2e7d32",
  allowed: "#0288d1",
  tolerated: "#ed6c02",
  sunset: "#d84315",
  prohibited: "#b71c1c",
};

interface StandardRow {
  id: string;
  name: string;
  category: Category;
  status: Status;
  open_exceptions?: number;
}

interface RadarData {
  categories: Category[];
  statuses: Status[];
  matrix: Record<string, Record<string, StandardRow[]>>;
  summary: { total: number; by_status: Record<string, number>; open_exceptions: number };
}

interface ExceptionRow {
  id: string;
  standard_id: string;
  card: { id: string; name: string } | null;
  justification: string | null;
  compensating_controls: string | null;
  status: string;
  expiry_date: string | null;
  approver_id: string | null;
}

const EXC_STATUS_COLOR: Record<string, "default" | "info" | "success" | "error" | "warning"> = {
  requested: "info",
  approved: "success",
  rejected: "error",
  expired: "warning",
};

export default function TechnologyStandardsRadar() {
  const { t } = useTranslation(["reports", "common"]);
  const [tab, setTab] = useState(0);
  const [radar, setRadar] = useState<RadarData | null>(null);
  const [exceptions, setExceptions] = useState<ExceptionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<{ name: string; category: Category; status: Status }>({
    name: "",
    category: "technology",
    status: "allowed",
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [r, e] = await Promise.all([
        api.get<RadarData>("/tech-standards/radar"),
        api.get<ExceptionRow[]>("/tech-standards/exceptions"),
      ]);
      setRadar(r);
      setExceptions(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const createStandard = async () => {
    if (!form.name.trim()) return;
    await api.post("/tech-standards", form);
    setDialogOpen(false);
    setForm({ name: "", category: "technology", status: "allowed" });
    await load();
  };

  const decide = async (id: string, action: "approve" | "reject") => {
    await api.post(`/tech-standards/exceptions/${id}/decision?action=${action}`, {});
    await load();
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1300, mx: "auto", p: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
        <MaterialSymbol icon="radar" size={26} color="#003399" />
        <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>
          {t("techStandards.title")}
        </Typography>
        <Button
          variant="contained"
          startIcon={<MaterialSymbol icon="add" size={18} />}
          onClick={() => setDialogOpen(true)}
        >
          {t("techStandards.newStandard")}
        </Button>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label={t("techStandards.radarTab")} />
        <Tab
          label={
            <Badge
              color="warning"
              badgeContent={exceptions.filter((e) => e.status === "requested").length}
            >
              <Box sx={{ pr: 1 }}>{t("techStandards.exceptionsTab")}</Box>
            </Badge>
          }
        />
      </Tabs>

      {/* --- Radar / heatmap matrix --- */}
      {tab === 0 && radar && (
        <Box>
          <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
            {STATUSES.map((s) => (
              <Chip
                key={s}
                size="small"
                label={`${t(`techStandards.status.${s}`)}: ${radar.summary.by_status[s] || 0}`}
                sx={{ bgcolor: STATUS_COLOR[s], color: "#fff" }}
              />
            ))}
          </Box>

          <Paper variant="outlined" sx={{ overflowX: "auto" }}>
            <Table size="small" sx={{ minWidth: 900 }}>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700 }}>{t("techStandards.category")}</TableCell>
                  {STATUSES.map((s) => (
                    <TableCell key={s} sx={{ fontWeight: 700 }}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                        <Box
                          sx={{
                            width: 10,
                            height: 10,
                            borderRadius: "50%",
                            bgcolor: STATUS_COLOR[s],
                          }}
                        />
                        {t(`techStandards.status.${s}`)}
                      </Box>
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {CATEGORIES.map((cat) => (
                  <TableRow key={cat}>
                    <TableCell sx={{ fontWeight: 600, verticalAlign: "top" }}>
                      {t(`techStandards.category.${cat}`)}
                    </TableCell>
                    {STATUSES.map((s) => (
                      <TableCell key={s} sx={{ verticalAlign: "top" }}>
                        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                          {(radar.matrix[cat]?.[s] || []).map((std) => (
                            <Badge
                              key={std.id}
                              color="warning"
                              badgeContent={std.open_exceptions || 0}
                              overlap="rectangular"
                            >
                              <Chip
                                size="small"
                                variant="outlined"
                                label={std.name}
                                sx={{ borderColor: STATUS_COLOR[s] }}
                              />
                            </Badge>
                          ))}
                        </Box>
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </Box>
      )}

      {/* --- Exception register --- */}
      {tab === 1 && (
        <Paper variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t("techStandards.colCard")}</TableCell>
                <TableCell>{t("techStandards.colJustification")}</TableCell>
                <TableCell>{t("techStandards.colControls")}</TableCell>
                <TableCell>{t("techStandards.colExpiry")}</TableCell>
                <TableCell>{t("techStandards.colStatus")}</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {exceptions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4, color: "text.secondary" }}>
                    {t("techStandards.noExceptions")}
                  </TableCell>
                </TableRow>
              ) : (
                exceptions.map((e) => (
                  <TableRow key={e.id} hover>
                    <TableCell>
                      {e.card ? (
                        <Box
                          component="a"
                          href={`/cards/${e.card.id}`}
                          sx={{ color: "primary.main", textDecoration: "none" }}
                        >
                          {e.card.name}
                        </Box>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>{e.justification || "—"}</TableCell>
                    <TableCell>{e.compensating_controls || "—"}</TableCell>
                    <TableCell>{e.expiry_date || "—"}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={t(`techStandards.excStatus.${e.status}`, e.status)}
                        color={EXC_STATUS_COLOR[e.status] || "default"}
                      />
                    </TableCell>
                    <TableCell align="right">
                      {e.status === "requested" && (
                        <Box sx={{ display: "flex", gap: 0.5, justifyContent: "flex-end" }}>
                          <Button size="small" color="success" onClick={() => decide(e.id, "approve")}>
                            {t("techStandards.approve")}
                          </Button>
                          <Button size="small" color="error" onClick={() => decide(e.id, "reject")}>
                            {t("techStandards.reject")}
                          </Button>
                        </Box>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </Paper>
      )}

      {/* New standard dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{t("techStandards.newStandard")}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            autoFocus
            label={t("techStandards.name")}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            fullWidth
          />
          <TextField
            select
            label={t("techStandards.category")}
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value as Category })}
          >
            {CATEGORIES.map((c) => (
              <MenuItem key={c} value={c}>
                {t(`techStandards.category.${c}`)}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            label={t("techStandards.status")}
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value as Status })}
          >
            {STATUSES.map((s) => (
              <MenuItem key={s} value={s}>
                {t(`techStandards.status.${s}`)}
              </MenuItem>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={createStandard}>
            {t("common:actions.create")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
