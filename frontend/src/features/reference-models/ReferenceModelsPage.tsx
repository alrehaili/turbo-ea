/**
 * Reference Models — per-domain classification schemes (NEA National RMs).
 * NORA WP100.3.
 *
 * Six domain tabs (Business / Beneficiary Experience / Applications / Data /
 * Technology / Security), each listing its reference models with a governed
 * draft → published → archived lifecycle (publishing supersedes the previous
 * published RM of the domain). The selected model exposes its hierarchical
 * item tree with CRUD, plus xlsx export/import in the exchange layout
 * (Code | Parent Code | Name | Name (Arabic) | Description | Sort Order).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Tab from "@mui/material/Tab";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import MaterialSymbol from "@/components/MaterialSymbol";
import { hasPermission } from "@/components/RequirePermission";
import { api, ApiError } from "@/api/client";
import { useAuthContext } from "@/hooks/AuthContext";
import { invalidateActiveReferenceModels } from "@/hooks/useActiveReferenceModels";
import NarrativeEditor from "@/features/reference-models/browse/NarrativeEditor";
import VersionsDialog from "@/features/reference-models/browse/VersionsDialog";
import type {
  ReferenceModel,
  ReferenceModelDomain,
  ReferenceModelItem,
} from "@/types";

const DOMAINS: ReferenceModelDomain[] = [
  "business",
  "beneficiaryExperience",
  "applications",
  "data",
  "technology",
  "security",
];

const SOURCES = ["national", "sectoral", "agency"] as const;

const STATUS_COLOR: Record<string, "default" | "success" | "warning" | "info"> = {
  draft: "default",
  in_review: "info",
  published: "success",
  archived: "warning",
};

interface ModelEdit {
  id: string | null;
  domain: ReferenceModelDomain;
  name: string;
  name_ar: string;
  description: string;
  version: string;
  source: string;
}

interface ItemEdit {
  id: string | null;
  code: string;
  name: string;
  name_ar: string;
  description: string;
  parent_id: string;
  sort_order: number;
}

const EMPTY_ITEM: ItemEdit = {
  id: null,
  code: "",
  name: "",
  name_ar: "",
  description: "",
  parent_id: "",
  sort_order: 0,
};

/** Depth-first flatten of the item tree for indented rendering. */
function treeOrder(items: ReferenceModelItem[]): { item: ReferenceModelItem; depth: number }[] {
  const byParent = new Map<string | null, ReferenceModelItem[]>();
  for (const item of items) {
    const key = item.parent_id ?? null;
    const bucket = byParent.get(key) ?? [];
    bucket.push(item);
    byParent.set(key, bucket);
  }
  const known = new Set(items.map((i) => i.id));
  const out: { item: ReferenceModelItem; depth: number }[] = [];
  const walk = (parentId: string | null, depth: number) => {
    for (const item of byParent.get(parentId) ?? []) {
      out.push({ item, depth });
      walk(item.id, depth + 1);
    }
  };
  walk(null, 0);
  // Items whose parent row is missing (shouldn't happen) still render as roots.
  for (const item of items) {
    if (item.parent_id && !known.has(item.parent_id)) out.push({ item, depth: 0 });
  }
  return out;
}

export default function ReferenceModelsPage() {
  const { t, i18n } = useTranslation(["reports", "nav", "common"]);
  const { user } = useAuthContext();
  const canManage = hasPermission(user?.permissions, "reference_models.manage");
  const canPublish = canManage && hasPermission(user?.permissions, "governance.approve_step");
  const isArabic = i18n.language.startsWith("ar");

  const [domain, setDomain] = useState<ReferenceModelDomain>("business");
  const [models, setModels] = useState<ReferenceModel[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [items, setItems] = useState<ReferenceModelItem[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [modelEdit, setModelEdit] = useState<ModelEdit | null>(null);
  const [itemEdit, setItemEdit] = useState<ItemEdit | null>(null);
  const [publishFor, setPublishFor] = useState<ReferenceModel | null>(null);
  const [narrativeFor, setNarrativeFor] = useState<ReferenceModel | null>(null);
  const [versionsFor, setVersionsFor] = useState<ReferenceModel | null>(null);
  const [importNewOpen, setImportNewOpen] = useState(false);
  const [importName, setImportName] = useState("");
  const importIntoRef = useRef<HTMLInputElement>(null);
  const importNewRef = useRef<HTMLInputElement>(null);

  const selected = useMemo(
    () => models.find((m) => m.id === selectedId) ?? null,
    [models, selectedId],
  );

  const handleError = (e: unknown) => {
    setError(
      e instanceof ApiError && typeof e.detail === "string"
        ? e.detail
        : e instanceof Error
          ? e.message
          : "error",
    );
  };

  const displayName = (m: { name: string; name_ar: string | null }) =>
    isArabic && m.name_ar ? m.name_ar : m.name;

  const loadModels = useCallback(async () => {
    try {
      const res = await api.get<{ models: ReferenceModel[] }>("/reference-models");
      setModels(res.models);
    } catch (e) {
      handleError(e);
    }
  }, []);

  const loadItems = useCallback(async (modelId: string) => {
    try {
      const res = await api.get<{ model: ReferenceModel; items: ReferenceModelItem[] }>(
        `/reference-models/${modelId}`,
      );
      setItems(res.items);
    } catch (e) {
      handleError(e);
    }
  }, []);

  useEffect(() => {
    void loadModels();
  }, [loadModels]);

  useEffect(() => {
    if (selectedId) void loadItems(selectedId);
    else setItems([]);
  }, [selectedId, loadItems]);

  const domainModels = useMemo(
    () => models.filter((m) => m.domain === domain),
    [models, domain],
  );

  // Keep the selection inside the visible domain.
  useEffect(() => {
    if (selectedId && !domainModels.some((m) => m.id === selectedId)) setSelectedId(null);
  }, [domainModels, selectedId]);

  const refresh = async () => {
    await loadModels();
    if (selectedId) await loadItems(selectedId);
  };

  // ── Model actions ───────────────────────────────────────────────────────
  const saveModel = async () => {
    if (!modelEdit || !modelEdit.name.trim()) return;
    setError("");
    const payload = {
      name: modelEdit.name.trim(),
      name_ar: modelEdit.name_ar.trim() || null,
      description: modelEdit.description.trim() || null,
      version: modelEdit.version.trim() || "1.0",
      source: modelEdit.source,
    };
    try {
      if (modelEdit.id) {
        await api.patch(`/reference-models/${modelEdit.id}`, payload);
      } else {
        const created = await api.post<ReferenceModel>("/reference-models", {
          ...payload,
          domain: modelEdit.domain,
        });
        setSelectedId(created.id);
      }
      setModelEdit(null);
      await refresh();
    } catch (e) {
      handleError(e);
    }
  };

  const deleteModel = async (m: ReferenceModel) => {
    setError("");
    try {
      await api.delete(`/reference-models/${m.id}`);
      if (selectedId === m.id) setSelectedId(null);
      await loadModels();
    } catch (e) {
      handleError(e);
    }
  };

  const publish = async () => {
    if (!publishFor) return;
    setError("");
    try {
      await api.post(`/reference-models/${publishFor.id}/publish`, {});
      setPublishFor(null);
      invalidateActiveReferenceModels();
      await refresh();
    } catch (e) {
      handleError(e);
    }
  };

  const archive = async (m: ReferenceModel) => {
    setError("");
    try {
      await api.post(`/reference-models/${m.id}/archive`, {});
      invalidateActiveReferenceModels();
      await refresh();
    } catch (e) {
      handleError(e);
    }
  };

  const submitForReview = async (m: ReferenceModel) => {
    setError("");
    try {
      await api.post(`/reference-models/${m.id}/submit`, {});
      await refresh();
    } catch (e) {
      handleError(e);
    }
  };

  const reject = async (m: ReferenceModel) => {
    setError("");
    try {
      await api.post(`/reference-models/${m.id}/reject`, {});
      await refresh();
    } catch (e) {
      handleError(e);
    }
  };

  // ── Item actions ────────────────────────────────────────────────────────
  const saveItem = async () => {
    if (!itemEdit || !selected || !itemEdit.code.trim() || !itemEdit.name.trim()) return;
    setError("");
    const payload = {
      code: itemEdit.code.trim(),
      name: itemEdit.name.trim(),
      name_ar: itemEdit.name_ar.trim() || null,
      description: itemEdit.description.trim() || null,
      sort_order: itemEdit.sort_order,
    };
    try {
      if (itemEdit.id) {
        await api.patch(`/reference-models/items/${itemEdit.id}`, {
          ...payload,
          ...(itemEdit.parent_id
            ? { parent_id: itemEdit.parent_id }
            : { clear_parent: true }),
        });
      } else {
        await api.post(`/reference-models/${selected.id}/items`, {
          ...payload,
          parent_id: itemEdit.parent_id || null,
        });
      }
      setItemEdit(null);
      await refresh();
    } catch (e) {
      handleError(e);
    }
  };

  const deleteItem = async (item: ReferenceModelItem) => {
    setError("");
    try {
      await api.delete(`/reference-models/items/${item.id}`);
      await refresh();
    } catch (e) {
      handleError(e);
    }
  };

  // ── Export / import ─────────────────────────────────────────────────────
  const exportModel = async (m: ReferenceModel) => {
    setError("");
    try {
      const res = await api.getRaw(`/reference-models/${m.id}/export`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${m.name.replace(/[^\w؀-ۿ-]+/g, "_")}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      handleError(e);
    }
  };

  const importSummary = (summary: Record<string, number>, errors: string[]) => {
    setNotice(
      t("rmLibrary.importDone", {
        created: summary.created ?? 0,
        updated: summary.updated ?? 0,
        unchanged: summary.unchanged ?? 0,
      }) + (errors.length ? ` — ${errors.join("; ")}` : ""),
    );
  };

  const importIntoSelected = async (file: File) => {
    if (!selected) return;
    setError("");
    setNotice("");
    try {
      const res = await api.upload<{ summary: Record<string, number>; errors: string[] }>(
        `/reference-models/${selected.id}/import`,
        file,
      );
      importSummary(res.summary, res.errors);
      await refresh();
    } catch (e) {
      handleError(e);
    }
  };

  const importAsNew = async (file: File) => {
    setError("");
    setNotice("");
    try {
      const res = await api.upload<{
        model: ReferenceModel;
        summary: Record<string, number>;
        errors: string[];
      }>("/reference-models/import", file, "file", {
        domain,
        name: importName.trim() || file.name.replace(/\.xlsx$/i, ""),
      });
      importSummary(res.summary, res.errors);
      setImportNewOpen(false);
      setImportName("");
      await loadModels();
      setSelectedId(res.model.id);
    } catch (e) {
      handleError(e);
    }
  };

  const orderedItems = useMemo(() => treeOrder(items), [items]);

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 0.5 }}>
        <MaterialSymbol icon="schema" size={28} color="#00695c" />
        <Typography variant="h5" fontWeight={700}>
          {t("rmLibrary.title")}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {t("rmLibrary.subtitle")}
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      {notice && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setNotice("")}>
          {notice}
        </Alert>
      )}

      <Tabs
        value={domain}
        onChange={(_e, v) => setDomain(v)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}
      >
        {DOMAINS.map((d) => (
          <Tab
            key={d}
            value={d}
            label={`${t(`nav:noraProgram.domain.${d}`)} (${models.filter((m) => m.domain === d).length})`}
          />
        ))}
      </Tabs>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
          <Typography variant="subtitle1" fontWeight={700}>
            {t("rmLibrary.modelsIn", { domain: t(`nav:noraProgram.domain.${domain}`) })}
          </Typography>
          <Box sx={{ flex: 1 }} />
          {canManage && (
            <>
              <Button
                size="small"
                variant="outlined"
                startIcon={<MaterialSymbol icon="upload_file" size={16} />}
                onClick={() => setImportNewOpen(true)}
              >
                {t("rmLibrary.importNew")}
              </Button>
              <Button
                size="small"
                variant="contained"
                startIcon={<MaterialSymbol icon="add" size={16} />}
                onClick={() =>
                  setModelEdit({
                    id: null,
                    domain,
                    name: "",
                    name_ar: "",
                    description: "",
                    version: "1.0",
                    source: "agency",
                  })
                }
              >
                {t("rmLibrary.addModel")}
              </Button>
            </>
          )}
        </Box>

        {domainModels.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {t("rmLibrary.emptyDomain")}
          </Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>{t("rmLibrary.colName")}</TableCell>
                <TableCell sx={{ fontWeight: 700, width: 110 }}>
                  {t("rmLibrary.colVersion")}
                </TableCell>
                <TableCell sx={{ fontWeight: 700, width: 120 }}>
                  {t("rmLibrary.colSource")}
                </TableCell>
                <TableCell sx={{ fontWeight: 700, width: 130 }}>
                  {t("rmLibrary.colStatus")}
                </TableCell>
                <TableCell sx={{ fontWeight: 700, width: 90 }} align="right">
                  {t("rmLibrary.colItems")}
                </TableCell>
                <TableCell sx={{ width: 190 }} />
              </TableRow>
            </TableHead>
            <TableBody>
              {domainModels.map((m) => (
                <TableRow
                  key={m.id}
                  hover
                  selected={m.id === selectedId}
                  onClick={() => setSelectedId(m.id)}
                  sx={{ cursor: "pointer" }}
                >
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                      {displayName(m)}
                    </Typography>
                    {m.name_ar && !isArabic && (
                      <Typography variant="caption" color="text.secondary">
                        {m.name_ar}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip size="small" variant="outlined" label={m.version} />
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      variant="outlined"
                      label={t(`rmLibrary.source.${m.source}`)}
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      color={STATUS_COLOR[m.status]}
                      label={t(`rmLibrary.status.${m.status}`)}
                    />
                  </TableCell>
                  <TableCell align="right">{m.item_count ?? 0}</TableCell>
                  <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                    <Tooltip title={t("rmLibrary.export")}>
                      <IconButton size="small" onClick={() => void exportModel(m)}>
                        <MaterialSymbol icon="download" size={16} />
                      </IconButton>
                    </Tooltip>
                    {m.status === "published" && (
                      <Tooltip title={t("rmVersion.title")}>
                        <IconButton size="small" onClick={() => setVersionsFor(m)}>
                          <MaterialSymbol icon="history" size={16} />
                        </IconButton>
                      </Tooltip>
                    )}
                    {canManage && (
                      <>
                        {m.status === "draft" && (
                          <Tooltip title={t("rmReview.submit")}>
                            <IconButton size="small" onClick={() => void submitForReview(m)}>
                              <MaterialSymbol icon="send" size={16} />
                            </IconButton>
                          </Tooltip>
                        )}
                        {m.status === "in_review" && canPublish && (
                          <Tooltip title={t("rmReview.reject")}>
                            <IconButton size="small" color="error" onClick={() => void reject(m)}>
                              <MaterialSymbol icon="cancel" size={16} />
                            </IconButton>
                          </Tooltip>
                        )}
                        {m.status !== "published" && (
                          <Tooltip
                            title={
                              canPublish
                                ? t("rmLibrary.publish")
                                : t("rmLibrary.publishNeedsGovernance")
                            }
                          >
                            <span>
                              <IconButton
                                size="small"
                                color="success"
                                disabled={!canPublish}
                                onClick={() => setPublishFor(m)}
                              >
                                <MaterialSymbol icon="verified" size={16} />
                              </IconButton>
                            </span>
                          </Tooltip>
                        )}
                        {m.status === "published" && (
                          <Tooltip title={t("rmLibrary.archive")}>
                            <IconButton size="small" onClick={() => void archive(m)}>
                              <MaterialSymbol icon="archive" size={16} />
                            </IconButton>
                          </Tooltip>
                        )}
                        <Tooltip title={t("rmPoster.editTitle")}>
                          <IconButton size="small" onClick={() => setNarrativeFor(m)}>
                            <MaterialSymbol icon="dashboard_customize" size={16} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={t("common:actions.edit")}>
                          <IconButton
                            size="small"
                            onClick={() =>
                              setModelEdit({
                                id: m.id,
                                domain: m.domain,
                                name: m.name,
                                name_ar: m.name_ar ?? "",
                                description: m.description ?? "",
                                version: m.version,
                                source: m.source,
                              })
                            }
                          >
                            <MaterialSymbol icon="edit" size={16} />
                          </IconButton>
                        </Tooltip>
                        {m.status !== "published" && (
                          <Tooltip title={t("common:actions.delete")}>
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => void deleteModel(m)}
                            >
                              <MaterialSymbol icon="delete" size={16} />
                            </IconButton>
                          </Tooltip>
                        )}
                      </>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>

      {selected && (
        <Paper sx={{ p: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
            <MaterialSymbol icon="account_tree" size={20} color="#00695c" />
            <Typography variant="subtitle1" fontWeight={700}>
              {t("rmLibrary.itemsTitle", { name: displayName(selected) })}
            </Typography>
            <Chip
              size="small"
              color={STATUS_COLOR[selected.status]}
              label={t(`rmLibrary.status.${selected.status}`)}
            />
            <Box sx={{ flex: 1 }} />
            {canManage && (
              <>
                <Button
                  size="small"
                  variant="outlined"
                  component="label"
                  startIcon={<MaterialSymbol icon="upload_file" size={16} />}
                >
                  {t("rmLibrary.importInto")}
                  <input
                    ref={importIntoRef}
                    hidden
                    type="file"
                    accept=".xlsx"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) void importIntoSelected(file);
                      e.target.value = "";
                    }}
                  />
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<MaterialSymbol icon="add" size={16} />}
                  onClick={() => setItemEdit({ ...EMPTY_ITEM })}
                >
                  {t("rmLibrary.addItem")}
                </Button>
              </>
            )}
          </Box>
          {selected.description && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {selected.description}
            </Typography>
          )}

          {orderedItems.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {t("rmLibrary.emptyItems")}
            </Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 700, width: 160 }}>
                    {t("rmLibrary.colCode")}
                  </TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>{t("rmLibrary.colName")}</TableCell>
                  <TableCell sx={{ fontWeight: 700 }}>
                    {t("rmLibrary.colDescription")}
                  </TableCell>
                  <TableCell sx={{ width: 130 }} />
                </TableRow>
              </TableHead>
              <TableBody>
                {orderedItems.map(({ item, depth }) => (
                  <TableRow key={item.id} hover>
                    <TableCell>
                      <Box sx={{ pl: depth * 2.5, display: "flex", alignItems: "center", gap: 0.5 }}>
                        {depth > 0 && (
                          <MaterialSymbol icon="subdirectory_arrow_right" size={14} />
                        )}
                        <Typography variant="body2" fontFamily="monospace">
                          {item.code}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{displayName(item)}</Typography>
                      {item.name_ar && !isArabic && (
                        <Typography variant="caption" color="text.secondary">
                          {item.name_ar}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {item.description}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      {canManage && (
                        <>
                          <Tooltip title={t("rmLibrary.addChild")}>
                            <IconButton
                              size="small"
                              onClick={() => setItemEdit({ ...EMPTY_ITEM, parent_id: item.id })}
                            >
                              <MaterialSymbol icon="add" size={16} />
                            </IconButton>
                          </Tooltip>
                          <IconButton
                            size="small"
                            onClick={() =>
                              setItemEdit({
                                id: item.id,
                                code: item.code,
                                name: item.name,
                                name_ar: item.name_ar ?? "",
                                description: item.description ?? "",
                                parent_id: item.parent_id ?? "",
                                sort_order: item.sort_order,
                              })
                            }
                          >
                            <MaterialSymbol icon="edit" size={16} />
                          </IconButton>
                          <IconButton size="small" color="error" onClick={() => void deleteItem(item)}>
                            <MaterialSymbol icon="delete" size={16} />
                          </IconButton>
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Paper>
      )}

      {/* Model create / edit dialog */}
      <Dialog open={!!modelEdit} onClose={() => setModelEdit(null)} fullWidth maxWidth="sm">
        <DialogTitle>
          {modelEdit?.id ? t("rmLibrary.editModel") : t("rmLibrary.addModel")}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            autoFocus
            label={t("rmLibrary.colName")}
            value={modelEdit?.name ?? ""}
            onChange={(e) => setModelEdit((p) => (p ? { ...p, name: e.target.value } : p))}
          />
          <TextField
            label={t("rmLibrary.nameAr")}
            dir="rtl"
            value={modelEdit?.name_ar ?? ""}
            onChange={(e) => setModelEdit((p) => (p ? { ...p, name_ar: e.target.value } : p))}
          />
          <TextField
            label={t("rmLibrary.colDescription")}
            multiline
            minRows={2}
            value={modelEdit?.description ?? ""}
            onChange={(e) => setModelEdit((p) => (p ? { ...p, description: e.target.value } : p))}
          />
          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              label={t("rmLibrary.colVersion")}
              sx={{ flex: 1 }}
              value={modelEdit?.version ?? ""}
              onChange={(e) => setModelEdit((p) => (p ? { ...p, version: e.target.value } : p))}
            />
            <TextField
              select
              label={t("rmLibrary.colSource")}
              sx={{ flex: 1 }}
              value={modelEdit?.source ?? "agency"}
              onChange={(e) => setModelEdit((p) => (p ? { ...p, source: e.target.value } : p))}
            >
              {SOURCES.map((s) => (
                <MenuItem key={s} value={s}>
                  {t(`rmLibrary.source.${s}`)}
                </MenuItem>
              ))}
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setModelEdit(null)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" onClick={saveModel} disabled={!modelEdit?.name.trim()}>
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Item create / edit dialog */}
      <Dialog open={!!itemEdit} onClose={() => setItemEdit(null)} fullWidth maxWidth="sm">
        <DialogTitle>
          {itemEdit?.id ? t("rmLibrary.editItem") : t("rmLibrary.addItem")}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <Box sx={{ display: "flex", gap: 2 }}>
            <TextField
              autoFocus
              label={t("rmLibrary.colCode")}
              sx={{ flex: 1 }}
              value={itemEdit?.code ?? ""}
              onChange={(e) => setItemEdit((p) => (p ? { ...p, code: e.target.value } : p))}
            />
            <TextField
              label={t("rmLibrary.colSortOrder")}
              type="number"
              sx={{ width: 140 }}
              value={itemEdit?.sort_order ?? 0}
              onChange={(e) =>
                setItemEdit((p) =>
                  p ? { ...p, sort_order: parseInt(e.target.value, 10) || 0 } : p,
                )
              }
            />
          </Box>
          <TextField
            label={t("rmLibrary.colName")}
            value={itemEdit?.name ?? ""}
            onChange={(e) => setItemEdit((p) => (p ? { ...p, name: e.target.value } : p))}
          />
          <TextField
            label={t("rmLibrary.nameAr")}
            dir="rtl"
            value={itemEdit?.name_ar ?? ""}
            onChange={(e) => setItemEdit((p) => (p ? { ...p, name_ar: e.target.value } : p))}
          />
          <TextField
            label={t("rmLibrary.colDescription")}
            multiline
            minRows={2}
            value={itemEdit?.description ?? ""}
            onChange={(e) => setItemEdit((p) => (p ? { ...p, description: e.target.value } : p))}
          />
          <TextField
            select
            label={t("rmLibrary.parent")}
            value={itemEdit?.parent_id ?? ""}
            onChange={(e) => setItemEdit((p) => (p ? { ...p, parent_id: e.target.value } : p))}
          >
            <MenuItem value="">{t("rmLibrary.noParent")}</MenuItem>
            {items
              .filter((i) => i.id !== itemEdit?.id)
              .map((i) => (
                <MenuItem key={i.id} value={i.id}>
                  {i.code} — {displayName(i)}
                </MenuItem>
              ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setItemEdit(null)}>{t("common:actions.cancel")}</Button>
          <Button
            variant="contained"
            onClick={saveItem}
            disabled={!itemEdit?.code.trim() || !itemEdit?.name.trim()}
          >
            {t("common:actions.save")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Publish confirmation */}
      <Dialog open={!!publishFor} onClose={() => setPublishFor(null)} fullWidth maxWidth="xs">
        <DialogTitle>{t("rmLibrary.publishConfirmTitle")}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t("rmLibrary.publishConfirmBody", {
              name: publishFor ? displayName(publishFor) : "",
              domain: t(`nav:noraProgram.domain.${publishFor?.domain ?? domain}`),
            })}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPublishFor(null)}>{t("common:actions.cancel")}</Button>
          <Button variant="contained" color="success" onClick={publish}>
            {t("rmLibrary.publish")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Import-as-new dialog */}
      <Dialog
        open={importNewOpen}
        onClose={() => setImportNewOpen(false)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>{t("rmLibrary.importNew")}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <DialogContentText>{t("rmLibrary.importHint")}</DialogContentText>
          <TextField
            label={t("rmLibrary.colName")}
            value={importName}
            onChange={(e) => setImportName(e.target.value)}
          />
          <Button variant="contained" component="label">
            {t("rmLibrary.chooseFile")}
            <input
              ref={importNewRef}
              hidden
              type="file"
              accept=".xlsx"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void importAsNew(file);
                e.target.value = "";
              }}
            />
          </Button>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setImportNewOpen(false)}>{t("common:actions.cancel")}</Button>
        </DialogActions>
      </Dialog>

      <NarrativeEditor
        open={!!narrativeFor}
        model={narrativeFor}
        onClose={() => setNarrativeFor(null)}
        onSaved={(updated) => {
          setModels((prev) => prev.map((m) => (m.id === updated.id ? { ...m, ...updated } : m)));
          setNotice(t("rmPoster.saved"));
        }}
      />

      <VersionsDialog
        open={!!versionsFor}
        model={versionsFor}
        onClose={() => setVersionsFor(null)}
      />
    </Box>
  );
}
