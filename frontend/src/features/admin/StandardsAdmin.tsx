import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import TextField from "@mui/material/TextField";
import Switch from "@mui/material/Switch";
import Chip from "@mui/material/Chip";
import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Divider from "@mui/material/Divider";
import MaterialSymbol from "@/components/MaterialSymbol";
import { api } from "@/api/client";
import type { EAPrinciple, Standard } from "@/types";

interface StandardForm {
  title: string;
  description: string;
  rationale: string;
  implications: string;
  is_active: boolean;
  principle_ids: string[];
}

const EMPTY_FORM: StandardForm = {
  title: "",
  description: "",
  rationale: "",
  implications: "",
  is_active: true,
  principle_ids: [],
};

export default function StandardsAdmin() {
  const { t } = useTranslation(["admin", "common"]);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [principles, setPrinciples] = useState<EAPrinciple[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<StandardForm>(EMPTY_FORM);
  const [deleteConfirm, setDeleteConfirm] = useState<Standard | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [stds, prins] = await Promise.all([
        api.get<Standard[]>("/metamodel/standards"),
        api.get<EAPrinciple[]>("/metamodel/principles"),
      ]);
      setStandards(stds);
      setPrinciples(prins);
    } catch {
      setError(t("metamodel.standards.loadError"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const principleTitle = (id: string) => principles.find((p) => p.id === id)?.title ?? id;

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (s: Standard) => {
    setEditingId(s.id);
    setForm({
      title: s.title,
      description: s.description || "",
      rationale: s.rationale || "",
      implications: s.implications || "",
      is_active: s.is_active,
      principle_ids: s.principle_ids || [],
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingId) {
        await api.patch(`/metamodel/standards/${editingId}`, {
          title: form.title,
          description: form.description || null,
          rationale: form.rationale || null,
          implications: form.implications || null,
          is_active: form.is_active,
          principle_ids: form.principle_ids,
        });
      } else {
        await api.post("/metamodel/standards", {
          title: form.title,
          description: form.description || null,
          rationale: form.rationale || null,
          implications: form.implications || null,
          is_active: form.is_active,
          principle_ids: form.principle_ids,
          sort_order: standards.length,
        });
      }
      setDialogOpen(false);
      fetchData();
    } catch {
      setError(t("metamodel.standards.saveError"));
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await api.delete(`/metamodel/standards/${deleteConfirm.id}`);
      setDeleteConfirm(null);
      fetchData();
    } catch {
      setError(t("metamodel.standards.deleteError"));
    }
  };

  const handleToggleActive = async (s: Standard) => {
    await api.patch(`/metamodel/standards/${s.id}`, {
      is_active: !s.is_active,
    });
    fetchData();
  };

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 2,
        }}
      >
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 600 }}>
          {t("metamodel.standards.description")}
        </Typography>
        <Button
          variant="contained"
          startIcon={<MaterialSymbol icon="add" size={18} />}
          onClick={openCreate}
        >
          {t("metamodel.standards.add")}
        </Button>
      </Box>

      <Divider sx={{ mb: 2 }} />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {!loading && standards.length === 0 && (
        <Box
          sx={{
            py: 6,
            textAlign: "center",
            border: "1px dashed",
            borderColor: "divider",
            borderRadius: 2,
          }}
        >
          <MaterialSymbol icon="rule" size={40} color="#bbb" />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {t("metamodel.standards.empty")}
          </Typography>
        </Box>
      )}

      <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        {standards.map((s) => (
          <Card
            key={s.id}
            sx={{
              opacity: s.is_active ? 1 : 0.55,
              transition: "opacity 0.2s",
            }}
          >
            <CardContent sx={{ py: 2, "&:last-child": { pb: 2 } }}>
              <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.5 }}>
                <MaterialSymbol icon="rule" size={22} color={s.is_active ? "#1976d2" : "#bbb"} />
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                    <Typography variant="subtitle2" fontWeight={600}>
                      {s.title}
                    </Typography>
                    {!s.is_active && (
                      <Chip
                        size="small"
                        label={t("metamodel.standards.inactive")}
                        sx={{ height: 20, fontSize: 11 }}
                      />
                    )}
                  </Box>
                  {s.description && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                      {s.description}
                    </Typography>
                  )}
                  {s.principle_ids.length > 0 && (
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mt: 0.75, flexWrap: "wrap" }}>
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        {t("metamodel.standards.linkedPrinciples")}:
                      </Typography>
                      {s.principle_ids.map((pid) => (
                        <Chip
                          key={pid}
                          size="small"
                          icon={<MaterialSymbol icon="bookmark_star" size={14} />}
                          label={principleTitle(pid)}
                          sx={{ height: 22, fontSize: 11 }}
                        />
                      ))}
                    </Box>
                  )}
                  {(s.rationale || s.implications) && (
                    <Box sx={{ display: "flex", gap: 3, mt: 0.5, flexWrap: "wrap" }}>
                      {s.rationale && (
                        <Box sx={{ flex: 1, minWidth: 200 }}>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            {t("metamodel.standards.rationale")}:
                          </Typography>
                          <Box component="ul" sx={{ m: 0, pl: 2, listStyleType: "'•  '" }}>
                            {s.rationale.split("\n").filter(Boolean).map((line, idx) => (
                              <Typography
                                key={idx}
                                component="li"
                                variant="caption"
                                color="text.secondary"
                                sx={{ py: 0.1 }}
                              >
                                {line}
                              </Typography>
                            ))}
                          </Box>
                        </Box>
                      )}
                      {s.implications && (
                        <Box sx={{ flex: 1, minWidth: 200 }}>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            {t("metamodel.standards.implications")}:
                          </Typography>
                          <Box component="ul" sx={{ m: 0, pl: 2, listStyleType: "'•  '" }}>
                            {s.implications.split("\n").filter(Boolean).map((line, idx) => (
                              <Typography
                                key={idx}
                                component="li"
                                variant="caption"
                                color="text.secondary"
                                sx={{ py: 0.1 }}
                              >
                                {line}
                              </Typography>
                            ))}
                          </Box>
                        </Box>
                      )}
                    </Box>
                  )}
                </Box>
                <Tooltip
                  title={
                    s.is_active
                      ? t("metamodel.standards.deactivate")
                      : t("metamodel.standards.activate")
                  }
                >
                  <Switch size="small" checked={s.is_active} onChange={() => handleToggleActive(s)} />
                </Tooltip>
                <Tooltip title={t("common:actions.edit")}>
                  <IconButton size="small" onClick={() => openEdit(s)}>
                    <MaterialSymbol icon="edit" size={18} />
                  </IconButton>
                </Tooltip>
                <Tooltip title={t("common:actions.delete")}>
                  <IconButton size="small" onClick={() => setDeleteConfirm(s)}>
                    <MaterialSymbol icon="delete" size={18} />
                  </IconButton>
                </Tooltip>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* Create / Edit Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        disableRestoreFocus
      >
        <DialogTitle>
          {editingId
            ? t("metamodel.standards.editTitle")
            : t("metamodel.standards.createTitle")}
        </DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label={t("metamodel.standards.titleLabel")}
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            sx={{ mt: 1, mb: 2 }}
            placeholder={t("metamodel.standards.titlePlaceholder")}
          />
          <TextField
            fullWidth
            multiline
            rows={2}
            label={t("metamodel.standards.descriptionLabel")}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            sx={{ mb: 2 }}
            placeholder={t("metamodel.standards.descriptionPlaceholder")}
          />
          <Autocomplete
            multiple
            options={principles.map((p) => p.id)}
            value={form.principle_ids}
            onChange={(_, val) => setForm({ ...form, principle_ids: val })}
            getOptionLabel={principleTitle}
            renderInput={(params) => (
              <TextField
                {...params}
                label={t("metamodel.standards.linkedPrinciples")}
                placeholder={t("metamodel.standards.linkedPrinciplesPlaceholder")}
              />
            )}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            multiline
            rows={2}
            label={t("metamodel.standards.rationaleLabel")}
            value={form.rationale}
            onChange={(e) => setForm({ ...form, rationale: e.target.value })}
            sx={{ mb: 2 }}
            placeholder={t("metamodel.standards.rationalePlaceholder")}
          />
          <TextField
            fullWidth
            multiline
            rows={2}
            label={t("metamodel.standards.implicationsLabel")}
            value={form.implications}
            onChange={(e) => setForm({ ...form, implications: e.target.value })}
            placeholder={t("metamodel.standards.implicationsPlaceholder")}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={handleSave} disabled={!form.title.trim()}>
            {editingId ? t("common:actions.save") : t("common:actions.create")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog
        open={!!deleteConfirm}
        onClose={() => setDeleteConfirm(null)}
        maxWidth="xs"
        fullWidth
        disableRestoreFocus
      >
        <DialogTitle>{t("metamodel.standards.deleteTitle")}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mt: 1 }}>
            {t("metamodel.standards.deleteConfirm", { title: deleteConfirm?.title })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(null)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>
            {t("common:actions.delete")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
