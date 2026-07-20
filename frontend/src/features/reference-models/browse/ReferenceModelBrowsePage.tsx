/**
 * Reference Model overview page (RMPlan Phase 1, pages 2–4 in one screen).
 *
 * Shows one domain's published reference model as an expandable tree or a
 * flat table, with per-item mapped-inventory counts and coverage badges.
 * Selecting an item opens a side panel with its details and the actual
 * inventory cards mapped to it (via the domain's RM code attribute), each
 * linking into the card detail page. View mode, search text and selection
 * live in URL query params so views can be bookmarked and shared.
 *
 * [FORK FEATURE] — Reference Models browse (RMPlan/rmPlan.md).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Alert from "@mui/material/Alert";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import InputAdornment from "@mui/material/InputAdornment";
import MaterialSymbol from "@/components/MaterialSymbol";
import { hasPermission } from "@/components/RequirePermission";
import { api } from "@/api/client";
import { useAuthContext } from "@/hooks/AuthContext";
import type {
  ReferenceModel,
  ReferenceModelItemWithCounts,
  ReferenceModelMappedCard,
  ReferenceModelSummary,
} from "@/types";
import { RM_DOMAIN_META, isRmDomain } from "./domainMeta";
import MappingDialog from "./MappingDialog";
import ReferenceModelPoster from "./ReferenceModelPoster";
import ReferenceModelCoverage from "./ReferenceModelCoverage";

type Coverage = "covered" | "partial" | "notMapped";

function coverageOf(item: ReferenceModelItemWithCounts): Coverage {
  if (item.mapped_direct > 0) return "covered";
  if (item.mapped_total > 0) return "partial";
  return "notMapped";
}

const COVERAGE_CHIP: Record<Coverage, "success" | "warning" | "default"> = {
  covered: "success",
  partial: "warning",
  notMapped: "default",
};

interface TreeRow {
  item: ReferenceModelItemWithCounts;
  depth: number;
  hasChildren: boolean;
}

export default function ReferenceModelBrowsePage() {
  const { domain } = useParams();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation(["reports", "nav", "common"]);
  const { user } = useAuthContext();
  const canManage = hasPermission(user?.permissions, "reference_models.manage");
  const isAr = i18n.language === "ar";
  const [searchParams, setSearchParams] = useSearchParams();

  const canMap = canManage || hasPermission(user?.permissions, "reference_models.map");
  const rawView = searchParams.get("view");
  const view =
    rawView === "table" || rawView === "unmapped" || rawView === "map" || rawView === "coverage"
      ? rawView
      : "tree";
  const query = searchParams.get("q") ?? "";
  const selectedId = searchParams.get("selected");

  const [summary, setSummary] = useState<ReferenceModelSummary | null>(null);
  const [noModel, setNoModel] = useState(false);
  const [error, setError] = useState(false);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  // Bumped after a mapping mutation so the item panel refetches its card list.
  const [mutationTick, setMutationTick] = useState(0);

  const setParam = useCallback(
    (key: string, value: string | null) => {
      const next = new URLSearchParams(searchParams);
      if (value) next.set(key, value);
      else next.delete(key);
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const loadSummary = useCallback(async (modelId: string) => {
    const s = await api.get<ReferenceModelSummary>(`/reference-models/${modelId}/summary`);
    setSummary(s);
  }, []);

  useEffect(() => {
    if (!isRmDomain(domain)) return;
    let cancelled = false;
    setSummary(null);
    setNoModel(false);
    setError(false);
    api
      .get<{ model: ReferenceModel | null }>(`/reference-models/active?domain=${domain}`)
      .then((res) => {
        if (cancelled) return;
        if (!res.model) {
          setNoModel(true);
          return;
        }
        return loadSummary(res.model.id).catch(() => {
          if (!cancelled) setError(true);
        });
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, [domain, loadSummary]);

  // Refetch counts + panel after a mapping create/edit/delete.
  const onMappingMutated = useCallback(() => {
    setMutationTick((n) => n + 1);
    if (summary?.model) loadSummary(summary.model.id).catch(() => undefined);
  }, [summary, loadSummary]);

  const itemName = useCallback(
    (item: { name: string; name_ar: string | null }) =>
      isAr && item.name_ar ? item.name_ar : item.name,
    [isAr],
  );

  const byId = useMemo(
    () => new Map((summary?.items ?? []).map((i) => [i.id, i])),
    [summary],
  );

  // Depth-first tree order, honouring the search filter (a match keeps its
  // ancestors visible) and the collapsed set.
  const treeRows = useMemo<TreeRow[]>(() => {
    if (!summary) return [];
    const items = summary.items;
    const children = new Map<string | null, ReferenceModelItemWithCounts[]>();
    const known = new Set(items.map((i) => i.id));
    for (const item of items) {
      const parent = item.parent_id && known.has(item.parent_id) ? item.parent_id : null;
      const bucket = children.get(parent) ?? [];
      bucket.push(item);
      children.set(parent, bucket);
    }
    const q = query.trim().toLowerCase();
    const matches = (i: ReferenceModelItemWithCounts) =>
      !q ||
      i.code.toLowerCase().includes(q) ||
      i.name.toLowerCase().includes(q) ||
      (i.name_ar ?? "").toLowerCase().includes(q);
    const visible = new Set<string>();
    if (q) {
      const markUp = (id: string | null) => {
        while (id) {
          if (visible.has(id)) break;
          visible.add(id);
          id = byId.get(id)?.parent_id ?? null;
        }
      };
      for (const item of items) if (matches(item)) markUp(item.id);
    }
    const out: TreeRow[] = [];
    const walk = (parentId: string | null, depth: number) => {
      for (const item of children.get(parentId) ?? []) {
        if (q && !visible.has(item.id)) continue;
        const kids = children.get(item.id) ?? [];
        out.push({ item, depth, hasChildren: kids.length > 0 });
        if (!collapsed.has(item.id)) walk(item.id, depth + 1);
      }
    };
    walk(null, 0);
    return out;
  }, [summary, query, collapsed, byId]);

  const depthOf = useCallback(
    (item: ReferenceModelItemWithCounts) => {
      let depth = 0;
      let parent = item.parent_id;
      const seen = new Set<string>();
      while (parent && byId.has(parent) && !seen.has(parent)) {
        seen.add(parent);
        depth += 1;
        parent = byId.get(parent)!.parent_id;
      }
      return depth;
    },
    [byId],
  );

  if (!isRmDomain(domain)) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">{t("rmBrowse.unknownDomain")}</Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate("/reference-models")}>
          {t("rmBrowse.backToModels")}
        </Button>
      </Box>
    );
  }

  const meta = RM_DOMAIN_META[domain];
  const model = summary?.model ?? null;
  const totals = summary?.totals;
  const selected = selectedId ? (byId.get(selectedId) ?? null) : null;

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: "auto" }}>
      {/* Breadcrumb-ish back link + header */}
      <Button
        size="small"
        startIcon={<MaterialSymbol icon={isAr ? "arrow_forward" : "arrow_back"} size={18} />}
        onClick={() => navigate("/reference-models")}
        sx={{ mb: 1 }}
      >
        {t("rmBrowse.backToModels")}
      </Button>

      {error && <Alert severity="error">{t("common:errors.generic")}</Alert>}
      {noModel && (
        <Alert
          severity="info"
          action={
            canManage ? (
              <Button size="small" onClick={() => navigate("/reference-models/manage")}>
                {t("rmBrowse.manage")}
              </Button>
            ) : undefined
          }
        >
          {t("rmBrowse.noPublished")}
        </Alert>
      )}
      {!summary && !noModel && !error && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {summary && model && totals && (
        <>
          <Paper variant="outlined" sx={{ p: 2, mb: 2, borderTop: `3px solid ${meta.color}` }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, flexWrap: "wrap" }}>
              <Avatar sx={{ bgcolor: meta.color, width: 44, height: 44 }}>
                <MaterialSymbol icon={meta.icon} size={24} />
              </Avatar>
              <Box sx={{ flex: 1, minWidth: 220 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                  <Typography variant="h6" fontWeight={700}>
                    {itemName(model)}
                  </Typography>
                  <Chip size="small" label={meta.code} sx={{ direction: "ltr" }} />
                  <Chip size="small" variant="outlined" label={`v${model.version}`} sx={{ direction: "ltr" }} />
                  <Chip size="small" color="success" label={t("rmLibrary.status.published")} />
                  <Chip size="small" variant="outlined" label={t(`rmLibrary.source.${model.source}`)} />
                </Box>
                {model.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {model.description}
                  </Typography>
                )}
              </Box>
              {canManage && (
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<MaterialSymbol icon="settings" size={18} />}
                  onClick={() => navigate("/reference-models/manage")}
                >
                  {t("rmBrowse.manage")}
                </Button>
              )}
            </Box>
            <Box sx={{ display: "flex", gap: 3, mt: 1.5, flexWrap: "wrap" }}>
              <HeaderMetric label={t("rmBrowse.items")} value={totals.total_items} />
              <HeaderMetric
                label={t("rmBrowse.coverage")}
                value={`${totals.total_items ? Math.round((totals.covered_items / totals.total_items) * 100) : 0}%`}
              />
              <HeaderMetric label={t("rmBrowse.mappedCards")} value={totals.mapped_cards} />
              <HeaderMetric label={t("rmBrowse.unmatched")} value={totals.unmatched_cards} />
              <HeaderMetric label={t("rmBrowse.uncoded")} value={totals.uncoded_cards} />
            </Box>
          </Paper>

          {/* Toolbar: view switcher + search */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 1.5, flexWrap: "wrap" }}>
            <ToggleButtonGroup
              size="small"
              exclusive
              value={view}
              onChange={(_e, v) => v && setParam("view", v === "tree" ? null : v)}
            >
              <ToggleButton value="map">
                <MaterialSymbol icon="grid_view" size={18} />
                <Box component="span" sx={{ mx: 0.5 }}>{t("rmBrowse.viewMap")}</Box>
              </ToggleButton>
              <ToggleButton value="tree">
                <MaterialSymbol icon="account_tree" size={18} />
                <Box component="span" sx={{ ms: 0.5, mx: 0.5 }}>{t("rmBrowse.viewTree")}</Box>
              </ToggleButton>
              <ToggleButton value="table">
                <MaterialSymbol icon="table_chart" size={18} />
                <Box component="span" sx={{ mx: 0.5 }}>{t("rmBrowse.viewTable")}</Box>
              </ToggleButton>
              <ToggleButton value="coverage">
                <MaterialSymbol icon="insights" size={18} />
                <Box component="span" sx={{ mx: 0.5 }}>{t("rmBrowse.viewCoverage")}</Box>
              </ToggleButton>
              <ToggleButton value="unmapped">
                <MaterialSymbol icon="link_off" size={18} />
                <Box component="span" sx={{ mx: 0.5 }}>{t("rmBrowse.viewUnmapped")}</Box>
              </ToggleButton>
            </ToggleButtonGroup>
            <TextField
              size="small"
              value={query}
              onChange={(e) => setParam("q", e.target.value || null)}
              placeholder={t("rmBrowse.searchPlaceholder")}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <MaterialSymbol icon="search" size={18} />
                  </InputAdornment>
                ),
              }}
              sx={{ width: 280 }}
            />
          </Box>

          {view === "coverage" ? (
            <ReferenceModelCoverage
              modelId={model.id}
              query={query}
              itemName={itemName}
              onSelect={(id) => setParam("selected", id)}
            />
          ) : view === "map" ? (
            <ReferenceModelPoster
              model={model}
              items={summary.items}
              itemName={itemName}
              selectedId={selectedId}
              onSelect={(id) => setParam("selected", id)}
            />
          ) : view === "tree" ? (
            <Paper variant="outlined">
              {treeRows.length === 0 && (
                <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                  {t("rmBrowse.noItems")}
                </Typography>
              )}
              {treeRows.map(({ item, depth, hasChildren }) => {
                const cov = coverageOf(item);
                return (
                  <Box
                    key={item.id}
                    onClick={() => setParam("selected", item.id)}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                      py: 0.5,
                      px: 1,
                      ps: `${8 + depth * 28}px`,
                      paddingInlineStart: `${8 + depth * 28}px`,
                      cursor: "pointer",
                      borderBottom: "1px solid",
                      borderColor: "divider",
                      bgcolor: selectedId === item.id ? "action.selected" : undefined,
                      "&:hover": { bgcolor: "action.hover" },
                    }}
                  >
                    {hasChildren ? (
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          setCollapsed((prev) => {
                            const next = new Set(prev);
                            if (next.has(item.id)) next.delete(item.id);
                            else next.add(item.id);
                            return next;
                          });
                        }}
                      >
                        <MaterialSymbol
                          icon={collapsed.has(item.id) ? (isAr ? "chevron_left" : "chevron_right") : "expand_more"}
                          size={18}
                        />
                      </IconButton>
                    ) : (
                      <Box sx={{ width: 34 }} />
                    )}
                    <Chip size="small" variant="outlined" label={item.code} sx={{ direction: "ltr", fontFamily: "monospace" }} />
                    <Typography variant="body2" sx={{ flex: 1, minWidth: 0 }} noWrap>
                      {itemName(item)}
                    </Typography>
                    <Tooltip title={t("rmBrowse.mappedTotalHint")}>
                      <Chip
                        size="small"
                        color={COVERAGE_CHIP[cov]}
                        variant={cov === "notMapped" ? "outlined" : "filled"}
                        label={item.mapped_total}
                      />
                    </Tooltip>
                  </Box>
                );
              })}
            </Paper>
          ) : view === "table" ? (
            <Paper variant="outlined" sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("rmLibrary.colCode")}</TableCell>
                    <TableCell>{t("rmLibrary.colName")}</TableCell>
                    <TableCell align="center">{t("rmBrowse.colLevel")}</TableCell>
                    <TableCell>{t("rmLibrary.parent")}</TableCell>
                    <TableCell align="center">{t("rmBrowse.colMappedDirect")}</TableCell>
                    <TableCell align="center">{t("rmBrowse.colMappedTotal")}</TableCell>
                    <TableCell>{t("rmBrowse.coverage")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {summary.items
                    .filter((i) => {
                      const q = query.trim().toLowerCase();
                      return (
                        !q ||
                        i.code.toLowerCase().includes(q) ||
                        i.name.toLowerCase().includes(q) ||
                        (i.name_ar ?? "").toLowerCase().includes(q)
                      );
                    })
                    .map((item) => {
                      const cov = coverageOf(item);
                      const parent = item.parent_id ? byId.get(item.parent_id) : null;
                      return (
                        <TableRow
                          key={item.id}
                          hover
                          selected={selectedId === item.id}
                          sx={{ cursor: "pointer" }}
                          onClick={() => setParam("selected", item.id)}
                        >
                          <TableCell sx={{ direction: "ltr", fontFamily: "monospace" }}>{item.code}</TableCell>
                          <TableCell>{itemName(item)}</TableCell>
                          <TableCell align="center">{depthOf(item) + 1}</TableCell>
                          <TableCell>{parent ? itemName(parent) : "—"}</TableCell>
                          <TableCell align="center">{item.mapped_direct}</TableCell>
                          <TableCell align="center">{item.mapped_total}</TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              color={COVERAGE_CHIP[cov]}
                              variant={cov === "notMapped" ? "outlined" : "filled"}
                              label={t(`rmBrowse.${cov}`)}
                            />
                          </TableCell>
                        </TableRow>
                      );
                    })}
                </TableBody>
              </Table>
            </Paper>
          ) : (
            <UnmappedView modelId={model.id} query={query} />
          )}
        </>
      )}

      {/* Item side panel */}
      <ItemPanel
        modelId={model?.id ?? null}
        item={selected}
        itemName={itemName}
        cardType={summary?.card_type ?? ""}
        codeField={summary?.code_field ?? ""}
        canMap={canMap}
        mutationTick={mutationTick}
        onMutated={onMappingMutated}
        onClose={() => setParam("selected", null)}
      />
    </Box>
  );
}

function HeaderMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <Box>
      <Typography variant="h6" component="div" sx={{ lineHeight: 1.2 }}>
        {value}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}

const MAPPING_TYPE_COLOR: Record<string, "primary" | "info" | "default" | "warning"> = {
  primary: "primary",
  secondary: "info",
  supporting: "info",
  candidate: "warning",
  historical: "default",
};

function ItemPanel({
  modelId,
  item,
  itemName,
  cardType,
  codeField,
  canMap,
  mutationTick,
  onMutated,
  onClose,
}: {
  modelId: string | null;
  item: ReferenceModelItemWithCounts | null;
  itemName: (i: { name: string; name_ar: string | null }) => string;
  cardType: string;
  codeField: string;
  canMap: boolean;
  mutationTick: number;
  onMutated: () => void;
  onClose: () => void;
}) {
  const { t } = useTranslation(["reports", "common"]);
  const [cards, setCards] = useState<ReferenceModelMappedCard[] | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ReferenceModelMappedCard | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    if (!item || !modelId) return;
    let cancelled = false;
    setCards(null);
    api
      .get<{ cards: ReferenceModelMappedCard[] }>(
        `/reference-models/${modelId}/items/${item.id}/cards`,
      )
      .then((res) => {
        if (!cancelled) setCards(res.cards);
      })
      .catch(() => {
        if (!cancelled) setCards([]);
      });
    return () => {
      cancelled = true;
    };
  }, [item, modelId, mutationTick]);

  const removeMapping = async (mappingId: string) => {
    setBusyId(mappingId);
    try {
      await api.delete(`/reference-models/mappings/${mappingId}`);
      onMutated();
    } finally {
      setBusyId(null);
    }
  };

  // Explicit mappings already on this item — hidden from the picker so a card
  // can't be double-mapped to the same item.
  const mappedCardIds = (cards ?? []).filter((c) => c.mapping_id).map((c) => c.id);

  return (
    <Drawer anchor="right" open={!!item} onClose={onClose}>
      <Box sx={{ width: { xs: "100vw", sm: 440 }, p: 2 }}>
        {item && (
          <>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
              <Chip size="small" variant="outlined" label={item.code} sx={{ direction: "ltr", fontFamily: "monospace" }} />
              <Typography variant="subtitle1" fontWeight={700} sx={{ flex: 1, minWidth: 0 }}>
                {itemName(item)}
              </Typography>
              <IconButton size="small" onClick={onClose}>
                <MaterialSymbol icon="close" size={20} />
              </IconButton>
            </Box>
            {item.name_ar && item.name_ar !== itemName(item) && (
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                {item.name_ar}
              </Typography>
            )}
            {item.description && (
              <Typography variant="body2" sx={{ mb: 2 }}>
                {item.description}
              </Typography>
            )}
            <Box sx={{ display: "flex", gap: 3, mb: 2 }}>
              <HeaderMetric label={t("rmBrowse.colMappedDirect")} value={item.mapped_direct} />
              <HeaderMetric label={t("rmBrowse.colMappedTotal")} value={item.mapped_total} />
            </Box>

            <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
              <Typography variant="subtitle2" sx={{ flex: 1 }}>
                {t("rmBrowse.mappedInventory", { count: cards?.length ?? 0 })}
              </Typography>
              {canMap && (
                <Button
                  size="small"
                  startIcon={<MaterialSymbol icon="add_link" size={18} />}
                  onClick={() => {
                    setEditing(null);
                    setDialogOpen(true);
                  }}
                >
                  {t("rmMap.addTitle")}
                </Button>
              )}
            </Box>
            {cards === null && (
              <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
                <CircularProgress size={22} />
              </Box>
            )}
            {cards && cards.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                {t("rmBrowse.mappedInventoryEmpty")}
              </Typography>
            )}
            {cards &&
              cards.map((card) => (
                <Paper
                  key={card.id}
                  variant="outlined"
                  sx={{ display: "flex", alignItems: "center", gap: 1, p: 1, mb: 0.75 }}
                >
                  <Box
                    component={Link}
                    to={`/cards/${card.id}`}
                    sx={{ flex: 1, minWidth: 0, textDecoration: "none", color: "inherit" }}
                  >
                    <Typography variant="body2" noWrap>
                      {card.name}
                    </Typography>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mt: 0.25 }}>
                      <Chip
                        size="small"
                        color={MAPPING_TYPE_COLOR[card.mapping_type] ?? "default"}
                        variant={card.source === "code" ? "outlined" : "filled"}
                        label={t(`rmMap.type.${card.mapping_type}`)}
                      />
                      {card.mapping_status && card.mapping_status !== "confirmed" && (
                        <Chip size="small" variant="outlined" label={t(`rmMap.status.${card.mapping_status}`)} />
                      )}
                      {card.confidence != null && (
                        <Typography variant="caption" color="text.secondary">
                          {card.confidence}%
                        </Typography>
                      )}
                    </Box>
                  </Box>
                  {card.code && (
                    <Chip size="small" variant="outlined" label={card.code} sx={{ direction: "ltr", fontFamily: "monospace" }} />
                  )}
                  {canMap && card.mapping_id && (
                    <>
                      <IconButton
                        size="small"
                        onClick={() => {
                          setEditing(card);
                          setDialogOpen(true);
                        }}
                      >
                        <MaterialSymbol icon="edit" size={16} />
                      </IconButton>
                      <IconButton
                        size="small"
                        disabled={busyId === card.mapping_id}
                        onClick={() => removeMapping(card.mapping_id!)}
                      >
                        <MaterialSymbol icon="link_off" size={16} />
                      </IconButton>
                    </>
                  )}
                </Paper>
              ))}
            {cards && cards.length > 0 && (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                {t("rmBrowse.includesDescendants", { field: codeField })}
              </Typography>
            )}
          </>
        )}
      </Box>
      {item && modelId && (
        <MappingDialog
          open={dialogOpen}
          itemId={item.id}
          cardType={cardType}
          excludeCardIds={mappedCardIds}
          editing={editing}
          onClose={() => setDialogOpen(false)}
          onSaved={onMutated}
        />
      )}
    </Drawer>
  );
}

function UnmappedView({ modelId, query }: { modelId: string; query: string }) {
  const { t } = useTranslation(["reports"]);
  const [cards, setCards] = useState<ReferenceModelMappedCard[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    setCards(null);
    api
      .get<{ cards: ReferenceModelMappedCard[] }>(`/reference-models/${modelId}/unmapped-inventory`)
      .then((res) => {
        if (!cancelled) setCards(res.cards);
      })
      .catch(() => {
        if (!cancelled) setCards([]);
      });
    return () => {
      cancelled = true;
    };
  }, [modelId]);

  const q = query.trim().toLowerCase();
  const filtered = (cards ?? []).filter(
    (c) => !q || c.name.toLowerCase().includes(q) || (c.code ?? "").toLowerCase().includes(q),
  );

  if (cards === null) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Paper variant="outlined">
      <Box sx={{ p: 1.5, borderBottom: "1px solid", borderColor: "divider" }}>
        <Typography variant="body2" color="text.secondary">
          {t("rmBrowse.unmappedHint", { count: cards.length })}
        </Typography>
      </Box>
      {filtered.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
          {t("rmBrowse.unmappedEmpty")}
        </Typography>
      )}
      {filtered.map((card) => (
        <Box
          key={card.id}
          component={Link}
          to={`/cards/${card.id}`}
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            py: 0.75,
            px: 1.5,
            textDecoration: "none",
            color: "inherit",
            borderBottom: "1px solid",
            borderColor: "divider",
            "&:hover": { bgcolor: "action.hover" },
          }}
        >
          <Typography variant="body2" sx={{ flex: 1, minWidth: 0 }} noWrap>
            {card.name}
          </Typography>
          {card.code && (
            <Chip
              size="small"
              variant="outlined"
              color="warning"
              label={card.code}
              sx={{ direction: "ltr", fontFamily: "monospace" }}
            />
          )}
        </Box>
      ))}
    </Paper>
  );
}
