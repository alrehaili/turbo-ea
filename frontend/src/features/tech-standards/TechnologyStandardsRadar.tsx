import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import CardPicker, { type CardOption } from "@/components/CardPicker";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
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

type Mandate = "mandatory" | "recommended" | "optional";
const MANDATES: Mandate[] = ["mandatory", "recommended", "optional"];

interface StandardRow {
  id: string;
  name: string;
  category: Category;
  status: Status;
  open_exceptions?: number;
  // NORA TRM metadata (noraPlan.md WP1.3)
  standard_body?: string | null;
  mandate?: Mandate;
  review_date?: string | null;
  spec_url?: string | null;
  trm_code?: string | null;
  tech_category?: { id: string; name: string; type: string } | null;
}

interface StandardForm {
  name: string;
  category: Category;
  status: Status;
  standard_body: string;
  mandate: Mandate;
  review_date: string;
  spec_url: string;
  trm_code: string;
  tech_category: CardOption | null;
}

const EMPTY_FORM: StandardForm = {
  name: "",
  category: "technology",
  status: "allowed",
  standard_body: "",
  mandate: "recommended",
  review_date: "",
  spec_url: "",
  trm_code: "",
  tech_category: null,
};

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
  // null = creating a new standard; otherwise the id being edited.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<StandardForm>(EMPTY_FORM);

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

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (s: StandardRow) => {
    setEditingId(s.id);
    setForm({
      name: s.name,
      category: s.category,
      status: s.status,
      standard_body: s.standard_body || "",
      mandate: s.mandate || "recommended",
      review_date: s.review_date || "",
      spec_url: s.spec_url || "",
      trm_code: s.trm_code || "",
      tech_category: s.tech_category
        ? { id: s.tech_category.id, name: s.tech_category.name, type: s.tech_category.type }
        : null,
    });
    setDialogOpen(true);
  };

  const saveStandard = async () => {
    if (!form.name.trim()) return;
    const payload = {
      name: form.name,
      category: form.category,
      status: form.status,
      standard_body: form.standard_body.trim() || null,
      mandate: form.mandate,
      review_date: form.review_date || null,
      spec_url: form.spec_url.trim() || null,
      trm_code: form.trm_code.trim() || null,
      tech_category_id: form.tech_category?.id ?? null,
    };
    if (editingId) {
      await api.patch(`/tech-standards/${editingId}`, payload);
    } else {
      await api.post("/tech-standards", payload);
    }
    setDialogOpen(false);
    setEditingId(null);
    setForm(EMPTY_FORM);
    await load();
  };

  const deleteStandard = async (s: StandardRow) => {
    if (!window.confirm(t("techStandards.confirmDeleteStandard", { name: s.name }))) return;
    await api.delete(`/tech-standards/${s.id}`);
    setDialogOpen(false);
    setEditingId(null);
    await load();
  };

  const deleteException = async (id: string) => {
    if (!window.confirm(t("techStandards.confirmDeleteException"))) return;
    await api.delete(`/tech-standards/exceptions/${id}`);
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
          onClick={openCreate}
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
                                onClick={() => openEdit(std)}
                                sx={{ borderColor: STATUS_COLOR[s], cursor: "pointer" }}
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
                      <Box sx={{ display: "flex", gap: 0.5, justifyContent: "flex-end", alignItems: "center" }}>
                        {e.status === "requested" && (
                          <>
                            <Button size="small" color="success" onClick={() => decide(e.id, "approve")}>
                              {t("techStandards.approve")}
                            </Button>
                            <Button size="small" color="error" onClick={() => decide(e.id, "reject")}>
                              {t("techStandards.reject")}
                            </Button>
                          </>
                        )}
                        <Tooltip title={t("common:actions.delete")}>
                          <IconButton size="small" color="error" onClick={() => deleteException(e.id)}>
                            <MaterialSymbol icon="delete" size={18} />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </Paper>
      )}

      {/* Create / edit standard dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>
          {editingId ? t("techStandards.editStandard") : t("techStandards.newStandard")}
        </DialogTitle>
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
          {/* NORA TRM metadata (noraPlan.md WP1.3) */}
          <TextField
            select
            label={t("techStandards.mandate")}
            value={form.mandate}
            onChange={(e) => setForm({ ...form, mandate: e.target.value as Mandate })}
          >
            {MANDATES.map((m) => (
              <MenuItem key={m} value={m}>
                {t(`techStandards.mandateLevel.${m}`)}
              </MenuItem>
            ))}
          </TextField>
          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              label={t("techStandards.trmCode")}
              value={form.trm_code}
              onChange={(e) => setForm({ ...form, trm_code: e.target.value })}
              sx={{ flex: 1 }}
            />
            <TextField
              label={t("techStandards.standardBody")}
              value={form.standard_body}
              onChange={(e) => setForm({ ...form, standard_body: e.target.value })}
              sx={{ flex: 2 }}
            />
          </Box>
          <CardPicker
            types="TechCategory"
            value={form.tech_category}
            onChange={(v) => setForm({ ...form, tech_category: v })}
            label={t("techStandards.trmCategory")}
            enabled={dialogOpen}
          />
          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              type="date"
              label={t("techStandards.reviewDate")}
              value={form.review_date}
              onChange={(e) => setForm({ ...form, review_date: e.target.value })}
              InputLabelProps={{ shrink: true }}
              sx={{ flex: 1 }}
            />
            <TextField
              label={t("techStandards.specUrl")}
              value={form.spec_url}
              onChange={(e) => setForm({ ...form, spec_url: e.target.value })}
              sx={{ flex: 2 }}
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ justifyContent: editingId ? "space-between" : "flex-end" }}>
          {editingId && (
            <Button
              color="error"
              startIcon={<MaterialSymbol icon="delete" size={18} />}
              onClick={() => {
                const found = radar
                  ? Object.values(radar.matrix)
                      .flatMap((byStatus) => Object.values(byStatus).flat())
                      .find((s) => s.id === editingId)
                  : undefined;
                if (found) deleteStandard(found);
              }}
            >
              {t("common:actions.delete")}
            </Button>
          )}
          <Box sx={{ display: "flex", gap: 1 }}>
            <Button onClick={() => setDialogOpen(false)}>{t("common:actions.cancel")}</Button>
            <Button variant="contained" onClick={saveStandard}>
              {editingId ? t("common:actions.save") : t("common:actions.create")}
            </Button>
          </Box>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
